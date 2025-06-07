const { app, BrowserWindow, ipcMain } = require('electron')
const { spawn } = require('child_process')
const path = require('path')

let pythonProcess = null;
let mainWindow = null; // Keep a reference to the main window
let settingsWindow = null; // Keep a reference to the settings window
let writeAssistWindow = null; // Keep a reference to the Write Assist window

function createSettingsWindow() {
  if (settingsWindow) {
    settingsWindow.focus();
    return;
  }

  settingsWindow = new BrowserWindow({
    width: 500,
    height: 600,
    parent: mainWindow, // Make it a child of the main window
    modal: false, // Set to true to block interaction with mainWindow while settings is open
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js') // Reuse the same preload
    }
  });

  settingsWindow.loadFile(path.join(__dirname, 'settings.html'));

  settingsWindow.on('closed', () => {
    settingsWindow = null;
  });
}

function createWriteAssistWindow() {
  if (writeAssistWindow) {
    writeAssistWindow.focus();
    return;
  }

  writeAssistWindow = new BrowserWindow({
    width: 600,
    height: 700,
    parent: mainWindow, // Optional: can be a top-level window too
    modal: false,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js') // Reuse the same preload
    }
  });

  writeAssistWindow.loadFile(path.join(__dirname, 'write_assist.html'));

  writeAssistWindow.on('closed', () => {
    writeAssistWindow = null;
  });
}

function createWindow () {
  mainWindow = new BrowserWindow({ // Assign to mainWindow
    width: 1000,
    height: 700,
    webPreferences: {
      nodeIntegration: false, // Recommended for security
      contextIsolation: true, // Recommended for security
      preload: path.join(__dirname, 'preload.js')
    }
  })

  mainWindow.loadFile('index.html')

  // Spawn the Python process
  // Adjust 'python' to 'python3' if necessary, depending on system setup
  const scriptPath = path.join(__dirname, '..', 'python-backend', 'main.py');
  pythonProcess = spawn('python', [scriptPath]);

  pythonProcess.stdout.on('data', (data) => {
    const message = data.toString();
    console.log(`Python stdout: ${message}`);

    // Try to send to the focused window, could be main or settings
    let targetWindow = BrowserWindow.getFocusedWindow();

    // If no window is focused, it's tricky. Default to mainWindow,
    // but settings or writeAssist might be open but not focused.
    // A more robust system might use message content or sender info if Python could provide it.
    if (!targetWindow) {
        // Check if any of our specific windows are open, though not focused.
        // This is a simple heuristic.
        if (writeAssistWindow && !writeAssistWindow.isDestroyed() && writeAssistWindow.webContents.getURL().includes('write_assist.html')) {
            // Heuristic: If write assist is open, maybe message is for it?
            // This is not very robust. Better to have specific channels or message routing.
            // For now, if it's a write_assist_response, it's likely for it.
            // But generic messages are hard to route without focus.
            // Defaulting to mainWindow if no focus is safer for generic messages.
        } else if (settingsWindow && !settingsWindow.isDestroyed() && settingsWindow.webContents.getURL().includes('settings.html')) {
            // Similar heuristic for settings
        }
        targetWindow = mainWindow; // Fallback to mainWindow if no specific logic hits
    }


    if (targetWindow && !targetWindow.isDestroyed()) {
      targetWindow.webContents.send('python-message', message);
    } else if (mainWindow && !mainWindow.isDestroyed()) {
      // Fallback to main window if focused window somehow got destroyed before send
      mainWindow.webContents.send('python-message', message);
    }
     else {
      console.error("No valid target window (focused or main) to send Python message to. Message:", message);
    }
  });

  pythonProcess.stderr.on('data', (data) => {
    console.error(`Python stderr: ${data.toString()}`);
  });

  pythonProcess.on('close', (code) => {
    console.log(`Python process exited with code ${code}`);
    pythonProcess = null; // Clear the reference
  });
}

app.whenReady().then(() => {
  createWindow();

  ipcMain.on('send-to-python', (event, arg) => {
    if (pythonProcess && pythonProcess.stdin) {
      // The console.log for the arg is already in the renderer or will be in Python's stderr
      pythonProcess.stdin.write(arg + '\n');
    } else {
      console.error('Python process not running or stdin not available.');
      // Send an error message back to the window that sent the message
      if (event.sender) {
         event.sender.send('python-message', JSON.stringify({
            tool: "echo_message",
            message: "Error from Electron Main: Python process not running or stdin not available."
        }));
      }
    }
  });

  // IPC handler to open the settings window
  ipcMain.on('open-settings-window', () => {
    createSettingsWindow();
  });

  // IPC handler for settings window to request close
  ipcMain.on('close-settings-window', () => {
    if (settingsWindow) {
      settingsWindow.close();
    }
    settingsWindow = null; // Ensure it's cleared after closing
  });

  // IPC handler to open the Write Assist window
  ipcMain.on('open-write-assist-window', () => {
    createWriteAssistWindow();
  });

  // IPC handler for Write Assist window to request close
  ipcMain.on('close-write-assist-window', () => {
    if (writeAssistWindow) {
      writeAssistWindow.close();
    }
    writeAssistWindow = null; // Ensure it's cleared
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
  // Quit Python process if it's running
  if (pythonProcess) {
    console.log('Quitting Python process...');
    pythonProcess.kill();
  }
})

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    createWindow();
  }
})

// Ensure Python process is terminated when app quits
app.on('will-quit', () => {
  if (pythonProcess) {
    console.log('Terminating Python process on app quit...');
    pythonProcess.kill(); // Send SIGTERM
  }
});
