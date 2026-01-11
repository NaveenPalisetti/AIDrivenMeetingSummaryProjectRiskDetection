
"""
Streamlit Orchestrator Client: A standalone Streamlit app that sends user queries to the orchestrator API endpoint and displays results.
"""

# Ensure project root is in sys.path for package imports (works in Colab, local, etc)
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

import streamlit as st
import requests
from mcp.ui.orchestrator_ui_components import (
    event_selector, display_event_details, display_processed_transcripts, display_summaries, display_errors
)

st.set_page_config(page_title="AI Orchestrator Client", layout="wide")

API_URL = "http://localhost:8000/mcp/orchestrate"  # Adjust if your FastAPI server runs elsewhere

st.title("🤖 AI Orchestrator Client")
st.caption("This app sends queries to the orchestrator API and displays the workflow results.")

# Sidebar: All options
with st.sidebar:
    st.header("Options")
    mode = st.selectbox("Summarization Mode", ["bart", "mistral"], index=0, key="sidebar_summarization_mode")

# --- Chat UI ---
WELCOME_MSG = (
    "Hello! 👋 I can help you with your meeting data.\n\n"
    "You can ask me to:\n"
    "- Fetch recent meeting events\n"
    "- Summarize selected meetings\n"
    "- Detect risks in meetings\n"
    "- Create Jira tasks from meeting summaries\n"
    "- Set permissions (e.g., summary, jira)\n"
    "- Approve Jira creation\n\n"
    "Just type your request below to get started!"
)

if "chat_history" not in st.session_state:
    st.session_state["chat_history"] = []
if not st.session_state["chat_history"] or st.session_state["chat_history"][0]["content"] != WELCOME_MSG:
    st.session_state["chat_history"].insert(0, {"role": "orchestrator", "content": WELCOME_MSG})

# Display chat history
import json
def render_orchestrator_message(content):
    try:
        if isinstance(content, dict):
            result = content
        else:
            result = json.loads(content.replace("'", '"')) if content.strip().startswith('{') else None
        if result and isinstance(result, dict) and result.get('stage') == 'fetch' and 'calendar_events' in result:
            st.markdown("**Orchestrator:** Here are your recent meeting events:")
            events = result['calendar_events']
            if events:
                event_rows = []
                for ev in events:
                    event_rows.append({
                        'Summary': ev.get('summary', ''),
                        'Date': ev.get('created', '')[:10],
                        'Description': ev.get('description', '')[:100] + ('...' if len(ev.get('description', '')) > 100 else '')
                    })
                st.table(event_rows)
            else:
                st.info("No events found.")
            return
    except Exception:
        pass
    st.markdown(f"**Orchestrator:** {content}")

for msg in st.session_state["chat_history"]:
    if msg["role"] == "user":
        st.markdown(f"**You:** {msg['content']}")
    else:
        render_orchestrator_message(msg['content'])

# Show results/expanders after chat history
result = st.session_state.get('last_result', None)
events = []
transcripts = []
if result:
    # Try common keys for events and transcripts
    if "calendar_events" in result:
        events = result.get("calendar_events", [])
    elif "events" in result:
        events = result.get("events", [])
    if "calendar_transcripts" in result:
        transcripts = result.get("calendar_transcripts", [])
    elif "transcripts" in result:
        transcripts = result.get("transcripts", [])

    if events:
        st.markdown("**Event & Transcript Overview**")
        st.metric("Event Count", len(events))
        st.metric("Transcript Count", len(transcripts))
        selected_indices = event_selector(events, transcripts)
        with st.form("process_form"):
            process_submitted = st.form_submit_button("Process Selected Events")
        if process_submitted:
            st.info(f"[DEBUG] Selected indices: {selected_indices}")
            payload = {
                "query": "process_selected_events",
                "selected_event_indices": selected_indices,
                "mode": mode
            }
            st.info(f"[DEBUG] Payload: {payload}")
            with st.spinner("Processing selected events..."):
                try:
                    response = requests.post(API_URL, json=payload)
                    st.info(f"[DEBUG] Response status: {response.status_code}")
                    st.info(f"[DEBUG] Response text: {response.text}")
                    if response.status_code == 200:
                        result = response.json()
                        st.info(f"[DEBUG] Result: {result}")
                        st.session_state['last_result'] = result
                        st.success("Selected events processed.")
                    else:
                        st.error(f"API Error: {response.status_code} {response.text}")
                except Exception as e:
                    st.error(f"Request failed: {e}")

    with st.expander("Processed Transcripts"):
        processed = result.get("processed_transcripts", [])
        display_processed_transcripts(processed)
    with st.expander("Agent States & Outputs"):
        if 'preproc_task_state' in result:
            st.info(f"Preprocessing Task State: {result['preproc_task_state']}")
        if 'preproc_response' in result:
            st.json(result['preproc_response'])
        if 'summ_task_state' in result:
            st.info(f"Summarization Task State: {result['summ_task_state']}")
        if 'summ_response' in result:
            st.json(result['summ_response'])
        if result.get('jira'):
            st.info("Jira Task State:")
            if 'jira_task_state' in result:
                st.write(result['jira_task_state'])
            st.json(result['jira'])
        if result.get('risk'):
            st.info("Risk Detection Task State:")
            if 'risk_task_state' in result:
                st.write(result['risk_task_state'])
            st.json(result['risk'])
    with st.expander("Errors & Debug Info"):
        display_errors(result)
