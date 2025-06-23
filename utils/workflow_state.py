"""
Workflow State Management

This module manages the state of the multi-agent workflow, tracking phases,
agent statuses, and overall progress through the project generation process.
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import uuid

from utils.agent_messages import (
    AgentStatus, ProjectInfo, ProjectPlan, Phase, 
    TestResult, FixPlan, ProjectFiles
)
from utils.logger import get_logger


class WorkflowStatus(Enum):
    """Overall workflow status."""
    IDLE = "idle"
    PLANNING = "planning"
    WRITING = "writing"
    REVIEWING = "reviewing"
    TESTING = "testing"
    FIXING = "fixing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PhaseStatus(Enum):
    """Status of individual phases."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"


@dataclass
class PhaseState:
    """State information for a single phase."""
    phase: Phase
    status: PhaseStatus = PhaseStatus.PENDING
    attempt_count: int = 0
    max_attempts: int = 3
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    generated_files: Optional[ProjectFiles] = None
    test_results: List[TestResult] = field(default_factory=list)
    fix_plans: List[FixPlan] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    
    @property
    def duration(self) -> Optional[float]:
        """Get the duration of the phase in seconds."""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None
    
    @property
    def can_retry(self) -> bool:
        """Check if the phase can be retried."""
        return self.attempt_count < self.max_attempts and self.status == PhaseStatus.FAILED


@dataclass
class AgentState:
    """State information for an agent."""
    name: str
    agent_type: str
    status: AgentStatus = AgentStatus.IDLE
    current_phase_id: Optional[str] = None
    message_count: int = 0
    error_count: int = 0
    last_activity: Optional[datetime] = None
    
    def update_activity(self):
        """Update the last activity timestamp."""
        self.last_activity = datetime.now()


