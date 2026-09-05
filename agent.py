import traceback
from langchain_nvidia_ai_endpoints import ChatNVIDIA
from langchain.agents import AgentExecutor, create_json_chat_agent
from langchain_core.prompts import ChatPromptTemplate

# Import all tools
from tools.inventory import receive_stock, add_new_product, query_stock, query_low_stock
from tools.billing import manage_bill
from tools.product_resolution import resolve_product
from tools.khata import manage_khata
from tools.reporting import daily_close, set_preference, get_preferences
from utils.pdf_gen import generate_invoice_pdf_tool
from utils.pptx_gen import generate_analysis_deck_tool
from db import supabase

# Initialize LLM
llm = ChatNVIDIA(
    model="nvidia/nemotron-3-ultra-550b-a55b",
    temperature=0.1,
    top_p=0.9,
    max_tokens=1024,
)

tools = [
    resolve_product, receive_stock, add_new_product, query_stock, query_low_stock,
    manage_bill, manage_khata, daily_close, set_preference, get_preferences,
    generate_invoice_pdf_tool, generate_analysis_deck_tool
]

# JSON Chat Prompt (Bulletproof for multi-argument tools)
json_prompt = ChatPromptTemplate.from_messages([
    ("system", """You are a highly capable Supermarket Operations Agent. 
You manage inventory, billing, customer credit (khata), and daily reporting.

You have access to the following tools:
{tools}

To use a tool, you MUST use the following JSON format:
```json
{{
  "action": "tool_name",
  "action_input": {{"arg1": "value1", "arg2": "value2"}}
}}
```
Valid "action" values: {tool_names}

If you want to respond to the human without using a tool, use this format:
```json
{{
  "action": "Final Answer",
  "action_input": "Your natural language response here"
}}
```

Begin!"""),
    ("human", "{input}\n\n{agent_scratchpad}")
])

# Create Agent using JSON Chat (supports multi-argument tools safely)
agent = create_json_chat_agent(llm, tools, json_prompt)
agent_executor = AgentExecutor(
    agent=agent, 
    tools=tools, 
    verbose=True, 
    handle_parsing_errors="Please format your response as a valid JSON blob with 'action' and 'action_input' keys.",
    max_iterations=4,
    early_stopping_method="force"
)

def process_message(session_id: str, user_message: str) -> dict:
    """Processes a message through the agent, maintaining chat history in Supabase."""
    try:
        # Load history
        res = supabase.table("chat_history").select("*").eq("session_id", session_id).order("created_at").execute()
        chat_history = []
        last_interaction_time = None
        
        for row in res.data:
            msg = row['message']
            prefix = "Human: " if msg['type'] == 'human' else "AI: "
            chat_history.append(f"{prefix}{msg['content']}")
            last_interaction_time = row['created_at'] # ISO string
            
        history_str = "\n".join(chat_history)
        
        # Determine Greeting/Re-engagement context
        greeting_context = ""
        if not chat_history:
            greeting_context = "[SYSTEM NOTE: This is your very first conversation with this store owner. Briefly introduce yourself, explain what you do (manage stock, bills, khata), and offer help.]\n\n"
        elif last_interaction_time:
            from datetime import datetime, timezone
            # Basic re-engagement if last message was > 24 hours ago
            last_dt = datetime.fromisoformat(last_interaction_time.replace("Z", "+00:00"))
            hours_since = (datetime.now(timezone.utc) - last_dt).total_seconds() / 3600
            if hours_since > 24:
                greeting_context = "[SYSTEM NOTE: You haven't spoken to the owner in over 24 hours. Start with a brief, friendly 'welcome back' or 'long time no see' type greeting.]\n\n"
            
        # Execute agent
        response = agent_executor.invoke({
            "input": greeting_context + user_message,
            "chat_history": history_str
        })
        
        output = response.get("output", "I processed your request.")
        
        # Save to history
        supabase.table("chat_history").insert({"session_id": session_id, "message": {"type": "human", "content": user_message}}).execute()
        supabase.table("chat_history").insert({"session_id": session_id, "message": {"type": "ai", "content": output}}).execute()
        
        return {"text": output}
        
    except Exception as e:
        # YAGNI: Print full traceback to console for debugging, return clean message to user
        print("--- AGENT ERROR ---")
        traceback.print_exc()
        print("-------------------")
        return {"text": f"An internal error occurred while thinking: {str(e)}\nPlease check the console logs for details."}
