'use client';

import React from 'react';
import { motion } from 'framer-motion';

interface FloatingOrbsProps {
  colors: string[];
}

export default function FloatingOrbs({ colors }: FloatingOrbsProps) {
  // We'll render exactly 3 orbs for atmospheric effect
  return (
    <div className="absolute inset-0 overflow-hidden pointer-events-none -z-10">
      {colors.map((color, i) => {
        // Vary the position and animation for each orb
        const size = i === 0 ? 'w-96 h-96' : i === 1 ? 'w-64 h-64' : 'w-80 h-80';
        const position = 
          i === 0 ? 'top-[-10%] left-[-10%]' : 
          i === 1 ? 'bottom-[10%] right-[-5%]' : 
          'top-[40%] left-[50%]';
        
        return (
          <motion.div
            key={i}
            className={`absolute rounded-full opacity-20 blur-[100px] ${size} ${position}`}
            style={{ backgroundColor: color }}
            animate={{
              y: [0, -30, 0],
              x: [0, 20, 0],
              scale: [1, 1.1, 1]
            }}
            transition={{
              duration: 8 + i * 2,
              repeat: Infinity,
              repeatType: "reverse",
              ease: "easeInOut",
              delay: i * 1.5
            }}
          />
        );
      })}
    </div>
  );
}