class WorkflowState:
    """
    Manages the overall state of the multi-agent workflow.
    This is a session-based state manager (not persisted).
    """
    
    def __init__(self, project_info: ProjectInfo, max_attempts: int = 3):
        """
        Initialize the workflow state.
        
        Args:
            project_info: Information about the project being generated
            max_attempts: Maximum number of attempts per phase
        """
        self.workflow_id = f"workflow_{uuid.uuid4().hex[:12]}"
        self.project_info = project_info
        self.max_attempts = max_attempts
        self.status = WorkflowStatus.IDLE
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        
        # Project plan and phases
        self.project_plan: Optional[ProjectPlan] = None
        self.phases: Dict[str, PhaseState] = {}
        self.current_phase_id: Optional[str] = None
        self.completed_phases: List[str] = []
        
        # Agent states
        self.agents: Dict[str, AgentState] = {}
        
        # Statistics
        self.total_attempts = 0
        self.total_errors = 0
        self.total_files_generated = 0
        
        self.logger = get_logger()
        self.logger.info(f"Workflow state initialized: {self.workflow_id}")
    
    def set_project_plan(self, project_plan: ProjectPlan):
        """Set the project plan and initialize phases."""
        self.project_plan = project_plan
        
        # Initialize phase states
        for phase in project_plan.phases:
            self.phases[phase.phase_id] = PhaseState(
                phase=phase,
                max_attempts=self.max_attempts
            )
        
        self.logger.info(f"Project plan set with {len(project_plan.phases)} phases")
    
    def register_agent(self, name: str, agent_type: str) -> AgentState:
        """Register an agent with the workflow."""
        agent_state = AgentState(name=name, agent_type=agent_type)
        self.agents[name] = agent_state
        self.logger.debug(f"Agent registered: {name} ({agent_type})")
        return agent_state
    
    def update_agent_status(self, agent_name: str, status: AgentStatus, 
                           phase_id: Optional[str] = None):
        """Update an agent's status."""
        if agent_name in self.agents:
            agent = self.agents[agent_name]
            agent.status = status
            agent.current_phase_id = phase_id
            agent.update_activity()
            
            self.logger.debug(f"Agent {agent_name} status updated: {status.value}")
    
    def increment_agent_messages(self, agent_name: str):
        """Increment message count for an agent."""
        if agent_name in self.agents:
            self.agents[agent_name].message_count += 1
            self.agents[agent_name].update_activity()
    
    def increment_agent_errors(self, agent_name: str):
        """Increment error count for an agent."""
        if agent_name in self.agents:
            self.agents[agent_name].error_count += 1
            self.agents[agent_name].update_activity()
            self.total_errors += 1
    
    def start_workflow(self):
        """Start the workflow."""
        self.status = WorkflowStatus.PLANNING
        self.start_time = datetime.now()
        self.logger.info(f"Workflow started: {self.workflow_id}")
    
    def complete_workflow(self, success: bool = True):
        """Complete the workflow."""
        self.status = WorkflowStatus.COMPLETED if success else WorkflowStatus.FAILED
        self.end_time = datetime.now()
        
        status_msg = "completed successfully" if success else "failed"
        self.logger.info(f"Workflow {status_msg}: {self.workflow_id}")
    
    def cancel_workflow(self):
        """Cancel the workflow."""
        self.status = WorkflowStatus.CANCELLED
        self.end_time = datetime.now()
        self.logger.info(f"Workflow cancelled: {self.workflow_id}")
    
    def start_phase(self, phase_id: str) -> bool:
        """Start a phase."""
        if phase_id not in self.phases:
            self.logger.error(f"Unknown phase: {phase_id}")
            return False
        
        phase_state = self.phases[phase_id]
        if phase_state.status != PhaseStatus.PENDING:
            # Allow retrying failed phases
            if not phase_state.can_retry:
                self.logger.error(f"Phase {phase_id} cannot be started (status: {phase_state.status.value})")
                return False
            phase_state.status = PhaseStatus.RETRYING
        else:
            phase_state.status = PhaseStatus.IN_PROGRESS
        
        phase_state.attempt_count += 1
        phase_state.start_time = datetime.now()
        self.current_phase_id = phase_id
        self.total_attempts += 1
        
        self.logger.info(f"Phase started: {phase_id} (attempt {phase_state.attempt_count})")
        return True
    
    def complete_phase(self, phase_id: str, success: bool = True, 
                      generated_files: Optional[ProjectFiles] = None,
                      test_results: Optional[List[TestResult]] = None):
        """Complete a phase."""
        if phase_id not in self.phases:
            self.logger.error(f"Unknown phase: {phase_id}")
            return
        
        phase_state = self.phases[phase_id]
        phase_state.status = PhaseStatus.COMPLETED if success else PhaseStatus.FAILED
        phase_state.end_time = datetime.now()
        
        if generated_files:
            phase_state.generated_files = generated_files
            self.total_files_generated += len(generated_files.files)
        
        if test_results:
            phase_state.test_results.extend(test_results)
        
        if success:
            self.completed_phases.append(phase_id)
            self.logger.info(f"Phase completed successfully: {phase_id}")
        else:
            self.logger.warning(f"Phase failed: {phase_id}")
    
    def add_phase_error(self, phase_id: str, error: str):
        """Add an error to a phase."""
        if phase_id in self.phases:
            self.phases[phase_id].errors.append(error)
            self.total_errors += 1
    
    def add_fix_plan(self, phase_id: str, fix_plan: FixPlan):
        """Add a fix plan to a phase."""
        if phase_id in self.phases:
            self.phases[phase_id].fix_plans.append(fix_plan)
    
    def set_phase_files(self, phase_id: str, project_files: ProjectFiles):
        """Set the generated files for a phase."""
        if phase_id in self.phases:
            self.phases[phase_id].generated_files = project_files
            self.total_files_generated += len(project_files.files)
            self.logger.debug(f"Set {len(project_files.files)} files for phase {phase_id}")
    
    def get_current_phase(self) -> Optional[PhaseState]:
        """Get the current phase state."""
        if self.current_phase_id:
            return self.phases.get(self.current_phase_id)
        return None
    
    def get_next_phase(self) -> Optional[str]:
        """Get the next phase to execute."""
        if not self.project_plan:
            return None
        
        for phase in self.project_plan.phases:
            phase_state = self.phases.get(phase.phase_id)
            if phase_state and phase_state.status == PhaseStatus.PENDING:
                return phase.phase_id
            elif phase_state and phase_state.can_retry:
                return phase.phase_id
        
        return None
    
    def get_failed_phases(self) -> List[PhaseState]:
        """Get all failed phases that cannot be retried."""
        return [
            phase_state for phase_state in self.phases.values()
            if phase_state.status == PhaseStatus.FAILED and not phase_state.can_retry
        ]
    
    def is_workflow_complete(self) -> bool:
        """Check if the workflow is complete."""
        if not self.project_plan:
            return False
        
        return len(self.completed_phases) == len(self.project_plan.phases)
    
    def has_failures(self) -> bool:
        """Check if there are any unrecoverable failures."""
        return len(self.get_failed_phases()) > 0
    
    @property
    def duration(self) -> Optional[float]:
        """Get the total workflow duration in seconds."""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        elif self.start_time:
            return (datetime.now() - self.start_time).total_seconds()
        return None
    
    @property
    def progress_percentage(self) -> float:
        """Get the workflow progress as a percentage."""
        if not self.project_plan:
            return 0.0
        
        total_phases = len(self.project_plan.phases)
        if total_phases == 0:
            return 100.0
        
        return (len(self.completed_phases) / total_phases) * 100.0
    
    def get_workflow_summary(self) -> Dict[str, Any]:
        """Get a comprehensive summary of the workflow state."""
        
        # Collect detailed phase information with attempt counts
        phase_details = []
        total_attempts_across_phases = 0
        
        # Sort phases by phase_id to maintain order
        sorted_phases = sorted(self.phases.items(), key=lambda x: x[0])
        
        for phase_id, phase_state in sorted_phases:
            phase_info = {
                "phase_id": phase_id,
                "name": phase_state.phase.name,
                "status": phase_state.status.value,
                "attempts": phase_state.attempt_count,
                "duration": phase_state.duration,
                "files_generated": len(phase_state.generated_files.files) if phase_state.generated_files else 0
            }
            phase_details.append(phase_info)
            total_attempts_across_phases += phase_state.attempt_count
        
        return {
            "workflow_id": self.workflow_id,
            "status": self.status.value,
            "progress": self.progress_percentage,
            "duration": self.duration,
            "phases": {
                "total": len(self.phases),
                "completed": len(self.completed_phases),
                "failed": len(self.get_failed_phases()),
                "current": self.current_phase_id,
                "details": phase_details
            },
            "agents": {
                name: {
                    "type": agent.agent_type,
                    "status": agent.status.value,
                    "messages": agent.message_count,
                    "errors": agent.error_count
                }
                for name, agent in self.agents.items()
            },
            "statistics": {
                "total_attempts": self.total_attempts,
                "total_errors": self.total_errors,
                "files_generated": self.total_files_generated,
                "phase_attempts": total_attempts_across_phases
            },
            "project_info": {
                "prompt": self.project_info.prompt,
                "type": self.project_info.project_type,
                "language": self.project_info.language
            }
        }
    
    def get_phase_summary(self, phase_id: str) -> Optional[Dict[str, Any]]:
        """Get a summary of a specific phase."""
        if phase_id not in self.phases:
            return None
        
        phase_state = self.phases[phase_id]
        return {
            "phase_id": phase_id,
            "name": phase_state.phase.name,
            "status": phase_state.status.value,
            "attempts": phase_state.attempt_count,
            "can_retry": phase_state.can_retry,
            "duration": phase_state.duration,
            "files_generated": len(phase_state.generated_files.files) if phase_state.generated_files else 0,
            "test_results": len(phase_state.test_results),
            "errors": len(phase_state.errors)
        }