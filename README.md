# Agentic Browser

## Overview

Agentic Browser is an AI-powered desktop application designed to provide intelligent browsing capabilities, automation through workflows, and a conversational interface for interacting with web services and local tasks. The project combines an Electron-based frontend with a Python backend, enabling a rich user experience and powerful backend processing.

## Current Features

*   **AI Chat Interface:**
    *   Built with Electron and powered by a Python backend.
    *   Allows users to issue commands and receive feedback in a conversational manner.
*   **Browser Control:**
    *   Uses Playwright for robust browser automation.
    *   Supports navigation to URLs via chat commands (e.g., "navigate to https://example.com").
*   **Gmail Integration:**
    *   Allows listing recent unread emails through chat commands (e.g., "list emails").
    *   Requires OAuth2 setup (`gmail_credentials.json`).
*   **Workflow Engine:**
    *   **Creation & Management:**
        *   Workflows can be defined via a dedicated UI within the application.
        *   Supports creating workflows through natural language chat commands (e.g., "create workflow My Task to navigate to https://site.com on schedule 0 10 * * *").
        *   Workflows can be listed and deleted through the UI and chat commands.
    *   **Trigger Mechanisms:**
        *   **Cron-based Scheduling:** Workflows can be scheduled to run at specific times/intervals using cron expressions (powered by APScheduler).
        *   **Semantic Condition Triggers (Planned):** Pydantic models are defined for semantic condition triggers (e.g., "trigger if X happens"). The execution logic for these is pending.
    *   **Actions:**
        *   Currently supports browser navigation and listing Gmail emails as workflow actions.
    *   **Persistence:** Workflows are saved in a JSON file (`python-backend/workflows.json`) and loaded on startup.
*   **Modular Design:** Clear separation between frontend (`electron-app`) and backend (`python-backend`) logic.

## Technologies Used

*   **Frontend:** Electron, HTML, CSS, JavaScript.
*   **Backend:** Python 3.x.
*   **Browser Automation:** Playwright.
*   **Scheduling:** APScheduler.
*   **Data Validation/Modeling (Python):** Pydantic.
*   **Inter-Process Communication (Electron <-> Python):** Standard I/O (stdin/stdout) pipes.
*   **Google API Client Library:** For Gmail integration.

## Project Structure

```
.
├── electron-app/         # Frontend Electron application
│   ├── main.js           # Electron main process
│   ├── renderer.js       # Electron renderer process logic
│   ├── preload.js        # Electron preload script
│   ├── index.html        # Main HTML file for the UI
│   └── package.json      # Node.js dependencies and scripts
├── python-backend/       # Backend Python logic
│   ├── main.py           # Main script for the Python backend, handles IPC
│   ├── agent.py          # Agent logic for interpreting commands
│   ├── workflow_manager.py # Manages CRUD for workflows
│   ├── workflow_models.py  # Pydantic models for workflows
│   ├── scheduler.py      # APScheduler integration for cron jobs
│   ├── gmail_integration.py # Gmail API interaction logic
│   └── requirements.txt  # Python dependencies
└── README.md             # This file
```

## Setup Instructions

### Prerequisites

*   Python 3.7+
*   Node.js and npm (latest LTS recommended)
*   Git (for cloning, if applicable)

### Python Backend

1.  Navigate to the Python backend directory:
    ```bash
    cd python-backend
    ```
2.  Install required Python packages:
    ```bash
    pip install -r requirements.txt
    ```
3.  Install Playwright browsers (if not already installed or if you encounter issues):
    ```bash
    playwright install
    ```
    (You might need to use `python -m playwright install` or `/path/to/your/python -m playwright install` depending on your environment).
4.  **Gmail Integration (Optional):**
    *   To use Gmail features, you need to enable the Gmail API in your Google Cloud Console and obtain OAuth 2.0 credentials.
    *   Download your credentials as `credentials.json`.
    *   Rename and place this file as `gmail_credentials.json` inside the `python-backend/` directory.
    *   The first time you run a command that uses Gmail (e.g., "list emails"), the application may attempt to open a browser window for you to authorize access. A `gmail_token.json` file will be created to store your authorization token.

### Electron Frontend

1.  Navigate to the Electron frontend directory:
    ```bash
    cd electron-app
    ```
    (If you are in `python-backend`, use `cd ../electron-app`)
2.  Install Node.js dependencies:
    ```bash
    npm install
    ```

## How to Run

1.  **Start the Python Backend:**
    Open a terminal and navigate to the project root directory. Run:
    ```bash
    python python-backend/main.py
    ```
    Alternatively, from within the `python-backend` directory:
    ```bash
    python main.py
    ```
    You should see log messages indicating the backend has started.

2.  **Start the Electron Frontend:**
    Open another terminal, navigate to the `electron-app` directory, and run:
    ```bash
    npm start
    ```
    This will launch the Electron application window.

## (Optional) Future Work/Roadmap

*   **Full Semantic Condition Trigger Execution:** Implement the logic to evaluate semantic conditions and trigger workflows.
*   **Write Assist Feature:** Integrate LLM capabilities for content generation or assistance within the browser context.
*   **Enhanced Settings UI:** Develop a more comprehensive UI for managing application settings, API keys, etc.
*   **More Connectors & Actions:** Expand with more target connectors (e.g., Discord, Slack, Webhooks) and corresponding actions.
*   **MCPs (Modular Capability Packages):** Develop a plugin-like architecture for easily adding new tools and capabilities.
*   **Refined Error Handling and User Feedback:** Improve how errors are communicated to the user.
*   **Packaging and Distribution:** Create distributable versions of the application for different operating systems.

---
*This README provides a snapshot of the project's current state and planned development.*