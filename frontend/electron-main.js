import { app, BrowserWindow, ipcMain } from 'electron'
import { spawn } from 'child_process'
import path from 'path'
import { fileURLToPath } from 'url'
import fs from 'fs'

const __dirname = path.dirname(fileURLToPath(import.meta.url))

// Определяем режим разработки
const isDev = process.env.NODE_ENV === 'development' || !app.isPackaged

let mainWindow = null
let pythonProcess = null

// Функция для получения пути к backend
function getBackendPath() {
  if (isDev) {
    // В режиме разработки - backend находится на уровень выше
    return path.join(__dirname, '..', 'backend')
  } else {
    // В собранном приложении
    return path.join(process.resourcesPath, 'backend')
  }
}

// Функция для получения пути к index.html
function getIndexPath() {
  if (isDev) {
    return 'http://localhost:5173'
  } else {
    return path.join(__dirname, 'dist', 'index.html')
  }
}

// Создание окна приложения
function createWindow() {
  mainWindow = new BrowserWindow({
    width: 900,
    height: 700,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js')
    },
    icon: path.join(__dirname, 'assets', 'icon.ico'),
    title: 'Hand Tracking Control'
  })

  const indexPath = getIndexPath()
  
  if (isDev) {
    mainWindow.loadURL(indexPath)
    mainWindow.webContents.openDevTools()
  } else {
    mainWindow.loadFile(indexPath)
  }

  mainWindow.on('closed', () => {
    mainWindow = null
  })
}

// Запуск Python скрипта
function startPythonScript() {
  if (pythonProcess) {
    console.log('Python process already running')
    return
  }

  const backendPath = getBackendPath()
  const scriptPath = path.join(backendPath, 'app.py')
  
  console.log('Starting Python from:', scriptPath)
  
  // Проверяем существование файла
  if (!fs.existsSync(scriptPath)) {
    console.error('app.py not found at:', scriptPath)
    mainWindow?.webContents.send('python-error', 'app.py not found')
    return
  }

  // Запускаем Python процесс
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

  pythonProcess.on('close', (code) => {
    console.log(`Python process exited with code ${code}`)
    pythonProcess = null
    mainWindow?.webContents.send('python-status', 'stopped')
  })

  mainWindow?.webContents.send('python-status', 'running')
  mainWindow?.webContents.send('python-log', 'Python process started successfully')
}

// Остановка Python скрипта
function stopPythonScript() {
  if (pythonProcess) {
    pythonProcess.kill()
    pythonProcess = null
    console.log('Python process stopped')
    mainWindow?.webContents.send('python-status', 'stopped')
    mainWindow?.webContents.send('python-log', 'Python process stopped')
  }
}

// IPC обработчики для связи с renderer процессом
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

// Жизненный цикл приложения
app.whenReady().then(() => {
  createWindow()
})

app.on('window-all-closed', () => {
  stopPythonScript()
  if (process.platform !== 'darwin') {
    app.quit()
  }
})

app.on('activate', () => {
  if (mainWindow === null) {
    createWindow()
  }
})