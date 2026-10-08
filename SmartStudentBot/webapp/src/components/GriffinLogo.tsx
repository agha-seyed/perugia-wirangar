import React from 'react';
import { Box } from '@mui/material';
import { motion } from 'framer-motion';

interface GriffinLogoProps {
  size?: number;
  showShield?: boolean;
  animated?: boolean;
}

export default function GriffinLogo({ size = 110, showShield = true, animated = true }: GriffinLogoProps) {
  return (
    <Box
      sx={{
        width: size,
        height: size,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        position: 'relative',
        filter: 'drop-shadow(0 0 14px rgba(255, 215, 0, 0.45))',
      }}
    >
      <svg
        viewBox="0 0 200 200"
        width="100%"
        height="100%"
        style={{ overflow: 'visible' }}
      >
        <defs>
          {/* Gradients */}
          <linearGradient id="shieldGrad" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#9E003A" />
            <stop offset="50%" stopColor="#670024" />
            <stop offset="100%" stopColor="#2A000E" />
          </linearGradient>

          <linearGradient id="goldCrownGrad" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#FFF2A3" />
            <stop offset="50%" stopColor="#FFD700" />
            <stop offset="100%" stopColor="#D4A017" />
          </linearGradient>

          <linearGradient id="griffinBodyGrad" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#FFFFFF" />
            <stop offset="40%" stopColor="#F4FBF7" />
            <stop offset="80%" stopColor="#D8F3DC" />
            <stop offset="100%" stopColor="#94D2BD" />
          </linearGradient>

          <linearGradient id="wingGoldGrad" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#FFF7B2" />
            <stop offset="50%" stopColor="#FFD700" />
            <stop offset="100%" stopColor="#02C39A" />
          </linearGradient>

          <radialGradient id="auraGlow" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="rgba(255, 215, 0, 0.4)" />
            <stop offset="70%" stopColor="rgba(184, 0, 79, 0.15)" />
            <stop offset="100%" stopColor="transparent" />
          </radialGradient>
        </defs>

        {/* Outer Glow */}
        <circle cx="100" cy="100" r="92" fill="url(#auraGlow)" />

        {/* Historic Perugia Shield (Stemma di Perugia) */}
        {showShield && (
          <g>
            <path
              d="M 100 12 C 145 12 175 18 175 60 C 175 125 135 168 100 188 C 65 168 25 125 25 60 C 25 18 55 12 100 12 Z"
              fill="url(#shieldGrad)"
              stroke="#FFD700"
              strokeWidth="3.5"
              strokeLinejoin="round"
            />
            {/* Inner Shield Gold Inset Border */}
            <path
              d="M 100 20 C 138 20 165 25 165 62 C 165 118 130 156 100 174 C 70 156 35 118 35 62 C 35 25 62 20 100 20 Z"
              fill="none"
              stroke="rgba(255, 215, 0, 0.35)"
              strokeWidth="1.5"
            />
          </g>
        )}

        {/* ═══ THE GRIFFIN OF PERUGIA (Il Grifone Rampante) ═══ */}
        <g transform="translate(10, 8)">
          {/* Royal Ducal Crown (Corona Reale di Perugia) */}
          <path
            d="M 72 28 L 76 38 L 84 32 L 88 42 L 96 32 L 100 42 L 108 32 L 112 38 L 116 28 L 110 48 L 78 48 Z"
            fill="url(#goldCrownGrad)"
            stroke="#996515"
            strokeWidth="0.8"
          />
          <circle cx="74" cy="28" r="2.2" fill="#FFD700" />
          <circle cx="86" cy="31" r="2.2" fill="#FFD700" />
          <circle cx="98" cy="31" r="2.2" fill="#FFD700" />
          <circle cx="114" cy="28" r="2.2" fill="#FFD700" />

          {/* Griffin Head & Eagle Beak */}
          <path
            d="M 80 46 C 75 48 70 52 64 54 C 60 55 57 58 54 62 C 60 63 68 64 72 61 C 70 65 67 67 62 70 C 69 70 76 68 81 63 C 83 67 87 72 90 77 L 96 74 C 94 68 93 62 94 56 C 94 50 88 47 80 46 Z"
            fill="url(#griffinBodyGrad)"
            stroke="#C0C0C0"
            strokeWidth="0.8"
          />
          {/* Sharp Beak Tip (Hooked Gold Eagle Beak) */}
          <path
            d="M 64 54 C 58 56 52 62 50 67 C 54 67 58 65 62 62 Z"
            fill="#FFD700"
            stroke="#B8860B"
            strokeWidth="0.8"
          />
          {/* Piercing Eye */}
          <circle cx="76" cy="53" r="2" fill="#B8004F" />
          <circle cx="76.5" cy="52.5" r="0.7" fill="#FFFFFF" />

          {/* Outspread Majestic Wings (Ali del Grifone) */}
          <motion.path
            d="M 92 60 C 104 42 120 28 142 22 C 146 32 143 45 134 54 C 145 46 154 36 158 48 C 152 56 142 63 131 68 C 142 62 149 56 150 66 C 144 73 133 78 122 81 C 132 77 140 73 139 82 C 131 88 120 90 108 90 L 98 75 Z"
            fill="url(#wingGoldGrad)"
            stroke="#FFD700"
            strokeWidth="1.2"
            animate={animated ? {
              rotate: [0, 2, 0, -1.5, 0],
              transformOrigin: "98px 75px"
            } : {}}
            transition={{ duration: 4, repeat: Infinity, ease: "easeInOut" }}
          />

          {/* Wing Feathers Inner Details */}
          <path
            d="M 104 56 Q 125 40 138 32 M 106 66 Q 126 54 140 50 M 108 76 Q 124 67 136 67 M 106 84 Q 118 78 128 80"
            fill="none"
            stroke="rgba(255, 255, 255, 0.7)"
            strokeWidth="1"
          />

          {/* Rampant Torso & Muscular Chest */}
          <path
            d="M 88 72 C 84 80 82 92 84 104 C 85 110 88 116 88 124 C 84 126 78 120 74 114 C 70 108 72 98 74 90 C 76 82 82 76 88 72 Z"
            fill="url(#griffinBodyGrad)"
            stroke="#B0C4DE"
            strokeWidth="0.8"
          />

          {/* Raised Front Paws (Claws / Zampe Anteriori Rampanti) */}
          {/* Upper Claw */}
          <path
            d="M 84 76 L 72 70 L 60 72 L 54 69 L 52 73 L 58 75 L 53 79 L 57 82 L 64 78 L 74 84 L 84 84 Z"
            fill="url(#goldCrownGrad)"
            stroke="#996515"
            strokeWidth="0.8"
          />
          {/* Lower Front Claw */}
          <path
            d="M 82 88 L 68 88 L 58 92 L 53 90 L 52 94 L 57 96 L 53 100 L 58 102 L 66 98 L 76 98 Z"
            fill="url(#goldCrownGrad)"
            stroke="#996515"
            strokeWidth="0.8"
          />

          {/* Hind Legs (Lion Legs / Zampe Posteriori da Leone) */}
          <path
            d="M 86 118 C 94 124 102 132 100 144 C 98 152 90 156 82 158 C 76 159 70 154 74 148 C 78 144 82 140 84 134 L 82 125 Z"
            fill="url(#griffinBodyGrad)"
            stroke="#B0C4DE"
            strokeWidth="0.8"
          />
          {/* Claws of Hind Foot */}
          <path
            d="M 82 158 L 76 163 L 70 162 L 73 158 L 78 155 Z"
            fill="#FFD700"
          />

          {/* Majestic Lion Tail (Coda di Leone Fiammeggiante) */}
          <motion.path
            d="M 96 122 C 108 126 122 124 128 112 C 132 102 126 94 118 96 C 112 98 112 106 118 108 C 122 109 124 104 122 102 M 122 96 C 128 92 134 94 136 100 C 138 106 132 114 124 116"
            fill="none"
            stroke="#FFD700"
            strokeWidth="3.2"
            strokeLinecap="round"
            animate={animated ? {
              scale: [1, 1.05, 0.98, 1],
            } : {}}
            transition={{ duration: 3, repeat: Infinity, ease: "easeInOut" }}
          />
          {/* Tuft of Tail (Fiocco della Coda) */}
          <path
            d="M 120 95 C 126 88 136 88 138 98 C 134 98 130 94 124 96 Z"
            fill="#B8004F"
          />
        </g>
      </svg>
    </Box>
  );
}
