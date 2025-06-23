# LazyToCode Multi-Agent System Implementation Guide (Refined)

## 🎯 Refined Requirements Summary

- **Container Runtime**: Docker only
- **Testing Scope**: Build validation only (for now)
- **Language Priority**: Python first, others later
- **Resource Limits**: 4GB memory maximum
- **State Persistence**: Future feature (not implemented now)
- **Error Analysis**: File-level detail initially

## 📋 Refined Implementation Plan

### Phase 1: Multi-Agent Foundation & Communication (Week 1)

#### Phase 1.1: Core Agent Framework
**Files to create/modify:**
- `agents/base_agent.py` - Common agent functionality
- `utils/agent_messages.py` - Message types for inter-agent communication
- `orchestrator.py` - Main workflow coordinator
- `utils/workflow_state.py` - Session-based state management

**Key Features:**
```python
# Agent Communication Protocol
class AgentMessage:
    message_type: str  # "plan_request", "write_request", "test_request", "fix_request"
    sender: str
    recipient: str
    payload: Dict
    phase_id: str
    timestamp: datetime

# Base Agent Class
class BaseAgent(RoutedAgent):
    async def send_message(self, recipient: str, message: AgentMessage)
    async def handle_message(self, message: AgentMessage)
    def get_status(self) -> AgentStatus
```

#### Phase 1.2: Planner Agent (Python-focused)
**File:** `agents/planner_agent.py`

**Core Responsibilities:**
- Analyze Python project requirements from prompt
- Break down into logical phases (setup, core logic, testing, packaging)
- Generate detailed implementation plans
- Validate phase completion (3-attempt limit)

**Python Project Analysis:**
```python
class PythonProjectAnalyzer:
    def detect_project_type(self, prompt: str) -> ProjectType:
        # CLI tool, web app (Flask/FastAPI), library, script, etc.
    
    def generate_file_structure(self, project_type: ProjectType) -> FileStructure:
        # requirements.txt, main.py, setup.py, etc.
    
    def create_phase_plan(self, structure: FileStructure) -> List[Phase]:
        # Phase 1: Setup files, Phase 2: Core implementation, etc.
```

**Testing Checkpoint 1:** Basic agent communication + Python project planning

### Phase 2: Enhanced Writer & Docker Testing (Week 2)

#### Phase 2.1: Writer Agent Enhancement
**File:** Refactor `agents/coding_assistant.py` → `agents/writer_agent.py`

**Enhanced Capabilities:**
- Multi-file project generation
- Python-specific code patterns and best practices
- Requirements.txt generation
- Basic Python project structure (src/, tests/, setup.py)

```python
class WriterAgent(BaseAgent):
    async def write_python_project(self, plan: ProjectPlan) -> ProjectFiles:
        # Generate multiple files based on plan
    
    def generate_requirements_file(self, dependencies: List[str]) -> str:
        # Create requirements.txt with pinned versions
    
    def create_setup_py(self, project_info: ProjectInfo) -> str:
        # Basic setup.py for Python packages
```

#### Phase 2.2: Docker Testing Infrastructure
**Files to create:**
- `agents/tester_agent.py`
- `utils/docker_manager.py`
- `templates/python_dockerfile.template`

**Docker Testing Setup:**
```python
class DockerManager:
    memory_limit: str = "4g"
    
    async def create_python_test_container(self, project_path: Path) -> str:
        # Create Python 3.11 container with project mounted
    
    async def run_build_validation(self, container_id: str) -> TestResult:
        # pip install -r requirements.txt
        # python -m py_compile *.py (syntax check)
        # python -m pytest --collect-only (if tests exist)
    
    async def cleanup_container(self, container_id: str):
        # Remove container and cleanup
```

**Python Build Validation:**
1. Syntax validation (`python -m py_compile`)
2. Dependencies installation (`pip install -r requirements.txt`)
3. Import validation (attempt to import main modules)
4. Basic execution test (if `if __name__ == "__main__"` present)

**Testing Checkpoint 2:** End-to-end Python project generation + Docker testing

### Phase 3: Error Analysis & Fixing Agent (Week 3)

#### Phase 3.1: Fixing Agent Implementation
**File:** `agents/fixing_agent.py`

**File-Level Error Analysis:**
```python
class PythonErrorAnalyzer:
    def analyze_syntax_errors(self, error_log: str) -> List[FileError]:
        # Parse Python syntax errors, identify problematic files
    
    def analyze_import_errors(self, error_log: str) -> List[FileError]:
        # Missing modules, circular imports, etc.
    
    def analyze_dependency_errors(self, error_log: str) -> List[FileError]:
        # Missing packages in requirements.txt
    
    def generate_fix_plan(self, errors: List[FileError]) -> FixPlan:
        # File-level fixes: update imports, add dependencies, fix syntax
```

