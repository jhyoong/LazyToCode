Background
  This project aims to develop multiple AI Agents with specialised tasks. The end goal of this project is to allow a human user to input in a prompt - be it detailed or simple, and the project will attempt to develop a working software codebase based on the prompt. There are two main workflows in this project:
  1. Plan and create.
  2. Test and fix.

  - For the first workflow, "Plan and create", the Planner agent will first take in the user's prompt, craft a detailed implementation plan of what needs to be done, what files to be created, and split them into multiple phases if necessary. If the project is big, each phase should be then passed into the writer agent, then once the writer agent has finished the phase, the Reviewer agent will check if the phase was implemented as directed before starting the next phase. This feedback look should have a default of 3 attempts to ensure that it does not stay stuck in the same phase forever.
  - For the second workflow, "Test and fix", the Tester agent will create a basic testing framework necessary for the project in a containerized environment. The test should aim to check if the build passes based on the technology stack of the project, and validate application startup and basic functionality. If there are errors, they should be logged down fully and passed to the fixing agent. The fixing agent will then identify the core issues, and draft out a detailed plan to fix the affected files. This plan will then be sent to the writer agent. Once that is done, it will then call for the Tester agent to test the new changes made to see if there are any errors. This feedback loop should have a default of 3 times in total to ensure that the system doesn't run forever. 

  The agents already created are:
  1. Planner Agent - Main function is to draft out and orchestrate detailed plans for the Writer Agent. If necessary, the plans can be split into smaller phases.
  2. Writer Agent - Main function is to write and edit files based on the plans given by either the Planner Agent or the Fixing Agent. The base agent is the coding_assistant.
  3. Reviewer Agent - Main function is to check if the Writer agent has successfully created the files as detailed in the plans created by the Planner agent. The check passes only if all success criteria has been met. If failed, it sends specific feedback to the writer agent to continue working on the phase to fix the issues.
  The agents to be created are:
  4. Tester Agent - Main function is to test the entire software project, and identify errors and submit the error logs to the fixing agent.
  5. Fixing Agent - Main function is to create a detailed plan of which files have to be fixed based on the errors provided by the tester agent. These plans will then be sent to the Writer agent to be applied.

Core rules:
1. Never put hardcoded secrets or values into code directly. If necessary, always use a separate .env or config file.
2. Suggest implementation plans in detail first before making changes to the code.
3. Ask clarifying questions if provided context is not enough to make a strong, informed, and confident decision.
4. Do not use emojis in the response unless explicity asked to.

What has been completed:
1. Plan and create workflow.
2. Planner, Writer, Reviewer agents.
3. Interactive mode for Planner agent with plan approval, modification, and rejection capabilities.
4. Refer to README.md for more project information.

To Do:
- Enable OpenAI API as model provider alternative
- Code cleanup
- Create Tester and Fixing agents.
- Create test and fix workflow.
- Fine-tune agents and workflows 
- skip-review flag. This will enable a simple hardcoded filecheck based on plan.json, and not call the reviewer agent.