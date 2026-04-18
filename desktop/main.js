const { app, BrowserWindow } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const express = require('express');
const { createProxyMiddleware } = require('http-proxy-middleware');

let mainWindow;
let pythonProcess;
let expressServer;

const distDir = path.join(__dirname, '../frontend/dist');
const frontendPort = 45678;

function startFrontendServer() {
  const server = express();

  // Proxy /api calls to the Python backend so standard fetch calls work properly
  server.use(
    '/api',
    createProxyMiddleware({
      target: 'http://localhost:5000/api',
      changeOrigin: true,
    })
  );

  // Serve the frontend built static files
  server.use(express.static(distDir));

  // SPA Route parsing
  server.get('*', (req, res) => {
    res.sendFile(path.join(distDir, 'index.html'));
  });

  expressServer = server.listen(frontendPort, () => {
    console.log(`Frontend server running internally on http://localhost:${frontendPort}`);
  });
}

function startPythonBackend() {
  // Use system Python with PYTHONPATH set to project root
  const pythonExe = 'python';
  const backendScript = path.join(__dirname, '../scripts/run_backend.py');
  const projectRoot = path.join(__dirname, '..');

  console.log('Spawning offline Python backend process...');
  console.log(`Project root: ${projectRoot}`);
  
  pythonProcess = spawn(pythonExe, [backendScript], {
    cwd: projectRoot,
    env: { ...process.env, PYTHONPATH: projectRoot }
  });

  pythonProcess.stdout.on('data', (data) => console.log(`Python: ${data.toString()}`));
  pythonProcess.stderr.on('data', (data) => console.error(`Python Error: ${data.toString()}`));
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    title: "Log Sentinel Desktop",
    webPreferences: {
      nodeIntegration: true,
      contextIsolation: false
    },
    autoHideMenuBar: true
  });

  // Launch the Electron window using our local web server
  mainWindow.loadURL(`http://localhost:${frontendPort}/`);

  mainWindow.on('closed', function () {
    mainWindow = null;
  });
}

app.on('ready', () => {
  // 1: Fire up the core AI Backend automatically
  startPythonBackend();
  // 2: Serve the frontend offline statically
  startFrontendServer();
  // 3: Wait 2.5 seconds to ensure backend port binds before opening client window
  setTimeout(createWindow, 2500);
});

app.on('window-all-closed', function () {
  if (process.platform !== 'darwin') app.quit();
});

app.on('will-quit', () => {
  // Ensure we do not leak the python background thread!
  if (pythonProcess) pythonProcess.kill();
  if (expressServer) expressServer.close();
});
