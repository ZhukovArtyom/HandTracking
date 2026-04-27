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

    <div className="h-screen w-full bg-white">
      <div class="w-full h-6/100 bg-white border-b-2 border-gray-300">
        Шапка
      </div>
      <div class="w-full h-5/10 bg-white flex">
        <div class="w-6/10 bg-red-200 mt-5 ml-5 mb-5">
            <div class="relative w-full h-9/10 bg-blue-200">
                <div class="absolute inset-0 bg-gray-500 rounded-xl mb-5">
                    Камера
                </div>
                <div class="absolute inset-0 mt-3 ml-3 mr-3 mb-8 grid grid-rows-[32px_10fr] grid-cols-[32px_10fr] gap-1">
                  <div class="bg-red-200"></div>
                  <div>
                    <div class="h-full bg-white/50 px-2 rounded-xl">
                        <input type="range" class="h-full w-full"/>
                    </div>


                  </div>
                  <div class="w-50 h-full place-self-center flex">
                      <div class="h-full w-[32px] bg-white/50 rounded-xl">
                        <input type="range" class="h-full w-full rotate-270"/>
                    </div>

                  </div>
                  <div class="bg-orange-200 p-4">
                      область отслеживания
                  </div>
                </div>
            </div>
            <div class="w-full h-1/10 bg-green-200 flex">
                <button class="w-2/3 bg-blue-500 text-white px-4 py-2 rounded-xl">
                  Нажми меня
                </button>
                <button class="w-1/3 bg-white text-blue-500 border-2 px-4 py-2 rounded-xl ml-3">
                  Нажми меня
                </button>
            </div>
        </div>
        <div class="w-4/10 bg-white rounded-xl shadow-[2px_2px_8px_rgba(0,0,0,0.25)] m-5">
            Правый блок
        </div>
      </div>
      <div class="w-full h-4/10 bg-green-200">
        Нижний блок — 1/3 высоты
      </div>
      <div class="w-full h-4/100 bg-red-500">
        Подвал
      </div>
    </div>
  )
}

export default App

