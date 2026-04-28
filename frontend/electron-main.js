const { app, BrowserWindow, ipcMain } = require('electron')
const fs = require('fs')
const path = require('path')

let mainWindow

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
  console.log('start-python handler')

  return { success: true }
})

ipcMain.handle('stop-python', async () => {
  console.log('stop-python handler')

  return { success: true }
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