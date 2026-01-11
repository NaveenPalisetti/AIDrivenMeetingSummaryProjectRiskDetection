"""
Orchestrator agent for MCP: Handles user queries, input validation, agent routing, parallel execution, and workflow state management.
"""
from typing import Dict, Any, List
from concurrent.futures import ThreadPoolExecutor, as_completed
import uuid

from mcp.protocols.a2a import a2a_endpoint, a2a_request
from mcp.agents.mcp_google_calendar import MCPGoogleCalendar
from mcp.agents.transcript_preprocessing_agent import TranscriptPreprocessingAgent
from mcp.agents.summarization_agent import SummarizationAgent
from mcp.agents.risk_detection_agent import RiskDetectionAgent
from mcp.core.a2a_base_agent import A2AMessage, A2ATask, TaskState
from mcp.agents.notification_agent import NotificationAgent

class OrchestratorState:
    def __init__(self):
        self.state = {}
    def update(self, key, value):
        self.state[key] = value
    def get(self, key, default=None):
        return self.state.get(key, default)


class OrchestratorAgent:
    def __init__(self):
        self.tasks = {}

    @a2a_endpoint
    def handle_query(self, query: str, user: str, date: str = None, permissions: list = None, selected_event_indices: list = None, mode: str = None, create_jira: bool = False, stage: str = "fetch") -> dict:
        """
        Interactive, stepwise workflow for orchestrator:
        stage: 'fetch' | 'preprocess' | 'summarize' | 'jira' | 'risk' | 'notify'
        """
        print(f"[DEBUG] OrchestratorAgent.handle_query stage: {stage}, mode: {mode}, create_jira: {create_jira}")
        mode = "bart"  # Force BART mode regardless of input
        result = {"stage": stage}
        try:
            if stage == "fetch":
                cal = MCPGoogleCalendar(calendar_id="primary")
                import datetime
                now = datetime.datetime.utcnow()
                start_time = now - datetime.timedelta(days=37)
                end_time = now + datetime.timedelta(days=1)
                events = cal.fetch_events(start_time, end_time)
                transcripts = cal.get_transcripts_from_events(events)
                result['calendar_events'] = events
                result['calendar_transcripts'] = transcripts
                result['event_count'] = len(events)
                result['transcript_count'] = len(transcripts)
                result['next_actions'] = ["preprocess"]
                return result

            if stage == "preprocess":
                # UI-driven event selection
                cal_events = []
                cal_transcripts = []
                if 'calendar_events' in query and 'calendar_transcripts' in query:
                    cal_events = query['calendar_events']
                    cal_transcripts = query['calendar_transcripts']
                else:
                    # Fallback: fetch again
                    cal = MCPGoogleCalendar(calendar_id="primary")
                    import datetime
                    now = datetime.datetime.utcnow()
                    start_time = now - datetime.timedelta(days=37)
                    end_time = now + datetime.timedelta(days=1)
                    cal_events = cal.fetch_events(start_time, end_time)
                    cal_transcripts = cal.get_transcripts_from_events(cal_events)
                if selected_event_indices is not None and isinstance(selected_event_indices, list) and selected_event_indices:
                    selected_events = [cal_events[i] for i in selected_event_indices if 0 <= i < len(cal_events)]
                    selected_transcripts = [cal_transcripts[i] for i in selected_event_indices if 0 <= i < len(cal_transcripts)]
                else:
                    selected_events = cal_events
                    selected_transcripts = cal_transcripts
                result['selected_events'] = selected_events
                result['selected_transcripts'] = selected_transcripts
                preproc = TranscriptPreprocessingAgent()
                preproc_payload = {"transcripts": selected_transcripts}
                preproc_response = a2a_request(preproc.process, preproc_payload)
                if preproc_response["status"] == "ok":
                    processed_transcripts_msg = preproc_response["result"]
                    processed_transcripts = []
                    if hasattr(processed_transcripts_msg, 'parts'):
                        for part in processed_transcripts_msg.parts:
                            if getattr(part, 'content_type', None) == "application/json":
                                processed_transcripts = part.content.get('processed_transcripts', [])
                    result['processed_transcripts'] = processed_transcripts
                    result['processed_transcript_count'] = len(processed_transcripts)
                    result['next_actions'] = ["summarize"]
                else:
                    result['preprocessing_error'] = preproc_response["error"]
                return result

            if stage == "summarize":
                processed_transcripts = query.get('processed_transcripts', []) if isinstance(query, dict) else []
                summarizer = SummarizationAgent(mode=mode)
                initial_msg = A2AMessage(message_id=str(uuid.uuid4()), role="user")
                initial_msg.add_part("application/json", {"processed_transcripts": processed_transcripts, "mode": mode})
                task_id = summarizer.create_task(initial_msg)
                summary_msg = summarizer.summarize_protocol(processed_transcripts=processed_transcripts, mode=mode)
                summarizer.update_task(task_id, summary_msg, TaskState.COMPLETED)
                summaries = []
                if hasattr(summary_msg, 'parts'):
                    for part in summary_msg.parts:
                        if getattr(part, 'content_type', None) == "text/plain":
                            summaries.append(part.content)
                result['summaries'] = summaries
                result['summary_count'] = len(summaries)
                result['next_actions'] = ["jira", "risk"]
                return result

            if stage == "jira":
                summaries = query.get('summaries', []) if isinstance(query, dict) else []
                from mcp.agents.jira_agent import JiraAgent
                jira_agent = JiraAgent()
                jira_msg = A2AMessage(message_id=str(uuid.uuid4()), role="user")
                jira_msg.add_part("application/json", {"summary": summaries, "user": user, "date": date})
                jira_task_id = jira_agent.create_task(jira_msg)
                jira_response_msg = jira_agent.create_jira(summaries, user=user, date=date)
                jira_agent.update_task(jira_task_id, jira_response_msg, TaskState.COMPLETED)
                created_tasks = []
                if hasattr(jira_response_msg, 'parts'):
                    for part in jira_response_msg.parts:
                        if getattr(part, 'content_type', None) == "application/json":
                            created_tasks = part.content.get('created_tasks', [])
                result['jira'] = [created_tasks]
                result['next_actions'] = ["risk"]
                return result

            if stage == "risk":
                summaries = query.get('summaries', []) if isinstance(query, dict) else []
                created_tasks = query.get('jira', [{}])[0] if isinstance(query, dict) and 'jira' in query else []
                summary_for_risk = summaries[0] if summaries else ""
                tasks_for_risk = created_tasks.get('created_tasks', []) if isinstance(created_tasks, dict) else []
                progress = {}
                risk_agent = RiskDetectionAgent()
                detected_risks = risk_agent.detect(meeting_id=date or "meeting", summary={"summary_text": summary_for_risk}, tasks=tasks_for_risk, progress=progress)
                result['risk'] = [
                    {"parts": [
                        {"content_type": "application/json", "content": {"detected_risks": detected_risks}}
                    ]}
                ]
                result['next_actions'] = ["notify"]
                return result

            if stage == "notify":
                summaries = query.get('summaries', []) if isinstance(query, dict) else []
                created_tasks = query.get('jira', [{}])[0] if isinstance(query, dict) and 'jira' in query else []
                risks = query.get('risk', [{}])[0] if isinstance(query, dict) and 'risk' in query else []
                summary_for_notify = summaries[0] if summaries else ""
                tasks_for_notify = created_tasks.get('created_tasks', []) if isinstance(created_tasks, dict) else []
                detected_risks = risks.get('parts', [{}])[0].get('content', {}).get('detected_risks', []) if isinstance(risks, dict) else []
                notification_agent = NotificationAgent()
                notification_agent.notify(
                    meeting_id=date or "meeting",
                    summary={"summary_text": summary_for_notify},
                    tasks=tasks_for_notify,
                    risks=detected_risks
                )
                result['notified'] = True
                result['next_actions'] = []
                return result

            result['error'] = f"Unknown stage: {stage}"
            return result
        except Exception as e:
            result['error'] = str(e)
            return result

    def _validate_date(self, date: str) -> bool:
        # Simple YYYY-MM-DD check
        import re
        return bool(re.match(r"^\\d{4}-\\d{2}-\\d{2}$", date))

    def _check_permissions(self, user: str, permissions: List[str]) -> bool:
        # Stub: always true for demo
        return True

    def _detect_intent(self, query: str) -> str:
        # Simple keyword-based intent detection
        q = query.lower()
        if "calendar" in q or "event" in q or "fetch transcript" in q:
            return "calendar"
        if "summary" in q:
            return "summarize"
        if "jira" in q:
            return "create_jira"
        return "unknown"

    def _route_agents(self, intent: str) -> List[str]:
        # Map intent to agent function names
        if intent == "calendar":
            return ["calendar_agent"]
        if intent == "summarize":
            return ["summary_agent"]
        if intent == "create_jira":
            return ["jira_agent"]
        if intent == "unknown":
            return ["summary_agent", "jira_agent"]  # Example: run both
        return []

    def _execute_agents_parallel(self, agents: List[str], query: str, user: str, date: str):
        # Map agent names to callables
        def calendar_agent_func(**kwargs):
            import traceback
            debug_info = {}
            try:
                # Fetch events for the last 7 days and next 1 day
                cal = MCPGoogleCalendar()
                import datetime
                now = datetime.datetime.utcnow()
                start_time = now - datetime.timedelta(days=7)
                end_time = now + datetime.timedelta(days=1)
                debug_info['start_time'] = str(start_time)
                debug_info['end_time'] = str(end_time)
                events = cal.fetch_events(start_time, end_time)
                debug_info['event_count'] = len(events)
                transcripts = cal.get_transcripts_from_events(events)
                debug_info['transcript_count'] = len(transcripts)
                return {"transcripts": transcripts, "event_count": len(events), "debug": debug_info}
            except Exception as e:
                debug_info['error'] = str(e)
                debug_info['traceback'] = traceback.format_exc()
                return {"error": str(e), "debug": debug_info}

        agent_funcs = {
            "calendar_agent": calendar_agent_func,
            "summary_agent": lambda **kwargs: {"summary": f"Summary for {kwargs['query']}"},
            "jira_agent": lambda **kwargs: {"jira": f"Jira created for {kwargs['query']}"}
        }
        results = {}
        with ThreadPoolExecutor() as executor:
            futures = {executor.submit(a2a_request, agent_funcs[a], {"query": query, "user": user, "date": date}): a for a in agents}
            for future in as_completed(futures):
                agent = futures[future]
                try:
                    results[agent] = future.result()
                except Exception as e:
                    results[agent] = {"error": str(e)}
        return results

# Example usage:
# orchestrator = OrchestratorAgent()
# result = orchestrator.handle_query("Please summarize and create jira", "alice", date="2026-01-09", permissions=["summary", "jira"])
# print(result)
