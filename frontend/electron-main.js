import { app, BrowserWindow, ipcMain } from 'electron'
import { spawn } from 'child_process'
import path from 'path'
import { fileURLToPath } from 'url'
import fs from 'fs'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const isDev = process.env.NODE_ENV === 'development' || !app.isPackaged

let mainWindow = null
let pythonProcess = null

function getBackendPath() {
  if (isDev) {
    return path.join(__dirname, '..', 'backend')
  } else {
    return path.join(process.resourcesPath, 'backend')
  }
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 900,
    height: 700,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: 'C:\\Users\\Артем\\Desktop\\HandTracking\\frontend\\preload.js'
    },
    title: 'Hand Tracking Control'
  })

  if (isDev) {
    mainWindow.loadURL('http://localhost:5173')
    mainWindow.webContents.openDevTools()
  } else {
    mainWindow.loadFile(path.join(__dirname, 'dist', 'index.html'))
  }
}

function startPythonScript() {
  if (pythonProcess) return

  const backendPath = getBackendPath()
  const scriptPath = path.join(backendPath, 'app.py')

  if (!fs.existsSync(scriptPath)) {
    console.error('app.py not found at:', scriptPath)
    mainWindow?.webContents.send('python-error', 'app.py not found')
    return
  }

  pythonProcess = spawn('python', [scriptPath], {
    cwd: backendPath,
    stdio: ['pipe', 'pipe', 'pipe']
  })

  pythonProcess.stdout.on('data', (data) => {
    const log = data.toString()
    console.log(`Python: ${log}`)
    mainWindow?.webContents.send('python-log', log)
  })

  pythonProcess.stderr.on('data', (data) => {
    const error = data.toString()
    console.error(`Python error: ${error}`)
    mainWindow?.webContents.send('python-log', `ERROR: ${error}`)
  })

  pythonProcess.on('close', () => {
    pythonProcess = null
    mainWindow?.webContents.send('python-status', 'stopped')
  })

  mainWindow?.webContents.send('python-status', 'running')
  mainWindow?.webContents.send('python-log', 'Python process started')
}

function stopPythonScript() {
  if (pythonProcess) {
    pythonProcess.kill()
    pythonProcess = null
    mainWindow?.webContents.send('python-status', 'stopped')
  }
}

// IPC handlers
ipcMain.handle('start-python', () => {
  startPythonScript()
  return true
})

ipcMain.handle('stop-python', () => {
  stopPythonScript()
  return true
})

ipcMain.handle('get-python-status', () => {
  return pythonProcess !== null
})

app.whenReady().then(createWindow)

app.on('window-all-closed', () => {
  stopPythonScript()
  if (process.platform !== 'darwin') app.quit()
})