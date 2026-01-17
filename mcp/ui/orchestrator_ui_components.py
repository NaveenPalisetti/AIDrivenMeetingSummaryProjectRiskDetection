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
    st.subheader("Selected Event Details:")
    for idx in selected_indices:
        st.markdown(f"**Event {idx+1}:**")
        st.json(events[idx])
        st.markdown(f"**Transcript:**\n{transcripts[idx]}")

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
