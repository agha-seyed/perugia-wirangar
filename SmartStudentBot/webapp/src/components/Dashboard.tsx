import { useState } from 'react';
import { Box, Typography, Card, Divider, Chip, ButtonBase } from '@mui/material';
import {
  Cloud,
  Person,
  Forum,
  Calculate,
  LocationOn,
  Storefront,
  Article,
  Event,
  HeadsetMic,
  Code,
  Memory,
  Terminal,
  AutoFixHigh,
  Stars,
  School
} from '@mui/icons-material';
import { motion, AnimatePresence } from 'framer-motion';

const translations = {
  fa: {
    title: "اسمارت پروجا",
    subtitle: "سامانه یکپارچه و هوشمند زندگی دانشجویی در ایتالیا",
    quickAccess: "دسترسی سریع به امکانات",
    aboutUs: "توسعه‌یافته توسط گروه ویرانگران (Wirangaran)",
    aboutText: "پیشرو در طراحی سیستم‌های نوین، هوش مصنوعی و اتوماسیون دانشجویی. ما با ادغام نوآوری و هنر، تجربه زندگی دانشجویی در ایتالیا را متحول می‌سازیم.",
    menus: {
      weather: 'آب‌وهوا',
      roommate: 'هم‌اتاقی',
      ai: 'دستیار هوش مصنوعی',
      isee: 'محاسبه ایزه (ISEE)',
      places: 'مکان‌یاب پروجا',
      market: 'بازارچه دانشجویی',
      news: 'اخبار دانشگاه',
      events: 'رویدادها و تورها',
      consult: 'مشاوره و پشتیبانی'
    },
    skills: ['توسعه هوشمند', 'الگوریتم‌های پیشرفته', 'معماری مدرن', 'پشتیبانی دانشجویی']
  },
  en: {
    title: "Smart Perugia",
    subtitle: "The Integrated Smart Platform for Student Life in Italy",
    quickAccess: "Quick Access",
    aboutUs: "Developed by Wirangaran Group",
    aboutText: "Pioneering smart software, artificial intelligence and modern student automation. Bridging cutting-edge technology with seamless university life.",
    menus: {
      weather: 'Weather',
      roommate: 'Roommate',
      ai: 'AI Assistant',
      isee: 'ISEE Calculator',
      places: 'Perugia Places',
      market: 'Student Market',
      news: 'UniPG News',
      events: 'Events & Tours',
      consult: 'Consultation & Support'
    },
    skills: ['Software Dev', 'Artificial Intelligence', 'Smart Systems', 'Student Support']
  },
  it: {
    title: "Smart Perugia",
    subtitle: "La Piattaforma Intelligente per la Vita Studentesca a Perugia",
    quickAccess: "Accesso Rapido",
    aboutUs: "Sviluppato dal Gruppo Wirangaran",
    aboutText: "Leader nella creazione di sistemi intelligenti, intelligenza artificiale e innovazione accademica.",
    menus: {
      weather: 'Meteo',
      roommate: 'Coinquilino',
      ai: 'Assistente AI',
      isee: 'Calcolo ISEE',
      places: 'Luoghi Perugia',
      market: 'Mercatino',
      news: 'Notizie UniPG',
      events: 'Eventi & Tour',
      consult: 'Supporto & Guida'
    },
    skills: ['Sviluppo Software', 'Intelligenza Artificiale', 'Sistemi Smart', 'Supporto Studenti']
  }
};

type LangKey = 'fa' | 'en' | 'it';

interface DashboardProps {
  onNavigate?: (tabIndex: number) => void;
}

