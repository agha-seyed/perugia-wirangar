import React, { useState, useEffect, useRef } from 'react';
import {
  Box,
  Typography,
  Card,
  CardContent,
  Chip,
  Button,
  IconButton,
  TextField,
  InputAdornment
} from '@mui/material';
import {
  LocationOn,
  Directions,
  Schedule,
  Search,
  Apartment,
  School,
  Kitchen,
  Train,
  Map,
  OpenInNew,
  MyLocation
} from '@mui/icons-material';
import L from 'leaflet';

interface PlaceItem {
  id: string;
  name: string;
  name_it: string;
  category: 'gov' | 'uni' | 'canteen' | 'transit';
  category_fa: string;
  lat: number;
  lng: number;
  address: string;
  hours: string;
  desc: string;
  color: string;
}

const PERUGIA_PLACES: PlaceItem[] = [
  {
    id: "questura",
    name: "Questura di Perugia (اداره پلیس مهاجرت)",
    name_it: "Questura - Ufficio Immigrazione",
    category: "gov",
    category_fa: "ادارات دولتی",
    lat: 43.0800,
    lng: 12.3420,
    address: "Via del Tabacchificio, 21, Ellera di Corciano",
    hours: "دوشنبه تا جمعه ۸:۳۰ - ۱۲:۳۰",
    desc: "محل انجام انگشت‌نگاری و تحویل کارت فیزیکی پرمسو دی سوجورنو (اقامت تحصیلی).",
    color: "#E63946"
  },
  {
    id: "agenzia",
    name: "Agenzia delle Entrate (اداره مالیات)",
    name_it: "Agenzia delle Entrate - Ufficio Territoriale",
    category: "gov",
    category_fa: "ادارات دولتی",
    lat: 43.10895,
    lng: 12.38885,
    address: "Via Canali, 12, 06124 Perugia",
    hours: "دوشنبه تا جمعه ۸:۳۰ - ۱۳:۰۰ (با نوبت آنلاین)",
    desc: "صدور رایگان کد مالیاتی (Codice Fiscale) و ثبت رسمی قراردادهای اجاره مسکن.",
    color: "#E63946"
  },
  {
    id: "poste",
    name: "Poste Italiane Centrale (پست مرکزی)",
    name_it: "Poste Italiane - Perugia Centro",
    category: "gov",
    category_fa: "ادارات دولتی",
    lat: 43.11072,
    lng: 12.38918,
    address: "Piazza Giacomo Matteotti, 14",
    hours: "دوشنبه تا جمعه ۸:۲۰ - ۱۹:۰۵، شنبه تا ۱۲:۳۵",
    desc: "دریافت و ارسال کیت زرد پرمسو، افتتاح کارت بانکی Postepay Evolution و پرداخت فیش‌های دولتی.",
    color: "#E63946"
  },
  {
    id: "adisu",
    name: "ADiSU Umbria (امور بورس و خوابگاه)",
    name_it: "ADiSU Umbria - Sede Centrale",
    category: "gov",
    category_fa: "ادارات دولتی",
    lat: 43.1190,
    lng: 12.3880,
    address: "Via Benedetta, 14, Perugia",
    hours: "دوشنبه تا پنجشنبه ۹:۰۰ - ۱۳:۰۰",
    desc: "مرکز اداری بورس استانی، امضای قرارداد خوابگاه دانشجویی و پیگیری کارت سلف سرویس.",
    color: "#B8004F"
  },
  {
    id: "uni_main",
    name: "دانشگاه پروجا - ساختمان مرکزی",
    name_it: "Università degli Studi di Perugia (Rettorato)",
    category: "uni",
    category_fa: "دانشگاه‌ها",
    lat: 43.1160,
    lng: 12.3860,
    address: "Piazza dell'Università, 1",
    hours: "دوشنبه تا جمعه ۸:۳۰ - ۱۸:۰۰",
    desc: "ساختمان ریاست دانشگاه، دبیرخانه مرکزی و اداره روابط بین‌الملل دانشجویان خارجی.",
    color: "#FFD700"
  },
  {
    id: "engineering",
    name: "دانشکده مهندسی UniPG",
    name_it: "Polo d'Ingegneria UniPG",
    category: "uni",
    category_fa: "دانشگاه‌ها",
    lat: 43.0990,
    lng: 12.3750,
    address: "Via Goffredo Duranti, 93 (منطقه Elce)",
    hours: "دوشنبه تا جمعه ۸:۰۰ - ۱۹:۳۰",
    desc: "دانشکده مهندسی برق، عمران، کامپیوتر، مکانیک و کتابخانه‌های تخصصی.",
    color: "#FFD700"
  },
  {
    id: "medicine",
    name: "دانشکده پزشکی و جراحی",
    name_it: "Polo Didattico di Medicina",
    category: "uni",
    category_fa: "دانشگاه‌ها",
    lat: 43.1040,
    lng: 12.3900,
    address: "Piazzale Lucio Severi, 1 (Ospedale Silvestrini)",
    hours: "دوشنبه تا جمعه ۸:۰۰ - ۱۸:۰۰",
    desc: "پردیس علوم پزشکی، داروسازی و بیمارستان آموزشی پروجا.",
    color: "#FFD700"
  },
  {
    id: "mensa_pascoli",
    name: "سلف مرکزی دانشگاه (Mensa Pascoli)",
    name_it: "Mensa Universitaria Via Pascoli",
    category: "canteen",
    category_fa: "سلف و غذاخوری",
    lat: 43.1180,
    lng: 12.3840,
    address: "Via Giovanni Pascoli, 23",
    hours: "ناهار ۱۲:۰۰ - ۱۴:۳۰ | شام ۱۹:۰۰ - ۲۱:۱۵",
    desc: "سلف اصلی دانشگاه پروجا با سالن بزرگ پیتزا و غذای کامل با کارت بورس ادیسو.",
    color: "#02C39A"
  },
  {
    id: "mensa_innamorati",
    name: "سلف دانشجویی الچه (Mensa Elce)",
    name_it: "Mensa Innamorati",
    category: "canteen",
    category_fa: "سلف و غذاخوری",
    lat: 43.1195,
    lng: 12.3785,
    address: "Via degli Innamorati, 3",
    hours: "ناهار ۱۲:۱۵ - ۱۴:۱۵",
    desc: "سلف نزدیک دانشکده مهندسی و علوم تربیتی در منطقه دانشجویی الچه.",
    color: "#02C39A"
  },
  {
    id: "fontivegge",
    name: "ایستگاه قطار مرکزی (Fontivegge)",
    name_it: "Stazione Ferroviaria Perugia Fontivegge",
    category: "transit",
    category_fa: "حمل‌ونقل",
    lat: 43.1048,
    lng: 12.3752,
    address: "Piazza Vittorio Veneto",
    hours: "۲۴ ساعته",
    desc: "ایستگاه اصلی قطارهای بین‌شهری به سمت رم، فلورانس و فرودگاه‌ها + ترمینال اتوبوس.",
    color: "#00A896"
  },
  {
    id: "minimetro_pincetto",
    name: "مینی‌مترو Pincetto (مرکز شهر)",
    name_it: "Minimetrò Pincetto - Centro Storico",
    category: "transit",
    category_fa: "حمل‌ونقل",
    lat: 43.1085,
    lng: 12.3912,
    address: "Via Pincetto, Centro Storico",
    hours: "۷:۰۰ صبح تا ۲۱:۲۰ شب",
    desc: "ایستگاه نهایی مینی‌مترو در مرکز تاریخی و دسترسی سریع به میدان ۴ نوامبر و خیابان وانتوچی.",
    color: "#00A896"
  },
  {
    id: "minimetro_cupa",
    name: "ایستگاه مینی‌مترو Cupa",
    name_it: "Minimetrò Cupa",
    category: "transit",
    category_fa: "حمل‌ونقل",
    lat: 43.1130,
    lng: 12.3820,
    address: "Via Pellini / Cupa",
    hours: "۷:۰۰ صبح تا ۲۱:۲۰ شب",
    desc: "مجهز به پله‌برقی به سمت دانشکده حقوق و سلف غذاخوری پاسکولی.",
    color: "#00A896"
  }
];

