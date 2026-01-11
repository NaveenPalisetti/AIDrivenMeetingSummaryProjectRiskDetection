from mcp.core.utils import gen_id  # Used for risk IDs
class RiskDetectionAgent:
	def __init__(self):
		pass

	def detect(self, meeting_id: str, summary: dict, tasks: list, progress: dict):
		risks = []
		blockers = summary.get('blockers', [])
		summary_text = summary.get('summary_text','').lower()
		if blockers:
			for b in blockers:
				risks.append({
					'id': gen_id('risk'),
					'meeting_id': meeting_id,
					'description': b,
					'severity': 'high'
				})
		if any(k in summary_text for k in ['delay', 'delayed', 'blocked', 'pending', 'cannot', 'error']):
			risks.append({
				'id': gen_id('risk'),
				'meeting_id': meeting_id,
				'description': 'Detected terms indicating potential delay or blockage.',
				'severity': 'medium'
			})
		if len(tasks) > 5:
			risks.append({
				'id': gen_id('risk'),
				'meeting_id': meeting_id,
				'description': 'Many open tasks created in single meeting — check capacity.',
				'severity': 'medium'
			})
		if not risks:
			risks.append({
				'id': gen_id('risk'),
				'meeting_id': meeting_id,
				'description': 'No immediate risks detected.',
				'severity': 'low'
			})
		return risks