export default function Dashboard({ onNavigate }: DashboardProps) {
  const [lang, setLang] = useState<LangKey>('fa');
  const t = translations[lang];
  const isRtl = lang === 'fa';

  const menuItems = [
    { id: 'isee', icon: <Calculate sx={{ fontSize: 36 }} />, color: '#FFD700', bg: 'rgba(255, 215, 0, 0.12)' },
    { id: 'ai', icon: <Forum sx={{ fontSize: 36 }} />, color: '#02C39A', bg: 'rgba(2, 195, 154, 0.12)' },
    { id: 'roommate', icon: <Person sx={{ fontSize: 36 }} />, color: '#B8004F', bg: 'rgba(184, 0, 79, 0.14)' },
    { id: 'weather', icon: <Cloud sx={{ fontSize: 36 }} />, color: '#00A896', bg: 'rgba(0, 168, 150, 0.12)' },
    { id: 'places', icon: <LocationOn sx={{ fontSize: 36 }} />, color: '#E63946', bg: 'rgba(230, 57, 70, 0.12)' },
    { id: 'market', icon: <Storefront sx={{ fontSize: 36 }} />, color: '#FFB703', bg: 'rgba(255, 183, 3, 0.12)' },
    { id: 'news', icon: <Article sx={{ fontSize: 36 }} />, color: '#94D2BD', bg: 'rgba(148, 210, 189, 0.12)' },
    { id: 'events', icon: <Event sx={{ fontSize: 36 }} />, color: '#FFD700', bg: 'rgba(255, 215, 0, 0.12)' },
    { id: 'consult', icon: <HeadsetMic sx={{ fontSize: 36 }} />, color: '#E60067', bg: 'rgba(230, 0, 103, 0.12)' }
  ];

  const handleItemClick = (id: string) => {
    if (id === 'roommate') onNavigate?.(1);
    else if (id === 'ai') onNavigate?.(2);
    else if (id === 'weather') onNavigate?.(3);
    else if (id === 'isee') {
      alert('🧮 محاسبه هوشمند ISEE:\nبرای دریافت گزارش جامع عددی و کارنامه تخمین بورسیه، لطفاً از دستور /start و منوی محاسبه ISEE در تلگرام استفاده کنید.');
    } else {
      alert(`✨ بخش «${(t.menus as any)[id]}» آماده خدمات‌رسانی در ربات هوشمند شماست.`);
    }
  };

  return (
    <Box sx={{ p: 2, overflow: 'hidden', display: 'flex', flexDirection: 'column', alignItems: 'center', dir: isRtl ? 'rtl' : 'ltr' }}>
      
      {/* Royal Language Selector */}
      <Box sx={{ display: 'flex', gap: 1, width: '100%', justifyContent: 'flex-end', mb: 2 }}>
        {(['fa', 'en', 'it'] as LangKey[]).map((l) => (
          <ButtonBase 
            key={l}
            onClick={() => setLang(l)}
            sx={{ 
              color: lang === l ? '#FFD700' : '#70A9A1', 
              fontWeight: 800, 
              fontSize: '0.85rem',
              px: 1.5,
              py: 0.5,
              borderRadius: '20px',
              border: lang === l ? '1px solid #FFD700' : '1px solid rgba(255, 215, 0, 0.15)',
              background: lang === l ? 'rgba(184, 0, 79, 0.4)' : 'rgba(7, 39, 35, 0.5)',
              boxShadow: lang === l ? '0 0 10px rgba(255, 215, 0, 0.3)' : 'none',
              textTransform: 'uppercase',
              transition: 'all 0.25s ease'
            }}
          >
            {l === 'fa' ? 'فارسی' : l === 'en' ? 'EN' : 'IT'}
          </ButtonBase>
        ))}
      </Box>

      {/* Hero Section: Grifo di Perugia with Teal, Crimson & Gold Glow */}
      <Box sx={{ width: '100%', display: 'flex', flexDirection: 'column', alignItems: 'center', mb: 4 }}>
        
        {/* Animated Royal Crest / Grifo Symbol */}
        <Box sx={{ position: 'relative', width: 170, height: 170, mb: 2, display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
          {/* Crimson & Peacock Ambient Aura */}
          <Box sx={{
            position: 'absolute', width: 130, height: 130,
            background: 'radial-gradient(circle, rgba(184,0,79,0.35) 0%, rgba(0,168,150,0.3) 60%, transparent 100%)',
            borderRadius: '50%',
            filter: 'blur(35px)',
            animation: 'royalPulse 3s infinite alternate'
          }} />
          
          <svg viewBox="0 0 100 100" width="100%" height="100%" style={{ filter: 'drop-shadow(0 0 12px rgba(255, 215, 0, 0.5))' }}>
            <defs>
              <linearGradient id="royalGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stopColor="#FFD700" />
                <stop offset="45%" stopColor="#B8004F" />
                <stop offset="100%" stopColor="#02C39A" />
              </linearGradient>
            </defs>
            <motion.path
              d="M 50 15 L 45 25 C 30 20 15 35 25 50 C 15 60 20 80 40 75 L 45 90 L 55 90 L 60 75 C 80 80 85 60 75 50 C 85 35 70 20 55 25 Z"
              fill="rgba(7, 39, 35, 0.4)"
              stroke="url(#royalGradient)"
              strokeWidth="2.2"
              initial={{ pathLength: 0, opacity: 0 }}
              animate={{ pathLength: 1, opacity: 1 }}
              transition={{ duration: 3.5, repeat: Infinity, repeatType: "reverse", ease: "easeInOut" }}
            />
            {/* Wing Details */}
            <motion.path
              d="M 40 40 Q 20 30 25 15 Q 40 25 50 35 M 60 40 Q 80 30 75 15 Q 60 25 50 35"
              fill="none"
              stroke="#FFD700"
              strokeWidth="1.6"
              initial={{ pathLength: 0 }}
              animate={{ pathLength: 1 }}
              transition={{ duration: 2.5, repeat: Infinity, repeatType: "reverse", ease: "easeInOut", delay: 0.8 }}
            />
          </svg>
        </Box>

        <Box sx={{ zIndex: 2, textAlign: 'center', px: 2 }}>
          <motion.div key={lang} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }}>
            <Typography variant="h4" sx={{
              fontWeight: 900,
              mb: 0.5,
              background: 'linear-gradient(135deg, #FFF099 0%, #FFD700 45%, #02C39A 100%)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
              filter: 'drop-shadow(0 2px 10px rgba(255, 215, 0, 0.3))'
            }}>
              {t.title}
            </Typography>
            <Typography variant="body2" sx={{ color: '#94D2BD', fontWeight: 400, maxWidth: 360, mx: 'auto', lineHeight: 1.6 }}>
              {t.subtitle}
            </Typography>
          </motion.div>
        </Box>
      </Box>

      {/* Quick Highlights / Stats Ribbon */}
      <Box sx={{
        display: 'flex',
        gap: 1.5,
        width: '100%',
        maxWidth: 480,
        mb: 3.5,
        p: 1.5,
        borderRadius: 4,
        background: 'linear-gradient(135deg, rgba(184, 0, 79, 0.18) 0%, rgba(0, 168, 150, 0.18) 100%)',
        border: '1px solid rgba(255, 215, 0, 0.25)',
        backdropFilter: 'blur(10px)',
        justifyContent: 'space-around',
        textAlign: 'center'
      }}>
        <Box>
          <Typography variant="caption" sx={{ color: '#FFD700', fontWeight: 'bold', display: 'block' }}>
            بورسیه ADiSU
          </Typography>
          <Typography variant="body2" sx={{ color: '#FFFFFF', fontWeight: 800 }}>
            ۷,۰۰۰€ + خوابگاه
          </Typography>
        </Box>
        <Divider orientation="vertical" flexItem sx={{ borderColor: 'rgba(255, 215, 0, 0.2)' }} />
        <Box>
          <Typography variant="caption" sx={{ color: '#02C39A', fontWeight: 'bold', display: 'block' }}>
            دانشگاه پروجا
          </Typography>
          <Typography variant="body2" sx={{ color: '#FFFFFF', fontWeight: 800 }}>
            UniPG • ۱۳۰۸ م.
          </Typography>
        </Box>
        <Divider orientation="vertical" flexItem sx={{ borderColor: 'rgba(255, 215, 0, 0.2)' }} />
        <Box>
          <Typography variant="caption" sx={{ color: '#E60067', fontWeight: 'bold', display: 'block' }}>
            پشتیبانی ۲۴/۷
          </Typography>
          <Typography variant="body2" sx={{ color: '#FFFFFF', fontWeight: 800 }}>
            ویرانگران
          </Typography>
        </Box>
      </Box>

      {/* Section Title */}
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2.5, width: '100%', maxWidth: 480 }}>
        <Stars sx={{ color: '#FFD700', fontSize: 20 }} />
        <Typography variant="subtitle1" sx={{ fontWeight: 800, color: '#FFD700', letterSpacing: '0.3px' }}>
          {t.quickAccess}
        </Typography>
      </Box>

      {/* Grid of Menus - 3 columns for rich app feel */}
      <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 1.5, width: '100%', maxWidth: 480 }} dir={isRtl ? 'rtl' : 'ltr'}>
        <AnimatePresence>
          {menuItems.map((item, index) => (
            <motion.div 
              key={item.id + lang}
              initial={{ opacity: 0, scale: 0.9, y: 15 }} 
              animate={{ opacity: 1, scale: 1, y: 0 }} 
              transition={{ duration: 0.35, delay: index * 0.04 }}
              whileHover={{ scale: 1.04 }}
              whileTap={{ scale: 0.95 }}
            >
              <Card 
                elevation={0}
                onClick={() => handleItemClick(item.id)}
                sx={{ 
                  background: `linear-gradient(160deg, ${item.bg} 0%, rgba(7, 39, 35, 0.7) 100%)`,
                  backdropFilter: 'blur(14px)',
                  border: `1px solid rgba(255, 215, 0, 0.16)`,
                  borderRadius: 4,
                  textAlign: 'center',
                  cursor: 'pointer',
                  p: 1.5,
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  justifyContent: 'center',
                  minHeight: 105,
                  boxShadow: `0 6px 16px rgba(0,0,0,0.35)`,
                  transition: 'all 0.25s ease',
                  '&:hover': {
                    borderColor: '#FFD700',
                    boxShadow: `0 0 20px rgba(255, 215, 0, 0.3), inset 0 0 10px ${item.bg}`,
                  }
                }}
              >
                <Box sx={{
                  color: item.color,
                  mb: 1,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  filter: `drop-shadow(0 0 8px ${item.color})`
                }}>
                  {item.icon}
                </Box>
                <Typography variant="caption" sx={{
                  fontWeight: 700,
                  color: '#FFFFFF',
                  fontSize: '0.78rem',
                  lineHeight: 1.3,
                  textAlign: 'center'
                }}>
                  {(t.menus as any)[item.id]}
                </Typography>
              </Card>
            </motion.div>
          ))}
        </AnimatePresence>
      </Box>

      {/* About Us Section - Royal Wirangaran Card */}
      <Box sx={{ mt: 5, mb: 3, width: '100%', maxWidth: 480 }} dir={isRtl ? 'rtl' : 'ltr'}>
        <motion.div key={lang + 'about'} initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }}>
          <Box sx={{ 
            background: 'linear-gradient(145deg, rgba(7, 39, 35, 0.9) 0%, rgba(4, 25, 22, 0.95) 100%)', 
            backdropFilter: 'blur(16px)',
            borderRadius: 5, 
            p: 3, 
            border: '1px solid rgba(255, 215, 0, 0.25)',
            position: 'relative',
            overflow: 'hidden',
            textAlign: 'center',
            boxShadow: '0 10px 30px rgba(0,0,0,0.5), inset 0 1px 0 rgba(255, 215, 0, 0.2)'
          }}>
            <Box sx={{
              position: 'absolute',
              right: '50%',
              top: '50%',
              transform: 'translate(50%, -50%) scale(5)',
              opacity: 0.03,
              color: '#FFD700'
            }}>
              <Terminal />
            </Box>
            
            <Typography variant="h6" sx={{
              color: '#FFD700',
              fontWeight: 900,
              mb: 1,
              letterSpacing: '0.5px'
            }}>
              {t.aboutUs}
            </Typography>
            <Typography variant="body2" sx={{ color: '#94D2BD', mb: 2.5, lineHeight: 1.7, fontSize: '0.85rem' }}>
              {t.aboutText}
            </Typography>

            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, justifyContent: 'center' }}>
              <Chip
                icon={<Code sx={{ fontSize: '1rem !important', color: '#02C39A !important' }} />}
                label={t.skills[0]}
                sx={{ color: '#F0FDF4', borderColor: 'rgba(0, 168, 150, 0.4)', background: 'rgba(0, 168, 150, 0.15)', fontSize: '0.75rem' }}
                variant="outlined"
              />
              <Chip
                icon={<AutoFixHigh sx={{ fontSize: '1rem !important', color: '#FFD700 !important' }} />}
                label={t.skills[1]}
                sx={{ color: '#F0FDF4', borderColor: 'rgba(255, 215, 0, 0.3)', background: 'rgba(255, 215, 0, 0.12)', fontSize: '0.75rem' }}
                variant="outlined"
              />
              <Chip
                icon={<Memory sx={{ fontSize: '1rem !important', color: '#B8004F !important' }} />}
                label={t.skills[2]}
                sx={{ color: '#F0FDF4', borderColor: 'rgba(184, 0, 79, 0.4)', background: 'rgba(184, 0, 79, 0.15)', fontSize: '0.75rem' }}
                variant="outlined"
              />
              <Chip
                icon={<School sx={{ fontSize: '1rem !important', color: '#00A896 !important' }} />}
                label={t.skills[3]}
                sx={{ color: '#F0FDF4', borderColor: 'rgba(0, 168, 150, 0.4)', background: 'rgba(0, 168, 150, 0.15)', fontSize: '0.75rem' }}
                variant="outlined"
              />
            </Box>
          </Box>
        </motion.div>
      </Box>

      <Box sx={{ height: 20 }} />
      <style>{`
        @keyframes royalPulse {
          from { transform: scale(0.9); opacity: 0.2; }
          to { transform: scale(1.15); opacity: 0.45; }
        }
      `}</style>
    </Box>
  );
}
