import React, { useState } from 'react'

import settings_img from '../assets/settings_icon.png'
import plus_img from '../assets/plus_icon.png'
import hand_blue_bg_img from '../assets/hand_blue_bg.png'

function NewGestureMenu({ }) {


  return (

      <div class="h-[44vmax] w-full pl-[2vmax]">

           <div class="w-full h-full bg-white rounded-xl shadow-[2px_2px_8px_rgba(0,0,0,0.25)] flex flex-col">
                <div class="w-full h-[5vmax] border-b-2 border-gray-300 flex items-center">
                    <div class="h-4/10 flex items-center ml-3">
                      <img src={plus_img} class="h-full m-[1vmax]" alt="config" />
                      <p class="text-[2vmax]">Создание нового жеста</p>
                    </div>
                  </div>

                  <div class="h-[33.5vmax] m-[1vmax]">

                      <div class="h-3/10 flex items-center pb-[1.5vmax]">
                            <img class="h-full aspect-[1/1] bg-gray-500 rounded-full"/>
                            <button class="h-1/2 px-[3vmax] ml-[2vmax] text-[1.7vmax] bg-[rgb(6,207,249)] rounded-xl text-white">
                                    Записать жест
                            </button>

                      </div>

                      <div class="h-3/10 flex flex-col justify-between pb-[1.5vmax]">
                            <div class="h-1/4 flex items-center">
                              <img src={hand_blue_bg_img} class="h-full" alt="config" />
                              <p class="text-[2vmax] pl-[1vmax]">Имя жеста</p>
                            </div>

                            <p class="h-3/5 text-[1.7vmax] pl-[1vmax] border-1 border-gray-300 rounded-xl flex items-center">
                                Действие

                            </p>
                      </div>

                      <div class="h-3/10 flex flex-col justify-between pb-[1.5vmax]">
                            <div class="h-1/4 flex items-center">
                              <img src={settings_img} class="h-full" alt="config" />
                              <p class="text-[2vmax] pl-[1vmax]">Действие</p>
                            </div>

                            <p class="h-3/5 text-[1.7vmax] pl-[1vmax] border-1 border-gray-300 rounded-xl flex items-center">
                                Действие
                            </p>

                      </div>

                      <div class="h-1/10 flex justify-between">
                            <button class="h-full w-1/2 text-[1.7vmax] bg-[rgb(6,207,249)] rounded-xl text-white ">
                                    Сохранить
                            </button>

                            <button class="h-full w-1/2 text-[1.7vmax] ml-[1.5vmax] border-2 border-[rgb(6,207,249)] rounded-xl text-[rgb(6,207,249)]">
                                    Отменить
                            </button>

                      </div>

                </div>

           </div>

        </div>

  )
}

export default NewGestureMenu