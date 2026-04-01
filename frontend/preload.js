const { contextBridge, ipcRenderer } = require('electron')

contextBridge.exposeInMainWorld('electronAPI', {
  startPython: () => ipcRenderer.invoke('start-python'),
  stopPython: () => ipcRenderer.invoke('stop-python'),
  getPythonStatus: () => ipcRenderer.invoke('get-python-status'),
  onPythonLog: (callback) => ipcRenderer.on('python-log', (event, data) => callback(data)),
  onPythonStatus: (callback) => ipcRenderer.on('python-status', (event, data) => callback(data)),
  onPythonError: (callback) => ipcRenderer.on('python-error', (event, data) => callback(data)),
  removeAllListeners: () => {
    ipcRenderer.removeAllListeners('python-log')
    ipcRenderer.removeAllListeners('python-status')
    ipcRenderer.removeAllListeners('python-error')
  }
})