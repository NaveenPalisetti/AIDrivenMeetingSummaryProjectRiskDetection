from typing import Dict, Any, Optional, List
import uuid
import logging
from dataclasses import dataclass, field

# AgentCard and Capability
@dataclass
class AgentCapability:
    name: str
    description: str
    parameters: Dict[str, Any] = field(default_factory=dict)

@dataclass
class AgentCard:
    agent_id: str
    name: str
    description: str
    version: str
    base_url: str = ""
    capabilities: List[AgentCapability] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "base_url": self.base_url,
            "capabilities": [cap.__dict__ for cap in self.capabilities]
        }

# Task State Enum
class TaskState:
    SUBMITTED = "submitted"
    WORKING = "working"
    COMPLETED = "completed"
    FAILED = "failed"

# Message Part
@dataclass
class MessagePart:
    part_id: str
    content_type: str
    content: Any

    def to_dict(self) -> Dict[str, Any]:
        return {
            "part_id": self.part_id,
            "content_type": self.content_type,
            "content": self.content
        }

# A2AMessage
@dataclass
class A2AMessage:
    message_id: str
    role: str
    parts: List[MessagePart] = field(default_factory=list)

    def add_part(self, content_type: str, content: Any) -> str:
        part_id = str(uuid.uuid4())
        self.parts.append(MessagePart(part_id, content_type, content))
        return part_id

    def to_dict(self) -> Dict[str, Any]:
        return {
            "message_id": self.message_id,
            "role": self.role,
            "parts": [part.to_dict() for part in self.parts]
        }

# A2ATask
@dataclass
class A2ATask:
    task_id: str
    state: str
    messages: List[A2AMessage] = field(default_factory=list)

    def update_state(self, new_state: str):
        self.state = new_state

    def add_message(self, message: A2AMessage):
        self.messages.append(message)

# Base Agent
class A2AAgent:
    def __init__(self, agent_card: AgentCard):
        self.agent_card = agent_card
        self.tasks: Dict[str, A2ATask] = {}
        logging.info(f"Agent initialized: {agent_card.name} ({agent_card.agent_id})")

    def get_agent_card(self) -> Dict[str, Any]:
        return self.agent_card.to_dict()

    def create_task(self, initial_message: A2AMessage) -> str:
        task_id = str(uuid.uuid4())
        task = A2ATask(task_id=task_id, state=TaskState.SUBMITTED, messages=[initial_message])
        self.tasks[task_id] = task
        logging.info(f"Task created: {task_id}")
        return task_id

    def update_task(self, task_id: str, message: A2AMessage, new_state: Optional[str] = None):
        task = self.tasks.get(task_id)
        if task:
            task.add_message(message)
            if new_state:
                task.update_state(new_state)
