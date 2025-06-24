"""
Plan Formatter for Interactive Mode

This module provides formatting utilities for presenting implementation plans
to users in a readable, structured format during interactive mode.
"""

from typing import Dict, List, Any
import json


class PlanFormatter:
    """Formatter for presenting implementation plans to users."""
    
    @staticmethod
    def format_plan_summary(plan_dict: Dict[str, Any]) -> str:
        """
        Format plan for user presentation in interactive mode.
        
        Args:
            plan_dict: Dictionary containing the implementation plan
            
        Returns:
            Formatted string representation of the plan
        """
        try:
            # Extract plan components
            project_info = plan_dict.get("project_info", {})
            phases = plan_dict.get("phases", [])
            overall_structure = plan_dict.get("overall_structure", {})
            
            # Build formatted output
            output = []
            
            # Header
            output.append("📋 Generated Implementation Plan")
            output.append("═" * 50)
            output.append("")
            
            # Project Overview
            project_name = project_info.get("name", "Unknown Project")
            project_type = project_info.get("type", "Unknown")
            complexity = project_info.get("complexity", "N/A")
            language = project_info.get("language", "Unknown")
            
            output.append(f"🎯 Project: {project_name}")
            output.append(f"📁 Type: {project_type}")
            output.append(f"🏗️  Complexity: {complexity}/5" if str(complexity).isdigit() else f"🏗️  Complexity: {complexity}")
            output.append(f"📦 Main Language: {language}")
            output.append("")
            
            # Phases Overview
            phase_count = len(phases)
            output.append(f"📋 PHASES ({phase_count} total):")
            
            for i, phase in enumerate(phases, 1):
                phase_name = phase.get("name", f"Phase {i}")
                files = phase.get("files_to_create", [])
                file_count = len(files) if files else 0
                dependencies = phase.get("dependencies", [])
                
                # Phase header with tree structure
                if i == phase_count:
                    prefix = "└─"
                else:
                    prefix = "├─"
                
                output.append(f"{prefix} Phase {i}: {phase_name}")
                
                # Files
                file_names = [f.get("filename", "unknown") if isinstance(f, dict) else str(f) for f in files[:3]]
                if file_count > 3:
                    file_display = ", ".join(file_names) + f", ... (+{file_count - 3} more)"
                else:
                    file_display = ", ".join(file_names) if file_names else "No files specified"
                
                continuation = "│  " if i != phase_count else "   "
                output.append(f"{continuation}├─ Files: {file_display}")
                
                # Dependencies
                if dependencies:
                    dep_display = ", ".join(dependencies[:3])
                    if len(dependencies) > 3:
                        dep_display += f", ... (+{len(dependencies) - 3} more)"
                    output.append(f"{continuation}└─ Dependencies: {dep_display}")
                else:
                    output.append(f"{continuation}└─ Dependencies: none")
                
                if i != phase_count:
                    output.append("")
            
            output.append("")
            
            # Commands
            output.append("🎮 Commands:")
            output.append("• 'approve' or 'a' - Approve and proceed")
            output.append("• 'modify' or 'm' - Request modifications")
            output.append("• 'reject' or 'r' - Reject and exit")
            output.append("• 'details' or 'd' - Show detailed plan breakdown")
            output.append("• 'help' or 'h' - Show detailed help")
            output.append("")
            
            return "\n".join(output)
            
        except Exception as e:
            return f"❌ Error formatting plan: {str(e)}\n\nRaw plan data:\n{json.dumps(plan_dict, indent=2)}"
    
    @staticmethod
    def format_phase_details(phases: List[Dict[str, Any]]) -> str:
        """
        Format detailed phase information for user review.
        
        Args:
            phases: List of phase dictionaries
            
        Returns:
            Detailed formatted string representation of phases
        """
        try:
            output = []
            output.append("📋 Detailed Phase Breakdown")
            output.append("═" * 50)
            output.append("")
            
            for i, phase in enumerate(phases, 1):
                phase_name = phase.get("name", f"Phase {i}")
                description = phase.get("description", "No description provided")
                files = phase.get("files_to_create", [])
                dependencies = phase.get("dependencies", [])
                success_criteria = phase.get("success_criteria", [])
                
                output.append(f"🔷 Phase {i}: {phase_name}")
                output.append("-" * (len(f"Phase {i}: {phase_name}") + 2))
                output.append(f"📝 Description: {description}")
                output.append("")
                
                # Files to create
                if files:
                    output.append("📄 Files to Create:")
                    for file_info in files:
                        if isinstance(file_info, dict):
                            filename = file_info.get("filename", "unknown")
                            description = file_info.get("description", "")
                            if description:
                                output.append(f"  • {filename} - {description}")
                            else:
                                output.append(f"  • {filename}")
                        else:
                            output.append(f"  • {file_info}")
                else:
                    output.append("📄 Files to Create: None specified")
                output.append("")
                
                # Dependencies
                if dependencies:
                    output.append("📦 Dependencies:")
                    for dep in dependencies:
                        output.append(f"  • {dep}")
                else:
                    output.append("📦 Dependencies: None")
                output.append("")
                
                # Success criteria
                if success_criteria:
                    output.append("✅ Success Criteria:")
                    for criteria in success_criteria:
                        output.append(f"  • {criteria}")
                else:
                    output.append("✅ Success Criteria: Not specified")
                
                if i < len(phases):
                    output.append("")
                    output.append("-" * 50)
                    output.append("")
            
            return "\n".join(output)
            
        except Exception as e:
            return f"❌ Error formatting phase details: {str(e)}"
    
    @staticmethod
    def format_project_overview(project_info: Dict[str, Any], overall_structure: Dict[str, Any] = None) -> str:
        """
        Format project overview section with structure information.
        
        Args:
            project_info: Project information dictionary
            overall_structure: Overall project structure information
            
        Returns:
            Formatted project overview string
        """
        try:
            output = []
            output.append("🎯 Project Overview")
            output.append("═" * 30)
            output.append("")
            
            # Basic project info
            output.append(f"📛 Name: {project_info.get('name', 'Unknown Project')}")
            output.append(f"📁 Type: {project_info.get('type', 'Unknown')}")
            output.append(f"🏗️  Complexity: {project_info.get('complexity', 'N/A')}")
            output.append(f"📦 Language: {project_info.get('language', 'Unknown')}")
            
            if project_info.get('description'):
                output.append(f"📝 Description: {project_info['description']}")
            
            output.append("")
            
            # Overall structure if available
            if overall_structure:
                output.append("🏗️  Project Structure:")
                
                directory_structure = overall_structure.get("directory_structure", [])
                if directory_structure:
                    for item in directory_structure[:10]:  # Limit to first 10 items
                        output.append(f"  • {item}")
                    if len(directory_structure) > 10:
                        output.append(f"  ... and {len(directory_structure) - 10} more items")
                
                main_components = overall_structure.get("main_components", [])
                if main_components:
                    output.append("")
                    output.append("🔧 Main Components:")
                    for component in main_components:
                        output.append(f"  • {component}")
            
            return "\n".join(output)
            
        except Exception as e:
            return f"❌ Error formatting project overview: {str(e)}"
    
    @staticmethod
    def format_help_text() -> str:
        """
        Format help text for interactive mode commands.
        
        Returns:
            Formatted help text string
        """
        output = []
        output.append("🆘 Interactive Mode Help")
        output.append("═" * 40)
        output.append("")
        output.append("📋 Available Commands:")
        output.append("")
        output.append("🟢 approve, a")
        output.append("   Approve the current plan and proceed with code generation.")
        output.append("   This will start the Writer Agent to create the files.")
        output.append("")
        output.append("🔄 modify, m")
        output.append("   Request modifications to the current plan.")
        output.append("   You'll be prompted to provide specific feedback on what")
        output.append("   you'd like to change, add, or remove from the plan.")
        output.append("")
        output.append("❌ reject, r")
        output.append("   Reject the current plan and exit without generating code.")
        output.append("   This will terminate the entire workflow.")
        output.append("")
        output.append("📊 details, d")
        output.append("   Show detailed breakdown of all phases, including")
        output.append("   files to create, dependencies, and success criteria.")
        output.append("")
        output.append("🆘 help, h")
        output.append("   Show this help information.")
        output.append("")
        output.append("💡 Tips:")
        output.append("• Commands are case-insensitive")
        output.append("• You can use single letters for quick commands (a, m, r, d, h)")
        output.append("• When modifying, be specific about what you want changed")
        output.append("• Use 'details' to review the plan thoroughly before approving")
        output.append("")
        
        return "\n".join(output)