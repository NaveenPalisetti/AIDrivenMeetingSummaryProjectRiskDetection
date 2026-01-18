"""
AI-Driven Meeting Summary & Risk Detection - Streamlit App
"""

import streamlit as st
import requests
from streamlit import components

API_URL = "http://localhost:8000/mcp/orchestrate"  # Update if needed

st.set_page_config(page_title="AI-Driven Meeting Summary & Risk Detection", layout="wide")
st.title("🤖 AI-Driven Meeting Summary & Risk Detection")
st.write("Welcome to the AI-Driven Meeting Summary & Risk Detection Project!")

# Chat input with icon
chat_col, button_col = st.columns([4, 1])
with chat_col:
    st.markdown("<span style='font-size:1.5em;'>💬</span>", unsafe_allow_html=True)
    chat_input = st.text_input("Type your message", key="chat_input")
with button_col:
    send_clicked = st.button("Send", key="send_button")

if "chat_history" not in st.session_state:
    st.session_state["chat_history"] = []

if chat_input or send_clicked:
    if chat_input:
        st.session_state["chat_history"].append({"role": "user", "content": chat_input})
        # Detect fetch events intent
        if "fetch" in chat_input.lower() and "event" in chat_input.lower():
            payload = {"query": chat_input, "mode": "bart"}
            try:
                resp = requests.post(API_URL, json=payload, timeout=30)
                if resp.status_code == 200:
                    result = resp.json()
                    response = f"[Calendar Agent] {result.get('event_count', 'No count')} events fetched."
                    # Optionally show more details
                    if 'calendar_events' in result:
                        response += f"\nEvents: {result['calendar_events']}"
                    st.session_state["chat_history"].append({"role": "agent", "content": response})
                else:
                    st.session_state["chat_history"].append({"role": "agent", "content": f"[Error] API returned {resp.status_code}: {resp.text}"})
            except Exception as e:
                st.session_state["chat_history"].append({"role": "agent", "content": f"[Error] API call failed: {e}"})
        else:
            st.session_state["chat_history"].append({"role": "agent", "content": "[Agent] Command not recognized. Try 'fetch events'."})
        st.experimental_rerun()

st.markdown("---")

for msg in st.session_state["chat_history"]:
    if msg["role"] == "user":
        st.markdown(f"**You:** {msg['content']}")
    else:
        st.markdown(f"**Bot:** {msg['content']}")
