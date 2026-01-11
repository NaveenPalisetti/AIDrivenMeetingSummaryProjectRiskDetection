import os, json
from typing import Optional

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
DATA_DIR = os.path.abspath(DATA_DIR)

class ContextHandler:
	def __init__(self):
		self.base = os.path.join(DATA_DIR)
		self.summaries_dir = os.path.join(self.base, 'summaries')
		os.makedirs(self.summaries_dir, exist_ok=True)

	def store_meeting_raw(self, meeting_id: str, transcript: str):
		path = os.path.join(self.base, 'transcripts', f'{meeting_id}.txt')
		os.makedirs(os.path.dirname(path), exist_ok=True)
		with open(path, 'w', encoding='utf-8') as f:
			f.write(transcript)

	def save_summary(self, meeting_id: str, summary_obj: dict):
		path = os.path.join(self.summaries_dir, f'{meeting_id}.json')
		with open(path, 'w', encoding='utf-8') as f:
			json.dump(summary_obj, f, indent=2)

	def get_summary(self, meeting_id: str) -> Optional[dict]:
		path = os.path.join(self.summaries_dir, f'{meeting_id}.json')
		if not os.path.exists(path):
			return None
		with open(path, 'r', encoding='utf-8') as f:
			return json.load(f)
