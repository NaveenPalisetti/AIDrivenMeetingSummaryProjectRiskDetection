from meeting_mcp.tools.nlp_task_extraction import extract_tasks_structured


def summarize_with_bart(tokenizer, model, transcript, meeting_id):
    if not transcript or len(transcript.split()) < 10:
        bart_summary = "Transcript too short for summarization."
    else:
        try:
            input_ids = tokenizer.encode(transcript, truncation=True, max_length=1024, return_tensors="pt")
            summary_ids = model.generate(
                input_ids,
                max_length=130,
                min_length=30,
                do_sample=False,
                num_beams=4,
                early_stopping=True
            )
            bart_summary = tokenizer.decode(summary_ids[0], skip_special_tokens=True)
        except Exception as e:
            bart_summary = f"[BART summarization error: {e}]"
    try:
        raw_items = extract_tasks_structured(transcript, max_tasks=10)
        action_items = []
        for item in raw_items:
            action_items.append({
                "summary": item.get("title", ""),
                "assignee": item.get("owner", None),
                "issue_type": "Task",
                "story_points": None,
                "due_date": item.get("due", None)
            })
    except Exception:
        action_items = []
    return {
        'meeting_id': meeting_id,
        'summary_text': bart_summary,
        'action_items': action_items
    }
