# Supermarket Ops Agent — README

**Live bot:** [@NebuuuuuBot] (Telegram)

## 1. Harness: LangChain agent, and why

The agent is built on **LangChain** (Python) rather than Claude Agent SDK / deep agent / Vercel AI SDK.

- **Tool-calling model fits the task shape.** The brief explicitly forbids a regex/intent router; LangChain's tool-calling `AgentExecutor` puts the model in charge of picking and chaining tools each turn, with structured (Pydantic) tool schemas that reject malformed calls before they touch the store.
- **Clean separation of prompt vs. business logic.** Tools are plain Python functions with their own validation, transactions, and error paths — the prompt only carries persona, store context, and standing preferences, never the rules themselves.
- **Fits the deployment surface.** A Flask webhook is a natural front door for Telegram; LangChain's agent runs synchronously inside a request handler without needing a bespoke node-graph runtime, avoiding the LangGraph-style state machine the brief explicitly steers away from.
- **Persistence-friendly.** Supabase (Postgres) sits behind the tools, so every tool call is a normal transactional DB operation — no framework-specific state to keep in sync with the database.

## 2. Control loop

```
Telegram update → POST /webhook (Flask) → dedupe by update_id
   → load owner + standing preferences from Supabase
   → LangChain AgentExecutor: observe → reason → call tool(s) → observe result → continue
     (multiple tool calls chained within one turn, e.g. lookup price → check stock → add to draft bill)
   → final natural-language reply → sent back to Telegram
```
The loop is a straight ReAct-style cycle per incoming message; each tool call and its result is appended to the agent's scratchpad so it can chain lookups (price, stock, GST slab) before acting, and re-plan if a tool refuses.

## 3. Skill / tool design

Tools are grouped by store function, each thin and single-purpose so the model composes them rather than any one tool encoding a workflow:

- **Inventory** — `add_product`, `receive_stock`, `get_stock`, `low_stock_report`
- **Billing** — `start_bill`, `add_line_item`, `remove_line_item`, `finalize_bill` (only this decrements stock)
- **Khata** — `credit_add`, `credit_pay`, `credit_balance`
- **Operations** — `daily_close`
- **Documents** — `generate_invoice_pdf`, `generate_analysis_deck`
- **Preferences** — `get_preference`, `set_preference`

Every tool validates its own inputs against the DB (no hardcoded product/price data), and every write is a single Supabase RPC transaction so partial updates can't happen.

## 4. How each hard part was solved

1. **Grounding** — all product, price, GST slab, and stock lookups are tool calls against Supabase; the agent has no product knowledge of its own.
2. **Oversell guard** — `finalize_bill` calls a Postgres RPC that checks-and-decrements stock inside one transaction; insufficient stock raises an error the tool surfaces back to the model, which reports the refusal instead of billing.
3. **GST correctness** — each SKU carries HSN code and slab in the DB; billing computes CGST/SGST split per line item and rounds at the invoice level, not per line, to avoid drift.
4. **Multi-turn bills** — a draft bill row (keyed by chat ID) holds line items across messages; `add_line_item`/`remove_line_item` mutate the draft, and stock is only touched on `finalize_bill`.
5. **Idempotency** — Telegram's `update_id` is recorded and deduped at the webhook layer; `finalize_bill` also takes an idempotency key so a retried finalize returns the existing bill instead of billing twice.
6. **Concurrency** — stock mutations go through a Supabase RPC using row-level locking (`SELECT ... FOR UPDATE`), so a bill finalize and a stock-in racing each other serialize instead of corrupting quantity.
7. **Guardrails** — `finalize_bill` refuses lines priced below cost, there is no delete-stock tool at all (only stock-in/stock-out with audit trail), and `credit_pay`/`credit_balance` check the customer exists before acting — refusals are returned as tool errors, not swallowed.
8. **Real artifacts** — `generate_invoice_pdf` renders a proper GST invoice (tax breakup, HSN, CGST/SGST) from the finalized bill row; `generate_analysis_deck` builds a PPTX with real charts (sales trend, top items, stock health, GST collected) from Supabase aggregates.
9. **Memory across sessions** — standing preferences (default payment mode, preferred brand, shop name/GSTIN) live in a Supabase `preferences` table keyed by owner, loaded at the start of every turn regardless of `/new` — memory lives outside the LangChain conversation buffer entirely.
