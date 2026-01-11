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
        for i, summary in enumerate(summaries, 1):
            st.markdown(f"**Summary {i}:**\n{summary}")

def display_errors(result):
    if result.get("calendar_error"):
        st.error(f"Calendar Error: {result['calendar_error']}")
    if result.get("preprocessing_error"):
        st.error(f"Preprocessing Error: {result['preprocessing_error']}")
    if result.get("summarization_error"):
        st.error(f"Summarization Error: {result['summarization_error']}")
