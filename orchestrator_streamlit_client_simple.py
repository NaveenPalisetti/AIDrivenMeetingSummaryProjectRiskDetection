"""Simplified Streamlit Orchestrator Client (new file)

Minimal chat-style UI in a centered layout. Keeps backend calls
and uses the existing UI helper components to render summaries,
action items, processed transcripts and risks.

This does not modify the original `orchestrator_streamlit_client.py`.
"""

import sys
import os
import json
import re
import streamlit as st
from datetime import datetime
import html

# Ensure project root is importable
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from mcp.ui.orchestrator_ui_components import (
    display_risks,
    display_action_items,
    display_processed_transcripts,
    display_summaries,
    display_errors,
)
from mcp.ui.orchestrator_client import call_orchestrator

# Orchestrator endpoint can be set via env or Streamlit secrets. If set,
# UI will prefer calling the orchestrator for actions instead of local stubs.
API_URL = os.environ.get('ORCHESTRATOR_URL') or st.secrets.get('ORCHESTRATOR_URL', None) or "http://localhost:8000/mcp/orchestrate"
USE_ORCHESTRATOR = bool(API_URL)

st.set_page_config(page_title="AI-Driven Meeting Summary", layout="centered")

st.title("🤖 AI-Driven Meeting Summary — Simple Chat")
st.caption("A compact chat UI. Type commands and see results below. Uses Streamlit chat components.")

# Layout: chat (left) and workflow controls (right)
col_chat, col_controls = st.columns([2, 1])

# --- Session state initialization ---
if 'chat_messages' not in st.session_state:
    st.session_state['chat_messages'] = []  # {role: 'user'|'assistant', content: str|dict}
if 'last_result' not in st.session_state:
    st.session_state['last_result'] = None
if 'events' not in st.session_state:
    st.session_state['events'] = []
if 'processed_transcripts' not in st.session_state:
    st.session_state['processed_transcripts'] = []
if 'summarizer_model' not in st.session_state:
    st.session_state['summarizer_model'] = 'BART'

# Model selector (top, simple)
st.selectbox("Summarizer Model", ["BART", "Mistral"], index=0, key='summarizer_model')


def _call_backend(payload, timeout=1000):
    """Call the orchestrator backend and return the result (dict or str).
    Stores the last_result in session state.
    """
    try:
        if not API_URL:
            raise RuntimeError('ORCHESTRATOR_URL not configured')
        result = call_orchestrator(API_URL, payload, timeout=timeout)
    except Exception as e:
        result = {"error": str(e)}
    st.session_state['last_result'] = result
    return result


def orchestrator_or_stub(action: str, payload: dict = None, timeout: int = 300):
    """Route an action to the orchestrator backend if available, otherwise call local stub functions.

    action: one of 'fetch_events','preprocess','summarize','detect_risks','create_tasks','notify'
    payload: action-specific kwargs
    """
    payload = payload or {}
    if not API_URL:
        return {'error': 'ORCHESTRATOR_URL not configured'}
    # Always route to the orchestrator backend for all actions.
    call_payload = {'action': action, **payload}
    return _call_backend(call_payload, timeout=timeout)


def _add_assistant_typing():
    """Append a typing placeholder assistant message and return its index."""
    idx = len(st.session_state['chat_messages'])
    st.session_state['chat_messages'].append({'role': 'assistant', 'content': {'typing': True}, 'time': datetime.utcnow().isoformat()})
    return idx


def _replace_assistant_message(index: int, content):
    """Replace a previously added assistant message at index with real content."""
    if 0 <= index < len(st.session_state['chat_messages']):
        st.session_state['chat_messages'][index]['content'] = content
        st.session_state['chat_messages'][index]['time'] = datetime.utcnow().isoformat()
    else:
        # fallback: append
        st.session_state['chat_messages'].append({'role': 'assistant', 'content': content, 'time': datetime.utcnow().isoformat()})


