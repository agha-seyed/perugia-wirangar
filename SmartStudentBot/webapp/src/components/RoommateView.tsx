import { useState } from 'react';
import {
  Box,
  Typography,
  Card,
  CardContent,
  Chip,
  Button,
  TextField,
  InputAdornment,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  MenuItem
} from '@mui/material';
import {
  LocationOn,
  Euro,
  Wifi,
  LocalLaundryService,
  Search,
  PersonAdd,
  Message,
  Balcony,
  AcUnit,
  DoneAll
} from '@mui/icons-material';
import { motion } from 'framer-motion';

interface RoommateAd {
  id: string;
  title: string;
  area: string;
  price: number;
  type: string;
  amenities: string[];
  contact: string;
  description: string;
}

const initialAds: RoommateAd[] = [
  {
    id: '1',
    title: 'اتاق سینگل دلباز نزدیک دانشکده مهندسی',
    area: 'Elce',
    price: 320,
    type: 'اتاق تک‌نفره (Singola)',
    amenities: ['wifi', 'washing', 'balcony'],
    contact: '@perugia_student1',
    description: 'آپارتمان آرام و ۳ خوابه، دسترسی ۳ دقیقه تا دانشکده مهندسی و سوپرمارکت Coop. مناسب مطالعه.'
  },
  {
    id: '2',
    title: 'اتاق مستر در مرکز تاریخی با ویوی پانوراما',
    area: 'Centro Storico',
    price: 380,
    type: 'اتاق تک‌نفره لوکس',
    amenities: ['wifi', 'balcony', 'ac'],
    contact: '@ali_perugia',
    description: 'نزدیک به ایستگاه مینی‌مترو Pincetto و دانشگاه خارجی‌ها (UniStraPg). خانه بازسازی‌شده.'
  },
  {
    id: '3',
    title: 'اتاق دابل اقتصادی برای دو نفر دانشجو',
    area: 'Fontivegge',
    price: 220,
    type: 'تخت در اتاق اشتراکی (Doppia)',
    amenities: ['wifi', 'washing'],
    contact: '@sara_italy',
    description: 'نزدیک ایستگاه قطار مرکزی، ایستگاه اتوبوس‌های بین‌شهری و مرکز خرید Eurospin.'
  },
  {
    id: '4',
    title: 'اتاق سینگل مبله با تراس بزرگ و آرام',
    area: 'Monteluce',
    price: 300,
    type: 'اتاق تک‌نفره',
    amenities: ['wifi', 'washing', 'balcony'],
    contact: '@omid_pg',
    description: 'منطقه بسیار آرام و سرسبز با دسترسی خطوط مستقیم اتوبوس به دانشگاه و مرکز شهر.'
  }
];

