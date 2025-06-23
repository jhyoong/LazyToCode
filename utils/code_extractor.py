import re
from typing import Optional, Tuple, List
from utils.logger import get_logger

class CodeExtractor:
    """Extract clean code from model responses that may contain explanations and markdown."""
    
    def __init__(self):
        self.logger = get_logger()
        
        # Pattern to match markdown code blocks
        self.code_block_pattern = re.compile(
            r'```(?P<language>\w+)?\s*\n(?P<code>.*?)\n```',
            re.DOTALL | re.MULTILINE
        )
        
        # Pattern to match inline code
        self.inline_code_pattern = re.compile(r'`([^`]+)`')
        
        # Common programming language extensions
        self.language_extensions = {
            'python': '.py',
            'javascript': '.js',
            'typescript': '.ts',
            'java': '.java',
            'c++': '.cpp',
            'cpp': '.cpp',
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
            'shell': '.sh',
            'sh': '.sh'
        }
    
    def extract_code_blocks(self, content: str) -> List[Tuple[Optional[str], str]]:
        """Extract all code blocks from the content.
        
        Returns:
            List of tuples (language, code) for each code block found
        """
        code_blocks = []
        
        # Find all code blocks
        matches = self.code_block_pattern.findall(content)
        
        for match in matches:
            language = match[0].lower() if match[0] else None
            code = match[1].strip()
            
            if code:  # Only include non-empty code blocks
                code_blocks.append((language, code))
                self.logger.debug(f"Found code block: language={language}, length={len(code)}")
        
        return code_blocks
    
    def extract_primary_code(self, content: str, preferred_language: Optional[str] = None) -> Tuple[Optional[str], str]:
        """Extract the primary code block from content.
        
        Args:
            content: The raw model response
            preferred_language: Preferred programming language (optional)
            
        Returns:
            Tuple of (detected_language, clean_code)
        """
        self.logger.debug("Extracting primary code from response")
        
        # First, try to find code blocks
        code_blocks = self.extract_code_blocks(content)
        
        if code_blocks:
            # If preferred language is specified, look for it first
            if preferred_language:
                preferred_lower = preferred_language.lower()
                for language, code in code_blocks:
                    if language and language.lower() == preferred_lower:
                        self.logger.info(f"Found preferred language block: {language}")
                        return language, code
            
            # Otherwise, return the first (usually largest/primary) code block
            language, code = code_blocks[0]
            self.logger.info(f"Using primary code block: language={language}")
            return language, code
        
        # If no code blocks found, try to detect if the entire content is code
        self.logger.debug("No code blocks found, checking if entire content is code")
        
        # Remove common markdown artifacts and explanations
        cleaned_content = self._clean_raw_content(content)
        
        if self._looks_like_code(cleaned_content):
            detected_language = self._detect_language_from_content(cleaned_content)
            self.logger.info(f"Detected raw code: language={detected_language}")
            return detected_language, cleaned_content
        
        # Last resort: return the original content
        self.logger.warning("Could not extract clean code, returning original content")
        return None, content
    
    def _clean_raw_content(self, content: str) -> str:
        """Clean raw content by removing common explanation patterns."""
        
        # Remove common explanation patterns
        patterns_to_remove = [
            r'^.*?(?:Here\'s|Below is|This is).*?:\s*\n',  # Introduction lines
            r'### Explanation:.*$',  # Explanation sections
            r'### Usage:.*$',  # Usage sections
            r'^\s*Certainly!.*?\n',  # Polite responses
            r'^\s*Sure!.*?\n',  # Polite responses
            r'^\s*Of course!.*?\n',  # Polite responses
        ]
        
        cleaned = content
        for pattern in patterns_to_remove:
            cleaned = re.sub(pattern, '', cleaned, flags=re.MULTILINE | re.DOTALL)
        
        # Remove excessive whitespace
        cleaned = re.sub(r'\n\s*\n\s*\n', '\n\n', cleaned)
        
        return cleaned.strip()
    
    def _looks_like_code(self, content: str) -> bool:
        """Heuristic to determine if content looks like code."""
        
        # Code indicators
        code_indicators = [
            r'def \w+\(',  # Python functions
            r'function \w+\(',  # JavaScript functions
            r'class \w+',  # Class definitions
            r'import \w+',  # Import statements
            r'#include',  # C/C++ includes
            r'if\s+.*:',  # Conditional statements
            r'for\s+.*:',  # Loop statements
            r'while\s+.*:',  # While loops
            r'{\s*$',  # Opening braces
            r'}\s*$',  # Closing braces
            r';\s*$',  # Semicolons at end of lines
        ]
        
        # Count matches
        matches = 0
        for pattern in code_indicators:
            if re.search(pattern, content, re.MULTILINE):
                matches += 1
        
        # Also check for high ratio of code-like characters
        code_chars = len(re.findall(r'[{}();=\[\]<>]', content))
        total_chars = len(content.replace(' ', '').replace('\n', ''))
        
        char_ratio = code_chars / max(total_chars, 1)
        
        self.logger.debug(f"Code detection: {matches} pattern matches, {char_ratio:.2f} char ratio")
        
        # Consider it code if we have multiple indicators or high char ratio
        return matches >= 2 or char_ratio > 0.1
    
    def _detect_language_from_content(self, content: str) -> Optional[str]:
        """Detect programming language from code content."""
        
        # Language detection patterns
        language_patterns = {
            'python': [
                r'def \w+\(',
                r'import \w+',
                r'from \w+ import',
                r'if __name__ == ["\']__main__["\']:',
                r'print\(',
            ],
            'javascript': [
                r'function \w+\(',
                r'const \w+ =',
                r'let \w+ =',
                r'var \w+ =',
                r'console\.log\(',
            ],
            'java': [
                r'public class \w+',
                r'public static void main',
                r'import java\.',
                r'System\.out\.println\(',
            ],
            'c++': [
                r'#include\s*<.*>',
                r'using namespace std;',
                r'int main\(',
                r'cout\s*<<',
            ],
            'c': [
                r'#include\s*<.*\.h>',
                r'int main\(',
                r'printf\(',
            ],
            'html': [
                r'<!DOCTYPE html>',
                r'<html.*?>',
                r'<head>',
                r'<body>',
            ],
            'css': [
                r'\w+\s*{',
                r':\s*[^;]+;',
                r'@media',
                r'#\w+\s*{',
            ],
            'sql': [
                r'SELECT\s+.*\s+FROM',
                r'CREATE TABLE',
                r'INSERT INTO',
                r'UPDATE\s+.*\s+SET',
            ],
            'bash': [
                r'#!/bin/bash',
                r'#!/bin/sh',
                r'echo\s+',
                r'\$\w+',
            ]
        }
        
        # Score each language
        language_scores = {}
        for language, patterns in language_patterns.items():
            score = 0
            for pattern in patterns:
                if re.search(pattern, content, re.MULTILINE | re.IGNORECASE):
                    score += 1
            language_scores[language] = score
        
        # Return the language with the highest score
        if language_scores:
            best_language = max(language_scores, key=language_scores.get)
            if language_scores[best_language] > 0:
                self.logger.debug(f"Detected language: {best_language} (score: {language_scores[best_language]})")
                return best_language
        
        return None
    
    def get_file_extension(self, language: Optional[str]) -> str:
        """Get file extension for the detected language."""
        if language and language.lower() in self.language_extensions:
            return self.language_extensions[language.lower()]
        return '.txt'
    
    def extract_and_clean(self, content: str, preferred_language: Optional[str] = None) -> Tuple[str, str, str]:
        """Extract and clean code from model response.
        
        Returns:
            Tuple of (detected_language, clean_code, file_extension)
        """
        language, code = self.extract_primary_code(content, preferred_language)
        extension = self.get_file_extension(language)
        
        return language or 'unknown', code, extension