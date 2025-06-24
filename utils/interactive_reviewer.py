"""
Interactive Plan Reviewer for User Approval

This module provides the interactive interface for users to review, approve,
modify, or reject implementation plans during interactive mode.
"""

from typing import Dict, Optional, Tuple, Any
from enum import Enum
import sys
import json
from utils.plan_formatter import PlanFormatter


class UserCommand(Enum):
    """Enumeration of available user commands in interactive mode."""
    APPROVE = "approve"
    MODIFY = "modify"
    REJECT = "reject"
    DETAILS = "details"
    HELP = "help"
    UNKNOWN = "unknown"


class InteractivePlanReviewer:
    """Interactive interface for plan review and approval."""
    
    def __init__(self, logger):
        """
        Initialize the interactive plan reviewer.
        
        Args:
            logger: Logger instance for tracking user interactions
        """
        self.logger = logger
        self.formatter = PlanFormatter()
        
    def present_plan(self, plan_dict: Dict[str, Any]) -> None:
        """
        Present the implementation plan to the user in a formatted way.
        
        Args:
            plan_dict: Dictionary containing the implementation plan
        """
        try:
            # Clear screen for better visibility (optional)
            print("\n" * 2)
            
            # Format and display the plan
            formatted_plan = self.formatter.format_plan_summary(plan_dict)
            print(formatted_plan)
            
            self.logger.info("Implementation plan presented to user for review")
            
        except Exception as e:
            self.logger.error(f"Error presenting plan: {str(e)}")
            print(f"❌ Error displaying plan: {str(e)}")
            
            # Fallback: show raw plan data
            print("\nRaw plan data:")
            try:
                print(json.dumps(plan_dict, indent=2))
            except Exception:
                print(str(plan_dict))
    
    def get_user_input(self) -> str:
        """
        Get user command with proper input handling.
        
        Returns:
            User input string (trimmed and lowercased)
        """
        try:
            # Use input() with a clear prompt
            user_input = input("Your choice: ").strip().lower()
            
            self.logger.info(f"User input received: '{user_input}'")
            return user_input
            
        except KeyboardInterrupt:
            print("\n\n🛑 Operation cancelled by user")
            self.logger.info("User cancelled operation with Ctrl+C")
            sys.exit(130)  # Standard exit code for keyboard interrupt
            
        except EOFError:
            print("\n\n🛑 End of input reached")
            self.logger.info("EOF reached during user input")
            return "reject"  # Default to reject if input stream ends
            
        except Exception as e:
            self.logger.error(f"Error getting user input: {str(e)}")
            print(f"❌ Error reading input: {str(e)}")
            return "help"  # Default to help on input errors
    
    def handle_user_command(self, command: str, plan_dict: Dict[str, Any]) -> Tuple[UserCommand, Optional[str]]:
        """
        Process user commands and return appropriate action.
        
        Args:
            command: User input command string
            plan_dict: Current implementation plan dictionary
            
        Returns:
            Tuple of (UserCommand, optional_feedback_string)
        """
        try:
            # Normalize command
            cmd = command.strip().lower()
            
            # Map commands to enums
            if cmd in ['approve', 'a']:
                self.logger.info("User approved the plan")
                return UserCommand.APPROVE, None
                
            elif cmd in ['reject', 'r']:
                self.logger.info("User rejected the plan")
                return UserCommand.REJECT, None
                
            elif cmd in ['details', 'd']:
                self.show_plan_details(plan_dict)
                return self.handle_user_command(self.get_user_input(), plan_dict)
                
            elif cmd in ['help', 'h']:
                self.show_help()
                return self.handle_user_command(self.get_user_input(), plan_dict)
                
            elif cmd in ['modify', 'm']:
                feedback = self.get_modification_feedback()
                if feedback:
                    self.logger.info(f"User requested plan modification: {feedback}")
                    return UserCommand.MODIFY, feedback
                else:
                    print("❌ No feedback provided. Please try again.")
                    return self.handle_user_command(self.get_user_input(), plan_dict)
                    
            else:
                print(f"❌ Unknown command: '{command}'")
                print("💡 Type 'help' or 'h' to see available commands.")
                return self.handle_user_command(self.get_user_input(), plan_dict)
                
        except Exception as e:
            self.logger.error(f"Error handling user command '{command}': {str(e)}")
            print(f"❌ Error processing command: {str(e)}")
            print("💡 Type 'help' to see available commands.")
            return self.handle_user_command(self.get_user_input(), plan_dict)
    
    def show_plan_details(self, plan_dict: Dict[str, Any]) -> None:
        """
        Show detailed breakdown of the implementation plan.
        
        Args:
            plan_dict: Dictionary containing the implementation plan
        """
        try:
            print("\n" + "=" * 60)
            
            # Show project overview
            project_info = plan_dict.get("project_info", {})
            overall_structure = plan_dict.get("overall_structure", {})
            
            if project_info or overall_structure:
                overview = self.formatter.format_project_overview(project_info, overall_structure)
                print(overview)
                print("")
            
            # Show detailed phase information
            phases = plan_dict.get("phases", [])
            if phases:
                phase_details = self.formatter.format_phase_details(phases)
                print(phase_details)
            else:
                print("❌ No phases found in plan")
            
            print("\n" + "=" * 60)
            print("📋 Plan details displayed above.")
            print("💡 Use 'approve', 'modify', or 'reject' to proceed.")
            print("")
            
            self.logger.info("Detailed plan information displayed to user")
            
        except Exception as e:
            self.logger.error(f"Error showing plan details: {str(e)}")
            print(f"❌ Error displaying plan details: {str(e)}")
            
            # Fallback: show raw plan
            print("\nRaw plan details:")
            try:
                print(json.dumps(plan_dict, indent=2))
            except Exception:
                print(str(plan_dict))
    
    def show_help(self) -> None:
        """Display help information for interactive commands."""
        try:
            print("\n" + "=" * 60)
            help_text = self.formatter.format_help_text()
            print(help_text)
            print("=" * 60)
            print("")
            
            self.logger.info("Help information displayed to user")
            
        except Exception as e:
            self.logger.error(f"Error showing help: {str(e)}")
            print(f"❌ Error displaying help: {str(e)}")
            
            # Fallback help
            print("""
🆘 Quick Help:
• approve (a) - Approve plan and proceed
• modify (m) - Request plan modifications  
• reject (r) - Reject plan and exit
• details (d) - Show detailed plan breakdown
• help (h) - Show this help
            """)
    
    def get_modification_feedback(self) -> Optional[str]:
        """
        Get user feedback for plan modifications.
        
        Returns:
            User feedback string or None if cancelled
        """
        try:
            print("\n🔄 Plan Modification Request")
            print("-" * 40)
            print("Please describe what you'd like to modify about the plan.")
            print("Be as specific as possible about:")
            print("• Files you want added, removed, or changed")
            print("• Dependencies or technologies to include/exclude")
            print("• Phase organization or structure changes")
            print("• Any other specific requirements")
            print("")
            print("💡 Type your feedback below (press Enter twice to finish):")
            print("")
            
            # Collect multi-line feedback
            feedback_lines = []
            empty_lines = 0
            
            while True:
                try:
                    line = input("   ")
                    
                    if line.strip() == "":
                        empty_lines += 1
                        if empty_lines >= 2:  # Two empty lines ends input
                            break
                        # Don't add empty lines to feedback until we know input continues
                    else:
                        empty_lines = 0
                        feedback_lines.append(line)
                        
                except KeyboardInterrupt:
                    print("\n\n🛑 Modification cancelled by user")
                    self.logger.info("User cancelled modification with Ctrl+C")
                    return None
                    
                except EOFError:
                    print("\n\n🛑 Input ended")
                    break
            
            # Process feedback
            feedback = "\n".join(feedback_lines).strip()
            
            if not feedback:
                print("❌ No feedback provided.")
                return None
            
            print(f"\n✅ Feedback received ({len(feedback)} characters)")
            print("🔄 Regenerating plan with your feedback...")
            print("")
            
            return feedback
            
        except Exception as e:
            self.logger.error(f"Error getting modification feedback: {str(e)}")
            print(f"❌ Error collecting feedback: {str(e)}")
            return None
    
    def show_regeneration_status(self, success: bool, message: str = "") -> None:
        """
        Show status of plan regeneration to user.
        
        Args:
            success: Whether regeneration was successful
            message: Optional status message
        """
        if success:
            print("✅ Plan regenerated successfully with your feedback!")
            print("📋 Please review the updated plan below:")
            if message:
                print(f"💡 {message}")
            print("")
        else:
            print("❌ Failed to regenerate plan with your feedback.")
            if message:
                print(f"🔍 Error: {message}")
            print("💡 You can try modifying again with different feedback, or approve/reject the current plan.")
            print("")
        
        self.logger.info(f"Plan regeneration status shown to user: success={success}, message='{message}'")