document.addEventListener('DOMContentLoaded', () => {
    const promptInput = document.getElementById('writeAssistPromptInput');
    const generateButton = document.getElementById('generateTextButton');
    const outputArea = document.getElementById('writeAssistOutputArea');
    const copyButton = document.getElementById('copyToClipboardButton');
    const copyAndCloseButton = document.getElementById('copyAndCloseButton');
    const statusDiv = document.getElementById('writeAssistStatus');

    function showStatus(message, type = 'info') { // type can be 'info', 'success', 'error'
        if (!statusDiv) return;
        statusDiv.textContent = message;
        statusDiv.className = 'status-message'; // Reset classes
        statusDiv.classList.add(`status-${type}`);
        statusDiv.style.display = 'block';

        // Automatically hide info/success messages after a delay
        if (type === 'info' || type === 'success') {
            setTimeout(() => {
                if (statusDiv.textContent === message) { // Only hide if message hasn't changed
                    statusDiv.style.display = 'none';
                }
            }, 3000);
        }
    }

    if (generateButton) {
        generateButton.addEventListener('click', () => {
            const promptText = promptInput.value.trim();
            if (!promptText) {
                showStatus('Please enter a prompt or some text first.', 'error');
                return;
            }
            if (window.electronAPI && typeof window.electronAPI.sendToPython === 'function') {
                outputArea.value = ''; // Clear previous output
                showStatus('Generating text...', 'info');
                // Using a more structured command format for clarity with agent
                const commandPayload = {
                    type: "generate_text", // Specific type for write assist
                    prompt: promptText
                };
                // The agent will decide what tool this corresponds to.
                // For now, we'll send it as part of an "agent_command"
                window.electronAPI.sendToPython(`agent_command: assist_write_generate ${JSON.stringify(commandPayload)}`);
            } else {
                showStatus('Error: Backend communication API is not available.', 'error');
                console.error('electronAPI.sendToPython is not available.');
            }
        });
    }

    if (copyButton) {
        copyButton.addEventListener('click', () => {
            if (outputArea.value) {
                navigator.clipboard.writeText(outputArea.value)
                    .then(() => showStatus('Text copied to clipboard!', 'success'))
                    .catch(err => {
                        showStatus('Failed to copy text.', 'error');
                        console.error('Error copying text: ', err);
                    });
            } else {
                showStatus('Nothing to copy.', 'info');
            }
        });
    }

    if (copyAndCloseButton) {
        copyAndCloseButton.addEventListener('click', () => {
            let copied = false;
            if (outputArea.value) {
                navigator.clipboard.writeText(outputArea.value)
                    .then(() => {
                        copied = true;
                        showStatus('Text copied! Closing window...', 'success');
                    })
                    .catch(err => {
                        showStatus('Failed to copy text. Window will not close.', 'error');
                        console.error('Error copying text: ', err);
                    })
                    .finally(() => {
                        if (copied && window.electronAPI && typeof window.electronAPI.closeWriteAssistWindow === 'function') {
                            setTimeout(() => window.electronAPI.closeWriteAssistWindow(), 1000); // Delay for status message
                        } else if (copied) {
                             console.error('electronAPI.closeWriteAssistWindow is not available to close window.');
                        }
                    });
            } else {
                showStatus('Nothing to copy. Closing window...', 'info');
                 if (window.electronAPI && typeof window.electronAPI.closeWriteAssistWindow === 'function') {
                    setTimeout(() => window.electronAPI.closeWriteAssistWindow(), 1000);
                }
            }
        });
    }

    // Handle responses from Python backend
    if (window.electronAPI && typeof window.electronAPI.receivePythonMessage === 'function') {
        window.electronAPI.receivePythonMessage((rawResponse) => {
            console.log('Write Assist window received raw data from Python:', rawResponse);
            try {
                const response = JSON.parse(rawResponse);
                // Expecting Python to send back an echo_message with the generated text
                if (response.tool === 'echo_message' && response.message) {
                    // Further, we expect the message to be JSON for write_assist results
                    try {
                        const messageContent = JSON.parse(response.message);
                        if (messageContent.type === 'write_assist_response' && messageContent.text) {
                            outputArea.value = messageContent.text;
                            showStatus('Text generated successfully.', 'success');
                        } else if (messageContent.type === 'write_assist_error') {
                            showStatus(`Error from AI: ${messageContent.error}`, 'error');
                        } else {
                            // Generic echo message, not specifically for write assist output
                            // This might be a confirmation or an unrelated error from backend.
                            // For now, just log it, as this window is specific.
                            console.log("Received generic echo message:", messageContent);
                            // showStatus(typeof messageContent === 'string' ? messageContent : JSON.stringify(messageContent), 'info');
                        }
                    } catch (e) {
                        // Message content was not JSON, treat as plain text echo, potentially an error or simple status
                        console.log('Write Assist received non-JSON echo message content:', response.message);
                        // If it's a simple string and seems like a status, display it.
                        // This might be useful for "Setting X updated" if it came here by mistake.
                        // However, this window should ideally only get write_assist responses or critical errors.
                        // For now, we'll assume any direct string in echo_message might be a status.
                        // showStatus(response.message, 'info');
                    }
                }
            } catch (error) {
                console.error('Error parsing response in Write Assist window:', error, "Raw data:", rawResponse);
                // displayStatus('Error processing response from backend.', true);
            }
        });
    } else {
        console.error('electronAPI.receivePythonMessage is not available in Write Assist window.');
    }
});
```
