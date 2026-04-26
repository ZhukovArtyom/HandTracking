import React, { useState, useEffect, useRef } from 'react'
import './App.css'

function App() {
  const [pythonRunning, setPythonRunning] = useState(false)
  const [logs, setLogs] = useState([])
  const [apiReady, setApiReady] = useState(false)
  const logContainerRef = useRef(null)

  // Проверка наличия API
  useEffect(() => {
    if (window.electronAPI) {
      console.log('electronAPI found!')
      setApiReady(true)
    } else {
      console.error('electronAPI not found! Check preload script.')
      addLog('ERROR: electronAPI not available. Please restart the application.')
    }
  }, [])

  // Автоскролл логов
  useEffect(() => {
    if (logContainerRef.current) {
      logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight
    }
  }, [logs])

  // Добавление лога
  const addLog = (message) => {
    const timestamp = new Date().toLocaleTimeString()
    setLogs(prev => [`[${timestamp}] ${message}`, ...prev].slice(0, 100))
  }

  // Обработчики событий от Python
  useEffect(() => {
    if (!apiReady) return

    const handlePythonLog = (log) => addLog(log)
    const handlePythonStatus = (status) => {
      setPythonRunning(status === 'running')
      addLog(`Python status changed: ${status}`)
    }
    const handlePythonError = (error) => addLog(`ERROR: ${error}`)

    // Подписываемся на события
    window.electronAPI.onPythonLog(handlePythonLog)
    window.electronAPI.onPythonStatus(handlePythonStatus)
    window.electronAPI.onPythonError(handlePythonError)

    // Проверяем статус при запуске
    window.electronAPI.getPythonStatus().then(setPythonRunning).catch(err => {
      console.error('Error getting status:', err)
      addLog(`Error getting status: ${err}`)
    })

    addLog('UI started. Ready to control hand tracking.')

    // Отписываемся при размонтировании
    return () => {
      if (window.electronAPI) {
        window.electronAPI.removeAllListeners()
      }
    }
  }, [apiReady])

  const startPython = async () => {
    if (!apiReady) {
      addLog('ERROR: electronAPI not ready')
      return
    }

    try {
      addLog('Starting Python process...')
      await window.electronAPI.startPython()
    } catch (error) {
      addLog(`Error starting Python: ${error}`)
    }
  }

  const stopPython = async () => {
    if (!apiReady) {
      addLog('ERROR: electronAPI not ready')
      return
    }

    try {
      addLog('Stopping Python process...')
      await window.electronAPI.stopPython()
    } catch (error) {
      addLog(`Error stopping Python: ${error}`)
    }
  }

  return (
    <div className="container">
      <div className="header">
        <h1>🖐️ Hand Tracking Control</h1>
        <div className={`status-badge ${pythonRunning ? 'status-running' : 'status-stopped'}`}>
          {pythonRunning ? '🟢 Python: RUNNING' : '🔴 Python: STOPPED'}
        </div>
      </div>

      <div className="controls">
        {!apiReady ? (
          <button disabled className="btn btn-disabled">
            ⏳ Loading...
          </button>
        ) : !pythonRunning ? (
          <button onClick={startPython} className="btn btn-start">
            ▶ START TRACKING
          </button>
        ) : (
          <button onClick={stopPython} className="btn btn-stop">
            ⏹️ STOP TRACKING
          </button>
        )}
      </div>

      <div className="log-panel">
        <h3>📋 Log</h3>
        <div className="log-content" ref={logContainerRef}>
          {logs.length === 0 ? (
            <div className="log-empty">No logs yet. Click START to begin...</div>
          ) : (
            logs.map((log, index) => (
              <div key={index} className="log-line">{log}</div>
            ))
          )}
        </div>
      </div>

      <div className="info">
        <p>💡 Tip: When tracking is active, use your hand to control the mouse cursor</p>
        <p>🖱️ Gestures: Index+Thumb = Left Click | Ring+Thumb = Right Click</p>
        <p>🎮 Hold Index+Thumb for Drag & Drop</p>
      </div>
    </div>
  )
}

export default App