const { app, BrowserWindow, ipcMain } = require('electron')
const fs = require('fs')
const path = require('path')

const { spawn } = require('child_process')
let pythonProcess = null
let mainWindow = null



function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      nodeIntegration: false,
      contextIsolation: true
    }
  })

  if (process.env.NODE_ENV === 'development') {
    mainWindow.loadURL('http://localhost:5173')
    mainWindow.webContents.openDevTools()
  } else {
    mainWindow.loadFile('dist/index.html')
  }
}

// Получение пути к settings.json
function getSettingsPath() {
  const projectRoot = path.join(__dirname, '..')
  return path.join(projectRoot, 'backend', 'config', 'settings.json')
}

// Чтение настроек
ipcMain.handle('read-settings', async () => {
  try {
    const settingsPath = getSettingsPath()
    console.log('Reading settings from:', settingsPath)

    if (fs.existsSync(settingsPath)) {
      const data = fs.readFileSync(settingsPath, 'utf8')
      return JSON.parse(data)
    } else {
      console.error('Settings file not found')
      return null
    }
  } catch (error) {
    console.error('Error reading settings:', error)
    return null
  }
})

// Сохранение настроек
ipcMain.handle('save-settings', async (event, newSettings) => {
  try {
    const settingsPath = getSettingsPath()

    // Читаем текущие настройки
    let currentSettings = {}
    if (fs.existsSync(settingsPath)) {
      const data = fs.readFileSync(settingsPath, 'utf8')
      currentSettings = JSON.parse(data)
    }

    // Объединяем с новыми настройками
    const mergedSettings = { ...currentSettings, ...newSettings }

    // Сохраняем в файл
    fs.writeFileSync(settingsPath, JSON.stringify(mergedSettings, null, 2), 'utf8')
    console.log('Settings saved successfully')

    // Отправляем уведомление Python процессу (если запущен)
    if (mainWindow) {
      mainWindow.webContents.send('settings-changed', mergedSettings)
    }

    return mergedSettings
  } catch (error) {
    console.error('Error saving settings:', error)
    return null
  }
})

ipcMain.handle('start-python', async () => {
  if (pythonProcess) {
    return { success: false, message: 'Python already running' }
  }

  // Путь к Python скрипту
  const scriptPath = path.join(__dirname, '..', 'backend', 'app.py')
  const backendDir = path.join(__dirname, '..', 'backend')

  console.log('Script path:', scriptPath)
  console.log('Working directory:', backendDir)

  // Проверяем существование файла
  if (!fs.existsSync(scriptPath)) {
    console.error('Python script not found at:', scriptPath)
    return { success: false, message: 'Python script not found' }
  }

  // Запускаем Python с правильной рабочей директорией
  pythonProcess = spawn('python', [scriptPath], {
    cwd: backendDir,  // ← КЛЮЧЕВОЕ: рабочая директория = папка backend
    env: {
      ...process.env,
      PYTHONUNBUFFERED: '1',
      PYTHONIOENCODING: 'utf-8'  // ← добавляем кодировку
    }
  })

  pythonProcess.stdout.on('data', (data) => {
    const output = data.toString('utf-8')  // ← явно указываем кодировку
    console.log(`Python: ${output}`)
    mainWindow?.webContents.send('python-log', output)
  })

  pythonProcess.stderr.on('data', (data) => {
    const error = data.toString('utf-8')  // ← явно указываем кодировку
    console.error(`Python error: ${error}`)
    mainWindow?.webContents.send('python-error', error)
  })

  pythonProcess.on('close', (code) => {
    console.log(`Python process exited with code ${code}`)
    pythonProcess = null
    mainWindow?.webContents.send('python-status', 'stopped')
  })

  pythonProcess.on('error', (err) => {
    console.error(`Failed to start Python: ${err.message}`)
    pythonProcess = null
    mainWindow?.webContents.send('python-error', err.message)
  })

  mainWindow?.webContents.send('python-status', 'running')
  return { success: true }
})

ipcMain.handle('stop-python', async () => {
  if (pythonProcess) {
    pythonProcess.kill()
    pythonProcess = null
    mainWindow?.webContents.send('python-status', 'stopped')
    return { success: true }
  }
  return { success: false, message: 'Python not running' }
})

ipcMain.handle('get-python-status', async () => {
  console.log('get-python-status handler')
  return false
})

app.whenReady().then(createWindow)

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit()
  }
})