def display_chat_history():
    """Render chat messages using Streamlit chat components."""
    for idx, msg in enumerate(st.session_state['chat_messages']):
        role = msg.get('role')
        content = msg.get('content')
        ts = msg.get('time')
        is_typing = isinstance(content, dict) and content.get('typing')
        meta = ''
        if ts:
            try:
                meta = datetime.fromisoformat(ts).strftime('%Y-%m-%d %H:%M:%S')
            except Exception:
                meta = ts
        # Use Streamlit chat_message for modern chat UI
        if role == 'user':
            with st.chat_message('user'):
                st.markdown(f"**You**: {html.escape(str(content))}")
                if meta:
                    st.markdown(f"<div style='font-size:12px;color:#666'>{meta}</div>", unsafe_allow_html=True)
        else:
            with st.chat_message('assistant'):
                st.markdown("**Assistant:**")
                if meta:
                    st.markdown(f"<div style='font-size:12px;color:#666'>{meta}</div>", unsafe_allow_html=True)
                # Typing indicator
                if is_typing:
                    st.markdown("⏳ Assistant is typing...", unsafe_allow_html=True)
                    continue
                if isinstance(content, dict):
                    if content.get('summaries'):
                        display_summaries(content.get('summaries'))
                    if content.get('action_items'):
                        display_action_items(content.get('action_items'))
                    if content.get('processed_transcripts'):
                        with st.expander('Processed Transcripts'):
                            display_processed_transcripts(content.get('processed_transcripts'))
                    if content.get('risk'):
                        risk_obj = content.get('risk')
                        detected_risks = []
                        if isinstance(risk_obj, dict) and 'detected_risks' in risk_obj:
                            detected_risks = risk_obj['detected_risks']
                        elif isinstance(risk_obj, list):
                            for part in risk_obj:
                                try:
                                    parts = part.get('parts', [])
                                    for p in parts:
                                        c = p.get('content', {})
                                        if isinstance(c, dict) and 'detected_risks' in c:
                                            detected_risks.extend(c['detected_risks'])
                                except Exception:
                                    pass
                        if detected_risks:
                            display_risks(detected_risks)
                        else:
                            st.info('No risks detected.')
                    if content.get('error'):
                        st.error(content.get('error'))
                else:
                    st.markdown(html.escape(str(content)))
            # per-message actions
            cols = st.columns([1,1,1,6])
            if cols[0].button('Regenerate', key=f'regen_{idx}'):
                # resend the last user query that produced this assistant message if available
                # we search backwards for the previous user message
                for prev in reversed(st.session_state['chat_messages'][:idx]):
                    if prev.get('role') == 'user':
                        query = prev.get('content')
                        typ_idx = _add_assistant_typing()
                        resp = orchestrator_or_stub('query', {'query': query, 'model': st.session_state.get('summarizer_model','BART')}, timeout=300)
                        _replace_assistant_message(typ_idx, resp)
                        st.experimental_rerun()
                        break
            if cols[1].button('Create Jira', key=f'jira_{idx}'):
                # if assistant message contains action_items, send create-jira payload
                if isinstance(content, dict) and content.get('action_items'):
                    typ_idx = _add_assistant_typing()
                    resp = orchestrator_or_stub('create_tasks', {'action_items': content.get('action_items')}, timeout=120)
                    _replace_assistant_message(typ_idx, {'stage': 'jira', 'jira': resp})
                    st.experimental_rerun()
            if cols[2].button('Notify', key=f'notify_{idx}'):
                typ_idx = _add_assistant_typing()
                resp = orchestrator_or_stub('notify', {'items': st.session_state.get('events', []), 'channel': 'in-app'}, timeout=60)
                _replace_assistant_message(typ_idx, {'stage': 'notify', 'result': resp})
                st.experimental_rerun()


# Show history
with col_chat:
    display_chat_history()

