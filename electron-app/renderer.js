document.addEventListener('DOMContentLoaded', () => {
  const messageInput = document.getElementById('messageInput');
  const sendMessageButton = document.getElementById('sendMessageButton');
  const pythonResponseDiv = document.getElementById('pythonResponse');

  if (sendMessageButton) {
    sendMessageButton.addEventListener('click', () => {
      const message = messageInput.value;
      if (message && window.electronAPI && typeof window.electronAPI.sendToPython === 'function') {
        window.electronAPI.sendToPython(message);
        messageInput.value = ''; // Clear input after sending
      } else {
        console.error('electronAPI.sendToPython is not available or message is empty.');
        pythonResponseDiv.textContent = 'Error: Cannot send message. API not ready or message empty.';
      }
    });
  } else {
    console.error('Send Message Button not found.');
  }

  if (window.electronAPI && typeof window.electronAPI.receivePythonMessage === 'function') {
    window.electronAPI.receivePythonMessage((message) => {
      console.log('Renderer received from main:', message);
      // Append new message, ensuring proper formatting if multiple lines arrive
      const currentText = pythonResponseDiv.textContent;
      pythonResponseDiv.textContent = (currentText ? currentText + '\n' : '') + message.trim();
    });
  } else {
    console.error('electronAPI.receivePythonMessage is not available.');
    if(pythonResponseDiv) {
        pythonResponseDiv.textContent = 'Error: Cannot receive messages. API not ready.';
    }
  }

  // Optional: Clean up listener when the window is unloaded
  // (though for a simple app like this, it might not be strictly necessary)
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
