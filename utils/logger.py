import logging
import sys
import json
import time
from pathlib import Path
from typing import Optional, Dict, Any


class AgentFormatter(logging.Formatter):
    """Enhanced formatter that includes agent context and timing information."""
    
    def format(self, record):
        # Add timing information if not present
        if not hasattr(record, 'agent_context'):
            record.agent_context = getattr(record, 'agent_name', 'system')
        
        # Enhanced format with agent context
        if hasattr(record, 'agent_name') and record.agent_name:
            record.name = f"lazytocode.{record.agent_name}"
        
        # Call parent format
        formatted = super().format(record)
        
        # Add timing info if available
        if hasattr(record, 'operation_time'):
            formatted += f" [took {record.operation_time:.3f}s]"
            
        return formatted


class StructuredDebugHandler(logging.Handler):
    """Handler that outputs structured debug information to JSON files."""
    
    def __init__(self, debug_dir: Path, agent_name: str):
        super().__init__()
        self.debug_dir = debug_dir
        self.agent_name = agent_name
        self.session_id = int(time.time())
        
        # Create debug directory
        self.debug_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize debug file
        self.debug_file = self.debug_dir / f"{agent_name}_debug_{self.session_id}.jsonl"
    
    def emit(self, record):
        try:
            # Only log debug records with structured data
            if record.levelno == logging.DEBUG and hasattr(record, 'structured_data'):
                debug_entry = {
                    'timestamp': time.time(),
                    'agent': self.agent_name,
                    'level': record.levelname,
                    'message': record.getMessage(),
                    'data': record.structured_data
                }
                
                with open(self.debug_file, 'a', encoding='utf-8') as f:
                    f.write(json.dumps(debug_entry) + '\n')
        except Exception:
            # Don't let debug logging break the application
            pass


def setup_logger(debug_mode=False, log_file=None, debug_dir=None):
    """Setup and configure logging for LazyToCode."""
    
    # Create root logger
    logger = logging.getLogger('lazytocode')
    logger.setLevel(logging.DEBUG if debug_mode else logging.INFO)
    
    # Clear existing handlers
    logger.handlers.clear()
    
    # Create enhanced formatter
    formatter = AgentFormatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG if debug_mode else logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler (optional)
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_path)
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    # Set up debug directory for structured logging
    if debug_mode and debug_dir:
        Path(debug_dir).mkdir(parents=True, exist_ok=True)
    
    return logger


def get_logger(agent_name: Optional[str] = None):
    """Get a logger instance, optionally with agent-specific context."""
    if agent_name:
        logger_name = f'lazytocode.{agent_name}'
        logger = logging.getLogger(logger_name)
        
        # If this is a new agent logger, inherit from parent
        if not logger.handlers:
            logger.parent = logging.getLogger('lazytocode')
            
        return logger
    else:
        return logging.getLogger('lazytocode')


def get_agent_logger(agent_name: str, debug_dir: Optional[Path] = None):
    """Get an agent-specific logger with enhanced debugging capabilities."""
    
    logger = get_logger(agent_name)
    
    # Add structured debug handler if debug directory is provided
    if debug_dir and logging.getLogger('lazytocode').level == logging.DEBUG:
        # Check if we already have a structured debug handler for this agent
        has_structured_handler = any(
            isinstance(handler, StructuredDebugHandler) and handler.agent_name == agent_name
            for handler in logger.handlers
        )
        
        if not has_structured_handler:
            structured_handler = StructuredDebugHandler(debug_dir, agent_name)
            structured_handler.setLevel(logging.DEBUG)
            logger.addHandler(structured_handler)
    
    return logger


class LogContext:
    """Context manager for adding timing and structured data to log messages."""
    
    def __init__(self, logger, operation_name: str, agent_name: str = None):
        self.logger = logger
        self.operation_name = operation_name
        self.agent_name = agent_name
        self.start_time = None
        self.structured_data = {}
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time:
            operation_time = time.time() - self.start_time
            
            # Create log record with timing info
            extra = {
                'operation_time': operation_time,
                'agent_name': self.agent_name,
                'structured_data': {
                    'operation': self.operation_name,
                    'duration': operation_time,
                    **self.structured_data
                }
            }
            
            if exc_type:
                self.logger.debug(
                    f"Operation '{self.operation_name}' failed after {operation_time:.3f}s: {exc_val}",
                    extra=extra
                )
            else:
                self.logger.debug(
                    f"Operation '{self.operation_name}' completed in {operation_time:.3f}s",
                    extra=extra
                )
    
    def add_data(self, key: str, value: Any):
        """Add structured data to the log context."""
        self.structured_data[key] = value


def log_model_interaction(logger, agent_name: str, operation: str, 
                         request_data: Dict[str, Any], response_data: Dict[str, Any], 
                         duration: float):
    """Log detailed model interaction data."""
    
    # Log basic info at info level
    logger.info(f"Model interaction: {operation} completed in {duration:.3f}s")
    
    # Log full details at debug level with structured data
    structured_data = {
        'operation_type': 'model_interaction',
        'operation': operation,
        'duration': duration,
        'request_size': len(str(request_data)),
        'response_size': len(str(response_data)),
        'request_preview': str(request_data)[:200] + '...' if len(str(request_data)) > 200 else str(request_data),
        'full_request': request_data,
        'full_response': response_data
    }
    
    extra = {
        'agent_name': agent_name,
        'structured_data': structured_data
    }
    
    logger.debug(
        f"[{agent_name}] Model {operation}: Request({len(str(request_data))} chars) -> Response({len(str(response_data))} chars)",
        extra=extra
    )