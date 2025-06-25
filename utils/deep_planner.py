"""
Deep Planning Manager - Manages the reflection loop between Planner and Plan Reviewer agents.

This module implements the core logic for the deep planning feature, managing
iterative plan improvement through AI-driven reflection following the Microsoft
Autogen Reflection design pattern.
"""

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
import json
from pathlib import Path

from utils.logger import get_logger
from utils.agent_messages import AgentMessage, MessageType


class DeepPlanningManager:
    """
    Manages the deep planning workflow with reflection between Planner and Plan Reviewer agents.
    
    This class orchestrates the iterative improvement process where:
    1. Planner generates initial plan
    2. Plan Reviewer provides detailed feedback
    3. Planner improves plan based on feedback
    4. Process repeats until convergence or max iterations
    """
    
    def __init__(self, 
                 max_iterations: int = 3,
                 convergence_threshold: float = 8.0,
                 min_score_improvement: float = 0.5,
                 output_dir: Optional[Path] = None,
                 debug_mode: bool = False):
        """
        Initialize the Deep Planning Manager.
        
        Args:
            max_iterations: Maximum number of reflection iterations
            convergence_threshold: Score threshold for early convergence (1-10)
            min_score_improvement: Minimum score improvement to continue iterating
            output_dir: Directory for saving iteration history
            debug_mode: Enable detailed debug logging
        """
        
        self.max_iterations = max_iterations
        self.convergence_threshold = convergence_threshold
        self.min_score_improvement = min_score_improvement
        self.output_dir = output_dir or Path("./output")
        self.debug_mode = debug_mode
        
        self.logger = get_logger()
        
        # Planning iteration tracking
        self.current_iteration = 0
        self.plan_history: List[Dict[str, Any]] = []
        self.review_history: List[Dict[str, Any]] = []
        self.iteration_start_time = None
        
        # Create debug directory if needed
        if self.debug_mode:
            self.debug_dir = self.output_dir / "debug" / "deep_planning"
            self.debug_dir.mkdir(parents=True, exist_ok=True)
        
        self.logger.info(f"DeepPlanningManager initialized: max_iterations={max_iterations}, "
                        f"convergence_threshold={convergence_threshold}")
    
    async def execute_deep_planning_cycle(self, 
                                        planner_agent, 
                                        reviewer_agent, 
                                        initial_prompt: str,
                                        project_context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Execute the complete deep planning cycle with reflection iterations.
        
        Args:
            planner_agent: The PlannerAgent instance
            reviewer_agent: The PlanReviewerAgent instance  
            initial_prompt: Initial project prompt
            project_context: Optional context for planning
            
        Returns:
            Dictionary with final plan, iteration history, and metrics
        """
        
        try:
            self.logger.info("Starting deep planning cycle")
            self.iteration_start_time = datetime.now()
            self._reset_iteration_state()
            
            # Generate initial plan
            self.logger.info("Generating initial plan")
            current_plan = await planner_agent.generate_plan(initial_prompt, project_context)
            self.plan_history.append({
                "iteration": 0,
                "plan": current_plan,
                "timestamp": datetime.now().isoformat(),
                "type": "initial"
            })
            
            await self._save_iteration_debug(0, current_plan, None, "initial_plan")
            
            best_plan = current_plan
            best_score = 0.0
            previous_score = 0.0
            
            # Reflection iteration loop
            for iteration in range(1, self.max_iterations + 1):
                self.current_iteration = iteration
                self.logger.info(f"Starting reflection iteration {iteration}/{self.max_iterations}")
                
                # Review current plan
                review_result = await reviewer_agent.review_plan(current_plan)
                
                if not review_result.get("success"):
                    self.logger.warning(f"Plan review failed in iteration {iteration}: {review_result.get('error')}")
                    break
                
                review_feedback = review_result["review_feedback"]
                self.review_history.append({
                    "iteration": iteration,
                    "review": review_feedback,
                    "timestamp": datetime.now().isoformat()
                })
                
                await self._save_iteration_debug(iteration, current_plan, review_feedback, "review")
                
                # Assess plan quality and convergence
                quality_assessment = self._assess_plan_quality(review_feedback)
                current_score = quality_assessment["score"]
                
                self.logger.info(f"Iteration {iteration} - Plan score: {current_score}, "
                               f"Quality: {quality_assessment['quality']}, "
                               f"Action: {quality_assessment['action']}")
                
                # Update best plan if this is better
                if current_score > best_score:
                    best_plan = current_plan
                    best_score = current_score
                
                # Check convergence conditions
                convergence_result = self._check_convergence(quality_assessment, current_score, previous_score)
                
                if convergence_result["converged"]:
                    self.logger.info(f"Convergence reached: {convergence_result['reason']}")
                    break
                
                # Check if we should continue iterating
                if iteration >= self.max_iterations:
                    self.logger.info("Maximum iterations reached")
                    break
                
                # Generate improved plan based on feedback
                self.logger.info(f"Generating improved plan for iteration {iteration + 1}")
                
                try:
                    improvement_result = await planner_agent.regenerate_plan_with_feedback(
                        current_plan, 
                        self._format_feedback_for_improvement(review_feedback)
                    )
                    
                    if improvement_result.get("success"):
                        current_plan = improvement_result["plan_dict"]
                        self.plan_history.append({
                            "iteration": iteration,
                            "plan": current_plan,
                            "timestamp": datetime.now().isoformat(),
                            "type": "improved",
                            "previous_score": previous_score,
                            "feedback_applied": True
                        })
                        
                        await self._save_iteration_debug(iteration, current_plan, review_feedback, "improved_plan")
                    else:
                        self.logger.warning("Plan improvement failed, using previous plan")
                        break
                        
                except Exception as e:
                    self.logger.error(f"Error during plan improvement: {e}")
                    break
                
                previous_score = current_score
            
            # Finalize results
            total_duration = (datetime.now() - self.iteration_start_time).total_seconds() if self.iteration_start_time else 0
            
            result = {
                "success": True,
                "final_plan": best_plan,
                "best_score": best_score,
                "total_iterations": self.current_iteration,
                "plan_history": self.plan_history,
                "review_history": self.review_history,
                "duration_seconds": total_duration,
                "convergence_info": convergence_result if 'convergence_result' in locals() else None,
                "improvement_summary": self._generate_improvement_summary()
            }
            
            await self._save_final_results(result)
            
            self.logger.info(f"Deep planning completed: {self.current_iteration} iterations, "
                           f"best score: {best_score:.1f}, duration: {total_duration:.1f}s")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Deep planning cycle failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "final_plan": self.plan_history[-1]["plan"] if self.plan_history else None,
                "partial_results": {
                    "plan_history": self.plan_history,
                    "review_history": self.review_history,
                    "iterations_completed": self.current_iteration
                }
            }
    
    def _check_convergence(self, quality_assessment: Dict[str, Any], 
                          current_score: float, previous_score: float) -> Dict[str, Any]:
        """
        Check if the planning process has converged.
        
        Args:
            quality_assessment: Current plan quality assessment
            current_score: Current plan score
            previous_score: Previous plan score
            
        Returns:
            Dictionary with convergence status and reason
        """
        
        # High quality threshold reached (stricter threshold)
        if current_score >= self.convergence_threshold:
            return {
                "converged": True,
                "reason": f"High quality threshold reached (score: {current_score:.1f})",
                "type": "quality_threshold"
            }
        
        # Plan explicitly approved by reviewer
        if quality_assessment.get("action") == "approve":
            return {
                "converged": True,
                "reason": "Plan approved by reviewer",
                "type": "reviewer_approval"
            }
        
        # Minimal improvement between iterations
        if self.current_iteration > 1:
            score_improvement = current_score - previous_score
            if score_improvement < self.min_score_improvement:
                return {
                    "converged": True,
                    "reason": f"Minimal improvement (improvement: {score_improvement:.1f})",
                    "type": "minimal_improvement"
                }
        
        # Only converge if no critical OR high severity issues remain AND score is high enough
        critical_issues = quality_assessment.get("critical_issues", 0)
        high_issues = quality_assessment.get("high_issues", 0)
        if critical_issues == 0 and high_issues == 0 and current_score >= 8.5:
            return {
                "converged": True,
                "reason": "No critical or high-severity issues remaining",
                "type": "issues_resolved"
            }
        
        return {
            "converged": False,
            "reason": "Convergence criteria not met",
            "type": "continue"
        }
    
    def _assess_plan_quality(self, review_feedback: Dict[str, Any]) -> Dict[str, Any]:
        """
        Assess plan quality based on review feedback.
        
        Args:
            review_feedback: Feedback from plan reviewer
            
        Returns:
            Quality assessment dictionary
        """
        
        try:
            overall_assessment = review_feedback.get("overall_assessment", {})
            issues = review_feedback.get("issues", [])
            improvements = review_feedback.get("improvements", [])
            
            score = overall_assessment.get("score", 5.0)
            recommendation = overall_assessment.get("recommendation", "needs_major_revision")
            
            # Count issues by severity
            critical_issues = len([issue for issue in issues if issue.get("severity") == "critical"])
            high_issues = len([issue for issue in issues if issue.get("severity") == "high"])
            
            # Count improvements by priority  
            high_priority_improvements = len([imp for imp in improvements if imp.get("priority") == "high"])
            
            # Use Plan Reviewer's recommendation as primary, but validate against issues
            reviewer_recommendation = recommendation
            
            # Override only if there are critical issues that reviewer missed
            if critical_issues > 0:
                action = "needs_major_revision"
                quality = "poor"
            elif high_issues > 2:  # Multiple high issues should override reviewer if they're lenient
                action = "needs_major_revision" if reviewer_recommendation == "approve" else reviewer_recommendation
                quality = "fair"
            else:
                # Trust the reviewer's assessment
                action = reviewer_recommendation
                
            # Determine quality level based on action and score
            if action == "approve_as_is":
                quality = "excellent"
            elif action == "approve_with_minor_changes":
                quality = "good" if score >= 7.0 else "fair"
            elif action == "needs_major_revision":
                quality = "poor" if score < 6.0 else "fair"
            else:  # needs_revision or other
                quality = "fair"
            
            return {
                "score": score,
                "quality": quality,
                "action": action,
                "recommendation": recommendation,
                "critical_issues": critical_issues,
                "high_issues": high_issues,
                "high_priority_improvements": high_priority_improvements,
                "total_issues": len(issues),
                "total_improvements": len(improvements)
            }
            
        except Exception as e:
            self.logger.error(f"Failed to assess plan quality: {e}")
            return {
                "score": 5.0,
                "quality": "unknown",
                "action": "needs_review",
                "error": str(e)
            }
    
    def _format_feedback_for_improvement(self, review_feedback: Dict[str, Any]) -> str:
        """
        Format review feedback into a clear improvement prompt.
        
        Args:
            review_feedback: Review feedback from plan reviewer
            
        Returns:
            Formatted feedback string for plan improvement
        """
        
        try:
            feedback_parts = []
            
            # Overall assessment
            overall = review_feedback.get("overall_assessment", {})
            if overall:
                feedback_parts.append(f"OVERALL ASSESSMENT: {overall.get('summary', '')}")
                feedback_parts.append(f"Current Score: {overall.get('score', 'N/A')}/10")
                feedback_parts.append(f"Recommendation: {overall.get('recommendation', 'N/A')}")
                feedback_parts.append("")
            
            # Critical and high-priority issues
            issues = review_feedback.get("issues", [])
            critical_issues = [issue for issue in issues if issue.get("severity") in ["critical", "high"]]
            
            if critical_issues:
                feedback_parts.append("CRITICAL ISSUES TO ADDRESS:")
                for i, issue in enumerate(critical_issues, 1):
                    feedback_parts.append(f"{i}. {issue.get('description', '')}")
                    if issue.get("suggestion"):
                        feedback_parts.append(f"   Solution: {issue['suggestion']}")
                    feedback_parts.append("")
            
            # High-priority improvements
            improvements = review_feedback.get("improvements", [])
            high_priority = [imp for imp in improvements if imp.get("priority") == "high"]
            
            if high_priority:
                feedback_parts.append("HIGH-PRIORITY IMPROVEMENTS:")
                for i, improvement in enumerate(high_priority, 1):
                    feedback_parts.append(f"{i}. {improvement.get('description', '')}")
                    if improvement.get("specific_changes"):
                        feedback_parts.append(f"   Changes: {improvement['specific_changes']}")
                    feedback_parts.append("")
            
            # Questions that need addressing
            questions = review_feedback.get("questions", [])
            if questions:
                feedback_parts.append("QUESTIONS TO CONSIDER:")
                for i, question in enumerate(questions, 1):
                    feedback_parts.append(f"{i}. {question}")
                feedback_parts.append("")
            
            # Strengths to maintain
            strengths = review_feedback.get("strengths", [])
            if strengths:
                feedback_parts.append("STRENGTHS TO MAINTAIN:")
                for strength in strengths:
                    feedback_parts.append(f"- {strength}")
            
            return "\n".join(feedback_parts)
            
        except Exception as e:
            self.logger.error(f"Failed to format feedback: {e}")
            return "Please improve the plan based on the review feedback provided."
    
    def _generate_improvement_summary(self) -> Dict[str, Any]:
        """Generate a summary of improvements made during the planning cycle."""
        
        if len(self.plan_history) < 2:
            return {"improvements_made": False, "summary": "No iterations completed"}
        
        first_plan = self.plan_history[0]["plan"]
        final_plan = self.plan_history[-1]["plan"]
        
        # Compare plan metrics
        initial_phases = len(first_plan.get("phases", []))
        final_phases = len(final_plan.get("phases", []))
        
        initial_complexity = first_plan.get("project_info", {}).get("complexity", 0)
        final_complexity = final_plan.get("project_info", {}).get("complexity", 0)
        
        # Collect review scores
        scores = []
        for review in self.review_history:
            overall = review["review"].get("overall_assessment", {})
            score = overall.get("score")
            if score:
                scores.append(score)
        
        score_improvement = scores[-1] - scores[0] if len(scores) >= 2 else 0
        
        return {
            "improvements_made": True,
            "iterations_completed": self.current_iteration,
            "phase_count_change": final_phases - initial_phases,
            "complexity_change": final_complexity - initial_complexity,
            "score_improvement": score_improvement,
            "initial_score": scores[0] if scores else None,
            "final_score": scores[-1] if scores else None,
            "total_reviews": len(self.review_history)
        }
    
    def _reset_iteration_state(self):
        """Reset iteration tracking state for a new planning cycle."""
        self.current_iteration = 0
        self.plan_history.clear()
        self.review_history.clear()
        self.iteration_start_time = None
    
    async def _save_iteration_debug(self, iteration: int, plan: Dict[str, Any], 
                                  review: Optional[Dict[str, Any]], iteration_type: str):
        """Save debug information for a specific iteration."""
        
        if not self.debug_mode:
            return
        
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"iteration_{iteration:02d}_{iteration_type}_{timestamp}.json"
            filepath = self.debug_dir / filename
            
            debug_data = {
                "iteration": iteration,
                "type": iteration_type,
                "timestamp": datetime.now().isoformat(),
                "plan": plan,
                "review": review
            }
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(debug_data, f, indent=2, ensure_ascii=False)
            
            self.logger.debug(f"Iteration debug saved: {filepath}")
            
        except Exception as e:
            self.logger.warning(f"Failed to save iteration debug: {e}")
    
    async def _save_final_results(self, result: Dict[str, Any]):
        """Save final deep planning results."""
        
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"deep_planning_results_{timestamp}.json"
            filepath = self.output_dir / filename
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Deep planning results saved: {filepath}")
            
        except Exception as e:
            self.logger.warning(f"Failed to save final results: {e}")
    
    def format_review_for_display(self, review_feedback: Dict[str, Any]) -> str:
        """
        Format review feedback for user-friendly display.
        
        Args:
            review_feedback: Review feedback dictionary
            
        Returns:
            Formatted string for display
        """
        
        try:
            lines = []
            
            # Header
            lines.append("🔍 PLAN REVIEW FEEDBACK")
            lines.append("=" * 50)
            lines.append("")
            
            # Overall Assessment
            overall = review_feedback.get("overall_assessment", {})
            if overall:
                score = overall.get("score", "N/A")
                summary = overall.get("summary", "No summary available")
                recommendation = overall.get("recommendation", "N/A")
                
                lines.append(f"📊 Overall Score: {score}/10")
                lines.append(f"📝 Summary: {summary}")
                lines.append(f"🎯 Recommendation: {recommendation.replace('_', ' ').title()}")
                lines.append("")
            
            # Strengths
            strengths = review_feedback.get("strengths", [])
            if strengths:
                lines.append("✅ STRENGTHS:")
                for strength in strengths:
                    lines.append(f"  • {strength}")
                lines.append("")
            
            # Issues
            issues = review_feedback.get("issues", [])
            if issues:
                lines.append("⚠️  ISSUES TO ADDRESS:")
                for issue in issues:
                    severity = issue.get("severity", "medium").upper()
                    description = issue.get("description", "No description")
                    suggestion = issue.get("suggestion", "")
                    
                    lines.append(f"  🔸 [{severity}] {description}")
                    if suggestion:
                        lines.append(f"     💡 Suggestion: {suggestion}")
                lines.append("")
            
            # Improvements
            improvements = review_feedback.get("improvements", [])
            if improvements:
                lines.append("🚀 IMPROVEMENT OPPORTUNITIES:")
                for improvement in improvements:
                    priority = improvement.get("priority", "medium").upper()
                    description = improvement.get("description", "No description")
                    changes = improvement.get("specific_changes", "")
                    
                    lines.append(f"  🔹 [{priority}] {description}")
                    if changes:
                        lines.append(f"     🔧 Changes: {changes}")
                lines.append("")
            
            # Questions
            questions = review_feedback.get("questions", [])
            if questions:
                lines.append("❓ QUESTIONS FOR CONSIDERATION:")
                for question in questions:
                    lines.append(f"  • {question}")
                lines.append("")
            
            return "\n".join(lines)
            
        except Exception as e:
            self.logger.error(f"Failed to format review for display: {e}")
            return f"Review feedback available but formatting failed: {e}"
    
    def get_iteration_summary(self) -> Dict[str, Any]:
        """Get a summary of the current iteration state."""
        
        return {
            "current_iteration": self.current_iteration,
            "max_iterations": self.max_iterations,
            "total_plans_generated": len(self.plan_history),
            "total_reviews_completed": len(self.review_history),
            "elapsed_time": (datetime.now() - self.iteration_start_time).total_seconds() 
                           if self.iteration_start_time else 0,
            "convergence_threshold": self.convergence_threshold
        }