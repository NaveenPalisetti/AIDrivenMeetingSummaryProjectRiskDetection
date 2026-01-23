def display_risks(risks):
    """
    Display detected risks in a user-friendly way, with severity-based color coding.
    Accepts a list of risk dicts or a single dict.
    """
    import streamlit as st
    if not risks:
        st.info("No risks detected.")
        return
    if isinstance(risks, dict):
        risks = [risks]
    st.subheader("Detected Risks")
    for risk in risks:
        if isinstance(risk, dict):
            desc = risk.get('description', str(risk))
            sev = (risk.get('severity', '') or '').lower()
            mid = risk.get('meeting_id', None)
        else:
            desc = str(risk)
            sev = ''
            mid = None
        msg = f"**Severity:** {sev.capitalize()}\n**Description:** {desc}"
        if mid:
            msg += f"\n**Meeting ID:** {mid}"
        if sev == 'high':
            st.error(msg)
        elif sev == 'medium':
            st.warning(msg)
        else:
            st.info(msg)
"""
Reusable Streamlit UI components for the Orchestrator Client
"""
import streamlit as st

def event_selector(events, transcripts):
    event_titles = []
    for i, e in enumerate(events):
        title = e.get('summary') or e.get('title') or f"Event {i+1}"
        start = e.get('start', {}).get('dateTime', '') or e.get('start', {}).get('date', '')
        event_titles.append(f"{i+1}. {title} ({start})")
    selected = st.multiselect("Select events to process:", event_titles, default=event_titles[:1], key=f"event_selector_{id(events)}")
    selected_indices = [event_titles.index(s) for s in selected]
    return selected_indices

def display_event_details(events, transcripts, selected_indices):
    st.subheader("Selected Event Details")
    for idx in selected_indices:
        ev = events[idx]
        transcript = transcripts[idx] if idx < len(transcripts) else ""
        summary = ev.get('summary', ev.get('title', f'Event {idx+1}'))
        start = ev.get('start', {}).get('dateTime') or ev.get('start', {}).get('date', '')
        end = ev.get('end', {}).get('dateTime') or ev.get('end', {}).get('date', '')
        organizer = ev.get('organizer', {}).get('email') if isinstance(ev.get('organizer'), dict) else ev.get('organizer', '')
        attendees = ev.get('attendees', [])
        description = ev.get('description', '')

        st.markdown(f"**Event {idx+1}: {summary}**")
        cols = st.columns([2, 1])
        with cols[0]:
            st.markdown(f"**Summary:** {summary}")
            if start:
                st.markdown(f"**Start:** {start}")
            if end:
                st.markdown(f"**End:** {end}")
            if organizer:
                st.markdown(f"**Organizer:** {organizer}")
            if attendees:
                st.markdown("**Attendees:**")
                for a in attendees:
                    email = a.get('email', '')
                    name = a.get('displayName') if a.get('displayName') else email
                    role = ' (self)' if a.get('self') else ''
                    st.markdown(f"- {name} <{email}>{role}")
                if description:
                    st.markdown("**Description:**")
                    desc_snippet = description if len(description) <= 400 else description[:400] + '...'
                    st.write(desc_snippet)
                    if len(description) > 400:
                        with st.expander("Show full description"):
                            st.write(description)
        with cols[1]:
            st.markdown("**Transcript**")
            if transcript:
                # show a snippet and provide expander for full transcript to avoid UI clutter
                transcript_snippet = transcript if len(transcript) <= 1000 else transcript[:1000] + '...'
                st.write(transcript_snippet)
                try:
                    st.download_button(label="Download Transcript", data=transcript, file_name=f"transcript_event_{idx+1}.txt")
                except Exception:
                    pass
                if len(transcript) > 1000:
                    with st.expander("Show full transcript"):
                        st.write(transcript)
            else:
                st.info("No transcript available for this event.")
            with st.expander("Show raw event JSON"):
                st.json(ev)

def display_processed_transcripts(processed):
    if processed:
        st.subheader("Processed Transcripts:")
        for i, pt in enumerate(processed, 1):
            st.markdown(f"**Chunk {i}:**\n{pt}")

