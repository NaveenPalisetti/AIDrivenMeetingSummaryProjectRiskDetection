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
API_URL = "http://localhost:8000/mcp/orchestrate"  # Use local URL for FastAPI backend in Colab

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
            # else:
            #     st.info("No events found.")
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
        # Allow selecting events and processing selected ones
        st.markdown("Select events to process below:")
        if 'events' in st.session_state:
            session_events = st.session_state['events']
            session_transcripts = st.session_state.get('transcripts', [])
        else:
            session_events = events
            session_transcripts = transcripts
        selected_indices = event_selector(session_events, session_transcripts)
        if st.button("Process Selected Events"):
            payload = {"query": "process_selected_events", "selected_event_indices": selected_indices, "mode": mode}
            send_query(payload)
            st.experimental_rerun()

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
    pass

# Additional section for summarizing processed events
if result and "processed_transcripts" in result:
    # No summarize button; instruct user to type in chat

    # Show summaries clearly after summarization
    if result.get("summaries"):
        st.markdown("## Summaries & Action Items")
        summaries = result.get("summaries", [])
        action_items = result.get("action_items", [])
        cols = st.columns([2, 1])
        with cols[0]:
            st.markdown("### Summary")
            if isinstance(summaries, str):
                display_summaries([summaries])
            else:
                display_summaries(summaries)
        with cols[1]:
            st.markdown("### Action Items")
            if action_items:
                from mcp.ui.orchestrator_ui_components import display_action_items
                display_action_items(action_items)

    # Show action items clearly after summarization
    if result.get("action_items"):
        from mcp.ui.orchestrator_ui_components import display_action_items
        st.markdown("## Action Items")
        action_items = result.get("action_items", [])
        display_action_items(action_items)

# Move chat input and Send button to the bottom
st.markdown("---")

# Helper to send queries to the backend and update session state
def send_query(payload):
    with st.spinner("Processing your request..."):
        try:
            response = requests.post(API_URL, json=payload)
            if response.status_code == 200:
                result = response.json()
                st.session_state["chat_history"].append({"role": "orchestrator", "content": result})
                st.session_state['last_result'] = result
                # Cache events/transcripts for UI selections
                if isinstance(result, dict) and result.get('calendar_events'):
                    st.session_state['events'] = result.get('calendar_events', [])
                if isinstance(result, dict) and result.get('calendar_transcripts'):
                    st.session_state['transcripts'] = result.get('calendar_transcripts', [])
            else:
                st.session_state["chat_history"].append({"role": "orchestrator", "content": f"API Error: {response.status_code} {response.text}"})
        except Exception as e:
            st.session_state["chat_history"].append({"role": "orchestrator", "content": f"Request failed: {e}"})


# Sidebar quick-action toolbar
st.sidebar.markdown("### Quick Actions")
if st.sidebar.button("Fetch Events"):
    st.session_state["chat_history"].append({"role": "user", "content": "Fetch my recent events"})
    payload = {"query": "fetch recent events", "mode": mode}
    send_query(payload)
    st.experimental_rerun()

if st.sidebar.button("Summarize Events"):
    st.session_state["chat_history"].append({"role": "user", "content": "Summarize selected events"})
    payload = {"query": "summarize selected events", "mode": mode}
    send_query(payload)
    st.experimental_rerun()

if st.sidebar.button("Detect Risks"):
    st.session_state["chat_history"].append({"role": "user", "content": "Detect risks in last summary"})
    payload = {"query": "detect risks", "mode": mode}
    send_query(payload)
    st.experimental_rerun()

if st.sidebar.button("Extract Tasks"):
    st.session_state["chat_history"].append({"role": "user", "content": "Extract tasks from last summary"})
    payload = {"query": "extract tasks", "mode": mode}
    send_query(payload)
    st.experimental_rerun()

if st.sidebar.button("Create Jira"):
    st.session_state["chat_history"].append({"role": "user", "content": "Create Jira from action items"})
    payload = {"query": "create jira from action items", "mode": mode}
    send_query(payload)
    st.experimental_rerun()


# Chat input (uses chat_input if available, falls back to text_input)
try:
    chat_input = st.chat_input("Type your message and press Enter", key="chat_input")
except Exception:
    chat_input = st.text_input(
        "Type your message and press Enter",
        key="chat_input_fallback",
        value="" if st.session_state.get("clear_input", False) else st.session_state.get("chat_input", "")
    )

if chat_input:
    st.session_state["chat_history"].append({"role": "user", "content": chat_input})
    payload = {"query": chat_input, "mode": mode}
    # Special-case quick responses for action-words to show cached results first
    if any(word in chat_input.lower() for word in ["task", "action item", "action items", "tasks"]):
        last_result = st.session_state.get('last_result', {})
        action_items = last_result.get("action_items", [])
        if action_items:
            from mcp.ui.orchestrator_ui_components import display_action_items
            st.markdown("**Orchestrator:** Here are the action items from the last summary:")
            display_action_items(action_items)
            st.session_state["clear_input"] = True
        else:
            send_query(payload)
    else:
        send_query(payload)
    st.session_state["_last_chat_input"] = chat_input
    st.session_state["clear_input"] = True
    st.experimental_rerun()

elif st.session_state.get("clear_input"):
    st.session_state["clear_input"] = False

    # Show detected risks clearly after risk step
    if result and result.get("risk"):
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


