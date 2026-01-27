import json
import asyncio
import streamlit as st


_CSS = """
<style>
    .main-header { font-size: 2rem; font-weight:700; color: #1f77b4; }
    .sub-header { font-size: 1rem; color: #666; margin-bottom: 1rem; }
    .badge { display:inline-block; padding:0.2rem .6rem; border-radius:4px; background:#f0f0f0; margin-right:6px; }
    .credentials { background:#fff; padding:0.5rem; border-radius:6px; box-shadow: 0 1px 2px rgba(0,0,0,0.04); }
</style>
"""


def render_css():
    st.markdown(_CSS, unsafe_allow_html=True)


def render_chat_messages(messages):
    for message in messages:
        role = message.get("role", "system")
        with st.chat_message(role):
            st.markdown(message.get("content", ""))


def render_processed_chunks(processed, title, add_message, debug: dict | None = None):
    # Persist full processed chunks into chat history
    full_text = "\n\n".join([f"Chunk {i+1}:\n{chunk}" for i, chunk in enumerate(processed)])
    add_message("assistant", full_text)

    # Cache processed chunks for later summarization (keyed by title)
    try:
        if "processed_cache" not in st.session_state:
            st.session_state["processed_cache"] = {}
        st.session_state["processed_cache"][title] = processed
    except Exception:
        pass

    rows = []
    for i, chunk in enumerate(processed):
        preview = chunk if len(chunk) <= 200 else chunk[:200].rstrip() + '...'
        rows.append({"Chunk": i + 1, "Preview": preview})
    st.table(rows)
    for i, chunk in enumerate(processed):
        with st.expander(f"Chunk {i+1}"):
            try:
                safe_key = f"{safe_title}_chunk_{i+1}"
            except Exception:
                safe_key = f"chunk_{i+1}"
            # use a string label (empty string allowed) to avoid type errors
            st.text_area(label=f"Chunk {i+1}", value=chunk, height=300, key=safe_key)

    try:
        safe_title = title.replace(' ', '_').replace('/', '_')
    except Exception:
        safe_title = 'processed_transcript'
    joined = "\n\n".join(processed)
    st.download_button(f"Download processed transcript", data=joined, file_name=f"{safe_title}_processed.txt", mime="text/plain")

    # If debug info was provided, show it in an expander for quick inspection
    if debug:
        with st.expander("Preprocess debug", expanded=False):
            try:
                st.json(debug)
            except Exception:
                st.write(debug)


def render_summary_result(summary_obj, title, add_message):
    """Render a structured summary result (summary text/list and action items).
    Accepts either a string summary or a dict with keys `summary` and `action_items`.
    """
    # Persist the summary to chat history
    try:
        summary_text = ""
        action_items = []
        if isinstance(summary_obj, dict):
            summary_val = summary_obj.get('summary')
            if isinstance(summary_val, list):
                summary_text = "\n".join([f"- {s}" for s in summary_val])
            else:
                summary_text = str(summary_val or "")
            action_items = summary_obj.get('action_items') or []
        else:
            summary_text = str(summary_obj)
        if summary_text:
            add_message("assistant", f"Summary for {title}:\n\n{summary_text}")
    except Exception:
        pass

    st.header(f"Summary — {title}")
    if isinstance(summary_obj, dict) and summary_obj.get('summary'):
        s = summary_obj.get('summary')
        if isinstance(s, list):
            for item in s:
                st.markdown(f"- {item}")
        else:
            st.markdown(s)
    else:
        st.markdown(str(summary_obj))

    if isinstance(summary_obj, dict) and summary_obj.get('action_items'):
        st.subheader("Action Items")
        ais = summary_obj.get('action_items')
        for ai in ais:
            if isinstance(ai, dict):
                owner = ai.get('assignee') or ai.get('owner') or ai.get('assignee')
                summary_field = ai.get('summary') or ai.get('task') or ai.get('title') or str(ai)
                st.markdown(f"- **{summary_field}** — owner: {owner}")
            else:
                st.markdown(f"- {ai}")


