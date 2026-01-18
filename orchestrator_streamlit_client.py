"""
Streamlit Orchestrator Client: A standalone Streamlit app that sends user queries to the orchestrator API endpoint and displays results.
"""

# Ensure project root is in sys.path for package imports (works in Colab, local, etc)
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))



import streamlit as st
import requests
import re
from mcp.ui.orchestrator_ui_components import (
    event_selector, display_event_details, display_processed_transcripts, display_summaries, display_errors
)
from mcp.ui.orchestrator_client import call_orchestrator
import logging

# --- Fallback get_dynamic_suggestions if not imported ---

# Helper to get ordinal string (1st, 2nd, 3rd, ...)
def ordinal(n):
    if 10 <= n % 100 <= 20:
        suffix = 'th'
    else:
        suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')
    return str(n) + suffix

def get_dynamic_suggestions(chat_history, last_result, events):
    suggestions = []
    # If no events, suggest fetching events
    if not events or len(events) == 0:
        suggestions.append("fetch events")
    else:
        # If events are present, suggest processing each event first, then summarizing
        for idx, event in enumerate(events):
            suggestions.append(f"process the {ordinal(idx+1)} event")
        suggestions.append("process selected events")
        suggestions.append("summarize events with " + st.session_state.get('summarizer_model', 'BART'))
    # If last_result has summaries, suggest risk detection and extracting tasks
    if last_result and isinstance(last_result, dict):
        if last_result.get("summaries"):
            suggestions.append("detect risks")
            suggestions.append("extract tasks")
        if last_result.get("action_items"):
            suggestions.append("create jira from action items")
    # Always suggest help
    suggestions.append("help")
    return suggestions

st.set_page_config(page_title="AI Orchestrator Client", layout="wide")
API_URL = "http://localhost:8000/mcp/orchestrate"  # Use local URL for FastAPI backend in Colab

st.title("🤖 AI-Driven Meeting Selected transcripts for preprocessingSummary & Risk Detection")
st.caption("This app sends queries to the orchestrator API and displays the workflow results.")



# --- Ensure results_history is always initialized ---
if 'results_history' not in st.session_state:
    st.session_state['results_history'] = []
results_history = st.session_state['results_history']

# --- Ensure chat_history is always initialized ---
if 'chat_history' not in st.session_state:
    st.session_state['chat_history'] = []
chat_history = st.session_state['chat_history']


# --- Ensure events and mode are always defined ---
if 'events' not in st.session_state:
    st.session_state['events'] = []
events = st.session_state['events']
mode = st.session_state.get('mode', 'default')

# --- Sidebar: Suggestions and History ---

with st.sidebar:
    st.header("🧠 Summarizer Model")
    model_choice = st.radio("Choose a summarizer: ", ["BART", "Mistral"], key="summarizer_model")

    st.header("💡 Suggestions")
    if results_history:
        last_entry = results_history[-1]
        conversation = []
        for entry in results_history:
            if entry['user']:
                conversation.append({'role': 'user', 'content': entry['user']})
        last_result = last_entry['result']
        last_events = last_entry.get('events', [])
        suggestions = get_dynamic_suggestions(conversation, last_result, last_events)
        sidebar_cmds = {"fetch events", "summarize selected events", "detect risks", "extract tasks", "create jira from action items", "process selected events"}
        filtered = [s for s in suggestions if s.lower() not in sidebar_cmds]
        if filtered:
            for s in filtered:
                st.markdown(f"- {s}")
    else:
        # Show helpful starter suggestions on first load
        starter_suggestions = [
            "fetch events",
            "summarize events with BART",
            "summarize events with Mistral",
            "detect risks",
            "extract tasks",
            "create jira from action items"
        ]
        for s in starter_suggestions:
            st.markdown(f"- {s}")
    st.markdown("---")
    st.header("🕑 History")
    for entry in results_history:
        if entry['user']:
            st.markdown(f"**You:** {entry['user']}")
        if entry['result']:
            st.markdown(f"**Orchestrator:** {str(entry['result'])[:100]}{'...' if len(str(entry['result']))>100 else ''}")



# --- Chat input with icon at the bottom (st.chat_input) ---
st.markdown("---")
chat_input = st.chat_input("Type your command or question:")
send_clicked = chat_input is not None and chat_input != ""

# Small accessibility and style improvements
st.markdown(
    """
    <style>
    .stButton>button:focus {outline: 3px solid #0366d6;}
    .reportview-container .markdown-text-container p {line-height:1.4}
    </style>
    """,
    unsafe_allow_html=True,
)



# Helper: call orchestrator and return result

# Remove old _call_and_update definition (now replaced by the new one with timeout)

# New _call_and_update function with timeout
def _call_and_update(payload, chat_history, timeout=90):    
    with st.spinner("Processing your request..."):
        try:
            result = call_orchestrator(API_URL, payload, timeout=timeout)
            chat_history.append({"role": "orchestrator", "content": result})
            return result
        except Exception as e:
            chat_history.append({"role": "orchestrator", "content": f"API Error: {e}"})
            return None

