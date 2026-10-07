import { useState } from 'react';
import { Box, Typography, Card, CardContent, Grid, Chip } from '@mui/material';
import { WbSunny, Cloud, Air, WaterDrop, Shield, Terrain, Hiking } from '@mui/icons-material';

export default function WeatherView() {
  const [hourly] = useState([
    { time: '12:00', temp: 22, icon: <WbSunny sx={{ color: '#FFD700' }} /> },
    { time: '15:00', temp: 24, icon: <WbSunny sx={{ color: '#FFD700' }} /> },
    { time: '18:00', temp: 19, icon: <Cloud sx={{ color: '#02C39A' }} /> },
    { time: '21:00', temp: 16, icon: <Cloud sx={{ color: '#02C39A' }} /> },
    { time: '00:00', temp: 13, icon: <Cloud sx={{ color: '#94D2BD' }} /> }
  ]);

  return (
    <Box sx={{ p: 2, pb: 11, width: '100%', maxWidth: 540, mx: 'auto', dir: 'rtl' }}>
      
      {/* Title */}
      <Box sx={{ textAlign: 'center', mb: 2.5 }}>
        <Typography
          variant="h5"
          sx={{
            fontWeight: 900,
            background: 'linear-gradient(135deg, #FFF099 0%, #FFD700 45%, #02C39A 100%)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
            filter: 'drop-shadow(0 2px 8px rgba(255, 215, 0, 0.3))',
            mb: 0.5
          }}
        >
          🌤️ آب‌وهوای هوشمند پروجا
        </Typography>
        <Typography variant="body2" sx={{ color: '#94D2BD', fontSize: '0.82rem' }}>
          پیش‌بینی وضع جوی با توجه به شرایط کوهپایه‌ای و تپه‌های تاریخی اومبریا
        </Typography>
      </Box>

      {/* کارت اصلی آب‌وهوا با تم سلطنتی کله‌غازی و طلایی */}
      <Card sx={{
        background: 'linear-gradient(145deg, rgba(7, 39, 35, 0.9) 0%, rgba(4, 25, 22, 0.98) 100%)',
        backdropFilter: 'blur(16px)',
        border: '1px solid rgba(255, 215, 0, 0.3)',
        borderRadius: 4,
        textAlign: 'center',
        p: 3,
        mb: 3,
        boxShadow: '0 10px 30px rgba(0, 0, 0, 0.5), inset 0 1px 1px rgba(255, 215, 0, 0.2)'
      }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
          <Typography variant="subtitle1" sx={{ color: '#FFD700', fontWeight: 800 }}>
            پروجا (Perugia, Umbria) 🇮🇹
          </Typography>
          <Chip
            size="small"
            icon={<Terrain sx={{ fontSize: '14px !important', color: '#02C39A !important' }} />}
            label="۴۹۳ متر ارتفاع"
            sx={{
              background: 'rgba(0, 168, 150, 0.18)',
              border: '1px solid rgba(0, 168, 150, 0.4)',
              color: '#02C39A',
              fontSize: '0.72rem',
              fontWeight: 700
            }}
          />
        </Box>

        <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', my: 2, gap: 2 }}>
          <WbSunny sx={{ fontSize: 72, color: '#FFD700', filter: 'drop-shadow(0 0 18px rgba(255, 215, 0, 0.65))' }} />
          <Typography variant="h2" sx={{
            fontWeight: 900,
            background: 'linear-gradient(135deg, #FFFFFF 0%, #FFF099 50%, #FFD700 100%)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent'
          }}>
            22°C
          </Typography>
        </Box>

        <Typography variant="body2" sx={{ color: '#02C39A', fontWeight: 800, mb: 2.5 }}>
          آسمان صاف تا نیمه‌ابری • شرایط ایده‌آل پیاده‌روی به دانشگاه
        </Typography>

        {/* شاخص‌های جزئی ۳ تایی */}
        <Grid container spacing={1.5}>
          <Grid size={{ xs: 4 }}>
            <Box sx={{
              p: 1.2,
              borderRadius: 3,
              background: 'rgba(0, 168, 150, 0.1)',
              border: '1px solid rgba(0, 168, 150, 0.25)',
              textAlign: 'center'
            }}>
              <WaterDrop sx={{ color: '#02C39A', fontSize: 20 }} />
              <Typography variant="caption" sx={{ display: 'block', color: '#94D2BD', fontSize: '0.7rem' }}>رطوبت</Typography>
              <Typography variant="body2" sx={{ fontWeight: 800, color: '#FFFFFF' }}>54%</Typography>
            </Box>
          </Grid>
          <Grid size={{ xs: 4 }}>
            <Box sx={{
              p: 1.2,
              borderRadius: 3,
              background: 'rgba(255, 215, 0, 0.1)',
              border: '1px solid rgba(255, 215, 0, 0.25)',
              textAlign: 'center'
            }}>
              <Air sx={{ color: '#FFD700', fontSize: 20 }} />
              <Typography variant="caption" sx={{ display: 'block', color: '#94D2BD', fontSize: '0.7rem' }}>باد</Typography>
              <Typography variant="body2" sx={{ fontWeight: 800, color: '#FFFFFF' }}>11 km/h</Typography>
            </Box>
          </Grid>
          <Grid size={{ xs: 4 }}>
            <Box sx={{
              p: 1.2,
              borderRadius: 3,
              background: 'rgba(184, 0, 79, 0.15)',
              border: '1px solid rgba(184, 0, 79, 0.3)',
              textAlign: 'center'
            }}>
              <Shield sx={{ color: '#E60067', fontSize: 20 }} />
              <Typography variant="caption" sx={{ display: 'block', color: '#94D2BD', fontSize: '0.7rem' }}>شاخص UV</Typography>
              <Typography variant="body2" sx={{ fontWeight: 800, color: '#FFFFFF' }}>متوسط (4)</Typography>
            </Box>
          </Grid>
        </Grid>
      </Card>

      {/* پیش‌بینی ساعتی */}
      <Typography variant="subtitle2" sx={{ color: '#FFD700', mb: 1.5, fontWeight: 800, display: 'flex', alignItems: 'center', gap: 0.8 }}>
        ⏰ پیش‌بینی ساعات آینده
      </Typography>
      <Box sx={{ display: 'flex', gap: 1.2, overflowX: 'auto', pb: 1, mb: 3 }}>
        {hourly.map((h, i) => (
          <Box
            key={i}
            sx={{
              minWidth: 78,
              p: 1.5,
              borderRadius: 3,
              background: 'linear-gradient(160deg, rgba(7, 39, 35, 0.7) 0%, rgba(3, 23, 21, 0.9) 100%)',
              border: '1px solid rgba(255, 215, 0, 0.15)',
              textAlign: 'center',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              gap: 0.5,
              boxShadow: '0 4px 12px rgba(0,0,0,0.3)'
            }}
          >
            <Typography variant="caption" sx={{ color: '#94D2BD', fontSize: '0.72rem' }}>{h.time}</Typography>
            {h.icon}
            <Typography variant="body2" sx={{ fontWeight: 800, color: '#FFFFFF' }}>{h.temp}°</Typography>
          </Box>
        ))}
      </Box>

      {/* جعبه توصیه‌های دانشجویی مخصوص پروجا (زرشکی و طلایی) */}
      <Card sx={{
        background: 'linear-gradient(145deg, rgba(184, 0, 79, 0.18) 0%, rgba(114, 0, 38, 0.25) 100%)',
        border: '1px solid rgba(255, 215, 0, 0.35)',
        borderRadius: 4,
        p: 2.2,
        boxShadow: '0 6px 20px rgba(0,0,0,0.4)'
      }}>
        <CardContent sx={{ p: '0 !important' }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1.2 }}>
            <Hiking sx={{ color: '#FFD700', fontSize: 22 }} />
            <Typography variant="subtitle2" sx={{ fontWeight: 900, color: '#FFD700' }}>
              توصیه مهم برای شیب‌ها و پله‌های پروجا:
            </Typography>
          </Box>
          <Typography variant="body2" sx={{ color: '#F0FDF4', lineHeight: 1.8, fontSize: '0.82rem' }}>
            • با توجه به تپه‌ای بودن مسیر مرکز تاریخی (Piazza IV Novembre) به سمت دانشکده‌های Elce و San Pietro، حتماً از کفش راحت با زیره عاج‌دار استفاده فرمایید.<br />
            • پس از غروب آفتاب دمای هوا در ارتفاعات پروجا حدود ۵ درجه کاهش می‌یابد؛ به همراه داشتن یک بارانی یا ژاکت سبک پیشنهاد می‌شود.
          </Typography>
        </CardContent>
      </Card>
    </Box>
  );
}
