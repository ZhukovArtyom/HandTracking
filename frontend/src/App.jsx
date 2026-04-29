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
  const [controlHand, setControlHand] = useState('right') // Добавлен state для выбранной руки

  const [currentFrame, setCurrentFrame] = useState(null)

  const getZoneStyles = () => {
    // Размер зоны в процентах от родителя (trackingSize)
    const sizePercent = trackingSize

    // Ширина и высота зоны в процентах
    const zoneSizePercent = sizePercent
    const padding = 5

    const offsetX = padding/2+((100-padding - zoneSizePercent) / 100) * sensitivityZoneX
    const offsetY = padding/2+((100-padding - zoneSizePercent) / 100) * (100 - sensitivityZoneY)

    // Левый верхний угол зоны
    const left = offsetX
    const top = offsetY

    // Ограничиваем значения в пределах 0-100
    const clampedLeft = Math.min(100 - zoneSizePercent, Math.max(0, left))
    const clampedTop = Math.min(100 - zoneSizePercent, Math.max(0, top))

    return {
      position: 'absolute',
      width: `${zoneSizePercent}%`,
      height: `${zoneSizePercent}%`,
      left: `${clampedLeft}%`,
      top: `${clampedTop}%`,
      borderRadius: '0.75rem',
      border: '2px solid rgb(6,207,249)',
      pointerEvents: 'none'
    }
  }

  const saveFullSettings = async (updates) => {
      if (!window.electronAPI?.saveSettings) return

      try {
        // Получаем текущие настройки
        const currentSettings = await window.electronAPI.readSettings()
        if (!currentSettings) return

        // Создаём копию
        const newSettings = JSON.parse(JSON.stringify(currentSettings))

        // Обновляем нужные поля
        if (updates.cursor) {
          newSettings.cursor = { ...newSettings.cursor, ...updates.cursor }
        }
        if (updates.gestures) {
          newSettings.gestures = { ...newSettings.gestures, ...updates.gestures }
        }

        // Сохраняем
        await window.electronAPI.saveSettings(newSettings)
      } catch (error) {
        console.error('Error saving settings:', error)
      }
  }

  // Обработчик для кнопок выбора основной руки
  const handleControlHandChange = (hand) => {
    setControlHand(hand)
    saveFullSettings({
      cursor: { control_hand: hand }
    })
  }

  // Использование:
  const handleTrackingSizeChange = (value) => {
    setTrackingSize(value)
    saveFullSettings({
      cursor: { sensitivity_zone_percent: value }
    })
  }

  const handleSmoothingLevelChange = (value) => {
    setSmoothingLevel(value)
    saveFullSettings({
      cursor: { smoothing_level: value / 100 }
    })
  }

  const handleGestureSensitivityChange = (value) => {
    setGestureSensitivity(value)
    saveFullSettings({
      gestures: { click_distance_threshold: value / 1000 }
    })
  }

  const handleActivationDelayChange = (value) => {
    setActivationDelay(value)
    saveFullSettings({
      gestures: { activation_delay: value }
    })
  }

  const handleSensitivityZoneXChange = (value) => {
    setSensitivityZoneX(value)
    saveFullSettings({
      cursor: { sensitivity_zone_X: value }
    })
  }

  const handleSensitivityZoneYChange = (value) => {
      setSensitivityZoneY(value)
      saveFullSettings({
        cursor: { sensitivity_zone_Y: 100-value }
     })
  }

  // Получение кадра
  useEffect(() => {
    if (window.electronAPI?.onFrame) {
      window.electronAPI.onFrame((frameData) => {
        setCurrentFrame(`data:image/jpeg;base64,${frameData}`)
      })
    }
  }, [])

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
              setSensitivityZoneY(100-settings.cursor.sensitivity_zone_Y)
            }
            if (settings.cursor?.smoothing_level !== undefined) {
              setSmoothingLevel(Math.round(settings.cursor.smoothing_level * 100))
            }
            if (settings.cursor?.control_hand !== undefined) {
              setControlHand(settings.cursor.control_hand)
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
        if (settings.cursor?.control_hand !== undefined) {
          setControlHand(settings.cursor.control_hand)
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
            <div class="absolute inset-0 bg-gray-500 rounded-xl mb-5 overflow-hidden">
              {currentFrame ? (
                <img
                  src={currentFrame}
                  alt="Camera feed"
                  className="w-full h-full object-cover"
                />
              ) : (
                <div class="w-full h-full flex items-center justify-center text-white">
                  Камера
                </div>
              )}
            </div>

            <div class="absolute inset-0 rounded-xl mb-5 pointer-events-none">
              <div
                id="sensetivity_zone"
                style={getZoneStyles()}
              ></div>
            </div>

            <div class="absolute inset-0 mt-3 ml-3 mr-3 mb-8 grid grid-rows-[32px_10fr] grid-cols-[32px_10fr] gap-1">
              <div class="h-full bg-white/50 p-[3px] rounded-xl">
                    <img src={moving_img} class="h-full" />
              </div>
              <div>
                <div class="h-full bg-white/50 px-2 py-2 rounded-xl flex items-center">
                  <input
                    id="sensitivity_zone_x"
                    type="range"
                    min="0"
                    max="100"
                    value={sensitivityZoneX}
                    onChange={(e) => handleSensitivityZoneXChange(Number(e.target.value))}
                    className="h-full w-full
                        [&::-webkit-slider-runnable-track]:bg-white
                        [&::-webkit-slider-runnable-track]:rounded-full
                        [&::-webkit-slider-runnable-track]:h-full
                        [&::-moz-range-track]:bg-white
                        [&::-moz-range-track]:rounded-full
                        [&::-moz-range-track]:h-[10px]
                        [&::-moz-range-progress]:bg-white
                        [&::-moz-range-progress]:rounded-full
                        [&::-moz-range-progress]:h-[10px]"
                  />
                </div>
              </div>
              <div>
                <div class="h-full bg-white/50 py-2 px-2 rounded-xl flex items-center justify-center">
                    <input
                        id="sensitivity_zone_y"
                        type="range"
                        min={0}
                        max={100}
                        value={sensitivityZoneY}
                        onChange={(e) => handleSensitivityZoneYChange(Number(e.target.value))}
                        className="h-full w-full
                        [&::-webkit-slider-runnable-track]:bg-white
                        [&::-webkit-slider-runnable-track]:rounded-full
                        [&::-webkit-slider-runnable-track]:w-full
                        [&::-moz-range-track]:bg-white
                        [&::-moz-range-track]:rounded-full
                        [&::-moz-range-track]:w-[10px]
                        [&::-moz-range-progress]:bg-white
                        [&::-moz-range-progress]:rounded-full
                        [&::-moz-range-progress]:w-[10px]"
                        style={{
                          WebkitAppearance: 'slider-vertical',
                          appearance: 'slider-vertical',
                        }}
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
                      <button
                        onClick={() => handleControlHandChange('left')}
                        className={`w-1/2 h-full mr-[2px] rounded-xl transition-colors ${
                          controlHand === 'left'
                            ? 'bg-[rgb(6,207,249)] text-white'
                            : 'bg-white text-[rgb(6,207,249)]'
                        }`}
                      >
                        Левая
                      </button>
                      <button
                        onClick={() => handleControlHandChange('right')}
                        className={`w-1/2 h-full rounded-xl transition-colors ${
                          controlHand === 'right'
                            ? 'bg-[rgb(6,207,249)] text-white'
                            : 'bg-white text-[rgb(6,207,249)]'
                        }`}
                      >
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