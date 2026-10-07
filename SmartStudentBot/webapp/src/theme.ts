import { createTheme } from '@mui/material/styles';

export const theme = createTheme({
  palette: {
    mode: 'dark',
    primary: {
      main: '#00A896', // Peacock Green / سبز کله‌غازی درخشان
      light: '#02C39A',
      dark: '#00564D',
      contrastText: '#FFFFFF',
    },
    secondary: {
      main: '#B8004F', // Royal Crimson / زرشکی سلطنتی
      light: '#E60067',
      dark: '#6E002B',
      contrastText: '#FFFFFF',
    },
    warning: {
      main: '#FFD700', // Imperial Gold / طلایی اشرافی
      light: '#FFE55C',
      dark: '#B89B00',
      contrastText: '#000000',
    },
    background: {
      default: '#031715', // Deep Peacock Night / پس‌زمینه کله‌غازی تیره
      paper: '#072723',   // Dark Teal Glass
    },
    text: {
      primary: '#F0FDF4',
      secondary: '#94D2BD',
    },
    error: {
      main: '#E63946',
    },
  },
  typography: {
    fontFamily: '"Vazirmatn", "Plus Jakarta Sans", "Roboto", sans-serif',
  },
  components: {
    MuiButton: {
      styleOverrides: {
        root: {
          borderRadius: 12,
          textTransform: 'none',
          fontWeight: 'bold',
          transition: 'all 0.3s ease',
          boxShadow: '0 4px 14px rgba(0, 168, 150, 0.25)',
          '&:hover': {
            boxShadow: '0 6px 20px rgba(0, 168, 150, 0.45)',
            transform: 'translateY(-1px)',
          },
        },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          borderRadius: 20,
          border: '1px solid rgba(255, 215, 0, 0.18)',
          background: 'linear-gradient(145deg, rgba(7, 39, 35, 0.85) 0%, rgba(4, 25, 22, 0.95) 100%)',
          backdropFilter: 'blur(16px)',
          boxShadow: '0 8px 32px rgba(0, 0, 0, 0.37), inset 0 1px 1px rgba(255, 215, 0, 0.15)',
        },
      },
    },
  },
});
