import React, { useState, useEffect} from 'react'

import settings_img from '../assets/settings_icon.png'
import delete_img from '../assets/delete_icon.png'

function GestureCard({ gesture, onToggle, onEdit, onDelete }) {
  const [isEnabled, setIsEnabled] = useState(gesture.enabled === true)

  const [iconSrc, setIconSrc] = useState(null)

  // Загружаем иконку при монтировании компонента
  useEffect(() => {
    const loadIcon = async () => {
      if (gesture.image && gesture.image !== '') {
        try {
          // Запрашиваем иконку через Electron API
          const base64Data = await window.electronAPI.getIcon(gesture.image)
          if (base64Data) {
            setIconSrc(`data:image/png;base64,${base64Data}`)
          }
        } catch (error) {
          console.error('Error loading icon:', error)
          setIconSrc(null)
        }
      }
    }

    loadIcon()
  }, [gesture.image])

  const handleToggle = () => {
    const newState = !isEnabled
    setIsEnabled(newState)
    if (onToggle) {
      onToggle(gesture.id, newState)
    }
  }

  return (
    <div className="h-full aspect-[6/5] bg-white rounded-xl shadow-[2px_2px_8px_rgba(0,0,0,0.25)] mr-3 p-[1.5vmax] flex flex-col ">
        <div className="h-3/4 w-full py-2 flex">
            <div className="h-full aspect-[1/1] rounded-full bg-gray-200 flex items-center justify-center overflow-hidden">
                    {iconSrc ? (
                        <img
                          src={iconSrc}
                          style={{
                            objectFit: 'contain'
                          }}
                          className="w-full h-full bg-[rgb(6,207,249)]"
                          alt={gesture.name}
                        />
                      ) : (
                        <svg className="w-12 h-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 5v2m0 4v2m0 4v2M5 5h14a2 2 0 012 2v10a2 2 0 01-2 2H5a2 2 0 01-2-2V7a2 2 0 012-2z" />
                        </svg>
                    )}
            </div>

            <div className="flex-1 flex flex-col items-end">


                    <div className="h-1/5 w-full flex justify-end items-center mb-[2.5vmax] gap-[1vmax]">
{/*                             <button */}
{/*                               onClick={() => onEdit && onEdit(gesture)} */}
{/*                               className="h-full aspect-[1/1] mr-3" */}
{/*                             > */}
{/*                                 <img src={settings_img} class="h-full"/> */}
{/*                             </button> */}
                            <button
                                onClick={handleToggle}
                                className={`relative inline-flex w-[5vmax] h-[3vmax] p-[0.5vmax] items-center rounded-full transition-colors ${
                                  isEnabled ? 'bg-[rgb(6,207,249)]' : 'bg-gray-300'
                                }`}
                              >
                                <span
                                  className={`inline-block h-[2vmax] aspect-[1/1] transform rounded-full bg-white transition-transform ${
                                    isEnabled ? 'translate-x-[2vmax]' : 'translate-x-[0.2vmax]'
                                  }`}
                              />
                            </button>
                            <button
                              onClick={() => onDelete && onDelete(gesture.id)}
                              className="h-full aspect-[1/1]"
                            >
                                    <img src={delete_img} class="h-full"/>
                            </button>
                     </div>




            </div>
        </div>
        <div className="h-1/4 max-w-[31vmax] flex flex-col">

                    <h3 className="text-[2.5vmax] font-semibold text-black text-left overflow-hidden truncate text-ellipsis">
                      {gesture.name || 'Название'}
                    </h3>


                <p className="text-[2vmax] font-regular text-black text-left overflow-hidden truncate text-ellipsis">
                  {'Действие: ' + gesture.action_name || 'Действие'}
                </p>

        </div>


    </div>
  )
}

export default GestureCard