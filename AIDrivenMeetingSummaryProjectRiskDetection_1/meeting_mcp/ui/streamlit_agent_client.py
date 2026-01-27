import sys
import pathlib
import json
import asyncio
import os
import streamlit as st

# Ensure project root is importable when Streamlit runs the script.
# This is a small developer convenience (prefer running Streamlit from
# the project root or setting PYTHONPATH in production).
ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from meeting_mcp.system import create_system

# Page config
st.set_page_config(
    page_title="AI-Driven Meeting Summary & Project Risk Management",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)




_CSS = """
<style>
    .main-header { font-size: 2rem; font-weight:700; color: #1f77b4; }
    .sub-header { font-size: 1rem; color: #666; margin-bottom: 1rem; }
    .badge { display:inline-block; padding:0.2rem .6rem; border-radius:4px; background:#f0f0f0; margin-right:6px; }
    .credentials { background:#fff; padding:0.5rem; border-radius:6px; box-shadow: 0 1px 2px rgba(0,0,0,0.04); }
</style>
"""


@st.cache_resource
def create_runtime(mode: str = "hybrid"):
    # Returns: (mcp_host, inproc_host, tools, orchestrator)
    return create_system(mode=mode)


# No runtime selector in chat-only UX; use default wiring
mcp_host, inproc_host, tools, orchestrator = create_runtime()


# Initialize message history in session state
if "messages" not in st.session_state:
    st.session_state.messages = []


def add_message(role: str, content: str):
    st.session_state.messages.append({"role": role, "content": content})


def credentials_status() -> str:
    # Check env var or repo config path
    env_path = os.environ.get("MCP_SERVICE_ACCOUNT_FILE")
    if env_path and os.path.exists(env_path):
        return f"Using {env_path} (MCP_SERVICE_ACCOUNT_FILE)"
    fallback = os.path.join(os.path.dirname(__file__), "../config/credentials.json")
    fallback = os.path.abspath(fallback)
    if os.path.exists(fallback):
        return f"Using {fallback} (meeting_mcp/config/credentials.json)"
    return "No credentials found — set MCP_SERVICE_ACCOUNT_FILE or place credentials.json in meeting_mcp/config/"


st.markdown(_CSS, unsafe_allow_html=True)

# Page heading similar to orchestrator_streamlit_client
st.title("🤖 AI-Driven Meeting Summary & Project Risk Management")
st.caption("A lightweight UI to run the orchestrator and inspect results.")

# Sidebar: summarizer/model selector (BART / Mistral)
with st.sidebar:
    st.header("🧠 Summarizer Model")
    if 'summarizer_model' not in st.session_state:
        st.session_state['summarizer_model'] = 'BART'
    model_choice = st.radio("Choose a summarizer:", ["BART", "Mistral"], key="summarizer_model")

col1 = st.container()

    # Chat-only message area using Streamlit's chat components
for message in st.session_state.messages:
    role = message.get("role", "system")
    with st.chat_message(role):
        st.markdown(message.get("content", ""))

# Chat input: submit with Enter — runs the orchestrator by default
if prompt := st.chat_input("Describe your request (press Enter to send)"):
    add_message("user", prompt)
    with st.chat_message("user"):
        st.markdown(prompt)

    # Run orchestrator (chat-only UX; no params textarea)
    try:
        result = asyncio.run(orchestrator.orchestrate(prompt, {}))

        # Add a compact system entry for history (keeps messages small)
        short_summary = result.get("intent", "")
        add_message("system", f"intent: {short_summary}")

        # Prepare assistant content to persist in session history
        calendar_block = result.get("results", {}).get("calendar") if isinstance(result, dict) else None
        if calendar_block and calendar_block.get("status") == "success":
            events = calendar_block.get("events", [])
            # Build a concise markdown summary for session history
            if not events:
                assistant_md = "No calendar events found for the requested range."
            else:
                lines = [f"**Calendar:** {len(events)} event(s) returned"]
                for ev in events[:10]:
                    when = ev.get('start', {}).get('dateTime') or ev.get('start', {}).get('date')
                    lines.append(f"- {when} — {ev.get('summary')}")
                if len(events) > 10:
                    lines.append(f"...and {len(events)-10} more events")
                assistant_md = "\n".join(lines)
        else:
            # Fallback: short textual summary
            assistant_md = f"Result: intent={result.get('intent')}"

        # Persist assistant summary to session history so previous responses remain
        add_message("assistant", assistant_md)

        # Render assistant response. If this is a calendar result, show nicely.
        with st.chat_message("assistant"):
            if calendar_block and calendar_block.get("status") == "success":
                events = calendar_block.get("events", [])
                if not events:
                    st.info("No calendar events found for the requested range.")
                else:
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
                            with cols[1]:
                                st.markdown("**Metadata**")
                                st.write({k: ev.get(k) for k in ("id", "status", "iCalUID") if ev.get(k)})

                # Keep the raw JSON available for debugging
                with st.expander("Raw calendar JSON", expanded=False):
                    st.code(json.dumps(calendar_block, indent=2), language="json")
            else:
                # Fallback: show full result as formatted JSON
                st.markdown("Result:\n\n" + "```json\n" + json.dumps(result, indent=2) + "\n```")
    except Exception as e:
        add_message("system", f"Error: {e}")
        with st.chat_message("assistant"):
            st.markdown(f"Error: {e}")

# Status & Tools hidden in chat-only mode per user request
