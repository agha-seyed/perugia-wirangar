import { useState } from 'react';
import { Box, Typography, TextField, IconButton, Paper, Chip, Avatar, CircularProgress } from '@mui/material';
import { Send, SmartToy, Person, AutoAwesome } from '@mui/icons-material';

interface ChatMessage {
  id: string;
  sender: 'user' | 'ai';
  text: string;
  time: string;
}

export default function AIChatView() {
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: '1',
      sender: 'ai',
      text: 'درود! 🇮🇹 من دستیار هوشمند و تخصصی دانشجویان پروجا هستم.\nدرباره بورسیه استانی ADiSU، نحوه اخذ کدیچه فیسکاله، پرمسو دی سوجورنو (اقامت)، سلف دانشگاه (Mensa)، ثبت‌نام یا اجاره خانه هر سوالی دارید بفرمایید!',
      time: 'هم‌اکنون'
    }
  ]);

  const quickPrompts = [
    'شرایط و مبلغ بورسیه ADiSU پروجا؟',
    'مراحل دریافت Codice Fiscale؟',
    'مدارک لازم برای پرمسو دی سوجورنو؟',
    'آدرس سلف دانشگاه و خوابگاه‌ها؟',
    'نحوه افتتاح حساب بانکی در ایتالیا؟'
  ];

  const handleSend = async (textToSend?: string) => {
    const query = textToSend || input;
    if (!query.trim()) return;

    const userMsg: ChatMessage = {
      id: Date.now().toString(),
      sender: 'user',
      text: query,
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };

    setMessages((prev) => [...prev, userMsg]);
    setInput('');
    setLoading(true);

    try {
      // Build history for backend AI
      const historyPayload = messages.slice(-6).map((m) => ({
        role: m.sender === 'user' ? 'user' : 'assistant',
        content: m.text
      }));

      const response = await fetch('/api/v1/webapp/ai/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: query,
          history: historyPayload
        })
      });

      if (response.ok) {
        const data = await response.json();
        if (data && data.text) {
          const aiMsg: ChatMessage = {
            id: (Date.now() + 1).toString(),
            sender: 'ai',
            text: data.text,
            time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
          };
          setMessages((prev) => [...prev, aiMsg]);
          setLoading(false);
          return;
        }
      }
    } catch (err) {
      console.warn('Backend AI API fallback:', err);
    }

    // پاسخ هوشمند پشتیبان در صورت آفلاین بودن
    let reply = '';
    const q = query.toLowerCase();

    if (q.includes('بورسیه') || q.includes('adisu')) {
      reply = '💶 **بورسیه استانی ADiSU Umbria:**\n• مبلغ سالانه: تا حدود ۷,۰۰۰ یورو وجه نقد\n• خوابگاه رایگان دولتی در پروجا\n• روزانه ۲ وعده غذای گرم و رایگان در رستوران‌های Mensa\n• شرط مالی: عدد ISEE Parificato کمتر از ۲۵,۵۰۰ یورو\n• نکته: ثبت‌نام معمولاً از تیرماه (Luglio) آغاز می‌شود.';
    } else if (q.includes('کدیچه') || q.includes('codice')) {
      reply = '🏛 **کد مالیاتی (Codice Fiscale):**\n• برای اجاره خانه، سیم‌کارت و افتتاح حساب ضروری است.\n• مکان در پروجا: اداره Agenzia delle Entrate در خیابان Via Mario Angeloni\n• مدارک: اصل پاسپورت + کپی صفحه اول و ویزا\n• هزینه: کاملاً رایگان و صدور در همان لحظه!';
    } else if (q.includes('پرمسو') || q.includes('اقامت') || q.includes('soggiorno')) {
      reply = '🛂 **پرمسو دی سوجورنو (Permesso di Soggiorno):**\n• مهلت: ظرف حداکثر ۸ روز کاری پس از ورود به خاک ایتالیا\n• دریافت کیت پستی زرد (Kit Postale) از باجه‌های Poste Italiane (پست مرکزی در میدان Piazza Matteotti یا Fontivegge)\n• مدارک: کپی پاسپورت، کپی بیمه، کپی گواهی ثبت‌نام یا پذیرش دانشگاه، تمبر مارکا دا بولو ۱۶ یورویی.';
    } else if (q.includes('سلف') || q.includes('mensa')) {
      reply = '🍝 **سلف‌های غذاخوری (Mensa Universitari):**\n۱. سلف مرکزی Via Pascoli (نزدیک مرکز تاریخی و خوابگاه‌های اصلی)\n۲. سلف مهندسی در منطقه Ingegneria / San Sisto\n• برای بورسیه‌ها کاملاً رایگان است و منوی روزانه شامل پاستا، گوشت، سالاد و دسر تازه ایتالیایی است.';
    } else if (q.includes('بانک') || q.includes('حساب')) {
      reply = '💳 **افتتاح حساب بانکی:**\nدانشجویان پروجا معمولاً از کارت‌های زیر استفاده می‌کنند:\n• کارت Revolut یا N26 (آنلاین و فوری)\n• حساب PostePay Evolution در اداره پست\n• حساب دانشجویی بانک Intesa Sanpaolo (رایگان تا سن ۳۵ سالگی).';
    } else {
      reply = `پاسخ به سوال «${query}»:\nدانشگاه دولتی پروجا (UniPG) با بیش از ۷۰۰ سال قدمت، خدمات کاملی به دانشجویان بین‌المللی ارائه می‌دهد. برای جزئیات پرونده اختصاصی، می‌توانید از منوی هوش مصنوعی و دکمه مشاوره ربات تلگرام نیز استفاده نمایید.`;
    }

    const aiMsg: ChatMessage = {
      id: (Date.now() + 1).toString(),
      sender: 'ai',
      text: reply,
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };
    setMessages((prev) => [...prev, aiMsg]);
    setLoading(false);
  };

  return (
    <Box sx={{ p: 2, pb: 11, width: '100%', maxWidth: 540, mx: 'auto', display: 'flex', flexDirection: 'column', height: 'calc(100vh - 120px)', dir: 'rtl' }}>
      
      {/* Header */}
      <Box sx={{ textAlign: 'center', mb: 2 }}>
        <Typography
          variant="h5"
          sx={{
            fontWeight: 900,
            background: 'linear-gradient(135deg, #FFF099 0%, #FFD700 45%, #02C39A 100%)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
            filter: 'drop-shadow(0 2px 8px rgba(255, 215, 0, 0.3))',
            mb: 0.3
          }}
        >
          🤖 دستیار هوشمند دانشجویی پروجا
        </Typography>
        <Typography variant="caption" sx={{ color: '#94D2BD', fontSize: '0.78rem' }}>
          پاسخ آنی به قوانین ویزا، بورسیه ADiSU، دانشگاه و اقامت ۲۰۲۵-۲۰۲۶
        </Typography>
      </Box>

      {/* Quick Prompts Chips */}
      <Box sx={{ display: 'flex', gap: 1, overflowX: 'auto', pb: 1, mb: 2 }}>
        {quickPrompts.map((p, i) => (
          <Chip
            key={i}
            icon={<AutoAwesome sx={{ fontSize: '13px !important', color: '#FFD700 !important' }} />}
            label={p}
            onClick={() => handleSend(p)}
            sx={{
              background: 'rgba(7, 39, 35, 0.85)',
              border: '1px solid rgba(255, 215, 0, 0.25)',
              color: '#F0FDF4',
              fontSize: '0.75rem',
              fontWeight: 600,
              cursor: 'pointer',
              boxShadow: '0 2px 8px rgba(0,0,0,0.3)',
              '&:hover': {
                background: 'rgba(184, 0, 79, 0.3)',
                borderColor: '#FFD700'
              }
            }}
          />
        ))}
      </Box>

      {/* Messages Feed */}
      <Paper sx={{
        flexGrow: 1,
        overflowY: 'auto',
        p: 2,
        borderRadius: 4,
        background: 'linear-gradient(180deg, rgba(7, 39, 35, 0.8) 0%, rgba(3, 23, 21, 0.95) 100%)',
        backdropFilter: 'blur(16px)',
        border: '1px solid rgba(255, 215, 0, 0.2)',
        display: 'flex',
        flexDirection: 'column',
        gap: 1.5,
        mb: 2,
        boxShadow: '0 8px 32px rgba(0,0,0,0.45)'
      }}>
        {messages.map((m) => (
          <Box
            key={m.id}
            sx={{
              display: 'flex',
              justifyContent: m.sender === 'user' ? 'flex-end' : 'flex-start',
              gap: 1,
              alignItems: 'flex-start'
            }}
          >
            {m.sender === 'ai' && (
              <Avatar sx={{
                bgcolor: 'rgba(0, 168, 150, 0.25)',
                border: '1px solid #FFD700',
                color: '#FFD700',
                width: 34,
                height: 34
              }}>
                <SmartToy sx={{ fontSize: 18 }} />
              </Avatar>
            )}

            <Box sx={{
              maxWidth: '82%',
              p: 1.8,
              borderRadius: 3.5,
              background: m.sender === 'user'
                ? 'linear-gradient(135deg, #B8004F 0%, #720026 100%)'
                : 'linear-gradient(135deg, rgba(7, 45, 40, 0.95) 0%, rgba(3, 25, 22, 0.95) 100%)',
              color: '#FFFFFF',
              border: m.sender === 'user'
                ? '1px solid rgba(255, 215, 0, 0.3)'
                : '1px solid rgba(0, 168, 150, 0.35)',
              boxShadow: m.sender === 'user'
                ? '0 4px 14px rgba(184, 0, 79, 0.35)'
                : '0 4px 14px rgba(0, 168, 150, 0.2)'
            }}>
              <Typography variant="body2" sx={{ lineHeight: 1.7, whiteSpace: 'pre-line', fontSize: '0.85rem' }}>
                {m.text}
              </Typography>
              <Typography variant="caption" sx={{
                display: 'block',
                textAlign: m.sender === 'user' ? 'left' : 'right',
                mt: 0.5,
                color: '#FFD700',
                opacity: 0.8,
                fontSize: '0.65rem'
              }}>
                {m.time}
              </Typography>
            </Box>

            {m.sender === 'user' && (
              <Avatar sx={{
                bgcolor: '#B8004F',
                border: '1px solid #FFD700',
                color: '#FFFFFF',
                width: 34,
                height: 34
              }}>
                <Person sx={{ fontSize: 18 }} />
              </Avatar>
            )}
          </Box>
        ))}

        {loading && (
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, color: '#FFD700', p: 1 }}>
            <CircularProgress size={16} sx={{ color: '#FFD700' }} />
            <Typography variant="caption" sx={{ color: '#94D2BD' }}>
              دستیار هوشمند در حال تحلیل و آماده‌سازی پاسخ...
            </Typography>
          </Box>
        )}
      </Paper>

      {/* Input Row */}
      <Box sx={{ display: 'flex', gap: 1 }}>
        <TextField
          fullWidth
          size="small"
          placeholder="سوالی درباره پروجا، دانشگاه یا ویزا بپرسید..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSend()}
          sx={{
            '& .MuiOutlinedInput-root': {
              borderRadius: 3.5,
              background: 'rgba(7, 39, 35, 0.75)',
              backdropFilter: 'blur(10px)',
              color: '#F0FDF4',
              '& fieldset': { borderColor: 'rgba(255, 215, 0, 0.25)' },
              '&:hover fieldset': { borderColor: '#FFD700' },
              '&.Mui-focused fieldset': { borderColor: '#02C39A' }
            }
          }}
        />
        <IconButton
          onClick={() => handleSend()}
          sx={{
            background: 'linear-gradient(135deg, #B8004F 0%, #800020 100%)',
            border: '1px solid #FFD700',
            color: '#FFD700',
            borderRadius: 3,
            p: 1.2,
            boxShadow: '0 4px 12px rgba(184, 0, 79, 0.4)',
            '&:hover': {
              background: 'linear-gradient(135deg, #E60067 0%, #B8004F 100%)',
              boxShadow: '0 6px 16px rgba(255, 215, 0, 0.4)'
            }
          }}
        >
          <Send sx={{ transform: 'rotate(180deg)' }} />
        </IconButton>
      </Box>
    </Box>
  );
}
