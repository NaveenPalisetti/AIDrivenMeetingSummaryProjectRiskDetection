from langchain.tools import tool
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
from mcp.agents.bart_summarizer import summarize_with_bart
from mcp.agents.mistral_summarizer import summarize_with_mistral




import os
# BART model path logic
bart_drive_path = os.environ.get("BART_MODEL_PATH")
if bart_drive_path and os.path.exists(bart_drive_path):
    bart_model_path = bart_drive_path
else:
    bart_model_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "models", "bart_finetuned_meeting_summary"))
bart_tokenizer = AutoTokenizer.from_pretrained(bart_model_path)
bart_model = AutoModelForSeq2SeqLM.from_pretrained(bart_model_path)

# Mistral model path logic
mistral_drive_path = os.environ.get("MISTRAL_MODEL_PATH")
colab_mistral_path = "/content/mistral-7B-Instruct-v0.2"
if mistral_drive_path and os.path.exists(mistral_drive_path):
    mistral_model_path = mistral_drive_path
elif os.path.exists(colab_mistral_path):
    mistral_model_path = colab_mistral_path
else:
    mistral_model_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "models", "mistral_finetuned_meeting_summary"))
try:
    mistral_tokenizer = AutoTokenizer.from_pretrained(mistral_model_path)
    mistral_model = AutoModelForSeq2SeqLM.from_pretrained(mistral_model_path)
except Exception:
    mistral_tokenizer = None
    mistral_model = None



@tool
def summarize_meeting(transcript: str, mode: str = "bart") -> dict:
    """Summarize a meeting transcript using the selected model (bart or mistral), with action item extraction."""
    if not transcript or len(transcript.split()) < 10:
        return {"summary": "Transcript too short for summarization.", "action_items": []}
    meeting_id = "meeting"
    if mode == "mistral" and mistral_tokenizer and mistral_model:
        result = summarize_with_mistral(mistral_tokenizer, mistral_model, transcript, meeting_id)
        summary = result.get('summary_text', '')
        action_items = result.get('action_items', [])
    else:
        result = summarize_with_bart(bart_tokenizer, bart_model, transcript, meeting_id)
        summary = result.get('summary_text', '')
        action_items = result.get('action_items', [])
    return {"summary": summary, "action_items": action_items}


# --- Additional LangChain tools for other agents ---

@tool
def fetch_calendar_events_tool(user_id: str = None, date_range: str = None) -> dict:
    """Fetch calendar events or meeting transcript for a user and date range."""
    # TODO: Replace with real calendar agent logic
    return {"events": ["Meeting 1", "Meeting 2"], "transcript": "Sample transcript for summarization."}

@tool
def detect_risks_tool(summary: str = None) -> dict:
    """Detect risks from a meeting summary."""
    # TODO: Replace with real risk detection agent logic
    return {"risks": ["Risk 1: Deadline tight", "Risk 2: Resource missing"]}

@tool
def extract_tasks_tool(summary: str = None) -> dict:
    """Extract tasks/action items from a meeting summary."""
    # TODO: Replace with real task extraction agent logic
    return {"tasks": ["Task 1: Prepare slides", "Task 2: Email client"]}

@tool
def send_notification_tool(task: str = None, user: str = None) -> dict:
    """Send a notification to a user about a task or event."""
    # TODO: Replace with real notification agent logic
    return {"notified": True, "user": user, "task": task}
