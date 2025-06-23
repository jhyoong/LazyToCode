#!/usr/bin/env python3
"""
LazyToCode - AI Coding Agent using Microsoft Autogen

A CLI tool that uses Microsoft's Autogen library to build an AI agent 
capable of writing code based on user prompts.
"""

import asyncio
import sys
from pathlib import Path

from utils.cli_parser import parse_arguments
from utils.logger import setup_logger, get_logger
from config.agent_config import ModelClientFactory
from agents.coding_assistant import CodingAssistant
from agents.user_proxy import UserProxy

async def main():
    """Main async function for LazyToCode CLI."""
    
    logger = None
    
    try:
        # Parse command line arguments
        args = parse_arguments()
        
        # Setup logging
        logger = setup_logger(
            debug_mode=args.debug,
            log_file="lazytocode.log" if args.debug else None
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
        
        # Create agents
        logger.info("Creating agents...")
        
        coding_assistant = CodingAssistant(
            name="CodingAssistant",
            model_client=model_client,
            output_dir=args.output_dir
        )
        
        user_proxy = UserProxy(
            name="UserProxy",
            output_dir=args.output_dir
        )
        
        logger.info("Agents created successfully")
        
        # Execute workflow
        logger.info("Starting code generation workflow...")
        
        result = await user_proxy.execute_workflow(
            coding_assistant=coding_assistant,
            prompt=args.prompt_content,
            prompt_type=args.prompt_type,
            debug_mode=args.debug
        )
        
        # Process results
        if result["status"] == "success":
            logger.info("Code generation completed successfully!")
            
            if result["output_file"]:
                print(f"✅ Code generated and saved to: {result['output_file']}")
            else:
                print("✅ Code generated successfully")
                print("\nGenerated Code:")
                print("-" * 50)
                print(result["generated_code"])
                print("-" * 50)
            
            # Show summary if debug mode
            if args.debug:
                summary = await user_proxy.get_generation_summary()
                logger.debug(f"Generation summary: {summary}")
                
                print(f"\nOutput directory: {summary['output_directory']}")
                print(f"Total files: {summary['total_files']}")
                
                if summary['files']:
                    print("\nGenerated files:")
                    for file_info in summary['files']:
                        print(f"  - {file_info['name']} ({file_info['size']} bytes)")
            
            return 0
            
        else:
            logger.error(f"Code generation failed: {result.get('error', 'Unknown error')}")
            print(f"❌ Code generation failed: {result.get('error', 'Unknown error')}")
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