# Display persistent results history and dynamic suggestions
import json
def render_orchestrator_message(content):
    try:
        # If content is a dict, only show user-friendly messages for known stages
        if isinstance(content, dict):
            result = content
        else:
            result = json.loads(content.replace("'", '"')) if isinstance(content, str) and content.strip().startswith('{') else None
        if result and isinstance(result, dict):
            if result.get('stage') == 'fetch' and 'calendar_events' in result:
                st.markdown(f"**Orchestrator:** Found {len(result.get('calendar_events', []))} recent meeting events. Use the table below to view details.")
                return
            # For summarize/process/preprocess, show summaries/action items if present, else show processing message
            if result.get('stage') in ['preprocess', 'process', 'summarize']:
                if result.get('summaries') or result.get('action_items'):
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
                    return
                else:
                    st.markdown(f"**Orchestrator:** Processing event...")
                    return
    except Exception:
        pass
    if not isinstance(content, dict):
        st.markdown(f"**Orchestrator:** {content}")

# Render the full conversation and results history
for entry in results_history:
    if entry['user']:
        st.markdown(f"**You:** {entry['user']}")
    render_orchestrator_message(entry['result'])
    # Show events table if present
    if entry.get('events'):
        st.markdown(f"**Fetched {len(entry['events'])} Events**")
        event_rows = []
        for ev in entry['events']:
            row = {}
            if 'id' in ev:
                row['id'] = ev['id']
            if 'summary' in ev:
                row['summary'] = ev['summary']
            event_rows.append(row)
        st.table(event_rows)
    # Show summaries and action items if present
    result = entry['result']
    if isinstance(result, dict) and result.get('summaries'):
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
    # --- Show warning if no summaries returned after summarize command ---
    if (
        isinstance(result, dict)
        and 'summaries' not in result
        and isinstance(entry.get('user', ''), str)
        and 'summarize' in entry.get('user', '').lower()
    ):
        st.warning("No summaries were returned by the orchestrator. Please check the backend or try again.")
    # Show processed transcripts if present
    if isinstance(result, dict) and result.get("processed_transcripts"):
        with st.expander("Processed Transcripts"):
            processed = result.get("processed_transcripts", [])
            display_processed_transcripts(processed)
    # Show agent states and outputs if present
    if isinstance(result, dict) and (
        result.get('preproc_task_state') or result.get('preproc_response') or result.get('summ_task_state') or result.get('summ_response') or result.get('jira') or result.get('risk')):
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
    # Show errors if present
    if isinstance(result, dict):
        with st.expander("Errors & Debug Info"):
            display_errors(result)

# Dynamic suggestions based on full conversation
if results_history:
    last_entry = results_history[-1]
    # Use the full conversation for context
    conversation = []
    for entry in results_history:
        if entry['user']:
            conversation.append({'role': 'user', 'content': entry['user']})
    last_result = last_entry['result']
    last_events = last_entry.get('events', [])
    suggestions = get_dynamic_suggestions(
        conversation,
        last_result,
        last_events
    )
else:
    suggestions = []
with st.expander("Suggested Commands / Tips", expanded=False):
    sidebar_cmds = {"fetch events", "summarize selected events", "detect risks", "extract tasks", "create jira from action items", "process selected events"}
    filtered = [s for s in suggestions if s.lower() not in sidebar_cmds]
    if filtered:
        st.markdown("**You can try these conversation commands:**")
        for s in filtered:
            st.markdown(f"- {s}")
def parse_process_event_command(text):
    # Match phrases like 'process the first event', 'process the 2nd event', etc.
    match = re.search(r"process the (\d+)(?:st|nd|rd|th)? event", text.lower())
    if match:
        idx = int(match.group(1)) - 1
        return idx
    # Also support 'process first event', 'process second event', etc.
    words = ["first", "second", "third", "fourth", "fifth", "sixth", "seventh", "eighth", "ninth", "tenth"]
    for i, w in enumerate(words):
        if f"process the {w} event" in text.lower() or f"process {w} event" in text.lower():
            return i
    return None

if chat_input:
    chat_history.append({"role": "user", "content": chat_input})
    # Check for summarization command
    summarize_bart = re.search(r"summarize events with bart", chat_input, re.IGNORECASE)
    summarize_mistral = re.search(r"summarize events with mistral", chat_input, re.IGNORECASE)
    process_idx = parse_process_event_command(chat_input)
    # Persist processed_transcripts in session state if present in last_result
    if 'processed_transcripts' not in st.session_state:
        st.session_state['processed_transcripts'] = []
    if summarize_bart or summarize_mistral:
        model = "BART" if summarize_bart else "Mistral"
        # Use processed_transcripts from session state if available
        processed_transcripts = st.session_state.get('processed_transcripts', [])
        payload = {"query": f"summarize events", "mode": mode, "model": model}
        if processed_transcripts:
            payload["processed_transcripts"] = processed_transcripts
        last_result = _call_and_update(payload, chat_history, timeout=90)
    elif process_idx is not None and events and 0 <= process_idx < len(events):
        # User requested to process a specific event by order
        event = events[process_idx]
        event_id = event.get('id')
        if event_id:
            payload = {"query": f"process event {event_id}", "mode": mode}
            last_result = _call_and_update(payload, chat_history, timeout=90)
    else:
        payload = {"query": chat_input, "mode": mode}
        last_result = _call_and_update(payload, chat_history, timeout=90)
    # Extract events, transcripts, and processed_transcripts if present
    if last_result:
        if isinstance(last_result, dict):
            if 'calendar_events' in last_result:
                events = last_result.get('calendar_events', [])
            elif 'events' in last_result:
                events = last_result.get('events', [])
            if 'calendar_transcripts' in last_result:
                transcripts = last_result.get('calendar_transcripts', [])
            elif 'transcripts' in last_result:
                transcripts = last_result.get('transcripts', [])
            # Store processed_transcripts in session state for next step
            if 'processed_transcripts' in last_result and last_result['processed_transcripts']:
                st.session_state['processed_transcripts'] = last_result['processed_transcripts']