export default function RoommateView() {
  const [ads, setAds] = useState<RoommateAd[]>(initialAds);
  const [selectedArea, setSelectedArea] = useState<string>('all');
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [openModal, setOpenModal] = useState<boolean>(false);

  // فرم ثبت آگهی جدید
  const [newTitle, setNewTitle] = useState('');
  const [newArea, setNewArea] = useState('Elce');
  const [newPrice, setNewPrice] = useState('');
  const [newContact, setNewContact] = useState('');
  const [newDesc, setNewDesc] = useState('');

  const areas = ['all', 'Elce', 'Centro Storico', 'Fontivegge', 'Monteluce', 'San Sisto'];

  const filteredAds = ads.filter((ad) => {
    const matchesArea = selectedArea === 'all' || ad.area === selectedArea;
    const matchesSearch =
      ad.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
      ad.area.toLowerCase().includes(searchTerm.toLowerCase()) ||
      ad.description.toLowerCase().includes(searchTerm.toLowerCase());
    return matchesArea && matchesSearch;
  });

  const handleAddAd = () => {
    if (!newTitle.trim() || !newPrice.trim() || !newContact.trim()) {
      alert('لطفاً عنوان، قیمت و آیدی تلگرام را وارد کنید.');
      return;
    }

    const created: RoommateAd = {
      id: Date.now().toString(),
      title: newTitle.trim(),
      area: newArea,
      price: parseInt(newPrice) || 300,
      type: 'آگهی جدید دانشجویی',
      amenities: ['wifi', 'washing'],
      contact: newContact.startsWith('@') ? newContact : `@${newContact}`,
      description: newDesc.trim() || 'اطلاعات بیشتر در چت تلگرام.'
    };

    setAds([created, ...ads]);
    setOpenModal(false);
    setNewTitle('');
    setNewPrice('');
    setNewContact('');
    setNewDesc('');
    alert('✅ آگهی شما با موفقیت ثبت شد و در لیست مینی‌اپ قرار گرفت!');
  };

  return (
    <Box sx={{ p: 2, pb: 11, width: '100%', maxWidth: 520, mx: 'auto', dir: 'rtl' }}>
      
      {/* Title with Teal & Crimson Royal Glow */}
      <Box sx={{ textAlign: 'center', mb: 3 }}>
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
          🏠 هم‌اتاقی و مسکن پروجا
        </Typography>
        <Typography variant="body2" sx={{ color: '#94D2BD', fontSize: '0.82rem' }}>
          جستجو و آگهی مستقیم اتاق و خانه دانشجویی بدون کمیسیون بنگاه
        </Typography>
      </Box>

      {/* جستجو با استایل کله‌غازی و طلایی */}
      <TextField
        fullWidth
        size="small"
        placeholder="جستجوی منطقه، کلمه یا عنوان..."
        value={searchTerm}
        onChange={(e) => setSearchTerm(e.target.value)}
        sx={{
          mb: 2,
          '& .MuiOutlinedInput-root': {
            borderRadius: 3.5,
            background: 'rgba(7, 39, 35, 0.7)',
            backdropFilter: 'blur(10px)',
            color: '#F0FDF4',
            '& fieldset': { borderColor: 'rgba(255, 215, 0, 0.25)' },
            '&:hover fieldset': { borderColor: '#FFD700' },
            '&.Mui-focused fieldset': { borderColor: '#02C39A' }
          }
        }}
        slotProps={{
          input: {
            startAdornment: (
              <InputAdornment position="start">
                <Search sx={{ color: '#FFD700' }} />
              </InputAdornment>
            )
          }
        }}
      />

      {/* فیلتر محله‌ها با تگ‌های شکیل */}
      <Box sx={{ display: 'flex', gap: 1, overflowX: 'auto', pb: 1.5, mb: 2.5 }}>
        {areas.map((area) => {
          const isSelected = selectedArea === area;
          return (
            <Chip
              key={area}
              label={area === 'all' ? 'همه محله‌ها' : area}
              onClick={() => setSelectedArea(area)}
              sx={{
                borderRadius: '16px',
                background: isSelected
                  ? 'linear-gradient(135deg, #B8004F 0%, #6E002B 100%)'
                  : 'rgba(7, 39, 35, 0.6)',
                border: isSelected ? '1px solid #FFD700' : '1px solid rgba(0, 168, 150, 0.25)',
                color: isSelected ? '#FFD700' : '#94D2BD',
                fontWeight: isSelected ? 800 : 500,
                fontSize: '0.78rem',
                boxShadow: isSelected ? '0 0 10px rgba(184, 0, 79, 0.4)' : 'none',
                cursor: 'pointer',
                transition: 'all 0.25s ease'
              }}
            />
          );
        })}
      </Box>

      {/* دکمه ثبت آگهی جدید */}
      <Button
        fullWidth
        variant="contained"
        startIcon={<PersonAdd />}
        onClick={() => setOpenModal(true)}
        sx={{
          mb: 3,
          py: 1.2,
          borderRadius: 3.5,
          background: 'linear-gradient(135deg, #00A896 0%, #00564D 100%)',
          border: '1px solid rgba(255, 215, 0, 0.35)',
          color: '#FFFFFF',
          fontWeight: 800,
          boxShadow: '0 4px 15px rgba(0, 168, 150, 0.35)',
          '&:hover': {
            background: 'linear-gradient(135deg, #02C39A 0%, #00A896 100%)',
            boxShadow: '0 6px 20px rgba(0, 168, 150, 0.55)'
          }
        }}
      >
        ➕ ثبت آگهی اتاق یا هم‌اتاقی جدید
      </Button>

      {/* لیست آگهی‌ها */}
      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
        {filteredAds.map((ad, idx) => (
          <motion.div
            key={ad.id}
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: idx * 0.08 }}
          >
            <Card sx={{
              background: 'linear-gradient(145deg, rgba(7, 39, 35, 0.85) 0%, rgba(4, 25, 22, 0.95) 100%)',
              backdropFilter: 'blur(16px)',
              border: '1px solid rgba(255, 215, 0, 0.22)',
              borderRadius: 4,
              boxShadow: '0 8px 24px rgba(0,0,0,0.45)',
              overflow: 'hidden'
            }}>
              <CardContent sx={{ p: 2.5 }}>
                {/* Header: Title & Price Tag */}
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 1 }}>
                  <Typography variant="subtitle1" sx={{ fontWeight: 800, color: '#FFFFFF', fontSize: '0.95rem', flex: 1, pr: 1 }}>
                    {ad.title}
                  </Typography>
                  <Box sx={{
                    background: 'linear-gradient(135deg, rgba(184, 0, 79, 0.3) 0%, rgba(255, 215, 0, 0.15) 100%)',
                    border: '1px solid #FFD700',
                    borderRadius: 2,
                    px: 1.2,
                    py: 0.3,
                    display: 'flex',
                    alignItems: 'center',
                    gap: 0.3,
                    boxShadow: '0 0 10px rgba(255, 215, 0, 0.25)'
                  }}>
                    <Typography variant="subtitle2" sx={{ fontWeight: 900, color: '#FFD700' }}>
                      {ad.price}
                    </Typography>
                    <Euro sx={{ fontSize: 15, color: '#FFD700' }} />
                    <Typography variant="caption" sx={{ color: '#94D2BD', fontSize: '0.65rem' }}>
                      /ماه
                    </Typography>
                  </Box>
                </Box>

                {/* Subtitle: Location & Type */}
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.8, color: '#02C39A', mb: 1.5, fontSize: '0.8rem' }}>
                  <LocationOn sx={{ fontSize: 16, color: '#FFD700' }} />
                  <span style={{ fontWeight: 700 }}>{ad.area}</span>
                  <span style={{ opacity: 0.4 }}>•</span>
                  <span style={{ color: '#94D2BD' }}>{ad.type}</span>
                </Box>

                {/* Description */}
                <Typography variant="body2" sx={{ color: '#E0F2E9', mb: 2, lineHeight: 1.6, fontSize: '0.82rem' }}>
                  {ad.description}
                </Typography>

                {/* Amenities */}
                <Box sx={{ display: 'flex', gap: 1, mb: 2, flexWrap: 'wrap' }}>
                  {ad.amenities.includes('wifi') && (
                    <Chip size="small" icon={<Wifi sx={{ fontSize: '13px !important', color: '#02C39A !important' }} />} label="وای‌فای" sx={{ background: 'rgba(0,168,150,0.15)', color: '#02C39A', fontSize: '0.7rem' }} />
                  )}
                  {ad.amenities.includes('washing') && (
                    <Chip size="small" icon={<LocalLaundryService sx={{ fontSize: '13px !important', color: '#B8004F !important' }} />} label="لباسشویی" sx={{ background: 'rgba(184,0,79,0.15)', color: '#E60067', fontSize: '0.7rem' }} />
                  )}
                  {ad.amenities.includes('balcony') && (
                    <Chip size="small" icon={<Balcony sx={{ fontSize: '13px !important', color: '#FFD700 !important' }} />} label="بالکن" sx={{ background: 'rgba(255,215,0,0.12)', color: '#FFD700', fontSize: '0.7rem' }} />
                  )}
                  {ad.amenities.includes('ac') && (
                    <Chip size="small" icon={<AcUnit sx={{ fontSize: '13px !important', color: '#00A896 !important' }} />} label="اسپلیت" sx={{ background: 'rgba(0,168,150,0.15)', color: '#00A896', fontSize: '0.7rem' }} />
                  )}
                </Box>

                {/* Contact Button */}
                <Button
                  fullWidth
                  variant="outlined"
                  startIcon={<Message />}
                  onClick={() => {
                    const username = ad.contact.replace('@', '');
                    window.open(`https://t.me/${username}`, '_blank');
                  }}
                  sx={{
                    borderColor: 'rgba(184, 0, 79, 0.7)',
                    background: 'rgba(184, 0, 79, 0.15)',
                    color: '#FFFFFF',
                    borderRadius: 2.5,
                    fontWeight: 700,
                    fontSize: '0.82rem',
                    textTransform: 'none',
                    py: 0.8,
                    '&:hover': {
                      borderColor: '#FFD700',
                      background: 'rgba(184, 0, 79, 0.35)',
                      boxShadow: '0 0 12px rgba(184, 0, 79, 0.4)'
                    }
                  }}
                >
                  ارتباط تلگرامی با مالک ({ad.contact})
                </Button>
              </CardContent>
            </Card>
          </motion.div>
        ))}
      </Box>

      {/* Modal: ثبت آگهی جدید */}
      <Dialog
        open={openModal}
        onClose={() => setOpenModal(false)}
        slotProps={{
          paper: {
            sx: {
              background: 'linear-gradient(145deg, #072723 0%, #031715 100%)',
              border: '1px solid rgba(255, 215, 0, 0.35)',
              borderRadius: 4,
              color: '#F0FDF4',
              maxWidth: 420,
              p: 1
            }
          }
        }}
      >
        <DialogTitle sx={{ color: '#FFD700', fontWeight: 900, textAlign: 'center' }}>
          ثبت آگهی هم‌اتاقی در پروجا
        </DialogTitle>
        <DialogContent sx={{ display: 'flex', flexDirection: 'column', gap: 2, pt: 1 }}>
          <TextField
            label="عنوان آگهی (مثال: اتاق تک‌نفره السه)"
            size="small"
            fullWidth
            value={newTitle}
            onChange={(e) => setNewTitle(e.target.value)}
            slotProps={{ inputLabel: { sx: { color: '#94D2BD' } } }}
            sx={{ '& .MuiOutlinedInput-root': { color: '#fff', '& fieldset': { borderColor: 'rgba(0,168,150,0.4)' } } }}
          />
          <TextField
            select
            label="محله"
            size="small"
            fullWidth
            value={newArea}
            onChange={(e) => setNewArea(e.target.value)}
            slotProps={{ inputLabel: { sx: { color: '#94D2BD' } } }}
            sx={{ '& .MuiOutlinedInput-root': { color: '#fff', '& fieldset': { borderColor: 'rgba(0,168,150,0.4)' } } }}
          >
            {areas.filter(a => a !== 'all').map((a) => (
              <MenuItem key={a} value={a}>{a}</MenuItem>
            ))}
          </TextField>
          <TextField
            label="اجاره ماهانه (€ یورو)"
            size="small"
            type="number"
            fullWidth
            value={newPrice}
            onChange={(e) => setNewPrice(e.target.value)}
            slotProps={{ inputLabel: { sx: { color: '#94D2BD' } } }}
            sx={{ '& .MuiOutlinedInput-root': { color: '#fff', '& fieldset': { borderColor: 'rgba(0,168,150,0.4)' } } }}
          />
          <TextField
            label="آیدی تلگرام برای تماس (مثال: @username)"
            size="small"
            fullWidth
            value={newContact}
            onChange={(e) => setNewContact(e.target.value)}
            slotProps={{ inputLabel: { sx: { color: '#94D2BD' } } }}
            sx={{ '& .MuiOutlinedInput-root': { color: '#fff', '& fieldset': { borderColor: 'rgba(0,168,150,0.4)' } } }}
          />
          <TextField
            label="توضیحات و امکانات"
            multiline
            rows={3}
            size="small"
            fullWidth
            value={newDesc}
            onChange={(e) => setNewDesc(e.target.value)}
            slotProps={{ inputLabel: { sx: { color: '#94D2BD' } } }}
            sx={{ '& .MuiOutlinedInput-root': { color: '#fff', '& fieldset': { borderColor: 'rgba(0,168,150,0.4)' } } }}
          />
        </DialogContent>
        <DialogActions sx={{ p: 2, justifyContent: 'space-between' }}>
          <Button onClick={() => setOpenModal(false)} sx={{ color: '#94D2BD' }}>
            انصراف
          </Button>
          <Button
            variant="contained"
            onClick={handleAddAd}
            startIcon={<DoneAll />}
            sx={{
              background: 'linear-gradient(135deg, #B8004F 0%, #6E002B 100%)',
              color: '#FFD700',
              fontWeight: 800,
              border: '1px solid #FFD700'
            }}
          >
            ثبت و انتشار
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
