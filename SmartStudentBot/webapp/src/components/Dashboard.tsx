import { useState } from 'react';
import {
  Box,
  Typography,
  Card,
  CardContent,
  Divider,
  Chip,
  ButtonBase,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
  IconButton
} from '@mui/material';
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
  School,
  Close,
  OpenInNew,
  CheckCircle,
  AccountBalance,
  Apartment,
  AttachMoney,
  Info,
  DirectionsBike,
  Computer,
  MenuBook,
  LocalFireDepartment,
  Kitchen,
  ConfirmationNumber,
  Map,
  Campaign,
  SupportAgent
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

const modalTranslations = {
  fa: {
    iseeTitle: "🧮 شبیه‌ساز و محاسبه‌گر سریع ISEE Parificato",
    iseeDesc: "تخمین هوشمند عدد ایزه و ارزیابی شانس قبولی در بورسیه استانی ADiSU Umbria",
    familyMembers: "تعداد اعضای خانواده",
    annualIncome: "درآمد سالانه خانواده (€)",
    realEstate: "ارزش املاک و مستغلات (€)",
    financialAssets: "موجودی بانکی و دارایی مالی (€)",
    eligibleFull: "🎉 واجد شرایط بورسیه کامل استانی ADiSU (تا ۷۰۰۰ یورو + خوابگاه رایگان + غذای رایگان)",
    notEligible: "⚠️ بالاتر از سقف ۲۵,۵۰۰ یورو - مشمول تخفیف پلکانی شهریه دانشگاه UniPG",
    openInBot: "🚀 صدور کارنامه رسمی در ربات تلگرام",
    close: "بستن",
    marketTitle: "🛒 بازارچه دانشجویی پروجا",
    marketDesc: "خرید و فروش لوازم دست‌دوم، کتب و دوچرخه دانشجویی در پروجا",
    contactSeller: "پیام به فروشنده",
    postAdInBot: "➕ ثبت آگهی جدید در ربات تلگرام",
    eventsTitle: "🎉 رویدادها، تورها و دورهمی‌های دانشجویی",
    eventsDesc: "تورهای تفریحی، کارگاه‌های اداری و دورهمی‌های دانشجویان در پروجا",
    joinEventInBot: "🌟 هماهنگی و شرکت در ربات تلگرام",
    placesTitle: "📍 مکان‌های حیاتی و اداری پروجا",
    placesDesc: "آدرس و مسیریابی سریع به مراکز ضروری دانشجویی",
    openMap: "🗺 مسیریابی در نقشه",
    morePlacesInBot: "📍 راهنمای صوتی و لیست کامل در ربات",
    newsTitle: "📰 اخبار و اطلاعیه‌های رسمی UniPG",
    newsDesc: "آخرین اطلاعیه‌های بورسیه، دانشگاه و حمل‌ونقل شهری",
    openNewsInBot: "🔔 مشاهده اخبار کامل در ربات تلگرام",
    consultTitle: "💬 مشاوره تخصصی تحصیلی و امور اداری",
    consultDesc: "ثبت پرونده پذیرش، ویزا، بورسیه ADiSU و پرمسو با مشاوران با‌تجربه",
    startConsultInBot: "📝 شروع مشاوره در ربات تلگرام"
  },
  en: {
    iseeTitle: "🧮 Smart ISEE Parificato Calculator",
    iseeDesc: "Estimate your ISEE score and ADiSU Umbria scholarship eligibility",
    familyMembers: "Family Members Count",
    annualIncome: "Annual Family Income (€)",
    realEstate: "Real Estate Property Value (€)",
    financialAssets: "Bank Balance & Movable Assets (€)",
    eligibleFull: "🎉 Eligible for Full ADiSU Scholarship (~€7,000 + Free Housing + 2 Meals/day)",
    notEligible: "⚠️ Over €25,500 threshold - Eligible for tiered tuition reduction at UniPG",
    openInBot: "🚀 Get Official PDF Report in Telegram Bot",
    close: "Close",
    marketTitle: "🛒 Perugia Student Marketplace",
    marketDesc: "Second-hand student furniture, bikes, and textbooks in Perugia",
    contactSeller: "Message Seller",
    postAdInBot: "➕ Post New Ad in Telegram Bot",
    eventsTitle: "🎉 Student Events & Tours in Perugia",
    eventsDesc: "Tours, legal workshops, and international student meetups",
    joinEventInBot: "🌟 RSVP & Join in Telegram Bot",
    placesTitle: "📍 Essential Perugia Student Landmarks",
    placesDesc: "Directions and key info for administrative and university locations",
    openMap: "🗺 Navigate on Map",
    morePlacesInBot: "📍 Full Audio Guide & Locations in Bot",
    newsTitle: "📰 UniPG & Perugia Official News",
    newsDesc: "Latest updates on scholarships, exams, and urban transit",
    openNewsInBot: "🔔 Read Full Bulletins in Telegram Bot",
    consultTitle: "💬 University & Legal Consultation",
    consultDesc: "Guidance on admissions, visas, ADiSU scholarship, and residency permit",
    startConsultInBot: "📝 Start Consultation in Telegram Bot"
  },
  it: {
    iseeTitle: "🧮 Calcolatore Rapido ISEE Parificato",
    iseeDesc: "Simula il valore del tuo ISEE e verifica i requisiti per la borsa ADiSU Umbria",
    familyMembers: "Numero Componenti Nucleo Familiare",
    annualIncome: "Reddito Familiare Annuo (€)",
    realEstate: "Valore Patrimonio Immobiliare (€)",
    financialAssets: "Saldo Patrimonio Mobiliare (€)",
    eligibleFull: "🎉 Idoneo Borsa ADiSU Completa (fino a 7.000€ + Alloggio Gratuito + Mensa)",
    notEligible: "⚠️ Supera la soglia di 25.500€ - Idoneo a riduzione parziale tasse UniPG",
    openInBot: "🚀 Richiedi Report Ufficiale nel Bot Telegram",
    close: "Chiudi",
    marketTitle: "🛒 Mercatino Studentesco di Perugia",
    marketDesc: "Compravendita di libri, biciclette e arredi usati a Perugia",
    contactSeller: "Contatta Venditore",
    postAdInBot: "➕ Pubblica Annuncio nel Bot Telegram",
    eventsTitle: "🎉 Eventi, Tour e Incontri a Perugia",
    eventsDesc: "Gite culturali, workshop burocratici e feste universitarie",
    joinEventInBot: "🌟 Partecipa nel Bot Telegram",
    placesTitle: "📍 Punti Chiave per Studenti a Perugia",
    placesDesc: "Indirizzi e mappe per questura, mense universitarie e uffici ADiSU",
    openMap: "🗺 Apri su Google Maps",
    morePlacesInBot: "📍 Guida Completa dei Luoghi nel Bot",
    newsTitle: "📰 Notizie Ufficiali UniPG & Trasporti",
    newsDesc: "Avvisi su scadenze borse di studio e aggiornamenti cittadini",
    openNewsInBot: "🔔 Leggi Notizie nel Bot Telegram",
    consultTitle: "💬 Consulenza e Assistenza Studenti",
    consultDesc: "Supporto su immatricolazione, visto, borsa di studio e permesso di soggiorno",
    startConsultInBot: "📝 Avvia Consulenza nel Bot Telegram"
  }
};

