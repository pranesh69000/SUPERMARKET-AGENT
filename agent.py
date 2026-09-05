import traceback
from langchain_nvidia_ai_endpoints import ChatNVIDIA
from langchain.agents import AgentExecutor, create_react_agent
from langchain_core.prompts import PromptTemplate

# Import all tools
from tools.inventory import receive_stock, add_new_product, query_stock, query_low_stock
from tools.billing import manage_bill
from tools.khata import manage_khata
from tools.reporting import daily_close, set_preference, get_preferences
from utils.pdf_gen import generate_invoice_pdf_tool
from utils.pptx_gen import generate_analysis_deck_tool
from db import supabase

tools = [
    receive_stock, add_new_product, query_stock, query_low_stock,
    manage_bill, manage_khata, daily_close, set_preference, get_preferences,
    generate_invoice_pdf_tool, generate_analysis_deck_tool
]

# Initialize LLM
llm = ChatNVIDIA(
    model="nvidia/nemotron-3-ultra-550b-a55b",
    temperature=0.1,
    max_tokens=2048,
)

# Standard ReAct Prompt that works without native bind_tools support
react_prompt = PromptTemplate.from_template("""You are the AI operations assistant for an Indian supermarket/kirana store.
You communicate via Telegram with the store owner. Your responses should be concise, professional, and helpful.

TOOLS:
------
You have access to the following tools:

{tools}

To use a tool, please use the following format:

```
Thought: Do I need to use a tool? Yes
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
```

When you have a response to say to the Human, or if you do not need to use a tool, you MUST use the format:

```
Thought: Do I need to use a tool? No
Final Answer: [your response here]
```

Begin!

Previous conversation history:
{chat_history}

New input: {input}
{agent_scratchpad}""")

# Create Agent using ReAct (works with any model)
agent = create_react_agent(llm, tools, react_prompt)
agent_executor = AgentExecutor(
    agent=agent, 
    tools=tools, 
    verbose=True, 
    handle_parsing_errors="Check your output format! You MUST use 'Action:' and 'Action Input:' to use a tool, or 'Final Answer:' to talk to the user. Do not just output conversational text.",
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
