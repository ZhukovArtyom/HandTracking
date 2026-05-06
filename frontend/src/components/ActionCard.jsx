// ActionCard.jsx
import React from 'react';

function ActionCard({ command, icon }) {

  return (
    <div className="min-h-[5vmax] h-auto bg-white mb-[1vmax] p-[0.5vmax] flex-shrink-0 rounded-xl shadow-[2px_2px_8px_rgba(0,0,0,0.25)] flex items-center cursor-pointer hover:shadow-[4px_4px_12px_rgba(0,0,0,0.3)] transition-all">
        {icon ? (
            <img src={icon} className="h-[4vmax] aspect-[1/1] ml-[1vmax] bg-black p-[0.5vmax] "/>
          ) : (
            <div className="h-[4vmax] ml-[1vmax] aspect-[1/1] rounded-full"></div>
          )}
        <p className="h-full w-full ml-[1vmax] py-[1vmax] text-[1.7vmax] font-semibold flex items-center ">
          {command}
        </p>
    </div>
  );
}

export default ActionCard;