else:
    # On first load, just show welcome and empty state
    last_result = None
    events = []
    transcripts = []



for msg in chat_history:
    if msg["role"] == "user":
        st.markdown(f"**You:** {msg['content']}")
    else:
        render_orchestrator_message(msg['content'])

# Show results/expanders after chat history

suggestions = []
# Show results/expanders after chat history
if last_result:
    if events:
        st.markdown(f"**Fetched {len(events)} Events**")
        # Show a table of event summaries only, no selection or details
        event_rows = []
        for ev in events:
            row = {}
            if 'id' in ev:
                row['id'] = ev['id']
            if 'summary' in ev:
                row['summary'] = ev['summary']
            event_rows.append(row)
        st.table(event_rows)
    # Update suggestions dynamically after each processing step
    suggestions = get_dynamic_suggestions(chat_history, last_result, events)
    with st.expander("Processed Transcripts"):
        processed = last_result.get("processed_transcripts", [])
        display_processed_transcripts(processed)
    with st.expander("Agent States & Outputs"):
        if 'preproc_task_state' in last_result:
            st.info(f"Preprocessing Task State: {last_result['preproc_task_state']}")
        if 'preproc_response' in last_result:
            st.json(last_result['preproc_response'])
        if 'summ_task_state' in last_result:
            st.info(f"Summarization Task State: {last_result['summ_task_state']}")
        if 'summ_response' in last_result:
            st.json(last_result['summ_response'])
        if last_result.get('jira'):
            st.info("Jira Task State:")
            if 'jira_task_state' in last_result:
                st.write(last_result['jira_task_state'])
            st.json(last_result['jira'])
        if last_result.get('risk'):
            st.info("Risk Detection Task State:")
            if 'risk_task_state' in last_result:
                st.write(last_result['risk_task_state'])
            # Try to extract and display detected risks in a user-friendly way
            risk_obj = last_result['risk']
            detected_risks = []
            # Handle both list and dict structures
            if isinstance(risk_obj, list):
                # Look for detected_risks in the nested structure
                for part in risk_obj:
                    try:
                        parts = part.get('parts', [])
                        for p in parts:
                            content = p.get('content', {})
                            if isinstance(content, dict) and 'detected_risks' in content:
                                detected_risks.extend(content['detected_risks'])
                    except Exception:
                        pass
            elif isinstance(risk_obj, dict):
                if 'detected_risks' in risk_obj:
                    detected_risks = risk_obj['detected_risks']
            if detected_risks:
                st.markdown("### Detected Risks")
                for risk in detected_risks:
                    st.warning(risk)
            else:
                st.json(risk_obj)
    with st.expander("Errors & Debug Info"):
        display_errors(last_result)


# Additional section for summarizing processed events
if last_result and "processed_transcripts" in last_result:
    if last_result.get("summaries"):
        st.markdown("## Summaries & Action Items")
        summaries = last_result.get("summaries", [])
        action_items = last_result.get("action_items", [])
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
    if last_result.get("action_items"):
        from mcp.ui.orchestrator_ui_components import display_action_items
        st.markdown("## Action Items")
        action_items = last_result.get("action_items", [])
        display_action_items(action_items)

# Move chat input and Send button to the bottom
st.markdown("---")






# --- Ensure events in session_state are always up-to-date with last_result ---
last_result = st.session_state.get('last_result', None)
if last_result:
    # Try to extract events from last_result if session_state['events'] is empty
    if not st.session_state.get('events'):
        events = []
        if isinstance(last_result, dict):
            if 'calendar_events' in last_result:
                events = last_result.get('calendar_events', [])
            elif 'events' in last_result:
                events = last_result.get('events', [])
        if events:
            st.session_state['events'] = events





# Suggested commands help box
with st.expander("Suggested Commands / Tips", expanded=False):
    sidebar_cmds = {"fetch events", "summarize selected events", "detect risks", "extract tasks", "create jira from action items", "process selected events"}
    filtered = [s for s in suggestions if s.lower() not in sidebar_cmds]
    if filtered:
        st.markdown("**You can try these conversation commands:**")
        for s in filtered:
            st.markdown(f"- {s}")


