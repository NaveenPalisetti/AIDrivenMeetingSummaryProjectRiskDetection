import os
import asyncio  # Used in async summarize
import json
import uuid

with open('mcp/config/credentials.json') as f:
    creds = json.load(f)
os.environ["OPENAI_API_KEY"] = creds.get("openai_api_key", "")

from mcp.core.context_handler import ContextHandler
from mcp.core.a2a_base_agent import A2AAgent, AgentCard, AgentCapability, A2AMessage, MessagePart, A2ATask, TaskState
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM, AutoModelForCausalLM
from transformers import BitsAndBytesConfig
from mcp.agents.mistral_summarizer import summarize_with_mistral
from mcp.agents.bart_summarizer import summarize_with_bart




try:
    import openai
    from openai import OpenAI
except Exception:
    openai = None


def get_bart_model():
    print("[DEBUG] Entering get_bart_model()")
    if not hasattr(get_bart_model, "tokenizer") or not hasattr(get_bart_model, "model"):
        bart_drive_path = os.environ.get("BART_MODEL_PATH")
        print(f"[DEBUG] BART_MODEL_PATH env: {bart_drive_path}")
        if bart_drive_path and os.path.exists(bart_drive_path):
            model_path = bart_drive_path
        else:
            model_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "models", "bart_finetuned_meeting_summary"))
        print(f"[DEBUG] BART model_path resolved: {model_path}")
        if not os.path.exists(model_path):
            print(f"[ERROR] BART model path does not exist: {model_path}")
            raise FileNotFoundError(f"BART model path not found: {model_path}")
        try:
            get_bart_model.tokenizer = AutoTokenizer.from_pretrained(model_path)
            get_bart_model.model = AutoModelForSeq2SeqLM.from_pretrained(model_path)
            print(f"[DEBUG] BART model and tokenizer loaded from {model_path}")
        except Exception as e:
            print(f"[ERROR] Exception loading BART model: {e}")
            raise
    else:
        print("[DEBUG] BART model/tokenizer already loaded (cached)")
    return get_bart_model.tokenizer, get_bart_model.model

def get_mistral_model():
    if not hasattr(get_mistral_model, "tokenizer") or not hasattr(get_mistral_model, "model"):
        # Check for Google Drive path via env var, else fallback to local
        mistral_drive_path = os.environ.get("MISTRAL_MODEL_PATH")
        if mistral_drive_path and os.path.exists(mistral_drive_path):
            model_path = mistral_drive_path
        else:
            # Hardcoded path for user's actual Mistral model location
            model_path = r"H:\Learning\BITS\Dissertation\Project\Week6\AIDrivenMeetingSummarizationTest\models\mistral-7B-Instruct-v0.2"
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Mistral model path not found: {model_path}")
        get_mistral_model.tokenizer = AutoTokenizer.from_pretrained(model_path)
        try:
            print(f"[INFO] Attempting to load Mistral from {model_path} in 4-bit quantized mode (bitsandbytes)...")
            get_mistral_model.model = AutoModelForCausalLM.from_pretrained(
                model_path,
                device_map="auto",
                quantization_config=BitsAndBytesConfig(load_in_4bit=True)
            )
            print("[INFO] Loaded Mistral in 4-bit quantized mode.")
        except Exception as e:
            print(f"[WARN] 4-bit quantization failed or bitsandbytes not available: {e}\nFalling back to normal model load.")
            get_mistral_model.model = AutoModelForCausalLM.from_pretrained(model_path)
    return get_mistral_model.tokenizer, get_mistral_model.model


