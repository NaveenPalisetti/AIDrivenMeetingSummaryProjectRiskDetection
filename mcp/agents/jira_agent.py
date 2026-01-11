from mcp.core.a2a_base_agent import A2AAgent, AgentCard, AgentCapability, A2AMessage
import uuid  # Used for message IDs

class JiraAgent(A2AAgent):
    def __init__(self):
        agent_card = AgentCard(
            agent_id="jira-agent",
            name="Jira Task Creation Agent",
            description="Creates Jira issues from meeting summaries and action items.",
            version="1.0.0",
            capabilities=[
                AgentCapability(
                    name="create_jira",
                    description="Create Jira issues from summary.",
                    parameters={"summary": "str or dict", "user": "str", "date": "str"}
                )
            ]
        )
        super().__init__(agent_card)

    def create_jira(self, summary, user=None, date=None):
        from mcp.agents.task_manager_agent import TaskManagerAgent
        meeting_id = date or "meeting"
        if isinstance(summary, str):
            summary = {"summary_text": summary}
        task_manager = TaskManagerAgent()
        tasks = task_manager.extract_and_create_tasks(meeting_id, summary)
        message = A2AMessage(message_id=str(uuid.uuid4()), role="agent")
        message.add_part("application/json", {"created_tasks": tasks, "user": user, "date": date})
        return message
