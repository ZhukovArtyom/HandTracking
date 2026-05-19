const { app, BrowserWindow, ipcMain } = require('electron')
const fs = require('fs')
const path = require('path')
const { spawn } = require('child_process')

let pythonProcess = null
let mainWindow = null

// Функция получения пути к python.exe
function getPythonPath() {
  if (process.env.NODE_ENV === 'development') {
    return 'python';  // используем системный Python в разработке
  } else {
    // В продакшене используем упакованный Python из resources
    const pythonExe = path.join(process.resourcesPath, 'python-embedded', 'python.exe');
    return pythonExe;
  }
}

// Функция для получения правильного пути в режиме разработки и продакшн
function getResourcePath(relativePath) {
  if (process.env.NODE_ENV === 'development') {
    return path.join(__dirname, '..', relativePath)
  } else {
    return path.join(process.resourcesPath, relativePath)
  }
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 640,
    height: 640,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      nodeIntegration: false,
      contextIsolation: true
    }
  })

  if (process.env.NODE_ENV === 'development') {
    mainWindow.loadURL('http://localhost:5173')
  } else {
    const indexPath = path.join(__dirname, 'dist', 'index.html')
    mainWindow.loadFile(indexPath)
  }
}

function getSettingsPath() {
  return getResourcePath(path.join('backend', 'config', 'settings.json'))
}

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

ipcMain.handle('save-settings', async (event, newSettings) => {
  try {
    const settingsPath = getSettingsPath()

    let currentSettings = {}
    if (fs.existsSync(settingsPath)) {
      const data = fs.readFileSync(settingsPath, 'utf8')
      currentSettings = JSON.parse(data)
    }

    const mergedSettings = { ...currentSettings, ...newSettings }
    fs.writeFileSync(settingsPath, JSON.stringify(mergedSettings, null, 2), 'utf8')
    console.log('Settings saved successfully')

    if (mainWindow) {
      mainWindow.webContents.send('settings-changed', mergedSettings)
    }

    return mergedSettings
  } catch (error) {
    console.error('Error saving settings:', error)
    return null
  }
})



ipcMain.handle('start-python', async (event, scriptFile) => {
  if (pythonProcess) {
    return { success: false, message: 'Python already running' }
  }

  const backendPath = getResourcePath('backend')
  let scriptPath

  if (scriptFile === "main") {
    scriptPath = path.join(backendPath, 'app.py')
  }
  else {
    scriptPath = path.join(backendPath, 'gesture_recorder.py')
  }

  console.log('Script path:', scriptPath)
  console.log('Working directory:', backendPath)

  if (!fs.existsSync(scriptPath)) {
    console.error('Python script not found at:', scriptPath)
    return { success: false, message: 'Python script not found' }
  }

  const pythonPath = getPythonPath();

  if (!fs.existsSync(pythonPath) && process.env.NODE_ENV !== 'development') {
    console.error('Python not found at:', pythonPath);
    return { success: false, message: 'Python executable not found' };
  }

  pythonProcess = spawn(pythonPath, [scriptPath], {
    cwd: backendPath,
    env: {
      ...process.env,
      PYTHONUNBUFFERED: '1',
      PYTHONIOENCODING: 'utf-8',
      PYTHONPATH: backendPath
    }
  })

  // ЕДИНЫЙ ОБРАБОТЧИК stdout
  pythonProcess.stdout.on('data', (data) => {
    const output = data.toString('utf-8')
    console.log('Python stdout:', output)

    // Проверяем, что это кадр (начинается с "FRAME:")
    if (output.startsWith('FRAME:')) {
      const frameData = output.substring(6)
      mainWindow?.webContents.send('frame', frameData)
    }
    else if (output.startsWith('FPS:')) {
        const fpsValue = parseInt(output.substring(4))
        mainWindow?.webContents.send('python-fps', fpsValue)
    }
    else if (output.startsWith('POINT_GROUPS:')) {
        const str_data = output.substring(13)
        try {
            const pointsData = JSON.parse(str_data)
            mainWindow?.webContents.send('point-groups', pointsData)
        } catch (e) {
            console.error('Failed to parse point groups:', e, 'Data:', str_data)
        }
    }
    else if (output.startsWith('ICON:')) {
        const iconData = output.substring(5)
        mainWindow?.webContents.send('icon', iconData)
    }
    else {
      console.log(`Python: ${output}`)
      mainWindow?.webContents.send('python-log', output)
    }
  })

  pythonProcess.stderr.on('data', (data) => {
    const error = data.toString('utf-8')
    console.error(`Python error: ${error}`)
    mainWindow?.webContents.send('python-error', error)
  })

  pythonProcess.on('spawn', () => {
      mainWindow?.webContents.send('python-status', 'starting')
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
  return pythonProcess !== null
})




ipcMain.handle('read-gestures', async () => {
  try {
    const gesturesPath = getResourcePath(path.join('backend', 'config', 'gestures.json'))
    console.log('Reading gestures from:', gesturesPath)

    if (fs.existsSync(gesturesPath)) {
      const data = fs.readFileSync(gesturesPath, 'utf8')
      return JSON.parse(data)
    } else {
      console.error('Gestures file not found')
      return { gestures: [] }
    }
  } catch (error) {
    console.error('Error reading gestures:', error)
    return { gestures: [] }
  }
})

ipcMain.handle('save-icon', async (event, { filename, data }) => {
    try {
        const iconsDir = getResourcePath(path.join('gestures_icons'))

        if (!fs.existsSync(iconsDir)) {
            fs.mkdirSync(iconsDir, { recursive: true });        }


        const iconPath = path.join(iconsDir, filename)
        const buffer = Buffer.from(data, 'base64')
        fs.writeFileSync(iconPath, buffer)

        const relativePath = `gestures_icons/${filename}`
        return { success: true, path: relativePath }
    } catch (error) {
        console.error('Error saving icon:', error)
        return { success: false, error: error.message }
    }
})

ipcMain.handle('get-icon', async (event, iconPath) => {
    try {
        const fullPath = getResourcePath(iconPath);

        if (fs.existsSync(fullPath)) {
            const buffer = fs.readFileSync(fullPath);
            return buffer.toString('base64');
        } else {
            console.error('Icon not found:', fullPath);
            return null;
        }
    } catch (error) {
        console.error('Error reading icon:', error);
        return null;
    }
});

ipcMain.handle('delete-icon', async (event, { iconPath }) => {
    try {
        const fullPath = getResourcePath(iconPath)

        if (fs.existsSync(fullPath)) {
            fs.unlinkSync(fullPath)
            return { success: true }
        } else {
            return { success: true, message: 'File already deleted' }
        }
    } catch (error) {
        console.error('Error deleting icon:', error)
        return { success: false, error: error.message }
    }
})

ipcMain.handle('save-gestures', async (event, gesturesData) => {
  try {
    const gesturesPath = getResourcePath(path.join('backend', 'config', 'gestures.json'))
    fs.writeFileSync(gesturesPath, JSON.stringify(gesturesData, null, 2), 'utf8')
    console.log('Gestures saved successfully')
    return { success: true }
  } catch (error) {
    console.error('Error saving gestures:', error)
    return { success: false }
  }
})

ipcMain.handle('record-gesture', async () => {
  if (pythonProcess) {
    pythonProcess.stdin.write('RECORD_GESTURE\n')
    return { success: true }
  }
  return { success: false, message: 'Python not running' }
})


app.whenReady().then(createWindow)

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit()
  }
})

app.on('before-quit', () => {
  if (pythonProcess) {
    pythonProcess.kill()
    pythonProcess = null
  }
})