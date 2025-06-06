document.addEventListener('DOMContentLoaded', () => {
  // DOM Elements
  const messageInput = document.getElementById('messageInput');
  const sendMessageButton = document.getElementById('sendMessageButton');
  const chatOutput = document.getElementById('chatOutput');
  const viewWorkflowsButton = document.getElementById('viewWorkflowsButton');
  const workflowsDisplayArea = document.getElementById('workflowsDisplayArea');

  // Workflow Form Elements
  const workflowIdInput = document.getElementById('workflowIdInput');
  const workflowNameInput = document.getElementById('workflowNameInput');
  const workflowCronInput = document.getElementById('workflowCronInput');
  const workflowTargetConnectorSelect = document.getElementById('workflowTargetConnectorSelect');
  const workflowActionTypeSelect = document.getElementById('workflowActionTypeSelect');
  const workflowActionParamsDiv = document.getElementById('workflowActionParamsDiv');
  const saveWorkflowButton = document.getElementById('saveWorkflowButton');
  const clearWorkflowFormButton = document.getElementById('clearWorkflowFormButton');

  // --- Action Definitions for Dynamic Form ---
  const actionDefinitions = {
    BROWSER: [
      { value: 'NAVIGATE', text: 'Navigate to URL', params: [{name: 'url', type: 'text', label: 'URL', placeholder: 'https://example.com'}] }
      // Future: { value: 'SCRAPE_ELEMENT', text: 'Scrape Element', params: [{name: 'selector', type: 'text', label: 'CSS Selector'}, {name: 'attribute', type: 'text', label: 'Attribute (optional)'}] }
    ],
    GMAIL: [
      { value: 'LIST_EMAILS', text: 'List Recent Emails', params: [{name: 'count', type: 'number', label: 'Number of emails', defaultValue: 5}] }
      // Future: { value: 'READ_EMAIL', text: 'Read Email', params: [{name: 'message_id', type: 'text', label: 'Email ID'}] },
      // Future: { value: 'SEND_EMAIL', text: 'Send Email', params: [{name: 'to', type: 'text', label: 'Recipient'}, {name: 'subject', type: 'text', label: 'Subject'}, {name: 'body', type: 'textarea', label: 'Body'}]}
    ]
    // Add other connectors like DISCORD, WEBHOOK here
  };

  function appendMessage(text, senderClass, targetOutputElement = chatOutput) {
    if (!targetOutputElement) return;
    const messageElement = document.createElement('div');
    messageElement.classList.add('message', senderClass);
    messageElement.textContent = text;
    // Prepend because chatOutput is flex-direction: column-reverse
    // This makes new messages appear at the bottom and auto-scrolls.
    targetOutputElement.insertBefore(messageElement, targetOutputElement.firstChild);
  }

  function displayWorkflows(workflows) {
    if (!workflowsDisplayArea) return;
    workflowsDisplayArea.innerHTML = ''; // Clear previous content

    if (!workflows || workflows.length === 0) {
      workflowsDisplayArea.textContent = 'No workflows found or defined.';
      return;
    }

    workflows.forEach(wf => {
      const wfElement = document.createElement('div');
      wfElement.classList.add('workflow-item'); // For potential future styling
      wfElement.style.marginBottom = '10px';
      wfElement.style.padding = '10px';
      wfElement.style.border = '1px solid #eee';
      wfElement.style.borderRadius = '4px';

      const title = document.createElement('strong');
      title.textContent = `ID: ${wf.id} - ${wf.name} (${wf.is_enabled ? 'Enabled' : 'Disabled'})`;

      const details = document.createElement('pre');
      details.style.fontSize = '0.9em';
      details.style.backgroundColor = '#fff';
      details.style.padding = '5px';
      details.textContent = JSON.stringify({
        trigger: wf.trigger,
        target_connector: wf.target_connector,
        action: wf.action
      }, null, 2);

      const deleteBtn = document.createElement('button');
      deleteBtn.textContent = 'Delete';
      deleteBtn.classList.add('deleteWorkflowBtn'); // Add class for styling/selection
      deleteBtn.setAttribute('data-id', wf.id);
      deleteBtn.style.backgroundColor = '#dc3545'; // Red color
      deleteBtn.style.color = 'white';
      deleteBtn.style.border = 'none';
      deleteBtn.style.padding = '5px 10px';
      deleteBtn.style.borderRadius = '3px';
      deleteBtn.style.cursor = 'pointer';
      deleteBtn.style.marginLeft = '10px';

      deleteBtn.addEventListener('click', handleDeleteWorkflow);

      // TODO: Add Edit Button here and its handler
      // const editBtn = document.createElement('button');
      // editBtn.textContent = 'Edit';
      // editBtn.setAttribute('data-id', wf.id);
      // editBtn.addEventListener('click', handleEditWorkflow); // Need to implement handleEditWorkflow
      // wfElement.appendChild(editBtn);


      wfElement.appendChild(title);
      wfElement.appendChild(deleteBtn); // Place delete button next to title
      wfElement.appendChild(details); // Details below

      workflowsDisplayArea.appendChild(wfElement);
    });
  }

  function handleDeleteWorkflow(event) {
    const workflowId = event.target.getAttribute('data-id');
    if (confirm(`Are you sure you want to delete workflow ID: ${workflowId}?`)) {
        const command = `agent_command: delete workflow ${JSON.stringify({id: workflowId})}`;
        appendMessage(`You: ${command}`, 'user-message');
        window.electronAPI.sendToPython(command);
        // Refresh list after attempting delete (response will confirm success/failure)
        setTimeout(() => window.electronAPI.sendToPython('list workflows'), 500); // Delay slightly for backend processing
    }
  }

  // --- Workflow Form Logic ---

  function populateTargetConnectors() {
    if (!workflowTargetConnectorSelect) return;
    workflowTargetConnectorSelect.innerHTML = '<option value="">-- Select Connector --</option>';
    Object.keys(actionDefinitions).forEach(connector => {
      const option = document.createElement('option');
      option.value = connector;
      option.textContent = connector;
      workflowTargetConnectorSelect.appendChild(option);
    });
  }

  function populateActionTypes(selectedConnector) {
    if (!workflowActionTypeSelect) return;
    workflowActionTypeSelect.innerHTML = '<option value="">-- Select Action --</option>';
    workflowActionParamsDiv.innerHTML = ''; // Clear params

    if (selectedConnector && actionDefinitions[selectedConnector]) {
      actionDefinitions[selectedConnector].forEach(action => {
        const option = document.createElement('option');
        option.value = action.value;
        option.textContent = action.text;
        workflowActionTypeSelect.appendChild(option);
      });
    }
  }

  function populateActionParams(selectedConnector, selectedActionValue) {
    if (!workflowActionParamsDiv) return;
    workflowActionParamsDiv.innerHTML = ''; // Clear previous params

    if (selectedConnector && selectedActionValue && actionDefinitions[selectedConnector]) {
      const actionDef = actionDefinitions[selectedConnector].find(a => a.value === selectedActionValue);
      if (actionDef && actionDef.params) {
        actionDef.params.forEach(param => {
          const paramLabel = document.createElement('label');
          paramLabel.textContent = `${param.label || param.name}:`;
          paramLabel.htmlFor = `param-${param.name}`;

          const paramInput = document.createElement('input');
          paramInput.type = param.type || 'text';
          paramInput.id = `param-${param.name}`;
          paramInput.name = param.name;
          if(param.placeholder) paramInput.placeholder = param.placeholder;
          if(param.defaultValue) paramInput.value = param.defaultValue;

          workflowActionParamsDiv.appendChild(paramLabel);
          workflowActionParamsDiv.appendChild(paramInput);
        });
      }
    }
  }

  function clearWorkflowForm() {
    if(workflowIdInput) workflowIdInput.value = '';
    if(workflowNameInput) workflowNameInput.value = '';
    if(workflowCronInput) workflowCronInput.value = '';
    if(workflowTargetConnectorSelect) workflowTargetConnectorSelect.value = '';
    if(workflowActionTypeSelect) workflowActionTypeSelect.innerHTML = '<option value="">-- Select Action --</option>';
    if(workflowActionParamsDiv) workflowActionParamsDiv.innerHTML = '';
  }

  // Event Listeners for Form
  if (workflowTargetConnectorSelect) {
    workflowTargetConnectorSelect.addEventListener('change', (e) => {
      populateActionTypes(e.target.value);
      // Trigger change on action type to clear/populate params for the first action if any
      if (workflowActionTypeSelect.options.length > 1) {
        workflowActionTypeSelect.value = workflowActionTypeSelect.options[1].value; // Select first actual action
      } else {
        workflowActionTypeSelect.value = ""; // Or no actions available
      }
      workflowActionTypeSelect.dispatchEvent(new Event('change'));
    });
  }

  if (workflowActionTypeSelect) {
    workflowActionTypeSelect.addEventListener('change', (e) => {
      populateActionParams(workflowTargetConnectorSelect.value, e.target.value);
    });
  }

  if (saveWorkflowButton) {
    saveWorkflowButton.addEventListener('click', () => {
      const id = workflowIdInput.value || null; // null if empty, backend will generate ID for new
      const name = workflowNameInput.value;
      const cronExpression = workflowCronInput.value;
      const targetConnector = workflowTargetConnectorSelect.value;
      const actionType = workflowActionTypeSelect.value;

      if (!name || !cronExpression || !targetConnector || !actionType) {
        appendMessage('Error: Name, Cron, Target, and Action Type are required for workflow.', 'python-message');
        return;
      }

      const params = {};
      if (workflowActionParamsDiv) {
        Array.from(workflowActionParamsDiv.querySelectorAll('input')).forEach(input => {
          if (input.name) {
            // Convert to number if input type is number and value is not empty
            params[input.name] = input.type === 'number' && input.value !== '' ? parseFloat(input.value) : input.value;
          }
        });
      }

      const workflowData = {
        id: id, // Send null for new, or existing id for update
        name: name,
        trigger: { trigger_type: "cron", config: { cron_expression: cronExpression } },
        target_connector: targetConnector,
        action: { action_type: actionType, params: params },
        is_enabled: true // Default to true for new/updated, backend can handle this
      };

      // Determine command based on presence of ID (for update)
      const commandPrefix = id ? "agent_command: update workflow " : "agent_command: create workflow ";
      const fullCommand = commandPrefix + JSON.stringify(workflowData);

      appendMessage(`You: ${commandPrefix.trim()} (see console for data)`, 'user-message');
      console.log("Sending workflow data to backend:", workflowData);
      window.electronAPI.sendToPython(fullCommand);

      clearWorkflowForm();
      // Refresh workflow list after a short delay
      setTimeout(() => {
        if (viewWorkflowsButton) viewWorkflowsButton.click(); // Simulate click to refresh list
      }, 500); // Delay to allow backend to process
    });
  }

  if(clearWorkflowFormButton){
    clearWorkflowFormButton.addEventListener('click', clearWorkflowForm);
  }

  // Initial population of form elements
  populateTargetConnectors();


  // --- Message Handling from Python ---
  if (sendMessageButton) {
    sendMessageButton.addEventListener('click', () => {
      const message = messageInput.value.trim();
      if (message) {
        if (window.electronAPI && typeof window.electronAPI.sendToPython === 'function') {
          appendMessage(`You: ${message}`, 'user-message');
          window.electronAPI.sendToPython(message);
          messageInput.value = ''; // Clear input after sending
        } else {
          console.error('electronAPI.sendToPython is not available.');
          appendMessage('Error: Cannot send message. API not ready.', 'python-message'); // Show error in chat
        }
      }
    });

    // Allow sending with Enter key in input field
    messageInput.addEventListener('keypress', (event) => {
      if (event.key === 'Enter') {
        event.preventDefault(); // Prevent default form submission or newline
        sendMessageButton.click();
      }
    });

  } else {
    console.error('Send Message Button not found.');
  }

  if (window.electronAPI && typeof window.electronAPI.receivePythonMessage === 'function') {
    window.electronAPI.receivePythonMessage((rawMessageFromPython) => {
      console.log('Renderer received raw data from main:', rawMessageFromPython);

      // The message from Python is expected to be a JSON string itself,
      // containing the tool and the actual message.
      // e.g., {"tool": "echo_message", "message": "This is a simple echo"}
      // or {"tool": "echo_message", "message": "{\"type\": \"workflow_list\", \"data\": [...]}"}

      let toolResponse;
      try {
        toolResponse = JSON.parse(rawMessageFromPython);
      } catch (e) {
        console.error('Error parsing JSON from Python:', e, "Raw data:", rawMessageFromPython);
        appendMessage(`Error: Malformed response from Python backend. ${rawMessageFromPython}`, 'python-message');
        return;
      }

      if (toolResponse.tool === 'echo_message') {
        const actualMessageContent = toolResponse.message;
        let parsedWorkflowData = null;
        try {
          // Attempt to parse the message content itself as JSON (for workflow list)
          parsedWorkflowData = JSON.parse(actualMessageContent);
        } catch (e) {
          // Not JSON, or not the specific JSON structure we're looking for; treat as plain text
        }

        if (parsedWorkflowData && parsedWorkflowData.type === 'workflow_list') {
          console.log('Displaying workflow list:', parsedWorkflowData.data);
          displayWorkflows(parsedWorkflowData.data);
          // Optionally, also send a small confirmation to chat output
          appendMessage('Workflows displayed below.', 'python-message');
        } else {
          // If it's not a workflow list, display it as a normal chat message
          appendMessage(`${actualMessageContent.trim()}`, 'python-message');
        }
      } else {
        // Handle other tools if any in the future, or unexpected tool responses
        console.warn(`Received unknown tool response from Python: ${toolResponse.tool}`);
        appendMessage(`Unknown response type from backend: ${rawMessageFromPython.trim()}`, 'python-message');
      }
    });
  } else {
    console.error('electronAPI.receivePythonMessage is not available.');
    appendMessage('Error: Cannot receive messages. API not ready.', 'python-message');
  }

  if (viewWorkflowsButton) {
    viewWorkflowsButton.addEventListener('click', () => {
      if (window.electronAPI && typeof window.electronAPI.sendToPython === 'function') {
        // Display in chat that the command was sent
        appendMessage('You: list workflows', 'user-message');
        window.electronAPI.sendToPython('list workflows');
      } else {
        console.error('electronAPI.sendToPython is not available for viewWorkflowsButton.');
        appendMessage('Error: Cannot send "list workflows" command. API not ready.', 'python-message');
      }
    });
  } else {
    console.error('View Workflows Button not found.');
  }

  const openSettingsButton = document.getElementById('openSettingsButton');
  if (openSettingsButton) {
    openSettingsButton.addEventListener('click', () => {
      if (window.electronAPI && typeof window.electronAPI.openSettingsWindow === 'function') {
        window.electronAPI.openSettingsWindow();
      } else {
        console.error('electronAPI.openSettingsWindow is not available.');
        appendMessage('Error: Could not open settings window. API not available.', 'python-message');
      }
    });
  } else {
    console.error('Open Settings Button not found.');
  }

  const openWriteAssistBtn = document.getElementById('openWriteAssistBtn');
  if (openWriteAssistBtn) {
    openWriteAssistBtn.addEventListener('click', () => {
      if (window.electronAPI && typeof window.electronAPI.openWriteAssistWindow === 'function') {
        window.electronAPI.openWriteAssistWindow();
      } else {
        console.error('electronAPI.openWriteAssistWindow is not available.');
        appendMessage('Error: Could not open Write Assist window. API not available.', 'python-message');
      }
    });
  } else {
    console.error('Open Write Assist Button not found.');
  }

  // Optional: Clean up listener when the window is unloaded
  // window.addEventListener('beforeunload', () => {
  //   if (window.electronAPI && typeof window.electronAPI.removePythonMessageListener === 'function') {
  //      // This assumes your callback for receivePythonMessage is accessible here to remove it.
  //      // For simplicity, this example doesn't store the callback in a way that's easily removable
  //      // without making it global or module-scoped and passed around.
  //      // A more robust app might manage listener callbacks more explicitly.
  //      // window.electronAPI.removePythonMessageListener(theActualCallbackFunction);
  //   }
  // });
});
