# LazyToCode

> [!IMPORTANT]  
> **This is a hobby project that's a work in progess. Expect bugs and breaking changes.**

AI-powered multi-agent development system that generates complete software projects from simple prompts. Uses specialized agents for planning, writing, and reviewing code to create (hopefully) production-ready applications.

## Features

- **Multi-Agent Architecture** - Planner, Writer, and Reviewer agents work together
- **Complete Project Generation** - Creates multi-file projects with documentation and tests
- **Phase-Based Development** - Complex projects split into manageable phases
- **Interactive Mode** - Review, modify, or reject plans before code generation
- **Model Support** - Works with Ollama and LlamaCpp providers
- **Workflow Orchestration** - Automated retry and validation loops
- **Debug Mode** - Comprehensive logging and plan persistence

## Installation

**Prerequisites:** Python 3.10+, Ollama or LlamaCpp

```bash
git clone <repository-url>
cd LazyToCode
python -m venv lazyenv
source lazyenv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # Edit with your model settings
```

## Usage

```bash
# Generate a complete project
python main.py --prompt "Create a CLI calculator with tests"

# Use interactive mode to review and approve plans
python main.py --prompt "Build a web API" --interactive

# Use file input with debug mode
python main.py --prompt ./project_spec.txt --debug

# Custom output and model
python main.py --prompt "Build a web API" --output-dir ./api --model llama3
```

## Options

| Flag | Description | Default |
|------|-------------|---------|
| `--prompt` | Text prompt or .txt file path | Required |
| `--output-dir` | Output directory | `./output` |
| `--model` | Model name | `qwen2.5-coder:14b` |
| `--model-provider` | `ollama` or `llamacpp` | `ollama` |
| `--retry-attempts` | Max retry attempts per phase | `3` |
| `--max-phases` | Maximum number of phases | `10` |
| `--timeout` | Workflow timeout in minutes | `60` |
| `--interactive` | Enable plan approval mode | `false` |
| `--debug` | Verbose logging | `false` |

## How It Works

**Multi-Agent Workflow:**

1. **Planner Agent** - Analyzes prompt and creates detailed implementation plan
2. **Writer Agent** - Generates code files based on the plan  
3. **Reviewer Agent** - Validates implementation against success criteria
4. **Orchestrator** - Coordinates agents with retry logic and phase management

**Project Generation:**
- Complex projects are split into phases
- Each phase is implemented and reviewed before proceeding
- Automatic retry on validation failures (configurable attempts)
- Complete project structure with documentation and tests

## Project Structure

```
LazyToCode/
├── main.py                # CLI entry point  
├── orchestrator.py        # Workflow coordination
├── agents/                # Multi-agent system
│   ├── planner_agent.py   # Project planning
│   ├── writer_agent.py    # Code generation
│   ├── reviewer_agent.py  # Validation
│   ├── base_agent.py      # Foundation
│   ├── coding_assistant.py # Legacy agent
│   └── user_proxy.py      # Agent communication
├── config/                # Model configuration
│   └── agent_config.py    # Model client factory
├── utils/                 # Core utilities
│   ├── logger.py          # Logging system
│   ├── agent_messages.py  # Message structures
│   ├── workflow_state.py  # State management
│   ├── file_handler.py    # File operations
│   ├── interactive_reviewer.py # Interactive plan review
│   └── plan_formatter.py  # Plan presentation formatting
└── output/                # Generated projects
```

## Configuration

Create `.env` file:

```bash
# Ollama
OLLAMA_ENDPOINT=http://localhost:11434
OLLAMA_MODEL=qwen2.5-coder:14b

# LlamaCpp  
LLAMACPP_MODEL_PATH=/path/to/model.gguf
LLAMACPP_N_GPU_LAYERS=-1
LLAMACPP_N_CTX=4096
```

## Interactive Mode

The `--interactive` flag enables plan approval mode, allowing you to review and modify implementation plans before code generation begins.

### How Interactive Mode Works

1. **Plan Generation** - AI generates an initial implementation plan
2. **Plan Review** - Plan is presented in a user-friendly format
3. **User Decision** - Choose to approve, modify, or reject the plan
4. **Plan Modification** - Request changes with natural language feedback
5. **Iterative Refinement** - Repeat modification until satisfied
6. **Code Generation** - Approved plan proceeds to code generation

### Interactive Commands

```bash
# During plan review, use these commands:
approve (a)  - Approve plan and proceed with code generation
modify (m)   - Request modifications with feedback
reject (r)   - Reject plan and exit
details (d)  - Show detailed plan breakdown
help (h)     - Show command help
```

### Interactive Mode Examples

**Basic Interactive Usage:**
```bash
python main.py --prompt "Create a web scraper" --interactive
```

**Interactive with Custom Settings:**
```bash
python main.py --prompt "Build a REST API" --interactive --debug --max-phases 5
```

**Sample Interactive Session:**
```
📋 Generated Implementation Plan
═══════════════════════════════

🎯 Project: Web Scraper Tool
📁 Type: CLI Tool
🏗️  Complexity: 3/5
📦 Main Language: Python

📋 PHASES (3 total):
├─ Phase 1: Project Setup
│  ├─ Files: setup.py, requirements.txt, README.md
│  └─ Dependencies: requests, beautifulsoup4
├─ Phase 2: Core Scraper Implementation
│  ├─ Files: scraper.py, cli.py
│  └─ Dependencies: argparse, logging
└─ Phase 3: Testing & Documentation
   ├─ Files: test_scraper.py, docs/
   └─ Dependencies: pytest

Your choice: modify
What would you like to modify? Add error handling and rate limiting

🔄 Regenerating plan with your feedback...
✅ Plan updated with your feedback

[Updated plan displayed...]

Your choice: approve
✅ Plan approved! Proceeding with code generation...
```

## Examples

**Simple Project:**
```bash
python main.py --prompt "Create a CLI calculator with error handling"
```

**Complex Application:**
```bash  
python main.py --prompt "Build a FastAPI REST service with database integration" --debug
```

**Generated Output:**
- Complete project structure with multiple files
- Documentation (README.md, setup.py)
- Test files and configuration
- Debug logs and implementation plans (when using --debug)

## Status

**Currently Implemented:**
- ✅ Plan and Create workflow (Planner → Writer → Reviewer)
- ✅ Multi-file project generation 
- ✅ Phase-based development with retry logic
- ✅ Interactive plan approval and modification mode
- ✅ Ollama and LlamaCpp model support

**In Development:**
- 🚧 Test and Fix workflow (Tester → Fixing agents)
- 🚧 Containerized testing environment
- 🚧 Build validation and error analysis

Built with Microsoft Autogen framework.