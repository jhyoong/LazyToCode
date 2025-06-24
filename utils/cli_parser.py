import argparse
import os
from pathlib import Path
from dotenv import load_dotenv

def parse_arguments():
    """Parse command line arguments for LazyToCode CLI."""
    load_dotenv()
    
    parser = argparse.ArgumentParser(
        description="LazyToCode - AI Coding Agent using Microsoft Autogen",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --prompt "Create a Python function to calculate fibonacci numbers"
  python main.py --prompt ./prompts/web_scraper.txt --output_dir ./my_code --model llama3
  python main.py --prompt "Build a REST API" --model_provider llamacpp --debug
        """
    )
    
    # Required arguments
    parser.add_argument(
        "--prompt",
        type=str,
        required=True,
        help="Text prompt or path to .txt file containing prompt"
    )
    
    # Optional arguments
    parser.add_argument(
        "--output_dir",
        type=str,
        default=os.getenv("DEFAULT_OUTPUT_DIR", "./output"),
        help="Output directory for generated code (default: ./output)"
    )
    
    parser.add_argument(
        "--model",
        type=str,
        default=os.getenv("OLLAMA_MODEL", "Qwen2.5-Coder:14b"),
        help="Model name (default: Qwen2.5-Coder:14b)"
    )
    
    parser.add_argument(
        "--model_provider",
        type=str,
        choices=["ollama", "llamacpp", "openai"],
        default="ollama",
        help="Provider choice - 'ollama', 'llamacpp', or 'openai' (default: ollama)"
    )
    
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable verbose logging"
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
    
    return args