type LangKey = 'fa' | 'en' | 'it';

interface DashboardProps {
  onNavigate?: (tabIndex: number) => void;
}

export default function Dashboard({ onNavigate }: DashboardProps) {
  const [lang, setLang] = useState<LangKey>('fa');
  const [activeModal, setActiveModal] = useState<string | null>(null);

  // ISEE Calculator State
  const [familyMembers, setFamilyMembers] = useState<number>(4);
  const [annualIncome, setAnnualIncome] = useState<number>(8000);
  const [realEstate, setRealEstate] = useState<number>(0);
  const [financialAssets, setFinancialAssets] = useState<number>(1500);

  const t = translations[lang];
  const mt = modalTranslations[lang];
  const isRtl = lang === 'fa';

  // Real-time ISEE & ISPE calculation
  const getFamilyScale = (members: number) => {
    if (members <= 1) return 1.0;
    if (members === 2) return 1.57;
    if (members === 3) return 2.04;
    if (members === 4) return 2.46;
    if (members === 5) return 2.85;
    return 2.85 + (members - 5) * 0.35;
  };

  const scale = getFamilyScale(familyMembers);
  const iseeValue = Math.round((annualIncome + 0.2 * (realEstate + financialAssets)) / scale);
  const ispeValue = Math.round((realEstate + financialAssets) / scale);
  const isEligibleScholarship = iseeValue <= 25500 && ispeValue <= 55000;

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

  const handleAction = (actionId: string) => {
    const tg = (window as any).Telegram?.WebApp;
    if (tg) {
      if (tg.HapticFeedback) {
        tg.HapticFeedback.notificationOccurred('success');
      }
      try {
        tg.sendData(JSON.stringify({ action: actionId }));
      } catch (_) {}
      if (tg.openTelegramLink) {
        tg.openTelegramLink(`https://t.me/SmartStudentPerugiaBot?start=${actionId}`);
        return;
      }
    }
    window.open(`https://t.me/SmartStudentPerugiaBot?start=${actionId}`, '_blank');
  };

  const handleItemClick = (id: string) => {
    if (id === 'roommate') onNavigate?.(1);
    else if (id === 'ai') onNavigate?.(2);
    else if (id === 'weather') onNavigate?.(3);
    else {
      setActiveModal(id);
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

      {/* ═══════════════════════════════════════════════════════════════════════════ */}
      {/* 1. مودال محاسبه‌گر هوشمند ISEE */}
      {/* ═══════════════════════════════════════════════════════════════════════════ */}
      <Dialog
        open={activeModal === 'isee'}
        onClose={() => setActiveModal(null)}
        slotProps={{
          paper: {
            sx: {
              background: 'linear-gradient(145deg, #072723 0%, #031715 100%)',
              border: '1px solid rgba(255, 215, 0, 0.35)',
              borderRadius: 4,
              color: '#F0FDF4',
              maxWidth: 460,
              width: '95%',
              p: 1
            }
          }
        }}
      >
        <DialogTitle sx={{ color: '#FFD700', fontWeight: 900, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span>{mt.iseeTitle}</span>
          <IconButton onClick={() => setActiveModal(null)} sx={{ color: '#94D2BD' }} size="small">
            <Close />
          </IconButton>
        </DialogTitle>
        <DialogContent sx={{ display: 'flex', flexDirection: 'column', gap: 2, pt: 1 }}>
          <Typography variant="body2" sx={{ color: '#94D2BD', fontSize: '0.82rem', lineHeight: 1.6 }}>
            {mt.iseeDesc}
          </Typography>

          <TextField
            label={mt.familyMembers}
            type="number"
            size="small"
            value={familyMembers}
            onChange={(e) => setFamilyMembers(Math.max(1, Number(e.target.value)))}
            slotProps={{ inputLabel: { sx: { color: '#94D2BD' } } }}
            sx={{ '& .MuiOutlinedInput-root': { color: '#fff', '& fieldset': { borderColor: 'rgba(0,168,150,0.4)' } } }}
          />
          <TextField
            label={mt.annualIncome}
            type="number"
            size="small"
            value={annualIncome}
            onChange={(e) => setAnnualIncome(Math.max(0, Number(e.target.value)))}
            slotProps={{ inputLabel: { sx: { color: '#94D2BD' } } }}
            sx={{ '& .MuiOutlinedInput-root': { color: '#fff', '& fieldset': { borderColor: 'rgba(0,168,150,0.4)' } } }}
          />
          <TextField
            label={mt.realEstate}
            type="number"
            size="small"
            value={realEstate}
            onChange={(e) => setRealEstate(Math.max(0, Number(e.target.value)))}
            slotProps={{ inputLabel: { sx: { color: '#94D2BD' } } }}
            sx={{ '& .MuiOutlinedInput-root': { color: '#fff', '& fieldset': { borderColor: 'rgba(0,168,150,0.4)' } } }}
          />
          <TextField
            label={mt.financialAssets}
            type="number"
            size="small"
            value={financialAssets}
            onChange={(e) => setFinancialAssets(Math.max(0, Number(e.target.value)))}
            slotProps={{ inputLabel: { sx: { color: '#94D2BD' } } }}
            sx={{ '& .MuiOutlinedInput-root': { color: '#fff', '& fieldset': { borderColor: 'rgba(0,168,150,0.4)' } } }}
          />

          {/* نتایج محاسبه آنی */}
          <Box sx={{
            background: 'rgba(7, 39, 35, 0.75)',
            border: '1px solid #FFD700',
            borderRadius: 3,
            p: 2,
            mt: 1,
            boxShadow: '0 4px 15px rgba(0,0,0,0.4)'
          }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
              <Typography variant="body2" sx={{ color: '#94D2BD' }}>ISEE Parificato:</Typography>
              <Typography variant="subtitle2" sx={{ color: '#FFD700', fontWeight: 900 }}>
                {iseeValue.toLocaleString()} €
              </Typography>
            </Box>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
              <Typography variant="body2" sx={{ color: '#94D2BD' }}>ISPE:</Typography>
              <Typography variant="subtitle2" sx={{ color: '#02C39A', fontWeight: 900 }}>
                {ispeValue.toLocaleString()} €
              </Typography>
            </Box>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1.5 }}>
              <Typography variant="body2" sx={{ color: '#94D2BD' }}>Scala di Equivalenza:</Typography>
              <Typography variant="subtitle2" sx={{ color: '#FFFFFF', fontWeight: 800 }}>
                {scale.toFixed(2)}
              </Typography>
            </Box>
            <Divider sx={{ borderColor: 'rgba(255, 215, 0, 0.2)', mb: 1.5 }} />
            <Typography variant="caption" sx={{
              color: isEligibleScholarship ? '#02C39A' : '#FFB703',
              fontWeight: 800,
              display: 'block',
              lineHeight: 1.5
            }}>
              {isEligibleScholarship ? mt.eligibleFull : mt.notEligible}
            </Typography>
          </Box>
        </DialogContent>
        <DialogActions sx={{ p: 2, justifyContent: 'space-between' }}>
          <Button onClick={() => setActiveModal(null)} sx={{ color: '#94D2BD' }}>
            {mt.close}
          </Button>
          <Button
            variant="contained"
            onClick={() => handleAction('isee')}
            startIcon={<OpenInNew />}
            sx={{
              background: 'linear-gradient(135deg, #B8004F 0%, #6E002B 100%)',
              color: '#FFD700',
              fontWeight: 800,
              border: '1px solid #FFD700'
            }}
          >
            {mt.openInBot}
          </Button>
        </DialogActions>
      </Dialog>

      {/* ═══════════════════════════════════════════════════════════════════════════ */}
      {/* 2. مودال بازارچه دانشجویی */}
      {/* ═══════════════════════════════════════════════════════════════════════════ */}
      <Dialog
        open={activeModal === 'market'}
        onClose={() => setActiveModal(null)}
        slotProps={{
          paper: {
            sx: {
              background: 'linear-gradient(145deg, #072723 0%, #031715 100%)',
              border: '1px solid rgba(255, 215, 0, 0.35)',
              borderRadius: 4,
              color: '#F0FDF4',
              maxWidth: 480,
              width: '95%',
              p: 1
            }
          }
        }}
      >
        <DialogTitle sx={{ color: '#FFD700', fontWeight: 900, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span>{mt.marketTitle}</span>
          <IconButton onClick={() => setActiveModal(null)} sx={{ color: '#94D2BD' }} size="small">
            <Close />
          </IconButton>
        </DialogTitle>
        <DialogContent sx={{ display: 'flex', flexDirection: 'column', gap: 1.5, pt: 1 }}>
          <Typography variant="body2" sx={{ color: '#94D2BD', fontSize: '0.82rem' }}>
            {mt.marketDesc}
          </Typography>

          {[
            { id: 1, title: 'دوچرخه شهری Perugia City Bike (۷ دنده)', price: 70, loc: 'Elce', contact: '@ali_perugia', icon: <DirectionsBike sx={{ color: '#02C39A' }} /> },
            { id: 2, title: 'مانیتور ۲۴ اینچ Dell IPS همراه کابل HDMI', price: 85, loc: 'Centro', contact: '@sara_student', icon: <Computer sx={{ color: '#FFD700' }} /> },
            { id: 3, title: 'پکیج کامل کتاب‌های ایتالیایی Nuovo Espresso', price: 30, loc: 'Fontivegge', contact: '@omid_pg', icon: <MenuBook sx={{ color: '#94D2BD' }} /> },
            { id: 4, title: 'هیتر برقی کم‌مصرف Delonghi', price: 20, loc: 'Elce', contact: '@perugia_reza', icon: <LocalFireDepartment sx={{ color: '#E63946' }} /> },
            { id: 5, title: 'سرویس ظروف تفال و قابلمه دانشجویی', price: 25, loc: 'Monteluce', contact: '@student_pg', icon: <Kitchen sx={{ color: '#FFB703' }} /> }
          ].map((item) => (
            <Box
              key={item.id}
              sx={{
                p: 1.5,
                borderRadius: 2.5,
                background: 'rgba(7, 39, 35, 0.6)',
                border: '1px solid rgba(255, 215, 0, 0.15)',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center'
              }}
            >
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                {item.icon}
                <Box>
                  <Typography variant="subtitle2" sx={{ color: '#FFFFFF', fontWeight: 800, fontSize: '0.85rem' }}>
                    {item.title}
                  </Typography>
                  <Typography variant="caption" sx={{ color: '#94D2BD' }}>
                    {item.loc} • تماس: {item.contact}
                  </Typography>
                </Box>
              </Box>
              <Box sx={{ textAlign: 'right' }}>
                <Typography variant="subtitle2" sx={{ color: '#FFD700', fontWeight: 900 }}>
                  {item.price} €
                </Typography>
                <Button
                  size="small"
                  onClick={() => {
                    const tg = (window as any).Telegram?.WebApp;
                    const u = item.contact.replace('@', '');
                    if (tg?.openTelegramLink) tg.openTelegramLink(`https://t.me/${u}`);
                    else window.open(`https://t.me/${u}`, '_blank');
                  }}
                  sx={{ color: '#02C39A', p: 0, minWidth: 'auto', fontSize: '0.72rem' }}
                >
                  {mt.contactSeller}
                </Button>
              </Box>
            </Box>
          ))}
        </DialogContent>
        <DialogActions sx={{ p: 2, justifyContent: 'space-between' }}>
          <Button onClick={() => setActiveModal(null)} sx={{ color: '#94D2BD' }}>
            {mt.close}
          </Button>
          <Button
            variant="contained"
            onClick={() => handleAction('market')}
            startIcon={<OpenInNew />}
            sx={{
              background: 'linear-gradient(135deg, #B8004F 0%, #6E002B 100%)',
              color: '#FFD700',
              fontWeight: 800,
              border: '1px solid #FFD700'
            }}
          >
            {mt.postAdInBot}
          </Button>
        </DialogActions>
      </Dialog>

      {/* ═══════════════════════════════════════════════════════════════════════════ */}
      {/* 3. مودال رویدادها و تورها */}
      {/* ═══════════════════════════════════════════════════════════════════════════ */}
      <Dialog
        open={activeModal === 'events'}
        onClose={() => setActiveModal(null)}
        slotProps={{
          paper: {
            sx: {
              background: 'linear-gradient(145deg, #072723 0%, #031715 100%)',
              border: '1px solid rgba(255, 215, 0, 0.35)',
              borderRadius: 4,
              color: '#F0FDF4',
              maxWidth: 480,
              width: '95%',
              p: 1
            }
          }
        }}
      >
        <DialogTitle sx={{ color: '#FFD700', fontWeight: 900, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span>{mt.eventsTitle}</span>
          <IconButton onClick={() => setActiveModal(null)} sx={{ color: '#94D2BD' }} size="small">
            <Close />
          </IconButton>
        </DialogTitle>
        <DialogContent sx={{ display: 'flex', flexDirection: 'column', gap: 1.5, pt: 1 }}>
          <Typography variant="body2" sx={{ color: '#94D2BD', fontSize: '0.82rem' }}>
            {mt.eventsDesc}
          </Typography>

          {[
            { id: 1, title: 'تور پاییزی دریاچه تراسیمنو و شهر باستانی آسیزی', date: 'شنبه آینده ساعت ۹:۰۰', loc: 'ایستگاه Fontivegge', tag: 'گردشگری' },
            { id: 2, title: 'دورهمی و عصرانه دانشجویان در Piazza IV Novembre', date: 'چهارشنبه ساعت ۱۹:۰۰', loc: 'میدان مرکزی پینچتو', tag: 'دورهمی' },
            { id: 3, title: 'کارگاه رایگان آموزش اخذ پرمسو و معافیت با CAF', date: 'یکشنبه ساعت ۱۷:۰۰', loc: 'آنلاین و حضوری', tag: 'اداری/حقوقی' },
            { id: 4, title: 'شب سینمای ایتالیایی در سینما PostModernissimo', date: 'دوشنبه ساعت ۲۰:۳۰', loc: 'مرکز تاریخی', tag: 'فرهنگی' }
          ].map((ev) => (
            <Box
              key={ev.id}
              sx={{
                p: 1.5,
                borderRadius: 2.5,
                background: 'rgba(7, 39, 35, 0.6)',
                border: '1px solid rgba(255, 215, 0, 0.15)',
                display: 'flex',
                flexDirection: 'column',
                gap: 0.5
              }}
            >
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Typography variant="subtitle2" sx={{ color: '#FFFFFF', fontWeight: 800 }}>
                  {ev.title}
                </Typography>
                <Chip size="small" label={ev.tag} sx={{ background: 'rgba(0,168,150,0.25)', color: '#02C39A', fontSize: '0.7rem' }} />
              </Box>
              <Typography variant="caption" sx={{ color: '#FFD700', fontWeight: 700 }}>
                📅 {ev.date} • 📍 {ev.loc}
              </Typography>
            </Box>
          ))}
        </DialogContent>
        <DialogActions sx={{ p: 2, justifyContent: 'space-between' }}>
          <Button onClick={() => setActiveModal(null)} sx={{ color: '#94D2BD' }}>
            {mt.close}
          </Button>
          <Button
            variant="contained"
            onClick={() => handleAction('events')}
            startIcon={<OpenInNew />}
            sx={{
              background: 'linear-gradient(135deg, #B8004F 0%, #6E002B 100%)',
              color: '#FFD700',
              fontWeight: 800,
              border: '1px solid #FFD700'
            }}
          >
            {mt.joinEventInBot}
          </Button>
        </DialogActions>
      </Dialog>

      {/* ═══════════════════════════════════════════════════════════════════════════ */}
      {/* 4. مودال مکان‌های مهم پروجا */}
      {/* ═══════════════════════════════════════════════════════════════════════════ */}
      <Dialog
        open={activeModal === 'places'}
        onClose={() => setActiveModal(null)}
        slotProps={{
          paper: {
            sx: {
              background: 'linear-gradient(145deg, #072723 0%, #031715 100%)',
              border: '1px solid rgba(255, 215, 0, 0.35)',
              borderRadius: 4,
              color: '#F0FDF4',
              maxWidth: 480,
              width: '95%',
              p: 1
            }
          }
        }}
      >
        <DialogTitle sx={{ color: '#FFD700', fontWeight: 900, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span>{mt.placesTitle}</span>
          <IconButton onClick={() => setActiveModal(null)} sx={{ color: '#94D2BD' }} size="small">
            <Close />
          </IconButton>
        </DialogTitle>
        <DialogContent sx={{ display: 'flex', flexDirection: 'column', gap: 1.5, pt: 1 }}>
          <Typography variant="body2" sx={{ color: '#94D2BD', fontSize: '0.82rem' }}>
            {mt.placesDesc}
          </Typography>

          {[
            { id: 1, name: 'Questura di Perugia (اداره پلیس مهاجرت)', addr: 'Via Emanuele Petri', map: 'https://maps.google.com/?q=Questura+di+Perugia', icon: <Apartment sx={{ color: '#02C39A' }} /> },
            { id: 2, name: 'Mensa Universitaria Via Pascoli (سلف مرکزی دانشگاه)', addr: 'Via Pascoli 23', map: 'https://maps.google.com/?q=Mensa+Universitaria+Perugia', icon: <Kitchen sx={{ color: '#FFD700' }} /> },
            { id: 3, name: 'ADiSU Umbria (ساختمان بورسیه و خوابگاه)', addr: 'Via Faina 8', map: 'https://maps.google.com/?q=ADiSU+Perugia', icon: <School sx={{ color: '#B8004F' }} /> },
            { id: 4, name: 'Stazione Perugia Fontivegge (ایستگاه اصلی قطار)', addr: 'Piazza Vittorio Veneto', map: 'https://maps.google.com/?q=Stazione+Perugia+Fontivegge', icon: <LocationOn sx={{ color: '#FFB703' }} /> },
            { id: 5, name: 'Minimetro Pincetto (مرکز تاریخی)', addr: 'Pincetto Centro Storico', map: 'https://maps.google.com/?q=Minimetro+Pincetto', icon: <Map sx={{ color: '#94D2BD' }} /> }
          ].map((place) => (
            <Box
              key={place.id}
              sx={{
                p: 1.5,
                borderRadius: 2.5,
                background: 'rgba(7, 39, 35, 0.6)',
                border: '1px solid rgba(255, 215, 0, 0.15)',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center'
              }}
            >
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                {place.icon}
                <Box>
                  <Typography variant="subtitle2" sx={{ color: '#FFFFFF', fontWeight: 800, fontSize: '0.85rem' }}>
                    {place.name}
                  </Typography>
                  <Typography variant="caption" sx={{ color: '#94D2BD' }}>
                    {place.addr}
                  </Typography>
                </Box>
              </Box>
              <Button
                size="small"
                variant="outlined"
                onClick={() => window.open(place.map, '_blank')}
                sx={{
                  borderColor: 'rgba(255, 215, 0, 0.4)',
                  color: '#FFD700',
                  fontSize: '0.72rem',
                  borderRadius: 2,
                  textTransform: 'none'
                }}
              >
                {mt.openMap}
              </Button>
            </Box>
          ))}
        </DialogContent>
        <DialogActions sx={{ p: 2, justifyContent: 'space-between' }}>
          <Button onClick={() => setActiveModal(null)} sx={{ color: '#94D2BD' }}>
            {mt.close}
          </Button>
          <Button
            variant="contained"
            onClick={() => handleAction('places')}
            startIcon={<OpenInNew />}
            sx={{
              background: 'linear-gradient(135deg, #B8004F 0%, #6E002B 100%)',
              color: '#FFD700',
              fontWeight: 800,
              border: '1px solid #FFD700'
            }}
          >
            {mt.morePlacesInBot}
          </Button>
        </DialogActions>
      </Dialog>

      {/* ═══════════════════════════════════════════════════════════════════════════ */}
      {/* 5. مودال اخبار دانشگاه و شهر */}
      {/* ═══════════════════════════════════════════════════════════════════════════ */}
      <Dialog
        open={activeModal === 'news'}
        onClose={() => setActiveModal(null)}
        slotProps={{
          paper: {
            sx: {
              background: 'linear-gradient(145deg, #072723 0%, #031715 100%)',
              border: '1px solid rgba(255, 215, 0, 0.35)',
              borderRadius: 4,
              color: '#F0FDF4',
              maxWidth: 480,
              width: '95%',
              p: 1
            }
          }
        }}
      >
        <DialogTitle sx={{ color: '#FFD700', fontWeight: 900, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span>{mt.newsTitle}</span>
          <IconButton onClick={() => setActiveModal(null)} sx={{ color: '#94D2BD' }} size="small">
            <Close />
          </IconButton>
        </DialogTitle>
        <DialogContent sx={{ display: 'flex', flexDirection: 'column', gap: 1.5, pt: 1 }}>
          <Typography variant="body2" sx={{ color: '#94D2BD', fontSize: '0.82rem' }}>
            {mt.newsDesc}
          </Typography>

          {[
            { id: 1, title: 'انتشار فراخوان بورسیه استانی ADiSU Umbria برای سال تحصیلی جدید', date: '۲ روز پیش', tag: 'بورسیه' },
            { id: 2, title: 'تمدید مهلت تخفیف اشتراک سالانه اتوبوس و مینی‌مترو دانشجویی', date: 'هفته گذشته', tag: 'حمل‌ونقل' },
            { id: 3, title: 'آغاز دوره‌های رایگان آموزش زبان ایتالیایی در مرکز زبان دانشگاه (CLA)', date: 'جدید', tag: 'آموزش' }
          ].map((n) => (
            <Box
              key={n.id}
              sx={{
                p: 1.5,
                borderRadius: 2.5,
                background: 'rgba(7, 39, 35, 0.6)',
                border: '1px solid rgba(255, 215, 0, 0.15)',
                display: 'flex',
                flexDirection: 'column',
                gap: 0.5
              }}
            >
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Typography variant="subtitle2" sx={{ color: '#FFFFFF', fontWeight: 800 }}>
                  {n.title}
                </Typography>
                <Chip size="small" label={n.tag} sx={{ background: 'rgba(184, 0, 79, 0.25)', color: '#FFD700', fontSize: '0.7rem' }} />
              </Box>
              <Typography variant="caption" sx={{ color: '#94D2BD' }}>
                {n.date}
              </Typography>
            </Box>
          ))}
        </DialogContent>
        <DialogActions sx={{ p: 2, justifyContent: 'space-between' }}>
          <Button onClick={() => setActiveModal(null)} sx={{ color: '#94D2BD' }}>
            {mt.close}
          </Button>
          <Button
            variant="contained"
            onClick={() => handleAction('news')}
            startIcon={<OpenInNew />}
            sx={{
              background: 'linear-gradient(135deg, #B8004F 0%, #6E002B 100%)',
              color: '#FFD700',
              fontWeight: 800,
              border: '1px solid #FFD700'
            }}
          >
            {mt.openNewsInBot}
          </Button>
        </DialogActions>
      </Dialog>

      {/* ═══════════════════════════════════════════════════════════════════════════ */}
      {/* 6. مودال مشاوره تخصصی */}
      {/* ═══════════════════════════════════════════════════════════════════════════ */}
      <Dialog
        open={activeModal === 'consult'}
        onClose={() => setActiveModal(null)}
        slotProps={{
          paper: {
            sx: {
              background: 'linear-gradient(145deg, #072723 0%, #031715 100%)',
              border: '1px solid rgba(255, 215, 0, 0.35)',
              borderRadius: 4,
              color: '#F0FDF4',
              maxWidth: 480,
              width: '95%',
              p: 1
            }
          }
        }}
      >
        <DialogTitle sx={{ color: '#FFD700', fontWeight: 900, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span>{mt.consultTitle}</span>
          <IconButton onClick={() => setActiveModal(null)} sx={{ color: '#94D2BD' }} size="small">
            <Close />
          </IconButton>
        </DialogTitle>
        <DialogContent sx={{ display: 'flex', flexDirection: 'column', gap: 1.5, pt: 1 }}>
          <Typography variant="body2" sx={{ color: '#94D2BD', fontSize: '0.82rem' }}>
            {mt.consultDesc}
          </Typography>

          {[
            { id: 1, title: '🎓 پذیرش دانشگاهی و پیش‌ثبت‌نام Universitaly', desc: 'بررسی مدارک تحصیلی، ترجمه، رزومه و مکاتبه با اساتید' },
            { id: 2, title: '💶 مدارک بورسیه استانی ADiSU و ISEE Parificato', desc: 'راهنمای آماده‌سازی فیش حقوقی، مدارک دارایی و تایید کنسولگری' },
            { id: 3, title: '🛂 ویزای تحصیلی و تمدید پرمسو (Permesso)', desc: 'تکمیل کیت زرد پستی، وقت انگشت‌نگاری و بیمه درمانی SSN' },
            { id: 4, title: '🏠 قرارداد اجاره، کد مالیاتی و حساب بانکی', desc: 'اخذ Codice Fiscale، ثبت قرارداد در آژانس مالیاتی و کارت بانکی' }
          ].map((item) => (
            <Box
              key={item.id}
              sx={{
                p: 1.5,
                borderRadius: 2.5,
                background: 'rgba(7, 39, 35, 0.6)',
                border: '1px solid rgba(255, 215, 0, 0.15)',
                display: 'flex',
                flexDirection: 'column',
                gap: 0.5
              }}
            >
              <Typography variant="subtitle2" sx={{ color: '#FFFFFF', fontWeight: 800 }}>
                {item.title}
              </Typography>
              <Typography variant="caption" sx={{ color: '#94D2BD', lineHeight: 1.5 }}>
                {item.desc}
              </Typography>
            </Box>
          ))}
        </DialogContent>
        <DialogActions sx={{ p: 2, justifyContent: 'space-between' }}>
          <Button onClick={() => setActiveModal(null)} sx={{ color: '#94D2BD' }}>
            {mt.close}
          </Button>
          <Button
            variant="contained"
            onClick={() => handleAction('consult')}
            startIcon={<OpenInNew />}
            sx={{
              background: 'linear-gradient(135deg, #B8004F 0%, #6E002B 100%)',
              color: '#FFD700',
              fontWeight: 800,
              border: '1px solid #FFD700'
            }}
          >
            {mt.startConsultInBot}
          </Button>
        </DialogActions>
      </Dialog>

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
