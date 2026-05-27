const { contextBridge, ipcRenderer } = require('electron')

console.log('Preload script started')

const electronAPI = {
  startPython: (scriptFile) => {
    console.log('startPython called')
    return ipcRenderer.invoke('start-python', scriptFile)
  },
  stopPython: () => {
    console.log('stopPython called')
    return ipcRenderer.invoke('stop-python')
  },
  getPythonStatus: () => {
    console.log('getPythonStatus called')
    return ipcRenderer.invoke('get-python-status')
  },
  exportPrograms: () => {
    console.log('exportPrograms called')
    return ipcRenderer.invoke('export-programs')
  },
  readSettings: () => {
    console.log('readSettings called')
    return ipcRenderer.invoke('read-settings')
  },
  saveSettings: (settings) => {
    console.log('saveSettings called')
    return ipcRenderer.invoke('save-settings', settings)
  },
  onSettingsChanged: (callback) => {
    ipcRenderer.on('settings-changed', (event, settings) => callback(settings))
  },
  onFrame: (callback) => {
    ipcRenderer.on('frame', (event, frameData) => callback(frameData))
  },
  onPointGroups: (callback) => {
    ipcRenderer.on('point-groups', (event, pointsData) => callback(pointsData))
  },
  onIcon: (callback) => {
    ipcRenderer.on('icon', (event, iconData) => callback(iconData))
  },
  saveIcon: (data) => {
    return ipcRenderer.invoke('save-icon', data)
  },
  getIcon: (iconPath) => {
    return ipcRenderer.invoke('get-icon', iconPath);
  },
  deleteIcon: (data) => {
    return ipcRenderer.invoke('delete-icon', data)
  },
  readGestures: () => {
    console.log('readGestures called')
    return ipcRenderer.invoke('read-gestures')
  },
  saveGestures: (gestures) => {
    console.log('saveGestures called')
    return ipcRenderer.invoke('save-gestures', gestures)
  },
  onPythonStatus: (callback) => {
    ipcRenderer.on('python-status', (event, status) => callback(status))
  },
  onFps: (callback) => {
    ipcRenderer.on('python-fps', (event, fps) => callback(fps))
  },
  recordGesture: () => {
    ipcRenderer.invoke('record-gesture')
  }
}

contextBridge.exposeInMainWorld('electronAPI', electronAPI)
console.log('electronAPI exposed successfully')