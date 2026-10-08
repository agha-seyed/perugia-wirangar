import { useState, useEffect } from 'react';
import {
  ThemeProvider,
  CssBaseline,
  Box,
  Typography,
  AppBar,
  Toolbar,
  BottomNavigation,
  BottomNavigationAction,
  Paper,
  Avatar,
  Chip,
  ButtonBase
} from '@mui/material';
import {
  Home,
  Calculate,
  Person,
  Storefront,
  Map,
  AutoAwesome,
  WbSunny,
  ArrowBack
} from '@mui/icons-material';
import { theme } from './theme';
import Dashboard from './components/Dashboard';
import ISEECalculatorView from './components/ISEECalculatorView';
import RoommateView from './components/RoommateView';
import MarketView from './components/MarketView';
import PlacesMapView from './components/PlacesMapView';
import AIChatView from './components/AIChatView';
import WeatherView from './components/WeatherView';

export default function App() {
  // 0: خانه, 1: محاسبه ISEE, 2: هم‌اتاقی, 3: بازارچه, 4: نقشه پروجا, 5: هوش مصنوعی, 6: آب‌وهوا
  const [value, setValue] = useState(0);
  const [tgUser, setTgUser] = useState<any>(null);

  useEffect(() => {
    try {
      const tg = (window as any).Telegram?.WebApp;
      if (tg) {
        tg.ready();
        tg.expand();
        tg.enableClosingConfirmation?.();
        tg.setHeaderColor?.('#031715');
        tg.setBackgroundColor?.('#031715');
        if (tg.initDataUnsafe?.user) {
          setTgUser(tg.initDataUnsafe.user);
        }
      }
    } catch (e) {
      console.warn('Telegram WebApp SDK not initialized:', e);
    }
  }, []);

  const triggerHaptic = () => {
    try {
      const tg = (window as any).Telegram?.WebApp;
      if (tg?.HapticFeedback) {
        tg.HapticFeedback.impactOccurred('light');
      }
    } catch (_) {}
  };

  const handleTabChange = (_event: any, newValue: number) => {
    triggerHaptic();
    setValue(newValue);
  };

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Box sx={{ pb: 9, minHeight: '100vh', background: '#031715' }}>
        {/* Royal Navigation Bar */}
        <AppBar
          position="sticky"
          sx={{
            background: 'linear-gradient(180deg, rgba(3, 23, 21, 0.95) 0%, rgba(7, 39, 35, 0.85) 100%)',
            backdropFilter: 'blur(16px)',
            borderBottom: '1px solid rgba(255, 215, 0, 0.25)',
            boxShadow: '0 4px 20px rgba(0, 0, 0, 0.5)',
          }}
          elevation={0}
        >
          <Toolbar sx={{ display: 'flex', justifyContent: 'space-between', px: 2, minHeight: '60px !important' }}>
            {/* Logo & Title */}
            <Box
              sx={{ display: 'flex', alignItems: 'center', gap: 1, cursor: 'pointer' }}
              onClick={() => { triggerHaptic(); setValue(0); }}
            >
              <Box
                sx={{
                  width: 34,
                  height: 34,
                  borderRadius: '10px',
                  background: 'linear-gradient(135deg, #00A896 0%, #B8004F 100%)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  boxShadow: '0 0 12px rgba(255, 215, 0, 0.4)',
                  border: '1px solid #FFD700',
                }}
              >
                <AutoAwesome sx={{ color: '#FFD700', fontSize: 20 }} />
              </Box>
              <Box>
                <Typography
                  variant="subtitle1"
                  sx={{
                    fontWeight: 900,
                    lineHeight: 1.1,
                    letterSpacing: '0.5px',
                    background: 'linear-gradient(135deg, #FFF099 0%, #FFD700 50%, #02C39A 100%)',
                    WebkitBackgroundClip: 'text',
                    WebkitTextFillColor: 'transparent',
                  }}
                >
                  Smart Perugia
                </Typography>
                <Typography variant="caption" sx={{ color: '#94D2BD', fontSize: '0.65rem', display: 'block' }}>
                  پورتال هوشمند دانشجویی
                </Typography>
              </Box>
            </Box>

            {/* Actions & Badges */}
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              {/* Back to Home if on AI or Weather */}
              {value >= 5 && (
                <ButtonBase
                  onClick={() => { triggerHaptic(); setValue(0); }}
                  sx={{
                    px: 1.2,
                    py: 0.4,
                    borderRadius: 2,
                    background: 'rgba(255, 215, 0, 0.15)',
                    border: '1px solid #FFD700',
                    color: '#FFD700',
                    fontSize: '0.75rem',
                    fontWeight: 'bold',
                    display: 'flex',
                    alignItems: 'center',
                    gap: 0.5
                  }}
                >
                  <ArrowBack sx={{ fontSize: 16 }} />
                  بازگشت
                </ButtonBase>
              )}

              {/* Quick AI Assistant Shortcut */}
              <ButtonBase
                onClick={() => { triggerHaptic(); setValue(5); }}
                sx={{
                  px: 1.2,
                  py: 0.4,
                  borderRadius: 2,
                  background: value === 5 ? 'rgba(184, 0, 79, 0.4)' : 'rgba(0, 168, 150, 0.2)',
                  border: value === 5 ? '1px solid #B8004F' : '1px solid rgba(0, 168, 150, 0.4)',
                  color: value === 5 ? '#FFD700' : '#02C39A',
                  fontSize: '0.72rem',
                  fontWeight: 'bold',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 0.4
                }}
              >
                <AutoAwesome sx={{ fontSize: 14 }} />
                دستیار AI
              </ButtonBase>

              {/* Quick Weather Shortcut */}
              <ButtonBase
                onClick={() => { triggerHaptic(); setValue(6); }}
                sx={{
                  px: 1,
                  py: 0.4,
                  borderRadius: 2,
                  background: value === 6 ? 'rgba(255, 215, 0, 0.25)' : 'rgba(7, 39, 35, 0.6)',
                  border: value === 6 ? '1px solid #FFD700' : '1px solid rgba(255, 215, 0, 0.2)',
                  color: '#FFD700',
                  fontSize: '0.72rem',
                  fontWeight: 'bold',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 0.4
                }}
              >
                <WbSunny sx={{ fontSize: 14, color: '#FFD700' }} />
                هوا
              </ButtonBase>

              {/* Telegram User Badge */}
              {tgUser && (
                <Chip
                  avatar={<Avatar src={tgUser.photo_url} alt={tgUser.first_name}>{tgUser.first_name?.[0]}</Avatar>}
                  label={tgUser.first_name}
                  size="small"
                  sx={{
                    background: 'rgba(184, 0, 79, 0.25)',
                    border: '1px solid rgba(255, 215, 0, 0.3)',
                    color: '#FFD700',
                    fontWeight: 'bold',
                    fontSize: '0.72rem',
                  }}
                />
              )}
            </Box>
          </Toolbar>
        </AppBar>

        {/* Dynamic Views */}
        <Box sx={{ mt: 1 }}>
          {value === 0 && <Dashboard onNavigate={(newTab) => { triggerHaptic(); setValue(newTab); }} />}
          {value === 1 && <ISEECalculatorView />}
          {value === 2 && <RoommateView />}
          {value === 3 && <MarketView />}
          {value === 4 && <PlacesMapView />}
          {value === 5 && <AIChatView />}
          {value === 6 && <WeatherView />}
        </Box>

        {/* Royal 5-Tab Bottom Navigation */}
        <Paper
          sx={{
            position: 'fixed',
            bottom: 0,
            left: 0,
            right: 0,
            borderTop: '1px solid rgba(255, 215, 0, 0.2)',
            zIndex: 1000,
            background: 'linear-gradient(180deg, rgba(7, 39, 35, 0.95) 0%, rgba(3, 23, 21, 0.99) 100%)',
            backdropFilter: 'blur(16px)',
            boxShadow: '0 -4px 25px rgba(0, 0, 0, 0.5)',
          }}
          elevation={4}
        >
          <BottomNavigation
            showLabels
            value={value > 4 ? false : value}
            onChange={handleTabChange}
            sx={{
              background: 'transparent',
              height: 64,
              '& .Mui-selected': {
                color: '#FFD700 !important',
                fontWeight: 'bold',
                '& .MuiSvgIcon-root': {
                  transform: 'scale(1.15)',
                  filter: 'drop-shadow(0 0 8px rgba(255, 215, 0, 0.6))',
                },
              },
              '& .MuiBottomNavigationAction-root': {
                color: '#94D2BD',
                minWidth: 'auto',
                px: 0.5,
                transition: 'all 0.2s ease',
                '& .MuiBottomNavigationAction-label': {
                  fontSize: '0.72rem',
                  fontWeight: 600,
                  '&.Mui-selected': {
                    fontSize: '0.76rem',
                  }
                }
              },
            }}
          >
            <BottomNavigationAction
              label="خانه"
              icon={<Home />}
              sx={{ color: value === 0 ? '#FFD700' : '#94D2BD' }}
            />
            <BottomNavigationAction
              label="ایزه (ISEE)"
              icon={<Calculate />}
              sx={{ color: value === 1 ? '#FFD700' : '#94D2BD' }}
            />
            <BottomNavigationAction
              label="هم‌اتاقی"
              icon={<Person />}
              sx={{ color: value === 2 ? '#FFD700' : '#94D2BD' }}
            />
            <BottomNavigationAction
              label="بازارچه"
              icon={<Storefront />}
              sx={{ color: value === 3 ? '#FFD700' : '#94D2BD' }}
            />
            <BottomNavigationAction
              label="نقشه"
              icon={<Map />}
              sx={{ color: value === 4 ? '#FFD700' : '#94D2BD' }}
            />
          </BottomNavigation>
        </Paper>
      </Box>
    </ThemeProvider>
  );
}
