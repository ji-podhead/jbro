const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
  sendToPython: (message) => ipcRenderer.send('send-to-python', message),
  receivePythonMessage: (callback) => ipcRenderer.on('python-message', (_event, value) => callback(value)),
  // It's good practice to also allow removing listeners if the renderer component unmounts/re-renders
  removePythonMessageListener: (callback) => ipcRenderer.removeListener('python-message', callback)
});
