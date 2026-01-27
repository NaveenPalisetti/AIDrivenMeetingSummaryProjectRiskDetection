import os
import asyncio
import json
from typing import List, Dict, Any

# Local summarizers (meeting-scoped). These mirror the behaviour in the
# project's `mcp/agents` but live inside `meeting_mcp` to avoid importing
# implementation from the global `mcp` package.
from meeting_mcp.agents.bart_summarizer import summarize_with_bart
from meeting_mcp.agents.mistral_summarizer import summarize_with_mistral
from meeting_mcp import config as mm_config


def get_bart_model():
    if not hasattr(get_bart_model, "tokenizer") or not hasattr(get_bart_model, "model"):
        # Resolve BART model path via centralized helper in meeting_mcp.config
        bart_drive_path = mm_config.get_bart_model_path()
        if bart_drive_path:
            model_path = bart_drive_path
        else:
            # Default local model folder (project relative)
            model_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "models", "bart_finetuned_meeting_summary"))

        print(f"Loading BART model from: {model_path}")
        # Only raise if we're using the default local model and it's missing
        if (not bart_drive_path) and (not os.path.exists(model_path)):
            raise FileNotFoundError(f"BART model path not found: {model_path}")

        from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
        get_bart_model.tokenizer = AutoTokenizer.from_pretrained(model_path)
        get_bart_model.model = AutoModelForSeq2SeqLM.from_pretrained(model_path)
    return get_bart_model.tokenizer, get_bart_model.model


def get_mistral_model():
    if os.environ.get("MISTRAL_ENABLED", "0") != "1":
        raise RuntimeError("Mistral support is disabled. Set MISTRAL_ENABLED=1 and provide model path to enable.")
    if not hasattr(get_mistral_model, "tokenizer") or not hasattr(get_mistral_model, "model"):
        model_path = mm_config.get_mistral_model_path() or os.environ.get("MISTRAL_MODEL_PATH") or "/content/mistral-7B-Instruct-v0.2"
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Mistral model path not found: {model_path}")
        from transformers import AutoTokenizer, AutoModelForCausalLM
        from transformers import BitsAndBytesConfig
        import torch
        if not torch.cuda.is_available():
            raise RuntimeError("No CUDA GPU detected. Mistral requires a GPU. Set MISTRAL_ENABLED=0 to disable.")
        get_mistral_model.tokenizer = AutoTokenizer.from_pretrained(model_path)
        try:
            get_mistral_model.model = AutoModelForCausalLM.from_pretrained(
                model_path,
                device_map="cuda",
                quantization_config=BitsAndBytesConfig(load_in_4bit=True)
            )
        except Exception:
            get_mistral_model.model = AutoModelForCausalLM.from_pretrained(model_path, device_map="cuda")
    return get_mistral_model.tokenizer, get_mistral_model.model


class SummarizationAgent:
    def __init__(self, mode: str = "auto"):
        self.mode = mode

    def summarize_protocol(self, processed_transcripts: List[str] = None, mode: str = None, **kwargs) -> Dict[str, Any]:
        processed_transcripts = processed_transcripts or []
        mode = (mode or self.mode) or "auto"
        if isinstance(mode, str):
            mode = mode.lower()

        full_transcript = "\n".join(processed_transcripts)
        summary = None
        action_items = []
        download_link = None

        if mode == "bart":
            try:
                tokenizer, model = get_bart_model()
                summary_obj = summarize_with_bart(tokenizer, model, full_transcript, "meeting")
                summary = summary_obj.get('summary_text', '')
                action_items = summary_obj.get('action_items', [])
                download_link = summary_obj.get('download_link', None)
            except Exception as e:
                summary = full_transcript[:300] + ("..." if len(full_transcript) > 300 else f" [BART error: {e}]")
        elif mode == "mistral":
            try:
                mistral_tokenizer, mistral_model = get_mistral_model()
                summary_obj = summarize_with_mistral(mistral_tokenizer, mistral_model, full_transcript, "meeting")
                summary = summary_obj.get('summary_text', '')
                action_items = summary_obj.get('action_items', [])
                download_link = summary_obj.get('download_link', None)
            except Exception as e:
                # fallback to bart if mistral fails
                try:
                    tokenizer, model = get_bart_model()
                    summary_obj = summarize_with_bart(tokenizer, model, full_transcript, "meeting")
                    summary = summary_obj.get('summary_text', '')
                    action_items = summary_obj.get('action_items', [])
                    download_link = summary_obj.get('download_link', None)
                except Exception as e2:
                    summary = full_transcript[:300] + ("..." if len(full_transcript) > 300 else f" [Mistral/BART error: {e}; {e2}]")
        else:
            # auto / fallback: try bart, then mistral
            try:
                tokenizer, model = get_bart_model()
                summary_obj = summarize_with_bart(tokenizer, model, full_transcript, "meeting")
                summary = summary_obj.get('summary_text', '')
                action_items = summary_obj.get('action_items', [])
                download_link = summary_obj.get('download_link', None)
            except Exception:
                try:
                    mistral_tokenizer, mistral_model = get_mistral_model()
                    summary_obj = summarize_with_mistral(mistral_tokenizer, mistral_model, full_transcript, "meeting")
                    summary = summary_obj.get('summary_text', '')
                    action_items = summary_obj.get('action_items', [])
                    download_link = summary_obj.get('download_link', None)
                except Exception:
                    summary = full_transcript[:300]

        result = {
            "summary": summary or "No summary generated.",
            "action_items": action_items,
            "download_link": download_link,
            "mode": mode,
            "transcript_length": len(full_transcript)
        }
        return result

    async def summarize(self, meeting_id: str, transcript: str) -> Dict[str, Any]:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.summarize_protocol, [transcript], self.mode)


__all__ = ["SummarizationAgent"]
