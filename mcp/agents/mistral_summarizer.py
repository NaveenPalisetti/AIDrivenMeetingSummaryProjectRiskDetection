import re
import json
import torch

def summarize_with_mistral(mistral_tokenizer, mistral_model, transcript, meeting_id):
    print("[Mistral] summarize_with_mistral called. Meeting ID:", meeting_id)
    # Accept either a string (single transcript) or a list (pre-chunked)
    if isinstance(transcript, list):
        transcript_chunks = [t for t in transcript if t and isinstance(t, str) and len(t.split()) >= 10]
        print(f"[Mistral] Received transcript as list. {len(transcript_chunks)} valid chunks.")
        if not transcript_chunks:
            print("[Mistral] No valid transcript chunks for summarization.")
            return {
                'meeting_id': meeting_id,
                'summary_text': "Transcript too short for summarization.",
                'action_items': []
            }
    else:
        if not transcript or not isinstance(transcript, str) or len(transcript.split()) < 10:
            print("[Mistral] Transcript too short for summarization.")
            return {
                'meeting_id': meeting_id,
                'summary_text': "Transcript too short for summarization.",
                'action_items': []
            }
        def chunk_text(text, max_words=900):
            words = text.split()
            chunks = []
            for i in range(0, len(words), max_words):
                chunk = ' '.join(words[i:i+max_words])
                chunks.append(chunk)
            return chunks
        transcript_chunks = chunk_text(transcript, max_words=900)
        print(f"[Mistral] Transcript split into {len(transcript_chunks)} chunk(s).")

    all_summaries = []
    all_action_items = []

    for idx, chunk in enumerate(transcript_chunks):
        print(f"[Mistral][Chunk {idx+1}] Processing chunk of length {len(chunk.split())} words.")
        mistral_prompt = (
            "Role: You are a Senior Technical Analyst. Your goal is to synthesize meeting transcripts into a structured JSON schema for a project management dashboard.\n"
            "\n"
            "Task: Analyze the provided meeting transcript and extract the following fields into a valid JSON object:\n"
            "Metadata: Meeting ID, Project Name, Topic, and Sprint Number.\n"
            "Agenda: A bulleted list of the technical goals discussed.\n"
            "Participants: A list of the attendees and their roles.\n"
            "Summary Points: High-level takeaways focusing on technical decisions (MQL logic, JPO refactors, UI state).\n"
            "Risk Factors: Potential technical or process bottlenecks identified during the conversation.\n"
            "Action Items: A detailed array of objects. Use issue_type: 'Story' for major feature creation and 'Task' or 'Bug' for technical sub-work. Include: summary, assignee, and a logical due_date.\n"
            "\n"
            "Constraints:\n"
            "- The JSON must be strictly formatted for machine readability.\n"
            "- Technical terminology (JPO, MQL, REST, Triggers) must be preserved.\n"
            "- Ensure 'Story' actions are created at the start of new phases.\n"
            "\n"
            "RETURN THE OUTPUT IN THIS EXACT JSON FORMAT (as a code block):\n"
            "```json\n"
            "{\n"
            "  \"metadata\": {\"meeting_id\": \"\", \"project\": \"\", \"topic\": \"\", \"sprint\": \"\"},\n"
            "  \"agenda\": [\"<goal 1>\", \"<goal 2>\", ...],\n"
            "  \"participants\": [{\"name\": \"\", \"role\": \"\"}, ...],\n"
            "  \"summary_points\": [\"<point 1>\", ...],\n"
            "  \"risk_factors\": [\"<risk 1>\", ...],\n"
            "  \"action_items\": [\n"
            "    {\"summary\": \"\", \"assignee\": \"\", \"issue_type\": \"\", \"due_date\": \"\"}\n"
            "  ]\n"
            "}\n"
            "```\n"
            "\n"
            "TRANSCRIPT:\n"
            f"{chunk}\n"
        )
        # print(f"[Mistral][Chunk {idx+1}] Prompt sent to model (first 500 chars):\n", mistral_prompt[:500], "..." if len(mistral_prompt) > 500 else "")
        device = next(mistral_model.parameters()).device
        print(f"[Mistral][Chunk {idx+1}] Using device: {device}")
        encoded = mistral_tokenizer.encode_plus(
            mistral_prompt,
            truncation=True,
            max_length=4096,
            return_tensors="pt"
        )
        input_ids = encoded["input_ids"].to(device)
        attention_mask = encoded["attention_mask"].to(device)
        print(f"[Mistral][Chunk {idx+1}] Input IDs shape: {input_ids.shape}")
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
        print(f"[Mistral][Chunk {idx+1}] Model output (first 500 chars):\n{mistral_output[:500]}{'...' if len(mistral_output) > 500 else ''}")

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
            print(f"[Mistral][Chunk {idx+1}] JSON block found in output.")
            try:
                parsed = json.loads(json_str)
                summary_text = parsed.get('summary', [])
                action_items = parsed.get('action_items', [])
                print(f"[Mistral][Chunk {idx+1}] Parsed summary: {summary_text}")
                print(f"[Mistral][Chunk {idx+1}] Parsed action_items: {action_items}")
            except Exception as e:
                print(f"[Mistral][Chunk {idx+1}] JSON parsing error: {e}")
                summary_text = []
                action_items = []
        else:
            print(f"[Mistral][Chunk {idx+1}] No JSON block found in output.")
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
        print(f"[Mistral][Chunk {idx+1}] Filtered summary: {filtered_summaries}")
        print(f"[Mistral][Chunk {idx+1}] Filtered action_items: {filtered_action_items}")
        all_summaries.extend(filtered_summaries)
        all_action_items.extend(filtered_action_items)
        print(f"[Mistral][Chunk {idx+1}] all_summaries so far: {all_summaries}")
        print(f"[Mistral][Chunk {idx+1}] all_action_items so far: {all_action_items}")

    # print(f"[Mistral] FINAL all_summaries: {all_summaries}")
    # print(f"[Mistral] FINAL all_action_items: {all_action_items}")
    # Deduplicate summaries and action items
    def dedup_list(items):
        seen = set()
        deduped = []
        for item in items:
            key = json.dumps(item, sort_keys=True) if isinstance(item, dict) else str(item).strip().lower()
            if key not in seen:
                seen.add(key)
                deduped.append(item)
        return deduped

    deduped_summaries = dedup_list(all_summaries)
    deduped_action_items = dedup_list(all_action_items)
    print(f"[Mistral] FINAL deduped_summaries: {deduped_summaries}")
    print(f"[Mistral] FINAL deduped_action_items: {deduped_action_items}")
    return {
        'meeting_id': meeting_id,
        'summary_text': deduped_summaries,
        'action_items': deduped_action_items
    }
