"""
Writer Agent

Enhanced agent for multi-file project generation based on detailed plans.
Uses the existing coding assistant as a foundation but adds plan-following
capabilities and multi-file project generation.
"""

import json
import asyncio
from typing import Optional, Dict, Any, List
from pathlib import Path
from datetime import datetime

from autogen_core import RoutedAgent, message_handler
from autogen_core.models import UserMessage, SystemMessage

from utils.agent_messages import (
    AgentMessage, MessageType, ProjectFiles, FileContent, Phase, ProjectInfo,
    create_write_response, create_status_update, AgentStatus
)
from utils.logger import get_agent_logger, LogContext, log_model_interaction
from utils.file_handler import FileHandler


class WriterAgent(RoutedAgent):
    """Writer Agent for multi-file project generation following detailed plans."""
    
    def __init__(self, 
                 name: str = "WriterAgent",
                 model_client=None,
                 output_dir: Optional[Path] = None,
                 **kwargs):
        
        super().__init__(name)
        
        self.name = name
        self.agent_type = "writer"
        self.output_dir = Path(output_dir) if output_dir else Path("./output")
        
        # Enhanced logging with agent-specific logger
        debug_dir = self.output_dir / "debug" if output_dir else Path("./debug")
        self.logger = get_agent_logger("writer", debug_dir)
        self.model_client = model_client
        self.file_handler = FileHandler(self.output_dir)
        
        # Agent state
        self.current_phase_id = None
        self.current_project_info = None
        self.plan_json_path = None
        self.status = AgentStatus.IDLE
        
        # System message for the writer agent
        self.system_message = self._create_system_message()
        
        self.logger.info(f"WriterAgent '{name}' initialized with output directory: {self.output_dir}",
                        extra={'agent_name': 'writer'})
    
    def _create_system_message(self) -> str:
        """Create system message for the writer agent."""
        
        return f"""You are an expert AI Writer Agent specialized in multi-file project generation. Your role is to create complete, well-structured projects based on detailed implementation plans.

CORE RESPONSIBILITIES:
1. Read and understand detailed project plans from JSON files
2. Generate multiple files according to the plan specifications
3. Follow project structure and file organization requirements exactly
4. Incorporate feedback from Reviewer Agent to improve generated code
5. Ensure all files work together as a cohesive project
6. Intelligently determine the appropriate programming language and technology stack from the project requirements

CODE GENERATION GUIDELINES:
1. Always write clean, readable, and well-commented code
2. Follow best practices for the programming language being used (determined from project context)
3. Include proper error handling and input validation
4. Add docstrings and comments to explain complex logic
5. Consider security implications and avoid vulnerable patterns
6. Structure code logically with appropriate functions/classes
7. Ensure files have proper imports and dependencies

PLAN ADHERENCE:
1. Read the plan JSON file to understand requirements for each phase
2. Generate EXACTLY the files specified in the current phase
3. Follow the success criteria defined in the plan
4. Use the project structure and naming conventions from the plan
5. Include all dependencies and requirements specified

MULTI-FILE PROJECT STRUCTURE:
1. Create files in the correct directory structure
2. Ensure proper imports between files
3. Maintain consistency in coding style across all files
4. Include necessary configuration files (requirements.txt, etc.)
5. Create executable entry points where needed

FEEDBACK INTEGRATION:
1. When receiving feedback from Reviewer Agent, read it carefully
2. Identify specific issues mentioned in the feedback
3. Modify existing files or create new files as needed
4. Address all feedback points systematically
5. Maintain existing functionality while making improvements

OUTPUT DIRECTORY: {self.output_dir}

Always generate complete, runnable code that follows the project plan precisely. Ask for clarification only if the plan contains contradictory or unclear requirements."""
    
    @message_handler
    async def handle_message(self, message: AgentMessage, ctx: Any) -> AgentMessage:
        """Handle incoming messages from other agents."""
        
        try:
            extra = {'agent_name': 'writer'}
            self.logger.info(f"WriterAgent received {message.message_type.value} from {message.sender}", extra=extra)
            
            if message.message_type == MessageType.WRITE_REQUEST:
                return await self._handle_write_request(message)
            else:
                self.logger.warning(f"Unsupported message type: {message.message_type}", 
                                  extra={'agent_name': 'writer'})
                return self._create_error_response(message, "Unsupported message type")
                
        except Exception as e:
            self.logger.error(f"Error handling message: {str(e)}", 
                            extra={'agent_name': 'writer'}, exc_info=True)
            return self._create_error_response(message, str(e))
    
    async def _handle_write_request(self, message: AgentMessage) -> AgentMessage:
        """Handle write request from orchestrator."""
        
        with LogContext(self.logger, "handle_write_request", "writer") as ctx:
            try:
                self.status = AgentStatus.WORKING
                self.current_phase_id = message.phase_id
                
                ctx.add_data("phase_id", message.phase_id)
                ctx.add_data("correlation_id", message.correlation_id)
            
                # Extract phase and project info from message
                phase_data = message.payload.get("phase")
                project_info_data = message.payload.get("project_info")
                feedback = message.payload.get("feedback")  # From reviewer agent
                
                self.logger.debug(f"Processing write request with feedback: {bool(feedback)}",
                                extra={'agent_name': 'writer', 'structured_data': {
                                    'has_feedback': bool(feedback),
                                    'feedback_length': len(feedback) if feedback else 0,
                                    'phase_data_keys': list(phase_data.keys()) if phase_data else [],
                                    'project_info_keys': list(project_info_data.keys()) if project_info_data else []
                                }})
                
                if feedback:
                    self.logger.info(f"Incorporating reviewer feedback: {feedback[:100]}{'...' if len(feedback) > 100 else ''}",
                                   extra={'agent_name': 'writer', 'structured_data': {
                                       'full_feedback': feedback
                                   }})
                
                if not phase_data or not project_info_data:
                    raise ValueError("Missing phase or project_info in write request")
            
                # Convert back to objects
                phase = Phase(**phase_data)
                project_info = ProjectInfo(**project_info_data)
                self.current_project_info = project_info
                
                ctx.add_data("phase_name", phase.name)
                ctx.add_data("project_prompt", project_info.prompt)
                
                # Load the plan JSON to get detailed requirements
                plan_data = await self._load_plan_json()
                
                # Generate files for this phase
                project_files = await self._generate_phase_files(phase, project_info, plan_data, feedback)
                
                # Save files to disk
                await self._save_files_to_disk(project_files)
                
                ctx.add_data("files_generated", len(project_files.files))
                ctx.add_data("file_names", [f.filename for f in project_files.files])
            
                self.status = AgentStatus.COMPLETED
                
                # Create successful response
                response = create_write_response(
                    sender=self.name,
                    recipient=message.sender,
                    project_files=project_files,
                    phase_id=message.phase_id,
                    correlation_id=message.correlation_id
                )
                
                self.logger.info(f"Successfully generated {len(project_files.files)} files for phase {phase.phase_id}",
                               extra={'agent_name': 'writer', 'structured_data': {
                                   'files_generated': [{
                                       'filename': f.filename,
                                       'size': len(f.content),
                                       'language': f.language,
                                       'type': f.file_type
                                   } for f in project_files.files]
                               }})
                return response
            
            except Exception as e:
                self.status = AgentStatus.ERROR
                self.logger.error(f"Failed to handle write request: {str(e)}", 
                                extra={'agent_name': 'writer'}, exc_info=True)
                return self._create_error_response(message, str(e))
    
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
                           extra={'agent_name': 'writer'})
            
            with open(latest_plan_file, 'r', encoding='utf-8') as f:
                plan_data = json.load(f)
            
            return plan_data
            
        except Exception as e:
            self.logger.error(f"Failed to load plan JSON: {str(e)}", 
                            extra={'agent_name': 'writer'}, exc_info=True)
            raise
    
    async def _generate_phase_files(self, phase: Phase, project_info: ProjectInfo, 
                                   plan_data: Dict[str, Any], feedback: Optional[str] = None) -> ProjectFiles:
        """Generate all files for a specific phase based on the plan."""
        
        with LogContext(self.logger, f"generate_phase_files_{phase.phase_id}", "writer") as ctx:
            try:
                self.logger.info(f"Generating files for phase: {phase.name}", 
                               extra={'agent_name': 'writer'})
                
                ctx.add_data("phase_id", phase.phase_id)
                ctx.add_data("phase_name", phase.name)
                ctx.add_data("has_feedback", feedback is not None)
            
                # Find the specific phase details in the plan
                phase_details = self._find_phase_in_plan(phase.phase_id, plan_data)
                if not phase_details:
                    raise ValueError(f"Phase {phase.phase_id} not found in plan")
                
                files_to_create = phase_details.get("files", [])
                ctx.add_data("files_to_create", files_to_create)
                
                self.logger.debug(f"Phase details found: {len(files_to_create)} files to create",
                                extra={'agent_name': 'writer', 'structured_data': {
                                    'phase_details': phase_details,
                                    'files_to_create_count': len(files_to_create)
                                }})
                
                generated_files = []
                
                # Generate each file specified in the phase
                for i, file_spec in enumerate(files_to_create):
                    self.logger.debug(f"Generating file {i+1}/{len(files_to_create)}: {file_spec}",
                                    extra={'agent_name': 'writer'})
                    
                    file_content = await self._generate_single_file(
                        file_spec, phase_details, project_info, plan_data, feedback
                    )
                    if file_content:
                        generated_files.append(file_content)
                        self.logger.debug(f"Generated file: {file_content.filename} ({len(file_content.content)} chars)",
                                        extra={'agent_name': 'writer'})
            
                # Create project files object
                project_files = ProjectFiles(
                    files=generated_files,
                    phase_id=phase.phase_id,
                    dependencies=phase_details.get("dependencies", [])
                )
                
                ctx.add_data("generated_files_count", len(generated_files))
                
                return project_files
            
            except Exception as e:
                self.logger.error(f"Failed to generate phase files: {str(e)}", 
                                extra={'agent_name': 'writer'}, exc_info=True)
                raise
    
    def _find_phase_in_plan(self, phase_id: str, plan_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Find specific phase details in the plan data."""
        
        phases = plan_data.get("phases", [])
        for phase in phases:
            if phase.get("phase_id") == phase_id:
                return phase
        
        return None
    
    async def _generate_single_file(self, file_spec: Any, phase_details: Dict[str, Any], 
                                   project_info: ProjectInfo, plan_data: Dict[str, Any],
                                   feedback: Optional[str] = None) -> FileContent:
        """Generate a single file based on the file specification."""
        
        with LogContext(self.logger, f"generate_single_file_{file_spec}", "writer") as ctx:
            try:
                # Handle different file specification formats
                if isinstance(file_spec, str):
                    filename = file_spec
                    file_requirements = f"Create {filename} according to the project requirements"
                elif isinstance(file_spec, dict):
                    filename = file_spec.get("name", file_spec.get("filename", "unknown.py"))
                    file_requirements = file_spec.get("description", file_spec.get("requirements", ""))
                else:
                    filename = str(file_spec)
                    file_requirements = f"Create {filename} according to the project requirements"
                
                ctx.add_data("filename", filename)
                ctx.add_data("file_requirements", file_requirements)
                
                self.logger.debug(f"Generating file: {filename}", 
                                extra={'agent_name': 'writer'})
            
                # Create detailed prompt for this file
                prompt = self._create_file_generation_prompt(
                    filename, file_requirements, phase_details, project_info, plan_data, feedback
                )
                
                ctx.add_data("prompt_length", len(prompt))
                
                # Generate file content using the model
                raw_content = await self._generate_code_with_model(prompt, filename)
                
                # Clean the content to remove markdown formatting and explanatory text
                content = self._clean_generated_content(raw_content, filename)
                
                ctx.add_data("raw_content_length", len(raw_content))
                ctx.add_data("cleaned_content_length", len(content))
                
                # Determine file type and language
                file_extension = Path(filename).suffix.lower()
                language = self._determine_language(file_extension)
                file_type = self._determine_file_type(file_extension)
                
                return FileContent(
                    filename=filename,
                    content=content,
                    file_type=file_type,
                    language=language
                )
                
            except Exception as e:
                self.logger.error(f"Failed to generate file {file_spec}: {str(e)}", 
                                extra={'agent_name': 'writer'}, exc_info=True)
                # Return placeholder file to maintain workflow
                return FileContent(
                    filename=str(file_spec),
                    content=f"# Error generating {file_spec}: {str(e)}\n# TODO: Fix this file\n",
                    file_type="code",
                    language="python"
                )
    
    def _create_file_generation_prompt(self, filename: str, file_requirements: str,
                                      phase_details: Dict[str, Any], project_info: ProjectInfo,
                                      plan_data: Dict[str, Any], feedback: Optional[str] = None) -> str:
        """Create a detailed prompt for generating a specific file."""
        
        prompt_parts = [
            f"Generate the file '{filename}' for this project (determine appropriate language from context).",
            f"\nProject Description: {project_info.prompt}",
            f"\nPhase: {phase_details.get('name', 'Unknown Phase')}",
            f"Phase Description: {phase_details.get('description', '')}",
            f"\nFile Requirements: {file_requirements}",
        ]
        
        # Add success criteria if available
        success_criteria = phase_details.get("success_criteria", [])
        if success_criteria:
            prompt_parts.append(f"\nSuccess Criteria for this phase:")
            for i, criteria in enumerate(success_criteria, 1):
                prompt_parts.append(f"{i}. {criteria}")
        
        # Add project structure context
        all_files = []
        for phase in plan_data.get("phases", []):
            all_files.extend(phase.get("files", []))
        
        if all_files:
            prompt_parts.append(f"\nProject Structure (all files to be created):")
            for file_item in all_files:
                file_name = file_item if isinstance(file_item, str) else file_item.get("name", str(file_item))
                prompt_parts.append(f"- {file_name}")
        
        # Add dependencies
        dependencies = phase_details.get("dependencies", [])
        if dependencies:
            prompt_parts.append(f"\nDependencies required: {', '.join(dependencies)}")
        
        # Add feedback if provided
        if feedback:
            prompt_parts.append(f"\nReviewer Feedback to Address:")
            prompt_parts.append(feedback)
            prompt_parts.append("\nPlease address all feedback points in the generated code.")
        
        # Add specific instructions
        prompt_parts.extend([
            f"\nIMPORTANT INSTRUCTIONS:",
            f"1. Generate ONLY the content for '{filename}' - no other files",
            f"2. Return ONLY the raw file content - NO markdown code blocks (```), NO explanations",
            f"3. Do NOT include markdown formatting like ```python or ``` at the beginning/end",
            f"4. Do NOT add explanatory text or sections after the code",
            f"5. Include proper imports and dependencies",
            f"6. Add comprehensive docstrings and comments within the code",
            f"7. Follow best practices for the programming language (use context to determine language)",
            f"8. Ensure the file integrates well with other project files",
            f"9. Include error handling where appropriate",
            f"10. Make the code production-ready and maintainable",
            f"\nReturn the file content as if you're writing directly to the file - clean, executable code only."
        ])
        
        return "\n".join(prompt_parts)
    
    async def _generate_code_with_model(self, prompt: str, filename: str = "unknown") -> str:
        """Generate code using the model client."""
        
        import time
        start_time = time.time()
        
        try:
            if self.model_client is None:
                raise ValueError("Model client not initialized")
            
            self.logger.debug(f"Model client validated for {filename}: {type(self.model_client).__name__}", 
                            extra={'agent_name': 'writer', 'structured_data': {
                                'model_client_type': type(self.model_client).__name__,
                                'model_client_available': self.model_client is not None,
                                'filename': filename
                            }})
            
            messages = [
                SystemMessage(content=self.system_message, source="system"),
                UserMessage(content=prompt, source="user")
            ]
            
            self.logger.debug(f"Calling model client to generate code for {filename}...", 
                            extra={'agent_name': 'writer'})
            
            response = await self.model_client.create(messages)
            
            duration = time.time() - start_time
            
            if hasattr(response, 'content'):
                content = response.content
                
                # Log the model interaction with full details
                log_model_interaction(
                    self.logger, 
                    "writer", 
                    f"generate_code_{filename}",
                    {
                        "messages": [{
                            "role": "system",
                            "content": self.system_message[:500] + "..." if len(self.system_message) > 500 else self.system_message
                        }, {
                            "role": "user", 
                            "content": prompt
                        }],
                        "full_prompt": prompt,
                        "filename": filename
                    },
                    {
                        "content": content,
                        "content_length": len(content),
                        "filename": filename
                    },
                    duration
                )
                
                return content
            else:
                raise ValueError(f"Could not extract content from response: {response}")
                
        except Exception as e:
            duration = time.time() - start_time
            self.logger.error(f"Error generating code with model for {filename}: {str(e)}", 
                            extra={'agent_name': 'writer'}, exc_info=True)
            
            # Log the failed attempt
            log_model_interaction(
                self.logger,
                "writer",
                f"generate_code_{filename}_FAILED",
                {"filename": filename, "prompt_length": len(prompt)},
                {"error": str(e)},
                duration
            )
            
            # Return placeholder code
            return f"""# Error: Failed to generate code using model
# Error: {str(e)}

def placeholder():
    '''
    This is a placeholder because code generation failed.
    Please implement the required functionality here.
    '''
    pass

if __name__ == "__main__":
    placeholder()
"""
    
    def _determine_language(self, file_extension: str) -> str:
        """Determine programming language from file extension."""
        
        language_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.java': 'java',
            '.cpp': 'cpp',
            '.c': 'c',
            '.rs': 'rust',
            '.go': 'go',
            '.html': 'html',
            '.css': 'css',
            '.sql': 'sql',
            '.sh': 'bash',
            '.json': 'json',
            '.yaml': 'yaml',
            '.yml': 'yaml',
            '.md': 'markdown',
            '.txt': 'text'
        }
        
        return language_map.get(file_extension, 'text')
    
    def _determine_file_type(self, file_extension: str) -> str:
        """Determine file type from extension."""
        
        if file_extension in ['.py', '.js', '.ts', '.java', '.cpp', '.c', '.rs', '.go']:
            return 'code'
        elif file_extension in ['.html', '.css']:
            return 'web'
        elif file_extension in ['.json', '.yaml', '.yml']:
            return 'config'
        elif file_extension in ['.md', '.txt']:
            return 'documentation'
        elif file_extension in ['.sql']:
            return 'database'
        elif file_extension in ['.sh']:
            return 'script'
        else:
            return 'text'
    
    def _clean_generated_content(self, raw_content: str, filename: str) -> str:
        """Clean generated content by removing markdown formatting and explanatory text."""
        
        try:
            # Determine if this is a code file
            file_extension = Path(filename).suffix.lower()
            is_code_file = file_extension in ['.py', '.js', '.ts', '.java', '.cpp', '.c', '.rs', '.go', '.sh']
            
            # For non-code files (like README.md), return as-is after basic cleanup
            if not is_code_file:
                # Just remove any markdown code blocks if they exist
                content = raw_content
                if content.startswith('```'):
                    lines = content.split('\n')
                    # Remove first line if it's a markdown code block start
                    if lines[0].startswith('```'):
                        lines = lines[1:]
                    # Remove last lines that might be markdown code block end or explanations
                    while lines and (lines[-1].startswith('```') or lines[-1].strip() == '' or lines[-1].startswith('###')):
                        lines.pop()
                    content = '\n'.join(lines)
                return content.strip()
            
            # For code files, perform more aggressive cleaning
            content = raw_content.strip()
            
            # Remove markdown code blocks
            if content.startswith('```'):
                lines = content.split('\n')
                
                # Remove the opening code block (e.g., ```python)
                if lines[0].startswith('```'):
                    lines = lines[1:]
                
                # Find and remove the closing code block and any explanatory text after it
                cleaned_lines = []
                found_closing_block = False
                
                for line in lines:
                    if line.strip() == '```' or line.startswith('```'):
                        found_closing_block = True
                        break
                    elif line.startswith('###') or line.startswith('## '):
                        # Stop at explanatory sections
                        break
                    else:
                        cleaned_lines.append(line)
                
                content = '\n'.join(cleaned_lines)
            
            # Remove common explanatory sections that might appear after code
            lines = content.split('\n')
            cleaned_lines = []
            
            for line in lines:
                # Stop at explanation sections
                if (line.startswith('### Explanation') or 
                    line.startswith('## Explanation') or
                    line.startswith('### Usage') or
                    line.startswith('## Usage') or
                    line.startswith('### Key Features') or
                    line.startswith('This script') or
                    line.startswith('This file') or
                    line.startswith('The above')):
                    break
                cleaned_lines.append(line)
            
            content = '\n'.join(cleaned_lines)
            
            # Final cleanup - remove trailing whitespace and ensure single trailing newline
            content = content.rstrip() + '\n' if content.strip() else ''
            
            self.logger.debug(f"Cleaned content for {filename}: {len(raw_content)} -> {len(content)} chars", 
                            extra={'agent_name': 'writer', 'structured_data': {
                                'filename': filename,
                                'raw_length': len(raw_content),
                                'cleaned_length': len(content),
                                'had_markdown': '```' in raw_content,
                                'had_explanation': any(keyword in raw_content.lower() for keyword in ['explanation', 'usage', 'key features'])
                            }})
            
            return content
            
        except Exception as e:
            self.logger.error(f"Error cleaning content for {filename}: {str(e)}", 
                            extra={'agent_name': 'writer'}, exc_info=True)
            # Return raw content if cleaning fails
            return raw_content
    
    async def _save_files_to_disk(self, project_files: ProjectFiles) -> None:
        """Save generated files to the output directory."""
        
        try:
            # Create output directory if it doesn't exist
            self.output_dir.mkdir(parents=True, exist_ok=True)
            
            for file_content in project_files.files:
                file_path = self.output_dir / file_content.filename
                
                # Create parent directories if needed
                file_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Write file content
                await self.file_handler.write_file(file_path, file_content.content)
                
                self.logger.info(f"Saved file: {file_path}", 
                               extra={'agent_name': 'writer'})
            
        except Exception as e:
            self.logger.error(f"Failed to save files to disk: {str(e)}", 
                            extra={'agent_name': 'writer'}, exc_info=True)
            raise
    
    def _create_error_response(self, original_message: AgentMessage, error: str) -> AgentMessage:
        """Create an error response message."""
        
        return AgentMessage(
            message_type=MessageType.WRITE_RESPONSE,
            sender=self.name,
            recipient=original_message.sender,
            payload={
                "error": error,
                "success": False
            },
            phase_id=original_message.phase_id,
            timestamp=datetime.now(),
            correlation_id=original_message.correlation_id
        )
    
    def get_status(self) -> AgentStatus:
        """Get current agent status."""
        return self.status
    
    def set_output_directory(self, output_dir: Path) -> None:
        """Set the output directory for generated files."""
        self.output_dir = Path(output_dir)
        self.logger.info(f"Output directory updated to: {output_dir}", 
                       extra={'agent_name': 'writer'})
    
    async def cleanup(self):
        """Cleanup resources."""
        self.logger.info("WriterAgent cleanup completed", 
                       extra={'agent_name': 'writer'})