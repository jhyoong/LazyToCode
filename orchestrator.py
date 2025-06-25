"""
Workflow Orchestrator

This module orchestrates the multi-agent workflow, coordinating between
the Planner, Writer, Tester, and Fixing agents to generate complete projects.
"""

import asyncio
from typing import Dict, Optional, Any, List
from pathlib import Path
from datetime import datetime

from utils.agent_messages import (
    ProjectInfo, AgentStatus, MessageType,
    create_plan_request, create_write_request, 
    create_test_request, create_fix_request
)
from utils.workflow_state import WorkflowState, WorkflowStatus, PhaseStatus
from utils.logger import get_agent_logger, LogContext, log_model_interaction
from utils.deep_planner import DeepPlanningManager


class WorkflowOrchestrator:
    """
    Orchestrates the multi-agent workflow for project generation.
    
    Phase 2 Workflow (Plan and Create):
    1. Plan: Planner agent analyzes prompt and creates project plan with JSON file
    2. Write: Writer agent implements each phase based on the plan JSON
    3. Review: Reviewer agent validates generated files against success criteria
    4. Repeat Write-Review cycle up to max_attempts per phase
    5. Move to next phase or stop project if phase fails after max attempts
    """
    
    def __init__(self, project_info: ProjectInfo, max_attempts: int = 3, 
                 timeout_minutes: int = 60, interactive_mode: bool = False,
                 deep_plan_mode: bool = False):
        """
        Initialize the orchestrator.
        
        Args:
            project_info: Information about the project to generate
            max_attempts: Maximum attempts per phase before giving up
            timeout_minutes: Maximum time to spend on the entire workflow
            interactive_mode: Enable interactive plan approval mode
            deep_plan_mode: Enable deep planning with AI plan review and reflection
        """
        self.project_info = project_info
        self.max_attempts = max_attempts
        self.timeout_seconds = timeout_minutes * 60
        self.interactive_mode = interactive_mode
        self.deep_plan_mode = deep_plan_mode
        
        # Initialize workflow state
        self.workflow_state = WorkflowState(project_info, max_attempts)
        
        # Agent references (will be injected)
        self.agents: Dict[str, Any] = {}
        
        # Orchestrator state
        self.is_running = False
        self.should_stop = False
        
        # Enhanced logging with agent-specific logger
        output_dir = Path(project_info.output_dir) if hasattr(project_info, 'output_dir') and project_info.output_dir else Path("./output")
        debug_dir = output_dir / "debug"
        self.logger = get_agent_logger("orchestrator", debug_dir)
        
        # Initialize interactive reviewer if needed
        self.interactive_reviewer = None
        if self.interactive_mode:
            from utils.interactive_reviewer import InteractivePlanReviewer
            self.interactive_reviewer = InteractivePlanReviewer(self.logger)
        
        # Initialize deep planning manager if needed
        self.deep_planning_manager = None
        if self.deep_plan_mode:
            self.deep_planning_manager = DeepPlanningManager(
                output_dir=output_dir,
                debug_mode=True,  # Enable debug mode for deep planning
                max_iterations=3,
                convergence_threshold=8.0
            )
        
        self.logger.info(f"Orchestrator initialized for project: {project_info.project_type}",
                        extra={'agent_name': 'orchestrator', 'structured_data': {
                            'project_info': {
                                'project_type': project_info.project_type,
                                'language': project_info.language,
                                'prompt_length': len(project_info.prompt),
                                'output_dir': project_info.output_dir
                            },
                            'max_attempts': max_attempts,
                            'timeout_minutes': timeout_minutes
                        }})
    
    def register_agent(self, agent_name: str, agent_instance: Any):
        """
        Register an agent with the orchestrator.
        
        Args:
            agent_name: Name of the agent (planner, writer, tester, fixing)
            agent_instance: The agent instance
        """
        self.agents[agent_name] = agent_instance
        self.workflow_state.register_agent(agent_name, agent_instance.agent_type)
        self.logger.info(f"Agent registered: {agent_name}", 
                       extra={'agent_name': 'orchestrator', 'structured_data': {
                           'registered_agent': agent_name,
                           'agent_type': agent_instance.agent_type,
                           'total_agents': len(self.agents)
                       }})
    
    def get_required_agents(self) -> List[str]:
        """Get list of required agent names."""
        required = ["planner", "writer", "reviewer"]
        if self.deep_plan_mode:
            required.append("plan_reviewer")
        return required
    
    def validate_agents(self) -> bool:
        """Validate that all required agents are registered."""
        required = set(self.get_required_agents())
        registered = set(self.agents.keys())
        missing = required - registered
        
        if missing:
            self.logger.error(f"Missing required agents: {missing}", 
                            extra={'agent_name': 'orchestrator', 'structured_data': {
                                'required_agents': list(required),
                                'registered_agents': list(registered),
                                'missing_agents': list(missing)
                            }})
            return False
        
        return True
    
    async def execute_workflow(self) -> Dict[str, Any]:
        """
        Execute the complete workflow.
        
        Returns:
            Dictionary with workflow results and summary
        """
        if not self.validate_agents():
            self.logger.error("Cannot execute workflow: missing required agents", 
                            extra={'agent_name': 'orchestrator'})
            return {"success": False, "error": "Missing required agents"}
        
        self.is_running = True
        self.workflow_state.start_workflow()
        
        self.logger.info("Starting multi-agent workflow execution", 
                       extra={'agent_name': 'orchestrator', 'structured_data': {
                           'workflow_id': self.workflow_state.workflow_id,
                           'project_prompt': self.project_info.prompt[:200] + '...' if len(self.project_info.prompt) > 200 else self.project_info.prompt,
                           'max_attempts': self.max_attempts,
                           'timeout_seconds': self.timeout_seconds
                       }})
        
        try:
            # Set timeout for the entire workflow
            result = await asyncio.wait_for(
                self._execute_workflow_phases(),
                timeout=self.timeout_seconds
            )
            
            return result
            
        except asyncio.TimeoutError:
            self.logger.error(f"Workflow timed out after {self.timeout_seconds} seconds", 
                            extra={'agent_name': 'orchestrator', 'structured_data': {
                                'timeout_seconds': self.timeout_seconds,
                                'workflow_id': self.workflow_state.workflow_id,
                                'final_status': str(self.workflow_state.status)
                            }})
            self.workflow_state.cancel_workflow()
            return {
                "success": False,
                "error": "Workflow timeout",
                "summary": self.workflow_state.get_workflow_summary()
            }
            
        except Exception as e:
            self.logger.error(f"Workflow failed with error: {str(e)}", 
                            extra={'agent_name': 'orchestrator'}, exc_info=True)
            self.workflow_state.complete_workflow(success=False)
            return {
                "success": False,
                "error": str(e),
                "summary": self.workflow_state.get_workflow_summary()
            }
            
        finally:
            self.is_running = False
    
    async def _execute_workflow_phases(self) -> Dict[str, Any]:
        """Execute the main workflow phases."""
        
        with LogContext(self.logger, "execute_workflow_phases", "orchestrator") as ctx:
            # Phase 1: Planning
            self.logger.info("Starting planning phase...", extra={'agent_name': 'orchestrator'})
            
            ctx.add_data("phase", "planning")
            plan_success = await self._execute_planning_phase()
            ctx.add_data("planning_success", plan_success)
        
            if not plan_success:
                self.logger.error("Planning phase failed - stopping workflow", 
                                extra={'agent_name': 'orchestrator'})
                self.workflow_state.complete_workflow(success=False)
                return {
                    "success": False,
                    "error": "Planning phase failed",
                    "summary": self.workflow_state.get_workflow_summary()
                }
        
            # Phase 2: Execute project phases
            self.logger.info("Starting project execution phases...", extra={'agent_name': 'orchestrator'})
            
            ctx.add_data("phase", "execution")
            execution_success = await self._execute_project_phases()
            ctx.add_data("execution_success", execution_success)
            
            # Complete workflow
            self.workflow_state.complete_workflow(success=execution_success)
            
            summary = self.workflow_state.get_workflow_summary()
            generated_files = self._collect_generated_files()
            
            ctx.add_data("final_success", execution_success)
            ctx.add_data("files_generated", len(generated_files))
            
            self.logger.info(f"Workflow completed: {'SUCCESS' if execution_success else 'FAILED'}", 
                           extra={'agent_name': 'orchestrator', 'structured_data': {
                               'workflow_success': execution_success,
                               'summary': summary,
                               'files_generated': len(generated_files),
                               'file_list': [f.get('filename', 'unknown') for f in generated_files]
                           }})
            
            return {
                "success": execution_success,
                "summary": summary,
                "generated_files": generated_files
            }
    
    async def _execute_planning_phase(self) -> bool:
        """Execute the planning phase."""
        
        with LogContext(self.logger, "execute_planning_phase", "orchestrator") as ctx:
            try:
                self.workflow_state.status = WorkflowStatus.PLANNING
                
                self.logger.info("Workflow status changed to PLANNING", 
                               extra={'agent_name': 'orchestrator'})
            
                # Send plan request to planner agent
                planner = self.agents["planner"]
                phase_id = self.workflow_state.workflow_id + "_planning"
                
                ctx.add_data("phase_id", phase_id)
                ctx.add_data("planner_agent", str(type(planner).__name__))
                
                plan_request = create_plan_request(
                    sender="orchestrator",
                    recipient="planner",
                    project_info=self.project_info,
                    phase_id=phase_id
                )
                
                # Send message and wait for response
                self.logger.debug("Sending plan request to planner...", 
                                extra={'agent_name': 'orchestrator', 'structured_data': {
                                    'request_type': 'plan_request',
                                    'phase_id': phase_id,
                                    'project_prompt': self.project_info.prompt
                                }})
                
                response = await planner.handle_message(plan_request, None)
                
                ctx.add_data("response_received", response is not None)
                ctx.add_data("response_type", str(response.message_type) if response else None)
            
                if not response or response.message_type != MessageType.PLAN_RESPONSE:
                    self.logger.error("Invalid or missing plan response", 
                                    extra={'agent_name': 'orchestrator', 'structured_data': {
                                        'response_received': response is not None,
                                        'response_type': str(response.message_type) if response else None,
                                        'expected_type': str(MessageType.PLAN_RESPONSE)
                                    }})
                    return False
            
                # Extract project plan from response
                project_plan_data = response.payload.get("project_plan")
                if not project_plan_data:
                    self.logger.error("No project plan in response", 
                                    extra={'agent_name': 'orchestrator', 'structured_data': {
                                        'payload_keys': list(response.payload.keys()) if response.payload else [],
                                        'payload_size': len(response.payload) if response.payload else 0
                                    }})
                    return False
                
                # Log successful plan extraction
                phases_count = len(project_plan_data.get("phases", []))
                self.logger.info(f"Received project plan with {phases_count} phases", 
                               extra={'agent_name': 'orchestrator', 'structured_data': {
                                   'project_plan_keys': list(project_plan_data.keys()),
                                   'phases_count': phases_count,
                                   'plan_metadata': {
                                       'project_name': project_plan_data.get('project_name'),
                                       'total_phases': phases_count
                                   }
                               }})
                
                ctx.add_data("phases_count", phases_count)
                
                # Deep planning if enabled (takes precedence over interactive mode)
                if self.deep_plan_mode and self.deep_planning_manager:
                    deep_plan_result = await self._execute_deep_planning(project_plan_data)
                    if not deep_plan_result["success"]:
                        self.logger.error("Deep planning failed - using original plan")
                        # Continue with original plan rather than failing
                    else:
                        # Use the improved plan from deep planning
                        project_plan_data = deep_plan_result["final_plan"]
                        self.logger.info(f"Deep planning completed with {deep_plan_result.get('total_iterations', 0)} iterations")
                        
                        # Save the final improved plan in the correct format for Writer Agent
                        await self._save_final_plan_for_writer(project_plan_data)
                
                # Interactive plan approval if enabled (and not deep planning)
                elif self.interactive_mode and self.interactive_reviewer:
                    approved_plan_data = await self._interactive_plan_review(project_plan_data)
                    if not approved_plan_data:
                        self.logger.info("Plan rejected by user in interactive mode")
                        return False
                    # Use approved plan data (might be modified)
                    project_plan_data = approved_plan_data
            
                # Convert project_plan_data back to ProjectPlan object
                from utils.agent_messages import ProjectPlan, Phase
                
                # Extract phases from the response
                phases_data = project_plan_data.get("phases", [])
                phases = []
                
                for phase_data in phases_data:
                    phase = Phase(
                        phase_id=phase_data["phase_id"],
                        name=phase_data["name"],
                        description=phase_data["description"],
                        files_to_create=phase_data.get("files_to_create", []),
                        dependencies=phase_data.get("dependencies", []),
                        estimated_complexity=phase_data.get("estimated_complexity", 3),
                        prerequisites=phase_data.get("prerequisites", [])
                    )
                    phases.append(phase)
                
                project_plan = ProjectPlan(
                    project_info=self.project_info,
                    phases=phases,
                    total_phases=project_plan_data.get("total_phases", len(phases)),
                    estimated_duration=project_plan_data.get("estimated_duration", 60)
                )
                
                self.workflow_state.set_project_plan(project_plan)
                self.logger.info(f"Planning completed with {len(phases)} phases", 
                               extra={'agent_name': 'orchestrator'})
                
                return True
            
            except Exception as e:
                self.logger.error(f"Planning phase failed: {str(e)}", 
                                extra={'agent_name': 'orchestrator'}, exc_info=True)
                return False
    
    async def _interactive_plan_review(self, plan_dict: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Handle interactive plan review and approval.
        
        Args:
            plan_dict: Dictionary containing the implementation plan
            
        Returns:
            Approved plan dictionary or None if rejected
        """
        from utils.interactive_reviewer import UserCommand
        
        current_plan = plan_dict.copy()
        
        try:
            while True:
                # Present plan to user
                self.interactive_reviewer.present_plan(current_plan)
                
                # Get user input and handle command
                user_input = self.interactive_reviewer.get_user_input()
                command, feedback = self.interactive_reviewer.handle_user_command(user_input, current_plan)
                
                if command == UserCommand.APPROVE:
                    self.logger.info("Plan approved by user")
                    return current_plan
                    
                elif command == UserCommand.REJECT:
                    self.logger.info("Plan rejected by user")
                    return None
                    
                elif command == UserCommand.MODIFY:
                    if feedback:
                        # Regenerate plan with user feedback
                        self.logger.info(f"User requested plan modification: {feedback}")
                        modification_result = await self._regenerate_plan_with_feedback(current_plan, feedback)
                        
                        if modification_result:
                            if modification_result.get("fallback_used"):
                                # Plan modification failed, using original plan
                                self.interactive_reviewer.show_regeneration_status(False, 
                                    "Plan modification failed. Using original plan instead.")
                            else:
                                # Plan successfully modified
                                self.interactive_reviewer.show_regeneration_status(True, "Plan updated with your feedback")
                            current_plan = modification_result
                        else:
                            self.interactive_reviewer.show_regeneration_status(False, "Failed to regenerate plan")
                    else:
                        print("❌ No feedback provided for modification. Please try again.")
                        
                # Continue the loop for details, help, or retry after failed modification
                
        except KeyboardInterrupt:
            self.logger.info("Interactive plan review interrupted by user")
            print("\n\n🛑 Plan review cancelled by user")
            return None
            
        except Exception as e:
            self.logger.error(f"Error in interactive plan review: {str(e)}")
            print(f"❌ Error in plan review: {str(e)}")
            print("💡 Falling back to non-interactive mode")
            return plan_dict  # Return original plan as fallback
    
    async def _regenerate_plan_with_feedback(self, original_plan: Dict[str, Any], feedback: str) -> Optional[Dict[str, Any]]:
        """
        Regenerate plan based on user feedback.
        
        Args:
            original_plan: Original plan dictionary
            feedback: User feedback for modifications
            
        Returns:
            Modified plan dictionary or None if failed
        """
        try:
            # Get the planner agent
            planner = self.agents.get("planner")
            if not planner:
                self.logger.error("Planner agent not available for plan regeneration")
                return None
            
            # Call the planner's regeneration method
            result = await planner.regenerate_plan_with_feedback(original_plan, feedback)
            
            if result.get("success"):
                if result.get("fallback_used"):
                    self.logger.info("Plan modification failed, using original plan as fallback")
                else:
                    self.logger.info("Plan regenerated successfully with user feedback")
                
                # Return the plan with fallback information
                plan_dict = result.get("plan_dict")
                plan_dict["fallback_used"] = result.get("fallback_used", False)
                return plan_dict
            else:
                error_msg = result.get("error", "Unknown error during regeneration")
                self.logger.error(f"Plan regeneration failed: {error_msg}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error regenerating plan with feedback: {str(e)}")
            return None
    
    async def _execute_deep_planning(self, initial_plan_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute deep planning with reflection between Planner and Plan Reviewer agents.
        
        Args:
            initial_plan_data: The initial plan dictionary to improve
            
        Returns:
            Dictionary with deep planning results
        """
        
        try:
            self.logger.info("Starting deep planning process")
            
            # Get required agents
            planner = self.agents.get("planner")
            plan_reviewer = self.agents.get("plan_reviewer")
            
            if not planner:
                return {"success": False, "error": "Planner agent not available"}
            
            if not plan_reviewer:
                return {"success": False, "error": "Plan reviewer agent not available"}
            
            # Use deep planning manager to execute the reflection cycle
            result = await self.deep_planning_manager.execute_deep_planning_cycle(
                planner_agent=planner,
                reviewer_agent=plan_reviewer,
                initial_prompt=self.project_info.prompt,
                project_context={"initial_plan": initial_plan_data}
            )
            
            if result.get("success"):
                # Display deep planning summary to user
                self._display_deep_planning_summary(result)
                
                self.logger.info(f"Deep planning successful: {result.get('total_iterations', 0)} iterations, "
                               f"score improvement: {result.get('best_score', 0):.1f}")
            else:
                self.logger.error(f"Deep planning failed: {result.get('error', 'Unknown error')}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error during deep planning execution: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "final_plan": initial_plan_data  # Fallback to original plan
            }
    
    def _display_deep_planning_summary(self, deep_plan_result: Dict[str, Any]):
        """Display a summary of the deep planning process to the user."""
        
        try:
            print("\n🧠 DEEP PLANNING SUMMARY")
            print("=" * 50)
            
            iterations = deep_plan_result.get('total_iterations', 0)
            best_score = deep_plan_result.get('best_score', 0)
            duration = deep_plan_result.get('duration_seconds', 0)
            
            print(f"🔄 Reflection Iterations: {iterations}")
            print(f"📊 Final Plan Score: {best_score:.1f}/10")
            print(f"⏱️  Deep Planning Duration: {duration:.1f}s")
            
            # Show improvement summary if available
            improvement_summary = deep_plan_result.get('improvement_summary', {})
            if improvement_summary.get('improvements_made'):
                score_improvement = improvement_summary.get('score_improvement', 0)
                if score_improvement > 0:
                    print(f"📈 Score Improvement: +{score_improvement:.1f} points")
                else:
                    print("📊 Score maintained through iterations")
            
            # Show convergence info
            convergence_info = deep_plan_result.get('convergence_info')
            if convergence_info:
                print(f"🎯 Convergence: {convergence_info.get('reason', 'Completed')}")
            
            print("✅ Deep planning completed - using improved plan")
            print()
            
        except Exception as e:
            self.logger.warning(f"Failed to display deep planning summary: {e}")
            print("🧠 Deep planning completed successfully\n")
    
    async def _execute_project_phases(self) -> bool:
        """Execute all project phases with write-test-fix cycles."""
        if not self.workflow_state.project_plan:
            self.logger.error("No project plan available")
            return False
        
        overall_success = True
        
        # Execute each phase
        for phase in self.workflow_state.project_plan.phases:
            if self.should_stop:
                break
            
            phase_success = await self._execute_single_phase(phase.phase_id)
            if not phase_success:
                overall_success = False
                
                # Check if we should continue or stop
                if not self._should_continue_after_failure(phase.phase_id):
                    break
        
        return overall_success
    
    async def _execute_single_phase(self, phase_id: str) -> bool:
        """
        Execute a single phase with write-review retry logic.
        
        Args:
            phase_id: ID of the phase to execute
            
        Returns:
            True if phase completed successfully
        """
        phase_state = self.workflow_state.phases.get(phase_id)
        if not phase_state:
            self.logger.error(f"Unknown phase: {phase_id}")
            return False
        
        self.logger.info(f"Executing phase: {phase_state.phase.name}")
        
        # Attempt the phase up to max_attempts times
        for attempt in range(1, self.max_attempts + 1):
            if self.should_stop:
                break
            
            self.workflow_state.start_phase(phase_id)
            
            try:
                # Write-Review cycle
                success = await self._execute_write_review_cycle(phase_id, attempt)
                
                if success:
                    self.workflow_state.complete_phase(phase_id, success=True)
                    self.logger.info(f"Phase completed successfully: {phase_id}")
                    return True
                else:
                    self.logger.warning(f"Phase attempt {attempt} failed: {phase_id}")
                    self.workflow_state.complete_phase(phase_id, success=False)
                    
                    # If not the last attempt, continue to retry
                    if attempt < self.max_attempts:
                        self.logger.info(f"Retrying phase {phase_id} (attempt {attempt + 1})")
                        continue
                
            except Exception as e:
                self.logger.error(f"Phase execution error: {str(e)}")
                self.workflow_state.add_phase_error(phase_id, str(e))
                self.workflow_state.complete_phase(phase_id, success=False)
        
        # All attempts failed
        self.logger.error(f"Phase failed after {self.max_attempts} attempts: {phase_id}")
        return False
    
    async def _execute_write_review_cycle(self, phase_id: str, attempt_number: int) -> bool:
        """
        Execute the write-review cycle for a phase.
        
        Args:
            phase_id: ID of the phase
            attempt_number: Current attempt number (1-based)
            
        Returns:
            True if cycle completed successfully
        """
        # Step 1: Write
        self.workflow_state.status = WorkflowStatus.WRITING
        write_success, generated_files = await self._execute_write_step(phase_id, attempt_number)
        
        if not write_success:
            return False
        
        # Step 2: Review
        self.workflow_state.status = WorkflowStatus.REVIEWING
        review_success, feedback = await self._execute_review_step(phase_id, generated_files, attempt_number)
        
        if review_success:
            return True
        
        # If review failed and there are more attempts, prepare feedback for next iteration
        if attempt_number < self.max_attempts:
            # Store feedback for the next write attempt
            await self._store_feedback_for_retry(phase_id, feedback)
        
        return False
    
    async def _execute_write_step(self, phase_id: str, attempt_number: int = 1):
        """Execute the write step by sending request to Writer Agent."""
        try:
            self.logger.debug(f"Executing write step for phase: {phase_id} (attempt {attempt_number})")
            
            # Get phase details
            phase_state = self.workflow_state.phases.get(phase_id)
            if not phase_state:
                raise ValueError(f"Phase {phase_id} not found")
            
            # Get any stored feedback from previous attempts
            feedback = await self._get_stored_feedback(phase_id)
            
            # Send write request to Writer Agent
            writer = self.agents["writer"]
            
            write_request = create_write_request(
                sender="orchestrator",
                recipient="writer",
                phase=phase_state.phase,
                project_info=self.project_info,
                phase_id=phase_id
            )
            
            # Add feedback to the request if available
            if feedback:
                write_request.payload["feedback"] = feedback
            
            self.logger.debug("Sending write request to writer agent...")
            response = await writer.handle_message(write_request, None)
            
            if not response or response.message_type != MessageType.WRITE_RESPONSE:
                self.logger.error("Invalid or missing write response")
                return False, None
            
            # Check if write was successful
            if response.payload.get("error"):
                self.logger.error(f"Writer agent error: {response.payload['error']}")
                return False, None
            
            # Extract generated files from response
            project_files_data = response.payload.get("project_files")
            if not project_files_data:
                self.logger.error("No project files in write response")
                return False, None
            
            # Convert back to ProjectFiles object
            from utils.agent_messages import ProjectFiles, FileContent
            
            files = []
            for file_data in project_files_data.get("files", []):
                file_content = FileContent(
                    filename=file_data["filename"],
                    content=file_data["content"],
                    file_type=file_data["file_type"],
                    language=file_data["language"]
                )
                files.append(file_content)
            
            project_files = ProjectFiles(
                files=files,
                phase_id=project_files_data["phase_id"],
                dependencies=project_files_data.get("dependencies", [])
            )
            
            # Store generated files in workflow state
            self.workflow_state.set_phase_files(phase_id, project_files)
            
            self.logger.info(f"Write step completed for phase {phase_id} with {len(files)} files")
            return True, project_files
            
        except Exception as e:
            self.logger.error(f"Write step failed: {str(e)}")
            return False, None
    
    async def _execute_review_step(self, phase_id: str, generated_files, attempt_number: int):
        """Execute the review step by using the Reviewer Agent."""
        try:
            self.logger.debug(f"Executing review step for phase: {phase_id} (attempt {attempt_number})")
            
            # Get the reviewer agent
            reviewer = self.agents["reviewer"]
            
            # Use the reviewer agent's review method
            success, feedback = await reviewer.review_phase_completion(
                phase_id=phase_id,
                project_files=generated_files,
                project_info=self.project_info,
                attempt_number=attempt_number
            )
            
            if success:
                self.logger.info(f"Review step PASSED for phase {phase_id}")
            else:
                self.logger.warning(f"Review step FAILED for phase {phase_id} (attempt {attempt_number})")
                if feedback:
                    self.logger.debug(f"Review feedback: {feedback[:200]}...")
            
            return success, feedback
            
        except Exception as e:
            self.logger.error(f"Review step failed: {str(e)}")
            return False, f"Review failed due to error: {str(e)}"
    
    async def _store_feedback_for_retry(self, phase_id: str, feedback: str):
        """Store feedback for the next retry attempt."""
        try:
            # Store feedback in workflow state or a temporary location
            if not hasattr(self, '_phase_feedback'):
                self._phase_feedback = {}
            
            self._phase_feedback[phase_id] = feedback
            self.logger.debug(f"Stored feedback for phase {phase_id} retry")
            
        except Exception as e:
            self.logger.error(f"Failed to store feedback: {str(e)}")
    
    async def _get_stored_feedback(self, phase_id: str) -> Optional[str]:
        """Get stored feedback for a phase."""
        try:
            if hasattr(self, '_phase_feedback'):
                return self._phase_feedback.get(phase_id)
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to get stored feedback: {str(e)}")
            return None
    
    def _should_continue_after_failure(self, failed_phase_id: str) -> bool:
        """
        Determine if workflow should continue after a phase failure.
        
        Args:
            failed_phase_id: ID of the failed phase
            
        Returns:
            True if workflow should continue
        """
        # For now, stop on any phase failure
        # This could be made configurable based on phase criticality
        return False
    
    def _collect_generated_files(self) -> List[Dict[str, Any]]:
        """Collect all generated files from completed phases, deduplicating by filename."""
        files_dict = {}  # Use dict to deduplicate by filename
        
        # Sort phases by ID to ensure we get the latest version of each file
        sorted_phases = sorted(self.workflow_state.phases.items(), key=lambda x: x[0])
        
        for phase_id, phase_state in sorted_phases:
            if phase_state.generated_files:
                for file_content in phase_state.generated_files.files:
                    # Latest version of each file overwrites earlier versions
                    files_dict[file_content.filename] = {
                        "filename": file_content.filename,
                        "content": file_content.content,
                        "file_type": file_content.file_type,
                        "language": file_content.language,
                        "phase_id": phase_id
                    }
        
        return list(files_dict.values())
    
    def stop_workflow(self):
        """Request workflow to stop gracefully."""
        self.should_stop = True
        self.logger.info("Workflow stop requested")
    
    def get_workflow_status(self) -> Dict[str, Any]:
        """Get current workflow status."""
        return {
            "is_running": self.is_running,
            "should_stop": self.should_stop,
            "status": self.workflow_state.status.value,
            "current_phase": self.workflow_state.current_phase_id,
            "progress": self.workflow_state.progress_percentage,
            "summary": self.workflow_state.get_workflow_summary()
        }
    
    async def _save_final_plan_for_writer(self, plan_data: Dict[str, Any]):
        """
        Save the final improved plan in the correct format for the Writer Agent.
        
        Args:
            plan_data: The final plan dictionary from deep planning
        """
        
        try:
            from datetime import datetime
            import json
            
            # Calculate output directory the same way as in __init__
            output_dir = Path(self.project_info.output_dir) if hasattr(self.project_info, 'output_dir') and self.project_info.output_dir else Path("./output")
            
            # Ensure output directory exists
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate filename with timestamp (following the same pattern as planner agent)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"plan_{timestamp}.json"
            filepath = output_dir / filename
            
            # Save the clean plan data (not wrapped in review structure)
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(plan_data, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Final improved plan saved to: {filepath}")
            
        except Exception as e:
            self.logger.error(f"Failed to save final plan for writer: {e}")

    async def cleanup(self):
        """Cleanup resources and shutdown agents."""
        self.logger.info("Cleaning up orchestrator...")
        
        # Shutdown all agents
        for agent_name, agent in self.agents.items():
            try:
                if hasattr(agent, 'shutdown'):
                    await agent.shutdown()
            except Exception as e:
                self.logger.error(f"Error shutting down agent {agent_name}: {str(e)}")
        
        self.agents.clear()
        self.logger.info("Orchestrator cleanup completed")