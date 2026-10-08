import React, { useState, useEffect } from 'react';
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
  MenuItem,
  IconButton
} from '@mui/material';
import {
  Storefront,
  DirectionsBike,
  Computer,
  MenuBook,
  Kitchen,
  Search,
  AddCircle,
  Close,
  LocationOn,
  Message,
  Category,
  Euro
} from '@mui/icons-material';
import { API_BASE } from '../apiConfig';

interface MarketItem {
  id: string;
  title: string;
  category: string;
  price: number;
  area: string;
  contact: string;
  description: string;
  date?: string;
}

const INITIAL_MARKET_ITEMS: MarketItem[] = [
  {
    id: 'm1',
    title: 'دوچرخه شهری Perugia City Bike (۷ دنده)',
    category: 'bike',
    price: 70,
    area: 'Elce',
    contact: '@ali_perugia',
    description: 'همراه با قفل زنجیری فولادی و چراغ شب. کاملاً سالم و مناسب رفت‌وآمد به دانشگاه.',
    date: 'امروز'
  },
  {
    id: 'm2',
    title: 'مانیتور ۲۴ اینچ Dell IPS با کابل HDMI',
    category: 'digital',
    price: 85,
    area: 'Centro Storico',
    contact: '@sara_student',
    description: 'فوق‌العاده تمیز، بدون هیچ خط و خش. مناسب برنامه‌نویسی و مطالعه طولانی.',
    date: 'دیروز'
  },
  {
    id: 'm3',
    title: 'پکیج کتاب‌های آموزش ایتالیایی Nuovo Espresso 1,2,3',
    category: 'book',
    price: 30,
    area: 'Fontivegge',
    contact: '@omid_pg',
    description: 'کتاب‌های اورجینال به همراه سی‌دی‌های صوتی و حل‌المسائل گرامر.',
    date: '۳ روز پیش'
  },
  {
    id: 'm4',
    title: 'هیتر برقی فن‌دار کم‌مصرف DeLonghi',
    category: 'home',
    price: 20,
    area: 'Elce',
    contact: '@perugia_reza',
    description: 'گرمایش عالی و بی‌صدا برای اتاق خوابگاه یا خانه اجاره‌ای در زمستان.',
    date: '۴ روز پیش'
  },
  {
    id: 'm5',
    title: 'سرویس قابلمه تفلون، ماهیتابه و ظروف دانشجویی',
    category: 'home',
    price: 25,
    area: 'Monteluce',
    contact: '@student_pg',
    description: 'ست کامل آماده برای آشپزی بدون نیاز به خرید وسایل نو از ایکیا.',
    date: 'هفته گذشته'
  }
];

