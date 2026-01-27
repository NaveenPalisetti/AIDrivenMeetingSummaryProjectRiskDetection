
import os
import torch
import argparse
import pandas as pd
import re
import json
from transformers import BartTokenizer, BartForConditionalGeneration, T5Tokenizer, T5ForConditionalGeneration, PegasusTokenizer, PegasusForConditionalGeneration

# Argument parser for model selection
parser = argparse.ArgumentParser(description="Inference for summarization models (BART, T5, DistilBART, TinyBART, Pegasus)")

parser.add_argument('--model_type', type=str, default='bart', 
    choices=['bart', 't5', 'distilbart', 'tinybart', 'pegasus'], 
    help='Model type: bart, t5, distilbart, tinybart, or pegasus')
parser.add_argument('--model_name', type=str, default=None, help='Model directory or Hugging Face model name')
parser.add_argument('--input_csv', type=str, required=True, help='CSV file with transcripts')
parser.add_argument('--output_csv', type=str, default='predictions.csv', help='Output CSV for summaries')
args = parser.parse_args()

# Set model_dir based on model_name or default
if args.model_name:
    model_dir = args.model_name
else:
    # Default directories for each model type
    default_dirs = {
        'bart': './bart_finetuned_meeting_summary',
        'distilbart': './distilbart_finetuned_meeting_summary',
        'tinybart': './tinybart_finetuned_meeting_summary',
        't5': './t5_finetuned_meeting_summary',
        'pegasus': './pegasus_finetuned_meeting_summary',
    }
    model_dir = default_dirs.get(args.model_type, './bart_finetuned_meeting_summary')

print(f"Loading model and tokenizer from: {model_dir}")

# Model selection
if args.model_type in ['bart', 'distilbart', 'tinybart']:
    tokenizer = BartTokenizer.from_pretrained(model_dir)
    model = BartForConditionalGeneration.from_pretrained(model_dir)
elif args.model_type == 't5':
    tokenizer = T5Tokenizer.from_pretrained(model_dir)
    model = T5ForConditionalGeneration.from_pretrained(model_dir)

elif args.model_type == 'pegasus':
    tokenizer = PegasusTokenizer.from_pretrained(model_dir)
    model = PegasusForConditionalGeneration.from_pretrained(model_dir)
else:
    raise ValueError("Unsupported model_type. Use 'bart', 'distilbart', 'tinybart', 't5', or 'pegasus'.")

# Dynamically determine max_output_length based on expected JSON output length from training data
train_csv_guess = args.input_csv.replace('test', 'train').replace('val', 'train')
if os.path.exists(train_csv_guess):
    train_df = pd.read_csv(train_csv_guess)
    def compute_max_json_length(df, fields=["summary", "participants", "agenda", "action_items"]):
        max_len = 0
        for i, row in df.iterrows():
            try:
                target = json.dumps({
                    "summary": row.get("summary", ""),
                    "participants": json.loads(row.get("participants", "[]")),
                    "agenda": row.get("agenda", ""),
                    "action_items": json.loads(row.get("action_items", "[]")),
                }, ensure_ascii=False)
                max_len = max(max_len, len(target))
            except Exception as e:
                pass
        return max_len
    max_json_length = compute_max_json_length(train_df)
    max_output_length = int((max_json_length * 1.2) // 4) + 10
    print(f"[INFO] Computed max_output_length for JSON output: {max_output_length} tokens (max JSON chars: {max_json_length})")
else:
    max_output_length = 128
    print("[WARN] Could not find training CSV to estimate max_output_length. Using default 128.")

# Function to summarize a transcript with strict JSON prompt
def summarize(transcript, max_input_length=512, max_output_length=max_output_length):
    prompt = (
        "Given the following meeting transcript, generate a JSON object with the following fields: summary, participants, agenda, action_items. Output only valid JSON.\n"
        f"Transcript: {transcript}\nJSON:"
    )
    if args.model_type == 't5':
        prompt = "summarize: " + prompt
    inputs = tokenizer([prompt], max_length=max_input_length, truncation=True, return_tensors="pt")
    summary_ids = model.generate(
        inputs["input_ids"],
        num_beams=4,
        max_length=max_output_length,
        early_stopping=True,
        length_penalty=1.0,
        forced_bos_token_id=tokenizer.bos_token_id if hasattr(tokenizer, 'bos_token_id') and tokenizer.bos_token_id is not None else None
    )
    summary = tokenizer.decode(summary_ids[0], skip_special_tokens=True)
    # Try to extract valid JSON if possible
    match = re.search(r'\{.*\}', summary, re.DOTALL)
    if match:
        try:
            json.loads(match.group(0))
            return match.group(0)
        except Exception:
            pass
    return summary

if __name__ == "__main__":
    import pandas as pd
    # Load transcripts from CSV
    df = pd.read_csv(args.input_csv)
    if 'transcript' not in df.columns:
        raise ValueError("Input CSV must have a 'transcript' column.")

    # Parse generated output into separate columns, prefer JSON if available
    summaries = []
    participants = []
    agendas = []
    action_items = []
    full_outputs = []
    import json
    for idx, row in df.iterrows():
        transcript = str(row['transcript'])
        generated = summarize(transcript)
        full_outputs.append(generated)
        summary_val = ""
        participants_val = ""
        agenda_val = ""
        action_items_val = ""
        # Try JSON parse first
        try:
            parsed = json.loads(generated)
            summary_val = parsed.get("summary", "")
            participants_val = parsed.get("participants", "")
            agenda_val = parsed.get("agenda", "")
            action_items_val = parsed.get("action_items", "")
        except Exception:
            # Fallback to line-based parsing
            for line in generated.splitlines():
                if line.startswith("Summary:"):
                    summary_val = line.replace("Summary:", "").strip()
                elif line.startswith("Participants:"):
                    participants_val = line.replace("Participants:", "").strip()
                elif line.startswith("Agenda:"):
                    agenda_val = line.replace("Agenda:", "").strip()
                elif line.startswith("Action Items:"):
                    action_items_val = line.replace("Action Items:", "").strip()
        summaries.append(summary_val)
        participants.append(participants_val)
        agendas.append(agenda_val)
        action_items.append(action_items_val)

    df['generated_summary'] = summaries
    df['generated_participants'] = participants
    df['generated_agenda'] = agendas
    df['generated_action_items'] = action_items
    df['generated_full_output'] = full_outputs
    df.to_csv(args.output_csv, index=False)
    print(f"Saved {len(full_outputs)} structured outputs to {args.output_csv}")
