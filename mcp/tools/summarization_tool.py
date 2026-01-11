from mcp.core.mcp import MCPTool, MCPToolType
from mcp.agents.summarization_agent import SummarizationAgent
import asyncio

class SummarizationTool(MCPTool):
    def __init__(self, mode="auto"):
        super().__init__(
            tool_id="summarization",
            tool_type=MCPToolType.SUMMARIZATION,
            name="Meeting Summarizer",
            description="Summarizes meeting transcripts into concise bullet points and action items.",
            api_endpoint="/mcp/summarize",
            auth_required=False,
            parameters={"transcript": "str", "mode": "str"}
        )
        self.mode = mode
        self.agent = SummarizationAgent(mode=mode)

    async def execute(self, params):
        transcript = params.get("transcript", "")
        meeting_id = params.get("meeting_id", "mcp_demo")
        mode = params.get("mode", self.mode)
        if mode != self.mode:
            self.agent = SummarizationAgent(mode=mode)
            self.mode = mode
        summary_obj = await self.agent.summarize(meeting_id, transcript)
        # Fallback: If action_items is missing or empty, try to extract from summary_text
        if not summary_obj.get('action_items'):
            print("[DEBUG][SummarizationTool] No action_items in summary_obj, attempting fallback extraction from summary_text.")
            summary_text = summary_obj.get('summary_text', [])
            if isinstance(summary_text, str):
                lines = [summary_text]
            else:
                lines = summary_text
            action_keywords = ['fix', 'complete', 'implement', 'create', 'update', 'assign', 'test', 'review', 'prepare', 'set up', 'ensure', 'action item', 'task']
            fallback_action_items = [l for l in lines if any(k in l.lower() for k in action_keywords)]
            summary_obj['action_items'] = fallback_action_items
            print(f"[DEBUG][SummarizationTool] Fallback extracted action_items: {fallback_action_items}")
        return {
            "status": "success",
            "summary": summary_obj.get("summary_text", summary_obj),
            "action_items": summary_obj.get("action_items", [])
        }