export default function PlacesMapView() {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<L.Map | null>(null);
  const markersRef = useRef<{ [key: string]: L.Marker }>({});

  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [activePlace, setActivePlace] = useState<PlaceItem>(PERUGIA_PLACES[0]);

  // فیلتر مکان‌ها
  const filteredPlaces = PERUGIA_PLACES.filter((p) => {
    const matchCat = selectedCategory === 'all' || p.category === selectedCategory;
    const matchSearch =
      p.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      p.name_it.toLowerCase().includes(searchQuery.toLowerCase()) ||
      p.address.toLowerCase().includes(searchQuery.toLowerCase());
    return matchCat && matchSearch;
  });

  // راه‌اندازی نقشه Leaflet
  useEffect(() => {
    if (!mapContainerRef.current) return;

    if (!mapInstanceRef.current) {
      // ایجاد نمونه نقشه متمرکز روی پروجا
      const map = L.map(mapContainerRef.current, {
        center: [43.1107, 12.3890],
        zoom: 13,
        zoomControl: false
      });

      // افزودن لایه کاشی با استایل مناسب
      L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png', {
        attribution: '&copy; OpenStreetMap & CartoDB',
        maxZoom: 19
      }).addTo(map);

      mapInstanceRef.current = map;
    }

    const map = mapInstanceRef.current;

    // پاکسازی مارکرهای قبلی
    Object.values(markersRef.current).forEach((m) => m.remove());
    markersRef.current = {};

    // افزودن مارکرهای جدید
    filteredPlaces.forEach((place) => {
      // آیکون سفارشی شیک
      const customIcon = L.divIcon({
        className: 'custom-map-pin',
        html: `
          <div style="
            background: ${place.color};
            width: 32px;
            height: 32px;
            border-radius: 50% 50% 50% 0;
            transform: rotate(-45deg);
            display: flex;
            align-items: center;
            justify-content: center;
            border: 2px solid #FFFFFF;
            box-shadow: 0 4px 12px rgba(0,0,0,0.4);
            cursor: pointer;
          ">
            <div style="
              width: 12px;
              height: 12px;
              background: #031715;
              border-radius: 50%;
            "></div>
          </div>
        `,
        iconSize: [32, 32],
        iconAnchor: [16, 32]
      });

      const marker = L.marker([place.lat, place.lng], { icon: customIcon }).addTo(map);

      marker.on('click', () => {
        setActivePlace(place);
        map.flyTo([place.lat, place.lng], 15, { duration: 1 });
      });

      markersRef.current[place.id] = marker;
    });
  }, [selectedCategory, searchQuery]);

  const handleSelectPlace = (place: PlaceItem) => {
    setActivePlace(place);
    if (mapInstanceRef.current) {
      mapInstanceRef.current.flyTo([place.lat, place.lng], 15, { duration: 1.2 });
    }
  };

  const handleOpenGoogleMaps = (place: PlaceItem) => {
    window.open(`https://www.google.com/maps/dir/?api=1&destination=${place.lat},${place.lng}`, '_blank');
  };

  return (
    <Box sx={{ p: 2, pb: 12, width: '100%', maxWidth: 540, mx: 'auto', dir: 'rtl' }}>
      
      {/* عنوان بخش */}
      <Box sx={{ textAlign: 'center', mb: 2 }}>
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
          📍 نقشه تعاملی و مراکز مهم پروجا
        </Typography>
        <Typography variant="caption" sx={{ color: '#94D2BD', display: 'block' }}>
          دسترسی سریع به اداره پلیس، مالیات، سلف‌های ادیسو، دانشگاه‌ها و حمل‌ونقل
        </Typography>
      </Box>

      {/* جستجو */}
      <TextField
        fullWidth
        size="small"
        placeholder="جستجوی مرکز، اداره یا سلف..."
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
      <Box sx={{ display: 'flex', gap: 1, overflowX: 'auto', pb: 1, mb: 1.5 }}>
        {[
          { id: 'all', label: 'همه', icon: <Map fontSize="small" /> },
          { id: 'gov', label: 'ادارات دولتی', icon: <Apartment fontSize="small" /> },
          { id: 'uni', label: 'دانشگاه‌ها', icon: <School fontSize="small" /> },
          { id: 'canteen', label: 'سلف‌ها', icon: <Kitchen fontSize="small" /> },
          { id: 'transit', label: 'حمل‌ونقل', icon: <Train fontSize="small" /> },
        ].map((cat) => (
          <Chip
            key={cat.id}
            icon={cat.icon}
            label={cat.label}
            onClick={() => setSelectedCategory(cat.id)}
            sx={{
              background: selectedCategory === cat.id ? 'linear-gradient(135deg, #B8004F 0%, #6E002B 100%)' : 'rgba(7, 39, 35, 0.6)',
              color: selectedCategory === cat.id ? '#FFD700' : '#94D2BD',
              border: selectedCategory === cat.id ? '1px solid #FFD700' : '1px solid rgba(255, 215, 0, 0.15)',
              fontWeight: 800,
              fontSize: '0.75rem',
              cursor: 'pointer'
            }}
          />
        ))}
      </Box>

      {/* قاب نقشه تعاملی Leaflet */}
      <Box
        sx={{
          position: 'relative',
          width: '100%',
          height: 280,
          borderRadius: 4,
          overflow: 'hidden',
          border: '1px solid rgba(255, 215, 0, 0.35)',
          boxShadow: '0 8px 30px rgba(0, 0, 0, 0.5)',
          mb: 2.5
        }}
      >
        <div ref={mapContainerRef} style={{ width: '100%', height: '100%' }} />

        {/* دکمه مرکزیت مجدد روی پروجا */}
        <IconButton
          size="small"
          onClick={() => mapInstanceRef.current?.flyTo([43.1107, 12.3890], 13)}
          sx={{
            position: 'absolute',
            top: 12,
            right: 12,
            background: 'rgba(3, 23, 21, 0.85)',
            border: '1px solid #FFD700',
            color: '#FFD700',
            zIndex: 1000,
            '&:hover': { background: '#031715' }
          }}
        >
          <MyLocation fontSize="small" />
        </IconButton>
      </Box>

      {/* کارت جزئیات مرکز انتخاب‌شده */}
      {activePlace && (
        <Card
          sx={{
            mb: 2.5,
            borderRadius: 3.5,
            background: 'linear-gradient(145deg, rgba(7, 39, 35, 0.95) 0%, rgba(3, 23, 21, 0.95) 100%)',
            border: `2px solid ${activePlace.color}`,
            boxShadow: `0 8px 25px rgba(0, 0, 0, 0.5), inset 0 0 10px rgba(255, 215, 0, 0.1)`
          }}
        >
          <CardContent sx={{ p: 2, '&:last-child': { pb: 2 } }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 1 }}>
              <Box>
                <Typography variant="subtitle1" sx={{ color: '#FFFFFF', fontWeight: 900, lineHeight: 1.2 }}>
                  {activePlace.name}
                </Typography>
                <Typography variant="caption" sx={{ color: '#FFD700', fontStyle: 'italic', display: 'block', mt: 0.3 }}>
                  {activePlace.name_it}
                </Typography>
              </Box>
              <Chip
                label={activePlace.category_fa}
                size="small"
                sx={{ background: `${activePlace.color}25`, color: activePlace.color, border: `1px solid ${activePlace.color}50`, fontWeight: 800, fontSize: '0.7rem' }}
              />
            </Box>

            <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.8, my: 0.8 }}>
              <LocationOn sx={{ color: '#02C39A', fontSize: 18 }} />
              <Typography variant="caption" sx={{ color: '#94D2BD' }}>
                {activePlace.address}
              </Typography>
            </Box>

            <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.8, mb: 1.2 }}>
              <Schedule sx={{ color: '#FFB703', fontSize: 18 }} />
              <Typography variant="caption" sx={{ color: '#94D2BD' }}>
                {activePlace.hours}
              </Typography>
            </Box>

            <Typography variant="body2" sx={{ color: '#F0FDF4', fontSize: '0.82rem', lineHeight: 1.6, mb: 1.5, background: 'rgba(3, 23, 21, 0.6)', p: 1.2, borderRadius: 2 }}>
              💡 {activePlace.desc}
            </Typography>

            <Button
              fullWidth
              variant="contained"
              onClick={() => handleOpenGoogleMaps(activePlace)}
              startIcon={<Directions />}
              sx={{
                background: 'linear-gradient(135deg, #00A896 0%, #02C39A 100%)',
                color: '#031715',
                fontWeight: 900,
                borderRadius: 2.5
              }}
            >
              مسیریابی در Google Maps
            </Button>
          </CardContent>
        </Card>
      )}

      {/* لیست سایر مراکز */}
      <Typography variant="subtitle2" sx={{ color: '#FFD700', fontWeight: 800, mb: 1.2 }}>
        فهرست مراکز و اماکن ({filteredPlaces.length} مورد)
      </Typography>

      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
        {filteredPlaces.map((place) => (
          <Box
            key={place.id}
            onClick={() => handleSelectPlace(place)}
            sx={{
              p: 1.5,
              borderRadius: 2.5,
              background: activePlace.id === place.id ? 'rgba(255, 215, 0, 0.12)' : 'rgba(7, 39, 35, 0.5)',
              border: activePlace.id === place.id ? '1px solid #FFD700' : '1px solid rgba(255, 215, 0, 0.15)',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              cursor: 'pointer',
              transition: 'all 0.2s ease',
              '&:hover': {
                borderColor: '#FFD700',
                background: 'rgba(7, 39, 35, 0.8)'
              }
            }}
          >
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <Box sx={{ width: 10, height: 10, borderRadius: '50%', background: place.color }} />
              <Box>
                <Typography variant="subtitle2" sx={{ color: '#fff', fontWeight: 800, fontSize: '0.82rem' }}>
                  {place.name}
                </Typography>
                <Typography variant="caption" sx={{ color: '#94D2BD', fontSize: '0.7rem' }}>
                  {place.address}
                </Typography>
              </Box>
            </Box>
            <LocationOn sx={{ color: activePlace.id === place.id ? '#FFD700' : '#70A9A1', fontSize: 20 }} />
          </Box>
        ))}
      </Box>

    </Box>
  );
}
