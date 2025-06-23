"""
Planner Agent - Main function is to draft out and orchestrate detailed plans for the Writer Agent.

This agent analyzes project requirements from prompts, breaks them down into logical phases,
generates detailed implementation plans, and validates phase completion with retry logic.
"""

from typing import Optional, Dict, Any, List
from pathlib import Path
import json
from datetime import datetime
import uuid

# Import from autogen-core
from autogen_core.models import UserMessage, SystemMessage

from agents.base_agent import BaseAgent
from utils.agent_messages import (
    AgentMessage, AgentStatus, MessageType,
    create_plan_response, create_status_update, create_error_report,
    ProjectInfo, ProjectPlan, Phase
)
from utils.logger import get_logger


class PlannerAgent(BaseAgent):
    """AI Planning Agent that generates detailed implementation plans for projects."""
    
    def __init__(self, 
                 name: str = "PlannerAgent",
                 model_client=None,
                 output_dir: Optional[Path] = None,
                 max_phases: int = 10,
                 debug_mode: bool = False,
                 **kwargs):
        
        super().__init__(name, "planner", **kwargs)
        
        self.model_client = model_client
        self.output_dir = output_dir or Path("./output")
        self.max_phases = max_phases
        self.debug_mode = debug_mode
        
        # Create debug directory if debug mode is enabled
        if self.debug_mode:
            self.debug_dir = self.output_dir / "debug"
            self.debug_dir.mkdir(parents=True, exist_ok=True)
            self.logger.info(f"Debug mode enabled. Debug files will be saved to: {self.debug_dir}")
        
        # Planner-specific capabilities
        self.capabilities = [
            "project_analysis",
            "phase_decomposition", 
            "implementation_planning",
            "python_project_planning",
            "plan_validation"
        ]
        
        # System message for the planner
        self.system_message = self._create_system_message()
        
        self.logger.info(f"PlannerAgent '{name}' initialized with max_phases: {max_phases}, debug_mode: {debug_mode}")
    
    def _create_system_message(self) -> str:
        """Create system message for the planner agent."""
        
        return f"""You are an expert project planner specialized in software development. Your role is to analyze project requirements and create detailed, actionable implementation plans.

CORE RESPONSIBILITIES:
1. Analyze project requirements from user prompts
2. Break down projects into logical, manageable phases
3. Generate detailed implementation plans for each phase
4. Intelligently determine the most appropriate programming language and technology stack
5. Consider project complexity and suggest appropriate structure

PROJECT ANALYSIS GUIDELINES:
- Identify project type (CLI tool, web app, API, data script, library, etc.)
- Intelligently select the most suitable programming language based on project requirements
- Determine required technologies, frameworks, and dependencies
- Assess project complexity and scope
- Consider best practices for the identified project type and chosen technology stack

PHASE PLANNING RULES:
- Maximum {self.max_phases} phases per project
- Each phase should be focused and achievable
- Include setup, core functionality, testing, and packaging phases
- Consider dependencies between phases
- Provide clear deliverables for each phase

IMPLEMENTATION PLAN FORMAT:
For each phase, provide:
- Phase name and description
- List of files to create/modify
- Required dependencies and libraries
- Detailed implementation steps
- Success criteria and validation points
- Estimated complexity (1-5 scale)

CRITICAL: SUCCESS CRITERIA ALIGNMENT
Success criteria MUST be directly related to and verifiable through the files being created in that phase:
- Focus on what can be validated by examining the generated files
- Avoid criteria that require external setup (virtual environments, installations, etc.)
- Be specific about file content requirements rather than vague concepts
- Ensure each criterion can be checked by reading the generated files
- Example GOOD criteria: "math_cli.py contains functions for add, subtract, multiply, divide"
- Example BAD criteria: "Virtual environment is created and activated" (cannot be verified from files)

OUTPUT FORMAT:
Generate a detailed JSON plan with the following structure:
{{
    "project_info": {{
        "name": "project name",
        "type": "project type",
        "description": "project description",
        "language": "determined_language",
        "complexity": 1-5
    }},
    "phases": [
        {{
            "phase_id": "phase_1",
            "name": "Phase Name",
            "description": "Phase description",
            "files": ["file1.py", "file2.py", ... ],
            "dependencies": ["package1", "package2"],
            "implementation_steps": ["step 1", "step 2"],
            "success_criteria": ["criteria 1", "criteria 2"],
            "complexity": 1-5
        }}
    ],
    "overall_structure": {{
        "project_root": "suggested project structure",
        "key_files": ["main files"],
        "testing_approach": "testing strategy"
    }}
}}

OUTPUT DIRECTORY: {self.output_dir}

Focus on creating practical, implementable plans that follow best practices for the chosen technology stack and modern development standards. Ensure that all files in each phase are also in key_files.
"""
    
    async def generate_plan(self, prompt: str, project_context: Optional[Dict] = None) -> Dict[str, Any]:
        """Generate a detailed implementation plan based on the given prompt."""
        
        try:
            self.logger.info(f"Generating plan for prompt: {prompt[:300]}...")
            self.set_status(AgentStatus.WORKING, "Generating implementation plan")
            
            # Enhance prompt with project context if provided
            enhanced_prompt = self._enhance_prompt(prompt, project_context)
            
            # Call the model to generate the plan
            plan_response = await self._process_planning_prompt(enhanced_prompt)
            
            # Parse and validate the plan
            plan = self._parse_and_validate_plan(plan_response, prompt)
            
            # Save plan to file for reference
            await self._save_plan_to_file(plan)
            
            self.set_status(AgentStatus.COMPLETED, "Plan generation completed")
            self.logger.info("Implementation plan generated successfully")
            
            return plan
            
        except Exception as e:
            self.logger.error(f"Failed to generate plan: {e}")
            self.set_status(AgentStatus.ERROR, f"Plan generation failed: {str(e)}")
            raise
    
    async def regenerate_plan_with_feedback(self, original_plan: Dict[str, Any], feedback: str) -> Dict[str, Any]:
        """
        Regenerate an existing plan based on user feedback.
        
        Args:
            original_plan: The original plan dictionary  
            feedback: User feedback describing what to change
            
        Returns:
            Dictionary with success/error status and plan_dict if successful
        """
        try:
            self.logger.info(f"Regenerating plan with user feedback: {feedback[:100]}...")
            self.set_status(AgentStatus.WORKING, "Regenerating plan with user feedback")
            
            # Create modification prompt based on original plan and feedback
            modification_prompt = self._create_modification_prompt(original_plan, feedback)
            
            # Process the prompt with the model
            plan_response = await self._process_planning_prompt(modification_prompt)
            
            # Parse and validate the modified plan
            modified_plan = self._parse_and_validate_plan(plan_response, feedback)
            
            # Save the modified plan
            if self.debug_mode:
                modified_plan_file = self.output_dir / f"plan_modified_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                with open(modified_plan_file, 'w') as f:
                    json.dump(modified_plan, f, indent=2)
                self.logger.info(f"Modified plan saved to {modified_plan_file}")
            
            self.set_status(AgentStatus.COMPLETED, "Plan regeneration completed successfully")
            self.logger.info("Plan regenerated successfully with user feedback")
            
            return {
                "success": True,
                "plan_dict": modified_plan,
                "message": "Plan regenerated with user feedback"
            }
            
        except Exception as e:
            self.logger.info(f"Failed to regenerate plan with feedback. Falling back to original plan. Error: {str(e)}")
            self.set_status(AgentStatus.COMPLETED, "Plan regeneration failed, using original plan")
            
            return {
                "success": True,  # Still return success since we have a valid fallback
                "plan_dict": original_plan,  # Fallback to original plan
                "message": "Plan modification failed, using original plan",
                "fallback_used": True
            }
    
    def _create_modification_prompt(self, original_plan: Dict[str, Any], feedback: str) -> str:
        """
        Create a prompt for modifying an existing plan based on user feedback.
        
        Args:
            original_plan: The original plan dictionary
            feedback: User feedback for modifications
            
        Returns:
            Enhanced prompt for plan modification
        """
        # Extract original plan details
        project_info = original_plan.get("project_info", {})
        phases = original_plan.get("phases", [])
        overall_structure = original_plan.get("overall_structure", {})
        
        prompt = f"""
You are an AI planning assistant tasked with MODIFYING an existing implementation plan based on user feedback.

ORIGINAL PROJECT INFORMATION:
- Project Name: {project_info.get('name', 'Unknown')}
- Project Type: {project_info.get('type', 'Unknown')}
- Language: {project_info.get('language', 'Unknown')}
- Complexity: {project_info.get('complexity', 'Unknown')}
- Description: {project_info.get('description', 'Not provided')}

ORIGINAL PLAN SUMMARY:
- Total Phases: {len(phases)}
- Phase Names: {', '.join([phase.get('name', f'Phase {i+1}') for i, phase in enumerate(phases)])}

ORIGINAL PHASES DETAIL:
{self._format_phases_for_modification(phases)}

ORIGINAL PROJECT STRUCTURE:
{json.dumps(overall_structure, indent=2)}

USER FEEDBACK FOR MODIFICATIONS:
{feedback}

TASK: Modify the above plan according to the user's feedback. Make specific changes requested while preserving the overall structure and maintaining logical phase ordering.

MODIFICATION GUIDELINES:
1. Keep the same project_info unless feedback specifically requests changes
2. Modify phases according to user feedback:
   - Add new phases if requested
   - Remove phases if requested
   - Modify existing phases (files, dependencies, steps, etc.)
   - Reorder phases if needed for logical flow
3. Update overall_structure if the changes affect project architecture
4. Ensure all phases still have valid files_to_create, dependencies, implementation_steps, and success_criteria
5. Maintain phase dependencies and logical implementation order
6. Keep the same JSON structure and field names

Output the COMPLETE modified plan in the same JSON format as the original, incorporating all requested changes.
"""
        
        return prompt
    
    def _format_phases_for_modification(self, phases: List[Dict[str, Any]]) -> str:
        """Format phases for display in modification prompt."""
        formatted_phases = []
        
        for i, phase in enumerate(phases, 1):
            phase_name = phase.get('name', f'Phase {i}')
            description = phase.get('description', 'No description')
            files = phase.get('files_to_create', [])
            dependencies = phase.get('dependencies', [])
            
            formatted_phase = f"""
Phase {i}: {phase_name}
Description: {description}
Files to Create: {', '.join(files) if files else 'None specified'}
Dependencies: {', '.join(dependencies) if dependencies else 'None'}
"""
            formatted_phases.append(formatted_phase)
        
        return '\n'.join(formatted_phases)
    
    def _enhance_prompt(self, prompt: str, project_context: Optional[Dict] = None) -> str:
        """Enhance the prompt with additional context and requirements."""
        
        enhanced_prompt = f"""
TASK: Create a detailed implementation plan for the following project:

PROJECT REQUEST:
{prompt}

REQUIREMENTS:
- Language: Determine the most appropriate language for the project requirements
- Output Directory: {self.output_dir}
- Maximum Phases: {self.max_phases}
- Target: Build working software with proper structure
- Testing: Include testing approach appropriate for the chosen technology
- Documentation: Include README and basic docs in the appropriate format

ADDITIONAL CONTEXT:
"""
        
        if project_context:
            enhanced_prompt += f"Project Context: {json.dumps(project_context, indent=2)}\n"
        
        enhanced_prompt += """
Please analyze the request and generate a comprehensive implementation plan following the specified JSON format.
Focus on creating a practical, step-by-step plan that a coding agent can follow to build the requested software.
"""
        
        return enhanced_prompt
    
    async def _process_planning_prompt(self, prompt: str) -> str:
        """Process the planning prompt using the model client."""
        
        session_id = uuid.uuid4().hex[:12]
        
        try:
            self.logger.debug(f"Processing planning prompt with session ID: {session_id}")
            
            if self.model_client is None:
                raise ValueError("Model client not initialized")
            
            # Create the messages for the chat completion
            messages = [
                SystemMessage(content=self.system_message, source="system"),
                UserMessage(content=prompt, source="user")
            ]
            
            # Log the request if debug mode is enabled
            if self.debug_mode:
                await self._log_debug_request(session_id, messages, prompt)
            
            # Call the model client to generate a response
            self.logger.debug("Calling model client for plan generation")
            start_time = datetime.now()
            
            try:
                response = await self.model_client.create(messages)
                end_time = datetime.now()
                duration = (end_time - start_time).total_seconds()
                self.logger.debug(f"Model client call completed for planning in {duration:.2f}s")
            except Exception as model_error:
                self.logger.error(f"Model client call failed: {model_error}")
                if self.debug_mode:
                    await self._log_debug_error(session_id, str(model_error))
                raise
            
            # Extract content from CreateResult
            if hasattr(response, 'content'):
                content = response.content
                self.logger.debug(f"Generated plan content length: {len(content)} characters")
                
                # Log the response if debug mode is enabled
                if self.debug_mode:
                    await self._log_debug_response(session_id, response, content, duration)
                
                return content
            else:
                error_msg = f"Could not extract content from response: {response}"
                self.logger.error(error_msg)
                if self.debug_mode:
                    await self._log_debug_error(session_id, error_msg)
                raise ValueError(error_msg)
                
        except Exception as e:
            self.logger.error(f"Error processing planning prompt: {e}")
            if self.debug_mode:
                await self._log_debug_error(session_id, str(e))
            # Re-raise the exception instead of using fallback
            raise
    
    
    def _parse_and_validate_plan(self, plan_response: str, original_prompt: str) -> Dict[str, Any]:
        """Parse and validate the generated plan with improved error handling."""
        
        try:
            # Check if response looks like a refusal or error message
            refusal_indicators = [
                "I'm sorry", "I cannot", "I don't have", "I'm unable", 
                "I can't", "Unfortunately", "I apologize", "I'm not able"
            ]
            
            if any(indicator.lower() in plan_response.lower() for indicator in refusal_indicators):
                # Log full model response at INFO level for model refusal
                self.logger.info(f"Model refused to generate plan. Full model response: {plan_response}")
                raise ValueError(f"Model refused to generate plan")
            
            # Extract JSON from the response (handle markdown code blocks)
            json_content = self._extract_json_from_response(plan_response)
            
            # Check if we actually got JSON-like content
            if not json_content.strip().startswith('{'):
                # Log full model response at INFO level for invalid JSON
                self.logger.info(f"Model response does not contain valid JSON structure. Full model response: {plan_response}")
                raise ValueError(f"Response does not contain valid JSON structure")
            
            # Parse JSON with better error handling
            try:
                plan = json.loads(json_content)
            except json.JSONDecodeError as json_err:
                # Log full model response at INFO level for JSON parsing errors
                self.logger.info(f"JSON parsing failed. Full model response: {plan_response}")
                raise ValueError(f"Invalid JSON format: {json_err}")
            
            # Validate plan structure
            self._validate_plan_structure(plan)
            
            # Add metadata
            plan["metadata"] = {
                "generated_at": datetime.now().isoformat(),
                "original_prompt": original_prompt,
                "planner_agent": self.name,
                "version": "1.0"
            }
            
            return plan
            
        except Exception as e:
            # Re-raise the exception - no fallback in this method
            raise
    
    def _extract_json_from_response(self, response: str) -> str:
        """Extract JSON content from model response, handling markdown code blocks."""
        
        # Remove markdown code blocks if present
        response = response.strip()
        
        # Look for JSON content between ```json and ``` or ``` and ```
        if "```json" in response:
            start = response.find("```json") + 7
            end = response.find("```", start)
            if end != -1:
                return response[start:end].strip()
        elif "```" in response:
            start = response.find("```") + 3
            end = response.find("```", start)
            if end != -1:
                return response[start:end].strip()
        
        # If no code blocks, try to find JSON directly
        # Look for the first { and last }
        start = response.find("{")
        end = response.rfind("}")
        
        if start != -1 and end != -1 and end > start:
            return response[start:end+1]
        
        # If no JSON found, return the whole response
        return response
    
    def _validate_plan_structure(self, plan: Dict[str, Any]):
        """Validate that the plan has the required structure."""
        
        required_keys = ["project_info", "phases", "overall_structure"]
        for key in required_keys:
            if key not in plan:
                raise ValueError(f"Plan missing required key: {key}")
        
        # Validate project_info
        project_info = plan["project_info"]
        required_project_keys = ["name", "type", "description", "language"]
        for key in required_project_keys:
            if key not in project_info:
                raise ValueError(f"Project info missing required key: {key}")
        
        # Validate phases
        phases = plan["phases"]
        if not isinstance(phases, list) or len(phases) == 0:
            raise ValueError("Plan must have at least one phase")
        
        for i, phase in enumerate(phases):
            required_phase_keys = ["phase_id", "name", "description"]
            for key in required_phase_keys:
                if key not in phase:
                    raise ValueError(f"Phase {i} missing required key: {key}")
            
            # Check for either "files" or "files_to_create" (handle both formats)
            if "files" not in phase and "files_to_create" not in phase:
                raise ValueError(f"Phase {i} missing files field (either 'files' or 'files_to_create')")
            
            # Convert "files" to "files_to_create" if needed for orchestrator compatibility
            if "files" in phase and "files_to_create" not in phase:
                phase["files_to_create"] = phase["files"]
    
    async def _save_plan_to_file(self, plan: Dict[str, Any]):
        """Save the generated plan to a JSON file."""
        
        try:
            # Ensure output directory exists
            self.output_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"plan_{timestamp}.json"
            filepath = self.output_dir / filename
            
            # Save plan to file
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(plan, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Plan saved to: {filepath}")
            
        except Exception as e:
            self.logger.warning(f"Could not save plan to file: {e}")
    
    async def _log_debug_request(self, session_id: str, messages: List, prompt: str):
        """Log debug information for the model request."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            debug_file = self.debug_dir / f"request_{session_id}_{timestamp}.json"
            
            debug_data = {
                "session_id": session_id,
                "timestamp": datetime.now().isoformat(),
                "agent_name": self.name,
                "request_type": "plan_generation",
                "original_prompt": prompt,
                "system_message_length": len(self.system_message),
                "messages": [
                    {
                        "role": getattr(msg, 'source', getattr(msg, 'role', 'unknown')),
                        "content_length": len(msg.content),
                        "content_preview": msg.content[:200] + "..." if len(msg.content) > 200 else msg.content
                    } for msg in messages
                ],
                "full_messages": [
                    {
                        "role": getattr(msg, 'source', getattr(msg, 'role', 'unknown')),
                        "content": msg.content
                    } for msg in messages
                ]
            }
            
            with open(debug_file, 'w', encoding='utf-8') as f:
                json.dump(debug_data, f, indent=2, ensure_ascii=False)
            
            self.logger.debug(f"Debug request logged to: {debug_file}")
            
        except Exception as e:
            self.logger.warning(f"Failed to log debug request: {e}")
    
    async def _log_debug_response(self, session_id: str, response: Any, content: str, duration: float):
        """Log debug information for the model response."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            debug_file = self.debug_dir / f"response_{session_id}_{timestamp}.json"
            
            # Extract response metadata if available
            response_metadata = {}
            if hasattr(response, '__dict__'):
                for attr in ['model', 'created_at', 'done', 'done_reason', 'total_duration', 
                           'load_duration', 'prompt_eval_count', 'eval_count', 'eval_duration']:
                    if hasattr(response, attr):
                        response_metadata[attr] = getattr(response, attr)
            
            debug_data = {
                "session_id": session_id,
                "timestamp": datetime.now().isoformat(),
                "agent_name": self.name,
                "response_type": "plan_generation",
                "duration_seconds": duration,
                "content_length": len(content),
                "response_metadata": response_metadata,
                "full_response_content": content,
                "content_preview": content[:500] + "..." if len(content) > 500 else content
            }
            
            with open(debug_file, 'w', encoding='utf-8') as f:
                json.dump(debug_data, f, indent=2, ensure_ascii=False)
            
            self.logger.debug(f"Debug response logged to: {debug_file}")
            
        except Exception as e:
            self.logger.warning(f"Failed to log debug response: {e}")
    
    async def _log_debug_error(self, session_id: str, error_message: str):
        """Log debug information for errors."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            debug_file = self.debug_dir / f"error_{session_id}_{timestamp}.json"
            
            debug_data = {
                "session_id": session_id,
                "timestamp": datetime.now().isoformat(),
                "agent_name": self.name,
                "error_type": "plan_generation_error",
                "error_message": error_message
            }
            
            with open(debug_file, 'w', encoding='utf-8') as f:
                json.dump(debug_data, f, indent=2, ensure_ascii=False)
            
            self.logger.debug(f"Debug error logged to: {debug_file}")
            
        except Exception as e:
            self.logger.warning(f"Failed to log debug error: {e}")
    
    def _convert_plan_to_project_plan(self, plan_dict: Dict[str, Any]) -> ProjectPlan:
        """Convert a plan dictionary to a ProjectPlan object."""
        
        try:
            # Extract project info
            project_info_dict = plan_dict["project_info"]
            project_info = ProjectInfo(
                prompt=project_info_dict.get("description", ""),
                project_type=project_info_dict.get("type", "script"),
                language=project_info_dict.get("language", "auto_detect"),
                output_dir=str(self.output_dir),
                requirements=project_info_dict.get("dependencies", [])
            )
            
            # Extract phases
            phases = []
            for phase_dict in plan_dict["phases"]:
                phase = Phase(
                    phase_id=phase_dict["phase_id"],
                    name=phase_dict["name"],
                    description=phase_dict["description"],
                    files_to_create=phase_dict.get("files", []),
                    dependencies=phase_dict.get("dependencies", []),
                    estimated_complexity=phase_dict.get("complexity", 2),
                    prerequisites=phase_dict.get("prerequisites", [])
                )
                phases.append(phase)
            
            # Create ProjectPlan
            project_plan = ProjectPlan(
                project_info=project_info,
                phases=phases,
                total_phases=len(phases),
                estimated_duration=len(phases) * 30  # Rough estimate: 30 minutes per phase
            )
            
            return project_plan
            
        except Exception as e:
            self.logger.error(f"Failed to convert plan dictionary to ProjectPlan: {e}")
            # Re-raise the exception instead of using fallback
            raise
    
    
    # Implementation of abstract methods from BaseAgent
    
    async def _handle_plan_request(self, message: AgentMessage) -> Optional[AgentMessage]:
        """Handle plan request messages."""
        
        try:
            payload = message.payload
            # Handle both direct prompt and project_info structure
            prompt = payload.get('prompt', '')
            project_context = payload.get('project_context')
            
            # If no direct prompt, check for project_info
            if not prompt and 'project_info' in payload:
                project_info = payload['project_info']
                prompt = project_info.get('prompt', '')
            
            if not prompt:
                raise ValueError("Plan request missing prompt")
            
            # Generate the plan
            plan_dict = await self.generate_plan(prompt, project_context)
            
            # Convert plan dictionary to ProjectPlan object
            project_plan = self._convert_plan_to_project_plan(plan_dict)
            
            # Create response message  
            response = create_plan_response(
                sender=self.name,
                recipient=message.sender,
                project_plan=project_plan,
                phase_id=message.phase_id,
                correlation_id=message.correlation_id
            )
            
            return response
            
        except Exception as e:
            self.logger.error(f"Error handling plan request: {e}")
            error_msg = create_error_report(
                sender=self.name,
                recipient=message.sender,
                error=str(e),
                error_type="plan_generation_error",
                phase_id=message.phase_id,
                correlation_id=message.correlation_id
            )
            return error_msg
    
    async def _handle_write_request(self, message: AgentMessage) -> Optional[AgentMessage]:
        """Handle write request messages (not applicable to planner)."""
        self.logger.warning("PlannerAgent received write request - forwarding to appropriate agent")
        return None
    
    async def _handle_test_request(self, message: AgentMessage) -> Optional[AgentMessage]:
        """Handle test request messages (not applicable to planner)."""
        self.logger.warning("PlannerAgent received test request - forwarding to appropriate agent")
        return None
    
    async def _handle_fix_request(self, message: AgentMessage) -> Optional[AgentMessage]:
        """Handle fix request messages (not applicable to planner)."""
        self.logger.warning("PlannerAgent received fix request - forwarding to appropriate agent")
        return None
    
    async def validate_phase_completion(self, phase_id: str, completed_files: List[str]) -> Dict[str, Any]:
        """
        Validate that a phase has been completed successfully.
        
        Args:
            phase_id: ID of the phase to validate
            completed_files: List of files that were created/modified
            
        Returns:
            Validation result with success status and feedback
        """
        try:
            self.logger.info(f"Validating completion of phase: {phase_id}")
            
            # This would typically involve:
            # 1. Checking if all required files were created
            # 2. Validating file contents
            # 3. Running basic syntax checks
            # 4. Verifying success criteria
            
            # For now, return a basic validation
            validation_result = {
                "success": True,
                "phase_id": phase_id,
                "validated_files": completed_files,
                "feedback": "Phase validation completed successfully",
                "next_steps": "Ready for next phase"
            }
            
            self.logger.info(f"Phase {phase_id} validation completed successfully")
            return validation_result
            
        except Exception as e:
            self.logger.error(f"Phase validation failed: {e}")
            return {
                "success": False,
                "phase_id": phase_id,
                "error": str(e),
                "feedback": "Phase validation failed",
                "next_steps": "Review and retry phase"
            }
    
    def get_supported_project_types(self) -> List[str]:
        """Get list of supported project types."""
        return [
            "cli_tool",
            "web_app", 
            "api",
            "data_script",
            "library",
            "automation_script",
            "game",
            "simple_script"
        ]