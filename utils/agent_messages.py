"""
Agent Message Types and Communication Protocol

This module defines the message types and communication protocol used
between agents in the LazyToCode multi-agent system.
"""

from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from enum import Enum
import json


class MessageType(Enum):
    """Types of messages that can be sent between agents."""
    PLAN_REQUEST = "plan_request"
    PLAN_RESPONSE = "plan_response"
    WRITE_REQUEST = "write_request"
    WRITE_RESPONSE = "write_response"
    TEST_REQUEST = "test_request"
    TEST_RESPONSE = "test_response"
    FIX_REQUEST = "fix_request"
    FIX_RESPONSE = "fix_response"
    STATUS_UPDATE = "status_update"
    ERROR_REPORT = "error_report"


class AgentStatus(Enum):
    """Status of an agent."""
    IDLE = "idle"
    WORKING = "working"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class AgentMessage:
    """Base message class for inter-agent communication."""
    message_type: MessageType
    sender: str
    recipient: str
    payload: Dict[str, Any]
    phase_id: str
    timestamp: datetime
    correlation_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary for serialization."""
        data = asdict(self)
        data['message_type'] = self.message_type.value
        data['timestamp'] = self.timestamp.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AgentMessage':
        """Create message from dictionary."""
        data['message_type'] = MessageType(data['message_type'])
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        return cls(**data)
    
    def to_json(self) -> str:
        """Convert message to JSON string."""
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_json(cls, json_str: str) -> 'AgentMessage':
        """Create message from JSON string."""
        return cls.from_dict(json.loads(json_str))


@dataclass
class ProjectInfo:
    """Information about a project to be generated."""
    prompt: str
    project_type: str
    language: str = "python"
    output_dir: str = "./output"
    requirements: List[str] = None
    
    def __post_init__(self):
        if self.requirements is None:
            self.requirements = []


@dataclass
class Phase:
    """Represents a phase in the project implementation."""
    phase_id: str
    name: str
    description: str
    files_to_create: List[str]
    dependencies: List[str]
    estimated_complexity: int  # 1-5 scale
    prerequisites: List[str] = None
    
    def __post_init__(self):
        if self.prerequisites is None:
            self.prerequisites = []


@dataclass
class ProjectPlan:
    """Complete project implementation plan."""
    project_info: ProjectInfo
    phases: List[Phase]
    total_phases: int
    estimated_duration: int  # in minutes
    
    def __post_init__(self):
        self.total_phases = len(self.phases)


@dataclass
class FileContent:
    """Content of a generated file."""
    filename: str
    content: str
    file_type: str
    language: str = "python"


@dataclass
class ProjectFiles:
    """Collection of generated project files."""
    files: List[FileContent]
    phase_id: str
    dependencies: List[str] = None
    
    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []


@dataclass
class TestResult:
    """Result of testing a project."""
    success: bool
    phase_id: str
    test_type: str
    output: str
    errors: List[str] = None
    warnings: List[str] = None
    duration: float = 0.0  # in seconds
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []


@dataclass
class FileError:
    """Represents an error in a specific file."""
    filename: str
    error_type: str
    error_message: str
    line_number: Optional[int] = None
    severity: str = "error"  # error, warning, info


@dataclass
class FixPlan:
    """Plan for fixing errors in a project."""
    phase_id: str
    files_to_modify: List[str]
    dependencies_to_add: List[str]
    files_to_create: List[str]
    fix_description: str
    estimated_complexity: int  # 1-5 scale
    errors_addressed: List[FileError] = None
    
    def __post_init__(self):
        if self.errors_addressed is None:
            self.errors_addressed = []


# Message Factory Functions

def create_plan_request(sender: str, recipient: str, project_info: ProjectInfo, 
                       phase_id: str, correlation_id: Optional[str] = None) -> AgentMessage:
    """Create a plan request message."""
    return AgentMessage(
        message_type=MessageType.PLAN_REQUEST,
        sender=sender,
        recipient=recipient,
        payload={"project_info": asdict(project_info)},
        phase_id=phase_id,
        timestamp=datetime.now(),
        correlation_id=correlation_id
    )


def create_plan_response(sender: str, recipient: str, project_plan: ProjectPlan,
                        phase_id: str, correlation_id: Optional[str] = None) -> AgentMessage:
    """Create a plan response message."""
    return AgentMessage(
        message_type=MessageType.PLAN_RESPONSE,
        sender=sender,
        recipient=recipient,
        payload={"project_plan": asdict(project_plan)},
        phase_id=phase_id,
        timestamp=datetime.now(),
        correlation_id=correlation_id
    )


def create_write_request(sender: str, recipient: str, phase: Phase, project_info: ProjectInfo,
                        phase_id: str, correlation_id: Optional[str] = None) -> AgentMessage:
    """Create a write request message."""
    return AgentMessage(
        message_type=MessageType.WRITE_REQUEST,
        sender=sender,
        recipient=recipient,
        payload={
            "phase": asdict(phase),
            "project_info": asdict(project_info)
        },
        phase_id=phase_id,
        timestamp=datetime.now(),
        correlation_id=correlation_id
    )


def create_write_response(sender: str, recipient: str, project_files: ProjectFiles,
                         phase_id: str, correlation_id: Optional[str] = None) -> AgentMessage:
    """Create a write response message."""
    return AgentMessage(
        message_type=MessageType.WRITE_RESPONSE,
        sender=sender,
        recipient=recipient,
        payload={"project_files": asdict(project_files)},
        phase_id=phase_id,
        timestamp=datetime.now(),
        correlation_id=correlation_id
    )


def create_test_request(sender: str, recipient: str, project_files: ProjectFiles,
                       phase_id: str, correlation_id: Optional[str] = None) -> AgentMessage:
    """Create a test request message."""
    return AgentMessage(
        message_type=MessageType.TEST_REQUEST,
        sender=sender,
        recipient=recipient,
        payload={"project_files": asdict(project_files)},
        phase_id=phase_id,
        timestamp=datetime.now(),
        correlation_id=correlation_id
    )


def create_test_response(sender: str, recipient: str, test_result: TestResult,
                        phase_id: str, correlation_id: Optional[str] = None) -> AgentMessage:
    """Create a test response message."""
    return AgentMessage(
        message_type=MessageType.TEST_RESPONSE,
        sender=sender,
        recipient=recipient,
        payload={"test_result": asdict(test_result)},
        phase_id=phase_id,
        timestamp=datetime.now(),
        correlation_id=correlation_id
    )


def create_fix_request(sender: str, recipient: str, test_result: TestResult,
                      phase_id: str, correlation_id: Optional[str] = None) -> AgentMessage:
    """Create a fix request message."""
    return AgentMessage(
        message_type=MessageType.FIX_REQUEST,
        sender=sender,
        recipient=recipient,
        payload={"test_result": asdict(test_result)},
        phase_id=phase_id,
        timestamp=datetime.now(),
        correlation_id=correlation_id
    )


def create_fix_response(sender: str, recipient: str, fix_plan: FixPlan,
                       phase_id: str, correlation_id: Optional[str] = None) -> AgentMessage:
    """Create a fix response message."""
    return AgentMessage(
        message_type=MessageType.FIX_RESPONSE,
        sender=sender,
        recipient=recipient,
        payload={"fix_plan": asdict(fix_plan)},
        phase_id=phase_id,
        timestamp=datetime.now(),
        correlation_id=correlation_id
    )


def create_status_update(sender: str, recipient: str, status: AgentStatus, 
                        message: str, phase_id: str, 
                        correlation_id: Optional[str] = None) -> AgentMessage:
    """Create a status update message."""
    return AgentMessage(
        message_type=MessageType.STATUS_UPDATE,
        sender=sender,
        recipient=recipient,
        payload={
            "status": status.value,
            "message": message
        },
        phase_id=phase_id,
        timestamp=datetime.now(),
        correlation_id=correlation_id
    )


def create_error_report(sender: str, recipient: str, error: str, error_type: str,
                       phase_id: str, correlation_id: Optional[str] = None) -> AgentMessage:
    """Create an error report message."""
    return AgentMessage(
        message_type=MessageType.ERROR_REPORT,
        sender=sender,
        recipient=recipient,
        payload={
            "error": error,
            "error_type": error_type
        },
        phase_id=phase_id,
        timestamp=datetime.now(),
        correlation_id=correlation_id
    )