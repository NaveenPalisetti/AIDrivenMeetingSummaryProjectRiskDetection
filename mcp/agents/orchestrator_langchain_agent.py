from langchain.agents import initialize_agent, Tool
from langchain.memory import ConversationBufferMemory
from mcp.agents.langchain_tools import summarize_with_bart
# Import other tools as you implement them

# List all tools (add more as you refactor other agents)
tools = [
    Tool.from_function(summarize_with_bart),
    # Tool.from_function(fetch_calendar_events),
    # Tool.from_function(extract_tasks),
    # Tool.from_function(send_notification),
    # Tool.from_function(detect_risks),
]

memory = ConversationBufferMemory(memory_key="chat_history")

# You can use HuggingFaceHub or your own LLM wrapper for local models
llm = None  # Replace with your LLM instance if needed

agent = initialize_agent(
    tools,
    llm,
    agent_type="chat-conversational-react-description",
    memory=memory,
    verbose=True,
)

def orchestrator_agent_mcp(mcp_message: dict) -> dict:
    user_message = mcp_message["message"]
    context = mcp_message.get("context", {})
    state = mcp_message.get("state", {})
    result = agent.run(user_message)
    return {
        "context": context,
        "state": state,
        "message": user_message,
        "result": result
    }
