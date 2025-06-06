document.addEventListener('DOMContentLoaded', () => {
    const themeSettingSelect = document.getElementById('themeSetting');
    const llmModelPrefSettingInput = document.getElementById('llmModelPrefSetting');
    const notificationsEnabledSettingCheckbox = document.getElementById('notificationsEnabledSetting');
    const defaultDownloadPathSettingInput = document.getElementById('defaultDownloadPathSetting');
    const saveSettingsButton = document.getElementById('saveSettingsButton');
    const closeSettingsButton = document.getElementById('closeSettingsButton');
    const statusMessageDiv = document.getElementById('statusMessage');

    function displayStatus(message, isError = false) {
        if (!statusMessageDiv) return;
        statusMessageDiv.textContent = message;
        statusMessageDiv.className = 'status-message'; // Reset classes
        statusMessageDiv.classList.add(isError ? 'status-error' : 'status-success');
        statusMessageDiv.style.display = 'block';
        setTimeout(() => {
            statusMessageDiv.style.display = 'none';
        }, 3000); // Hide after 3 seconds
    }

    // Request all settings when the window loads
    if (window.electronAPI && typeof window.electronAPI.sendToPython === 'function') {
        console.log('Requesting all settings from backend...');
        window.electronAPI.sendToPython('get settings');
    } else {
        console.error('electronAPI.sendToPython is not available.');
        displayStatus('Error: Cannot communicate with backend API.', true);
    }

    // Listen for responses from the main process (via preload)
    if (window.electronAPI && typeof window.electronAPI.receivePythonMessage === 'function') {
        window.electronAPI.receivePythonMessage((rawResponse) => {
            console.log('Settings window received raw data from Python:', rawResponse);
            try {
                const response = JSON.parse(rawResponse);
                if (response.tool === 'echo_message' && response.message) {
                    // The actual message might be a JSON string itself
                    try {
                        const messageContent = JSON.parse(response.message);
                        if (messageContent.type === 'all_settings_response' && messageContent.data) {
                            populateSettingsForm(messageContent.data);
                        } else {
                            // Could be a success/error message from an update
                            console.log('Received echo message:', messageContent);
                            if (typeof messageContent === 'string' && messageContent.startsWith("Setting")) {
                                // Likely a success message from update setting like "Setting 'theme' updated successfully."
                                displayStatus(messageContent);
                            }
                        }
                    } catch (e) {
                        // Message content was not JSON, treat as plain text echo for status
                        console.log('Received plain text echo for status:', response.message);
                        if (typeof response.message === 'string' && (response.message.includes("updated successfully") || response.message.includes("Error:"))) {
                             displayStatus(response.message, response.message.includes("Error:"));
                        }
                    }
                }
            } catch (error) {
                console.error('Error parsing response in settings window:', error, "Raw data:", rawResponse);
                // displayStatus('Error processing response from backend.', true);
            }
        });
    } else {
        console.error('electronAPI.receivePythonMessage is not available in settings window.');
    }

    function populateSettingsForm(settings) {
        console.log('Populating settings form with:', settings);
        if (themeSettingSelect) themeSettingSelect.value = settings.theme || 'light';
        if (llmModelPrefSettingInput) llmModelPrefSettingInput.value = settings.llm_model_preference || '';
        if (notificationsEnabledSettingCheckbox) notificationsEnabledSettingCheckbox.checked = !!settings.notifications_enabled;
        if (defaultDownloadPathSettingInput) defaultDownloadPathSettingInput.value = settings.default_download_path || '';
        displayStatus('Settings loaded successfully.');
    }

    if (saveSettingsButton) {
        saveSettingsButton.addEventListener('click', () => {
            if (!window.electronAPI || typeof window.electronAPI.sendToPython !== 'function') {
                displayStatus('Error: Cannot communicate with backend API to save.', true);
                return;
            }

            const settingsToSave = [
                { key: 'theme', value: themeSettingSelect ? themeSettingSelect.value : 'light' },
                { key: 'llm_model_preference', value: llmModelPrefSettingInput ? llmModelPrefSettingInput.value : '' },
                { key: 'notifications_enabled', value: notificationsEnabledSettingCheckbox ? notificationsEnabledSettingCheckbox.checked : false },
                { key: 'default_download_path', value: defaultDownloadPathSettingInput ? defaultDownloadPathSettingInput.value : '' }
            ];

            let settingsUpdatedCount = 0;
            settingsToSave.forEach(setting => {
                // In a more complex app, you might compare with initially loaded settings
                // to only send changed values. For now, sending all.
                const command = `agent_command: update setting ${JSON.stringify(setting)}`;
                console.log(`Sending update for ${setting.key}`);
                window.electronAPI.sendToPython(command);
                settingsUpdatedCount++;
            });
            if(settingsUpdatedCount > 0) {
                 // The backend sends individual confirmations.
                 // We could have a more consolidated success message after all are sent,
                 // but individual ones via echo are fine for now.
                 // displayStatus("Settings update commands sent. See chat for confirmations.");
            }
        });
    }

    if (closeSettingsButton) {
        closeSettingsButton.addEventListener('click', () => {
            // This tells the main process to close this window
            if (window.electronAPI && typeof window.electronAPI.closeSettingsWindow === 'function') {
                window.electronAPI.closeSettingsWindow();
            } else {
                // Fallback if the specific API isn't exposed, though it should be.
                window.close();
            }
        });
    }
});
```
