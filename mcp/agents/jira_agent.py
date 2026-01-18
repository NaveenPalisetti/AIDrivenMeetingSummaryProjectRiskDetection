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
        print("[JiraAgent] Starting Jira issue creation...")
        import os, json
        cred_path_local = 'mcp/config/credentials.json'
        cred_path_drive = '/content/drive/MyDrive/Dissertation/Project/credentials.json'
        if os.path.exists(cred_path_local):
            with open(cred_path_local) as f:
                creds = json.load(f)
        elif os.path.exists(cred_path_drive):
            with open(cred_path_drive) as f:
                creds = json.load(f)
        else:
            creds = {}
        jira_cfg = creds.get("jira", {})

        os.environ["JIRA_URL"] = jira_cfg.get("base_url", os.environ.get("JIRA_URL", ""))
        os.environ["JIRA_USER"] = jira_cfg.get("user", os.environ.get("JIRA_USER", ""))
        os.environ["JIRA_TOKEN"] = jira_cfg.get("token", os.environ.get("JIRA_TOKEN", ""))
        os.environ["JIRA_PROJECT"] = jira_cfg.get("project", os.environ.get("JIRA_PROJECT", "PROJ"))

        JIRA_URL = os.environ.get("JIRA_URL")
        JIRA_USER = os.environ.get("JIRA_USER")
        JIRA_TOKEN = os.environ.get("JIRA_TOKEN")
        JIRA_PROJECT = os.environ.get("JIRA_PROJECT", "PROJ")

        print(f"[JiraAgent] JIRA_URL={JIRA_URL}")
        print(f"[JiraAgent] JIRA_USER={JIRA_USER}")
        print(f"[JiraAgent] JIRA_PROJECT={JIRA_PROJECT}")

        try:
            from jira import JIRA
        except ImportError:
            raise ImportError("Please install the 'jira' package: pip install jira")

        meeting_id = date or "meeting"
        if isinstance(summary, str):
            summary = {"summary_text": summary}
        from mcp.agents.task_utils import extract_and_create_tasks
        action_items = []
        if isinstance(summary, list):
            action_items = summary
        elif isinstance(summary, dict):
            if 'action_items' in summary and isinstance(summary['action_items'], list):
                action_items = summary['action_items']
            else:
                action_items = [summary]
        else:
            action_items = [{"title": str(summary)}]

        jira = None
        if JIRA and JIRA_URL and JIRA_USER and JIRA_TOKEN:
            print("[JiraAgent] Connecting to Jira...")
            try:
                jira = JIRA(server=JIRA_URL, basic_auth=(JIRA_USER, JIRA_TOKEN))
                print("[JiraAgent] Jira connection successful.")
            except Exception as e:
                print(f"[JiraAgent] Jira connection failed: {e}")
                jira = None
        else:
            print("[JiraAgent] Jira config missing or incomplete.")

        created_tasks = []
        for item in action_items:
            title = item.get('title', str(item))
            # Remove newlines from summary/title for Jira
            if isinstance(title, str):
                title = title.replace('\n', ' ').replace('\r', ' ')
            owner = item.get('owner', None)
            due = item.get('due', None)
            issue_dict = {
                'project': {'key': JIRA_PROJECT},
                'summary': title,
                'description': f"Owner: {owner or 'Unassigned'}\nDue: {due or 'Unspecified'}\nMeeting ID: {meeting_id}",
                'issuetype': {'name': 'Task'},
            }
            print(f"[JiraAgent] Creating Jira issue for: {title}")
            if jira:
                try:
                    issue = jira.create_issue(fields=issue_dict)
                    print(f"[JiraAgent] Jira issue created: {issue.key}")
                    created_tasks.append({
                        "meeting_id": meeting_id,
                        "title": title,
                        "owner": owner,
                        "due": due,
                        "task": f"Jira Issue {issue.key} created",
                        "jira_issue_key": issue.key
                    })
                except Exception as e:
                    print(f"[JiraAgent] Failed to create Jira issue: {e}")
                    created_tasks.append({
                        "meeting_id": meeting_id,
                        "title": title,
                        "owner": owner,
                        "due": due,
                        "task": f"Failed to create Jira issue: {e}",
                        "jira_issue_key": None
                    })
            else:
                print("[JiraAgent] Skipping Jira creation due to missing connection.")
                created_tasks.append({
                    "meeting_id": meeting_id,
                    "title": title,
                    "owner": owner,
                    "due": due,
                    "task": f"Jira config missing or JIRA not available.",
                    "jira_issue_key": None
                })
        print(f"[JiraAgent] Created tasks: {created_tasks}")
        message = A2AMessage(message_id=str(uuid.uuid4()), role="agent")
        message.add_part("application/json", {"created_tasks": created_tasks, "user": user, "date": date})
        print(f"[JiraAgent] Returning message: {message}")
        return message        