def display_summaries(summaries):
    if summaries:
        st.subheader("Summaries:")
        # Render summaries as cards in two columns
        cols = st.columns(2)
        for i, summary in enumerate(summaries, 1):
            col = cols[(i - 1) % 2]
            with col:
                st.markdown(f"**Summary {i}**")
                # If summary is a list, show bullets
                if isinstance(summary, list):
                    for s in summary:
                        st.markdown(f"- {s}")
                    summary_text = "\n".join(summary)
                else:
                    # Try to parse stringified lists
                    import ast
                    try:
                        parsed = ast.literal_eval(summary)
                        if isinstance(parsed, list):
                            for s in parsed:
                                st.markdown(f"- {s}")
                            summary_text = "\n".join(parsed)
                        else:
                            st.markdown(summary)
                            summary_text = str(summary)
                    except Exception:
                        st.markdown(summary)
                        summary_text = str(summary)

                # Download button for each summary
                try:
                    safe_name = f"summary_{i}.txt"
                    st.download_button(label="Download Summary", data=summary_text, file_name=safe_name)
                except Exception:
                    # Streamlit may not support download_button in some versions — ignore
                    pass
        st.markdown("&nbsp;")

def display_errors(result):
    if result.get("calendar_error"):
        st.error(f"Calendar Error: {result['calendar_error']}")
    if result.get("preprocessing_error"):
        st.error(f"Preprocessing Error: {result['preprocessing_error']}")
    if result.get("summarization_error"):
        st.error(f"Summarization Error: {result['summarization_error']}")

def display_action_items(action_items):
    if action_items:
        st.subheader("Action Items:")
        # If action_items is a list of dicts, show as table
        if isinstance(action_items, list) and all(isinstance(ai, dict) for ai in action_items):
            st.table(action_items)
            # Provide download of action items as CSV
            try:
                import io, csv
                buf = io.StringIO()
                keys = action_items[0].keys() if action_items else []
                writer = csv.DictWriter(buf, fieldnames=list(keys))
                writer.writeheader()
                for row in action_items:
                    writer.writerow(row)
                st.download_button("Download Action Items (CSV)", data=buf.getvalue(), file_name="action_items.csv")
            except Exception:
                pass
        # If action_items is a list of strings, show as bullets
        elif isinstance(action_items, list):
            for i, item in enumerate(action_items, 1):
                st.markdown(f"{i}. {item}")
            try:
                joined = "\n".join(action_items)
                st.download_button("Download Action Items (TXT)", data=joined, file_name="action_items.txt")
            except Exception:
                pass
        else:
            st.markdown(str(action_items))


def get_suggested_commands(chat_history, last_result=None):
    """Return a list of suggested command strings based on recent chat history and last_result.

    Heuristics:
    - If the last user message mentions fetching/calendar, suggest fetching and preprocessing.
    - If the last user message mentions summarize/summary, suggest summarize/extract tasks/detect risks.
    - If last_result contains processed transcripts but not summaries, always suggest 'summarize selected events'.
    - If last_result contains summaries, suggest extract tasks, create jira, detect risks.
    - Otherwise return a small set of sensible defaults.
    """
    suggestions = []
    last_user = None
    try:
        if chat_history:
            for msg in reversed(chat_history):
                if msg.get('role') == 'user':
                    last_user = msg.get('content', '')
                    break
    except Exception:
        last_user = None

    lu = (last_user or '').lower() if last_user else ''

    # Always suggest summarize if processed_transcripts exist but not summaries
    if last_result and isinstance(last_result, dict):
        has_processed = bool(last_result.get('processed_transcripts'))
        has_summaries = bool(last_result.get('summaries'))
        if has_processed and not has_summaries:
            suggestions.append('summarize selected events')
        if has_summaries:
            suggestions.append('extract tasks')
            suggestions.append('create jira from action items')
            suggestions.append('detect risks')

    # Heuristic based on last user message
    if 'fetch' in lu or 'calendar' in lu or 'event' in lu:
        if 'fetch recent' not in suggestions:
            suggestions.insert(0, 'fetch events')
        if 'process selected events' not in suggestions:
            suggestions.append('process selected events')
    if 'summarize' in lu or 'summary' in lu:
        if 'summarize selected events' not in suggestions:
            suggestions.insert(0, 'summarize selected events')
        if 'extract tasks' not in suggestions:
            suggestions.append('extract tasks')
        if 'detect risks' not in suggestions:
            suggestions.append('detect risks')

    # Defaults if nothing else
    if not suggestions:
        suggestions = [
            'fetch events',
            'summarize selected events',
            'detect risks',
            'extract tasks'
        ]

    # Deduplicate while preserving order
    seen = set()
    deduped = []
    for s in suggestions:
        if s not in seen:
            deduped.append(s)
            seen.add(s)
    return deduped
