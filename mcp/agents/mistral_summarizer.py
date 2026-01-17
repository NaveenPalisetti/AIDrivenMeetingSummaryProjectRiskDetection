import re
import json
import torch

def summarize_with_mistral(mistral_tokenizer, mistral_model, transcript, meeting_id):
    # Accept either a string (single transcript) or a list (pre-chunked)
    if isinstance(transcript, list):
        transcript_chunks = [t for t in transcript if t and len(t.split()) >= 10]
        if not transcript_chunks:
            # print("[Mistral] No valid transcript chunks for summarization.")
            return {
                'meeting_id': meeting_id,
                'summary_text': "Transcript too short for summarization.",
                'action_items': []
            }
        # print(f"[Mistral] Received {len(transcript_chunks)} pre-chunked transcript(s).")
    else:
        if not transcript or len(transcript.split()) < 10:
            # print("[Mistral] Transcript too short for summarization.")
            return {
                'meeting_id': meeting_id,
                'summary_text': "Transcript too short for summarization.",
                'action_items': []
            }
        # --- Chunking logic ---
        def chunk_text(text, max_words=900):
            words = text.split()
            chunks = []
            for i in range(0, len(words), max_words):
                chunk = ' '.join(words[i:i+max_words])
                chunks.append(chunk)
            return chunks
        transcript_chunks = chunk_text(transcript, max_words=900)
        # print(f"[Mistral] Transcript split into {len(transcript_chunks)} chunk(s).")

    all_summaries = []
    all_action_items = []

    for idx, chunk in enumerate(transcript_chunks):
        mistral_prompt = (
            "You are an AI specialized in analyzing meeting transcripts.\n"
            "Your task is to produce:\n"
            "1. A clear and concise SUMMARY of the meeting as a numbered or bulleted list (do not use 'point 1', 'point 2', use real content).\n"
            "2. A list of ACTION ITEMS with owners and deadlines if mentioned.\n"
            "3. A list of DECISIONS made during the meeting.\n"
            "4. A list of RISKS, blockers, or concerns raised.\n"
            "5. A list of FOLLOW-UP QUESTIONS that attendees should clarify.\n"
            "\n"
            "INSTRUCTIONS:\n"
            "- Read the provided meeting transcript thoroughly.\n"
            "- Do NOT invent information. Only extract what is explicitly or implicitly present.\n"
            "- If some sections have no information, return an empty list.\n"
            "- Keep summary short but complete (5–8 bullet points or numbers).\n"
            "- Use simple, business-friendly language.\n"
            "- DO NOT use placeholder text like 'point 1', 'point 2', '<summary bullet 1>', '<task>', etc.\n"
            "- DO NOT copy the example below. Fill with real meeting content.\n"
            "\n"
            "RETURN THE OUTPUT IN THIS EXACT JSON FORMAT (as a code block):\n"
            "```json\n"
            "{\n"
            "  \"summary\": [\"<summary bullet 1>\", \"<summary bullet 2>\"],\n"
            "  \"action_items\": [ {\"task\": \"<task>\", \"owner\": \"<owner>\", \"deadline\": \"<deadline>\"} ]\n"
            "}\n"
            "```\n"
            "\n"
            "TRANSCRIPT:\n"
            f"{chunk}\n"
        )
        # print(f"[Mistral][Chunk {idx+1}] Prompt sent to model (first 500 chars):\n", mistral_prompt[:500], "..." if len(mistral_prompt) > 500 else "")
        device = next(mistral_model.parameters()).device
        encoded = mistral_tokenizer.encode_plus(
            mistral_prompt,
            truncation=True,
            max_length=4096,
            return_tensors="pt"
        )
        input_ids = encoded["input_ids"].to(device)
        attention_mask = encoded["attention_mask"].to(device)
        summary_ids = mistral_model.generate(
            input_ids,
            attention_mask=attention_mask,
            max_new_tokens=512,
            do_sample=False,
            num_beams=4,
            early_stopping=True,
            pad_token_id=mistral_tokenizer.eos_token_id
        )
        mistral_output = mistral_tokenizer.decode(summary_ids[0], skip_special_tokens=True)
        # print(f"[Mistral][Chunk {idx+1}] Raw model output (first 500 chars):\n", mistral_output[:500], "..." if len(mistral_output) > 500 else "")
        # print(f"[Mistral][Chunk {idx+1}] Full decoded output:\n", mistral_output)

        def extract_last_json(text):
            # Find all top-level JSON objects and return the last one
            starts = []
            ends = []
            brace_count = 0
            start = None
            for i, c in enumerate(text):
                if c == '{':
                    if brace_count == 0:
                        start = i
                    brace_count += 1
                elif c == '}':
                    brace_count -= 1
                    if brace_count == 0 and start is not None:
                        starts.append(start)
                        ends.append(i+1)
                        start = None
            if starts and ends:
                # Return the last JSON block
                return text[starts[-1]:ends[-1]]
            return None

        json_str = extract_last_json(mistral_output)
        if json_str:
            # print(f"[Mistral][Chunk {idx+1}] JSON block found in output.")
            try:
                parsed = json.loads(json_str)
                summary_text = parsed.get('summary', [])
                action_items = parsed.get('action_items', [])
                # print(f"[Mistral][Chunk {idx+1}] Parsed summary: {summary_text}")
                # print(f"[Mistral][Chunk {idx+1}] Parsed action_items: {action_items}")
            except Exception as e:
                # print(f"[Mistral][Chunk {idx+1}] JSON parsing error: {e}")
                summary_text = []
                action_items = []
        else:
            # print(f"[Mistral][Chunk {idx+1}] No JSON block found in output.")
            summary_text = []
            action_items = []
            lines = mistral_output.splitlines()
            summary_started = False
            for line in lines:
                l = line.strip()
                if l.startswith('-') or l.startswith('1.') or l.startswith('•'):
                    summary_started = True
                if summary_started and l:
                    summary_text.append(l)
            if not summary_text:
                summary_text = [mistral_output.strip()]
        # Clean up and filter out empty/placeholder/point items
        def is_valid_summary_item(item):
            if not item or not isinstance(item, str):
                return False
            s = item.strip().lower()
            if s in ("point 1", "point 2", "point1", "point2", "", "-", "<summary bullet 1>", "<summary bullet 2>"):
                return False
            if s.startswith("point ") or s.startswith("<summary"):
                return False
            if '<' in s and '>' in s:
                return False
            return True
        def is_valid_action_item(item):
            if not item:
                return False
            if isinstance(item, dict):
                # Remove if any value is a placeholder like <task> or empty
                for v in item.values():
                    if isinstance(v, str) and (v.strip() == '' or v.strip().startswith('<')):
                        return False
                return any(v for v in item.values())
            if isinstance(item, str):
                s = item.strip()
                if s == '' or s.startswith('<'):
                    return False
                return True
            return False
        filtered_summaries = [s for s in (summary_text if isinstance(summary_text, list) else [summary_text]) if is_valid_summary_item(s)]
        filtered_action_items = [a for a in (action_items if isinstance(action_items, list) else [action_items]) if is_valid_action_item(a)]
        # print(f"[Mistral][Chunk {idx+1}] Filtered summary: {filtered_summaries}")
        # print(f"[Mistral][Chunk {idx+1}] Filtered action_items: {filtered_action_items}")
        all_summaries.extend(filtered_summaries)
        all_action_items.extend(filtered_action_items)
        # print(f"[Mistral][Chunk {idx+1}] all_summaries so far: {all_summaries}")
        # print(f"[Mistral][Chunk {idx+1}] all_action_items so far: {all_action_items}")

    # print(f"[Mistral] FINAL all_summaries: {all_summaries}")
    # print(f"[Mistral] FINAL all_action_items: {all_action_items}")
    return {
        'meeting_id': meeting_id,
        'summary_text': all_summaries,
        'action_items': all_action_items
    }
