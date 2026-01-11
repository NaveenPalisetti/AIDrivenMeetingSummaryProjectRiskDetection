from mcp.core.utils import gen_id
from mcp.core.a2a_base_agent import A2AAgent, AgentCard, AgentCapability, A2AMessage
import os, json, uuid
from mcp.agents.notification_agent import NotificationAgent
from mcp.tools.jira_monitor import notify_due_tasks, notify_sprints_ending_soon
from mcp.agents.task_utils import extract_and_create_tasks

with open('mcp/config/credentials.json') as f:
	creds = json.load(f)
jira = creds.get("jira", {})

os.environ["JIRA_URL"] = jira.get("base_url", "")
os.environ["JIRA_USER"] = jira.get("user", "")
os.environ["JIRA_TOKEN"] = jira.get("token", "")
os.environ["JIRA_PROJECT"] = jira.get("project", "PROJ")
try:
	from jira import JIRA
except ImportError:
	JIRA = None


class TaskManagerAgent(A2AAgent):
	def __init__(self):
		agent_card = AgentCard(
			agent_id="task-manager-agent",
			name="Meeting Task Manager Agent",
			description="Extracts and manages meeting action items, creates Jira issues if configured.",
			version="1.0.0",
			capabilities=[
				AgentCapability(
					name="extract_and_create_tasks",
					description="Extract action items from summary and create Jira issues.",
					parameters={"meeting_id": "str", "summary": "dict"}
				)
			]
		)
		super().__init__(agent_card)
		self.tasks_file = os.path.join(os.path.dirname(__file__), '..', 'data', 'tasks', 'tasks.json')
		os.makedirs(os.path.dirname(self.tasks_file), exist_ok=True)
		if not os.path.exists(self.tasks_file):
			with open(self.tasks_file, 'w', encoding='utf-8') as f:
				json.dump([], f)
		# Jira config (set these as env vars or config)
		self.jira_url = os.environ.get("JIRA_URL")
		self.jira_user = os.environ.get("JIRA_USER")
		self.jira_token = os.environ.get("JIRA_TOKEN")
		self.jira_project = os.environ.get("JIRA_PROJECT")
		self.jira = None
		print(f"TaskManagerAgent: JIRA_URL={self.jira_url}, JIRA_USER={self.jira_user}, JIRA_PROJECT={self.jira_project}")  
		if JIRA and self.jira_url and self.jira_user and self.jira_token:
			self.jira = JIRA(server=self.jira_url, basic_auth=(self.jira_user, self.jira_token))

	def get_due_soon_tasks(self, days=1):
		"""
		Return a list of Jira tasks due within the next `days` days.
		"""
		from datetime import datetime, timedelta
		due_soon = []
		if not self.jira:
			return due_soon
		jql = f'project={self.jira_project} AND duedate >= now() AND duedate <= {days}d order by duedate asc'
		try:
			issues = self.jira.search_issues(jql)
			for issue in issues:
				due = getattr(issue.fields, 'duedate', None)
				if due:
					due_soon.append({
						'key': issue.key,
						'summary': issue.fields.summary,
						'due_date': due
					})
		except Exception as e:
			print(f"[TaskManagerAgent] Error fetching due soon tasks: {e}")
		return due_soon

	def get_sprints_ending_soon(self, days=1):
		"""
		Return a list of sprints ending within the next `days` days (if using Jira Agile).
		"""
		# This requires Jira Agile API and board/sprint setup
		# Example assumes you have a board id set as self.jira_board_id
		from datetime import datetime, timedelta
		ending_soon = []
		if not self.jira or not hasattr(self, 'jira_board_id'):
			return ending_soon
		try:
			sprints = self.jira.sprints(self.jira_board_id, state='active')
			now = datetime.utcnow()
			soon = now + timedelta(days=days)
			for sprint in sprints:
				if sprint.endDate:
					end = datetime.strptime(sprint.endDate[:19], '%Y-%m-%dT%H:%M:%S')
					if now < end <= soon:
						ending_soon.append({
							'id': sprint.id,
							'name': sprint.name,
							'end_date': sprint.endDate
						})
		except Exception as e:
			print(f"[TaskManagerAgent] Error fetching sprints: {e}")
		return ending_soon

	def extract_and_create_tasks(self, meeting_id, summary):
		return extract_and_create_tasks(meeting_id, summary)
