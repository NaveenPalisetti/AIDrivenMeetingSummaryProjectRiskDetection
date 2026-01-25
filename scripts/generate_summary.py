
import sys
from transformers import BartTokenizer, BartForConditionalGeneration
import torch
import re

MODEL_PATH = "models/local_bart_large_cnn_finetuned/checkpoint-30"  # Path to your fine-tuned model

def chunk_text(text, tokenizer, max_tokens=512):
    # Split by sentences, then group sentences until max_tokens is reached
    sentences = re.split(r'(?<=[.!?])\s+', text)
    chunks = []
    current_chunk = ""
    for sentence in sentences:
        test_chunk = current_chunk + " " + sentence if current_chunk else sentence
        num_tokens = len(tokenizer.tokenize(test_chunk))
        if num_tokens > max_tokens:
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = sentence
        else:
            current_chunk = test_chunk
    if current_chunk:
        chunks.append(current_chunk.strip())
    return chunks

import json
def generate_summary_and_actions(transcript, model_path=MODEL_PATH, max_length=512):
    import json
    tokenizer = BartTokenizer.from_pretrained(model_path)
    model = BartForConditionalGeneration.from_pretrained(model_path)
    chunks = chunk_text(transcript, tokenizer, max_tokens=512)
    all_summary_points = []
    all_action_items = []
    debug_chunks = []
    for idx, chunk in enumerate(chunks):
        prompt = (
            "Read the following meeting transcript and return a JSON object with two keys: "
            "'summary_points' (a list of concise summary bullet points) and 'action_items' (a list of clear, actionable items with assignees if possible).\n"
            "Transcript:\n" + chunk
        )
        inputs = tokenizer([prompt], max_length=1024, truncation=True, return_tensors="pt")
        with torch.no_grad():
            summary_ids = model.generate(
                inputs["input_ids"],
                num_beams=4,
                length_penalty=2.0,
                max_length=max_length,
                min_length=30,
                no_repeat_ngram_size=3,
                early_stopping=True
            )
        output = tokenizer.decode(summary_ids[0], skip_special_tokens=True)
        print(f"\n=== Chunk {idx+1} Output ===\n{output}\n")
        debug_chunks.append(output)
        # Try to parse JSON from model output
        try:
            result = json.loads(output)
        except Exception:
            try:
                json_str = output[output.index('{'):output.rindex('}')+1]
                result = json.loads(json_str)
            except Exception:
                result = {"summary_points": [output], "action_items": []}

        # Only keep string items, not dicts/lists as strings
        def clean_items(items):
            clean = []
            for item in items:
                if isinstance(item, str):
                    # Filter out stringified dicts/lists
                    if not (item.strip().startswith("{") or item.strip().startswith("[")):
                        clean.append(item.strip())
                elif isinstance(item, list):
                    clean.extend(clean_items(item))
                elif isinstance(item, dict):
                    # If dict, try to extract summary_points/action_items recursively
                    clean.extend(clean_items(item.get("summary_points", [])))
                    clean.extend(clean_items(item.get("action_items", [])))
            return clean

        all_summary_points.extend(clean_items(result.get("summary_points", [])))
        all_action_items.extend(clean_items(result.get("action_items", [])))

    return {"summary_points": all_summary_points, "action_items": all_action_items, "debug_chunks": debug_chunks}

# Simple rule-based extraction: sentences starting with verbs or containing 'should', 'must', 'to', etc.
def extract_action_items(text):
    sentences = re.split(r'(?<=[.!?])\s+', text)
    action_items = []
    for s in sentences:
        s_strip = s.strip()
        if not s_strip:
            continue
        # Heuristic: contains 'should', 'must', 'to', or starts with a verb (capitalized word)
        if re.match(r'^[A-Z][a-z]+ ', s_strip) or any(word in s_strip.lower() for word in ['should', 'must', 'to ', 'action item', 'follow up']):
            action_items.append(s_strip)
    return action_items

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python generate_summary.py <transcript_file> [output_file]")
        sys.exit(1)
    transcript_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else "summary_output.json"
    with open(transcript_file, 'r', encoding='utf-8') as f:
        transcript = f.read()
    result = generate_summary_and_actions(transcript)
    # Print to console as before
    print("\n=== Aggregated Meeting Summary ===\n")
    for point in result.get("summary_points", []):
        print(f"- {point}")
    print("\n=== Aggregated Action Items ===\n")
    for item in result.get("action_items", []):
        print(f"- {item}")
    # Save full output (including debug info) to file
    try:
        with open(output_file, 'w', encoding='utf-8') as out_f:
            json.dump(result, out_f, ensure_ascii=False, indent=2)
        print(f"\nFull output (including debug info) saved to: {output_file}")
    except Exception as e:
        print(f"Error saving output to file: {e}")