with col_controls:
    st.header('Workflow')
    st.selectbox("Summarizer Model", ["BART", "Mistral"], index=0, key='summarizer_model')
    # Event selector
    ev_options = []
    for i, ev in enumerate(st.session_state.get('events', [])):
        title = ev.get('summary') or ev.get('description') or f'Event {i+1}'
        ev_options.append((f"{i+1}. {title}", i))
    selected = st.multiselect('Select events (for batch actions)', [x[0] for x in ev_options], key='selected_events')
    selected_indices = [i for label, i in ev_options if label in selected]
    st.session_state['selected_event_indices'] = selected_indices

    if st.button('Fetch Events'):
        idx = _add_assistant_typing()
        resp = orchestrator_or_stub('fetch_events', {'provider': 'mock'}, timeout=120)
        events = []
        if isinstance(resp, dict):
            events = resp.get('calendar_events') or resp.get('events') or []
        st.session_state['events'] = events
        _replace_assistant_message(idx, {'stage': 'fetch', 'calendar_events': events})
        st.experimental_rerun()

    if st.button('Preprocess Selected'):
        idxs = st.session_state.get('selected_event_indices', [])
        if not idxs:
            st.warning('No events selected. Please select events to preprocess.')
        else:
            with st.modal('Confirm Preprocess'):
                st.write(f'Preprocess {len(idxs)} selected event(s)?')
                if st.button('Confirm Preprocess', key='confirm_preproc'):
                    st.session_state['_run_preprocess'] = True
            if st.session_state.pop('_run_preprocess', False):
                # gather events and run local preprocessing
                events = [st.session_state.get('events', [])[i] for i in idxs]
                idx = _add_assistant_typing()
                resp = orchestrator_or_stub('preprocess', {'events': events}, timeout=300)
                processed = []
                if isinstance(resp, dict):
                    processed = resp.get('processed_transcripts', [])
                st.session_state['processed_transcripts'] = processed
                _replace_assistant_message(idx, {'stage': 'preprocess', 'processed_transcripts': processed})
                st.success('Preprocessing complete')
                st.experimental_rerun()

    if st.button('Summarize Selected'):
        idxs = st.session_state.get('selected_event_indices', [])
        if not idxs:
            st.warning('No events selected. Please select events to summarize.')
        else:
            model = st.session_state.get('summarizer_model','BART')
            with st.modal('Confirm Summarize'):
                st.write(f'Summarize {len(idxs)} selected event(s) with {model}?')
                if st.button('Confirm Summarize', key='confirm_summ'):
                    st.session_state['_run_summarize'] = True
            if st.session_state.pop('_run_summarize', False):
                # prepare transcripts to summarize
                if st.session_state.get('processed_transcripts'):
                    # take matching indices from processed_transcripts if lengths align
                    processed = st.session_state.get('processed_transcripts', [])
                    to_summarize = [processed[i] for i in idxs if i < len(processed)]
                else:
                    events = [st.session_state.get('events', [])[i] for i in idxs]
                    to_summarize = preprocess_events(events)
                idx = _add_assistant_typing()
                resp = orchestrator_or_stub('summarize', {'processed_transcripts': to_summarize, 'model': model}, timeout=1200)
                res = resp
                _replace_assistant_message(idx, res)
                st.success('Summarization complete')
                st.experimental_rerun()

    if st.button('Detect Risks'):
        # local risk detection
        last = st.session_state.get('last_result')
        summaries = []
        if isinstance(last, dict) and last.get('summaries'):
            summaries = last.get('summaries')
        elif st.session_state.get('processed_transcripts'):
            summaries = [{'meeting_index': i+1, 'summary': t} for i, t in enumerate(st.session_state.get('processed_transcripts'))]
        idx = _add_assistant_typing()
        resp = orchestrator_or_stub('detect_risks', {'summaries': summaries}, timeout=120)
        _replace_assistant_message(idx, {'stage': 'risk', 'risk': resp})
        st.experimental_rerun()

    if st.button('Create Tasks from Last Action Items'):
        last = st.session_state.get('last_result')
        items = last.get('action_items') if isinstance(last, dict) else None
        if not items:
            st.warning('No action items found in last result')
        else:
            with st.modal('Confirm Create Tasks'):
                st.write(f'Create tasks for {len(items)} action item(s)?')
                if st.button('Confirm Create Tasks', key='confirm_create_tasks'):
                    st.session_state['_run_create_tasks'] = True
            if st.session_state.pop('_run_create_tasks', False):
                idx = _add_assistant_typing()
                resp = orchestrator_or_stub('create_tasks', {'action_items': items}, timeout=300)
                _replace_assistant_message(idx, {'stage': 'jira', 'jira': resp})
                st.success('Task creation complete')
        st.experimental_rerun()

    st.markdown('---')
    if st.session_state.get('events'):
        st.markdown('**Events (preview)**')
        for i, ev in enumerate(st.session_state.get('events', []), start=1):
            st.markdown(f"**{i}.** {ev.get('summary','(no title)')} — {ev.get('id','')}")
    else:
        st.info('No events loaded.')

