import React, { useState, useEffect, useRef } from 'react'
import config_img from './assets/config.png'
import cursor_img from './assets/cursor.png'
import hand_blue_bg_img from './assets/hand_blue_bg.png'
import hand_white_bg_img from './assets/hand_white_bg.png'
import moving_img from './assets/moving.png'

function App() {
  const [pythonRunning, setPythonRunning] = useState(false)
  const [apiReady, setApiReady] = useState(false)

  const [cursorMenuOpen, setCursorMenuOpen] = useState(false)
  const [gestureMenuOpen, setGestureMenuOpen] = useState(false)

  const cursorMenuRef = useRef(null)
  const gestureMenuRef = useRef(null)

  const [trackingSize, setTrackingSize] = useState(50)
  const [sensitivityZoneX, setSensitivityZoneX] = useState(50)
  const [sensitivityZoneY, setSensitivityZoneY] = useState(50)
  const [smoothingLevel, setSmoothingLevel] = useState(50)
  const [gestureSensitivity, setGestureSensitivity] = useState(50)
  const [activationDelay, setActivationDelay] = useState(0)

  // Функция сохранения настроек
  const saveSettings = async (updates) => {
    if (!window.electronAPI?.saveSettings) return

    try {
      const settings = await window.electronAPI.saveSettings(updates)
      console.log('Saved:', updates)
    } catch (error) {
      console.error('Error saving settings:', error)
    }
  }

  // Обёртки для setState с автоматическим сохранением
  const handleTrackingSizeChange = (value) => {
    setTrackingSize(value)
    saveSettings({
      cursor: { sensitivity_zone_percent: value }
    })
  }

  const handleSensitivityZoneXChange = (value) => {
    setSensitivityZoneX(value)
    saveSettings({
      cursor: { sensitivity_zone_X: value }
    })
  }

  const handleSensitivityZoneYChange = (value) => {
    setSensitivityZoneY(value)
    saveSettings({
      cursor: { sensitivity_zone_Y: value }
    })
  }

  const handleSmoothingLevelChange = (value) => {
    setSmoothingLevel(value)
    saveSettings({
      cursor: { smoothing_level: value / 100 }
    })
  }

  const handleGestureSensitivityChange = (value) => {
    setGestureSensitivity(value)
    saveSettings({
      gestures: { click_distance_threshold: value / 1000 }
    })
  }

  const handleActivationDelayChange = (value) => {
    setActivationDelay(value)
    saveSettings({
      gestures: { activation_delay: value }
    })
  }

  // Загрузка настроек при запуске
  useEffect(() => {
    const loadSettings = async () => {
      try {
        if (window.electronAPI && window.electronAPI.readSettings) {
          const settings = await window.electronAPI.readSettings()
          if (settings) {
            if (settings.cursor?.sensitivity_zone_percent !== undefined) {
              setTrackingSize(settings.cursor.sensitivity_zone_percent)
            }
            if (settings.cursor?.sensitivity_zone_X !== undefined) {
              setSensitivityZoneX(settings.cursor.sensitivity_zone_X)
            }
            if (settings.cursor?.sensitivity_zone_Y !== undefined) {
              setSensitivityZoneY(settings.cursor.sensitivity_zone_Y)
            }
            if (settings.cursor?.smoothing_level !== undefined) {
              setSmoothingLevel(Math.round(settings.cursor.smoothing_level * 100))
            }
            if (settings.gestures?.click_distance_threshold !== undefined) {
              setGestureSensitivity(Math.round(settings.gestures.click_distance_threshold * 1000))
            }
            if (settings.gestures?.activation_delay !== undefined) {
              setActivationDelay(settings.gestures.activation_delay)
            }
            console.log('Settings loaded:', settings)
          }
        } else {
          console.log('Using demo data')
        }
      } catch (error) {
        console.error('Error loading settings:', error)
      }
    }

    loadSettings()
  }, [])

  // Подписка на изменения настроек извне
  useEffect(() => {
    if (window.electronAPI?.onSettingsChanged) {
      window.electronAPI.onSettingsChanged((settings) => {
        console.log('Settings changed externally:', settings)
        // Обновляем UI при внешних изменениях
        if (settings.cursor?.sensitivity_zone_percent !== undefined) {
          setTrackingSize(settings.cursor.sensitivity_zone_percent)
        }
        if (settings.cursor?.smoothing_level !== undefined) {
          setSmoothingLevel(Math.round(settings.cursor.smoothing_level * 100))
        }
      })
    }
  }, [])

  // Закрытие меню
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (cursorMenuRef.current && !cursorMenuRef.current.contains(event.target)) {
        setCursorMenuOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (gestureMenuRef.current && !gestureMenuRef.current.contains(event.target)) {
        setGestureMenuOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  useEffect(() => {
    if (window.electronAPI) {
      console.log('electronAPI found!')
      setApiReady(true)
    } else {
      console.error('electronAPI not found!')
    }
  }, [])

  useEffect(() => {
    if (apiReady) {
      window.electronAPI.getPythonStatus().then(setPythonRunning).catch(err => {
        console.error('Error getting status:', err)
      })
    }
  }, [apiReady])

  const startPython = async () => {
    if (!apiReady) return
    try {
      await window.electronAPI.startPython()
      setPythonRunning(true)
    } catch (error) {
      console.error('Error starting Python:', error)
    }
  }

  const stopPython = async () => {
    if (!apiReady) return
    try {
      await window.electronAPI.stopPython()
      setPythonRunning(false)
    } catch (error) {
      console.error('Error stopping Python:', error)
    }
  }

  const handlePythonToggle = () => {
    if (pythonRunning) {
      stopPython()
    } else {
      startPython()
    }
  }

  return (
    <div className="w-full min-h-screen bg-white flex flex-col">
      <div class="w-full h-[5vmax] bg-white border-b-2 border-gray-300 flex items-center">
        <img src={hand_blue_bg_img} class="h-full py-[1vmax] ml-[1vmax] mr-[0.5vmax]" alt="config" />
        <p class="text-[2vmax] text-[rgb(6,207,249)] font-bold">HandTrackingControl</p>
      </div>
      <div class="w-full bg-white flex">
        <div class="w-6/10 mt-5 ml-5 mb-5">
          <div class="relative w-full aspect-[4/3]">
            <div class="absolute inset-0 bg-gray-500 rounded-xl mb-5">
              Камера
            </div>

            <div class="absolute inset-0 rounded-xl mb-5">
              <div class="h-1/2 w-1/2 rounded-xl border-2 border-[rgb(6,207,249)]"></div>
            </div>

            <div class="absolute inset-0 mt-3 ml-3 mr-3 mb-8 grid grid-rows-[32px_10fr] grid-cols-[32px_10fr] gap-1">
              <div class="h-full bg-white/50 p-[3px] rounded-xl">
                    <img src={moving_img} class="h-full" />
              </div>
              <div>
                <div class="h-full bg-white/50 px-2 rounded-xl">
                  <input
                    id="sensitivity_zone_x"
                    type="range"
                    min="0"
                    max="100"
                    value={sensitivityZoneX}
                    onChange={(e) => handleSensitivityZoneXChange(Number(e.target.value))}
                    class="h-full w-full"
                  />
                </div>
              </div>
              <div>
                <div class="h-full bg-white/50 px-2 rounded-xl">
                  <input
                    id="sensitivity_zone_y"
                    type="range"
                    min="0"
                    max="100"
                    value={sensitivityZoneY}
                    onChange={(e) => handleSensitivityZoneYChange(Number(e.target.value))}
                    class="h-full w-full"
                  />
                </div>
              </div>
            </div>
          </div>
          <div class="w-full flex">
            <button
              onClick={handlePythonToggle}
              class={`w-2/3 text-white px-4 py-2 rounded-xl transition-colors ${
                pythonRunning
                  ? 'bg-red-500 hover:bg-red-700'
                  : 'bg-[rgb(6,207,249)] hover:bg-[rgb(5,180,220)]'
              }`}
            >
              {pythonRunning ? 'ОСТАНОВИТЬ' : 'ЗАПУСТИТЬ'}
            </button>
            <button class="w-1/3 bg-white text-[rgb(6,207,249)] border-2 border-[rgb(6,207,249)] px-4 py-2 rounded-xl ml-3">
              ПРОВЕРКА
            </button>
          </div>
        </div>

        <div class="w-4/10 bg-white rounded-xl shadow-[2px_2px_8px_rgba(0,0,0,0.25)] m-5">
          <div class="w-full h-[5vmax] border-b-2 border-gray-300 flex items-center">
            <div class="h-5/10 flex items-center ml-3">
              <img src={config_img} class="h-full m-2" alt="config" />
              <p class="text-[12pt]">Конфигурация</p>
            </div>
          </div>

          {/* Меню "Управление курсором" */}
          <div class="relative inline-block w-full" ref={cursorMenuRef}>
            <button
              onClick={() => setCursorMenuOpen(!cursorMenuOpen)}
              class="h-[4vmax] w-full text-black border-b border-gray-300 transition flex items-center"
            >
              <div class="h-5/10 flex items-center ml-5">
                <img src={cursor_img} class="h-full m-2" alt="cursor" />
                <p class="text-[10pt]">Управление курсором</p>
              </div>
            </button>

            {cursorMenuOpen && (
              <div class="w-full text-xs">
                <div class="px-4 py-2">
                    <div class="h-[4vmax] flex items-center justify-between">
                      <p class="text-[10pt]">РАЗМЕР ОБЛАСТИ ОТСЛЕЖИВАНИЯ</p>
                      <p class="text-sm text-[rgb(6,207,249)] font-bold">{trackingSize}%</p>
                    </div>

                    <div class="h-[4vmax] flex items-center">
                      <input
                        id="sensetivity_zone_size"
                        type="range"
                        min="0"
                        max="100"
                        value={trackingSize}
                        onChange={(e) => handleTrackingSizeChange(Number(e.target.value))}
                        class="h-full w-full"
                      />
                    </div>
                </div>

                <div class="px-4 py-2">
                    <div class="h-[4vmax] flex items-center justify-between">
                      <p class="text-[10pt]">СГЛАЖИВАНИЕ</p>
                      <p class="text-sm text-[rgb(6,207,249)] font-bold">{smoothingLevel}%</p>
                    </div>

                    <div class="h-[4vmax] flex items-center">
                      <input
                        id="smoothing_level"
                        type="range"
                        min="0"
                        max="100"
                        value={smoothingLevel}
                        onChange={(e) => handleSmoothingLevelChange(Number(e.target.value))}
                        class="h-full w-full"
                      />
                    </div>
                </div>

                <div class="px-4 py-2">
                    <div class="h-[4vmax] flex items-center">
                      <p class="text-[10pt]">ОСНОВНАЯ РУКА</p>
                    </div>

                    <div class="h-[4vmax] rounded-xl border border-gray-300 flex items-center p-[2px]">
                        <button class="w-1/2 h-full mr-[2px] text-[rgb(6,207,249)] rounded-xl">
                           Левая
                        </button>
                        <button class="w-1/2 h-full bg-[rgb(6,207,249)] text-white rounded-xl">
                           Правая
                        </button>
                    </div>
                </div>

              </div>
            )}
          </div>

          {/* Меню "Жесты" */}
          <div class="relative inline-block w-full" ref={gestureMenuRef}>
            <button
              onClick={() => setGestureMenuOpen(!gestureMenuOpen)}
              class="h-[4vmax] w-full text-black border-b border-gray-300 transition flex items-center"
            >
              <div class="h-5/10 flex items-center ml-5">
                <img src={hand_blue_bg_img} class="h-full m-2" alt="gestures" />
                <p class="text-[10pt]">Распознавание жестов</p>
              </div>
            </button>

            {gestureMenuOpen && (
              <div class="w-full">
                <div class="px-4 py-2">
                    <div class="h-[4vmax] flex items-center justify-between">
                      <p class="text-[10pt]">ЧУВСТВИТЕЛЬНОСТЬ РАСПОЗНАВАНИЯ ЖЕСТОВ</p>
                      <p class="text-sm text-[rgb(6,207,249)] font-bold">{gestureSensitivity}%</p>
                    </div>

                    <div class="h-[4vmax] flex items-center">
                      <input
                        id="gesture_sensitivity"
                        type="range"
                        min="0"
                        max="100"
                        value={gestureSensitivity}
                        onChange={(e) => handleGestureSensitivityChange(Number(e.target.value))}
                        class="h-full w-full"
                      />
                    </div>
                </div>

                <div class="px-4 py-2">
                    <div class="h-[4vmax] flex items-center justify-between">
                      <p class="text-[10pt]">ЗАДЕРЖКА СРАБАТЫВАНИЯ ЖЕСТОВ</p>
                      <p class="text-sm text-[rgb(6,207,249)] font-bold">{activationDelay} сек.</p>
                    </div>

                    <div class="h-[4vmax] flex items-center">
                      <input
                        id="activation_delay"
                        type="range"
                        min="0"
                        max="1"
                        step="0.01"
                        value={activationDelay}
                        onChange={(e) => handleActivationDelayChange(Number(e.target.value))}
                        class="h-full w-full"
                      />
                    </div>
                </div>
              </div>
            )}
          </div>

        </div>
      </div>

      <div class="w-full flex-1 min-h-[27vmax] flex flex-col">
        <div class="w-full h-[3vmax] px-5 flex justify-between">
            <div class="h-full flex items-center">
              <img src={hand_white_bg_img} class="h-full" />
              <p class="text-[12pt] ml-2">Библиотека жестов</p>
            </div>
            <button class="px-3 text-[10pt] text-[rgb(6,207,249)] border-2 border-[rgb(6,207,249)] rounded-xl">
              + ДОБАВИТЬ ЖЕСТ
            </button>
        </div>

        <div class="flex-1 flex overflow-x-auto mt-2 mb-5 ml-5 mr-5">
          <div class="flex-shrink-0 w-80 bg-red-500 mr-4">Элемент 1</div>
          <div class="flex-shrink-0 w-80 bg-red-500 mr-4">Элемент 2</div>
          <div class="flex-shrink-0 w-80 bg-red-500 mr-4">Элемент 3</div>
        </div>
      </div>
      <div class="w-full h-[3vmax] border-t-2 border-gray-300">
        Подвал
      </div>
    </div>
  )
}

export default App