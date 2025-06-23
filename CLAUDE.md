Background
  This project aims to develop multiple AI Agents with specialised tasks. The end goal of this project is to allow a human user to input in a prompt - be it detailed or simple, and the project will attempt to develop a working software codebase based on the prompt. There are two main workflows in this project:
  1. Plan and create.
  2. Test and fix.

  - For the first workflow, "Plan and create", the Planner agent will first take in the user's prompt, craft a detailed implementation plan of what needs to be done, what files to be created, and split them into multiple phases if necessary. If the project is big, each phase should be then passed into the writer agent, then once the writer agent has finished the phase, the Planner agent will check if the phase was implemented as directed before starting the next phase. This feedback look should have a default of 3 to ensure that it does not stay stuck in the same phase forever.
  - For the second workflow, "Test and fix", the Tester agent will create a basic testing framework necessary for the project in a containerized environment. The test should aim to check if the build passes based on the technology stack of the project, and validate application startup and basic functionality. If there are errors, they should be logged down fully and passed to the fixing agent. The fixing agent will then identify the core issues, and draft out a detailed plan to fix the affected files. This plan will then be sent to the writer agent. Once that is done, it will then call for the Tester agent to test the new changes made to see if there are any errors. This feedback loop should have a default of 3 times in total to ensure that the system doesn't run forever. 

  The agents to be created are:
  1. Planner Agent - Main function is to draft out and orchestrate detailed plans for the Writer Agent. If necessary, the plans can be split into smaller phases.
  2. Writer Agent - Main function is to write and edit files based on the plans given by either the Planner Agent or the Fixing Agent. The base agent is the coding_assistant.
  3. Tester Agent - Main function is to test the entire software project, and identify errors and submit the error logs to the fixing agent.
  4. Fixing Agent - Main function is to create a detailed plan of which files have to be fixed based on the errors provided by the tester agent. These plans will then be sent to the Writer agent to be applied.

These arguments must be configurable from the CLI command that can be used to start the project:
1. output_dir -> This should be where the agent will write the code to.
2. model -> This should be the model name to use, defaults to Qwen2.5-Coder
3. model_provider -> This should default to localhost. Acceptable inputs are `ollama` or `llamacpp`.
4. prompt -> This is a required field to start if not using `--help`. This should either accept a text string or a .txt file.
5. debug -> turns on verbose logs

Core rules:
1. Never put hardcoded secrets or values into code directly. If necessary, always use a separate .env or config file.
2. Suggest implementation plans in detail first before making changes to the code.
3. Ask clarifying questions if provided context is not enough to make a strong decision.
