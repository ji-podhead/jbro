const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
  // For main window and settings window communication with Python backend
  sendToPython: (message) => ipcRenderer.send('send-to-python', message),
  receivePythonMessage: (callback) => {
    const handler = (_event, value) => callback(value);
    ipcRenderer.on('python-message', handler);
    // Return a cleanup function to remove the listener
    return () => ipcRenderer.removeListener('python-message', handler);
  },
  // removePythonMessageListener: (callback) => ipcRenderer.removeListener('python-message', callback), // Replaced by returning cleanup

  // For main window to open settings
  openSettingsWindow: () => ipcRenderer.send('open-settings-window'),

  // For settings window to request close
  closeSettingsWindow: () => ipcRenderer.send('close-settings-window'),

  // For main window to open Write Assist
  openWriteAssistWindow: () => ipcRenderer.send('open-write-assist-window'),

  // For Write Assist window to request close
  closeWriteAssistWindow: () => ipcRenderer.send('close-write-assist-window')
});
