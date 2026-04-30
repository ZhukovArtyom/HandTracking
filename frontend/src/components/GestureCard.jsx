import React, { useState } from 'react'

import settings_img from '../assets/settings_icon.png'
import delete_img from '../assets/delete_icon.png'

function GestureCard({ gesture, onToggle, onEdit, onDelete }) {
  const [isEnabled, setIsEnabled] = useState(gesture.enabled === true)

  const handleToggle = () => {
    const newState = !isEnabled
    setIsEnabled(newState)
    if (onToggle) {
      onToggle(gesture.id, newState)
    }
  }

  return (
    <div className="h-[30vmax] aspect-[6/5] bg-white rounded-xl shadow-[2px_2px_8px_rgba(0,0,0,0.25)] mr-3 mb-2 mt-2 p-[1.5vmax] flex flex-col ">
        <div className="h-3/4 w-full py-2 flex">
            <div className="h-full aspect-[1/1] rounded-full bg-gray-200 flex items-center justify-center overflow-hidden">
                    {gesture.image ? (
                        <img src={gesture.image} alt={gesture.name} className="w-full h-full object-cover" />
                      ) : (
                        <svg className="w-12 h-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 5v2m0 4v2m0 4v2M5 5h14a2 2 0 012 2v10a2 2 0 01-2 2H5a2 2 0 01-2-2V7a2 2 0 012-2z" />
                        </svg>
                    )}
            </div>

            <div className="flex-1 flex flex-col items-end">


                    <div className="h-1/5 w-full flex justify-end mb-[2.5vmax]">
                            <button
                              onClick={() => onEdit && onEdit(gesture)}
                              className="h-full aspect-[1/1] mr-3"
                            >
                                <img src={settings_img} class="h-full"/>
                            </button>
                            <button
                              onClick={() => onDelete && onDelete(gesture.id)}
                              className="h-full aspect-[1/1]"
                            >
                                    <img src={delete_img} class="h-full"/>
                            </button>
                     </div>

                    <button
                        onClick={handleToggle}
                        className={`relative inline-flex w-1/2 aspect-[2/1] py-1 items-center rounded-full transition-colors ${
                          isEnabled ? 'bg-[rgb(6,207,249)]' : 'bg-gray-300'
                        }`}
                      >
                        <span
                          className={`inline-block h-full aspect-[1/1] transform rounded-full bg-white transition-transform ${
                            isEnabled ? 'translate-x-6' : 'translate-x-1'
                          }`}
                      />
                    </button>


            </div>
        </div>
        <div className="h-1/4 max-w-[31vmax] flex flex-col">

                    <h3 className="text-[2.5vmax] font-semibold text-black text-left overflow-hidden truncate text-ellipsis">
                      {gesture.name || 'Название'}
                    </h3>


                <p className="text-[2vmax] font-regular text-black text-left overflow-hidden truncate text-ellipsis">
                  {gesture.action_name || 'Действие'}
                </p>

        </div>


    </div>
  )
}

export default GestureCard