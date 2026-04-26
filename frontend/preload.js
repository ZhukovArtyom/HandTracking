
const { contextBridge, ipcRenderer } = require('electron')

console.log('Preload script started')

const electronAPI = {
  startPython: () => {
    console.log('startPython called, sending to main')
    return ipcRenderer.invoke('start-python')
  },
  stopPython: () => {
    console.log('stopPython called, sending to main')
    return ipcRenderer.invoke('stop-python')
  },
  getPythonStatus: () => {
    console.log('getPythonStatus called, sending to main')
    return ipcRenderer.invoke('get-python-status')
  },
  onPythonLog: (callback) => {
    ipcRenderer.on('python-log', (event, data) => callback(data))
  },
  onPythonStatus: (callback) => {
    ipcRenderer.on('python-status', (event, data) => callback(data))
  },
  onPythonError: (callback) => {
    ipcRenderer.on('python-error', (event, data) => callback(data))
  },
  removeAllListeners: () => {
    ipcRenderer.removeAllListeners('python-log')
    ipcRenderer.removeAllListeners('python-status')
    ipcRenderer.removeAllListeners('python-error')
  }
}

// Экспонируем API
contextBridge.exposeInMainWorld('electronAPI', electronAPI)

console.log('electronAPI exposed successfully')