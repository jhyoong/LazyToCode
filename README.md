# LazyToCode

An AI-powered coding agent that generates clean, production-ready code using Microsoft's Autogen framework. LazyToCode intelligently extracts code from AI responses, removing explanations and formatting to deliver pure, executable code files.

## ✨ Features

- 🤖 **AI Code Generation** - Uses Microsoft Autogen with Ollama/LlamaCpp models
- 🧹 **Smart Code Extraction** - Automatically extracts clean code from AI responses
- 🔍 **Language Detection** - Auto-detects programming languages and assigns proper file extensions
- 📝 **Debug Mode** - Saves both clean code and full AI responses for analysis
- 🎯 **Multi-Language Support** - Python, JavaScript, Java, C++, HTML, CSS, SQL, Bash, and more
- ⚡ **Async Architecture** - High-performance async implementation
- 🔒 **Secure Configuration** - Environment-based secrets management
- 📁 **Flexible Output** - Configurable output directories and file naming

## 🛠️ Installation

### Prerequisites
- Python 3.10+
- Ollama (for local models) or LlamaCpp support

### Setup
```bash
# Clone the repository
git clone <repository-url>
cd LazyToCode

# Create virtual environment
python -m venv lazyenv
source lazyenv/bin/activate  # On Windows: lazyenv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your model configurations
```

## 🚀 Quick Start

### Basic Usage
```bash
# Generate a simple Python script
python main.py --prompt "Write a hello world Python script"

# Generate a complex function
python main.py --prompt "Create a Python function to calculate fibonacci numbers with memoization"

# Generate with debug information
python main.py --prompt "Build a REST API with FastAPI" --debug
```

### Advanced Usage
```bash
# Custom output directory
python main.py --prompt "Create a web scraper" --output_dir ./scrapers

# Use different model
python main.py --prompt "Build a calculator" --model llama3

# Use LlamaCpp provider
python main.py --prompt "Create a game" --model_provider llamacpp

# File-based prompts
python main.py --prompt ./complex_request.txt --debug
```

## 📋 Command Line Options

| Option | Description | Default | Required |
|--------|-------------|---------|----------|
| `--prompt` | Text prompt or path to .txt file | - | ✅ |
| `--output_dir` | Output directory for generated code | `./output` | ❌ |
| `--model` | Model name to use | `Qwen2.5-Coder` | ❌ |
| `--model_provider` | Model provider (`ollama` or `llamacpp`) | `ollama` | ❌ |
| `--debug` | Enable verbose logging and save full responses | `false` | ❌ |
| `--help` | Show help message | - | ❌ |

## 🧠 How It Works

### Smart Code Extraction

LazyToCode intelligently processes AI model responses to extract clean, executable code:

**Before (Raw AI Response):**
```
Certainly! Below is a Python function that calculates Fibonacci numbers using memoization...

```python
def fibonacci(n, memo=None):
    if memo is None:
        memo = {}
    # ... rest of code
```

### Explanation:
- The function uses memoization to improve performance...
- Base cases handle n=0 and n=1...
```

**After (Clean Extracted Code):**
```python
def fibonacci(n, memo=None):
    if memo is None:
        memo = {}
    # ... rest of code
```

### Debug Mode

When using `--debug`, LazyToCode saves two files:

1. **Clean Code File** (e.g., `fibonacci.py`) - Production-ready code
2. **Debug Response File** (e.g., `fibonacci_full_response.md`) - Complete AI response with explanations

## 🏗️ Project Structure

```
LazyToCode/
├── main.py                 # CLI entry point
├── requirements.txt        # Dependencies
├── .env.example           # Environment template
├── .env                   # Your configuration (gitignored)
├── config/
│   └── agent_config.py    # Model client factory
├── agents/
│   ├── coding_assistant.py # AI coding agent
│   └── user_proxy.py      # Task coordination
├── utils/
│   ├── cli_parser.py      # Command line parsing
│   ├── code_extractor.py  # Smart code extraction
│   ├── file_handler.py    # Async file operations
│   └── logger.py          # Logging system
└── output/                # Generated code directory
```

