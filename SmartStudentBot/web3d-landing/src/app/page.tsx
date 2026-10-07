'use client';

import React, { useState, useEffect } from 'react';
import dynamic from 'next/dynamic';
import { 
  Calculator, 
  Bot, 
  Headset, 
  UtensilsCrossed, 
  MapPin, 
  CloudSun, 
  Users, 
  ShoppingBag, 
  Newspaper 
} from 'lucide-react';
import HoverCard from '@/components/HoverCard';
import FloatingOrbs from '@/components/FloatingOrbs';
import LanguageSwitcher from '@/components/LanguageSwitcher';
import { translations, Language } from '@/i18n/translations';

const Scene3D = dynamic(() => import('@/components/Scene3D'), {
  ssr: false,
  loading: () => <div className="fixed top-0 left-0 w-full h-full -z-10 bg-[#050505]" />
});

export default function Home() {
  const [lang, setLang] = useState<Language>('fa');
  const t = translations[lang];

  useEffect(() => {
    if (typeof window !== 'undefined' && (window as any).Telegram && (window as any).Telegram.WebApp) {
      const tg = (window as any).Telegram.WebApp;
      tg.ready();
      tg.expand();
      
      // Set theme color to match our cyberpunk vibe
      try {
        tg.setHeaderColor('#050505');
        tg.setBackgroundColor('#050505');
      } catch (e) {
        console.warn('Telegram setHeaderColor not supported on this client');
      }

      // Test backend connection with initData
      const initData = tg.initData || '';
      if (initData) {
        fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/webapp/me`, {
          headers: {
            'X-Telegram-Init-Data': initData
          }
        })
        .then(res => res.json())
        .then(data => console.log('Backend Auth Data:', data))
        .catch(err => console.error('Backend Auth Error:', err));
      }
    }
  }, []); // Run once on mount

  // Update theme based on lang if needed, though mostly handled by LanguageSwitcher
  const dir = lang === 'fa' ? 'rtl' : 'ltr';

  // Map icons and colors to our features array from dictionary
  const featuresConfig = [
    { icon: <Calculator size={40} />, themeColor: "#facc15", glowColor: "rgba(250, 204, 21, 0.4)", action: "isee" },
    { icon: <Bot size={40} />, themeColor: "#22d3ee", glowColor: "rgba(34, 211, 238, 0.4)", action: "ai" },
    { icon: <Headset size={40} />, themeColor: "#ffffff", glowColor: "rgba(255, 255, 255, 0.3)", action: "consult" },
    { icon: <UtensilsCrossed size={40} />, themeColor: "#ef4444", glowColor: "rgba(239, 68, 68, 0.4)", action: "mensa" },
    { icon: <MapPin size={40} />, themeColor: "#fde047", glowColor: "rgba(253, 224, 71, 0.4)", action: "places" },
    { icon: <CloudSun size={40} />, themeColor: "#60a5fa", glowColor: "rgba(96, 165, 250, 0.4)", action: "weather" },
    { icon: <Users size={40} />, themeColor: "#ec4899", glowColor: "rgba(236, 72, 153, 0.4)", action: "roommate" },
    { icon: <ShoppingBag size={40} />, themeColor: "#a855f7", glowColor: "rgba(168, 85, 247, 0.4)", action: "market" },
    { icon: <Newspaper size={40} />, themeColor: "#4ade80", glowColor: "rgba(74, 222, 128, 0.4)", action: "news" }
  ];

  const handleFeatureClick = (actionName: string) => {
    if (typeof window !== 'undefined') {
      const tg = (window as any).Telegram?.WebApp;
      if (tg) {
        if (tg.HapticFeedback) {
          tg.HapticFeedback.impactOccurred('medium');
        }
        if (tg.openTelegramLink) {
          tg.openTelegramLink(`https://t.me/SmartStudentBot?start=${actionName}`);
          return;
        }
      }
      window.open(`https://t.me/SmartStudentBot?start=${actionName}`, '_blank');
    }
  };

  return (
    <main className="relative w-full overflow-x-hidden" dir={dir}>
      <LanguageSwitcher currentLang={lang} onLanguageChange={setLang} />
      
      {/* 3D Background Canvas */}
      <Scene3D />

      {/* Scrollable HTML Content Area */}
      <div id="scroll-container" className="relative w-full z-10 pb-32">
        
        {/* Hero Section */}
        <section className="min-h-screen w-full flex flex-col items-center justify-center text-center px-4 relative pb-20">
          <FloatingOrbs colors={['#00ffff', '#3b82f6', '#8b5cf6']} />
          <h1 className="text-6xl md:text-8xl font-black tracking-tighter uppercase text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-blue-600 mb-4 drop-shadow-[0_0_15px_rgba(0,255,255,0.5)]">
            {t.heroTitle}
          </h1>
          <p className="text-xl md:text-2xl font-light text-gray-300 max-w-2xl">
            {t.heroSubtitle}
          </p>
          <div className="absolute bottom-10 animate-bounce text-cyan-400">
            <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 14l-7 7m0 0l-7-7m7 7V3" />
            </svg>
          </div>
        </section>

        {/* Section 1: AI & Academic */}
        <section className="min-h-[150vh] w-full flex flex-col items-center justify-start px-4 md:px-16 py-32 relative">
          <FloatingOrbs colors={['#eab308', '#06b6d4', '#ffffff']} />
          <div className="w-full max-w-6xl relative z-10 flex flex-col items-center">
            
            <div className="w-full flex flex-col gap-24 mt-10">
              <div className={`w-full md:w-[60%] lg:w-[45%] ${dir === 'rtl' ? 'ms-auto' : 'me-auto'}`}>
                <HoverCard 
                  index={0}
                  slideFrom={dir === 'rtl' ? "right" : "left"}
                  title={t.features[0].title}
                  description={t.features[0].description}
                  buttonText={t.features[0].buttonText}
                  onClick={() => handleFeatureClick(featuresConfig[0].action)}
                  {...featuresConfig[0]}
                />
              </div>

              <div className="w-full md:w-[60%] lg:w-[45%] mx-auto">
                <HoverCard 
                  index={1}
                  slideFrom="bottom"
                  title={t.features[1].title}
                  description={t.features[1].description}
                  buttonText={t.features[1].buttonText}
                  onClick={() => handleFeatureClick(featuresConfig[1].action)}
                  {...featuresConfig[1]}
                />
              </div>

              <div className={`w-full md:w-[60%] lg:w-[45%] ${dir === 'rtl' ? 'me-auto' : 'ms-auto'}`}>
                <HoverCard 
                  index={2}
                  slideFrom={dir === 'rtl' ? "left" : "right"}
                  title={t.features[2].title}
                  description={t.features[2].description}
                  buttonText={t.features[2].buttonText}
                  onClick={() => handleFeatureClick(featuresConfig[2].action)}
                  {...featuresConfig[2]}
                />
              </div>
            </div>
          </div>
        </section>

        {/* Section 2: Campus & City */}
        <section className="min-h-[150vh] w-full flex flex-col items-center justify-start px-4 md:px-16 py-32 relative">
          <FloatingOrbs colors={['#ef4444', '#fde047', '#60a5fa']} />
          <div className="w-full max-w-6xl relative z-10 flex flex-col items-center">
            
            <div className="w-full flex flex-col gap-24 mt-10">
              <div className={`w-full md:w-[60%] lg:w-[45%] ${dir === 'rtl' ? 'ms-auto' : 'me-auto'}`}>
                <HoverCard 
                  index={0}
                  slideFrom={dir === 'rtl' ? "left" : "right"}
                  title={t.features[3].title}
                  description={t.features[3].description}
                  buttonText={t.features[3].buttonText}
                  onClick={() => handleFeatureClick(featuresConfig[3].action)}
                  {...featuresConfig[3]}
                />
              </div>

              <div className="w-full md:w-[60%] lg:w-[45%] mx-auto">
                <HoverCard 
                  index={1}
                  slideFrom="bottom"
                  title={t.features[4].title}
                  description={t.features[4].description}
                  buttonText={t.features[4].buttonText}
                  onClick={() => handleFeatureClick(featuresConfig[4].action)}
                  {...featuresConfig[4]}
                />
              </div>

              <div className={`w-full md:w-[60%] lg:w-[45%] ${dir === 'rtl' ? 'me-auto' : 'ms-auto'}`}>
                <HoverCard 
                  index={2}
                  slideFrom={dir === 'rtl' ? "right" : "left"}
                  title={t.features[5].title}
                  description={t.features[5].description}
                  buttonText={t.features[5].buttonText}
                  onClick={() => handleFeatureClick(featuresConfig[5].action)}
                  {...featuresConfig[5]}
                />
              </div>
            </div>
          </div>
        </section>

        {/* Section 3: Community */}
        <section className="min-h-[150vh] w-full flex flex-col items-center justify-start px-4 md:px-16 py-32 relative">
          <FloatingOrbs colors={['#ec4899', '#a855f7', '#4ade80']} />
          <div className="w-full max-w-6xl relative z-10 flex flex-col items-center">
            
            <div className="w-full flex flex-col gap-24 mt-10">
              <div className={`w-full md:w-[60%] lg:w-[45%] ${dir === 'rtl' ? 'me-auto' : 'ms-auto'}`}>
                <HoverCard 
                  index={0}
                  slideFrom={dir === 'rtl' ? "right" : "left"}
                  title={t.features[6].title}
                  description={t.features[6].description}
                  buttonText={t.features[6].buttonText}
                  onClick={() => handleFeatureClick(featuresConfig[6].action)}
                  {...featuresConfig[6]}
                />
              </div>

              <div className="w-full md:w-[60%] lg:w-[45%] mx-auto">
                <HoverCard 
                  index={1}
                  slideFrom="bottom"
                  title={t.features[7].title}
                  description={t.features[7].description}
                  buttonText={t.features[7].buttonText}
                  onClick={() => handleFeatureClick(featuresConfig[7].action)}
                  {...featuresConfig[7]}
                />
              </div>

              <div className={`w-full md:w-[60%] lg:w-[45%] ${dir === 'rtl' ? 'ms-auto' : 'me-auto'}`}>
                <HoverCard 
                  index={2}
                  slideFrom={dir === 'rtl' ? "left" : "right"}
                  title={t.features[8].title}
                  description={t.features[8].description}
                  buttonText={t.features[8].buttonText}
                  onClick={() => handleFeatureClick(featuresConfig[8].action)}
                  {...featuresConfig[8]}
                />
              </div>
            </div>
          </div>
        </section>

      </div>
    </main>
  );
}