class SummarizationAgent(A2AAgent):
    def __init__(self, mode="auto"):
        agent_card = AgentCard(
            agent_id="summarization-agent",
            name="Meeting Summarization Agent",
            description="Summarizes meeting transcripts using LLM, BART, or Mistral.",
            version="1.0.0",
            capabilities=[
                AgentCapability(
                    name="summarize_protocol",
                    description="Summarize all transcript chunks as a single transcript.",
                    parameters={"processed_transcripts": "list", "mode": "str"}
                )
            ]
        )
        super().__init__(agent_card)
        self.context = ContextHandler()
        self.mode = mode

    def summarize_protocol(self, processed_transcripts=None, mode=None, **kwargs):
        """
        Protocol-driven: summarize all transcript chunks as a single transcript (sync, for orchestrator)
        mode: 'bart' or 'mistral' (defaults to self.mode)
        Returns: a single summary string
        """
        if processed_transcripts is None:
            processed_transcripts = kwargs.get("processed_transcripts", [])
        print(f"[DEBUG] summarize_protocol received mode arg: {mode}, self.mode: {self.mode}")
        mode = mode or self.mode
        print(f"[SummarizationAgent] summarize_protocol using mode: {mode}")
        print(f"[SummarizationAgent] Number of chunks: {len(processed_transcripts)}")
        full_transcript = "\n".join(processed_transcripts)
        print(f"[SummarizationAgent] Full transcript length: {len(full_transcript)}")
        summary = None
        if mode == "bart":
            print("[SummarizationAgent] Entering BART branch")
            try:
                tokenizer, model = get_bart_model()
                print(f"[DEBUG] BART model objects: tokenizer={tokenizer is not None}, model={model is not None}")
                summary_obj = summarize_with_bart(tokenizer, model, full_transcript, "meeting")
                summary = summary_obj.get('summary_text', '')
                print(f"[DEBUG] BART summary: {summary[:100]}")
            except Exception as e:
                print(f"[ERROR] BART Exception: {e}")
                summary = full_transcript[:100] + ("..." if len(full_transcript) > 100 else f" [BART error: {e}]")
        elif mode == "mistral":
            print("[SummarizationAgent] Entering Mistral branch")
            try:
                mistral_tokenizer, mistral_model = get_mistral_model()
                print("[SummarizationAgent] Mistral model loaded.")
                summary_obj = summarize_with_mistral(mistral_tokenizer, mistral_model, full_transcript, "meeting")
                summary = summary_obj.get('summary_text', '')
                print("[SummarizationAgent] Mistral summary received.")
            except Exception as e:
                print(f"[SummarizationAgent] Mistral Exception: {e}")
                summary = full_transcript[:100] + ("..." if len(full_transcript) > 100 else f" [Mistral error: {e}]")
        else:
            print(f"[SummarizationAgent] Unknown or fallback mode: {mode}")
            print("[SummarizationAgent] Entering fallback branch (no model available)")
            summary = full_transcript[:100] + ("..." if len(full_transcript) > 100 else "")
        print(f"[SummarizationAgent] Final summary length: {len(summary) if summary else 0}")
        
        # Compose A2AMessage response
        message = A2AMessage(message_id=str(uuid.uuid4()), role="agent")
        message.add_part("text/plain", f"Summary mode: {mode}")
        message.add_part("text/plain", f"Transcript length: {len(full_transcript)}")
        message.add_part("text/plain", summary or "No summary generated.")
        return message

    async def summarize(self, meeting_id: str, transcript: str) -> dict:
        api_key = os.environ.get('OPENAI_API_KEY')
        print(f"SummarizationAgent: Using mode={self.mode}")
        use_llm = (self.mode == "llm") or (self.mode == "auto" and api_key and openai)
        use_bart = (self.mode == "bart") or (self.mode == "auto" and not use_llm and self.mode != "mistral")
        use_mistral = (self.mode == "mistral") or (self.mode == "auto" and not use_llm and not use_bart)

        if use_llm:
            print("SummarizationAgent: Using LLM summarizer")
            prompt = (
                "You are an AI specialized in analyzing meeting transcripts.\n"
                "Your task is to produce:\n"
                "1. A clear and concise SUMMARY of the meeting.\n"
                "2. A list of ACTION ITEMS with owners and deadlines if mentioned.\n"
                "3. A list of DECISIONS made during the meeting.\n"
                "4. A list of RISKS, blockers, or concerns raised.\n"
                "5. A list of FOLLOW-UP QUESTIONS that attendees should clarify.\n"
                "\n"
                "INSTRUCTIONS:\n"
                "- Read the provided meeting transcript thoroughly.\n"
                "- Do NOT invent information. Only extract what is explicitly or implicitly present.\n"
                "- If some sections have no information, return an empty list.\n"
                "- Keep summary short but complete (5–8 bullet points).\n"
                "- Use simple, business-friendly language.\n"
                "\n"
                "RETURN THE OUTPUT IN THIS EXACT JSON FORMAT:\n"
                "{\n"
                "  \"summary\": [\"point 1\", \"point 2\"],\n"
                "  \"decisions\": [ {\"decision\": \"\", \"reason\": \"\", \"made_by\": \"\"} ],\n"
                "  \"action_items\": [ {\"task\": \"\", \"owner\": \"\", \"deadline\": \"\"} ],\n"
                "  \"risks\": [ {\"risk\": \"\", \"impact\": \"\", \"raised_by\": \"\"} ],\n"
                "  \"follow_up_questions\": [\"question 1\"]\n"
                "}\n"
                "\n"
                "TRANSCRIPT:\n"
                f"{transcript}\n"
            )
            print("[DEBUG][LLM] Prompt sent to LLM:\n", prompt[:1000], "..." if len(prompt) > 1000 else "")
            try:
                client = OpenAI(api_key=api_key)
                resp = client.chat.completions.create(
                    model='gpt-4o-mini',
                    messages=[{'role':'user','content':prompt}],
                    max_tokens=300,
                    temperature=0.2
                )
                text = resp.choices[0].message.content
                print("[DEBUG][LLM] Raw LLM response:\n", text)
                summary_obj = {'meeting_id': meeting_id, 'summary_text': text}
            except Exception as e:
                print(f"[DEBUG][LLM] Exception during LLM summarization: {e}")
                summary_obj = {'meeting_id': meeting_id, 'summary_text': transcript[:300], 'note': str(e)}

        elif use_bart:
            print("SummarizationAgent: Using BART summarizer")
            tokenizer, model = get_bart_model()
            summary_obj = summarize_with_bart(tokenizer, model, transcript, meeting_id)

        elif use_mistral:
            print("SummarizationAgent: Using local Mistral summarizer")
            print("[INFO] Loading Mistral model, this may take a few moments...")
            mistral_tokenizer, mistral_model = get_mistral_model()
            print("[INFO] Mistral model loaded!")
            summary_obj = summarize_with_mistral(mistral_tokenizer, mistral_model, transcript, meeting_id)

        else:
            print("SummarizationAgent: No valid summarization method available.")
            # Fallback: very basic extraction
            lines = [l.strip() for l in transcript.replace('\n', '. ').split('.') if l.strip()]
            action_keywords = ['fix', 'complete', 'implement', 'create', 'update', 'assign', 'test', 'review', 'prepare', 'set up', 'ensure']
            summary_text = lines[0] if lines else ''
            action_items = [l for l in lines if any(k in l.lower() for k in action_keywords)]
            summary_obj = {
                'meeting_id': meeting_id,
                'summary_text': summary_text,
                'action_items': action_items
            }

        self.context.save_summary(meeting_id, summary_obj)
        await asyncio.sleep(0)
        return summary_obj
