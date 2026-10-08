// src/apiConfig.ts
// آدرس پایه برای ارتباط مینی‌اپ با بک‌اند سرور در Render و محیط لوکال

export const API_BASE = (
  import.meta.env.VITE_API_BASE_URL ||
  (typeof window !== 'undefined' &&
  (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1')
    ? ''
    : 'https://smartstudentbot-backend.onrender.com')
).replace(/\/+$/, '');