export default function MarketView() {
  const [items, setItems] = useState<MarketItem[]>(INITIAL_MARKET_ITEMS);
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [openModal, setOpenModal] = useState<boolean>(false);

  // فرم ثبت آگهی کالا
  const [newTitle, setNewTitle] = useState('');
  const [newCategory, setNewCategory] = useState('home');
  const [newPrice, setNewPrice] = useState('');
  const [newArea, setNewArea] = useState('Elce');
  const [newContact, setNewContact] = useState('');
  const [newDesc, setNewDesc] = useState('');

  // دریافت آیتم‌ها از بک‌اند در صورت موجود بودن
  useEffect(() => {
    fetch(`${API_BASE}/api/v1/webapp/market`)
      .then((res) => res.json())
      .then((data) => {
        if (data.items && data.items.length > 0) {
          setItems([...data.items, ...INITIAL_MARKET_ITEMS]);
        }
      })
      .catch(() => {});
  }, []);

  const filteredItems = items.filter((item) => {
    const matchCat = selectedCategory === 'all' || item.category === selectedCategory;
    const matchSearch =
      item.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      item.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
      item.area.toLowerCase().includes(searchQuery.toLowerCase());
    return matchCat && matchSearch;
  });

  const getCategoryIcon = (cat: string) => {
    switch (cat) {
      case 'bike': return <DirectionsBike sx={{ color: '#02C39A' }} />;
      case 'digital': return <Computer sx={{ color: '#FFD700' }} />;
      case 'book': return <MenuBook sx={{ color: '#94D2BD' }} />;
      case 'home': default: return <Kitchen sx={{ color: '#FFB703' }} />;
    }
  };

  const handleCreateItem = async () => {
    if (!newTitle.trim() || !newPrice.trim() || !newContact.trim()) {
      alert('لطفاً عنوان کالا، قیمت و آیدی تلگرام را وارد فرمایید.');
      return;
    }

    const newItem: MarketItem = {
      id: `m_${Date.now()}`,
      title: newTitle.trim(),
      category: newCategory,
      price: parseFloat(newPrice) || 20,
      area: newArea,
      contact: newContact.startsWith('@') ? newContact : `@${newContact}`,
      description: newDesc.trim() || 'وسایل سالم و تحویل حضوری در پروجا.',
      date: 'لحظاتی پیش'
    };

    // ذخیره در وضعیت کلاینت
    setItems([newItem, ...items]);

    // ارسال به سرور
    try {
      await fetch(`${API_BASE}/api/v1/webapp/market`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newItem)
      });
    } catch (_) {}

    setOpenModal(false);
    setNewTitle('');
    setNewPrice('');
    setNewContact('');
    setNewDesc('');
    alert('✅ آگهی کالای شما با موفقیت ثبت شد!');
  };

  const handleContactSeller = (contact: string) => {
    const clean = contact.replace('@', '');
    const tg = (window as any).Telegram?.WebApp;
    if (tg?.openTelegramLink) {
      tg.openTelegramLink(`https://t.me/${clean}`);
    } else {
      window.open(`https://t.me/${clean}`, '_blank');
    }
  };

  return (
    <Box sx={{ p: 2, pb: 12, width: '100%', maxWidth: 520, mx: 'auto', dir: 'rtl' }}>
      
      {/* هدر بازارچه */}
      <Box sx={{ textAlign: 'center', mb: 2.5 }}>
        <Box sx={{ display: 'inline-flex', p: 1.5, borderRadius: '50%', background: 'rgba(255, 183, 3, 0.15)', mb: 1, border: '1px solid #FFB703' }}>
          <Storefront sx={{ fontSize: 36, color: '#FFB703' }} />
        </Box>
        <Typography
          variant="h5"
          sx={{
            fontWeight: 900,
            background: 'linear-gradient(135deg, #FFF099 0%, #FFD700 50%, #FFB703 100%)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
            filter: 'drop-shadow(0 2px 8px rgba(255, 183, 3, 0.3))',
            mb: 0.5
          }}
        >
          بازارچه دست‌دوم دانشجویی پروجا
        </Typography>
        <Typography variant="caption" sx={{ color: '#94D2BD', display: 'block' }}>
          خرید و فروش بی‌واسطه لوازم منزل، دوچرخه، کتاب و مانیتور میان دانشجویان
        </Typography>
      </Box>

      {/* دکمه ثبت آگهی کالا */}
      <Button
        fullWidth
        variant="contained"
        onClick={() => setOpenModal(true)}
        startIcon={<AddCircle />}
        sx={{
          mb: 2,
          py: 1.2,
          borderRadius: 3,
          background: 'linear-gradient(135deg, #B8004F 0%, #6E002B 100%)',
          color: '#FFD700',
          fontWeight: 900,
          border: '1px solid #FFD700',
          boxShadow: '0 4px 15px rgba(184, 0, 79, 0.4)'
        }}
      >
        ➕ ثبت آگهی کالای جدید
      </Button>

      {/* جستجو */}
      <TextField
        fullWidth
        size="small"
        placeholder="جستجو در بین آگهی‌های کالا..."
        value={searchQuery}
        onChange={(e) => setSearchQuery(e.target.value)}
        slotProps={{
          input: {
            startAdornment: (
              <InputAdornment position="start">
                <Search sx={{ color: '#94D2BD' }} />
              </InputAdornment>
            )
          }
        }}
        sx={{
          mb: 1.5,
          '& .MuiOutlinedInput-root': {
            background: 'rgba(7, 39, 35, 0.7)',
            borderRadius: 3,
            color: '#fff',
            '& fieldset': { borderColor: 'rgba(255, 215, 0, 0.25)' }
          }
        }}
      />

      {/* فیلتر دسته‌بندی‌ها */}
      <Box sx={{ display: 'flex', gap: 1, overflowX: 'auto', pb: 1, mb: 2 }}>
        {[
          { id: 'all', label: 'همه اجناس', icon: <Category fontSize="small" /> },
          { id: 'bike', label: 'دوچرخه و نقلیه', icon: <DirectionsBike fontSize="small" /> },
          { id: 'digital', label: 'دیجیتال و لپ‌تاپ', icon: <Computer fontSize="small" /> },
          { id: 'book', label: 'کتب آموزشی', icon: <MenuBook fontSize="small" /> },
          { id: 'home', label: 'وسایل منزل', icon: <Kitchen fontSize="small" /> },
        ].map((cat) => (
          <Chip
            key={cat.id}
            icon={cat.icon}
            label={cat.label}
            onClick={() => setSelectedCategory(cat.id)}
            sx={{
              background: selectedCategory === cat.id ? 'linear-gradient(135deg, #FFB703 0%, #D48B00 100%)' : 'rgba(7, 39, 35, 0.6)',
              color: selectedCategory === cat.id ? '#031715' : '#94D2BD',
              border: selectedCategory === cat.id ? '1px solid #FFD700' : '1px solid rgba(255, 215, 0, 0.15)',
              fontWeight: 800,
              fontSize: '0.75rem',
              cursor: 'pointer'
            }}
          />
        ))}
      </Box>

      {/* لیست کارت‌های آگهی بازارچه */}
      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
        {filteredItems.map((item) => (
          <Card
            key={item.id}
            sx={{
              borderRadius: 3.5,
              background: 'linear-gradient(145deg, rgba(7, 39, 35, 0.9) 0%, rgba(3, 23, 21, 0.95) 100%)',
              border: '1px solid rgba(255, 215, 0, 0.2)',
              boxShadow: '0 6px 20px rgba(0, 0, 0, 0.4)'
            }}
          >
            <CardContent sx={{ p: 2, '&:last-child': { pb: 2 } }}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 1 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.2 }}>
                  <Box sx={{ p: 1, borderRadius: 2, background: 'rgba(255, 215, 0, 0.1)', border: '1px solid rgba(255, 215, 0, 0.2)' }}>
                    {getCategoryIcon(item.category)}
                  </Box>
                  <Box>
                    <Typography variant="subtitle2" sx={{ color: '#fff', fontWeight: 900, fontSize: '0.88rem' }}>
                      {item.title}
                    </Typography>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mt: 0.3 }}>
                      <LocationOn sx={{ color: '#02C39A', fontSize: 14 }} />
                      <Typography variant="caption" sx={{ color: '#94D2BD' }}>
                        {item.area} {item.date ? `• ${item.date}` : ''}
                      </Typography>
                    </Box>
                  </Box>
                </Box>

                <Box sx={{ textAlign: 'left' }}>
                  <Typography variant="h6" sx={{ color: '#FFD700', fontWeight: 900, lineHeight: 1 }}>
                    {item.price} €
                  </Typography>
                </Box>
              </Box>

              <Typography variant="body2" sx={{ color: '#D8F3DC', fontSize: '0.8rem', lineHeight: 1.6, my: 1 }}>
                {item.description}
              </Typography>

              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', pt: 1, borderTop: '1px solid rgba(255, 215, 0, 0.12)' }}>
                <Typography variant="caption" sx={{ color: '#70A9A1' }}>
                  فروشنده: <b>{item.contact}</b>
                </Typography>
                <Button
                  size="small"
                  variant="outlined"
                  onClick={() => handleContactSeller(item.contact)}
                  startIcon={<Message fontSize="small" />}
                  sx={{
                    borderColor: 'rgba(2, 195, 154, 0.4)',
                    color: '#02C39A',
                    fontWeight: 800,
                    fontSize: '0.72rem',
                    borderRadius: 2,
                    textTransform: 'none'
                  }}
                >
                  چت در تلگرام
                </Button>
              </Box>
            </CardContent>
          </Card>
        ))}
      </Box>

      {/* مودال ثبت آگهی کالا */}
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
              maxWidth: 480,
              width: '95%',
              p: 1
            }
          }
        }}
      >
        <DialogTitle sx={{ color: '#FFD700', fontWeight: 900, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span>➕ ثبت کالای جدید در بازارچه</span>
          <IconButton onClick={() => setOpenModal(false)} sx={{ color: '#94D2BD' }} size="small">
            <Close />
          </IconButton>
        </DialogTitle>
        <DialogContent sx={{ display: 'flex', flexDirection: 'column', gap: 2, pt: 1 }}>
          <TextField
            label="عنوان کالا (مثلاً: دوچرخه شهری)"
            size="small"
            value={newTitle}
            onChange={(e) => setNewTitle(e.target.value)}
            slotProps={{ inputLabel: { sx: { color: '#94D2BD' } } }}
            sx={{ '& .MuiOutlinedInput-root': { color: '#fff' } }}
          />

          <TextField
            select
            label="دسته‌بندی"
            size="small"
            value={newCategory}
            onChange={(e) => setNewCategory(e.target.value)}
            slotProps={{ inputLabel: { sx: { color: '#94D2BD' } } }}
            sx={{ '& .MuiOutlinedInput-root': { color: '#fff' } }}
          >
            <MenuItem value="bike">دوچرخه و نقلیه</MenuItem>
            <MenuItem value="digital">لپ‌تاپ و وسایل دیجیتال</MenuItem>
            <MenuItem value="book">کتب و جزوات آموزشی</MenuItem>
            <MenuItem value="home">وسایل منزل و اتاق</MenuItem>
          </TextField>

          <TextField
            label="قیمت پیشنهادی (یورو €)"
            type="number"
            size="small"
            value={newPrice}
            onChange={(e) => setNewPrice(e.target.value)}
            slotProps={{ inputLabel: { sx: { color: '#94D2BD' } } }}
            sx={{ '& .MuiOutlinedInput-root': { color: '#fff' } }}
          />

          <TextField
            select
            label="منطقه تحویل در پروجا"
            size="small"
            value={newArea}
            onChange={(e) => setNewArea(e.target.value)}
            slotProps={{ inputLabel: { sx: { color: '#94D2BD' } } }}
            sx={{ '& .MuiOutlinedInput-root': { color: '#fff' } }}
          >
            <MenuItem value="Elce">Elce (نزدیک مهندسی)</MenuItem>
            <MenuItem value="Centro Storico">Centro Storico (مرکز شهر)</MenuItem>
            <MenuItem value="Fontivegge">Fontivegge (نزدیک قطار)</MenuItem>
            <MenuItem value="Monteluce">Monteluce</MenuItem>
            <MenuItem value="San Sisto">San Sisto (پزشکی)</MenuItem>
          </TextField>

          <TextField
            label="آیدی تلگرام برای ارتباط (مثلاً: student_pg@)"
            size="small"
            value={newContact}
            onChange={(e) => setNewContact(e.target.value)}
            slotProps={{ inputLabel: { sx: { color: '#94D2BD' } } }}
            sx={{ '& .MuiOutlinedInput-root': { color: '#fff' } }}
          />

          <TextField
            label="توضیحات و وضعیت کالا"
            multiline
            rows={2}
            size="small"
            value={newDesc}
            onChange={(e) => setNewDesc(e.target.value)}
            slotProps={{ inputLabel: { sx: { color: '#94D2BD' } } }}
            sx={{ '& .MuiOutlinedInput-root': { color: '#fff' } }}
          />
        </DialogContent>
        <DialogActions sx={{ p: 2, justifyContent: 'space-between' }}>
          <Button onClick={() => setOpenModal(false)} sx={{ color: '#94D2BD' }}>
            انصراف
          </Button>
          <Button
            variant="contained"
            onClick={handleCreateItem}
            sx={{
              background: 'linear-gradient(135deg, #00A896 0%, #02C39A 100%)',
              color: '#031715',
              fontWeight: 900
            }}
          >
            تایید و انتشار آگهی
          </Button>
        </DialogActions>
      </Dialog>

    </Box>
  );
}
