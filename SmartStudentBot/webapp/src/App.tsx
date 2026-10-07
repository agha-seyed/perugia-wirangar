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
  Chip
} from '@mui/material';
import { Cloud, Person, Forum, Home, AutoAwesome } from '@mui/icons-material';
import { theme } from './theme';
import Dashboard from './components/Dashboard';
import RoommateView from './components/RoommateView';
import AIChatView from './components/AIChatView';
import WeatherView from './components/WeatherView';

export default function App() {
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
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
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
                  مینی‌اپ جامع دانشجویی
                </Typography>
              </Box>
            </Box>

            {/* Telegram User Badge / Status */}
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              {tgUser ? (
                <Chip
                  avatar={<Avatar src={tgUser.photo_url} alt={tgUser.first_name}>{tgUser.first_name?.[0]}</Avatar>}
                  label={tgUser.first_name}
                  size="small"
                  sx={{
                    background: 'rgba(184, 0, 79, 0.25)',
                    border: '1px solid rgba(255, 215, 0, 0.3)',
                    color: '#FFD700',
                    fontWeight: 'bold',
                    fontSize: '0.75rem',
                  }}
                />
              ) : (
                <Chip
                  label="بورسیه & ویزا 🇮🇹"
                  size="small"
                  sx={{
                    background: 'rgba(0, 168, 150, 0.2)',
                    border: '1px solid rgba(0, 168, 150, 0.4)',
                    color: '#02C39A',
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
          {value === 1 && <RoommateView />}
          {value === 2 && <AIChatView />}
          {value === 3 && <WeatherView />}
        </Box>

        {/* Royal Bottom Navigation */}
        <Paper
          sx={{
            position: 'fixed',
            bottom: 0,
            left: 0,
            right: 0,
            borderTop: '1px solid rgba(255, 215, 0, 0.2)',
            zIndex: 1000,
            background: 'linear-gradient(180deg, rgba(7, 39, 35, 0.92) 0%, rgba(3, 23, 21, 0.98) 100%)',
            backdropFilter: 'blur(16px)',
            boxShadow: '0 -4px 25px rgba(0, 0, 0, 0.5)',
          }}
          elevation={4}
        >
          <BottomNavigation
            showLabels
            value={value}
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
                transition: 'all 0.2s ease',
              },
            }}
          >
            <BottomNavigationAction
              label="خانه"
              icon={<Home />}
              sx={{ color: value === 0 ? '#FFD700' : '#94D2BD' }}
            />
            <BottomNavigationAction
              label="هم‌اتاقی"
              icon={<Person />}
              sx={{ color: value === 1 ? '#FFD700' : '#94D2BD' }}
            />
            <BottomNavigationAction
              label="هوش مصنوعی"
              icon={<Forum />}
              sx={{ color: value === 2 ? '#FFD700' : '#94D2BD' }}
            />
            <BottomNavigationAction
              label="آب‌وهوا"
              icon={<Cloud />}
              sx={{ color: value === 3 ? '#FFD700' : '#94D2BD' }}
            />
          </BottomNavigation>
        </Paper>
      </Box>
    </ThemeProvider>
  );
}