# Chat input area: use Streamlit chat_input for a native chat box
user_text = st.chat_input('Type a command or question...')
if user_text:
    # add user message with timestamp
    st.session_state['chat_messages'].append({'role': 'user', 'content': user_text, 'time': datetime.utcnow().isoformat()})

    # quick action parsing can be done by helper functions in main app; here we send general payload
    payload = {
        'query': user_text,
        'mode': st.session_state.get('summarizer_model', 'BART'),
        'model': st.session_state.get('summarizer_model', 'BART'),
    }
    if st.session_state.get('processed_transcripts'):
        payload['processed_transcripts'] = st.session_state['processed_transcripts']

    timeout = 3000 if st.session_state.get('summarizer_model') == 'Mistral' else 60
    typ_idx = _add_assistant_typing()
    # use orchestrator route for queries
    q_payload = {'query': user_text, 'model': st.session_state.get('summarizer_model', 'BART')}
    if st.session_state.get('processed_transcripts'):
        q_payload['processed_transcripts'] = st.session_state.get('processed_transcripts')
    result = orchestrator_or_stub('query', q_payload, timeout=timeout)
    _replace_assistant_message(typ_idx, result)

    # update events and processed_transcripts from result if present
    if isinstance(result, dict):
        if 'calendar_events' in result:
            st.session_state['events'] = result.get('calendar_events', [])
        elif 'events' in result:
            st.session_state['events'] = result.get('events', [])
        if 'processed_transcripts' in result:
            st.session_state['processed_transcripts'] = result.get('processed_transcripts', [])

    # Rerun to show updated history immediately
    st.experimental_rerun()


# Small utility buttons
col_actions = st.columns([1,1,1,1,6])[0:4]
if col_actions[0].button('Fetch Events'):
    idx = _add_assistant_typing()
    resp = orchestrator_or_stub('fetch_events', {'provider': 'mock'}, timeout=120)
    events = []
    if isinstance(resp, dict):
        events = resp.get('calendar_events') or resp.get('events') or []
    st.session_state['events'] = events
    _replace_assistant_message(idx, {'stage': 'fetch', 'calendar_events': events})
    st.experimental_rerun()

if col_actions[1].button('Summarize Events'):
    model = st.session_state.get('summarizer_model','BART')
    if st.session_state.get('processed_transcripts'):
        to_summarize = st.session_state.get('processed_transcripts')
    else:
        to_summarize = preprocess_events(st.session_state.get('events', []))
    idx = _add_assistant_typing()
    resp = orchestrator_or_stub('summarize', {'processed_transcripts': to_summarize, 'model': model}, timeout=1200)
    _replace_assistant_message(idx, resp)
    st.experimental_rerun()

if col_actions[2].button('Detect Risks'):
    if st.session_state.get('last_result') and isinstance(st.session_state.get('last_result'), dict) and st.session_state.get('last_result').get('summaries'):
        summaries = st.session_state.get('last_result').get('summaries')
    elif st.session_state.get('processed_transcripts'):
        summaries = [{'meeting_index': i+1, 'summary': t} for i, t in enumerate(st.session_state.get('processed_transcripts'))]
    else:
        summaries = []
    idx = _add_assistant_typing()
    resp = orchestrator_or_stub('detect_risks', {'summaries': summaries}, timeout=120)
    _replace_assistant_message(idx, {'stage': 'risk', 'risk': resp})
    st.experimental_rerun()

if col_actions[3].button('Clear Chat'):
    st.session_state['chat_messages'] = []
    st.session_state['last_result'] = None
    st.experimental_rerun()

# Export button
chat_text = "\n\n".join([f"{m['role'].upper()}: {m['content'] if isinstance(m['content'], str) else json.dumps(m['content'])}" for m in st.session_state['chat_messages']])
st.download_button('Export Chat', chat_text, file_name='chat_export.txt')
