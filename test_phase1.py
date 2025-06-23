#!/usr/bin/env python3
"""
Test script for Phase 1 agent communication framework.

This script tests the basic agent communication and workflow orchestration
components we've implemented in Phase 1.
"""

import asyncio
import sys
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent))

from utils.agent_messages import (
    ProjectInfo, AgentMessage, MessageType, AgentStatus,
    create_plan_request, create_plan_response, ProjectPlan, Phase
)
from utils.workflow_state import WorkflowState, WorkflowStatus
from agents.base_agent import BaseAgent
from orchestrator import WorkflowOrchestrator
from utils.logger import setup_logger


class MockPlannerAgent(BaseAgent):
    """Mock Planner Agent for testing."""
    
    def __init__(self):
        super().__init__("planner", "planner")
        self.capabilities = ["project_analysis", "phase_planning"]
    
    async def _handle_plan_request(self, message: AgentMessage):
        """Handle plan request by creating a simple test plan."""
        self.logger.info("Handling plan request...")
        self.set_status(AgentStatus.WORKING)
        
        # Simulate planning work
        await asyncio.sleep(0.5)
        
        # Create a simple test project plan
        project_info = ProjectInfo(**message.payload["project_info"])
        
        phases = [
            Phase(
                phase_id="phase_1",
                name="Project Setup",
                description="Create basic project structure and requirements",
                files_to_create=["requirements.txt", "main.py", "README.md"],
                dependencies=[],
                estimated_complexity=2
            ),
            Phase(
                phase_id="phase_2", 
                name="Core Implementation",
                description="Implement main application logic",
                files_to_create=["src/__init__.py", "src/core.py"],
                dependencies=["requirements.txt"],
                estimated_complexity=4
            )
        ]
        
        project_plan = ProjectPlan(
            project_info=project_info,
            phases=phases,
            total_phases=len(phases),
            estimated_duration=45
        )
        
        self.set_status(AgentStatus.COMPLETED)
        
        # Create response message
        response = create_plan_response(
            sender=self.name,
            recipient=message.sender,
            project_plan=project_plan,
            phase_id=message.phase_id,
            correlation_id=message.correlation_id
        )
        
        return response
    
    async def _handle_write_request(self, message: AgentMessage):
        return None
    
    async def _handle_test_request(self, message: AgentMessage):
        return None
    
    async def _handle_fix_request(self, message: AgentMessage):
        return None


class MockWriterAgent(BaseAgent):
    """Mock Writer Agent for testing."""
    
    def __init__(self):
        super().__init__("writer", "writer")
        self.capabilities = ["code_generation", "file_writing"]
    
    async def _handle_plan_request(self, message: AgentMessage):
        return None
    
    async def _handle_write_request(self, message: AgentMessage):
        self.logger.info("Handling write request...")
        return None
    
    async def _handle_test_request(self, message: AgentMessage):
        return None
    
    async def _handle_fix_request(self, message: AgentMessage):
        return None


class MockTesterAgent(BaseAgent):
    """Mock Tester Agent for testing."""
    
    def __init__(self):
        super().__init__("tester", "tester")
        self.capabilities = ["docker_testing", "build_validation"]
    
    async def _handle_plan_request(self, message: AgentMessage):
        return None
    
    async def _handle_write_request(self, message: AgentMessage):
        return None
    
    async def _handle_test_request(self, message: AgentMessage):
        self.logger.info("Handling test request...")
        return None
    
    async def _handle_fix_request(self, message: AgentMessage):
        return None


class MockFixingAgent(BaseAgent):
    """Mock Fixing Agent for testing."""
    
    def __init__(self):
        super().__init__("fixing", "fixing")
        self.capabilities = ["error_analysis", "fix_planning"]
    
    async def _handle_plan_request(self, message: AgentMessage):
        return None
    
    async def _handle_write_request(self, message: AgentMessage):
        return None
    
    async def _handle_test_request(self, message: AgentMessage):
        return None
    
    async def _handle_fix_request(self, message: AgentMessage):
        self.logger.info("Handling fix request...")
        return None


async def test_agent_communication():
    """Test basic agent communication."""
    print("=== Testing Agent Communication ===")
    
    # Create mock agents
    planner = MockPlannerAgent()
    writer = MockWriterAgent()
    
    # Test agent initialization
    assert planner.get_status() == AgentStatus.IDLE
    assert planner.agent_type == "planner"
    assert planner.name == "planner"
    
    # Test message creation
    project_info = ProjectInfo(
        prompt="Create a simple Python CLI tool",
        project_type="cli_tool",
        language="python"
    )
    
    plan_request = create_plan_request(
        sender="test",
        recipient="planner",
        project_info=project_info,
        phase_id="test_phase_1"
    )
    
    assert plan_request.message_type == MessageType.PLAN_REQUEST
    assert plan_request.sender == "test"
    assert plan_request.recipient == "planner"
    
    # Test message handling
    response = await planner.handle_message(plan_request)
    assert response is not None
    assert response.message_type == MessageType.PLAN_RESPONSE
    
    print("✓ Agent communication test passed")