def render_calendar_result(calendar_block, orchestrator, add_message):
    # If a previous action requested suppression (e.g. summarize/preprocess), skip rendering
    try:
        if st.session_state.pop('suppress_calendar_render', False):
            return
    except Exception:
        pass

    if calendar_block and calendar_block.get("status") == "success":
        events = calendar_block.get("events", [])
        st.session_state['last_events'] = events

        if not events:
            st.info("No calendar events found for the requested range.")
            return

        # Present events as a table and individual expanders
        rows = []
        for ev in events:
            rows.append({
                "Summary": ev.get("summary"),
                "Start": ev.get("start", {}).get("dateTime") or ev.get("start", {}).get("date"),
                "End": ev.get("end", {}).get("dateTime") or ev.get("end", {}).get("date"),
                "Location": ev.get("location"),
                "Organizer": ev.get("organizer", {}).get("email"),
            })
        st.table(rows)

        for ev in events:
            title = ev.get("summary") or ev.get("id")
            ev_key = ev.get("id") or title
            with st.expander(title, expanded=False):
                cols = st.columns([3, 1])
                with cols[0]:
                    st.markdown(f"**When:** {ev.get('start', {}).get('dateTime') or ev.get('start', {}).get('date')}{' → ' + (ev.get('end', {}).get('dateTime') or ev.get('end', {}).get('date')) if ev.get('end') else ''}")
                    if ev.get("location"):
                        st.markdown(f"**Location:** {ev.get('location')}")
                    if ev.get("description"):
                        st.markdown(f"**Description:**\n\n{ev.get('description')}")
                    if ev.get("htmlLink"):
                        st.markdown(f"[Open in Google Calendar]({ev.get('htmlLink')})")

                    preprocess_text = ev.get("description") or ev.get("summary") or ""
                    if preprocess_text:
                        btn_key = f"preprocess_{ev_key}"
                        if st.button("Preprocess this meeting", key=btn_key):
                            user_action = f"Preprocess meeting: {title}"
                            add_message("user", user_action)
                            with st.chat_message("user"):
                                st.markdown(user_action)

                            try:
                                params = {"transcripts": [preprocess_text], "chunk_size": 1500}
                                proc_result = asyncio.run(orchestrator.orchestrate(f"preprocess transcripts for {title}", params))
                                proc_summary = proc_result.get("results", {}).get("transcript") or proc_result.get("results")
                                if isinstance(proc_summary, dict) and proc_summary.get("status") == "success":
                                    processed = proc_summary.get("processed", []) if isinstance(proc_summary, dict) else None
                                    if isinstance(processed, list):
                                        assistant_md = f"Preprocessed {len(processed)} chunk(s) for {title}."
                                    else:
                                        assistant_md = "Preprocessing completed."
                                else:
                                    assistant_md = f"Preprocessing result: {proc_result}"

                                add_message("assistant", assistant_md)
                                with st.chat_message("assistant"):
                                    st.markdown(assistant_md)
                                    if isinstance(proc_summary, dict) and proc_summary.get("status") == "success":
                                            processed = proc_summary.get("processed")
                                            debug = proc_summary.get("debug") if isinstance(proc_summary, dict) else None
                                            if processed:
                                                # persist and render processed chunks
                                                render_processed_chunks(processed, title, add_message, debug)
                                                # suppress re-rendering of the calendar/result JSON on this run
                                                try:
                                                    st.session_state['suppress_calendar_render'] = True
                                                except Exception:
                                                    pass
                            except Exception as e:
                                add_message("system", f"Error: {e}")
                                with st.chat_message("assistant"):
                                    st.markdown(f"Error: {e}")
                    # Summarize button: uses cached processed chunks or runs preprocess then summarization
                    if preprocess_text:
                        sum_key = f"summarize_{ev_key}"
                        if st.button("Summarize this meeting", key=sum_key):
                            meeting_title = title
                            add_message("user", f"Summarize meeting: {meeting_title}")
                            with st.chat_message("user"):
                                st.markdown(f"Summarize meeting: {meeting_title}")

                            try:
                                # Try to reuse cached processed chunks
                                processed = None
                                try:
                                    processed = st.session_state.get('processed_cache', {}).get(meeting_title)
                                except Exception:
                                    processed = None

                                if not processed:
                                    # Trigger preprocessing first
                                    params = {"transcripts": [preprocess_text], "chunk_size": 1500}
                                    proc_result = asyncio.run(orchestrator.orchestrate(f"preprocess transcripts for {meeting_title}", params))
                                    proc_summary = proc_result.get("results", {}).get("transcript") or proc_result.get("results")
                                    if isinstance(proc_summary, dict) and proc_summary.get("status") == "success":
                                        processed = proc_summary.get("processed")
                                        try:
                                            if "processed_cache" not in st.session_state:
                                                st.session_state["processed_cache"] = {}
                                            st.session_state["processed_cache"][meeting_title] = processed
                                        except Exception:
                                            pass

                                # Call summarization tool via orchestrator
                                mode = st.session_state.get('summarizer_model', 'BART')
                                mode_param = 'bart' if mode.lower().startswith('b') else 'mistral'
                                params = {"processed_transcripts": processed or [], "mode": mode_param}
                                sum_result = asyncio.run(orchestrator.orchestrate(f"summarize meeting {meeting_title}", params))
                                sum_block = sum_result.get('results', {}).get('summarization') or sum_result.get('results')
                                if isinstance(sum_block, dict) and sum_block.get('status') == 'success':
                                    summary_obj = sum_block.get('summary')
                                else:
                                    summary_obj = sum_block

                                add_message("assistant", f"Summary for {meeting_title} ready.")
                                with st.chat_message("assistant"):
                                    try:
                                        render_summary_result(summary_obj, meeting_title, add_message)
                                    except Exception:
                                        st.write(summary_obj)
                                    try:
                                        st.session_state['suppress_calendar_render'] = True
                                    except Exception:
                                        pass
                            except Exception as e:
                                add_message("system", f"Error: {e}")
                                with st.chat_message("assistant"):
                                    st.markdown(f"Error: {e}")
                with cols[1]:
                    st.markdown("**Metadata**")
                    st.write({k: ev.get(k) for k in ("id", "status", "iCalUID") if ev.get(k)})

        # Keep the raw JSON available for debugging
        with st.expander("Raw calendar JSON", expanded=False):
            st.code(json.dumps(calendar_block, indent=2), language="json")
    else:
        # Fallback: show full result as formatted JSON
        st.markdown("Result:\n\n" + "```json\n" + json.dumps(calendar_block, indent=2) + "\n```")
