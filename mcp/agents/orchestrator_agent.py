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
#from mcp.core.a2a_base_agent import A2AMessage, TaskState
from mcp.agents.notification_agent import NotificationAgent
from mcp.agents import langchain_tools as lc_tools
from mcp.agents.tool_adapter import invoke_tool
import os
from mcp.agents.jira_agent import JiraAgent
from mcp.agents.task_manager_agent import TaskManagerAgent
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

    def _invoke_tool(self, tool, full_transcript, mode_val=None):
        # Robust invocation wrapper for LangChain tool-like objects
        try:
            if callable(tool):
                try:
                    return tool(full_transcript, mode=mode_val)
                except TypeError:
                    # Try passing a dict payload
                    return tool({"transcript": full_transcript, "mode": mode_val})
            if hasattr(tool, 'run'):
                try:
                    return tool.run(full_transcript, mode=mode_val)
                except TypeError:
                    return tool.run({"transcript": full_transcript, "mode": mode_val})
            if hasattr(tool, 'func'):
                try:
                    return tool.func(full_transcript, mode=mode_val)
                except TypeError:
                    return tool.func({"transcript": full_transcript, "mode": mode_val})
        except Exception as e:
            raise
        raise TypeError("Tool object is not callable and does not expose run/func")

    def _fetch_calendar_events_and_transcripts(self, start_time=None, end_time=None):
        import datetime
        if start_time is None or end_time is None:
            now = datetime.datetime.utcnow()
            start_time = now - datetime.timedelta(days=37)
            end_time = now + datetime.timedelta(days=1)
        cal = MCPGoogleCalendar(calendar_id="primary")
        fetch_payload = {"start_time": start_time, "end_time": end_time}
        fetch_response = a2a_request(cal.fetch_events, fetch_payload)
        if fetch_response.get("status") == "ok":
            events = fetch_response["result"]
            transcripts = cal.get_transcripts_from_events(events)
        else:
            print(f"[ERROR] Calendar fetch failed: {fetch_response.get('error')}")
            events = []
            transcripts = []
        return events, transcripts

    @a2a_endpoint
    def handle_query(self, query: Any, selected_event_indices: list = None, mode: str = None, user: str = None, date: str = None, permissions: list = None, create_jira: bool = False, stage: str = "fetch", processed_transcripts: list = None, selected_action_items: list = None, event: dict = None) -> dict:
        """
        Interactive, stepwise workflow for orchestrator:
        stage: 'fetch' | 'preprocess' | 'summarize' | 'jira' | 'risk' | 'notify'
        """
        print(f"[DEBUG] OrchestratorAgent.handle_query called with:")
        print(f"        stage: {stage}")
        print(f"        mode: {mode}")
        print(f"        create_jira: {create_jira}")
        print(f"        user: {user}")
        print(f"        date: {date}")
        print(f"        permissions: {permissions}")
        print(f"        selected_event_indices: {selected_event_indices}")
        processed_transcripts_str = str(processed_transcripts)
        print(f"        processed_transcripts: {processed_transcripts_str[:100]}{'...' if len(processed_transcripts_str) > 100 else ''}")
        print(f"        query: {query}")
        # mode = "bart"  # Force BART mode regardless of input
        result = {"stage": stage}
        # If selected_action_items is provided, merge it into query dict for downstream access
        if selected_action_items is not None:
            if not isinstance(query, dict):
                query = {"query": query}
            query["selected_action_items"] = selected_action_items
        # If a single event is provided (for single-event processing), override event selection logic
        single_event = None
        single_transcript = None
        if (isinstance(query, dict) and 'event' in query and query['event'] is not None):
            single_event = query['event']
        elif event is not None:
            single_event = event
        # If we have a single event, try to get its transcript
        if single_event is not None:
            cal = MCPGoogleCalendar(calendar_id="primary")
            # get_transcripts_from_events expects a list
            single_transcript_list = cal.get_transcripts_from_events([single_event])
            if single_transcript_list:
                single_transcript = single_transcript_list[0]
        try:
            # Optionally run the LangGraph workflow when enabled.
            use_workflow_env = os.environ.get("USE_LANGGRAPH_WORKFLOW")
            if use_workflow_env == "1" and stage in ("fetch", "preprocess", "summarize", "jira", "risk", "notify"):
                print("[DEBUG] LangGraph workflow enabled. Attempting workflow execution...")
                try:
                    from mcp.agents.meeting_workflow_graph import workflow, MeetingState
                    init_state = MeetingState(user_id=user, date_range=None, transcript=None, mode=mode)
                    print(f"[DEBUG] Initial workflow state: {init_state}")
                    wf_state = None
                    invoke_err = None
                    try:
                        if hasattr(workflow, 'run'):
                            wf_state = workflow.run(init_state)
                        elif hasattr(workflow, 'execute'):
                            wf_state = workflow.execute(init_state)
                        elif hasattr(workflow, 'start'):
                            wf_state = workflow.start(init_state)
                        elif callable(workflow):
                            wf_state = workflow(init_state)
                        else:
                            raise AttributeError('No runnable entrypoint found on StateGraph')
                    except Exception as ie:
                        invoke_err = ie
                    if wf_state is None:
                        raise invoke_err or RuntimeError('Workflow invocation returned no state')
                    print(f"[DEBUG] Workflow state after execution: {wf_state}")
                    def _get(s, attr, default=None):
                        try:
                            if isinstance(s, dict):
                                return s.get(attr, default)
                            return getattr(s, attr, default)
                        except Exception:
                            return default
                    result['calendar_events'] = _get(wf_state, 'events', []) or []
                    transcript_val = _get(wf_state, 'transcript', None)
                    if transcript_val:
                        result['calendar_transcripts'] = [transcript_val]
                    else:
                        result['calendar_transcripts'] = _get(wf_state, 'transcripts', []) or []
                    summary_val = _get(wf_state, 'summary', None)
                    result['summaries'] = [summary_val] if summary_val else []
                    result['action_items'] = _get(wf_state, 'action_items', []) or []
                    result['risk'] = _get(wf_state, 'risks', []) or []
                    result['jira'] = _get(wf_state, 'tasks', []) or []
                    result['notification'] = _get(wf_state, 'notification', None)
                    result['stage'] = 'workflow'
                    print(f"[DEBUG] Workflow result: {result}")
                    return result
                except Exception as e:
                    print(f"[WARN] LangGraph workflow failed: {e}")


            if stage == "fetch":
                print("[DEBUG] Stage: fetch (A2A uniform)")
                # If single_event is provided, return only that event and its transcript
                if single_event is not None:
                    events = [single_event]
                    transcripts = [single_transcript] if single_transcript else []
                else:
                    events, transcripts = self._fetch_calendar_events_and_transcripts()
                print(f"[DEBUG] Events fetched: {len(events)}; Transcripts fetched: {len(transcripts)}")
                result['calendar_events'] = events
                result['calendar_transcripts'] = transcripts
                result['event_count'] = len(events)
                result['transcript_count'] = len(transcripts)
                result['next_actions'] = ["preprocess"]
                return result

            if stage == "preprocess":
                print("[DEBUG] Stage: preprocess (A2A uniform)")
                # If single_event is provided, process only that event
                print(f"[DEBUG] single_event: {str(single_event)[:100]}{'...' if single_event and len(str(single_event)) > 100 else ''}")
                if single_event is not None:
                    selected_events = [single_event]
                    selected_transcripts = [single_transcript] if single_transcript else []
                    print(f"[DEBUG] PREPROCESS: Received single_event from frontend: id={getattr(single_event, 'get', lambda x: single_event.get(x, None))('id') if isinstance(single_event, dict) else str(single_event)[:50]}, transcript_snippet={str(single_transcript)[:100]}")
                else:
                    cal_events = []
                    cal_transcripts = []
                    if 'calendar_events' in query and 'calendar_transcripts' in query:
                        cal_events = query['calendar_events']
                        cal_transcripts = query['calendar_transcripts']
                    else:
                        # Fallback: fetch again using helper
                        cal_events, cal_transcripts = self._fetch_calendar_events_and_transcripts()
                    if selected_event_indices is not None and isinstance(selected_event_indices, list) and selected_event_indices:
                        selected_events = [cal_events[i] for i in selected_event_indices if 0 <= i < len(cal_events)]
                        selected_transcripts = [cal_transcripts[i] for i in selected_event_indices if 0 <= i < len(cal_transcripts)]
                    else:
                        selected_events = cal_events
                        selected_transcripts = cal_transcripts
                result['selected_events'] = selected_events
                result['selected_transcripts'] = selected_transcripts
                result['transcript_chunks'] = selected_transcripts                              
                preproc = TranscriptPreprocessingAgent()
                preproc_payload = {"transcripts": selected_transcripts}
                preproc_response = a2a_request(preproc.process, preproc_payload)
                preproc_response_str = str(preproc_response)
                print(f"[DEBUG] Preprocessing response: {preproc_response_str[:100]}{'...' if len(preproc_response_str) > 100 else ''}")
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
                print(f"[DEBUG] Stage: summarize")
                processed_transcripts_str = str(processed_transcripts)
                print(f"[DEBUG] processed_transcripts arg: {processed_transcripts_str[:100]}{'...' if len(processed_transcripts_str) > 100 else ''}")
                # Determine transcripts to summarize, with fallbacks
                print(f"[DEBUG] transcripts_to_summarize (before): {processed_transcripts_str[:100]}{'...' if len(processed_transcripts_str) > 100 else ''}")
                if processed_transcripts is not None:
                    transcripts_to_summarize = processed_transcripts
                else:
                    if isinstance(query, dict):
                        transcripts_to_summarize = query.get('processed_transcripts') or query.get('calendar_transcripts') or []
                    else:
                        transcripts_to_summarize = []

                # If still empty, attempt to fetch calendar transcripts as a last resort using helper
                transcripts_str = str(transcripts_to_summarize)
                print(f"[DEBUG] transcripts_to_summarize (after fallback): {transcripts_str[:100]}{'...' if len(transcripts_str) > 100 else ''}")
                if not transcripts_to_summarize:
                    try:
                        _, transcripts_to_summarize = self._fetch_calendar_events_and_transcripts()
                    except Exception as e:
                        print(f"[WARN] Failed to fetch calendar transcripts as fallback: {e}")

                if not transcripts_to_summarize:
                    result['error'] = "No transcripts available to summarize. Please fetch and preprocess events first."
                    return result

                # Prefer LangChain summarize tool by default when available; env var can disable
                use_lc_env = os.environ.get("USE_LANGCHAIN_TOOLS")
                if use_lc_env is None:
                    use_lc = hasattr(lc_tools, 'summarize_meeting')
                else:
                    use_lc = use_lc_env == "1"

                summaries = []

                def _invoke_tool(tool, full_transcript, mode_val=None):
                    # Robust invocation wrapper for LangChain tool-like objects
                    try:
                        if callable(tool):
                            try:
                                return tool(full_transcript, mode=mode_val)
                            except TypeError:
                                # Try passing a dict payload
                                return tool({"transcript": full_transcript, "mode": mode_val})
                        if hasattr(tool, 'run'):
                            try:
                                return tool.run(full_transcript, mode=mode_val)
                            except TypeError:
                                return tool.run({"transcript": full_transcript, "mode": mode_val})
                        if hasattr(tool, 'func'):
                            try:
                                return tool.func(full_transcript, mode=mode_val)
                            except TypeError:
                                return tool.func({"transcript": full_transcript, "mode": mode_val})
                    except Exception as e:
                        raise
                    raise TypeError("Tool object is not callable and does not expose run/func")

                # Prefer calling LangChain summarize tool when enabled
                print(f"[DEBUG] use_lc: {use_lc}")
                if use_lc and hasattr(lc_tools, 'summarize_meeting'):
                    try:
                        print("[DEBUG] Invoking LangChain summarize_meeting tool...")
                        full_transcript = "\n".join(transcripts_to_summarize)
                        tool = lc_tools.summarize_meeting
                        inv = invoke_tool(tool, payload={"transcript": full_transcript, "mode": mode}, mode=mode)
                        inv_str = str(inv)
                        print(f"[DEBUG] summarize_meeting result: {inv_str[:200]}{'...' if len(inv_str) > 200 else ''}")
                        if inv.get('status') != 'ok':
                            raise RuntimeError(inv.get('error'))
                        res = inv.get('result')

                        # Normalize response
                        if isinstance(res, dict):
                            summaries = [res.get('summary', '')] if res.get('summary') else ([res.get('summaries')] if res.get('summaries') else [])
                            action_items = res.get('action_items', [])
                            if action_items:
                                result['action_items'] = action_items
                        elif isinstance(res, str):
                            summaries = [res]
                        else:
                            try:
                                summaries = [str(res)]
                            except Exception:
                                summaries = []
                    except Exception as e:
                        print(f"[WARN] LangChain summarizer failed: {e}")
                        summaries = []
                else:
                    # Protocol-compliant invocation of SummarizationAgent using a2a_request
                    summarizer = SummarizationAgent(mode=mode)
                    summarize_payload = {"processed_transcripts": transcripts_to_summarize, "mode": mode}
                    summarize_response = a2a_request(summarizer.summarize_protocol, summarize_payload)
                    if summarize_response.get("status") == "ok":
                        summary_result = summarize_response["result"]
                        if isinstance(summary_result, dict):
                            if summary_result.get('summary'):
                                summaries.append(summary_result['summary'])
                            if summary_result.get('action_items'):
                                result['action_items'] = summary_result['action_items']
                            if summary_result.get('download_link'):
                                result['download_link'] = summary_result['download_link']
                        else:
                            # fallback for legacy A2AMessage
                            if hasattr(summary_result, 'parts'):
                                for part in summary_result.parts:
                                    if getattr(part, 'content_type', None) == "text/plain":
                                        summaries.append(part.content)
                    else:
                        print(f"[ERROR] SummarizationAgent failed: {summarize_response.get('error')}")

                summaries_str = str(summaries)
                print(f"[DEBUG] Summaries: {summaries_str[:100]}{'...' if len(summaries_str) > 100 else ''}")
                result['summaries'] = summaries
                result['summary_count'] = len(summaries)
                result['next_actions'] = ["jira", "risk"]
                result_str = str(result)
                print(f"[DEBUG] Summarize result: {result_str[:200]}{'...' if len(result_str) > 200 else ''}")
                return result

            if stage == "jira":
                print("[DEBUG] Stage: jira")
                # Use selected_action_items if present, else fallback to summaries
                selected_action_items = None
                if isinstance(query, dict):
                    selected_action_items = query.get('selected_action_items', None)
                if selected_action_items:
                    summaries = selected_action_items
                    print(f"[DEBUG] Using selected_action_items for Jira: {summaries}")
                else:
                    summaries = query.get('summaries', []) if isinstance(query, dict) else []
                    print(f"[DEBUG] Summaries for jira: {summaries}")
                
                jira_agent = JiraAgent()
                jira_payload = {"summary": summaries, "user": user, "date": date}
                print(f"[DEBUG] Jira payload: {jira_payload}")
                jira_response = a2a_request(jira_agent.create_jira, jira_payload)
                created_tasks = []
                if jira_response.get("status") == "ok":
                    jira_result = jira_response["result"]
                    if hasattr(jira_result, 'parts'):
                        for part in jira_result.parts:
                            if getattr(part, 'content_type', None) == "application/json":
                                created_tasks = part.content.get('created_tasks', [])
                    elif isinstance(jira_result, dict):
                        created_tasks = jira_result.get('created_tasks', [])
                else:
                    print(f"[ERROR] JiraAgent failed: {jira_response.get('error')}")
                created_tasks_str = str(created_tasks)
                print(f"[DEBUG] Jira created tasks: {created_tasks_str[:100]}{'...' if len(created_tasks_str) > 100 else ''}")
                result['jira'] = [created_tasks]
                result['next_actions'] = ["risk"]
                result_str = str(result)
                print(f"[DEBUG] Jira result: {result_str[:100]}{'...' if len(result_str) > 100 else ''}")
                return result

            if stage == "risk":
                print("[DEBUG] Stage: risk")
                summaries = query.get('summaries', []) if isinstance(query, dict) else []
                created_tasks = query.get('jira', [{}])[0] if isinstance(query, dict) and 'jira' in query else []
                summary_for_risk = summaries[0] if summaries else ""
                tasks_for_risk = created_tasks.get('created_tasks', []) if isinstance(created_tasks, dict) else []
                print(f"[DEBUG] Summaries for risk: {summaries}")
                print(f"[DEBUG] Tasks for risk: {tasks_for_risk}")
                # Prefer LangChain risk tool if available (default ON when tool exists)
                use_lc_env = os.environ.get("USE_LANGCHAIN_TOOLS")
                if use_lc_env is None:
                    use_lc = hasattr(lc_tools, 'detect_risks_tool')
                else:
                    use_lc = use_lc_env == "1"
                detected_risks = []
                print(f"[DEBUG] use_lc: {use_lc}")
                if use_lc and hasattr(lc_tools, 'detect_risks_tool'):
                    try:
                        print("[DEBUG] Invoking LangChain detect_risks_tool...")
                        inv = invoke_tool(lc_tools.detect_risks_tool, payload={"summary": summary_for_risk})
                        print(f"[DEBUG] detect_risks_tool result: {inv}")
                        if inv.get('status') == 'ok':
                            res = inv.get('result')
                            detected_risks = res.get('risks', [])
                        else:
                            raise RuntimeError(inv.get('error'))
                    except Exception as e:
                        print(f"[WARN] LangChain risk tool failed: {e}")
                if not detected_risks:
                    risk_agent = RiskDetectionAgent()
                    risk_payload = {"meeting_id": date or "meeting", "summary": {"summary_text": summary_for_risk}, "tasks": tasks_for_risk, "progress": {}}
                    risk_response = a2a_request(risk_agent.detect, risk_payload)
                    if risk_response.get("status") == "ok":
                        detected_risks = risk_response["result"]
                    else:
                        print(f"[ERROR] RiskDetectionAgent failed: {risk_response.get('error')}")

                # --- Jira-based risk detection ---
                try:
                    # Import inside the function to avoid circular import
                    
                    tm_agent = TaskManagerAgent()
                    jira_risks = tm_agent.detect_jira_risks()
                    print(f"[DEBUG] Jira-based risks: {jira_risks}")
                except Exception as e:
                    print(f"[WARN] Jira-based risk detection failed: {e}")
                    jira_risks = []

                # Combine both types of risks
                result['risk'] = [
                    {"parts": [
                        {"content_type": "application/json", "content": {"detected_risks": detected_risks}},
                        {"content_type": "application/json", "content": {"jira_risks": jira_risks}}
                    ]}
                ]
                result['next_actions'] = ["notify"]
                print(f"[DEBUG] Risk result: {result}")
                return result

            if stage == "notify":
                print("[DEBUG] Stage: notify")
                summaries = query.get('summaries', []) if isinstance(query, dict) else []
                created_tasks = query.get('jira', [{}])[0] if isinstance(query, dict) and 'jira' in query else []
                risks = query.get('risk', [{}])[0] if isinstance(query, dict) and 'risk' in query else []
                summary_for_notify = summaries[0] if summaries else ""
                tasks_for_notify = created_tasks.get('created_tasks', []) if isinstance(created_tasks, dict) else []
                detected_risks = risks.get('parts', [{}])[0].get('content', {}).get('detected_risks', []) if isinstance(risks, dict) else []
                print(f"[DEBUG] Summaries for notify: {summaries}")
                print(f"[DEBUG] Tasks for notify: {tasks_for_notify}")
                print(f"[DEBUG] Detected risks for notify: {detected_risks}")
                # Prefer LangChain notification tool if available (default ON when tool exists)
                use_lc_env = os.environ.get("USE_LANGCHAIN_TOOLS")
                if use_lc_env is None:
                    use_lc = hasattr(lc_tools, 'send_notification_tool')
                else:
                    use_lc = use_lc_env == "1"
                print(f"[DEBUG] use_lc: {use_lc}")
                if use_lc and hasattr(lc_tools, 'send_notification_tool'):
                    try:
                        print("[DEBUG] Invoking LangChain send_notification_tool...")
                        inv = invoke_tool(lc_tools.send_notification_tool, payload={"task": str(tasks_for_notify[:1]), "user": user})
                        print(f"[DEBUG] send_notification_tool result: {inv}")
                        if inv.get('status') == 'ok':
                            result['notified'] = True
                        else:
                            raise RuntimeError(inv.get('error'))
                    except Exception as e:
                        print(f"[WARN] LangChain notification tool failed: {e}")
                        notification_agent = NotificationAgent()
                        notification_agent.notify(
                            meeting_id=date or "meeting",
                            summary={"summary_text": summary_for_notify},
                            tasks=tasks_for_notify,
                            risks=detected_risks
                        )
                        result['notified'] = True
                    result['next_actions'] = []
                    print(f"[DEBUG] Notify result: {result}")
                    return result
                else:
                    notification_agent = NotificationAgent()
                    notify_payload = {
                        "meeting_id": date or "meeting",
                        "summary": {"summary_text": summary_for_notify},
                        "tasks": tasks_for_notify,
                        "risks": detected_risks
                    }
                    notify_response = a2a_request(notification_agent.notify, notify_payload)
                    if notify_response.get("status") == "ok":
                        result['notified'] = True
                    else:
                        print(f"[ERROR] NotificationAgent failed: {notify_response.get('error')}")
                        result['notified'] = False
                    result['next_actions'] = []
                    print(f"[DEBUG] Notify result: {result}")
                    return result

            # --- Custom: Map user query to specific field and return only that field if requested ---
            # Only do this for 'fetch' and 'summarize' stages (where result has summaries, action_items, etc.)
            try:
                if stage in ("fetch", "summarize") and isinstance(query, str):
                    field_map = {
                        "decision": "decisions",
                        "decisions": "decisions",
                        "action item": "action_items",
                        "action items": "action_items",
                        "risk": "risks",
                        "risks": "risks",
                        "concern": "concerns",
                        "concerns": "concerns",
                        "follow up": "follow_up_questions",
                        "follow-up": "follow_up_questions",
                        "question": "follow_up_questions",
                        "summary": "summaries",
                    }
                    for key, field in field_map.items():
                        if key in query.lower():
                            # Try to get the field from result or from the first summary dict
                            value = result.get(field)
                            if value is None and result.get('summaries') and isinstance(result['summaries'], list):
                                # Try to get from the first summary dict if present
                                first = result['summaries'][0]
                                if isinstance(first, dict):
                                    value = first.get(field)
                            # If still None, fallback to empty list
                            if value is None:
                                value = []
                            # Return only the requested field
                            return {field: value, 'stage': stage}
            except Exception as e:
                print(f"[ERROR] Exception in query-to-field mapping: {e}")
            print(f"[DEBUG] Unknown stage encountered: {stage}")
            result['error'] = f"Unknown stage: {stage}"
            print(f"[DEBUG] Error result: {result}")
            return result
        except Exception as e:
            print(f"[ERROR] Exception in handle_query: {e}")
            result['error'] = str(e)
            print(f"[DEBUG] Exception result: {result}")
            return result

