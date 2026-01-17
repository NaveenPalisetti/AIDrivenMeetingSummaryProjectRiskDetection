from langchain.tools import tool
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
from mcp.agents.bart_summarizer import summarize_with_bart
from mcp.agents.mistral_summarizer import summarize_with_mistral


import os
# Lazy-loaded model holders
bart_tokenizer = None
bart_model = None
mistral_tokenizer = None
mistral_model = None


def _resolve_bart_path():
    bart_drive_path = os.environ.get("BART_MODEL_PATH")
    if bart_drive_path and os.path.exists(bart_drive_path):
        return bart_drive_path
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "models", "bart_finetuned_meeting_summary"))


def _resolve_mistral_path():
    mistral_drive_path = os.environ.get("MISTRAL_MODEL_PATH")
    colab_mistral_path = "/content/mistral-7B-Instruct-v0.2"
    if mistral_drive_path and os.path.exists(mistral_drive_path):
        return mistral_drive_path
    if os.path.exists(colab_mistral_path):
        return colab_mistral_path
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "models", "mistral_finetuned_meeting_summary"))


def get_bart_models():
    """Lazily load and return (tokenizer, model) for BART. Returns (None, None) on failure."""
    global bart_tokenizer, bart_model
    if bart_tokenizer is None or bart_model is None:
        model_path = _resolve_bart_path()
        if not os.path.exists(model_path):
            bart_tokenizer, bart_model = None, None
            return None, None
        try:
            bart_tokenizer = AutoTokenizer.from_pretrained(model_path, local_files_only=True)
            bart_model = AutoModelForSeq2SeqLM.from_pretrained(model_path, local_files_only=True)
        except Exception:
            bart_tokenizer, bart_model = None, None
    return bart_tokenizer, bart_model


def get_mistral_models():
    """Lazily load and return (tokenizer, model) for Mistral. Returns (None, None) on failure."""
    global mistral_tokenizer, mistral_model
    if mistral_tokenizer is None or mistral_model is None:
        model_path = _resolve_mistral_path()
        if not os.path.exists(model_path):
            mistral_tokenizer, mistral_model = None, None
            return None, None
        try:
            mistral_tokenizer = AutoTokenizer.from_pretrained(model_path, local_files_only=True)
            mistral_model = AutoModelForSeq2SeqLM.from_pretrained(model_path, local_files_only=True)
        except Exception:
            mistral_tokenizer, mistral_model = None, None
    return mistral_tokenizer, mistral_model

@tool
def summarize_meeting(transcript: str, mode: str = "bart") -> dict:
    """Summarize a meeting transcript using the selected model (bart or mistral), with action item extraction."""
    if not transcript or len(transcript.split()) < 10:
        return {"summary": "Transcript too short for summarization.", "action_items": []}
    meeting_id = "meeting"
    # Attempt to lazily load requested models
    if mode == "mistral":
        mtok, mmod = get_mistral_models()
        if mtok and mmod:
            result = summarize_with_mistral(mtok, mmod, transcript, meeting_id)
            summary = result.get('summary_text', '')
            action_items = result.get('action_items', [])
        else:
            # Fallback to BART if Mistral unavailable
            btok, bmod = get_bart_models()
            if btok and bmod:
                result = summarize_with_bart(btok, bmod, transcript, meeting_id)
                summary = result.get('summary_text', '')
                action_items = result.get('action_items', [])
            else:
                return {"summary": "No local models available for summarization.", "action_items": []}
    else:
        btok, bmod = get_bart_models()
        if btok and bmod:
            result = summarize_with_bart(btok, bmod, transcript, meeting_id)
            summary = result.get('summary_text', '')
            action_items = result.get('action_items', [])
        else:
            # Try Mistral as fallback
            mtok, mmod = get_mistral_models()
            if mtok and mmod:
                result = summarize_with_mistral(mtok, mmod, transcript, meeting_id)
                summary = result.get('summary_text', '')
                action_items = result.get('action_items', [])
            else:
                return {"summary": "No local models available for summarization.", "action_items": []}
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
