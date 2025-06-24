from typing import Optional
from pathlib import Path

# Import from autogen-core
from autogen_core import RoutedAgent, message_handler
from autogen_core.models import UserMessage, SystemMessage

from utils.logger import get_logger

class CodingAssistant(RoutedAgent):
    """AI Coding Assistant Agent that generates code based on prompts."""
    
    def __init__(self, 
                 name: str = "CodingAssistant",
                 model_client=None,
                 output_dir: Optional[Path] = None,
                 **kwargs):
        
        super().__init__(name)
        
        self.logger = get_logger()
        self.output_dir = output_dir or Path("./output")
        self.model_client = model_client
        
        # System message for the coding assistant
        self.system_message = self._create_system_message()
        
        self.logger.info(f"CodingAssistant '{name}' initialized with output directory: {self.output_dir}")
    
    def _create_system_message(self) -> str:
        """Create system message for the coding assistant."""
        
        return f"""You are an expert AI coding assistant. Your role is to generate high-quality, well-documented code based on user prompts.

GUIDELINES:
1. Always write clean, readable, and well-commented code
2. Follow best practices for the programming language being used
3. Include proper error handling and input validation
4. Add docstrings and comments to explain complex logic
5. Consider security implications and avoid vulnerable patterns
6. Structure code logically with appropriate functions/classes
7. Include example usage when appropriate

CODE QUALITY STANDARDS:
- Use meaningful variable and function names
- Follow language-specific style conventions (PEP 8 for Python, etc.)
- Keep functions focused and single-purpose
- Handle edge cases and potential errors
- Write efficient and maintainable code

OUTPUT FORMAT:
- Provide complete, runnable code
- Include necessary imports and dependencies
- Add brief explanations for complex implementations
- Suggest improvements or alternative approaches when relevant

OUTPUT DIRECTORY: {self.output_dir}

When generating code, consider the context and requirements carefully. Ask for clarification if the prompt is ambiguous or lacks necessary details."""
    
    async def generate_code(self, prompt: str, language: Optional[str] = None) -> str:
        """Generate code based on the given prompt."""
        
        try:
            self.logger.info(f"Generating code for prompt: {prompt[:100]}...")
            
            # Enhance prompt with language specification if provided
            enhanced_prompt = prompt
            if language:
                enhanced_prompt = f"Generate {language} code for the following request:\n\n{prompt}"
            
            # This would be the main interaction with the model
            # The actual implementation depends on the autogen-core API
            response = await self._process_prompt(enhanced_prompt)
            
            self.logger.info("Code generation completed successfully")
            return response
            
        except Exception as e:
            self.logger.error(f"Failed to generate code: {e}")
            raise
    
    async def _process_prompt(self, prompt: str) -> str:
        """Process the prompt using the model client."""
        
        try:
            self.logger.debug("Processing prompt with model client")
            
            if self.model_client is None:
                raise ValueError("Model client not initialized")
            
            # Create the messages for the chat completion
            messages = [
                SystemMessage(content=self.system_message, source="system"),
                UserMessage(content=prompt, source="user")
            ]
            
            # Call the model client to generate a response
            self.logger.debug("About to call model client.create()")
            try:
                response = await self.model_client.create(messages)
                self.logger.debug("Model client call completed")
            except Exception as model_error:
                self.logger.error(f"Model client call failed: {model_error}")
                raise
            
            # Log response for debugging
            self.logger.debug(f"Response type: {type(response)}")
            self.logger.debug(f"Response finish_reason: {getattr(response, 'finish_reason', 'N/A')}")
            
            # Extract content from CreateResult
            if hasattr(response, 'content'):
                content = response.content
                self.logger.debug(f"Generated content length: {len(content)} characters")
                return content
            else:
                raise ValueError(f"Could not extract content from response: {response}")
                
        except Exception as e:
            self.logger.error(f"Error processing prompt with model client: {e}")
            # Fallback to placeholder if model fails
            return f"""# Error: Model client failed to generate code
# Prompt: {prompt}
# Error: {str(e)}

def placeholder_function():
    '''
    This is a placeholder function because the model client failed.
    Error: {str(e)}
    '''
    print("Hello, World!")
    pass

if __name__ == "__main__":
    placeholder_function()
"""
    
    def set_output_directory(self, output_dir: Path) -> None:
        """Set the output directory for generated code."""
        self.output_dir = output_dir
        self.logger.info(f"Output directory updated to: {output_dir}")
    
    def get_supported_languages(self) -> list[str]:
        """Get list of supported programming languages."""
        return [
            "python", "javascript", "typescript", "java", "c++", "c", 
            "rust", "go", "html", "css", "sql", "bash", "shell",
            "json", "yaml", "markdown"
        ]
    
    def validate_language(self, language: str) -> bool:
        """Validate if the specified language is supported."""
        return language.lower() in [lang.lower() for lang in self.get_supported_languages()]