else:
    st.info("No events available to display. Please try fetching again or check your data source.")
    with st.expander("Raw Backend Response for Debugging"):
        st.code(json.dumps(result, indent=2), language="json")

# Additional section for summarizing processed events
if result and "processed_transcripts" in result:
    print("[DEBUG] Processed transcripts available for summarization.")
    with st.expander("Summarize Processed Events", expanded=True):
        with st.form("summarize_form"):
            summarize_submitted = st.form_submit_button("Summarize Processed Events")
        if summarize_submitted:
            processed_transcripts = result.get("processed_transcripts", [])
            st.info(f"[DEBUG] Summarize button clicked. Processed transcripts: {processed_transcripts}")
            payload = {
                "query": "summarize_processed_transcripts",
                "processed_transcripts": processed_transcripts,
                "mode": mode
            }
            st.info(f"[DEBUG] Summarize payload: {payload}")
            with st.spinner("Summarizing processed events..."):
                try:
                    response = requests.post(API_URL, json=payload)
                    st.info(f"[DEBUG] Summarize response status: {response.status_code}")
                    st.info(f"[DEBUG] Summarize response text: {response.text}")
                    if response.status_code == 200:
                        result = response.json()
                        st.info(f"[DEBUG] Summarize result: {result}")
                        st.session_state['last_result'] = result
                        st.success("Summarization complete.")
                    else:
                        st.error(f"Summarization failed: {response.status_code} {response.text}")
                except Exception as e:
                    st.error(f"Summarization request failed: {e}")

    # Show summaries clearly after summarization
    if result.get("summaries"):
        st.markdown("## Summaries")
        summaries = result.get("summaries", [])
        if isinstance(summaries, str):
            display_summaries([summaries])
        else:
            display_summaries(summaries)

# Move chat input and Send button to the bottom
st.markdown("---")
st.markdown("### Type your message and press Enter")
chat_input = st.text_input(
    "Type your message and press Enter",
    key="chat_input",
    value="" if st.session_state.get("clear_input", False) else st.session_state.get("chat_input", "")
)
send_clicked = st.button("Send", key="send_btn")

if send_clicked and chat_input:
    st.session_state["chat_history"].append({"role": "user", "content": chat_input})
    payload = {
        "query": chat_input,
        "mode": mode
    }
    with st.spinner("Processing your request..."):
        try:
            response = requests.post(API_URL, json=payload)
            if response.status_code == 200:
                result = response.json()
                st.session_state["chat_history"].append({"role": "orchestrator", "content": result})
                st.session_state['last_result'] = result
                st.session_state["_last_chat_input"] = chat_input
                st.session_state["clear_input"] = True
                st.rerun()
            else:
                st.session_state["chat_history"].append({"role": "orchestrator", "content": f"API Error: {response.status_code} {response.text}"})
        except Exception as e:
            st.session_state["chat_history"].append({"role": "orchestrator", "content": f"Request failed: {e}"})
        st.session_state["_last_chat_input"] = chat_input
        st.session_state["clear_input"] = True
        st.rerun()
elif st.session_state.get("clear_input"):
    st.session_state["clear_input"] = False

    # Show detected risks clearly after risk step
    if result.get("risk"):
        st.markdown("## Detected Risks")
        risks = result.get("risk", [])
        for risk_obj in risks:
            if isinstance(risk_obj, dict) and "parts" in risk_obj:
                for part in risk_obj["parts"]:
                    if part.get("content_type") == "application/json":
                        detected = part.get("content", {}).get("detected_risks", [])
                        if isinstance(detected, str):
                            import ast
                            detected = ast.literal_eval(detected)
                        for r in detected:
                            st.info(f"**Risk ID:** {r.get('id', '-')}, **Description:** {r.get('description', '-')}, **Severity:** {r.get('severity', '-')} ")


