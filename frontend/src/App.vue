<template>
  <div class="container">
    <div class="header">
      <h1>Hand Tracking </h1>
      <div class="status-badge" :class="pythonRunning ? 'status-running' : 'status-stopped'">
        {{ pythonRunning ? 'Python: RUNNING' : 'Python: STOPPED' }}
      </div>
    </div>

    <div class="controls">
      <button 
        v-if="!pythonRunning" 
        @click="startPython" 
        class="btn btn-start"
      >
         START TRACKING
      </button>
      <button 
        v-else 
        @click="stopPython" 
        class="btn btn-stop"
      >
         STOP TRACKING
      </button>
    </div>

    

    
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'

// Состояния
const pythonRunning = ref(false)
const logs = ref([])

// Функция для добавления лога
const addLog = (message) => {
  const timestamp = new Date().toLocaleTimeString()
  logs.value.unshift(`[${timestamp}] ${message}`)
  // Ограничиваем количество логов до 100
  if (logs.value.length > 100) {
    logs.value.pop()
  }
}

// Запуск Python
const startPython = async () => {
  try {
    addLog('Starting Python process...')
    await window.electronAPI.startPython()
  } catch (error) {
    addLog(`Error starting Python: ${error}`)
  }
}

// Остановка Python
const stopPython = async () => {
  try {
    addLog('Stopping Python process...')
    await window.electronAPI.stopPython()
  } catch (error) {
    addLog(`Error stopping Python: ${error}`)
  }
}

// Получение статуса Python при запуске
const checkPythonStatus = async () => {
  try {
    const status = await window.electronAPI.getPythonStatus()
    pythonRunning.value = status
  } catch (error) {
    console.error('Error getting Python status:', error)
  }
}

// Обработчики событий от Python
const handlePythonLog = (log) => {
  addLog(log)
}

const handlePythonStatus = (status) => {
  pythonRunning.value = (status === 'running')
  addLog(`Python status changed: ${status}`)
}

const handlePythonError = (error) => {
  addLog(`ERROR: ${error}`)
}

// Жизненный цикл компонента
onMounted(() => {
  // Подписываемся на события
  window.electronAPI.onPythonLog(handlePythonLog)
  window.electronAPI.onPythonStatus(handlePythonStatus)
  window.electronAPI.onPythonError(handlePythonError)
  
  // Проверяем статус Python при запуске
  checkPythonStatus()
  addLog('UI started. Ready to control hand tracking.')
})

onUnmounted(() => {
  // Отписываемся от событий
  window.electronAPI.removeAllListeners()
})
</script>

<style scoped>
.container {
  max-width: 800px;
  margin: 0 auto;
  padding: 20px;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 30px;
  padding-bottom: 20px;
  border-bottom: 2px solid #e0e0e0;
}

h1 {
  margin: 0;
  font-size: 24px;
  color: #333;
}

.status-badge {
  padding: 8px 16px;
  border-radius: 20px;
  font-weight: bold;
  font-size: 14px;
}

.status-running {
  background-color: #d4edda;
  color: #155724;
  border: 1px solid #c3e6cb;
}

.status-stopped {
  background-color: #f8d7da;
  color: #721c24;
  border: 1px solid #f5c6cb;
}

.controls {
  display: flex;
  justify-content: center;
  margin: 30px 0;
}

.btn {
  padding: 12px 32px;
  font-size: 18px;
  font-weight: bold;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.3s ease;
}

.btn-start {
  background-color: #28a745;
  color: white;
}

.btn-start:hover {
  background-color: #218838;
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(0,0,0,0.2);
}

.btn-stop {
  background-color: #dc3545;
  color: white;
}

.btn-stop:hover {
  background-color: #c82333;
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(0,0,0,0.2);
}


</style>