import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Card,
  CardContent,
  TextField,
  Button,
  Chip,
  Divider,
  InputAdornment,
  ToggleButton,
  ToggleButtonGroup,
  IconButton,
  CircularProgress,
  Slider
} from '@mui/material';
import {
  Calculate,
  Euro,
  Refresh,
  Edit,
  CheckCircle,
  Warning,
  Lightbulb,
  Home,
  AccountBalance,
  FamilyRestroom,
  TrendingDown,
  Info,
  Send
} from '@mui/icons-material';
import { motion, AnimatePresence } from 'framer-motion';

import { API_BASE } from '../apiConfig';

export default function ISEECalculatorView() {
  // ۱. نرخ زنده یورو به تومان (پیش‌فرض منطبق بر قیمت روز بازار آزاد ۳۰۴,۰۰۰)
  const [eurRate, setEurRate] = useState<number>(304000);
  const [isLiveRate, setIsLiveRate] = useState<boolean>(true);
  const [rateLoading, setRateLoading] = useState<boolean>(false);
  const [customRateOpen, setCustomRateOpen] = useState<boolean>(false);
  const [tempRate, setTempRate] = useState<string>('304000');

  // ۲. ورودی‌های کاربر
  const [familyMembers, setFamilyMembers] = useState<number>(4);
  const [isTenant, setIsTenant] = useState<boolean>(true);
  
  // واحد هر فیلد (toman یا eur)
  const [incomeUnit, setIncomeUnit] = useState<'toman' | 'eur'>('toman');
  const [incomeValue, setIncomeValue] = useState<string>('150000000'); // ۱۵۰ میلیون تومان پیش‌فرض

  const [rentUnit, setRentUnit] = useState<'toman' | 'eur'>('toman');
  const [rentValue, setRentValue] = useState<string>('60000000'); // ۶۰ میلیون تومان در سال

  const [propertyUnit, setPropertyUnit] = useState<'toman' | 'eur'>('toman');
  const [propertyValue, setPropertyValue] = useState<string>('2500000000'); // ۲.۵ میلیارد تومان ملک

  const [assetsUnit, setAssetsUnit] = useState<'toman' | 'eur'>('toman');
  const [assetsValue, setAssetsValue] = useState<string>('100000000'); // ۱۰۰ میلیون موجودی

  const [debtsUnit, setDebtsUnit] = useState<'toman' | 'eur'>('toman');
  const [debtsValue, setDebtsValue] = useState<string>('0');

  // واکشی نرخ زنده یورو در شروع
  const fetchLiveEurRate = async () => {
    setRateLoading(true);
    try {
      // ۱. ابتدا تلاش مستقیم از بک‌اند Render / Localhost
      const res = await fetch(`${API_BASE}/api/v1/webapp/currency`);
      if (res.ok) {
        const data = await res.json();
        if (data.eur_toman && data.eur_toman > 50000) {
          setEurRate(data.eur_toman);
          setTempRate(data.eur_toman.toString());
          setIsLiveRate(true);
          setRateLoading(false);
          return;
        }
      }
    } catch (_) {}

    // ۲. تلاش از پروکسی CORS به کلاستر TGJU
    try {
      const res = await fetch('https://api.allorigins.win/raw?url=' + encodeURIComponent('https://call.tgju.org/ajax.json'));
      if (res.ok) {
        const data = await res.json();
        const eurObj = data?.current?.price_eur || data?.current?.sarafiyaran_eur_sell || data?.current?.sarafiroyal_eur_sell;
        if (eurObj) {
          const valStr = typeof eurObj === 'object' ? eurObj.p : String(eurObj);
          const clean = valStr.replace(/[^\d]/g, '');
          const rial = parseInt(clean);
          if (rial > 500000) {
            const toman = Math.round(rial / 10);
            setEurRate(toman);
            setTempRate(toman.toString());
            setIsLiveRate(true);
            setRateLoading(false);
            return;
          }
        }
      }
    } catch (_) {}

    // ۳. در صورت آفلاین بودن، نرخ معتبر روز بازار آزاد
    setEurRate(304000);
    setTempRate('304000');
    setIsLiveRate(false);
    setRateLoading(false);
  };

  useEffect(() => {
    fetchLiveEurRate();
  }, []);

  // توابع تبدیل ارز
  const toEur = (valStr: string, unit: 'toman' | 'eur'): number => {
    const num = parseFloat(valStr.replace(/,/g, '')) || 0;
    if (unit === 'eur') return num;
    return eurRate > 0 ? num / eurRate : 0;
  };

  // ضرایب رسمی بعد خانوار (Scala di Equivalenza)
  const getScale = (m: number): number => {
    if (m <= 1) return 1.0;
    if (m === 2) return 1.57;
    if (m === 3) return 2.04;
    if (m === 4) return 2.46;
    if (m === 5) return 2.85;
    return 2.85 + (m - 5) * 0.35;
  };

  // محاسبات بر اساس DPCM 159/2013 ایتالیا
  const rawIncomeEur = toEur(incomeValue, incomeUnit);
  const rawRentEur = isTenant ? toEur(rentValue, rentUnit) : 0;
  const rawPropertyEur = toEur(propertyValue, propertyUnit);
  const rawAssetsEur = toEur(assetsValue, assetsUnit);
  const rawDebtsEur = toEur(debtsValue, debtsUnit);

  // ۱. کسر اجاره‌خانه (حداکثر ۷,۰۰۰ یورو)
  const rentDeduction = Math.min(rawRentEur, 7000);
  const adjustedIncome = Math.max(0, rawIncomeEur - rentDeduction);

  // ۲. معافیت خانه اول (پایه ۵۲,۵۰۰ یورو)
  const primaryHomeExemption = Math.min(rawPropertyEur, 52500);
  const adjustedProperty = Math.max(0, rawPropertyEur - primaryHomeExemption);

  // ۳. معافیت دارایی مالی (۶,۰۰۰ پایه + ۲,۰۰۰ به ازای هر عضو، حداکثر ۱۰,۰۰۰ یورو)
  const financialExemptionLimit = Math.min(6000 + familyMembers * 2000, 10000);
  const financialExemption = Math.min(rawAssetsEur, financialExemptionLimit);
  const adjustedAssets = Math.max(0, rawAssetsEur - financialExemption);

  // ۴. مجموع دارایی منقول و غیرمنقول پس از کسر بدهی
  const rawPatrimony = adjustedProperty + adjustedAssets;
  const debtDeduction = Math.min(rawDebtsEur, rawPatrimony);
  const totalPatrimony = Math.max(0, rawPatrimony - debtDeduction);

  // ۵. ضرایب نهایی
  const scale = getScale(familyMembers);
  const ise = adjustedIncome + 0.2 * totalPatrimony;
  const isee = Math.round(ise / scale);
  const ispe = Math.round(totalPatrimony / scale);

  const isEligibleScholarship = isee <= 25500 && ispe <= 55000;

  const handleApplyCustomRate = () => {
    const parsed = parseInt(tempRate.replace(/,/g, ''));
    if (parsed > 10000) {
      setEurRate(parsed);
      setIsLiveRate(false);
      setCustomRateOpen(false);
    }
  };

  const handleSendToBot = () => {
    const tg = (window as any).Telegram?.WebApp;
    if (tg) {
      tg.HapticFeedback?.notificationOccurred('success');
      try {
        tg.sendData(JSON.stringify({
          action: 'isee_calculated',
          isee: isee,
          ispe: ispe,
          members: familyMembers,
          eur_rate: eurRate
        }));
      } catch (_) {}
      if (tg.openTelegramLink) {
        tg.openTelegramLink(`https://t.me/SmartStudentPerugiaBot?start=isee`);
        return;
      }
    }
    window.open(`https://t.me/SmartStudentPerugiaBot?start=isee`, '_blank');
  };

  return (
    <Box sx={{ p: 2, pb: 12, width: '100%', maxWidth: 520, mx: 'auto', dir: 'rtl' }}>
      
      {/* هدر طلایی بخش ISEE */}
      <Box sx={{ textAlign: 'center', mb: 3 }}>
        <Box sx={{ display: 'inline-flex', p: 1.5, borderRadius: '50%', background: 'rgba(255, 215, 0, 0.15)', mb: 1, border: '1px solid #FFD700' }}>
          <Calculate sx={{ fontSize: 36, color: '#FFD700' }} />
        </Box>
        <Typography
          variant="h5"
          sx={{
            fontWeight: 900,
            background: 'linear-gradient(135deg, #FFF099 0%, #FFD700 50%, #02C39A 100%)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
            filter: 'drop-shadow(0 2px 8px rgba(255, 215, 0, 0.3))',
            mb: 0.5
          }}
        >
          شبیه‌ساز و محاسبه‌گر هوشمند ISEE
        </Typography>
        <Typography variant="caption" sx={{ color: '#94D2BD', display: 'block', lineHeight: 1.6 }}>
          ارزیابی شانس بورسیه استانی ADiSU Umbria و معافیت شهریه دانشگاه پروجا
        </Typography>
      </Box>

      {/* ۱. بنر نرخ زنده یورو به تومان */}
      <Card
        sx={{
          mb: 3,
          borderRadius: 3.5,
          background: 'linear-gradient(135deg, rgba(7, 39, 35, 0.95) 0%, rgba(3, 23, 21, 0.95) 100%)',
          border: '1px solid rgba(255, 215, 0, 0.35)',
          boxShadow: '0 8px 24px rgba(0, 0, 0, 0.5)',
          overflow: 'hidden'
        }}
      >
        <CardContent sx={{ p: 2, '&:last-child': { pb: 2 } }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <Box sx={{ width: 36, height: 36, borderRadius: 2, background: 'rgba(2, 195, 154, 0.2)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <Euro sx={{ color: '#02C39A', fontSize: 22 }} />
              </Box>
              <Box>
                <Typography variant="caption" sx={{ color: '#94D2BD', fontWeight: 600 }}>
                  نرخ مبنای تبدیل یورو (بازار آزاد)
                </Typography>
                <Typography variant="h6" sx={{ color: '#FFD700', fontWeight: 900, lineHeight: 1.2 }}>
                  {eurRate.toLocaleString('fa-IR')} تومان
                </Typography>
              </Box>
            </Box>

            <Box sx={{ display: 'flex', gap: 0.5 }}>
              <IconButton
                size="small"
                onClick={fetchLiveEurRate}
                disabled={rateLoading}
                sx={{ color: '#02C39A', background: 'rgba(2, 195, 154, 0.1)', border: '1px solid rgba(2, 195, 154, 0.3)' }}
              >
                {rateLoading ? <CircularProgress size={18} color="inherit" /> : <Refresh fontSize="small" />}
              </IconButton>
              <IconButton
                size="small"
                onClick={() => setCustomRateOpen(!customRateOpen)}
                sx={{ color: '#FFD700', background: 'rgba(255, 215, 0, 0.1)', border: '1px solid rgba(255, 215, 0, 0.3)' }}
              >
                <Edit fontSize="small" />
              </IconButton>
            </Box>
          </Box>

          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mt: 1.2, pt: 1, borderTop: '1px solid rgba(255, 215, 0, 0.15)' }}>
            <Chip
              label={isLiveRate ? "🟢 منبع زنده TGJU" : "✏️ نرخ سفارشی دستی"}
              size="small"
              sx={{ background: isLiveRate ? 'rgba(2, 195, 154, 0.15)' : 'rgba(255, 183, 3, 0.15)', color: isLiveRate ? '#02C39A' : '#FFB703', fontWeight: 700, fontSize: '0.68rem', height: 22 }}
            />
            <Typography variant="caption" sx={{ color: '#70A9A1', fontSize: '0.7rem' }}>
              ۱ یورو = {eurRate.toLocaleString('fa-IR')} ت
            </Typography>
          </Box>

          {/* فیلد تغییر دستی نرخ */}
          <AnimatePresence>
            {customRateOpen && (
              <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} exit={{ opacity: 0, height: 0 }}>
                <Box sx={{ mt: 1.5, pt: 1.5, borderTop: '1px dashed rgba(255, 215, 0, 0.2)', display: 'flex', gap: 1 }}>
                  <TextField
                    size="small"
                    fullWidth
                    label="نرخ دلخواه یورو (تومان)"
                    value={tempRate}
                    onChange={(e) => setTempRate(e.target.value)}
                    sx={{ '& .MuiOutlinedInput-root': { color: '#fff', fontSize: '0.85rem' } }}
                    slotProps={{ inputLabel: { sx: { color: '#94D2BD', fontSize: '0.8rem' } } }}
                  />
                  <Button
                    variant="contained"
                    onClick={handleApplyCustomRate}
                    sx={{ background: '#FFD700', color: '#031715', fontWeight: 800, whiteSpace: 'nowrap', '&:hover': { background: '#FFF099' } }}
                  >
                    اعمال
                  </Button>
                </Box>
              </motion.div>
            )}
          </AnimatePresence>
        </CardContent>
      </Card>

      {/* ۲. فرم سوالات ورودی (مطابق ربات) */}
      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2.2 }}>

        {/* سوال ۱: تعداد اعضای خانواده */}
        <Card sx={{ background: 'rgba(7, 39, 35, 0.8)', border: '1px solid rgba(255, 215, 0, 0.2)', borderRadius: 3, p: 2 }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1.5 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <FamilyRestroom sx={{ color: '#FFD700', fontSize: 22 }} />
              <Typography variant="subtitle2" sx={{ color: '#fff', fontWeight: 800 }}>
                ۱. تعداد اعضای خانواده
              </Typography>
            </Box>
            <Chip
              label={`ضریب مقیاس: ${scale.toFixed(2)}`}
              size="small"
              sx={{ background: 'rgba(255, 215, 0, 0.15)', color: '#FFD700', fontWeight: 800, fontSize: '0.72rem' }}
            />
          </Box>
          <Slider
            value={familyMembers}
            min={1}
            max={7}
            step={1}
            marks
            valueLabelDisplay="on"
            onChange={(_, val) => setFamilyMembers(val as number)}
            sx={{
              color: '#FFD700',
              '& .MuiSlider-valueLabel': { background: '#B8004F', color: '#FFD700', fontWeight: 800 }
            }}
          />
          <Typography variant="caption" sx={{ color: '#94D2BD', display: 'block', mt: 0.5 }}>
            شامل دانشجو، والدین و خواهران/برادران تحت تکفل سرپرست
          </Typography>
        </Card>

        {/* سوال ۲: درآمد سالانه سرپرست */}
        <Card sx={{ background: 'rgba(7, 39, 35, 0.8)', border: '1px solid rgba(255, 215, 0, 0.2)', borderRadius: 3, p: 2 }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
            <Typography variant="subtitle2" sx={{ color: '#fff', fontWeight: 800 }}>
              ۲. درآمد سالانه کل خانواده
            </Typography>
            <ToggleButtonGroup
              size="small"
              value={incomeUnit}
              exclusive
              onChange={(_, val) => val && setIncomeUnit(val)}
              sx={{ background: 'rgba(3, 23, 21, 0.8)', '& .MuiToggleButton-root': { color: '#94D2BD', px: 1, py: 0.3, fontSize: '0.72rem', '&.Mui-selected': { color: '#FFD700', background: 'rgba(184,0,79,0.35)', fontWeight: 800 } } }}
            >
              <ToggleButton value="toman">تومان</ToggleButton>
              <ToggleButton value="eur">یورو (€)</ToggleButton>
            </ToggleButtonGroup>
          </Box>

          <TextField
            fullWidth
            size="small"
            value={incomeValue}
            onChange={(e) => setIncomeValue(e.target.value)}
            slotProps={{
              input: {
                endAdornment: (
                  <InputAdornment position="end">
                    <Typography sx={{ color: '#02C39A', fontSize: '0.75rem', fontWeight: 700 }}>
                      ≈ {Math.round(rawIncomeEur).toLocaleString()} €
                    </Typography>
                  </InputAdornment>
                )
              }
            }}
            sx={{ '& .MuiOutlinedInput-root': { color: '#fff', '& fieldset': { borderColor: 'rgba(0,168,150,0.4)' } } }}
          />
          <Typography variant="caption" sx={{ color: '#94D2BD', mt: 0.8, display: 'block' }}>
            مجموع حقوق سالانه طبق فیش حقوقی یا حکم بازنشستگی
          </Typography>
        </Card>

        {/* سوال ۳: وضعیت مسکن و اجاره‌خانه */}
        <Card sx={{ background: 'rgba(7, 39, 35, 0.8)', border: '1px solid rgba(255, 215, 0, 0.2)', borderRadius: 3, p: 2 }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <Home sx={{ color: '#02C39A', fontSize: 20 }} />
              <Typography variant="subtitle2" sx={{ color: '#fff', fontWeight: 800 }}>
                ۳. وضعیت سکونت در ایران
              </Typography>
            </Box>
            <ToggleButtonGroup
              size="small"
              value={isTenant ? 'tenant' : 'owner'}
              exclusive
              onChange={(_, val) => setIsTenant(val === 'tenant')}
              sx={{ background: 'rgba(3, 23, 21, 0.8)', '& .MuiToggleButton-root': { color: '#94D2BD', px: 1, py: 0.3, fontSize: '0.72rem', '&.Mui-selected': { color: '#02C39A', background: 'rgba(0,168,150,0.3)', fontWeight: 800 } } }}
            >
              <ToggleButton value="tenant">مستأجر</ToggleButton>
              <ToggleButton value="owner">مالک</ToggleButton>
            </ToggleButtonGroup>
          </Box>

          {isTenant ? (
            <Box sx={{ mt: 1.5 }}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                <Typography variant="caption" sx={{ color: '#FFD700', fontWeight: 700 }}>
                  اجاره‌بهای پرداختی سالانه:
                </Typography>
                <ToggleButtonGroup
                  size="small"
                  value={rentUnit}
                  exclusive
                  onChange={(_, val) => val && setRentUnit(val)}
                  sx={{ '& .MuiToggleButton-root': { color: '#94D2BD', px: 0.8, py: 0.2, fontSize: '0.68rem', '&.Mui-selected': { color: '#FFD700' } } }}
                >
                  <ToggleButton value="toman">تومان</ToggleButton>
                  <ToggleButton value="eur">یورو</ToggleButton>
                </ToggleButtonGroup>
              </Box>
              <TextField
                fullWidth
                size="small"
                value={rentValue}
                onChange={(e) => setRentValue(e.target.value)}
                slotProps={{
                  input: {
                    endAdornment: (
                      <InputAdornment position="end">
                        <Typography sx={{ color: '#02C39A', fontSize: '0.75rem', fontWeight: 700 }}>
                          کسر قانونی: -{Math.round(rentDeduction).toLocaleString()} €
                        </Typography>
                      </InputAdornment>
                    )
                  }
                }}
                sx={{ '& .MuiOutlinedInput-root': { color: '#fff' } }}
              />
              <Typography variant="caption" sx={{ color: '#02C39A', mt: 0.5, display: 'block' }}>
                ✅ تا سقف ۷,۰۰۰ یورو مستقیماً از درآمد خانواده کسر می‌گردد!
              </Typography>
            </Box>
          ) : (
            <Typography variant="caption" sx={{ color: '#94D2BD', mt: 0.5, display: 'block' }}>
              در صورت مالکیت، ارزش ملک در بخش دارایی‌ها محاسبه می‌شود.
            </Typography>
          )}
        </Card>

        {/* سوال ۴: ارزش ملک مسکونی اول */}
        <Card sx={{ background: 'rgba(7, 39, 35, 0.8)', border: '1px solid rgba(255, 215, 0, 0.2)', borderRadius: 3, p: 2 }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
            <Typography variant="subtitle2" sx={{ color: '#fff', fontWeight: 800 }}>
              ۴. ارزش املاک و مستغلات
            </Typography>
            <ToggleButtonGroup
              size="small"
              value={propertyUnit}
              exclusive
              onChange={(_, val) => val && setPropertyUnit(val)}
              sx={{ background: 'rgba(3, 23, 21, 0.8)', '& .MuiToggleButton-root': { color: '#94D2BD', px: 1, py: 0.3, fontSize: '0.72rem', '&.Mui-selected': { color: '#FFD700', background: 'rgba(184,0,79,0.35)', fontWeight: 800 } } }}
            >
              <ToggleButton value="toman">تومان</ToggleButton>
              <ToggleButton value="eur">یورو</ToggleButton>
            </ToggleButtonGroup>
          </Box>

          <TextField
            fullWidth
            size="small"
            value={propertyValue}
            onChange={(e) => setPropertyValue(e.target.value)}
            slotProps={{
              input: {
                endAdornment: (
                  <InputAdornment position="end">
                    <Typography sx={{ color: '#02C39A', fontSize: '0.75rem', fontWeight: 700 }}>
                      ارزش: {Math.round(rawPropertyEur).toLocaleString()} €
                    </Typography>
                  </InputAdornment>
                )
              }
            }}
            sx={{ '& .MuiOutlinedInput-root': { color: '#fff' } }}
          />
          <Typography variant="caption" sx={{ color: '#02C39A', mt: 0.8, display: 'block' }}>
            🛡 معافیت خانه اول: ۵۲,۵۰۰ یورو از ارزش خانه به طور خودکار کسر می‌شود. (خالص: {Math.round(adjustedProperty).toLocaleString()} €)
          </Typography>
        </Card>

        {/* سوال ۵: موجودی بانکی و دارایی مالی */}
        <Card sx={{ background: 'rgba(7, 39, 35, 0.8)', border: '1px solid rgba(255, 215, 0, 0.2)', borderRadius: 3, p: 2 }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <AccountBalance sx={{ color: '#FFD700', fontSize: 20 }} />
              <Typography variant="subtitle2" sx={{ color: '#fff', fontWeight: 800 }}>
                ۵. موجودی حساب بانکی و طلا
              </Typography>
            </Box>
            <ToggleButtonGroup
              size="small"
              value={assetsUnit}
              exclusive
              onChange={(_, val) => val && setAssetsUnit(val)}
              sx={{ background: 'rgba(3, 23, 21, 0.8)', '& .MuiToggleButton-root': { color: '#94D2BD', px: 1, py: 0.3, fontSize: '0.72rem', '&.Mui-selected': { color: '#FFD700', background: 'rgba(184,0,79,0.35)', fontWeight: 800 } } }}
            >
              <ToggleButton value="toman">تومان</ToggleButton>
              <ToggleButton value="eur">یورو</ToggleButton>
            </ToggleButtonGroup>
          </Box>

          <TextField
            fullWidth
            size="small"
            value={assetsValue}
            onChange={(e) => setAssetsValue(e.target.value)}
            slotProps={{
              input: {
                endAdornment: (
                  <InputAdornment position="end">
                    <Typography sx={{ color: '#02C39A', fontSize: '0.75rem', fontWeight: 700 }}>
                      موجودی: {Math.round(rawAssetsEur).toLocaleString()} €
                    </Typography>
                  </InputAdornment>
                )
              }
            }}
            sx={{ '& .MuiOutlinedInput-root': { color: '#fff' } }}
          />
          <Typography variant="caption" sx={{ color: '#02C39A', mt: 0.8, display: 'block' }}>
            🛡 معافیت نقدی قانونی: {financialExemptionLimit.toLocaleString()} € کسر شد. (خالص مشمول: {Math.round(adjustedAssets).toLocaleString()} €)
          </Typography>
        </Card>

        {/* سوال ۶: بدهی‌ها و وام‌ها */}
        <Card sx={{ background: 'rgba(7, 39, 35, 0.8)', border: '1px solid rgba(255, 215, 0, 0.2)', borderRadius: 3, p: 2 }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <TrendingDown sx={{ color: '#E63946', fontSize: 20 }} />
              <Typography variant="subtitle2" sx={{ color: '#fff', fontWeight: 800 }}>
                ۶. وام‌ها و بدهی‌های بانکی
              </Typography>
            </Box>
            <ToggleButtonGroup
              size="small"
              value={debtsUnit}
              exclusive
              onChange={(_, val) => val && setDebtsUnit(val)}
              sx={{ background: 'rgba(3, 23, 21, 0.8)', '& .MuiToggleButton-root': { color: '#94D2BD', px: 1, py: 0.3, fontSize: '0.72rem', '&.Mui-selected': { color: '#FFD700', background: 'rgba(184,0,79,0.35)', fontWeight: 800 } } }}
            >
              <ToggleButton value="toman">تومان</ToggleButton>
              <ToggleButton value="eur">یورو</ToggleButton>
            </ToggleButtonGroup>
          </Box>

          <TextField
            fullWidth
            size="small"
            value={debtsValue}
            onChange={(e) => setDebtsValue(e.target.value)}
            slotProps={{
              input: {
                endAdornment: (
                  <InputAdornment position="end">
                    <Typography sx={{ color: '#02C39A', fontSize: '0.75rem', fontWeight: 700 }}>
                      کسر بدهی: -{Math.round(debtDeduction).toLocaleString()} €
                    </Typography>
                  </InputAdornment>
                )
              }
            }}
            sx={{ '& .MuiOutlinedInput-root': { color: '#fff' } }}
          />
        </Card>
      </Box>

      {/* ۳. کارت بزرگ نتیجه و ارزیابی نهایی */}
      <Card
        sx={{
          mt: 3.5,
          borderRadius: 4,
          background: isEligibleScholarship
            ? 'linear-gradient(145deg, rgba(2, 195, 154, 0.18) 0%, rgba(7, 39, 35, 0.95) 100%)'
            : 'linear-gradient(145deg, rgba(230, 57, 70, 0.18) 0%, rgba(7, 39, 35, 0.95) 100%)',
          border: isEligibleScholarship ? '2px solid #02C39A' : '2px solid #FFB703',
          boxShadow: isEligibleScholarship ? '0 10px 30px rgba(2, 195, 154, 0.25)' : '0 10px 30px rgba(255, 183, 3, 0.25)',
          overflow: 'hidden'
        }}
      >
        <CardContent sx={{ p: 2.5 }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
            <Typography variant="h6" sx={{ color: '#FFD700', fontWeight: 900 }}>
              📊 نتیجه نهایی ISEE Parificato
            </Typography>
            <Chip
              label={isEligibleScholarship ? "بورسیه کامل 🟢" : "بالاتر از سقف ⚠️"}
              sx={{
                background: isEligibleScholarship ? '#02C39A' : '#FFB703',
                color: '#031715',
                fontWeight: 900,
                fontSize: '0.8rem'
              }}
            />
          </Box>

          {/* نمرات اصلی */}
          <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 1.5, textAlign: 'center', mb: 2.5 }}>
            <Box sx={{ p: 1.5, borderRadius: 2.5, background: 'rgba(3, 23, 21, 0.7)', border: '1px solid rgba(255, 215, 0, 0.25)' }}>
              <Typography variant="caption" sx={{ color: '#94D2BD', display: 'block' }}>عدد ایزه (ISEE)</Typography>
              <Typography variant="h6" sx={{ color: '#FFD700', fontWeight: 900 }}>
                {isee.toLocaleString()} €
              </Typography>
              <Typography variant="caption" sx={{ color: '#70A9A1', fontSize: '0.65rem' }}>سقف: ۲۵,۵۰۰€</Typography>
            </Box>

            <Box sx={{ p: 1.5, borderRadius: 2.5, background: 'rgba(3, 23, 21, 0.7)', border: '1px solid rgba(255, 215, 0, 0.25)' }}>
              <Typography variant="caption" sx={{ color: '#94D2BD', display: 'block' }}>شاخص دارایی (ISPE)</Typography>
              <Typography variant="h6" sx={{ color: '#02C39A', fontWeight: 900 }}>
                {ispe.toLocaleString()} €
              </Typography>
              <Typography variant="caption" sx={{ color: '#70A9A1', fontSize: '0.65rem' }}>سقف: ۵۵,۰۰۰€</Typography>
            </Box>

            <Box sx={{ p: 1.5, borderRadius: 2.5, background: 'rgba(3, 23, 21, 0.7)', border: '1px solid rgba(255, 215, 0, 0.25)' }}>
              <Typography variant="caption" sx={{ color: '#94D2BD', display: 'block' }}>ضریب بعد خانوار</Typography>
              <Typography variant="h6" sx={{ color: '#FFFFFF', fontWeight: 900 }}>
                {scale.toFixed(2)}
              </Typography>
              <Typography variant="caption" sx={{ color: '#70A9A1', fontSize: '0.65rem' }}>{familyMembers} نفره</Typography>
            </Box>
          </Box>

          <Divider sx={{ borderColor: 'rgba(255, 215, 0, 0.2)', mb: 2 }} />

          {/* متن وضعیت و مزایا */}
          {isEligibleScholarship ? (
            <Box sx={{ display: 'flex', gap: 1.5, alignItems: 'flex-start' }}>
              <CheckCircle sx={{ color: '#02C39A', fontSize: 28, mt: 0.3 }} />
              <Box>
                <Typography variant="subtitle2" sx={{ color: '#02C39A', fontWeight: 900, mb: 0.5 }}>
                  🎉 تبریک! شما کاملاً واجد شرایط بورسیه استانی ADiSU هستید:
                </Typography>
                <Typography variant="body2" sx={{ color: '#F0FDF4', fontSize: '0.82rem', lineHeight: 1.7 }}>
                  • کمک‌هزینه نقدی تا <b>۷,۰۰۰ یورو در سال</b><br />
                  • <b>خوابگاه رایگان دانشجویی</b> در پروجا یا ترنی<br />
                  • روزانه <b>۲ وعده غذای کاملاً رایگان</b> در سلف دانشگاه (Mensa)<br />
                  • <b>معافیت ۱۰۰٪ از پرداخت شهریه دانشگاه UniPG</b>
                </Typography>
              </Box>
            </Box>
          ) : (
            <Box sx={{ display: 'flex', gap: 1.5, alignItems: 'flex-start' }}>
              <Warning sx={{ color: '#FFB703', fontSize: 28, mt: 0.3 }} />
              <Box>
                <Typography variant="subtitle2" sx={{ color: '#FFB703', fontWeight: 900, mb: 0.5 }}>
                  ⚠️ عدد ایزه شما بالاتر از سقف ۲۵,۵۰۰ یورو است:
                </Typography>
                <Typography variant="body2" sx={{ color: '#F0FDF4', fontSize: '0.82rem', lineHeight: 1.7 }}>
                  شما همچنان مشمول تخفیف پلکانی شهریه دانشگاه UniPG می‌شوید، اما برای دریافت خوابگاه و کمک‌هزینه نقدی ADiSU باید عدد ایزه کاهش یابد.
                </Typography>
              </Box>
            </Box>
          )}

          {/* استراتژی‌های کاهش ISEE اگر بالای سقف باشد */}
          {!isEligibleScholarship && (
            <Box sx={{ mt: 2, p: 1.5, borderRadius: 2.5, background: 'rgba(255, 183, 3, 0.1)', border: '1px dashed #FFB703' }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
                <Lightbulb sx={{ color: '#FFD700', fontSize: 18 }} />
                <Typography variant="caption" sx={{ color: '#FFD700', fontWeight: 800 }}>
                  راهکارهای عملی برای رساندن عدد ایزه به زیر ۲۵,۵۰۰ یورو:
                </Typography>
              </Box>
              <Typography variant="caption" sx={{ color: '#94D2BD', display: 'block', lineHeight: 1.6 }}>
                ۱. اگر مستأجر هستید، حتماً اجاره‌نامه رسمی را اضافه کنید (تا ۷۰۰۰€ کسر می‌شود).<br />
                ۲. موجودی حساب ملاک تاریخ ۳۱ دسامبر سال قبل است؛ انتقال دارایی به اقلام معاف می‌تواند کمک کند.<br />
                ۳. بدهی‌ها و اقساط وام‌های بانکی ثبت‌شده را در فرم لحاظ نمایید.
              </Typography>
            </Box>
          )}

          {/* دکمه ارسال به ربات جهت صدور کارنامه رسمی */}
          <Button
            fullWidth
            variant="contained"
            onClick={handleSendToBot}
            startIcon={<Send sx={{ transform: 'rotate(180deg)' }} />}
            sx={{
              mt: 2.5,
              background: 'linear-gradient(135deg, #B8004F 0%, #6E002B 100%)',
              color: '#FFD700',
              fontWeight: 800,
              border: '1px solid #FFD700',
              py: 1.2,
              borderRadius: 3,
              boxShadow: '0 4px 15px rgba(184, 0, 79, 0.4)',
              '&:hover': {
                background: 'linear-gradient(135deg, #E60067 0%, #B8004F 100%)'
              }
            }}
          >
            🚀 ارسال کارنامه رسمی به ربات تلگرام
          </Button>
        </CardContent>
      </Card>

    </Box>
  );
}