## ⚙️ Configuration

### Environment Variables (.env)

```bash
# Ollama Configuration
OLLAMA_ENDPOINT=http://localhost:11434
OLLAMA_MODEL=Qwen2.5-Coder

# LlamaCpp Configuration
LLAMACPP_MODEL_PATH=/path/to/model.gguf
LLAMACPP_REPO_ID=unsloth/Qwen2.5-Coder-7B-Instruct-GGUF
LLAMACPP_FILENAME=Qwen2.5-Coder-7B-Instruct-Q4_K_M.gguf
LLAMACPP_N_GPU_LAYERS=-1
LLAMACPP_N_CTX=4096

# Default Settings
DEFAULT_OUTPUT_DIR=./output
DEBUG_MODE=false
```

## 🎯 Supported Languages

LazyToCode automatically detects and properly formats code for:

- **Python** (`.py`)
- **JavaScript** (`.js`)
- **TypeScript** (`.ts`)
- **Java** (`.java`)
- **C/C++** (`.c`/`.cpp`)
- **Rust** (`.rs`)
- **Go** (`.go`)
- **HTML** (`.html`)
- **CSS** (`.css`)
- **SQL** (`.sql`)
- **Bash/Shell** (`.sh`)
- **JSON** (`.json`)
- **YAML** (`.yaml`)
- **Markdown** (`.md`)

## 📖 Examples

### Example 1: Simple Script
```bash
python main.py --prompt "Create a Python script to read a CSV file and calculate averages"
```

**Output:** Clean Python script with CSV processing logic

### Example 2: Complex Application
```bash
python main.py --prompt "Build a Flask web application with user authentication" --debug
```

**Output:** 
- `generated_code_TIMESTAMP.py` - Clean Flask application code
- `generated_code_TIMESTAMP_full_response.md` - Complete AI explanation

### Example 3: Multi-language Detection
```bash
python main.py --prompt "Create an HTML page with embedded JavaScript for a calculator"
```

**Output:** Properly formatted HTML file with embedded JavaScript

## 🚀 Advanced Features

### Async Architecture
LazyToCode uses modern async/await patterns for high performance:
- Non-blocking file operations
- Concurrent model API calls
- Efficient resource management

### Error Handling
Comprehensive error handling with graceful fallbacks:
- Model connectivity validation
- File permission checks
- Input validation and sanitization
- User-friendly error messages

### Backup and Versioning
- Automatic file backups when overwriting
- Timestamped file generation
- Safe file writing operations

## 🔧 Development

### Running Tests
```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Run tests
pytest tests/

# Run with coverage
pytest --cov=. tests/
```

## 📝 Logging

LazyToCode provides detailed logging:

- **INFO**: Basic operation status
- **DEBUG**: Detailed execution flow (use `--debug` flag)
- **ERROR**: Error conditions with context

Log files are created in debug mode for troubleshooting.

## 🤝 Model Providers

### Ollama
- **Local model hosting**
- **GPU acceleration support**
- **Wide model selection**
- **Easy setup and management**

### LlamaCpp
- **GGUF format support**
- **CPU and GPU inference**
- **HuggingFace integration**
- **Memory efficient**

## 🔮 Future Enhancements

- [ ] Support for OpenAPI endpoints
- [ ] Interactive conversation mode
- [ ] Code review and quality checking agents
- [ ] Multi-file project generation
- [ ] Template-based code generation
- [ ] Web interface option


## 🙏 Acknowledgments

- **Microsoft Autogen** - Core agent framework
- **Ollama** - Local model hosting
- **LlamaCpp** - Efficient model inference
- **Contributors** - Community support and feedback

---

**LazyToCode** - Making AI code generation simple, clean, and production-ready! 🚀