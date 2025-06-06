const { app, BrowserWindow, ipcMain } = require('electron')
const { spawn } = require('child_process')
const path = require('path')

let pythonProcess = null;
let mainWindow = null; // Keep a reference to the main window

function createWindow () {
  mainWindow = new BrowserWindow({ // Assign to mainWindow
    width: 800,
    height: 600,
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
    if (mainWindow) {
      mainWindow.webContents.send('python-message', message);
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
      console.log(`Sending to Python: ${arg}`);
      pythonProcess.stdin.write(arg + '\n');
    } else {
      console.error('Python process not running or stdin not available.');
      // Optionally, send an error back to renderer
      // event.reply('python-error', 'Python process not available');
    }
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