async def test_workflow_state():
    """Test workflow state management."""
    print("=== Testing Workflow State ===")
    
    project_info = ProjectInfo(
        prompt="Create a web scraper",
        project_type="script",
        language="python"
    )
    
    # Create workflow state
    workflow_state = WorkflowState(project_info, max_attempts=3)
    
    # Test initial state
    assert workflow_state.status == WorkflowStatus.IDLE
    assert workflow_state.project_info.prompt == "Create a web scraper"
    
    # Test agent registration
    agent_state = workflow_state.register_agent("planner", "planner")
    assert agent_state.name == "planner"
    assert agent_state.status == AgentStatus.IDLE
    
    # Test workflow start
    workflow_state.start_workflow()
    assert workflow_state.status == WorkflowStatus.PLANNING
    assert workflow_state.start_time is not None
    
    # Test phase management
    from utils.agent_messages import Phase, ProjectPlan
    
    phases = [
        Phase(
            phase_id="test_phase",
            name="Test Phase",
            description="A test phase",
            files_to_create=["test.py"],
            dependencies=[],
            estimated_complexity=3
        )
    ]
    
    project_plan = ProjectPlan(
        project_info=project_info,
        phases=phases,
        total_phases=1,
        estimated_duration=20
    )
    
    workflow_state.set_project_plan(project_plan)
    assert len(workflow_state.phases) == 1
    assert "test_phase" in workflow_state.phases
    
    # Test phase execution
    assert workflow_state.start_phase("test_phase") == True
    assert workflow_state.current_phase_id == "test_phase"
    
    workflow_state.complete_phase("test_phase", success=True)
    assert len(workflow_state.completed_phases) == 1
    assert workflow_state.is_workflow_complete() == True
    
    print("✓ Workflow state test passed")


async def test_orchestrator():
    """Test workflow orchestrator."""
    print("=== Testing Workflow Orchestrator ===")
    
    project_info = ProjectInfo(
        prompt="Build a simple calculator",
        project_type="cli_tool",
        language="python"
    )
    
    # Create orchestrator
    orchestrator = WorkflowOrchestrator(project_info, max_attempts=2, timeout_minutes=5)
    
    # Create and register mock agents
    planner = MockPlannerAgent()
    writer = MockWriterAgent()
    tester = MockTesterAgent()
    fixing = MockFixingAgent()
    
    orchestrator.register_agent("planner", planner)
    orchestrator.register_agent("writer", writer)
    orchestrator.register_agent("tester", tester)
    orchestrator.register_agent("fixing", fixing)
    
    # Test agent validation
    assert orchestrator.validate_agents() == True
    
    # Test workflow status
    status = orchestrator.get_workflow_status()
    assert status["is_running"] == False
    assert status["status"] == "idle"
    
    print("✓ Orchestrator test passed")


async def test_message_serialization():
    """Test message serialization and deserialization."""
    print("=== Testing Message Serialization ===")
    
    project_info = ProjectInfo(
        prompt="Test project",
        project_type="script",
        language="python"
    )
    
    # Create a message
    original_message = create_plan_request(
        sender="test_sender",
        recipient="test_recipient",
        project_info=project_info,
        phase_id="test_phase"
    )
    
    # Test serialization
    message_dict = original_message.to_dict()
    assert message_dict["sender"] == "test_sender"
    assert message_dict["message_type"] == "plan_request"
    
    # Test JSON serialization
    json_str = original_message.to_json()
    assert isinstance(json_str, str)
    assert "test_sender" in json_str
    
    # Test deserialization
    restored_message = AgentMessage.from_dict(message_dict)
    assert restored_message.sender == original_message.sender
    assert restored_message.message_type == original_message.message_type
    
    # Test JSON deserialization
    json_restored = AgentMessage.from_json(json_str)
    assert json_restored.sender == original_message.sender
    
    print("✓ Message serialization test passed")


async def run_all_tests():
    """Run all Phase 1 tests."""
    print("Starting Phase 1 Agent Communication Framework Tests...\n")
    
    try:
        await test_agent_communication()
        await test_workflow_state()
        await test_orchestrator()
        await test_message_serialization()
        
        print("\n🎉 All Phase 1 tests passed successfully!")
        print("\nPhase 1.1 Core Agent Framework is ready for Phase 1.2 (Planner Agent)")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    # Setup logging for tests
    setup_logger(debug_mode=True)
    
    # Run tests
    success = asyncio.run(run_all_tests())
    
    if success:
        print("\n✅ Phase 1.1 implementation completed successfully!")
        print("Ready to proceed to Phase 1.2: Planner Agent Implementation")
    else:
        print("\n❌ Phase 1.1 tests failed. Please fix issues before proceeding.")
        sys.exit(1)