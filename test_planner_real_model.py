#!/usr/bin/env python3
"""
Quick test for Planner Agent with real model integration.
"""

import asyncio
import sys
from pathlib import Path

# Add the project root to the path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from agents.planner_agent import PlannerAgent
from config.agent_config import ModelClientFactory
from utils.logger import get_logger


async def test_real_model_integration():
    """Test Planner Agent with real model client."""
    
    # Configure logging
    import logging
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    
    logger = get_logger()
    logger.info("Starting Real Model Integration Test")
    
    try:
        # Create real model client
        model_factory = ModelClientFactory()
        model_client = model_factory.create_client(
            provider="ollama", 
            model="Qwen2.5-Coder:14b"
        )
        
        # Create output directory
        output_dir = Path("./test_output")
        output_dir.mkdir(exist_ok=True)
        
        # Initialize Planner Agent with debug mode enabled
        planner = PlannerAgent(
            name="RealModelTestAgent",
            model_client=model_client,
            output_dir=output_dir,
            debug_mode=True
        )
        
        await planner.initialize()
        
        # Test with simple prompt
        prompt = "Create a Python function to calculate fibonacci numbers"
        logger.info(f"Testing with prompt: {prompt}")
        
        # Generate plan
        plan = await planner.generate_plan(prompt)
        
        # Verify results
        logger.info("✅ Plan generated successfully!")
        logger.info(f"Project: {plan['project_info']['name']}")
        logger.info(f"Type: {plan['project_info']['type']}")
        logger.info(f"Phases: {len(plan['phases'])}")
        
        # Print first phase details
        if plan['phases']:
            first_phase = plan['phases'][0]
            logger.info(f"First phase: {first_phase['name']}")
            logger.info(f"Files to create: {first_phase.get('files', [])}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(test_real_model_integration())
    print(f"\nReal model integration test: {'PASSED' if success else 'FAILED'}")
    sys.exit(0 if success else 1)