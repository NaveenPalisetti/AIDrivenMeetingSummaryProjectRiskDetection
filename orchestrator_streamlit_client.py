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
        action_items = last_result.get("action_items", [])
        if action_items:
            suggestions.append("create jira from action items")
            # Add context-specific commands for selective Jira creation
            # Limit to top 3 action items for Jira creation
            for idx, item in enumerate(action_items[:3]):
                item_str = item.get('title', str(item)) if isinstance(item, dict) else str(item)
                suggestions.append(f"create jira for action item {idx+1}")
            # Add only 1 keyword-based suggestion from the first action item
            if action_items:
                item_str = action_items[0].get('title', str(action_items[0])) if isinstance(action_items[0], dict) else str(action_items[0])
                keyword_match = re.search(r'\b\w{5,}\b', item_str)
                if keyword_match:
                    kw = keyword_match.group(0).lower()
                    suggestions.append(f"create jira for action item containing '{kw}'")
    # Always suggest help
    suggestions.append("help")
    return suggestions

st.set_page_config(page_title="AI Orchestrator Client", layout="wide")
API_URL = "http://localhost:8000/mcp/orchestrate"  # Use local URL for FastAPI backend in Colab

st.title("🤖 AI-Driven Meeting Summary & Project Risk Management")
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
        sidebar_cmds = {"fetch events", "summarize selected events", "create jira from action items", "process selected events"}
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
    sidebar_cmds = {"fetch events", "summarize selected events", "create jira from action items", "process selected events"}
    filtered = [s for s in suggestions if s.lower() not in sidebar_cmds]
    if filtered:
        st.markdown("**You can try these conversation commands:**")
        for s in filtered:
            st.markdown(f"- {s}")

# Top-level function for Jira command parsing
def parse_create_jira_command(text, action_items):
    # Match 'create jira for action item 2', 'create jira for action item containing "keyword"', etc.
    # Normalize input
    text = text.strip().replace('\n', ' ')
    match_num = re.search(r"create jira for action item (\d+)", text.lower())
    if match_num and action_items:
        idx = int(match_num.group(1)) - 1
        if 0 <= idx < len(action_items):
            item = action_items[idx]
            print(f"[DEBUG] parse_create_jira_command returning: {[item]}")
            return [item]  # Return full dict for mapping
    match_kw = re.search(r"create jira for action item containing ['\"]?([\w\s]+)['\"]?", text.lower())
    if match_kw and action_items:
        keyword = match_kw.group(1).strip().lower()
        filtered = []
        for item in action_items:
            item_str = item.get('title', str(item)) if isinstance(item, dict) else str(item)
            if keyword in item_str.lower():
                filtered.append(item)
        if filtered:
            print(f"[DEBUG] parse_create_jira_command returning: {filtered}")
            return filtered
    print("[DEBUG] parse_create_jira_command returning: None")
    return None

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
    summarize_bart = re.search(r"summarize events with bart", chat_input, re.IGNORECASE)
    summarize_mistral = re.search(r"summarize events with mistral", chat_input, re.IGNORECASE)
    process_idx = parse_process_event_command(chat_input)
    # Persist processed_transcripts in session state if present in last_result
    if 'processed_transcripts' not in st.session_state:
        st.session_state['processed_transcripts'] = []
    # Get action items from last_result if available
    action_items = []
    if 'last_result' in st.session_state and isinstance(st.session_state['last_result'], dict):
        print(f"[DEBUG] st.session_state['last_result'] before Jira command: {st.session_state['last_result']}")
        action_items = st.session_state['last_result'].get('action_items', [])
        print(f"[DEBUG] action_items from last_result: {action_items}")
        summaries_dbg = st.session_state['last_result'].get('summaries', [])
        print(f"[DEBUG] summaries from last_result: {summaries_dbg}")
    clean_chat_input = chat_input.strip()
    selected_action_items = parse_create_jira_command(clean_chat_input, action_items)
    print(f"[DEBUG] selected_action_items after parse_create_jira_command: {selected_action_items}")
    if 'create jira' in clean_chat_input.lower():
        print(f"[DEBUG] Preparing to send Jira payload. action_items: {action_items}, selected_action_items: {selected_action_items}")
    if summarize_bart or summarize_mistral:
        model = "BART" if summarize_bart else "Mistral"
        processed_transcripts = st.session_state.get('processed_transcripts', [])
        payload = {"query": f"summarize events", "mode": mode, "model": model}
        if processed_transcripts:
            payload["processed_transcripts"] = processed_transcripts
        print(f"[DEBUG] Sending summarize payload: {payload}")
        last_result = _call_and_update(payload, chat_history, timeout=180)
        # Only update the 'last_result' key in session state
        st.session_state['last_result'] = last_result
    elif process_idx is not None and events and 0 <= process_idx < len(events):
        event = events[process_idx]
        event_id = event.get('id')
        print(f"[DEBUG] Processing event index: {process_idx}, event_id: {event_id}")
        if event_id:
            payload = {"query": f"process event {event_id}", "mode": mode}
            print(f"[DEBUG] Sending process event payload: {payload}")
            last_result = _call_and_update(payload, chat_history, timeout=180)
    elif selected_action_items:
        # User requested to create Jira for specific action items
        # Send the actual user command in the query field, but always include selected_action_items (full dict)
        payload = {"query": chat_input, "mode": mode, "selected_action_items": selected_action_items}
        print(f"[DEBUG] Sending payload to orchestrator API: {payload}")
        print(f"[DEBUG] st.session_state['last_result'] at payload send: {st.session_state.get('last_result')}")
        last_result = _call_and_update(payload, chat_history, timeout=180)
    else:
        payload = {"query": chat_input, "mode": mode}
        print(f"[DEBUG] Sending generic payload: {payload}")
        last_result = _call_and_update(payload, chat_history, timeout=180)
    # Extract events, transcripts, and processed_transcripts if present
    if last_result:
        print(f"[DEBUG] last_result after API call: {last_result}")
        if isinstance(last_result, dict):
            if 'calendar_events' in last_result:
                events = last_result.get('calendar_events', [])
                print(f"[DEBUG] calendar_events extracted: {events}")
            elif 'events' in last_result:
                events = last_result.get('events', [])
                print(f"[DEBUG] events extracted: {events}")
            if 'calendar_transcripts' in last_result:
                transcripts = last_result.get('calendar_transcripts', [])
                print(f"[DEBUG] calendar_transcripts extracted: {transcripts}")
            elif 'transcripts' in last_result:
                transcripts = last_result.get('transcripts', [])
                print(f"[DEBUG] transcripts extracted: {transcripts}")
            if 'processed_transcripts' in last_result and last_result['processed_transcripts']:
                st.session_state['processed_transcripts'] = last_result['processed_transcripts']
                print(f"[DEBUG] processed_transcripts updated in session_state: {last_result['processed_transcripts']}")
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
    sidebar_cmds = {"fetch events", "summarize selected events", "create jira from action items", "process selected events"}
    filtered = [s for s in suggestions if s.lower() not in sidebar_cmds]
    if filtered:
        st.markdown("**You can try these conversation commands:**")
        for s in filtered:
            st.markdown(f"- {s}")


