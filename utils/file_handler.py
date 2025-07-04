import asyncio
import os
import shutil
from pathlib import Path
from typing import Optional, Union
from datetime import datetime

from utils.logger import get_logger
from utils.code_extractor import CodeExtractor

class FileHandler:
    """Async file operations handler for LazyToCode."""
    
    def __init__(self, output_dir: Union[str, Path]):
        self.output_dir = Path(output_dir)
        self.logger = get_logger()
        self.code_extractor = CodeExtractor()
        
        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    async def read_prompt_file(self, file_path: Union[str, Path]) -> str:
        """Asynchronously read prompt from a text file."""
        
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"Prompt file not found: {file_path}")
        
        if not file_path.suffix.lower() == '.txt':
            raise ValueError(f"Only .txt files are supported for prompts: {file_path}")
        
        try:
            self.logger.debug(f"Reading prompt file: {file_path}")
            
            # Use asyncio to read file asynchronously
            loop = asyncio.get_event_loop()
            content = await loop.run_in_executor(
                None, 
                lambda: file_path.read_text(encoding='utf-8')
            )
            
            self.logger.info(f"Successfully read prompt file: {file_path}")
            return content.strip()
            
        except Exception as e:
            self.logger.error(f"Failed to read prompt file {file_path}: {e}")
            raise
    
    async def write_generated_code(self, 
                                 content: str, 
                                 filename: Optional[str] = None,
                                 language: Optional[str] = None,
                                 create_backup: bool = True,
                                 extract_code: bool = True,
                                 debug_mode: bool = False) -> Path:
        """Write generated code to output directory."""
        
        # Extract clean code if requested
        if extract_code:
            self.logger.debug("Extracting clean code from model response")
            detected_language, clean_code, extension = self.code_extractor.extract_and_clean(content, language)
            
            # Use detected language if none was provided
            if not language:
                language = detected_language
            
            # Use clean code
            content_to_write = clean_code
            
            self.logger.info(f"Code extraction complete: language={detected_language}, extension={extension}")
        else:
            content_to_write = content
            extension = self._get_file_extension(language, content)
        
        # Generate filename if not provided
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            if not extension.startswith('.'):
                extension = f".{extension}"
            filename = f"generated_code_{timestamp}{extension}"
        
        output_file = self.output_dir / filename
        
        # Create backup if file exists
        if create_backup and output_file.exists():
            await self._create_backup(output_file)
        
        try:
            self.logger.debug(f"Writing generated code to: {output_file}")
            
            # Use asyncio to write file asynchronously
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: output_file.write_text(content_to_write, encoding='utf-8')
            )
            
            self.logger.info(f"Successfully wrote generated code to: {output_file}")
            
            # Save full model response in debug mode
            if debug_mode and extract_code:
                await self._save_debug_response(content, output_file)
            
            return output_file
            
        except Exception as e:
            self.logger.error(f"Failed to write generated code to {output_file}: {e}")
            raise
    
    async def validate_output_directory(self) -> bool:
        """Validate output directory permissions and accessibility."""
        
        try:
            # Check if directory exists and is writable
            if not self.output_dir.exists():
                self.output_dir.mkdir(parents=True, exist_ok=True)
            
            # Test write permissions
            test_file = self.output_dir / ".write_test"
            test_file.write_text("test")
            test_file.unlink()
            
            self.logger.debug(f"Output directory validation passed: {self.output_dir}")
            return True
            
        except Exception as e:
            self.logger.error(f"Output directory validation failed: {e}")
            return False
    
    async def _save_debug_response(self, full_response: str, code_file: Path) -> Optional[Path]:
        """Save the full model response for debugging purposes."""
        
        try:
            # Create debug filename based on the code file
            debug_filename = f"{code_file.stem}_full_response.md"
            debug_path = code_file.parent / debug_filename
            
            # Create debug content with metadata
            debug_content = f"""# Full Model Response - Debug Log
Generated: {datetime.now().isoformat()}
Code File: {code_file.name}

---

{full_response}
"""
            
            # Write debug file
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: debug_path.write_text(debug_content, encoding='utf-8')
            )
            
            self.logger.info(f"Debug response saved to: {debug_path}")
            return debug_path
            
        except Exception as e:
            self.logger.warning(f"Failed to save debug response: {e}")
            return None

    async def _create_backup(self, file_path: Path) -> Optional[Path]:
        """Create a backup of existing file."""
        
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"{file_path.stem}.backup_{timestamp}{file_path.suffix}"
            backup_path = file_path.parent / backup_name
            
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: shutil.copy2(file_path, backup_path)
            )
            
            self.logger.info(f"Created backup: {backup_path}")
            return backup_path
            
        except Exception as e:
            self.logger.warning(f"Failed to create backup for {file_path}: {e}")
            return None
    
    def _get_file_extension(self, language: Optional[str], content: str) -> str:
        """Determine file extension based on language or content."""
        
        if language:
            language = language.lower()
            extensions = {
                'python': '.py',
                'javascript': '.js',
                'typescript': '.ts',
                'java': '.java',
                'c++': '.cpp',
                'c': '.c',
                'rust': '.rs',
                'go': '.go',
                'html': '.html',
                'css': '.css',
                'json': '.json',
                'yaml': '.yaml',
                'yml': '.yml',
                'markdown': '.md',
                'sql': '.sql',
                'bash': '.sh',
                'shell': '.sh'
            }
            return extensions.get(language, '.txt')
        
        # Try to detect from content
        content_lower = content.lower()
        
        if '#!/usr/bin/env python' in content or 'import ' in content or 'def ' in content:
            return '.py'
        elif 'function ' in content or 'const ' in content or 'let ' in content:
            return '.js'
        elif 'public class ' in content or 'import java.' in content:
            return '.java'
        elif '#include' in content:
            return '.cpp' if 'iostream' in content else '.c'
        elif '<!DOCTYPE html>' in content or '<html' in content:
            return '.html'
        elif 'SELECT ' in content.upper() or 'CREATE TABLE' in content.upper():
            return '.sql'
        elif '#!/bin/bash' in content or '#!/bin/sh' in content:
            return '.sh'
        
        return '.txt'
    
    def get_output_directory(self) -> Path:
        """Get the configured output directory."""
        return self.output_dir
    
    def list_generated_files(self) -> list[Path]:
        """List all files in the output directory."""
        try:
            return [f for f in self.output_dir.iterdir() if f.is_file()]
        except Exception as e:
            self.logger.error(f"Failed to list files in output directory: {e}")
            return []
    
    async def write_file(self, file_path: Union[str, Path], content: str) -> Path:
        """Write content to a specific file path."""
        file_path = Path(file_path)
        
        try:
            # Ensure parent directory exists
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Use asyncio to write file asynchronously
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: file_path.write_text(content, encoding='utf-8')
            )
            
            self.logger.debug(f"Successfully wrote file: {file_path}")
            return file_path
            
        except Exception as e:
            self.logger.error(f"Failed to write file {file_path}: {e}")
            raise