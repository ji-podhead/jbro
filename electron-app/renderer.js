document.addEventListener('DOMContentLoaded', () => {
  const messageInput = document.getElementById('messageInput');
  const sendMessageButton = document.getElementById('sendMessageButton');
  const chatOutput = document.getElementById('chatOutput');
  const viewWorkflowsButton = document.getElementById('viewWorkflowsButton');
  const workflowsDisplayArea = document.getElementById('workflowsDisplayArea');

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
      wfElement.style.marginBottom = '10px';
      wfElement.style.padding = '5px';
      wfElement.style.border = '1px solid #eee';

      const title = document.createElement('strong');
      title.textContent = `ID: ${wf.id} - ${wf.name} (${wf.is_enabled ? 'Enabled' : 'Disabled'})`;
      wfElement.appendChild(title);

      const pre = document.createElement('pre');
      pre.textContent = JSON.stringify({
        trigger: wf.trigger,
        target_connector: wf.target_connector,
        action: wf.action
      }, null, 2);
      wfElement.appendChild(pre);

      workflowsDisplayArea.appendChild(wfElement);
    });
  }

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
