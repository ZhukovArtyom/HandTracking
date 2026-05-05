import React, { useState } from 'react'

import ActionCard from './ActionCard'

import action_img from '../assets/action_icon.png'
import keys_img from '../assets/keys.png'
import exe_img from '../assets/exe_icon.png'
import system_com_img from '../assets/system_com_icon.png'


function ActionLib({ }) {


  return (
        <div className="h-[42vmax]  w-full bg-white border-t-2 border-gray-300 -mt-[6vmax] flex flex-col shadow-[0px_-2px_8px_rgba(0,0,0,0.25)]">
            <div className="h-[6vmax] w-full flex items-center justify-between py-[1.2vmax] px-[2vmax] border-b-2 border-gray-300">
                <div className="h-full flex items-center">
                    <img src={action_img} className="h-full mr-[1vmax]"/>
                    <p class="text-[2vmax] font-semibold">Библиотека действий</p>
                </div>
                <input
                   type="text"
                   placeholder="Поиск..."
                   className="h-full text-[1.7vmax] p-[1.5vmax] border border-[rgb(6,207,249)] rounded-lg focus:outline-none focus:ring-1 focus:ring-[rgb(6,207,249)]"
                />

            </div>

            <div className="flex-1 min-h-0 flex pr-[2vmax]">
                <div className="h-full w-1/3 flex flex-col">
                      <div className="h-[3vmax] w-full flex items-center px-[2vmax] my-[2vmax]">
                            <img src={keys_img} className="h-full"/>
                            <p class="text-[1.6vmax] font-semibold pl-[2vmax]">Клавиши <br /> / Сочетания клавиш</p>
                      </div>

                     <div className="h-full flex flex-col overflow-y-auto pt-[0.5vmax] pl-[2vmax] pr-[1vmax]">
                            <ActionCard/>

                     </div>
                </div>

                 <div className="h-full w-1/3 flex flex-col">
                      <div className="h-[3vmax] w-full flex items-center px-[2vmax] my-[2vmax]">
                            <img src={exe_img} className="h-full"/>
                            <p class="text-[1.7vmax] font-semibold pl-[2vmax]">Открытие программ</p>
                      </div>

                     <div className="h-full flex flex-col overflow-y-auto pt-[0.5vmax] pl-[2vmax] pr-[1vmax]">
                         <ActionCard/>

                     </div>
                </div>

                <div className="h-full w-1/3 flex flex-col">
                      <div className="h-[3vmax] w-full flex items-center px-[2vmax] my-[2vmax]">
                            <img src={system_com_img} className="h-full"/>
                            <p class="text-[1.6vmax] font-semibold pl-[2vmax]">Мышь <br /> / Системные команды</p>
                      </div>

                     <div className="h-full flex flex-col overflow-y-auto pt-[0.5vmax] pl-[2vmax] pr-[1vmax]">
                         <ActionCard/>

                     </div>
                </div>
            </div>
        </div>
  )
}

export default ActionLib