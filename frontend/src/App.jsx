import React, { useState, useEffect, useRef } from 'react'


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
      console.error('electronAPI not found!')
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

    window.electronAPI.onPythonLog(handlePythonLog)
    window.electronAPI.onPythonStatus(handlePythonStatus)
    window.electronAPI.onPythonError(handlePythonError)
    window.electronAPI.getPythonStatus().then(setPythonRunning).catch(err => {
      addLog(`Error getting status: ${err}`)
    })
    addLog('UI started. Ready to control hand tracking.')

    return () => {
      window.electronAPI.removeAllListeners()
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
    <div className="min-h-screen bg-gradient-to-br from-purple-600 to-indigo-700 flex items-center justify-center p-4">
      <div className="max-w-2xl w-full bg-white rounded-2xl shadow-2xl p-8">
        {/* Header */}
        <div className="flex justify-between items-center mb-8 pb-4 border-b border-gray-200">
          <h1 className="text-2xl font-bold text-gray-800">
            🖐️ Hand Tracking Control
          </h1>
          <div className={`px-4 py-2 rounded-full font-semibold text-sm ${
            pythonRunning
              ? 'bg-green-100 text-green-700 border border-green-300'
              : 'bg-red-100 text-red-700 border border-red-300'
          }`}>
            {pythonRunning ? '🟢 Python: RUNNING' : '🔴 Python: STOPPED'}
          </div>
        </div>

        {/* Controls */}
        <div className="flex justify-center my-8">
          {!apiReady ? (
            <button disabled className="px-8 py-3 bg-gray-400 text-white font-bold rounded-lg cursor-not-allowed">
              ⏳ Loading...
            </button>
          ) : !pythonRunning ? (
            <button
              onClick={startPython}
              className="px-8 py-3 bg-green-600 hover:bg-green-700 text-white font-bold rounded-lg transition-all hover:scale-105 hover:shadow-lg"
            >
              ▶ START TRACKING
            </button>
          ) : (
            <button
              onClick={stopPython}
              className="px-8 py-3 bg-red-600 hover:bg-red-700 text-white font-bold rounded-lg transition-all hover:scale-105 hover:shadow-lg"
            >
              ⏹️ STOP TRACKING
            </button>
          )}
        </div>

        {/* Log Panel */}
        <div className="bg-gray-50 rounded-lg p-5 my-5 border border-gray-200">
          <h3 className="text-gray-700 font-semibold mb-3">📋 Log</h3>
          <div
            ref={logContainerRef}
            className="bg-gray-900 text-gray-300 rounded-md p-3 h-80 overflow-y-auto font-mono text-xs"
          >
            {logs.length === 0 ? (
              <div className="text-gray-500 text-center py-8 italic">
                No logs yet. Click START to begin...
              </div>
            ) : (
              logs.map((log, index) => (
                <div key={index} className="py-1 border-b border-gray-800">
                  {log}
                </div>
              ))
            )}
          </div>
        </div>

        {/* Info Panel */}
        <div className="bg-blue-50 border-l-4 border-blue-500 p-4 rounded mt-5">
          <p className="text-blue-800 text-sm mb-1">
            💡 Tip: When tracking is active, use your hand to control the mouse cursor
          </p>
          <p className="text-blue-800 text-sm mb-1">
            🖱️ Gestures: Index+Thumb = Left Click | Ring+Thumb = Right Click
          </p>
          <p className="text-blue-800 text-sm">
            🎮 Hold Index+Thumb for Drag & Drop
          </p>
        </div>
      </div>
    </div>
  )
}

export default App

