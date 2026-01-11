"""
Streamlit Orchestrator Client: A standalone Streamlit app that sends user queries to the orchestrator API endpoint and displays results.
"""


import streamlit as st
import requests
from mcp.ui.orchestrator_ui_components import (
    event_selector, display_event_details, display_processed_transcripts, display_summaries, display_errors
)

API_URL = "http://localhost:8000/mcp/orchestrate"  # Adjust if your FastAPI server runs elsewhere

st.set_page_config(page_title="AI Orchestrator Client", layout="wide")
st.title("🤖 AI Orchestrator Client")
st.caption("This app sends queries to the orchestrator API and displays the workflow results.")

# Sidebar: All options
with st.sidebar:
    st.header("Options")
    user = st.text_input("User", value="alice")
    date = st.text_input("Date (YYYY-MM-DD)", value="2026-01-09")
    permissions = st.text_input("Permissions (comma-separated)", value="summary,jira")
    mode = st.selectbox("Summarization Mode", ["bart", "mistral"], index=0)
    create_jira = st.checkbox("Approve and create Jira tasks after summarization", value=False)

# Main form for user query
with st.form("query_form"):
    query = st.text_input("Enter your request (e.g., 'Summarize and create jira')")
    submitted = st.form_submit_button("Fetch Events")

if submitted:
    payload = {
        "query": query,
        "user": user,
        "date": date if date else None,
        "permissions": [p.strip() for p in permissions.split(",") if p.strip()],
        "mode": mode,
        "create_jira": create_jira
    }
    with st.spinner("Fetching events and running workflow..."):
        try:
            response = requests.post(API_URL, json=payload)
            if response.status_code == 200:
                result = response.json()
                st.session_state['last_result'] = result
                st.success("Events fetched and workflow completed.")
            else:
                st.error(f"API Error: {response.status_code} {response.text}")
        except Exception as e:
            st.error(f"Request failed: {e}")

result = st.session_state.get('last_result', None)
if result:
    with st.expander("Event & Transcript Overview", expanded=True):
        st.metric("Event Count", result.get("event_count", 0))
        st.metric("Transcript Count", result.get("transcript_count", 0))
        events = result.get("calendar_events", [])
        transcripts = result.get("calendar_transcripts", [])
        selected_indices = event_selector(events, transcripts)

    with st.form("process_form"):
        process_submitted = st.form_submit_button("Process Selected Events")
    if process_submitted:
        payload = {
            "query": query,
            "user": user,
            "date": date if date else None,
            "permissions": [p.strip() for p in permissions.split(",") if p.strip()],
            "selected_event_indices": selected_indices,
            "mode": mode,
            "create_jira": create_jira
        }
        with st.spinner("Processing selected events..."):
            try:
                response = requests.post(API_URL, json=payload)
                if response.status_code == 200:
                    result = response.json()
                    st.session_state['last_result'] = result
                    st.success("Selected events processed.")
                else:
                    st.error(f"API Error: {response.status_code} {response.text}")
            except Exception as e:
                st.error(f"Request failed: {e}")

    # Results display
    with st.expander("Selected Event Details"):
        display_event_details(events, transcripts, selected_indices)
    with st.expander("Processed Transcripts"):
        processed = result.get("processed_transcripts", [])
        display_processed_transcripts(processed)
    with st.expander("Summaries"):
        summaries = result.get("summaries", [])
        if isinstance(summaries, str):
            display_summaries([summaries])
        else:
            display_summaries(summaries)
    with st.expander("Agent States & Outputs"):
        # Preprocessing
        if 'preproc_task_state' in result:
            st.info(f"Preprocessing Task State: {result['preproc_task_state']}")
        if 'preproc_response' in result:
            st.json(result['preproc_response'])
        # Summarization
        if 'summ_task_state' in result:
            st.info(f"Summarization Task State: {result['summ_task_state']}")
        if 'summ_response' in result:
            st.json(result['summ_response'])
        # Jira
        if result.get('jira'):
            st.info("Jira Task State:")
            if 'jira_task_state' in result:
                st.write(result['jira_task_state'])
            st.json(result['jira'])
        # Risk
        if result.get('risk'):
            st.info("Risk Detection Task State:")
            if 'risk_task_state' in result:
                st.write(result['risk_task_state'])
            st.json(result['risk'])
    with st.expander("Errors & Debug Info"):
        display_errors(result)
