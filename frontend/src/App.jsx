import React, { useState, useEffect, useRef } from 'react'
import GestureCard from './components/GestureCard'
import NewGestureMenu from './components/NewGestureMenu'
import ActionLib from './components/ActionLib'

import config_img from './assets/config.png'
import cursor_img from './assets/cursor.png'
import hand_blue_bg_img from './assets/hand_blue_bg.png'
import hand_white_bg_img from './assets/hand_white_bg.png'
import moving_img from './assets/moving.png'
import warning_img from './assets/warning_icon.png'
import success_img from './assets/success_icon.png'


function App() {
  const [pythonRunning, setPythonRunning] = useState(false)
  const [gestureScannerRunning, setGestureScannerRunning] = useState(false)

  const [apiReady, setApiReady] = useState(false)

  const [cursorMenuOpen, setCursorMenuOpen] = useState(false)
  const [gestureMenuOpen, setGestureMenuOpen] = useState(false)

  const [showAddGestureForm, setShowAddGestureForm] = useState(false)

  /*  Имя, группы точек и действие нового жеста */
  const [newGestureName, setNewGestureName] = useState('')
  const [pointGroups, setPointGroups] = useState([])
  const [selectedGestureAction, setSelectedGestureAction] = useState(null)
  const [gestureIcon, setGestureIcon] = useState(null)


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

  const [gestures, setGestures] = useState([])

  const [showDeleteModal, setShowDeleteModal] = useState(false)
  const [gestureToDelete, setGestureToDelete] = useState(null)

  const [pythonStatus, setPythonStatus] = useState('ОСТАНОВЛЕНО')
  const [fps, setFps] = useState(0)

  const [timerCount, setTimerCount] = useState(0)
  const [timerActive, setTimerActive] = useState(false)


  // Таймер перед командой записать жест
  useEffect(() => {
    let interval = null
    if (timerActive && timerCount > 0) {
      interval = setInterval(() => {
        setTimerCount(prev => prev - 1)
      }, 1000)
    } else if (timerCount === 0 && timerActive) {
      // Таймер закончился, отправляем команду на запись
      setTimerActive(false)

      // Отправляем команду записать жест
      window.electronAPI.recordGesture()

    }
    return () => clearInterval(interval)
  }, [timerActive, timerCount])



  const RecordGesture = async () => {

      setPointGroups([])


      if (!apiReady) return

      // запускаем таймер, по истечении которого отправится команда на запись жеста
      setTimerCount(3)
      setTimerActive(true)
  }


   /* Установка действия для нового жеста */
  const handleSelectAction = (action) => {
      setSelectedGestureAction(action)
  }

  const handleOpenAddGesture = () => {
    setShowAddGestureForm(true)

    handlePythonToggle('scanner')

  }

  const handleCloseAddGesture = () => {
    setShowAddGestureForm(false)
    setSelectedGestureAction(null)
    setNewGestureName('')
    setPointGroups([])

    handlePythonToggle('scanner')

  }

  const handleSaveNewGesture = () => {


      if (pointGroups.length === 0 || typeof pointGroups[0] === 'string') {
        // Вместо alert используем более мягкое уведомление
        const inputElement = document.getElementById('gesture_icon')
        if (inputElement) {
          inputElement.style.borderColor = 'red'
          setTimeout(() => {
            inputElement.style.borderColor = ''
          }, 1000)
        }

      }

      if (!newGestureName.trim()) {
        // Вместо alert используем более мягкое уведомление
        const inputElement = document.getElementById('gestureName')
        if (inputElement) {
          inputElement.style.borderColor = 'red'
          setTimeout(() => {
            inputElement.style.borderColor = ''
          }, 1000)
        }

      }

      if (!selectedGestureAction) {
        const actionElement = document.getElementById('gestureAction')
        if (actionElement) {
          actionElement.style.borderColor = 'red'
          setTimeout(() => {
            actionElement.style.borderColor = ''
          }, 1000)
        }

      }

      if (!selectedGestureAction || !newGestureName.trim() || pointGroups.length === 0 || typeof pointGroups[0] === 'string') {
          return
      }

      // Создаём новый жест
      const newGesture = {
          id: Date.now().toString(), // уникальный ID на основе времени
          name: newGestureName,
          action_name: selectedGestureAction.displayName,
          image: "",
          enabled: true,
          points_groups: pointGroups,
          type: selectedGestureAction.type,
          on_press: selectedGestureAction.on_press,
          on_release: selectedGestureAction.on_release || ""
      }

        // Добавляем в список жестов
      const updatedGestures = [...gestures, newGesture]
      setGestures(updatedGestures)

        // Сохраняем в файл
      if (window.electronAPI?.saveGestures) {
        window.electronAPI.saveGestures({ gestures: updatedGestures })
      }

        // Очищаем форму и закрываем
      setNewGestureName('')
      setSelectedGestureAction(null)
      setPointGroups([])



  }


  // Загрузка жестов из файла
  const loadGestures = async () => {
    try {
      if (window.electronAPI && window.electronAPI.readGestures) {
        const gesturesData = await window.electronAPI.readGestures()
        if (gesturesData && gesturesData.gestures) {
          setGestures(gesturesData.gestures)
          console.log('Gestures loaded:', gesturesData.gestures)
        }
      } else {
        console.log('electronAPI.readGestures not available')

      }
    } catch (error) {
      console.error('Error loading gestures:', error)
    }
  }


  const handleGestureToggle = async (id, enabled) => {
    // Обновляем локальный state
    setGestures(prevGestures =>
      prevGestures.map(g =>
        g.id === id ? { ...g, enabled} : g
      )
    )

    // Сохраняем в файл
    if (window.electronAPI?.saveGestures) {
      const updatedGestures = gestures.map(g =>
        g.id === id ? { ...g, enabled} : g
      )
      await window.electronAPI.saveGestures({ gestures: updatedGestures })
    }
  }

  const handleGestureEdit = (gesture) => {
    console.log('Edit gesture:', gesture)
    // Здесь будет открытие модального окна редактирования
  }

  const handleGestureDelete = (id) => {
      setGestureToDelete(id)
      setShowDeleteModal(true)
  }

  const confirmDelete = async () => {
    if (gestureToDelete) {
      // Удаляем жест
      const updatedGestures = gestures.filter(g => g.id !== gestureToDelete)
      setGestures(updatedGestures)

      // Сохраняем в файл
      if (window.electronAPI?.saveGestures) {
        await window.electronAPI.saveGestures({ gestures: updatedGestures })
      }

      // Закрываем модальное окно
      setShowDeleteModal(false)
      setGestureToDelete(null)
    }
  }

  const cancelDelete = () => {
    setShowDeleteModal(false)
    setGestureToDelete(null)
  }

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

        if (showAddGestureForm) { setPythonStatus('ГОТОВ К СКАНИРОВАНИЮ') }
        else { setPythonStatus('ЗАПУЩЕНО') }
        setPythonRunning(true)
      })
    }
  }, [showAddGestureForm])

  // Получение групп пересекающихся точек или предупреждений
  useEffect(() => {
    if (window.electronAPI?.onPointGroups) {
      window.electronAPI.onPointGroups((pointsData) => {
        setPointGroups(pointsData)
      })
    }
  }, [])

  // Получение иконки жеста
  useEffect(() => {
    if (window.electronAPI?.onIcon) {
      window.electronAPI.onIcon((iconData) => {
        setGestureIcon(`data:image/png;base64,${iconData}`)
      })
    }
  }, [])


  // Загрузка жестов при запуске
  useEffect(() => {
      loadGestures()
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

  // Получение статуса Python
  useEffect(() => {
    if (window.electronAPI?.onPythonStatus) {
      window.electronAPI.onPythonStatus((status) => {
        if (status === 'running') {
          setPythonRunning(true)
          // Статус "ЗАПУЩЕНО" установится при получении первого кадра
        } else if (status === 'stopped') {
          setPythonStatus('ОСТАНОВЛЕНО')
          setPythonRunning(false)
          setCurrentFrame(null)
          setFps(0)
        }
      })
    }
  }, [])

  useEffect(() => {
    if (window.electronAPI?.onFps) {
      window.electronAPI.onFps((fpsValue) => {
        setFps(fpsValue)
      })
    }
  }, [])

  const startPython = async (scriptFile) => {
    if (!apiReady) return
    try {
      setPythonStatus('ЗАПУСКАЕТСЯ...')
      await window.electronAPI.startPython(scriptFile)
      // Статус "ЗАПУЩЕНО" установится при получении первого кадра
    } catch (error) {
      console.error('Error starting Python:', error)
      setPythonStatus('ОСТАНОВЛЕНО')
    }
  }

  const stopPython = async () => {
    if (!apiReady) return
    try {
      await window.electronAPI.stopPython()
      setCurrentFrame(null)
      setFps(0)
    } catch (error) {
      console.error('Error stopping Python:', error)
    }
  }

  const handlePythonToggle = (scriptFile) => {
    if (pythonRunning) {
      stopPython()
    } else {
      startPython(scriptFile)
    }
  }






  return (
    <div className="w-full min-h-screen bg-white flex flex-col">
      <div class="w-full h-[5vmax] bg-white border-b-2 border-gray-300 flex items-center">
        <img src={hand_blue_bg_img} class="h-full py-[1vmax] ml-[1vmax] mr-[0.5vmax]" alt="config" />
        <p class="text-[2vmax] text-[rgb(6,207,249)] font-bold">HandTrackingControl</p>
      </div>
      <div class="w-full h-[52vmax] bg-white p-[2vmax] flex">
        <div class="h-full ">
          <div class="relative w-[59vmax] aspect-[4/3]">
            <div class="absolute inset-0 bg-gray-800 rounded-xl overflow-hidden shadow-[4px_4px_8px_rgba(0,0,0,0.5)]">
              {currentFrame ? (
                <img
                  src={currentFrame}
                  alt="Camera feed"
                  className="w-full h-full object-cover"
                />
              ) : (
                <div class="w-full h-full flex items-center justify-center text-white">

                </div>
              )}
            </div>

            {!showAddGestureForm ? (

               <div class="absolute inset-0 rounded-xl mb-5 pointer-events-none">
                  <div
                    id="sensetivity_zone"
                    style={getZoneStyles()}
                  ></div>
                </div>

            ) : (timerActive ? (

                  <div className="absolute inset-0 flex items-center justify-center">
                      {timerCount > 0 && (
                          <div

                              className="h-1/4 aspect-[1/1] rounded-full  flex
                              items-center justify-center text-[10vmax] font-bold text-[rgb(6,207,249)] opacity-50"

                              style={{
                                  animation: 'pulseScale 1s ease-out infinite'
                              }}
                          >
                            {timerCount}
                          </div>
                      )}

                  </div>


            ) : null )}



            <div class="absolute inset-0 m-3 grid grid-rows-[32px_10fr] grid-cols-[32px_10fr] gap-1">

              {!showAddGestureForm ? (

                <>
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
                </>

              ) : (
                 <>
                    <div></div>
                    {pointGroups.length !== 0 ? (

                        <div className="flex justify-end">

                            <div className={`bg-white/70 h-full rounded-xl px-3 py-1 flex items-center text-[1.5vmax] font-bold ${
                                typeof pointGroups[0] === 'string' ? 'text-red-500' : 'text-green-600'
                            }`}>

                                <img src={ typeof pointGroups[0] === 'string' ? warning_img : success_img} className="h-full mr-[0.5vmax]"/>
                                { typeof pointGroups[0] === 'string' ? pointGroups[0] : 'ЖЕСТ ЗАПИСАН'}

                            </div>
                        </div>

                    ) : (

                        <div></div>

                    )}

                    <div></div>
                 </>

              )}

              <div className="h-full w-full flex justify-end items-end">
                  <div className="bg-white/70 h-1/10 rounded-xl px-3 py-1 flex items-center gap-3">
                    <div className="flex items-center">
                      <p className="text-[1.5vmax] font-bold text-black">СТАТУС:</p>
                      <p className={`text-[1.5vmax] font-bold ml-2 ${
                        pythonStatus === 'ЗАПУЩЕНО' || pythonStatus === 'ГОТОВ К СКАНИРОВАНИЮ' ? 'text-green-600' :
                        pythonStatus === 'ЗАПУСКАЕТСЯ...' ? 'text-yellow-600' : 'text-red-600'
                      }`}>
                        {pythonStatus}
                      </p>
                    </div>

                    {!showAddGestureForm ? (

                        <div className="flex items-center">
                          <p className="text-[1.5vmax] font-bold text-black">FPS:</p>
                          <p className="text-[1.5vmax] font-bold text-black ml-2">
                            {fps}
                          </p>
                        </div>

                    ) : null}


                  </div>
              </div>

            </div>
          </div>
          <div class="w-full h-[5vmax] pt-[2vmax] flex">
            <button
              onClick={() => handlePythonToggle('main')}
              class={`w-2/3 text-white text-[1.5vmax] rounded-xl transition-colors ${
                pythonRunning
                  ? 'bg-red-500 hover:bg-red-700'
                  : 'bg-[rgb(6,207,249)] hover:bg-[rgb(5,180,220)]'
              }`}
            >
              {pythonRunning ? 'ОСТАНОВИТЬ' : 'ЗАПУСТИТЬ'}
            </button>
            <button class="w-1/3 bg-white text-[1.5vmax] text-[rgb(6,207,249)] border-2 border-[rgb(6,207,249)] rounded-xl ml-3">
              ПРОВЕРКА
            </button>
          </div>
        </div>

        {showAddGestureForm ? (
            <NewGestureMenu

              onCancel={handleCloseAddGesture}
              onSave={handleSaveNewGesture}
              onRecordGesture={RecordGesture}
              selectedAction={selectedGestureAction}
              gestureName={newGestureName}
              gestureIcon={gestureIcon}
              onGestureNameChange={setNewGestureName}
              pythonStatus={pythonStatus}

            />
          ) : (


            <div class="h-[49vmax] w-full ml-[2vmax] bg-white rounded-xl shadow-[2px_2px_8px_rgba(0,0,0,0.25)]">
              <div class="w-full h-[5vmax] border-b-2 border-gray-300 flex items-center">
                <div class="h-5/10 flex items-center ml-[0.5vmax]">
                  <img src={config_img} class="h-full m-2" alt="config" />
                  <p class="text-[2vmax]">Конфигурация</p>
                </div>
              </div>

              <div class="relative inline-block w-full" ref={cursorMenuRef}>
                <button
                  onClick={() => setCursorMenuOpen(!cursorMenuOpen)}
                  class="h-[4vmax] w-full text-black border-b border-gray-300 transition flex items-center"
                >
                  <div class="h-5/10 flex items-center ml-[2vmax]">
                    <img src={cursor_img} class="h-full m-2" alt="cursor" />
                    <p class="text-[1.7vmax]">Управление курсором</p>
                  </div>
                </button>
                {cursorMenuOpen && (
                  <div class="w-full text-xs">
                    <div class="px-[3vmax] py-[0.5vmax]">
                        <div class="h-[4vmax] flex items-center justify-between">
                          <p class="text-[1.5vmax]">РАЗМЕР ОБЛАСТИ ОТСЛЕЖИВАНИЯ</p>
                          <p class="text-[1.5vmax] text-[rgb(6,207,249)] font-bold">{trackingSize}%</p>
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
                    <div class="px-[3vmax] py-[0.5vmax]">
                        <div class="h-[4vmax] flex items-center justify-between">
                          <p class="text-[1.5vmax]">СГЛАЖИВАНИЕ</p>
                          <p class="text-[1.5vmax] text-[rgb(6,207,249)] font-bold">{smoothingLevel}%</p>
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
                    <div class="px-[3vmax] py-[0.5vmax]">
                        <div class="h-[4vmax] flex items-center">
                          <p class="text-[1.5vmax]">ОСНОВНАЯ РУКА</p>
                        </div>
                        <div class="h-[4vmax] rounded-xl border border-gray-300 flex items-center p-[2px]">
                          <button
                            onClick={() => handleControlHandChange('left')}
                            className={`w-1/2 h-full text-[2vmax] mr-[2px] rounded-xl transition-colors ${
                              controlHand === 'left'
                                ? 'bg-[rgb(6,207,249)] text-white'
                                : 'bg-white text-[rgb(6,207,249)]'
                            }`}
                          >
                            Левая
                          </button>
                          <button
                            onClick={() => handleControlHandChange('right')}
                            className={`w-1/2 h-full text-[2vmax] rounded-xl transition-colors ${
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

              <div class="relative inline-block w-full" ref={gestureMenuRef}>
                <button
                  onClick={() => setGestureMenuOpen(!gestureMenuOpen)}
                  class="h-[4vmax] w-full text-black border-b border-gray-300 transition flex items-center"
                >
                  <div class="h-5/10 flex items-center ml-[2vmax]">
                    <img src={hand_blue_bg_img} class="h-full m-2" alt="gestures" />
                    <p class="text-[1.7vmax]">Распознавание жестов</p>
                  </div>
                </button>
                {gestureMenuOpen && (
                  <div class="w-full">
                    <div class="px-[3vmax] py-[0.5vmax]">
                        <div class="h-[4vmax] flex items-center justify-between">
                          <p class="text-[1.3vmax]">ЧУВСТВИТЕЛЬНОСТЬ РАСПОЗНАВАНИЯ ЖЕСТОВ</p>
                          <p class="text-[1.5vmax] text-[rgb(6,207,249)] font-bold">{gestureSensitivity}%</p>
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
                    <div class="px-[3vmax] py-[0.5vmax]">
                        <div class="h-[4vmax] flex items-center justify-between">
                          <p class="text-[1.3vmax]">ЗАДЕРЖКА СРАБАТЫВАНИЯ ЖЕСТОВ</p>
                          <p class="text-[1.5vmax] text-[rgb(6,207,249)] font-bold">{activationDelay} сек.</p>
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
          )}

      </div>


      <div class="w-full h-[38vmax] flex flex-col mt-[2vmax]">

        {showAddGestureForm ? (
            <ActionLib
                onSelectAction={handleSelectAction}
            />
          ) : (

            <>
                <div class="w-full h-[4vmax] px-[2vmax] flex justify-between">
                    <div class="h-full flex items-center">
                      <img src={hand_white_bg_img} class="h-full" />
                      <p class="text-[1.5vmax] ml-2">Библиотека жестов</p>
                    </div>
                    <button
                        disabled={pythonRunning}
                        onClick={handleOpenAddGesture}
                        className={ !pythonRunning ? 'px-[3vmax] text-[1.2vmax] text-[rgb(6,207,249)] border-2 border-[rgb(6,207,249)] rounded-xl'
                            : 'px-[3vmax] text-[1.2vmax] text-gray-300 border-2 border-gray-300 rounded-xl'
                        }
                    >
                        + ДОБАВИТЬ ЖЕСТ
                    </button>
                </div>

                <div id="gestureLibrary" class="h-full flex overflow-x-auto  ml-[2vmax] mr-[2vmax] mb-[1vmax] pt-[2vmax] pb-[2vmax]">
                        {gestures.map((gesture) => (
                            <GestureCard
                              key={gesture.id}
                              gesture={gesture}
                              onToggle={handleGestureToggle}
                              onEdit={handleGestureEdit}
                              onDelete={() => handleGestureDelete(gesture.id)}
                            />
                        ))}
                </div>
            </>

        )}

      </div>
      <div class="w-full h-[3vmax] border-t-2 border-gray-300">
                {/*   Подвал */}
      </div>



      {showDeleteModal && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
            <div className="bg-white rounded-xl shadow-xl p-6 max-w-sm w-full mx-4">
              <h3 className="text-xl font-semibold text-gray-800 mb-2">
                Вы уверены, что хотите удалить этот жест?
              </h3>

              <div className="flex justify-end gap-3">
                <button
                  onClick={cancelDelete}
                  className="px-4 py-2 text-gray-600 bg-gray-100 hover:bg-gray-200 rounded-lg transition"
                >
                  Отмена
                </button>
                <button
                  onClick={confirmDelete}
                  className="px-4 py-2 text-white bg-red-500 hover:bg-red-600 rounded-lg transition"
                >
                  Удалить
                </button>
              </div>
            </div>

          </div>
        )}

    </div>
  )
}

export default App