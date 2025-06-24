"""
Reviewer Agent

Agent responsible for reviewing generated files against project plan success criteria
and providing detailed feedback to the Writer Agent for improvements.
"""

import json
import asyncio
from typing import Optional, Dict, Any, List, Tuple
from pathlib import Path
from datetime import datetime

from autogen_core import RoutedAgent, message_handler
from autogen_core.models import UserMessage, SystemMessage

from utils.agent_messages import (
    AgentMessage, MessageType, ProjectFiles, FileContent, Phase, ProjectInfo,
    create_status_update, AgentStatus
)
from utils.logger import get_agent_logger, LogContext, log_model_interaction
from utils.file_handler import FileHandler


class ReviewerAgent(RoutedAgent):
    """Reviewer Agent that validates generated files against plan success criteria."""
    
    def __init__(self, 
                 name: str = "ReviewerAgent",
                 model_client=None,
                 output_dir: Optional[Path] = None,
                 **kwargs):
        
        super().__init__(name)
        
        self.name = name
        self.agent_type = "reviewer"
        self.output_dir = Path(output_dir) if output_dir else Path("./output")
        
        # Enhanced logging with agent-specific logger
        debug_dir = self.output_dir / "debug" if output_dir else Path("./debug")
        self.logger = get_agent_logger("reviewer", debug_dir)
        self.model_client = model_client
        self.file_handler = FileHandler(self.output_dir)
        
        # Agent state
        self.current_phase_id = None
        self.current_project_info = None
        self.plan_json_path = None
        self.status = AgentStatus.IDLE
        self.phase_attempt_count = {}  # Track attempts per phase
        
        # System message for the reviewer agent
        self.system_message = self._create_system_message()
        
        self.logger.info(f"ReviewerAgent '{name}' initialized with output directory: {self.output_dir}",
                        extra={'agent_name': 'reviewer'})
    
    def _create_system_message(self) -> str:
        """Create system message for the reviewer agent."""
        
        return f"""You are an expert AI Reviewer Agent specialized in validating generated code against detailed project plans. Your role is to ensure that generated files meet all success criteria and provide constructive feedback for improvements.

CORE RESPONSIBILITIES:
1. Read and understand detailed project plans from JSON files
2. Validate generated files against plan success criteria
3. Provide specific, actionable feedback for improvements
4. Ensure all files work together as a cohesive project
5. Decide when to stop a phase due to repeated failures

CRITICAL REVIEW GUIDELINES:
- ONLY evaluate success criteria that can be verified by examining the generated files
- DO NOT require external setup, installations, or virtual environments unless actual files prove they exist
- Focus on file content, structure, and functionality rather than environment setup
- Be consistent in your evaluation standards across all attempts
- If a criterion mentions "setup" or "environment", interpret it as "documented in files" not "actually executed"

REVIEW PROCESS:
1. Load the project plan JSON to understand requirements and success criteria
2. Examine all generated files for the current phase
3. Check each file against the specific success criteria defined in the plan
4. Validate file structure, naming conventions, and content requirements
5. Ensure proper integration between files
6. Identify any missing or incomplete functionality

SUCCESS CRITERIA VALIDATION RULES:
1. Read success criteria from the plan JSON file for the current phase
2. For each criterion, ONLY check what can be verified from the generated files:
   - File existence and naming
   - Code content and functionality
   - Documentation and comments
   - Proper imports and structure
3. DO NOT fail criteria for missing external setup unless specific setup files are required
4. Be consistent: if you accept documentation in attempt 1, accept similar documentation in later attempts
5. Focus on the INTENT of the criterion rather than literal interpretation

INTERPRETATION GUIDELINES:
- "Project directory exists" = Files are organized properly
- "Virtual environment created" = Setup instructions are documented (unless venv files required)
- "Files are present" = Check actual file existence
- "Functionality implemented" = Code contains required functions/features
- "Tests written" = Test files contain actual test code

FEEDBACK GENERATION:
1. Provide specific, actionable feedback for each issue found
2. Reference exact file names and line numbers where possible
3. Suggest concrete improvements and corrections
4. Prioritize critical issues that prevent functionality
5. Include positive feedback for well-implemented features
6. Be consistent in your standards across review attempts

QUALITY STANDARDS:
1. Code should be clean, readable, and well-documented
2. Follow language-specific best practices and conventions
3. Include proper error handling and input validation
4. Ensure security considerations are addressed
5. Validate that all dependencies are properly handled

FAILURE HANDLING:
1. Track the number of attempts for each phase
2. Provide increasingly specific feedback with each failure
3. Stop the phase and end project creation after maximum attempts
4. Clearly communicate when and why a phase is being terminated

OUTPUT DIRECTORY: {self.output_dir}

Always provide constructive, specific feedback that helps the Writer Agent improve the generated code. Focus on the success criteria defined in the project plan and be CONSISTENT in your evaluation standards."""
    
    @message_handler
    async def handle_message(self, message: AgentMessage, ctx: Any) -> AgentMessage:
        """Handle incoming messages from other agents."""
        
        try:
            extra = {'agent_name': 'reviewer'}
            self.logger.info(f"ReviewerAgent received {message.message_type.value} from {message.sender}", extra=extra)
            
            # For now, we'll handle review requests through a custom message type
            # This will be integrated with the orchestrator's workflow
            if message.message_type == MessageType.WRITE_RESPONSE:
                return await self._handle_review_request(message)
            else:
                self.logger.warning(f"Unsupported message type: {message.message_type}", 
                                  extra={'agent_name': 'reviewer'})
                return self._create_status_response(message, "Unsupported message type")
                
        except Exception as e:
            self.logger.error(f"Error handling message: {str(e)}", 
                            extra={'agent_name': 'reviewer'}, exc_info=True)
            return self._create_error_response(message, str(e))
    
    async def review_phase_completion(self, phase_id: str, project_files: ProjectFiles, 
                                    project_info: ProjectInfo, attempt_number: int = 1) -> Tuple[bool, Optional[str]]:
        """
        Review if a phase has been completed successfully.
        
        Args:
            phase_id: ID of the phase to review
            project_files: Files generated for this phase
            project_info: Project information
            attempt_number: Current attempt number for this phase
            
        Returns:
            Tuple of (success: bool, feedback: Optional[str])
        """
        
        with LogContext(self.logger, f"review_phase_{phase_id}_attempt_{attempt_number}", "reviewer") as ctx:
            try:
                self.status = AgentStatus.WORKING
                self.current_phase_id = phase_id
                self.current_project_info = project_info
                
                # Track attempt count
                if phase_id not in self.phase_attempt_count:
                    self.phase_attempt_count[phase_id] = 0
                self.phase_attempt_count[phase_id] = attempt_number
                
                ctx.add_data("phase_id", phase_id)
                ctx.add_data("attempt_number", attempt_number)
                ctx.add_data("files_count", len(project_files.files))
                ctx.add_data("file_names", [f.filename for f in project_files.files])
                
                self.logger.info(f"Reviewing phase {phase_id} (attempt {attempt_number})", 
                               extra={'agent_name': 'reviewer', 'structured_data': {
                                   'phase_id': phase_id,
                                   'attempt_number': attempt_number,
                                   'files_to_review': [{
                                       'filename': f.filename,
                                       'size': len(f.content),
                                       'language': f.language,
                                       'type': f.file_type
                                   } for f in project_files.files]
                               }})
            
                # Load the project plan
                plan_data = await self._load_plan_json()
                
                # Find the phase details in the plan
                phase_details = self._find_phase_in_plan(phase_id, plan_data)
                if not phase_details:
                    raise ValueError(f"Phase {phase_id} not found in plan")
                
                success_criteria = phase_details.get("success_criteria", [])
                files_to_create = phase_details.get("files_to_create", [])
                
                ctx.add_data("success_criteria_count", len(success_criteria))
                ctx.add_data("required_files_count", len(files_to_create))
                
                self.logger.debug(f"Phase review criteria: {len(success_criteria)} criteria, {len(files_to_create)} files required",
                                extra={'agent_name': 'reviewer', 'structured_data': {
                                    'phase_details': phase_details,
                                    'success_criteria': success_criteria,
                                    'files_to_create': files_to_create
                                }})
                
                # Perform the review
                success, feedback = await self._perform_phase_review(
                    phase_details, project_files, project_info, attempt_number
                )
                
                ctx.add_data("review_result", "PASS" if success else "FAIL")
                ctx.add_data("feedback_length", len(feedback) if feedback else 0)
            
                self.status = AgentStatus.COMPLETED
                
                if success:
                    self.logger.info(f"Phase {phase_id} review PASSED", 
                                   extra={'agent_name': 'reviewer'})
                else:
                    self.logger.warning(f"Phase {phase_id} review FAILED (attempt {attempt_number})", 
                                      extra={'agent_name': 'reviewer', 'structured_data': {
                                          'full_feedback': feedback,
                                          'feedback_summary': feedback[:200] + '...' if feedback and len(feedback) > 200 else feedback
                                      }})
                
                return success, feedback
            
            except Exception as e:
                self.status = AgentStatus.ERROR
                self.logger.error(f"Failed to review phase {phase_id}: {str(e)}", 
                                extra={'agent_name': 'reviewer'}, exc_info=True)
                return False, f"Review failed due to error: {str(e)}"
    
    async def _handle_review_request(self, message: AgentMessage) -> AgentMessage:
        """Handle review request (for future integration)."""
        
        # This method would be used when the orchestrator sends review requests
        # For now, it's a placeholder for future integration
        return self._create_status_response(message, "Review functionality available through review_phase_completion method")
    
    async def _load_plan_json(self) -> Dict[str, Any]:
        """Load the project plan JSON file created by the planner agent."""
        
        try:
            # Look for the most recent plan.json file in the output directory
            plan_files = list(self.output_dir.glob("plan_*.json"))
            if not plan_files:
                # Fallback to looking in test_output directory
                test_output_dir = Path("test_output")
                if test_output_dir.exists():
                    plan_files = list(test_output_dir.glob("plan_*.json"))
            
            if not plan_files:
                raise FileNotFoundError("No plan JSON file found")
            
            # Use the most recent plan file
            latest_plan_file = max(plan_files, key=lambda p: p.stat().st_mtime)
            self.plan_json_path = latest_plan_file
            
            self.logger.info(f"Loading plan from: {latest_plan_file}", 
                           extra={'agent_name': 'reviewer'})
            
            with open(latest_plan_file, 'r', encoding='utf-8') as f:
                plan_data = json.load(f)
            
            return plan_data
            
        except Exception as e:
            self.logger.error(f"Failed to load plan JSON: {str(e)}", 
                            extra={'agent_name': 'reviewer'}, exc_info=True)
            raise
    
    def _find_phase_in_plan(self, phase_id: str, plan_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Find specific phase details in the plan data."""
        
        phases = plan_data.get("phases", [])
        for phase in phases:
            if phase.get("phase_id") == phase_id:
                return phase
        
        return None
    
    async def _perform_phase_review(self, phase_details: Dict[str, Any], project_files: ProjectFiles,
                                   project_info: ProjectInfo, attempt_number: int) -> Tuple[bool, Optional[str]]:
        """Perform the actual review of the phase."""
        
        with LogContext(self.logger, f"perform_phase_review_{phase_details.get('phase_id', 'unknown')}", "reviewer") as ctx:
            try:
                # Get success criteria from the phase
                success_criteria = phase_details.get("success_criteria", [])
                files_to_create = phase_details.get("files_to_create", [])
                
                ctx.add_data("success_criteria_count", len(success_criteria))
                ctx.add_data("files_to_create_count", len(files_to_create))
                ctx.add_data("attempt_number", attempt_number)
                
                review_results = []
                overall_success = True
            
                # Check if all required files were created
                file_check_result = self._check_required_files(files_to_create, project_files)
                review_results.append(file_check_result)
                if not file_check_result["passed"]:
                    overall_success = False
                
                self.logger.debug(f"File check result: {'PASS' if file_check_result['passed'] else 'FAIL'}",
                                extra={'agent_name': 'reviewer', 'structured_data': {
                                    'file_check_result': file_check_result
                                }})
                
                # Check each success criterion
                for i, criterion in enumerate(success_criteria):
                    self.logger.debug(f"Evaluating criterion {i+1}/{len(success_criteria)}: {criterion}",
                                    extra={'agent_name': 'reviewer'})
                    
                    criterion_result = await self._check_success_criterion(
                        criterion, project_files, phase_details, project_info
                    )
                    review_results.append(criterion_result)
                    
                    result_status = "PASS" if criterion_result["passed"] else "FAIL"
                    self.logger.debug(f"Criterion {i+1} result: {result_status} - {criterion_result.get('details', 'No details')}",
                                    extra={'agent_name': 'reviewer', 'structured_data': {
                                        'criterion_index': i,
                                        'criterion': criterion,
                                        'criterion_result': criterion_result
                                    }})
                    
                    if not criterion_result["passed"]:
                        overall_success = False
            
                # Generate feedback if needed
                feedback = None
                if not overall_success:
                    feedback = self._generate_feedback(review_results, attempt_number, phase_details)
                    
                    self.logger.info(f"Generated review feedback ({len(feedback)} chars)",
                                   extra={'agent_name': 'reviewer', 'structured_data': {
                                       'full_feedback': feedback,
                                       'review_results': review_results,
                                       'overall_success': overall_success
                                   }})
                
                ctx.add_data("overall_success", overall_success)
                ctx.add_data("feedback_generated", feedback is not None)
                
                return overall_success, feedback
            
            except Exception as e:
                self.logger.error(f"Error performing phase review: {str(e)}", 
                                extra={'agent_name': 'reviewer'}, exc_info=True)
                return False, f"Review error: {str(e)}"
    
    def _check_required_files(self, required_files: List[Any], project_files: ProjectFiles) -> Dict[str, Any]:
        """Check if all required files were created."""
        
        try:
            generated_filenames = {f.filename for f in project_files.files}
            
            missing_files = []
            for file_spec in required_files:
                # Handle different file specification formats
                if isinstance(file_spec, str):
                    filename = file_spec
                elif isinstance(file_spec, dict):
                    filename = file_spec.get("name", file_spec.get("filename", str(file_spec)))
                else:
                    filename = str(file_spec)
                
                if filename not in generated_filenames:
                    missing_files.append(filename)
            
            return {
                "type": "file_existence",
                "passed": len(missing_files) == 0,
                "details": f"Required files check: {len(required_files) - len(missing_files)}/{len(required_files)} files created",
                "issues": missing_files
            }
            
        except Exception as e:
            return {
                "type": "file_existence",
                "passed": False,
                "details": f"Error checking required files: {str(e)}",
                "issues": []
            }
    
    async def _check_success_criterion(self, criterion: str, project_files: ProjectFiles,
                                      phase_details: Dict[str, Any], project_info: ProjectInfo) -> Dict[str, Any]:
        """Check a specific success criterion using the model."""
        
        with LogContext(self.logger, f"check_criterion", "reviewer") as ctx:
            try:
                ctx.add_data("criterion", criterion)
                ctx.add_data("criterion_length", len(criterion))
                
                # Create a prompt to check this specific criterion
                prompt = self._create_criterion_check_prompt(criterion, project_files, phase_details, project_info)
                
                ctx.add_data("prompt_length", len(prompt))
                
                # Use the model to evaluate the criterion
                evaluation_result = await self._evaluate_with_model(prompt, criterion)
                
                ctx.add_data("evaluation_length", len(evaluation_result))
                
                # Parse the model's response to determine if criterion is met
                passed, details = self._parse_evaluation_result(evaluation_result, criterion)
                
                ctx.add_data("evaluation_passed", passed)
                
                return {
                    "type": "success_criterion",
                    "criterion": criterion,
                    "passed": passed,
                    "details": details,
                    "evaluation": evaluation_result
                }
                
            except Exception as e:
                self.logger.error(f"Error checking success criterion: {str(e)}", 
                                extra={'agent_name': 'reviewer'}, exc_info=True)
                return {
                    "type": "success_criterion",
                    "criterion": criterion,
                    "passed": False,
                    "details": f"Error evaluating criterion: {str(e)}",
                    "evaluation": ""
                }
    
    def _create_criterion_check_prompt(self, criterion: str, project_files: ProjectFiles,
                                      phase_details: Dict[str, Any], project_info: ProjectInfo) -> str:
        """Create a prompt for checking a specific success criterion."""
        
        # Get files that were supposed to be created in this phase
        files_to_create = phase_details.get("files", [])
        
        prompt_parts = [
            f"Evaluate whether the following success criterion is met by the generated files:",
            f"\nSUCCESS CRITERION: {criterion}",
            f"\nProject Description: {project_info.prompt}",
            f"Phase: {phase_details.get('name', 'Unknown Phase')}",
            f"Phase Description: {phase_details.get('description', '')}",
            f"Files supposed to be created in this phase: {', '.join(files_to_create)}",
            f"\nGenerated Files:"
        ]
        
        # Add file contents for analysis
        for file_content in project_files.files:
            prompt_parts.append(f"\n--- {file_content.filename} ---")
            # Truncate very long files for prompt efficiency
            content = file_content.content
            if len(content) > 2000:
                content = content[:2000] + "\n... (truncated)"
            prompt_parts.append(content)
        
        prompt_parts.extend([
            f"\nCRITICAL EVALUATION GUIDELINES:",
            f"1. ONLY evaluate what can be verified from the generated files above",
            f"2. If criterion mentions 'setup' or 'environment', interpret as 'documented in files'",
            f"3. Focus on file content, structure, and functionality",
            f"4. Do NOT require external setup unless specific setup files are mentioned",
            f"5. Be consistent with previous evaluations",
            f"\nEVALUATION INSTRUCTIONS:",
            f"1. Analyze the generated files against the success criterion",
            f"2. Check if the criterion is fully satisfied based on file content only",
            f"3. Look for both functional and structural requirements in the files",
            f"4. Respond with 'PASS' if criterion is met, 'FAIL' if not met",
            f"5. Provide specific details about what was found or missing in the files",
            f"6. Format your response as: 'RESULT: [PASS/FAIL] - [detailed explanation]'"
        ])
        
        return "\n".join(prompt_parts)
    
    async def _evaluate_with_model(self, prompt: str, criterion: str = "unknown") -> str:
        """Evaluate using the model client."""
        
        import time
        start_time = time.time()
        
        try:
            if self.model_client is None:
                # If no model client, do basic text-based evaluation
                return self._basic_text_evaluation(prompt)
            
            messages = [
                SystemMessage(content=self.system_message, source="system"),
                UserMessage(content=prompt, source="user")
            ]
            
            self.logger.debug(f"Calling model client for criterion evaluation: {criterion[:50]}{'...' if len(criterion) > 50 else ''}", 
                            extra={'agent_name': 'reviewer'})
            
            response = await self.model_client.create(messages)
            
            duration = time.time() - start_time
            
            if hasattr(response, 'content'):
                content = response.content
                
                # Log the full evaluation result without truncation
                self.logger.info(f"Criterion evaluation result: {content}",
                               extra={'agent_name': 'reviewer', 'structured_data': {
                                   'criterion': criterion,
                                   'full_evaluation': content,
                                   'evaluation_length': len(content),
                                   'duration': duration
                               }})
                
                # Log the model interaction with full details
                log_model_interaction(
                    self.logger,
                    "reviewer",
                    f"evaluate_criterion",
                    {
                        "messages": [{
                            "role": "system",
                            "content": self.system_message[:500] + "..." if len(self.system_message) > 500 else self.system_message
                        }, {
                            "role": "user",
                            "content": prompt
                        }],
                        "full_prompt": prompt,
                        "criterion": criterion
                    },
                    {
                        "content": content,
                        "content_length": len(content),
                        "criterion": criterion
                    },
                    duration
                )
                
                return content
            else:
                self.logger.debug("Model evaluation failed - no content in response", 
                                extra={'agent_name': 'reviewer'})
                return "Model evaluation failed - no content in response"
                
        except Exception as e:
            duration = time.time() - start_time
            self.logger.error(f"Error evaluating with model for criterion: {str(e)}", 
                            extra={'agent_name': 'reviewer'}, exc_info=True)
            
            # Log the failed attempt
            log_model_interaction(
                self.logger,
                "reviewer",
                f"evaluate_criterion_FAILED",
                {"criterion": criterion, "prompt_length": len(prompt)},
                {"error": str(e)},
                duration
            )
            
            return f"Model evaluation failed: {str(e)}"
    
    def _basic_text_evaluation(self, prompt: str) -> str:
        """Basic text-based evaluation when no model is available."""
        
        # Very basic checks - this is a fallback
        if "files created" in prompt.lower():
            return "RESULT: PASS - Basic file creation check passed"
        else:
            return "RESULT: FAIL - Unable to perform detailed evaluation without model"
    
    def _parse_evaluation_result(self, evaluation: str, criterion: str) -> Tuple[bool, str]:
        """Parse the model's evaluation result."""
        
        try:
            # Look for PASS/FAIL in the response
            evaluation_upper = evaluation.upper()
            
            if "RESULT: PASS" in evaluation_upper:
                # Extract details after PASS
                parts = evaluation.split("RESULT: PASS", 1)
                details = parts[1].strip(" -\n") if len(parts) > 1 else "Criterion met"
                return True, details
            elif "RESULT: FAIL" in evaluation_upper:
                # Extract details after FAIL
                parts = evaluation.split("RESULT: FAIL", 1)
                details = parts[1].strip(" -\n") if len(parts) > 1 else "Criterion not met"
                return False, details
            else:
                # If no clear PASS/FAIL, look for keywords
                if any(word in evaluation_upper for word in ["PASS", "SATISFIED", "MET", "SUCCESS"]):
                    return True, evaluation
                else:
                    return False, evaluation
                    
        except Exception as e:
            return False, f"Error parsing evaluation: {str(e)}"
    
    def _generate_feedback(self, review_results: List[Dict[str, Any]], attempt_number: int,
                          phase_details: Dict[str, Any]) -> str:
        """Generate detailed feedback based on review results."""
        
        feedback_parts = [
            f"REVIEW FEEDBACK - Phase: {phase_details.get('name', 'Unknown')} (Attempt {attempt_number})",
            f"=" * 60,
            ""
        ]
        
        # Categorize issues by severity
        critical_issues = []
        minor_issues = []
        
        for result in review_results:
            if not result["passed"]:
                if result["type"] == "file_existence":
                    critical_issues.append(f"MISSING FILES: {', '.join(result['issues'])}")
                else:
                    issue_text = f"CRITERION NOT MET: {result.get('criterion', 'Unknown')}"
                    if result.get('details'):
                        issue_text += f" - {result['details']}"
                    minor_issues.append(issue_text)
        
        # Add critical issues first
        if critical_issues:
            feedback_parts.append("CRITICAL ISSUES (Must Fix):")
            for issue in critical_issues:
                feedback_parts.append(f"❌ {issue}")
            feedback_parts.append("")
        
        # Add other issues
        if minor_issues:
            feedback_parts.append("REQUIREMENTS NOT MET:")
            for issue in minor_issues:
                feedback_parts.append(f"⚠️  {issue}")
            feedback_parts.append("")
        
        # Add specific recommendations based on attempt number
        feedback_parts.append("RECOMMENDATIONS:")
        if attempt_number == 1:
            feedback_parts.extend([
                "📋 Review the project plan JSON file carefully",
                "📁 Ensure all required files are created with correct names",
                "✅ Verify each success criterion is addressed in the code",
                "🔍 Check that files integrate properly with each other"
            ])
        elif attempt_number == 2:
            feedback_parts.extend([
                "🔄 Focus on the specific issues identified above",
                "💡 Consider simpler implementations if current approach is too complex",
                "📖 Add more detailed comments and documentation",
                "⚡ Ensure core functionality works before adding advanced features"
            ])
        else:
            feedback_parts.extend([
                "🚨 This is the final attempt - focus on critical issues only",
                "🎯 Implement minimal viable functionality that meets success criteria",
                "⏰ Time is limited - prioritize getting basic functionality working",
                "📋 Double-check against the project plan requirements"
            ])
        
        feedback_parts.append("")
        feedback_parts.append(f"Attempt {attempt_number} of maximum attempts. Please address all issues listed above.")
        
        return "\n".join(feedback_parts)
    
    def should_stop_phase(self, phase_id: str, max_attempts: int = 3) -> bool:
        """Determine if a phase should be stopped due to repeated failures."""
        
        current_attempts = self.phase_attempt_count.get(phase_id, 0)
        should_stop = current_attempts >= max_attempts
        
        if should_stop:
            self.logger.error(f"Stopping phase {phase_id} after {current_attempts} failed attempts", 
                            extra={'agent_name': 'reviewer'})
        
        return should_stop
    
    def _create_status_response(self, original_message: AgentMessage, message: str) -> AgentMessage:
        """Create a status response message."""
        
        return create_status_update(
            sender=self.name,
            recipient=original_message.sender,
            status=self.status,
            message=message,
            phase_id=original_message.phase_id,
            correlation_id=original_message.correlation_id
        )
    
    def _create_error_response(self, original_message: AgentMessage, error: str) -> AgentMessage:
        """Create an error response message."""
        
        return AgentMessage(
            message_type=MessageType.ERROR_REPORT,
            sender=self.name,
            recipient=original_message.sender,
            payload={
                "error": error,
                "error_type": "review_error"
            },
            phase_id=original_message.phase_id,
            timestamp=datetime.now(),
            correlation_id=original_message.correlation_id
        )
    
    def get_status(self) -> AgentStatus:
        """Get current agent status."""
        return self.status
    
    def get_phase_attempts(self, phase_id: str) -> int:
        """Get the number of attempts for a specific phase."""
        return self.phase_attempt_count.get(phase_id, 0)
    
    def reset_phase_attempts(self, phase_id: str):
        """Reset attempt count for a specific phase."""
        if phase_id in self.phase_attempt_count:
            del self.phase_attempt_count[phase_id]
    
    async def cleanup(self):
        """Cleanup resources."""
        self.logger.info("ReviewerAgent cleanup completed", 
                       extra={'agent_name': 'reviewer'})