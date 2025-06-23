This project is about using AI Agents to write code.

The first task is to setup a basic coding agent that can take in prompts and write simple code.

This project should use Microsoft's Autogen library as the agent control. The default model provider is Ollama. Details like endpoints and configurations should be set in a `.env` file. 

These arguments should be configurable from the CLI command that can be used to start the project:
1. output_dir -> This should be where the agent will write the code to.
2. model -> This should be the model name to use, defaults to Qwen2.5-Coder
3. model_provider -> This should default to localhost. Acceptable inputs are `ollama` or `llamacpp`.
4. prompt -> This is a required field to start if not using `--help`. This should either accept a text string or a .txt file.
5. debug -> turns on verbose logs

Core rules:
1. Never put hardcoded secrets or values into code directly. If necessary, always use a separate .env or config file.
2. Suggest implementation plans in detail first before making changes to the code.
3. Ask clarifying questions if provided context is not enough to make a strong decision.

References:
1. https://microsoft.github.io/autogen/stable//reference/python/autogen_ext.models.ollama.html#module-autogen_ext.models.ollama
2. https://microsoft.github.io/autogen/stable//reference/python/autogen_ext.models.llama_cpp.html
3. https://microsoft.github.io/autogen/stable//user-guide/core-user-guide/installation.html
4. https://github.com/microsoft/autogen
