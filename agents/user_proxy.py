from typing import Optional
from pathlib import Path

# Import from autogen-core
from autogen_core import RoutedAgent, message_handler

from utils.logger import get_logger
from utils.file_handler import FileHandler

class UserProxy(RoutedAgent):
    """User Proxy Agent that manages task coordination and user interaction."""
    
    def __init__(self, 
                 name: str = "UserProxy",
                 output_dir: Optional[Path] = None,
                 **kwargs):
        
        super().__init__(name)
        
        self.logger = get_logger()
        self.output_dir = output_dir or Path("./output")
        self.file_handler = FileHandler(self.output_dir)
        
        self.logger.info(f"UserProxy '{name}' initialized with output directory: {self.output_dir}")
    
    async def process_user_prompt(self, prompt: str, prompt_type: str = "text") -> dict:
        """Process user prompt and prepare for agent interaction."""
        
        try:
            self.logger.info(f"Processing user prompt (type: {prompt_type})")
            
            # Validate output directory
            is_valid = await self.file_handler.validate_output_directory()
            if not is_valid:
                raise RuntimeError(f"Output directory is not accessible: {self.output_dir}")
            
            # Prepare task information
            task_info = {
                "prompt": prompt,
                "prompt_type": prompt_type,
                "output_dir": str(self.output_dir),
                "timestamp": self._get_timestamp()
            }
            
            self.logger.debug(f"Task info prepared: {task_info}")
            return task_info
            
        except Exception as e:
            self.logger.error(f"Failed to process user prompt: {e}")
            raise
    
    async def coordinate_code_generation(self, coding_assistant, task_info: dict) -> dict:
        """Coordinate code generation with the coding assistant."""
        
        try:
            self.logger.info("Starting code generation coordination")
            
            # Extract prompt from task info
            prompt = task_info["prompt"]
            
            # Generate code using the coding assistant
            generated_code = await coding_assistant.generate_code(prompt)
            
            # Prepare result
            result = {
                "generated_code": generated_code,
                "task_info": task_info,
                "status": "success"
            }
            
            self.logger.info("Code generation coordination completed successfully")
            return result
            
        except Exception as e:
            self.logger.error(f"Code generation coordination failed: {e}")
            result = {
                "generated_code": None,
                "task_info": task_info,
                "status": "failed",
                "error": str(e)
            }
            return result
    
    async def save_generated_code(self, result: dict, filename: Optional[str] = None, debug_mode: bool = False) -> Optional[Path]:
        """Save generated code to output directory."""
        
        if result["status"] != "success" or not result["generated_code"]:
            self.logger.warning("No code to save - generation failed or produced no output")
            return None
        
        try:
            self.logger.info("Saving generated code to file")
            
            # Save the generated code
            output_file = await self.file_handler.write_generated_code(
                content=result["generated_code"],
                filename=filename,
                debug_mode=debug_mode
            )
            
            self.logger.info(f"Generated code saved to: {output_file}")
            return output_file
            
        except Exception as e:
            self.logger.error(f"Failed to save generated code: {e}")
            raise
    
    async def execute_workflow(self, 
                             coding_assistant, 
                             prompt: str, 
                             prompt_type: str = "text",
                             output_filename: Optional[str] = None,
                             debug_mode: bool = False) -> dict:
        """Execute the complete workflow from prompt to saved code."""
        
        try:
            self.logger.info("Starting complete workflow execution")
            
            # Step 1: Process user prompt
            task_info = await self.process_user_prompt(prompt, prompt_type)
            
            # Step 2: Coordinate code generation
            result = await self.coordinate_code_generation(coding_assistant, task_info)
            
            # Step 3: Save generated code (if successful)
            output_file = None
            if result["status"] == "success":
                output_file = await self.save_generated_code(result, output_filename, debug_mode)
            
            # Prepare final result
            final_result = {
                **result,
                "output_file": str(output_file) if output_file else None,
                "workflow_status": "completed"
            }
            
            self.logger.info("Workflow execution completed")
            return final_result
            
        except Exception as e:
            self.logger.error(f"Workflow execution failed: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "output_file": None,
                "workflow_status": "failed"
            }
    
    def _get_timestamp(self) -> str:
        """Get current timestamp string."""
        from datetime import datetime
        return datetime.now().isoformat()
    
    def get_output_directory(self) -> Path:
        """Get the configured output directory."""
        return self.output_dir
    
    def set_output_directory(self, output_dir: Path) -> None:
        """Set the output directory."""
        self.output_dir = output_dir
        self.file_handler = FileHandler(output_dir)
        self.logger.info(f"Output directory updated to: {output_dir}")
    
    async def get_generation_summary(self) -> dict:
        """Get summary of generated files in output directory."""
        
        try:
            files = self.file_handler.list_generated_files()
            
            summary = {
                "output_directory": str(self.output_dir),
                "total_files": len(files),
                "files": [
                    {
                        "name": f.name,
                        "path": str(f),
                        "size": f.stat().st_size if f.exists() else 0,
                        "modified": f.stat().st_mtime if f.exists() else 0
                    }
                    for f in files
                ]
            }
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Failed to get generation summary: {e}")
            return {
                "output_directory": str(self.output_dir),
                "total_files": 0,
                "files": [],
                "error": str(e)
            }