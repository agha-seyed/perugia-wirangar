'use client';

import React, { useRef, useState, useEffect } from 'react';
import { motion, useMotionValue, useSpring, useTransform } from 'framer-motion';

interface HoverCardProps {
  title: string;
  description: string;
  buttonText: string;
  icon: React.ReactNode;
  themeColor: string; // Tailwind color name like 'cyan-400' or hex like '#00ffff'
  glowColor: string; // rgba string like 'rgba(0, 255, 255, 0.4)'
  onClick?: () => void;
  index: number;
  slideFrom?: 'left' | 'right' | 'bottom';
}

export default function HoverCard({
  title,
  description,
  buttonText,
  icon,
  themeColor,
  glowColor,
  onClick,
  index,
  slideFrom = 'bottom'
}: HoverCardProps) {
  const cardRef = useRef<HTMLDivElement>(null);
  
  // Spotlight state
  const mouseX = useMotionValue(0);
  const mouseY = useMotionValue(0);

  // Tilt state
  const x = useMotionValue(0);
  const y = useMotionValue(0);

  const mouseXSpring = useSpring(x);
  const mouseYSpring = useSpring(y);

  const rotateX = useTransform(mouseYSpring, [-0.5, 0.5], ["10deg", "-10deg"]);
  const rotateY = useTransform(mouseXSpring, [-0.5, 0.5], ["-10deg", "10deg"]);

  const [isHovered, setIsHovered] = useState(false);

  const triggerHaptic = (style: 'light' | 'medium' | 'heavy' | 'rigid' | 'soft') => {
    if (typeof window !== 'undefined' && (window as any).Telegram && (window as any).Telegram.WebApp && (window as any).Telegram.WebApp.HapticFeedback) {
      (window as any).Telegram.WebApp.HapticFeedback.impactOccurred(style);
    }
  };

  const handleMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!cardRef.current) return;
    const rect = cardRef.current.getBoundingClientRect();
    
    // Spotlight coordinates (relative to card)
    mouseX.set(e.clientX - rect.left);
    mouseY.set(e.clientY - rect.top);

    // Tilt calculations (-0.5 to 0.5)
    const width = rect.width;
    const height = rect.height;
    const mouseXRel = (e.clientX - rect.left) / width - 0.5;
    const mouseYRel = (e.clientY - rect.top) / height - 0.5;
    
    x.set(mouseXRel);
    y.set(mouseYRel);
  };

  const handleMouseEnter = () => {
    setIsHovered(true);
    triggerHaptic('light');
  };

  const handleMouseLeave = () => {
    setIsHovered(false);
    x.set(0);
    y.set(0);
  };

  const handleClick = () => {
    triggerHaptic('heavy');
    if (onClick) onClick();
  };

  const initialX = slideFrom === 'left' ? -150 : slideFrom === 'right' ? 150 : 0;
  const initialY = slideFrom === 'bottom' ? 100 : 0;

  const cardVariants = {
    hidden: { 
      opacity: 0, 
      x: initialX, 
      y: initialY,
      transition: { 
        duration: 0.4, 
        ease: "easeOut" as const
      } 
    },
    visible: { 
      opacity: 1, 
      x: 0, 
      y: 0,
      transition: { 
        duration: 0.8, 
        delay: index * 0.15, 
        type: "spring" as const, 
        stiffness: 80, 
        damping: 20 
      }
    }
  };

  return (
    <motion.div
      variants={cardVariants}
      initial="hidden"
      whileInView="visible"
      viewport={{ once: false, amount: 0.1 }}
      style={{
        perspective: 1000,
      }}
      className="w-full"
    >
      <motion.div
        ref={cardRef}
        onMouseMove={handleMouseMove}
        onMouseEnter={handleMouseEnter}
        onMouseLeave={handleMouseLeave}
        style={{
          rotateX,
          rotateY,
          transformStyle: "preserve-3d",
        }}
        className={`relative h-full w-full glass-panel p-6 rounded-2xl border border-white/10 transition-all duration-300 bg-black/40 backdrop-blur-xl overflow-hidden cursor-pointer group`}
        onClick={handleClick}
      >
        {/* Spotlight Effect Layer */}
        <motion.div
          className="pointer-events-none absolute -inset-px rounded-2xl opacity-0 transition duration-300 group-hover:opacity-100"
          style={{
            background: `radial-gradient(400px circle at ${mouseX}px ${mouseY}px, ${glowColor}, transparent 40%)`,
          }}
        />

        {/* Content Container (lifted slightly in 3D) */}
        <div style={{ transform: "translateZ(30px)", transformStyle: "preserve-3d" }} className="relative z-10 flex flex-col h-full">
          
          {/* Header & Icon */}
          <div className="flex items-center gap-4 mb-4">
            <div 
              className="p-3 rounded-xl border border-white/10 shadow-lg"
              style={{ backgroundColor: isHovered ? glowColor.replace('0.4', '0.2') : 'rgba(255,255,255,0.05)', transition: 'background-color 0.3s' }}
            >
              <div style={{ color: themeColor, textShadow: isHovered ? `0 0 10px ${themeColor}` : 'none' }}>
                {icon}
              </div>
            </div>
            <h3 
              className="text-2xl font-bold transition-colors duration-300"
              style={{ color: isHovered ? themeColor : '#fff' }}
            >
              {title}
            </h3>
          </div>

          <p className="text-sm text-gray-300 mb-6 flex-grow leading-relaxed">
            {description}
          </p>

          <button 
            className="px-4 py-3 font-bold rounded-xl w-full transition-all duration-300 border relative overflow-hidden group/btn"
            style={{ 
              borderColor: isHovered ? themeColor : 'rgba(255,255,255,0.2)',
              color: isHovered ? '#000' : themeColor,
            }}
          >
            <div 
              className="absolute inset-0 transition-opacity duration-300"
              style={{ backgroundColor: themeColor, opacity: isHovered ? 1 : 0.1 }}
            />
            <span className="relative z-10">{buttonText}</span>
          </button>
        </div>
      </motion.div>
    </motion.div>
  );
}
