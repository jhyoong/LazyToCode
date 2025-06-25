# LazyToCode

> [!IMPORTANT]  
> **This is a hobby project that's a work in progess. Expect bugs and breaking changes.**

AI-powered multi-agent development system that generates complete software projects from simple prompts. Uses specialized agents for planning, writing, and reviewing code to create (hopefully) production-ready applications.

## Features

- **Multi-Agent Architecture** - Planner, Writer, Reviewer, and Plan Reviewer agents work together
- **Deep Planning Mode** - AI-driven plan review and iterative improvement using reflection
- **Complete Project Generation** - Creates multi-file projects with documentation and tests
- **Phase-Based Development** - Complex projects split into manageable phases
- **Interactive Mode** - Review, modify, or reject plans before code generation
- **Model Support** - Works with Ollama, LlamaCpp, and OpenAI providers
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

# Use deep planning mode for AI-driven plan improvement
python main.py --prompt "Build a web API" --deep-plan

# Use interactive mode to review and approve plans
python main.py --prompt "Build a web API" --interactive

# Use file input with debug mode
python main.py --prompt ./project_spec.txt --debug

# Custom output and model with deep planning
python main.py --prompt "Build a web API" --output-dir ./api --model llama3 --deep-plan
```

## Options

| Flag | Description | Default |
|------|-------------|---------|
| `--prompt` | Text prompt or .txt file path | Required |
| `--output-dir` | Output directory | `./output` |
| `--model` | Model name | `qwen2.5-coder:14b` |
| `--model-provider` | `ollama`, `llamacpp`, or `openai` | `ollama` |
| `--retry-attempts` | Max retry attempts per phase | `3` |
| `--max-phases` | Maximum number of phases | `10` |
| `--timeout` | Workflow timeout in minutes | `60` |
| `--interactive` | Enable plan approval mode | `false` |
| `--deep-plan` | Enable AI plan review and reflection | `false` |
| `--debug` | Verbose logging | `false` |

## How It Works

**Multi-Agent Workflow:**

1. **Planner Agent** - Analyzes prompt and creates detailed implementation plan
2. **Plan Reviewer Agent** - Critiques and improves plans through AI reflection (deep planning mode)
3. **Writer Agent** - Generates code files based on the plan  
4. **Reviewer Agent** - Validates implementation against success criteria
5. **Orchestrator** - Coordinates agents with retry logic and phase management

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
│   ├── plan_reviewer_agent.py # AI plan review and reflection
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
│   ├── deep_planner.py    # Deep planning reflection manager
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

## Deep Planning Mode

The `--deep-plan` flag enables advanced AI-driven plan improvement using the **Microsoft Autogen Reflection design pattern**. This mode uses iterative AI reflection to systematically improve implementation plans before code generation.

### How Deep Planning Works

1. **Initial Planning** - Planner Agent generates the first implementation plan
2. **AI Review** - Plan Reviewer Agent analyzes the plan and provides structured feedback
3. **Plan Improvement** - Planner Agent incorporates feedback and generates an improved plan
4. **Iteration** - Steps 2-3 repeat up to 3 times or until convergence
5. **Best Plan Selection** - The highest-quality plan version is selected for code generation

### Deep Planning Features

- **Structured Critique** - AI reviews plans across multiple dimensions (completeness, feasibility, best practices)
- **Iterative Improvement** - Plans are systematically refined through multiple reflection cycles
- **Quality Scoring** - Each plan version receives a quality score (1-10) for objective comparison
- **Convergence Detection** - Process terminates early when high quality is achieved
- **Transparent Process** - Users see each iteration and the improvements made

### Deep Planning Examples

**Basic Deep Planning:**
```bash
python main.py --prompt "Create a web scraper" --deep-plan
```

**Deep Planning with Debug:**
```bash
python main.py --prompt "Build a REST API" --deep-plan --debug
```

**Deep Planning Output:**
```
🧠 DEEP PLANNING SUMMARY
==================================================
🔄 Reflection Iterations: 3
📊 Final Plan Score: 8.5/10
⏱️  Deep Planning Duration: 45.2s
📈 Score Improvement: +2.1 points
🎯 Convergence: High quality threshold reached
✅ Deep planning completed - using improved plan
```

### When to Use Deep Planning

- **Complex Projects** - Multi-component applications with intricate requirements
- **Quality Critical** - Projects where plan quality directly impacts success
- **Learning** - Understanding how AI improves software architecture decisions
- **Best Practices** - Ensuring generated code follows industry standards

### Deep Planning vs Interactive Mode

| Feature | Deep Planning | Interactive Mode |
|---------|--------------|------------------|
| **Reviewer** | AI Plan Reviewer Agent | Human user |
| **Feedback** | Structured AI critique | Natural language feedback |
| **Iterations** | Automatic (up to 3) | User-controlled |
| **Speed** | Faster (no user input) | Slower (requires user interaction) |
| **Consistency** | Consistent AI evaluation | Variable user expertise |
| **Use Case** | Automated quality improvement | User control and customization |

> **Note:** Deep planning and interactive mode are mutually exclusive. Deep planning takes precedence when both flags are provided.

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
- ✅ Deep planning mode with AI plan review and reflection
- ✅ Multi-file project generation 
- ✅ Phase-based development with retry logic
- ✅ Interactive plan approval and modification mode
- ✅ Ollama, LlamaCpp, and OpenAI model support

**In Development:**
- 🚧 Test and Fix workflow (Tester → Fixing agents)
- 🚧 Containerized testing environment
- 🚧 Build validation and error analysis

Built with Microsoft Autogen framework.