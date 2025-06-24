#!/usr/bin/env python3
"""
LazyToCode - Multi-Agent AI Coding System

A CLI tool that uses a multi-agent system to plan, write, and review
complete software projects based on user prompts.
"""

import asyncio
import sys
import argparse
import os
from pathlib import Path
from dotenv import load_dotenv

from utils.logger import setup_logger, get_logger
from config.agent_config import ModelClientFactory
from agents.planner_agent import PlannerAgent
from agents.writer_agent import WriterAgent
from agents.reviewer_agent import ReviewerAgent
from orchestrator import WorkflowOrchestrator
from utils.agent_messages import ProjectInfo


def parse_arguments():
    """Parse command line arguments for LazyToCode CLI."""
    load_dotenv()
    
    parser = argparse.ArgumentParser(
        description="LazyToCode - Multi-Agent AI Coding System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --prompt "Create a Python CLI calculator"
  python main.py --prompt "Build a FastAPI REST API" --output-dir ./my_api --retry-attempts 2
  python main.py --prompt ./prompts/web_scraper.txt --model qwen2.5-coder:14b --debug
        """
    )
    
    # Required arguments
    parser.add_argument(
        "--prompt",
        type=str,
        required=True,
        help="Text prompt or path to .txt file containing project description"
    )
    
    # Optional arguments
    parser.add_argument(
        "--output-dir",
        type=str,
        default=os.getenv("DEFAULT_OUTPUT_DIR", "./output"),
        help="Output directory for generated code (default: ./output)"
    )
    
    parser.add_argument(
        "--model",
        type=str,
        default=os.getenv("OLLAMA_MODEL", "qwen2.5-coder:14b"),
        help="Model name (default: qwen2.5-coder:14b)"
    )
    
    parser.add_argument(
        "--model-provider",
        type=str,
        choices=["ollama", "llamacpp", "openai"],
        default="ollama",
        help="Provider choice - 'ollama', 'llamacpp', or 'openai' (default: ollama)"
    )
    
    parser.add_argument(
        "--retry-attempts",
        type=int,
        default=3,
        help="Maximum retry attempts per phase (default: 3)"
    )
    
    parser.add_argument(
        "--max-phases", 
        type=int,
        default=10,
        help="Maximum number of phases (default: 10)"
    )
    
    parser.add_argument(
        "--timeout",
        type=int,
        default=60,
        help="Workflow timeout in minutes (default: 60)"
    )
    
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable verbose logging"
    )
    
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Enable interactive plan approval mode"
    )
    
    args = parser.parse_args()
    
    # Validate and process arguments
    args = _validate_arguments(args)
    
    return args


def _validate_arguments(args):
    """Validate and process parsed arguments."""
    # Process prompt - check if it's a file path
    if args.prompt.endswith('.txt') and os.path.isfile(args.prompt):
        with open(args.prompt, 'r', encoding='utf-8') as f:
            args.prompt_content = f.read().strip()
        args.prompt_type = 'file'
        args.prompt_file = args.prompt
    else:
        args.prompt_content = args.prompt
        args.prompt_type = 'text'
        args.prompt_file = None
    
    # Validate and create output directory
    output_path = Path(args.output_dir)
    if not output_path.exists():
        output_path.mkdir(parents=True, exist_ok=True)
    args.output_dir = output_path.absolute()
    
    # Convert model-provider to model_provider for internal use
    args.model_provider = getattr(args, 'model_provider', None) or getattr(args, 'model-provider', 'ollama')
    
    return args


async def main():
    """Main async function for LazyToCode CLI."""
    
    logger = None
    
    try:
        # Parse command line arguments
        args = parse_arguments()
        
        # Setup logging with debug directory
        debug_dir = args.output_dir / "debug" if args.debug else None
        logger = setup_logger(
            debug_mode=args.debug,
            log_file="lazytocode.log" if args.debug else None,
            debug_dir=debug_dir
        )
        
        logger.info("LazyToCode starting...")
        logger.debug(f"Arguments: {vars(args)}")
        
        # Initialize model client
        logger.info(f"Initializing {args.model_provider} model client...")
        
        model_factory = ModelClientFactory()
        model_client = model_factory.create_client(
            provider=args.model_provider,
            model=args.model
        )
        
        # Validate model client
        is_valid = await model_factory.validate_client(model_client, args.model)
        if not is_valid:
            logger.error("Model client validation failed")
            return 1
        
        logger.info("Model client initialized successfully")
        
        # Create project info
        project_info = ProjectInfo(
            prompt=args.prompt_content,
            project_type="auto_detect",  # Let the model determine project type
            language="auto_detect",  # Let the model determine the appropriate language
            output_dir=str(args.output_dir)
        )
        
        # Create agents
        logger.info("Creating multi-agent system...")
        
        planner = PlannerAgent(
            name="PlannerAgent",
            model_client=model_client,
            output_dir=args.output_dir,
            max_phases=args.max_phases,
            debug_mode=args.debug
        )
        
        writer = WriterAgent(
            name="WriterAgent",
            model_client=model_client,
            output_dir=args.output_dir
        )
        
        reviewer = ReviewerAgent(
            name="ReviewerAgent",
            model_client=model_client,
            output_dir=args.output_dir
        )
        
        logger.info("Multi-agent system created successfully")
        
        # Create and configure orchestrator
        logger.info("Initializing workflow orchestrator...")
        
        orchestrator = WorkflowOrchestrator(
            project_info=project_info,
            max_attempts=args.retry_attempts,
            timeout_minutes=args.timeout,
            interactive_mode=args.interactive
        )
        
        # Register agents
        orchestrator.register_agent("planner", planner)
        orchestrator.register_agent("writer", writer)
        orchestrator.register_agent("reviewer", reviewer)
        
        logger.info("Workflow orchestrator initialized successfully")
        
        # Execute workflow
        logger.info("Starting multi-agent workflow...")
        print("🚀 Starting LazyToCode multi-agent workflow...")
        print(f"📝 Project: {args.prompt_content}")
        print(f"📁 Output: {args.output_dir}")
        print(f"🤖 Model: {args.model} ({args.model_provider})")
        print(f"🔄 Max attempts per phase: {args.retry_attempts}")
        print()
        
        result = await orchestrator.execute_workflow()
        
        # Process results
        if result["success"]:
            logger.info("Multi-agent workflow completed successfully!")
            
            print("✅ Project generation completed successfully!")
            print()
            
            # Show generated files
            generated_files = result.get("generated_files", [])
            if generated_files:
                print(f"📄 Generated {len(generated_files)} files:")
                for file_info in generated_files:
                    print(f"  - {file_info['filename']} ({file_info['language']})")
                print()
            
            # Show summary
            summary = result.get("summary", {})
            if summary:
                print("📊 Project Summary:")
                phases_info = summary.get('phases', {})
                statistics = summary.get('statistics', {})
                
                print(f"  Total phases: {phases_info.get('total', 0)}")
                print(f"  Completed phases: {phases_info.get('completed', 0)}")
                print(f"  Duration: {summary.get('duration', 'Unknown'):.2f}s" if isinstance(summary.get('duration'), (int, float)) else f"  Duration: {summary.get('duration', 'Unknown')}")
                print(f"  Total files: {len(generated_files)}")
                print(f"  Total phase attempts: {statistics.get('phase_attempts', 0)}")
                
                # Show detailed phase execution information
                phase_details = phases_info.get('details', [])
                if phase_details:
                    print("\n📋 Phase Execution Details:")
                    for phase in phase_details:
                        status_emoji = "✅" if phase['status'] == 'completed' else "❌" if phase['status'] == 'failed' else "⏳"
                        attempts_info = f"{phase['attempts']} attempt{'s' if phase['attempts'] != 1 else ''}"
                        duration_info = f"{phase['duration']:.1f}s" if isinstance(phase.get('duration'), (int, float)) else "N/A"
                        files_info = f"{phase['files_generated']} file{'s' if phase['files_generated'] != 1 else ''}"
                        
                        print(f"    {status_emoji} {phase['name']}: {attempts_info}, {duration_info}, {files_info}")
                
                print()
            
            print(f"🎉 Your project is ready in: {args.output_dir}")
            
            # Show next steps
            print("\n🚀 Next steps:")
            print(f"  1. cd {args.output_dir}")
            print("  2. Review the generated files")
            print("  3. Install dependencies if needed (pip install -r requirements.txt)")
            print("  4. Run your application!")
            
            return 0
            
        else:
            error_msg = result.get('error', 'Unknown error')
            logger.error(f"Multi-agent workflow failed: {error_msg}")
            
            print(f"❌ Project generation failed: {error_msg}")
            
            # Show partial results if any
            generated_files = result.get("generated_files", [])
            if generated_files:
                print(f"\n📄 Partial results ({len(generated_files)} files generated):")
                for file_info in generated_files:
                    print(f"  - {file_info['filename']}")
                print(f"\nFiles saved to: {args.output_dir}")
            
            summary = result.get("summary", {})
            if summary:
                print("\n📊 Workflow Summary:")
                print(f"  Status: {summary.get('status', 'Unknown')}")
                phases_info = summary.get('phases', {})
                statistics = summary.get('statistics', {})
                print(f"  Completed phases: {phases_info.get('completed', 0)}/{phases_info.get('total', 0)}")
                print(f"  Total phase attempts: {statistics.get('phase_attempts', 0)}")
                if summary.get('duration'):
                    duration = summary['duration']
                    if isinstance(duration, (int, float)):
                        print(f"  Duration: {duration:.2f}s")
                
                # Show phase attempt details even in failure case
                phase_details = phases_info.get('details', [])
                if phase_details:
                    print("\n📋 Phase Execution Details:")
                    for phase in phase_details:
                        status_emoji = "✅" if phase['status'] == 'completed' else "❌" if phase['status'] == 'failed' else "⏳"
                        attempts_info = f"{phase['attempts']} attempt{'s' if phase['attempts'] != 1 else ''}"
                        duration_info = f"{phase['duration']:.1f}s" if isinstance(phase.get('duration'), (int, float)) else "N/A"
                        files_info = f"{phase['files_generated']} file{'s' if phase['files_generated'] != 1 else ''}"
                        
                        print(f"    {status_emoji} {phase['name']}: {attempts_info}, {duration_info}, {files_info}")
            
            return 1
    
    except KeyboardInterrupt:
        if logger:
            logger.info("Operation cancelled by user")
        print("\n🛑 Operation cancelled by user")
        return 130
    
    except Exception as e:
        if logger:
            logger.error(f"Unexpected error: {e}")
        print(f"❌ Unexpected error: {e}")
        if args and args.debug:
            import traceback
            traceback.print_exc()
        return 1
    
    finally:
        if logger:
            logger.info("LazyToCode finished")


def cli_main():
    """Entry point for CLI execution."""
    
    try:
        # Run the async main function
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
        
    except KeyboardInterrupt:
        print("\n🛑 Operation cancelled by user")
        sys.exit(130)
    
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    cli_main()