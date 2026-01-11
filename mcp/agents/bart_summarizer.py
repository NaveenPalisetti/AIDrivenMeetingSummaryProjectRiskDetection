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
    # Improved rule-based extraction for action items
    lines = [l.strip() for l in transcript.replace('\n', '. ').split('.') if l.strip()]
    action_keywords = ['fix', 'complete', 'implement', 'create', 'update', 'assign', 'test', 'review', 'prepare', 'set up', 'ensure']
    action_items = [l for l in lines if any(k in l.lower() for k in action_keywords)]
    return {
        'meeting_id': meeting_id,
        'summary_text': bart_summary,
        'action_items': action_items
    }