**Fix Plan Structure:**
```python
class FixPlan:
    phase_id: str
    files_to_modify: List[str]
    dependencies_to_add: List[str]
    files_to_create: List[str]
    fix_description: str
    estimated_complexity: int  # 1-5 scale
```

#### Phase 3.2: Workflow Integration
**File:** `orchestrator.py` (enhanced)

**3-Attempt Retry Logic:**
```python
class WorkflowOrchestrator:
    max_attempts: int = 3
    
    async def execute_phase(self, phase: Phase) -> PhaseResult:
        for attempt in range(self.max_attempts):
            # Plan → Write → Test → Fix (if needed)
            if test_result.success:
                return PhaseResult.SUCCESS
            
            if attempt < self.max_attempts - 1:
                # Generate fix plan and retry
                fix_plan = await self.fixing_agent.analyze_errors(test_result.errors)
                await self.writer_agent.apply_fixes(fix_plan)
        
        return PhaseResult.FAILED
```

**Testing Checkpoint 3:** Complete test-and-fix cycle with Python projects

### Phase 4: Integration & Polish (Week 4)

#### Phase 4.1: CLI Integration
**File:** `main.py` (enhanced)

**New CLI Arguments:**
```bash
python main.py --prompt "Build a Python CLI tool" \
  --workflow full \           # plan-create, test-fix, or full
  --max-phases 5 \           # limit number of phases
  --docker-memory 4g         # Docker memory limit
```

#### Phase 4.2: Error Handling & Logging
- Comprehensive error handling for Docker failures
- Detailed logging of agent interactions
- Progress reporting during long-running operations
- Graceful handling of Docker daemon issues

**Testing Checkpoint 4:** Full system integration with Python projects

## 🐍 Python-Specific Features

### Project Type Detection
```python
PYTHON_PROJECT_PATTERNS = {
    "cli_tool": ["command line", "cli", "terminal", "argparse"],
    "web_app": ["flask", "fastapi", "django", "web", "api"],
    "data_script": ["pandas", "numpy", "analysis", "csv", "data"],
    "library": ["package", "library", "module", "pip install"],
    "script": ["script", "automation", "simple"]
}
```

### Python Testing Framework
```dockerfile
# Python test container template
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
RUN python -m py_compile *.py
CMD ["python", "-c", "import sys; print('Build validation passed')"]
```

## 📊 Success Metrics (Refined)

### Phase 1 Success Criteria
- [ ] Agent communication framework functional
- [ ] Python project planning working
- [ ] Phase decomposition for Python projects

### Phase 2 Success Criteria
- [ ] Multi-file Python project generation
- [ ] Docker build validation for Python
- [ ] Requirements.txt generation and validation

### Phase 3 Success Criteria
- [ ] Python error analysis (syntax, imports, dependencies)
- [ ] File-level fix plan generation
- [ ] 3-attempt retry logic working

### Phase 4 Success Criteria
- [ ] Complete CLI integration
- [ ] Robust error handling
- [ ] Python project end-to-end workflow

## 🧪 Testing Strategy (Python-focused)

### Test Cases
1. **Simple Python Script**: Hello world, basic calculations
2. **CLI Tool**: argparse-based command line utility
3. **Web API**: FastAPI/Flask simple REST API
4. **Data Processing**: pandas/numpy data analysis script
5. **Package**: Installable Python package with setup.py

### Error Scenarios to Test
1. Syntax errors in generated code
2. Missing dependencies in requirements.txt
3. Import errors (circular imports, missing modules)
4. Docker container failures
5. Memory limit exceeded scenarios

This refined plan focuses on Python-first implementation with Docker-only testing, making it more achievable while establishing a solid foundation for future language support.

## 🚀 Implementation Steps Summary

### Phase 1: Foundation (Week 1)
1. Create base agent communication framework
2. Implement Planner Agent with Python project analysis
3. Set up basic workflow orchestration
4. Test agent-to-agent communication

### Phase 2: Core Functionality (Week 2)
1. Enhance Writer Agent for multi-file Python projects
2. Implement Docker testing infrastructure
3. Create Tester Agent for Python build validation
4. Test end-to-end project generation and validation

### Phase 3: Error Handling (Week 3)
1. Implement Fixing Agent with file-level error analysis
2. Add 3-attempt retry logic to workflow
3. Integrate error analysis with Writer Agent fixes
4. Test complete error recovery workflow

### Phase 4: Integration & Polish (Week 4)
1. Update CLI with new multi-agent arguments
2. Add comprehensive error handling and logging
3. Optimize performance and resource usage
4. Complete system integration testing

Each phase builds upon the previous one, ensuring a solid foundation while progressively adding complexity. The focus on Python initially allows for thorough testing and refinement before expanding to other languages.