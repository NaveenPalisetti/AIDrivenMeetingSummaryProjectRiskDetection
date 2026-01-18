
from mcp.tools.notification import send_notification

def notify_due_tasks(days=2):
    from mcp.agents.task_manager_agent import TaskManagerAgent
    agent = TaskManagerAgent()
    due_tasks = agent.get_due_soon_tasks(days=days)
    for task in due_tasks:
        send_notification(f"Jira Task '{task['summary']}' is due soon: {task['due_date']}")

def notify_sprints_ending_soon(days=2):
    from mcp.agents.task_manager_agent import TaskManagerAgent
    agent = TaskManagerAgent()
    sprints = agent.get_sprints_ending_soon(days=days)
    for sprint in sprints:
        send_notification(f"Jira Sprint '{sprint['name']}' is ending soon: {sprint['end_date']}")

if __name__ == "__main__":
    notify_due_tasks()
    notify_sprints_ending_soon()
