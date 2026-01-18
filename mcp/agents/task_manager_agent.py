from mcp.core.utils import gen_id
from mcp.core.a2a_base_agent import A2AAgent, AgentCard, AgentCapability, A2AMessage
import os, json, uuid
from mcp.agents.notification_agent import NotificationAgent
from mcp.tools.jira_monitor import notify_due_tasks, notify_sprints_ending_soon
from mcp.agents.task_utils import extract_and_create_tasks


# Robust credentials loading: try local, else fallback to Google Drive
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

	def detect_jira_risks(self, days_overdue=0, days_stale=7):
		"""
		Detect risks from Jira issues: overdue, unassigned, blocked, no due date, stale, high priority unresolved.
		Returns a list of risk dicts.
		"""
		risks = []
		if not self.jira:
			return risks
		from datetime import datetime, timedelta
		now = datetime.utcnow()
		# 1. Overdue tasks
		try:
			jql_overdue = f'project={self.jira_project} AND duedate <= now() AND statusCategory != Done'
			for issue in self.jira.search_issues(jql_overdue):
				risks.append({
					'type': 'overdue',
					'key': issue.key,
					'summary': issue.fields.summary,
					'due_date': getattr(issue.fields, 'duedate', None),
					'description': 'Task is overdue.'
				})
		except Exception as e:
			print(f"[TaskManagerAgent] Error fetching overdue tasks: {e}")
		# 2. Unassigned tasks
		try:
			jql_unassigned = f'project={self.jira_project} AND assignee is EMPTY AND statusCategory != Done'
			for issue in self.jira.search_issues(jql_unassigned):
				risks.append({
					'type': 'unassigned',
					'key': issue.key,
					'summary': issue.fields.summary,
					'description': 'Task is unassigned.'
				})
		except Exception as e:
			print(f"[TaskManagerAgent] Error fetching unassigned tasks: {e}")
		# 3. Blocked/flagged issues (if using Jira Software flags)
		try:
			jql_blocked = f'project={self.jira_project} AND (flagged = Impediment OR status = Blocked) AND statusCategory != Done'
			for issue in self.jira.search_issues(jql_blocked):
				risks.append({
					'type': 'blocked',
					'key': issue.key,
					'summary': issue.fields.summary,
					'description': 'Task is blocked or flagged.'
				})
		except Exception as e:
			print(f"[TaskManagerAgent] Error fetching blocked tasks: {e}")
		# 4. No due date
		try:
			jql_nodue = f'project={self.jira_project} AND duedate is EMPTY AND statusCategory != Done'
			for issue in self.jira.search_issues(jql_nodue):
				risks.append({
					'type': 'no_due_date',
					'key': issue.key,
					'summary': issue.fields.summary,
					'description': 'Task has no due date.'
				})
		except Exception as e:
			print(f"[TaskManagerAgent] Error fetching no due date tasks: {e}")
		# 5. Stale tasks (not updated in days_stale)
		try:
			stale_date = (now - timedelta(days=days_stale)).strftime('%Y-%m-%d')
			jql_stale = f'project={self.jira_project} AND updated <= "{stale_date}" AND statusCategory != Done'
			for issue in self.jira.search_issues(jql_stale):
				risks.append({
					'type': 'stale',
					'key': issue.key,
					'summary': issue.fields.summary,
					'last_updated': getattr(issue.fields, 'updated', None),
					'description': f'Task not updated in {days_stale}+ days.'
				})
		except Exception as e:
			print(f"[TaskManagerAgent] Error fetching stale tasks: {e}")
		# 6. High priority unresolved
		try:
			jql_highprio = f'project={self.jira_project} AND priority = Highest AND statusCategory != Done'
			for issue in self.jira.search_issues(jql_highprio):
				risks.append({
					'type': 'high_priority',
					'key': issue.key,
					'summary': issue.fields.summary,
					'priority': getattr(issue.fields, 'priority', None),
					'description': 'High priority task unresolved.'
				})
		except Exception as e:
			print(f"[TaskManagerAgent] Error fetching high priority tasks: {e}")
		return risks
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
