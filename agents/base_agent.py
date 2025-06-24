"""
Base Agent Class

This module provides the base agent class that all specialized agents inherit from.
It provides common functionality for agent communication, state management, and logging.
"""

from abc import ABC, abstractmethod
from typing import Dict, Optional, Any, List
from pathlib import Path
import uuid
import asyncio
from datetime import datetime

# Import from autogen-core
from autogen_core import RoutedAgent, message_handler

from utils.agent_messages import (
    AgentMessage, AgentStatus, MessageType,
    create_status_update, create_error_report
)
from utils.logger import get_logger


class BaseAgent(RoutedAgent, ABC):
    """Base class for all LazyToCode agents."""
    
    def __init__(self, name: str, agent_type: str, **kwargs):
        """
        Initialize the base agent.
        
        Args:
            name: Unique name for this agent instance
            agent_type: Type of agent (planner, writer, tester, fixing)
            **kwargs: Additional configuration options
        """
        super().__init__(name)
        
        self.name = name  # Store the name explicitly
        self.agent_type = agent_type
        self.logger = get_logger()
        self.status = AgentStatus.IDLE
        self.current_phase_id: Optional[str] = None
        self.message_history: List[AgentMessage] = []
        self.error_count = 0
        self.max_errors = kwargs.get('max_errors', 10)
        
        # Agent capabilities and configuration
        self.capabilities: List[str] = []
        self.config: Dict[str, Any] = kwargs
        
        self.logger.info(f"{self.agent_type.title()} agent '{name}' initialized")
    
    @property
    def agent_id(self) -> str:
        """Get the agent's unique identifier."""
        return self.id if hasattr(self, 'id') else self.name
    
    def get_status(self) -> AgentStatus:
        """Get the current status of the agent."""
        return self.status
    
    def set_status(self, status: AgentStatus, message: Optional[str] = None):
        """
        Set the agent's status and optionally log a message.
        
        Args:
            status: New status for the agent
            message: Optional status message
        """
        old_status = self.status
        self.status = status
        
        log_message = f"Agent {self.name} status changed: {old_status.value} -> {status.value}"
        if message:
            log_message += f" ({message})"
        
        self.logger.info(log_message)
    
    async def send_message(self, recipient: str, message: AgentMessage) -> bool:
        """
        Send a message to another agent.
        
        Args:
            recipient: Name of the recipient agent
            message: Message to send
            
        Returns:
            True if message was sent successfully, False otherwise
        """
        try:
            # Add message to history
            self.message_history.append(message)
            
            # Log the message
            self.logger.debug(f"Sending {message.message_type.value} to {recipient}")
            
            # In a real implementation, this would use the autogen message routing
            # For now, we'll simulate message passing through a message bus
            await self._route_message(recipient, message)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to send message to {recipient}: {str(e)}")
            self.error_count += 1
            return False
    
    async def _route_message(self, recipient: str, message: AgentMessage):
        """
        Route a message to the recipient agent.
        This is a placeholder for the actual message routing implementation.
        """
        # This would be implemented using autogen's message routing system
        # For now, we'll just log it
        self.logger.debug(f"Routing message {message.message_type.value} to {recipient}")
    
    async def handle_message(self, message: AgentMessage, ctx=None) -> Optional[AgentMessage]:
        """
        Handle incoming messages from other agents.
        
        Args:
            message: Incoming message
            
        Returns:
            Optional response message
        """
        try:
            # Add to message history
            self.message_history.append(message)
            
            # Log the received message
            self.logger.debug(f"Received {message.message_type.value} from {message.sender}")
            
            # Set current phase ID
            self.current_phase_id = message.phase_id
            
            # Route to specific handler based on message type
            handler_map = {
                MessageType.PLAN_REQUEST: self._handle_plan_request,
                MessageType.WRITE_REQUEST: self._handle_write_request,
                MessageType.TEST_REQUEST: self._handle_test_request,
                MessageType.FIX_REQUEST: self._handle_fix_request,
                MessageType.STATUS_UPDATE: self._handle_status_update,
                MessageType.ERROR_REPORT: self._handle_error_report,
            }
            
            handler = handler_map.get(message.message_type)
            if handler:
                return await handler(message)
            else:
                self.logger.warning(f"No handler for message type: {message.message_type.value}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error handling message: {str(e)}")
            self.error_count += 1
            
            # Send error report back to sender
            error_msg = create_error_report(
                sender=self.name,
                recipient=message.sender,
                error=str(e),
                error_type="message_handling_error",
                phase_id=message.phase_id,
                correlation_id=message.correlation_id
            )
            await self.send_message(message.sender, error_msg)
            return None
    
    # Abstract methods that must be implemented by subclasses
    
    @abstractmethod
    async def _handle_plan_request(self, message: AgentMessage) -> Optional[AgentMessage]:
        """Handle plan request messages."""
        pass
    
    @abstractmethod
    async def _handle_write_request(self, message: AgentMessage) -> Optional[AgentMessage]:
        """Handle write request messages."""
        pass
    
    @abstractmethod
    async def _handle_test_request(self, message: AgentMessage) -> Optional[AgentMessage]:
        """Handle test request messages."""
        pass
    
    @abstractmethod
    async def _handle_fix_request(self, message: AgentMessage) -> Optional[AgentMessage]:
        """Handle fix request messages."""
        pass
    
    # Default implementations for status and error messages
    
    async def _handle_status_update(self, message: AgentMessage) -> Optional[AgentMessage]:
        """Handle status update messages."""
        payload = message.payload
        status = payload.get('status')
        status_message = payload.get('message', '')
        
        self.logger.info(f"Status update from {message.sender}: {status} - {status_message}")
        return None
    
    async def _handle_error_report(self, message: AgentMessage) -> Optional[AgentMessage]:
        """Handle error report messages."""
        payload = message.payload
        error = payload.get('error')
        error_type = payload.get('error_type')
        
        self.logger.error(f"Error report from {message.sender}: {error_type} - {error}")
        return None
    
    # Utility methods
    
    def generate_phase_id(self) -> str:
        """Generate a unique phase ID."""
        return f"phase_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
    
    def generate_correlation_id(self) -> str:
        """Generate a unique correlation ID for message tracking."""
        return f"corr_{uuid.uuid4().hex[:12]}"
    
    async def send_status_update(self, recipient: str, status: AgentStatus, 
                                message: str, phase_id: str) -> bool:
        """
        Send a status update to another agent.
        
        Args:
            recipient: Recipient agent name
            status: Current status
            message: Status message
            phase_id: Current phase ID
            
        Returns:
            True if sent successfully
        """
        status_msg = create_status_update(
            sender=self.name,
            recipient=recipient,
            status=status,
            message=message,
            phase_id=phase_id
        )
        return await self.send_message(recipient, status_msg)
    
    async def send_error_report(self, recipient: str, error: str, 
                               error_type: str, phase_id: str) -> bool:
        """
        Send an error report to another agent.
        
        Args:
            recipient: Recipient agent name
            error: Error description
            error_type: Type of error
            phase_id: Current phase ID
            
        Returns:
            True if sent successfully
        """
        error_msg = create_error_report(
            sender=self.name,
            recipient=recipient,
            error=error,
            error_type=error_type,
            phase_id=phase_id
        )
        return await self.send_message(recipient, error_msg)
    
    def get_message_history(self, message_type: Optional[MessageType] = None) -> List[AgentMessage]:
        """
        Get message history, optionally filtered by message type.
        
        Args:
            message_type: Optional filter by message type
            
        Returns:
            List of messages
        """
        if message_type:
            return [msg for msg in self.message_history if msg.message_type == message_type]
        return self.message_history.copy()
    
    def clear_message_history(self):
        """Clear the message history."""
        self.message_history.clear()
        self.logger.debug(f"Message history cleared for agent {self.name}")
    
    def get_agent_info(self) -> Dict[str, Any]:
        """
        Get comprehensive information about the agent.
        
        Returns:
            Dictionary with agent information
        """
        return {
            "name": self.name,
            "type": self.agent_type,
            "status": self.status.value,
            "current_phase": self.current_phase_id,
            "message_count": len(self.message_history),
            "error_count": self.error_count,
            "capabilities": self.capabilities,
            "config": self.config
        }
    
    async def initialize(self) -> bool:
        """
        Initialize the agent. Override in subclasses for specific initialization.
        
        Returns:
            True if initialization successful
        """
        self.logger.info(f"Initializing {self.agent_type} agent: {self.name}")
        self.set_status(AgentStatus.IDLE, "Agent initialized")
        return True
    
    async def shutdown(self):
        """Shutdown the agent gracefully."""
        self.logger.info(f"Shutting down {self.agent_type} agent: {self.name}")
        self.set_status(AgentStatus.IDLE, "Agent shutting down")
        self.clear_message_history()
    
    def __str__(self) -> str:
        """String representation of the agent."""
        return f"{self.agent_type.title()}Agent(name={self.name}, status={self.status.value})"
    
    def __repr__(self) -> str:
        """Detailed string representation of the agent."""
        return (f"{self.__class__.__name__}(name='{self.name}', "
                f"type='{self.agent_type}', status='{self.status.value}', "
                f"phase='{self.current_phase_id}', messages={len(self.message_history)})")