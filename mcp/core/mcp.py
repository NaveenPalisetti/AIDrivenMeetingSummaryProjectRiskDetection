import uuid
import logging
import datetime
from enum import Enum
from typing import Dict, List, Any
from dataclasses import dataclass, field

logger = logging.getLogger("meeting-mcp")

class MCPToolType(Enum):
    SUMMARIZATION = "summarization"
    TASK_MANAGER = "task_manager"
    RISK_DETECTION = "risk_detection"
    NOTIFICATION = "notification"
    OTHER = "other"

@dataclass
class MCPTool:
    tool_id: str
    tool_type: MCPToolType
    name: str
    description: str
    api_endpoint: str
    auth_required: bool = True
    parameters: Dict[str, Any] = field(default_factory=dict)

    async def execute(self, params: Dict[str, Any] = None) -> Dict[str, Any]:
        logger.info(f"Executing MCP tool: {self.name}")
        return {
            "status": "error",
            "message": "Tool execution not implemented in base class"
        }

class MCPHost:
    def __init__(self):
        self.tools: Dict[str, MCPTool] = {}
        self.sessions: Dict[str, Dict[str, Any]] = {}
        logger.info("MCP Host initialized")
        print("[DEBUG] MCPHost initialized")

    def register_tool(self, tool: MCPTool):
        print(f"[DEBUG] MCPHost.register_tool called for: {tool.name} ({tool.tool_id})")
        self.tools[tool.tool_id] = tool
        logger.info(f"Tool registered: {tool.name} ({tool.tool_id})")

    def create_session(self, agent_id: str) -> str:
        print(f"[DEBUG] MCPHost.create_session called for agent: {agent_id}")
        session_id = str(uuid.uuid4())
        self.sessions[session_id] = {
            "agent_id": agent_id,
            "created_at": datetime.datetime.now().isoformat(),
            "active": True,
            "context": {}
        }
        logger.info(f"Session created for agent {agent_id}: {session_id}")
        print(f"[DEBUG] MCPHost session created: {session_id}")
        return session_id

    async def execute_tool(self, session_id: str, tool_id: str, parameters: Dict[str, Any] = None) -> Dict[str, Any]:
        print(f"[DEBUG] MCPHost.execute_tool called: session_id={session_id}, tool_id={tool_id}, parameters={parameters}")
        if session_id not in self.sessions:
            logger.error(f"Invalid session ID: {session_id}")
            print(f"[DEBUG] MCPHost.execute_tool: Invalid session ID {session_id}")
            return {"status": "error", "message": "Invalid session ID"}
        if not self.sessions[session_id]["active"]:
            logger.error(f"Session {session_id} is not active")
            print(f"[DEBUG] MCPHost.execute_tool: Session {session_id} is not active")
            return {"status": "error", "message": "Session is not active"}
        if tool_id not in self.tools:
            logger.error(f"Tool not found: {tool_id}")
            print(f"[DEBUG] MCPHost.execute_tool: Tool not found {tool_id}")
            return {"status": "error", "message": "Tool not found"}
        tool = self.tools[tool_id]
        try:
            result = await tool.execute(parameters or {})
            logger.info(f"Tool {tool.name} executed successfully via MCP")
            print(f"[DEBUG] MCPHost.execute_tool: Tool {tool.name} executed successfully")
            return result
        except Exception as e:
            logger.error(f"Error executing tool {tool.name}: {str(e)}")
            print(f"[DEBUG] MCPHost.execute_tool: Error executing tool {tool.name}: {str(e)}")
            return {"status": "error", "message": str(e)}

    def get_available_tools(self, session_id: str) -> List[Dict[str, Any]]:
        print(f"[DEBUG] MCPHost.get_available_tools called: session_id={session_id}")
        if session_id not in self.sessions:
            logger.error(f"Invalid session ID: {session_id}")
            print(f"[DEBUG] MCPHost.get_available_tools: Invalid session ID {session_id}")
            return []
        if not self.sessions[session_id]["active"]:
            logger.error(f"Session {session_id} is not active")
            print(f"[DEBUG] MCPHost.get_available_tools: Session {session_id} is not active")
            return []
        return [
            {
                "tool_id": tool.tool_id,
                "name": tool.name,
                "description": tool.description,
                "tool_type": tool.tool_type.value,
                "parameters": tool.parameters
            }
            for tool in self.tools.values()
        ]

    def end_session(self, session_id: str) -> bool:
        print(f"[DEBUG] MCPHost.end_session called: session_id={session_id}")
        if session_id not in self.sessions:
            logger.error(f"Invalid session ID: {session_id}")
            print(f"[DEBUG] MCPHost.end_session: Invalid session ID {session_id}")
            return False
        self.sessions[session_id]["active"] = False
        logger.info(f"Session ended: {session_id}")
        print(f"[DEBUG] MCPHost session ended: {session_id}")
        return True

