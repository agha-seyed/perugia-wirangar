# handlers/places_handler.py - راهنمای پروجا و دوربین زنده (نسخه نهایی کامل)

import json
import os
from datetime import datetime
from aiogram import Router, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

router = Router()

# ==================== تنظیمات ====================

# لینک دوربین زنده
LIVE_CAM_URL = "https://www.youtube.com/watch?v=8TZ8YRt9nYc"

# لینک گوگل مپ تور یک‌روزه (اصلاح شده)
TOUR_MAP_URL = "https://www.google.com/maps/dir/Piazza+IV+Novembre,+Perugia/Rocca+Paolina/Corso+Vannucci/Giardini+Carducci/Arco+Etrusco/@43.1115,12.388,15z"

# مسیر فایل نظرات
DATA_DIR = "data"
REVIEWS_JSON = os.path.join(DATA_DIR, "places_reviews.json")


# ==================== States ====================

class ReviewState(StatesGroup):
    waiting_for_place = State()
    waiting_for_review = State()
    waiting_for_rating = State()


# ==================== توابع کمکی ====================

def ensure_data_dir():
    """اطمینان از وجود پوشه data"""
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)


def load_reviews() -> dict:
    """بارگذاری نظرات از فایل"""
    ensure_data_dir()
    try:
        if os.path.exists(REVIEWS_JSON):
            with open(REVIEWS_JSON, "r", encoding="utf-8") as f:
                content = f.read().strip()
                return json.loads(content) if content else {}
    except (json.JSONDecodeError, IOError):
        pass
    return {}


def save_reviews(reviews: dict) -> bool:
    """ذخیره نظرات در فایل"""
    ensure_data_dir()
    try:
        with open(REVIEWS_JSON, "w", encoding="utf-8") as f:
            json.dump(reviews, f, ensure_ascii=False, indent=2)
        return True
    except IOError:
        return False


def get_star_rating(rating: int) -> str:
    """تبدیل عدد به ستاره"""
    return "⭐" * rating + "☆" * (5 - rating)


def get_average_rating(place_name: str) -> tuple:
    """محاسبه میانگین امتیاز یک مکان"""
    reviews = load_reviews()
    ratings = []
    
    for review in reviews.values():
        if review.get("place", "").lower() == place_name.lower():
            if "rating" in review:
                ratings.append(review["rating"])
    
    if ratings:
        avg = sum(ratings) / len(ratings)
        return round(avg, 1), len(ratings)
    return 0, 0


# ==================== دیتابیس مکان‌ها ====================

CATEGORIES = {
    "historical": {
        "title": "🏛️ مکان‌های تاریخی و معماری",
        "emoji": "🏛️",
        "description": "سفر به گذشته باشکوه پروجا",
        "places": [
            {
                "id": "piazza_novembre",
                "name": "Piazza IV Novembre",
                "name_fa": "میدان چهارم نوامبر",
                "desc": "میدان اصلی شهر با فواره معروف Fontana Maggiore (قرن ۱۳) و کلیسای جامع San Lorenzo – قلب تپنده پروجا!",
                "hours": "۲۴ ساعته (فضای باز)",
                "cost": "رایگان",
                "cost_value": 0,
                "phone": "-",
                "website": "-",
                "student_discount": "رایگان",
                "best_season": "پاییز و بهار",
                "best_time": "صبح زود یا غروب",
                "accessibility": "♿ دسترسی مناسب",
                "tips": [
                    "بهترین قهوه در Caffè Sandri همین میدان",
                    "جمعه‌ها بازار محلی برپاست",
                    "شب‌ها نورپردازی زیبایی دارد"
                ],
                "coordinates": (43.1107, 12.3908),
                "map": "https://maps.app.goo.gl/9bZf3wK8vL2mN4bV6",
                "photo": "https://example.com/piazza.jpg"
            },
            {
                "id": "rocca_paolina",
                "name": "Rocca Paolina",
                "name_fa": "قلعه پائولینا",
                "desc": "قلعه زیرزمینی جادویی ساخته‌شده توسط پاپ پل سوم (۱۵۴۰) – تونل‌های مخفی، خیابان‌های مدفون و تجربه‌ای فراموش‌نشدنی!",
                "hours": "۰۶:۱۵ تا ۱۹:۰۰ (پله برقی) | موزه: ۰۹:۰۰-۱۹:۰۰",
                "cost": "رایگان",
                "cost_value": 0,
                "phone": "+39 075 577 2954",
                "website": "www.perugiaonline.it",
                "student_discount": "رایگان",
                "best_season": "همه فصل‌ها (فضای سرپوشیده)",
                "best_time": "هر ساعتی",
                "accessibility": "♿ پله برقی و آسانسور",
                "tips": [
                    "از پله برقی عمومی وارد شوید",
                    "نمایشگاه‌های موقت هنری دارد",
                    "مسیر میانبر از پایین به بالای شهر"
                ],
                "coordinates": (43.1089, 12.3886),
                "map": "https://maps.app.goo.gl/3jR5kL8pQ2vX7m9y7",
                "photo": None
            },
            {
                "id": "arco_etrusco",
                "name": "Arco Etrusco (Porta Augusta)",
                "name_fa": "دروازه اتروسکی",
                "desc": "دروازه ۲۳۰۰ ساله از تمدن اتروسک (قرن ۳ قبل میلاد) – یکی از بهترین نمونه‌های معماری اتروسکی در جهان!",
                "hours": "۲۴ ساعته (فضای باز)",
                "cost": "رایگان",
                "cost_value": 0,
                "phone": "-",
                "website": "-",
                "student_discount": "رایگان",
                "best_season": "پاییز",
                "best_time": "غروب – نور طلایی روی سنگ‌ها",
                "accessibility": "⚠️ مسیر شیب‌دار",
                "tips": [
                    "کتیبه لاتین روی طاق را ببینید",
                    "عکس از پایین طاق بگیرید",
                    "ادامه مسیر به Via Ulisse Rocchi"
                ],
                "coordinates": (43.1142, 12.3892),
                "map": "https://maps.app.goo.gl/8kPqR5tY6vM3nL9x8",
                "photo": None
            },
            {
                "id": "corso_vannucci",
                "name": "Corso Vannucci",
                "name_fa": "خیابان وانوچی",
                "desc": "خیابان اصلی و افسانه‌ای پیاده‌روی – بهترین جای مردم‌نگاری، خرید، ژلاتو و کافه‌نشینی!",
                "hours": "۲۴ ساعته | مغازه‌ها: ۱۰:۰۰-۲۰:۰۰",
                "cost": "رایگان (خرید اختیاری!)",
                "cost_value": 0,
                "phone": "-",
                "website": "-",
                "student_discount": "تخفیف در بسیاری از کافه‌ها با کارت دانشجویی",
                "best_season": "همه فصل‌ها",
                "best_time": "شب‌ها (passeggiata ایتالیایی)",
                "accessibility": "♿ کاملاً مناسب",
                "tips": [
                    "حتماً stracciatella gelato امتحان کنید",
                    "غروب‌ها شلوغ و پرانرژی است",
                    "هر شب locals اینجا قدم می‌زنند"
                ],
                "coordinates": (43.1104, 12.3895),
                "map": "https://maps.app.goo.gl/4fG7hJ9kL2mN5pQv6",
                "photo": None
            },
            {
                "id": "cattedrale_san_lorenzo",
                "name": "Cattedrale di San Lorenzo",
                "name_fa": "کلیسای جامع سن لورنزو",
                "desc": "کلیسای جامع گوتیک قرن ۱۴ با حلقه ازدواج مریم مقدس – یادگار مقدس!",
                "hours": "۰۷:۳۰-۱۲:۳۰ و ۱۵:۳۰-۱۹:۰۰",
                "cost": "کلیسا رایگان | موزه: ۵ یورو",
                "cost_value": 0,
                "phone": "+39 075 572 3832",
                "website": "www.diocesi.perugia.it",
                "student_discount": "موزه: ۳ یورو",
                "best_season": "همه فصل‌ها",
                "best_time": "صبح (خلوت‌تر)",
                "accessibility": "⚠️ پله در ورودی",
                "tips": [
                    "Holy Ring را در موزه ببینید",
                    "نمای بیرونی ناتمام ولی جذاب است",
                    "کنسرت‌های کلاسیک گاهی برگزار می‌شود"
                ],
                "coordinates": (43.1108, 12.3912),
                "map": "https://maps.app.goo.gl/KqR5tY6vM3nL9x8j7",
                "photo": None
            }
        ]
    },
    
    "nature": {
        "title": "🌿 پارک‌ها و طبیعت",
        "emoji": "🌿",
        "description": "استراحت در آغوش طبیعت اومبریا",
        "places": [
            {
                "id": "giardini_carducci",
                "name": "Giardini Carducci",
                "name_fa": "باغ‌های کاردوچی",
                "desc": "پارک پانوراما با منظره ۱۸۰ درجه به دره‌های اومبریا – بهترین جای غروب، پیک‌نیک و آرامش!",
                "hours": "طلوع تا غروب",
                "cost": "رایگان",
                "cost_value": 0,
                "phone": "-",
                "website": "-",
                "student_discount": "رایگان",
                "best_season": "بهار و پاییز",
                "best_time": "غروب – منظره طلایی دره",
                "accessibility": "♿ مناسب",
                "tips": [
                    "نیمکت‌های رو به غرب بگیرید",
                    "قهوه از کافه نزدیک بخرید",
                    "شب‌های تابستان کنسرت دارد"
                ],
                "coordinates": (43.1081, 12.3871),
                "map": "https://maps.app.goo.gl/7kL9mN2pQ5tR8vXy9",
                "photo": None
            },
            {
                "id": "parco_santa_margherita",
                "name": "Parco Santa Margherita",
                "name_fa": "پارک سانتا مارگریتا",
                "desc": "پارک بزرگ و سرسبز در پایین شهر – جای عالی برای دویدن، پیک‌نیک خانوادگی و فرار از شلوغی",
                "hours": "۰۷:۰۰ تا غروب",
                "cost": "رایگان",
                "cost_value": 0,
                "phone": "-",
                "website": "-",
                "student_discount": "رایگان",
                "best_season": "بهار – شکوفه‌های زیبا",
                "best_time": "صبح زود یا عصر",
                "accessibility": "♿ مسیرهای مناسب",
                "tips": [
                    "زمین بازی برای بچه‌ها دارد",
                    "مسیر دویدن علامت‌گذاری شده",
                    "نزدیک به ایستگاه مینی‌مترو"
                ],
                "coordinates": (43.1051, 12.3912),
                "map": "https://maps.app.goo.gl/5tR8vXy9kL9mN2pQ7",
                "photo": None
            },
            {
                "id": "monte_tezio",
                "name": "Monte Tezio",
                "name_fa": "کوه تتسیو",
                "desc": "کوهپیمایی آسان در ۲۰ دقیقه‌ای شهر – منظره ۳۶۰ درجه، طبیعت بکر و فرار کامل از شهر!",
                "hours": "۲۴ ساعته (روشنایی روز توصیه)",
                "cost": "رایگان",
                "cost_value": 0,
                "phone": "-",
                "website": "-",
                "student_discount": "رایگان",
                "best_season": "بهار و پاییز",
                "best_time": "صبح زود",
                "accessibility": "❌ مسیر کوهستانی",
                "tips": [
                    "کفش کوه ضروری",
                    "آب کافی ببرید",
                    "مسیر از Migiana di Monte Tezio",
                    "۲ ساعت رفت و برگشت"
                ],
                "coordinates": (43.1567, 12.3678),
                "map": "https://maps.app.goo.gl/8vXy9kL9mN2pQ5tR7",
                "photo": None
            }
        ]
    },
    
    "culture": {
        "title": "🎨 موزه‌ها و فرهنگ",
        "emoji": "🎨",
        "description": "غوطه‌ور شدن در هنر و تاریخ",
        "places": [
            {
                "id": "galleria_nazionale",
                "name": "Galleria Nazionale dell'Umbria",
                "name_fa": "گالری ملی اومبریا",
                "desc": "بزرگترین موزه هنر منطقه – شاهکارهای پروجینو، پینتوریکیو و فرا آنجلیکو از قرون ۱۳ تا ۱۹",
                "hours": "سه‌شنبه-یکشنبه ۰۸:۳۰-۱۹:۳۰ | دوشنبه تعطیل",
                "cost": "۸ یورو",
                "cost_value": 8,
                "phone": "+39 075 5866 8410",
                "website": "www.gallerianazionaledellumbria.it",
                "student_discount": "۴ یورو (اتحادیه اروپا ۱۸-۲۵) | زیر ۱۸ رایگان",
                "best_season": "زمستان (خلوت‌تر)",
                "best_time": "صبح",
                "accessibility": "♿ آسانسور و امکانات کامل",
                "tips": [
                    "اول یکشنبه ماه رایگان!",
                    "حداقل ۲ ساعت وقت بگذارید",
                    "کافه‌تریا با منظره خوب"
                ],
                "coordinates": (43.1104, 12.3898),
                "map": "https://maps.app.goo.gl/5jK8mL3pQ7tR9vXy6",
                "photo": None
            },
            {
                "id": "perugina_chocolate",
                "name": "Casa del Cioccolato Perugina",
                "name_fa": "خانه شکلات پروجینا",
                "desc": "موزه و کارخانه شکلات Baci – تور تولید، چشیدن شکلات و فروشگاه بزرگ!",
                "hours": "دوشنبه-جمعه ۰۹:۰۰-۱۷:۳۰ | شنبه ۰۹:۰۰-۱۳:۰۰",
                "cost": "تور: ۹ یورو | فروشگاه رایگان",
                "cost_value": 9,
                "phone": "+39 075 527 6770",
                "website": "www.perugina.com",
                "student_discount": "۷ یورو + تخفیف ۱۰٪ فروشگاه",
                "best_season": "اکتبر – فستیوال Eurochocolate!",
                "best_time": "صبح (تور ساعت ۱۰)",
                "accessibility": "♿ کاملاً مناسب",
                "tips": [
                    "رزرو آنلاین توصیه می‌شود",
                    "حمل‌ونقل عمومی: اتوبوس E",
                    "هدیه شکلاتی در پایان تور!"
                ],
                "coordinates": (43.0912, 12.4456),
                "map": "https://maps.app.goo.gl/9kM7nL4pQ8tR2vXy5",
                "photo": None
            },
            {
                "id": "pozzo_etrusco",
                "name": "Pozzo Etrusco",
                "name_fa": "چاه اتروسکی",
                "desc": "چاه آب باستانی ۳۷ متری از قرن ۳ قبل میلاد – شاهکار مهندسی زیرزمینی!",
                "hours": "۱۰:۰۰-۱۳:۳۰ و ۱۴:۳۰-۱۸:۰۰ (تابستان تا ۱۹:۰۰)",
                "cost": "۴ یورو",
                "cost_value": 4,
                "phone": "+39 075 573 3669",
                "website": "-",
                "student_discount": "۲ یورو",
                "best_season": "همه فصل‌ها (زیرزمینی)",
                "best_time": "هر ساعتی",
                "accessibility": "❌ پله‌های زیاد",
                "tips": [
                    "پله به عمق ۳۷ متر!",
                    "هنوز آب دارد",
                    "ترکیب با بلیط Cappella San Severo"
                ],
                "coordinates": (43.1118, 12.3895),
                "map": "https://maps.app.goo.gl/7nL4pQ8tR2vXy5kM9",
                "photo": None
            },
            {
                "id": "museo_archeologico",
                "name": "Museo Archeologico Nazionale",
                "name_fa": "موزه باستان‌شناسی ملی",
                "desc": "گنجینه آثار اتروسکی و رومی – سنگ Cippus Perusinus با خط اتروسکی!",
                "hours": "سه‌شنبه-یکشنبه ۰۸:۳۰-۱۹:۳۰ | دوشنبه تعطیل",
                "cost": "۵ یورو",
                "cost_value": 5,
                "phone": "+39 075 572 7141",
                "website": "www.archeopg.arti.beniculturali.it",
                "student_discount": "۲.۵ یورو",
                "best_season": "همه فصل‌ها",
                "best_time": "صبح",
                "accessibility": "♿ آسانسور",
                "tips": [
                    "در کلیسای San Domenico قرار دارد",
                    "مجموعه اتروسکی فوق‌العاده",
                    "یک ساعت کافی است"
                ],
                "coordinates": (43.1078, 12.3934),
                "map": "https://maps.app.goo.gl/4pQ8tR2vXy5kM9nL7",
                "photo": None
            }
        ]
    },
    
    "food_fun": {
        "title": "🍴 غذا و تفریح",
        "emoji": "🍴",
        "description": "طعم واقعی اومبریا",
        "places": [
            {
                "id": "via_volte",
                "name": "Via delle Volte della Pace",
                "name_fa": "کوچه طاق‌ها",
                "desc": "کوچه‌های قرون وسطایی با رستوران‌های رمانتیک – بهترین غذای محلی در فضایی جادویی!",
                "hours": "رستوران‌ها: ۱۲:۰۰-۱۵:۰۰ و ۱۹:۰۰-۲۳:۰۰",
                "cost": "۱۵-۳۰ یورو برای غذای کامل",
                "cost_value": 20,
                "phone": "-",
                "website": "-",
                "student_discount": "بعضی رستوران‌ها ۱۰٪ تخفیف",
                "best_season": "همه فصل‌ها",
                "best_time": "شام (۲۰:۰۰ به بعد)",
                "accessibility": "⚠️ سنگفرش ناهموار",
                "tips": [
                    "Umbricelli pasta امتحان کنید",
                    "رزرو برای آخر هفته",
                    "Osteria del Tureno معروف است"
                ],
                "coordinates": (43.1098, 12.3878),
                "map": "https://maps.app.goo.gl/8kP9qR7tY3vL6nMx5",
                "photo": None
            },
            {
                "id": "mercato_coperto",
                "name": "Mercato Coperto",
                "name_fa": "بازار سرپوشیده",
                "desc": "بازار محلی تازه‌ها – سبزیجات، پنیر، گوشت و محصولات اومبریایی اصیل!",
                "hours": "دوشنبه-شنبه ۰۷:۰۰-۱۳:۳۰ | پنج‌شنبه عصر هم باز",
                "cost": "خرید به دلخواه",
                "cost_value": 0,
                "phone": "-",
                "website": "-",
                "student_discount": "-",
                "best_season": "همه فصل‌ها",
                "best_time": "صبح زود (تازه‌ترین‌ها)",
                "accessibility": "♿ مناسب",
                "tips": [
                    "Pecorino cheese و Norcia ham",
                    "جمعه‌ها شلوغ‌تر",
                    "صبحانه در کافه داخلی"
                ],
                "coordinates": (43.1095, 12.3912),
                "map": "https://maps.app.goo.gl/2vXy5kM9nL7pQ8tR4",
                "photo": None
            },
            {
                "id": "borgo_bello",
                "name": "Borgo Bello",
                "name_fa": "محله بورگو بلو",
                "desc": "محله هنری و بوهمی پروجا – کافه‌های خاص، گالری‌های کوچک و فضای جوان!",
                "hours": "کافه‌ها: ۰۸:۰۰-۲۴:۰۰",
                "cost": "کافه: ۳-۸ یورو",
                "cost_value": 5,
                "phone": "-",
                "website": "-",
                "student_discount": "بعضی کافه‌ها تخفیف دانشجویی",
                "best_season": "بهار و تابستان",
                "best_time": "عصر و شب",
                "accessibility": "⚠️ شیب‌دار",
                "tips": [
                    "Via della Viola را پیدا کنید",
                    "شب‌های جمعه موسیقی زنده",
                    "گالری‌های هنر محلی"
                ],
                "coordinates": (43.1134, 12.3867),
                "map": "https://maps.app.goo.gl/5kM9nL7pQ8tR4vXy2",
                "photo": None
            },
            {
                "id": "gelateria_gambrinus",
                "name": "Gelateria Gambrinus",
                "name_fa": "ژلاتوی گامبرینوس",
                "desc": "بهترین ژلاتو در پروجا از ۱۹۱۴ – طعم‌های سنتی و خلاقانه!",
                "hours": "۱۱:۰۰-۲۳:۰۰ (تابستان تا ۲۴:۰۰)",
                "cost": "۲.۵-۵ یورو",
                "cost_value": 3,
                "phone": "+39 075 572 1578",
                "website": "-",
                "student_discount": "-",
                "best_season": "تابستان",
                "best_time": "عصر",
                "accessibility": "♿ مناسب",
                "tips": [
                    "Stracciatella کلاسیک!",
                    "Bacio flavor (شکلات محلی)",
                    "صف طولانی = ارزش انتظار!"
                ],
                "coordinates": (43.1106, 12.3889),
                "map": "https://maps.app.goo.gl/9nL7pQ8tR4vXy2kM5",
                "photo": None
            }
        ]
    },
    
    "university": {
        "title": "🎓 نقاط دانشگاهی",
        "emoji": "🎓",
        "description": "محل‌های مهم برای دانشجویان",
        "places": [
            {
                "id": "palazzo_gallenga",
                "name": "Palazzo Gallenga Stuart",
                "name_fa": "کاخ گالنگا",
                "desc": "ساختمان اصلی دانشگاه برای خارجیان – ثبت‌نام، کلاس‌ها و کتابخانه",
                "hours": "دوشنبه-جمعه ۰۸:۰۰-۱۹:۰۰",
                "cost": "-",
                "cost_value": 0,
                "phone": "+39 075 57461",
                "website": "www.unistrapg.it",
                "student_discount": "دانشجویان ثبت‌نام‌شده",
                "best_season": "-",
                "best_time": "ساعات اداری",
                "accessibility": "♿ آسانسور",
                "tips": [
                    "کارت دانشجویی را همیشه همراه داشته باشید",
                    "کتابخانه عالی برای مطالعه",
                    "WiFi رایگان"
                ],
                "coordinates": (43.1098, 12.3923),
                "map": "https://maps.app.goo.gl/7pQ8tR4vXy2kM5nL9",
                "photo": None
            },
            {
                "id": "mensa_universitaria",
                "name": "Mensa Universitaria",
                "name_fa": "غذاخوری دانشگاه",
                "desc": "غذای ارزان و مقوی برای دانشجویان – بهترین گزینه بودجه!",
                "hours": "ناهار ۱۲:۰۰-۱۴:۳۰ | شام ۱۹:۰۰-۲۱:۰۰",
                "cost": "۳-۵ یورو غذای کامل!",
                "cost_value": 4,
                "phone": "+39 075 5057211",
                "website": "www.adisupg.gov.it",
                "student_discount": "با کارت ADISU",
                "best_season": "-",
                "best_time": "۱۲:۳۰ یا ۱۹:۳۰ (کمتر صف)",
                "accessibility": "♿ مناسب",
                "tips": [
                    "کارت ADISU را فعال کنید",
                    "منوی روزانه متنوع",
                    "چند شعبه در شهر"
                ],
                "coordinates": (43.1112, 12.3945),
                "map": "https://maps.app.goo.gl/4vXy2kM5nL9pQ8tR7",
                "photo": None
            }
        ]
    }
}


# ==================== منوی اصلی ====================

@router.callback_query(F.data == "places")
async def show_places_main(callback: types.CallbackQuery, state: FSMContext):
    """نمایش منوی اصلی راهنمای پروجا"""
    
    # پاک کردن state قبلی
    await state.clear()
    
    # محاسبه تعداد کل مکان‌ها
    total_places = sum(len(cat["places"]) for cat in CATEGORIES.values())
    
    text = (
        "📸 <b>راهنمای کامل پروجا</b>\n\n"
        f"🗺️ {total_places} مکان دیدنی در ۵ دسته‌بندی\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        "🔴 <b>دوربین زنده ۲۴ ساعته میدان اصلی:</b>\n"
        f"<a href='{LIVE_CAM_URL}'>▶️ کلیک کنید و پروجا را زنده ببینید!</a>\n\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        "📂 <b>دسته‌بندی‌ها:</b>"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="🔴 دوربین زنده پروجا", 
            url=LIVE_CAM_URL
        )],
        [InlineKeyboardButton(
            text=f"{CATEGORIES['historical']['emoji']} تاریخی ({len(CATEGORIES['historical']['places'])})", 
            callback_data="cat_historical"
        )],
        [InlineKeyboardButton(
            text=f"{CATEGORIES['nature']['emoji']} طبیعت ({len(CATEGORIES['nature']['places'])})", 
            callback_data="cat_nature"
        )],
        [InlineKeyboardButton(
            text=f"{CATEGORIES['culture']['emoji']} موزه‌ها ({len(CATEGORIES['culture']['places'])})", 
            callback_data="cat_culture"
        )],
        [InlineKeyboardButton(
            text=f"{CATEGORIES['food_fun']['emoji']} غذا و تفریح ({len(CATEGORIES['food_fun']['places'])})", 
            callback_data="cat_food_fun"
        )],
        [InlineKeyboardButton(
            text=f"{CATEGORIES['university']['emoji']} نقاط دانشگاهی ({len(CATEGORIES['university']['places'])})", 
            callback_data="cat_university"
        )],
        [
            InlineKeyboardButton(text="🗺️ تور یک روزه", callback_data="tour_day"),
            InlineKeyboardButton(text="💰 فیلتر قیمت", callback_data="filter_price")
        ],
        [
            InlineKeyboardButton(text="⭐ نظرات", callback_data="show_reviews"),
            InlineKeyboardButton(text="✍️ ثبت نظر", callback_data="add_review")
        ],
        [InlineKeyboardButton(
            text="🏠 بازگشت به منوی اصلی", 
            callback_data="main_menu"
        )]
    ])
    
    await callback.message.edit_text(
        text, 
        reply_markup=keyboard, 
        parse_mode="HTML", 
        disable_web_page_preview=False
    )
    await callback.answer()


# ==================== نمایش دسته‌بندی ====================

@router.callback_query(F.data.startswith("cat_"))
async def show_category(callback: types.CallbackQuery):
    """نمایش مکان‌های یک دسته‌بندی"""
    
    cat_key = callback.data.replace("cat_", "")
    category = CATEGORIES.get(cat_key)
    
    if not category:
        await callback.answer("❌ دسته‌بندی یافت نشد!", show_alert=True)
        return
    
    text = (
        f"{category['emoji']} <b>{category['title']}</b>\n"
        f"📝 {category['description']}\n\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
    )
    
    # لیست مکان‌ها با دکمه برای جزئیات
    buttons = []
    
    for i, place in enumerate(category["places"], 1):
        avg_rating, count = get_average_rating(place["name"])
        rating_text = f" ⭐{avg_rating}" if count > 0 else ""
        
        text += f"{i}. <b>{place['name']}</b>{rating_text}\n"
        text += f"   └ {place['name_fa']}\n\n"
        
        buttons.append([
            InlineKeyboardButton(
                text=f"📍 {place['name']}", 
                callback_data=f"place_{place['id']}"
            )
        ])
    
    # دکمه‌های پایین
    buttons.append([
        InlineKeyboardButton(text="🗺️ همه در نقشه", callback_data=f"map_all_{cat_key}")
    ])
    buttons.append([
        InlineKeyboardButton(text="🔙 بازگشت", callback_data="places")
    ])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    await callback.message.edit_text(
        text, 
        reply_markup=keyboard, 
        parse_mode="HTML"
    )
    await callback.answer()


# ==================== نمایش جزئیات مکان ====================

@router.callback_query(F.data.startswith("place_"))
async def show_place_details(callback: types.CallbackQuery):
    """نمایش جزئیات کامل یک مکان"""
    
    place_id = callback.data.replace("place_", "")
    
    # پیدا کردن مکان
    place = None
    cat_key = None
    
    for key, category in CATEGORIES.items():
        for p in category["places"]:
            if p["id"] == place_id:
                place = p
                cat_key = key
                break
        if place:
            break
    
    if not place:
        await callback.answer("❌ مکان یافت نشد!", show_alert=True)
        return
    
    # محاسبه امتیاز
    avg_rating, review_count = get_average_rating(place["name"])
    rating_display = get_star_rating(round(avg_rating)) if review_count > 0 else "هنوز امتیازی ثبت نشده"
    
    text = (
        f"📍 <b>{place['name']}</b>\n"
        f"🏷️ {place['name_fa']}\n\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📝 <b>توضیحات:</b>\n{place['desc']}\n\n"
        f"🕐 <b>ساعت کاری:</b> {place['hours']}\n"
        f"💰 <b>هزینه:</b> {place['cost']}\n"
        f"🎓 <b>تخفیف دانشجویی:</b> {place['student_discount']}\n\n"
        f"🍂 <b>بهترین فصل:</b> {place['best_season']}\n"
        f"⏰ <b>بهترین زمان:</b> {place['best_time']}\n"
        f"♿ <b>دسترسی:</b> {place['accessibility']}\n\n"
    )
    
    # اطلاعات تماس
    if place['phone'] != "-":
        text += f"📞 <b>تماس:</b> {place['phone']}\n"
    if place['website'] != "-":
        text += f"🌐 <b>وبسایت:</b> {place['website']}\n"
    
    text += "\n"
    
    # نکات
    if place.get("tips"):
        text += "💡 <b>نکات مهم:</b>\n"
        for tip in place["tips"]:
            text += f"   • {tip}\n"
        text += "\n"
    
    # امتیاز
    text += "━━━━━━━━━━━━━━━━━━━━━\n"
    text += f"⭐ <b>امتیاز:</b> {rating_display}"
    if review_count > 0:
        text += f" ({review_count} نظر)"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="🗺️ نمایش در گوگل مپ", 
            url=place['map']
        )],
        [InlineKeyboardButton(
            text="📍 ارسال موقعیت", 
            callback_data=f"sendloc_{place['id']}"
        )],
        [
            InlineKeyboardButton(
                text="⭐ ثبت امتیاز", 
                callback_data=f"rate_{place['id']}"
            ),
            InlineKeyboardButton(
                text="💬 نظرات", 
                callback_data=f"reviews_{place['id']}"
            )
        ],
        [InlineKeyboardButton(
            text="🔙 بازگشت", 
            callback_data=f"cat_{cat_key}"
        )]
    ])
    
    await callback.message.edit_text(
        text, 
        reply_markup=keyboard, 
        parse_mode="HTML", 
        disable_web_page_preview=True
    )
    await callback.answer()


# ==================== ارسال موقعیت ====================

@router.callback_query(F.data.startswith("sendloc_"))
async def send_location(callback: types.CallbackQuery):
    """ارسال موقعیت مکان به صورت Location تلگرام"""
    
    place_id = callback.data.replace("sendloc_", "")
    
    # پیدا کردن مکان
    place = None
    for category in CATEGORIES.values():
        for p in category["places"]:
            if p["id"] == place_id:
                place = p
                break
        if place:
            break
    
    if not place or "coordinates" not in place:
        await callback.answer("❌ موقعیت یافت نشد!", show_alert=True)
        return
    
    lat, lon = place["coordinates"]
    
    await callback.message.answer_location(
        latitude=lat,
        longitude=lon
    )
    await callback.message.answer(
        f"📍 <b>{place['name']}</b>\n{place['name_fa']}",
        parse_mode="HTML"
    )
    await callback.answer("📍 موقعیت ارسال شد!")


# ==================== تور یک روزه ====================

@router.callback_query(F.data == "tour_day")
async def show_tour_day(callback: types.CallbackQuery):
    """نمایش برنامه تور یک‌روزه"""
    
    text = (
        "🗺️ <b>تور پیاده‌روی یک روزه در پروجا</b>\n\n"
        "مسیر طلایی برای کشف بهترین‌های شهر! ✨\n\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        
        "🌅 <b>صبح (۰۹:۰۰-۱۲:۰۰)</b>\n"
        "━━━━━━━━━━\n"
        "1️⃣ <b>Piazza IV Novembre</b>\n"
        "   └ شروع با قهوه در Caffè Sandri\n"
        "   └ عکس با Fontana Maggiore\n\n"
        
        "2️⃣ <b>Cattedrale San Lorenzo</b>\n"
        "   └ بازدید از کلیسا و موزه\n\n"
        
        "3️⃣ <b>Corso Vannucci</b>\n"
        "   └ پیاده‌روی و تماشای مغازه‌ها\n\n"
        
        "🍝 <b>ناهار (۱۲:۳۰-۱۴:۰۰)</b>\n"
        "━━━━━━━━━━\n"
        "4️⃣ <b>Via delle Volte</b>\n"
        "   └ غذای اومبریایی اصیل\n"
        "   └ Umbricelli با ترافل محلی\n\n"
        
        "🏛️ <b>بعدازظهر (۱۴:۳۰-۱۷:۰۰)</b>\n"
        "━━━━━━━━━━\n"
        "5️⃣ <b>Rocca Paolina</b>\n"
        "   └ ماجراجویی در تونل‌های زیرزمینی\n\n"
        
        "6️⃣ <b>Galleria Nazionale</b>\n"
        "   └ شاهکارهای هنری رنسانس\n\n"
        
        "🌳 <b>عصر (۱۷:۰۰-۱۹:۰۰)</b>\n"
        "━━━━━━━━━━\n"
        "7️⃣ <b>Giardini Carducci</b>\n"
        "   └ استراحت و تماشای غروب\n\n"
        
        "8️⃣ <b>Arco Etrusco</b>\n"
        "   └ عکس در نور طلایی غروب\n\n"
        
        "🌙 <b>شب (۲۰:۰۰+)</b>\n"
        "━━━━━━━━━━\n"
        "9️⃣ <b>Corso Vannucci</b>\n"
        "   └ ژلاتو و Passeggiata شبانه!\n\n"
        
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        "⏱️ <b>مدت:</b> ۸-۱۰ ساعت\n"
        "🚶 <b>مسافت:</b> ~۵ کیلومتر\n"
        "💰 <b>هزینه تقریبی:</b> ۲۵-۴۰ یورو\n"
        "👟 <b>کفش راحت فراموش نشود!</b>"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="🗺️ نمایش کل مسیر در گوگل مپ", 
            url=TOUR_MAP_URL
        )],
        [InlineKeyboardButton(
            text="📥 دانلود PDF مسیر", 
            callback_data="download_tour_pdf"
        )],
        [InlineKeyboardButton(
            text="🔙 بازگشت", 
            callback_data="places"
        )]
    ])
    
    await callback.message.edit_text(
        text, 
        reply_markup=keyboard, 
        parse_mode="HTML"
    )
    await callback.answer()


# ==================== فیلتر قیمت ====================

@router.callback_query(F.data == "filter_price")
async def filter_by_price(callback: types.CallbackQuery):
    """نمایش منوی فیلتر قیمت"""
    
    text = (
        "💰 <b>فیلتر مکان‌ها بر اساس هزینه</b>\n\n"
        "کدام دسته را می‌خواهید ببینید؟"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="🆓 رایگان", 
            callback_data="price_free"
        )],
        [InlineKeyboardButton(
            text="💵 کم‌هزینه (تا ۵ یورو)", 
            callback_data="price_low"
        )],
        [InlineKeyboardButton(
            text="💶 متوسط (۵-۱۰ یورو)", 
            callback_data="price_medium"
        )],
        [InlineKeyboardButton(
            text="🔙 بازگشت", 
            callback_data="places"
        )]
    ])
    
    await callback.message.edit_text(
        text, 
        reply_markup=keyboard, 
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("price_"))
async def show_filtered_places(callback: types.CallbackQuery):
    """نمایش مکان‌های فیلتر شده بر اساس قیمت"""
    
    filter_type = callback.data.replace("price_", "")
    
    # تعیین محدوده قیمت
    if filter_type == "free":
        min_price, max_price = 0, 0
        title = "🆓 مکان‌های رایگان"
    elif filter_type == "low":
        min_price, max_price = 0.01, 5
        title = "💵 مکان‌های کم‌هزینه (تا ۵ یورو)"
    else:  # medium
        min_price, max_price = 5, 10
        title = "💶 مکان‌های متوسط (۵-۱۰ یورو)"
    
    # جمع‌آوری مکان‌های مناسب
    filtered = []
    for cat_key, category in CATEGORIES.items():
        for place in category["places"]:
            cost = place.get("cost_value", 0)
            if filter_type == "free" and cost == 0:
                filtered.append((place, category["emoji"]))
            elif filter_type == "low" and 0 < cost <= 5:
                filtered.append((place, category["emoji"]))
            elif filter_type == "medium" and 5 < cost <= 10:
                filtered.append((place, category["emoji"]))
    
    text = f"<b>{title}</b>\n\n"
    
    if filtered:
        text += f"📍 {len(filtered)} مکان یافت شد:\n\n"
        buttons = []
        
        for place, emoji in filtered:
            text += f"{emoji} <b>{place['name']}</b>\n"
            text += f"   └ {place['cost']}\n\n"
            
            buttons.append([
                InlineKeyboardButton(
                    text=f"📍 {place['name']}", 
                    callback_data=f"place_{place['id']}"
                )
            ])
        
        buttons.append([
            InlineKeyboardButton(text="🔙 بازگشت", callback_data="filter_price")
        ])
    else:
        text += "❌ مکانی در این محدوده قیمت یافت نشد."
        buttons = [[
            InlineKeyboardButton(text="🔙 بازگشت", callback_data="filter_price")
        ]]
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    await callback.message.edit_text(
        text, 
        reply_markup=keyboard, 
        parse_mode="HTML"
    )
    await callback.answer()


# ==================== سیستم نظرات ====================

@router.callback_query(F.data == "add_review")
async def start_add_review(callback: types.CallbackQuery, state: FSMContext):
    """شروع فرآیند ثبت نظر"""
    
    # ساختن لیست مکان‌ها
    text = (
        "✍️ <b>ثبت نظر و تجربه شما</b>\n\n"
        "لطفاً مکان مورد نظر را انتخاب کنید:\n\n"
    )
    
    buttons = []
    for cat_key, category in CATEGORIES.items():
        for place in category["places"]:
            buttons.append([
                InlineKeyboardButton(
                    text=f"{category['emoji']} {place['name']}", 
                    callback_data=f"review_place_{place['id']}"
                )
            ])
    
    buttons.append([
        InlineKeyboardButton(text="❌ انصراف", callback_data="places")
    ])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    await callback.message.edit_text(
        text, 
        reply_markup=keyboard, 
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("review_place_"))
async def select_place_for_review(callback: types.CallbackQuery, state: FSMContext):
    """انتخاب مکان برای ثبت نظر"""
    
    place_id = callback.data.replace("review_place_", "")
    
    # پیدا کردن نام مکان
    place_name = None
    for category in CATEGORIES.values():
        for p in category["places"]:
            if p["id"] == place_id:
                place_name = p["name"]
                break
        if place_name:
            break
    
    if not place_name:
        await callback.answer("❌ مکان یافت نشد!", show_alert=True)
        return
    
    # ذخیره در state
    await state.set_state(ReviewState.waiting_for_rating)
    await state.update_data(place_id=place_id, place_name=place_name)
    
    text = (
        f"⭐ <b>امتیاز شما به {place_name}:</b>\n\n"
        "لطفاً امتیاز ۱ تا ۵ را انتخاب کنید:"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="1️⃣", callback_data="rating_1"),
            InlineKeyboardButton(text="2️⃣", callback_data="rating_2"),
            InlineKeyboardButton(text="3️⃣", callback_data="rating_3"),
            InlineKeyboardButton(text="4️⃣", callback_data="rating_4"),
            InlineKeyboardButton(text="5️⃣", callback_data="rating_5"),
        ],
        [InlineKeyboardButton(text="❌ انصراف", callback_data="places")]
    ])
    
    await callback.message.edit_text(
        text, 
        reply_markup=keyboard, 
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("rating_"), ReviewState.waiting_for_rating)
async def receive_rating(callback: types.CallbackQuery, state: FSMContext):
    """دریافت امتیاز و درخواست متن نظر"""
    
    rating = int(callback.data.replace("rating_", ""))
    await state.update_data(rating=rating)
    await state.set_state(ReviewState.waiting_for_review)
    
    data = await state.get_data()
    place_name = data.get("place_name", "")
    
    text = (
        f"✅ امتیاز {get_star_rating(rating)} ثبت شد!\n\n"
        f"📝 <b>حالا نظر خود درباره {place_name} را بنویسید:</b>\n\n"
        "💡 می‌توانید تجربه، نکات یا پیشنهادات خود را بنویسید.\n"
        "(یا /skip برای رد کردن)"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏭️ رد کردن (بدون نظر)", callback_data="skip_review_text")]
    ])
    
    await callback.message.edit_text(
        text, 
        reply_markup=keyboard, 
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "skip_review_text", ReviewState.waiting_for_review)
async def skip_review_text(callback: types.CallbackQuery, state: FSMContext):
    """رد کردن متن نظر و ذخیره فقط امتیاز"""
    
    data = await state.get_data()
    await save_user_review(callback.from_user, data, None)
    await state.clear()
    
    await callback.message.edit_text(
        "✅ <b>امتیاز شما با موفقیت ثبت شد!</b>\n\n"
        "🙏 ممنون از مشارکت شما!",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 بازگشت به راهنما", callback_data="places")]
        ]),
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(ReviewState.waiting_for_review)
async def receive_review_text(message: types.Message, state: FSMContext):
    """دریافت متن نظر"""
    
    if message.text == "/skip":
        data = await state.get_data()
        await save_user_review(message.from_user, data, None)
        await state.clear()
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 بازگشت به راهنما", callback_data="places")]
        ])
        
        await message.answer(
            "✅ <b>امتیاز شما ثبت شد!</b>",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        return
    
    # ذخیره نظر کامل
    data = await state.get_data()
    await save_user_review(message.from_user, data, message.text)
    await state.clear()
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 بازگشت به راهنما", callback_data="places")]
    ])
    
    await message.answer(
        "✅ <b>نظر شما با موفقیت ثبت شد!</b>\n\n"
        "🙏 ممنون از اشتراک تجربه‌تان!\n"
        "نظر شما به دیگران کمک می‌کند.",
        reply_markup=keyboard,
        parse_mode="HTML"
    )


async def save_user_review(user, data: dict, review_text: str | None):
    """ذخیره نظر کاربر"""
    
    reviews = load_reviews()
    
    review_id = f"{user.id}_{data['place_id']}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    reviews[review_id] = {
        "user_id": user.id,
        "user_name": user.full_name,
        "place_id": data["place_id"],
        "place": data["place_name"],
        "rating": data["rating"],
        "text": review_text,
        "date": datetime.now().strftime("%Y-%m-%d %H:%M")
    }
    
    save_reviews(reviews)


# ==================== نمایش نظرات ====================

@router.callback_query(F.data == "show_reviews")
async def show_all_reviews(callback: types.CallbackQuery):
    """نمایش آخرین نظرات"""
    
    reviews = load_reviews()
    
    if not reviews:
        text = (
            "💬 <b>نظرات کاربران</b>\n\n"
            "هنوز نظری ثبت نشده!\n"
            "اولین نفر باشید که تجربه خود را به اشتراک می‌گذارد."
        )
    else:
        text = "💬 <b>آخرین نظرات کاربران</b>\n\n"
        
        # مرتب‌سازی بر اساس تاریخ و نمایش ۱۰ تای آخر
        sorted_reviews = sorted(
            reviews.items(), 
            key=lambda x: x[1].get("date", ""), 
            reverse=True
        )[:10]
        
        for review_id, review in sorted_reviews:
            stars = get_star_rating(review.get("rating", 0))
            text += (
                f"📍 <b>{review.get('place', 'نامشخص')}</b>\n"
                f"   {stars}\n"
            )
            if review.get("text"):
                text += f"   💬 «{review['text'][:100]}»\n"
            text += f"   👤 {review.get('user_name', 'ناشناس')} | {review.get('date', '')}\n\n"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✍️ ثبت نظر جدید", callback_data="add_review")],
        [InlineKeyboardButton(text="🔙 بازگشت", callback_data="places")]
    ])
    
    await callback.message.edit_text(
        text, 
        reply_markup=keyboard, 
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("reviews_"))
async def show_place_reviews(callback: types.CallbackQuery):
    """نمایش نظرات یک مکان خاص"""
    
    place_id = callback.data.replace("reviews_", "")
    
    # پیدا کردن نام مکان
    place_name = None
    cat_key = None
    for key, category in CATEGORIES.items():
        for p in category["places"]:
            if p["id"] == place_id:
                place_name = p["name"]
                cat_key = key
                break
        if place_name:
            break
    
    if not place_name:
        await callback.answer("❌ مکان یافت نشد!", show_alert=True)
        return
    
    reviews = load_reviews()
    place_reviews = [
        r for r in reviews.values() 
        if r.get("place_id") == place_id
    ]
    
    avg_rating, count = get_average_rating(place_name)
    
    text = f"💬 <b>نظرات درباره {place_name}</b>\n\n"
    
    if count > 0:
        text += f"⭐ میانگین امتیاز: {avg_rating}/5 ({count} نظر)\n\n"
        text += "━━━━━━━━━━━━━━━━━━━━━\n\n"
        
        for review in place_reviews[-5:]:  # آخرین ۵ نظر
            stars = get_star_rating(review.get("rating", 0))
            text += f"{stars}\n"
            if review.get("text"):
                text += f"💬 «{review['text']}»\n"
            text += f"👤 {review.get('user_name', 'ناشناس')}\n"
            text += f"📅 {review.get('date', '')}\n\n"
    else:
        text += "هنوز نظری برای این مکان ثبت نشده.\n"
        text += "اولین نفر باشید! ⭐"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="⭐ ثبت نظر", 
            callback_data=f"review_place_{place_id}"
        )],
        [InlineKeyboardButton(
            text="🔙 بازگشت به مکان", 
            callback_data=f"place_{place_id}"
        )]
    ])
    
    await callback.message.edit_text(
        text, 
        reply_markup=keyboard, 
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("rate_"))
async def quick_rate(callback: types.CallbackQuery, state: FSMContext):
    """امتیازدهی سریع به مکان"""
    
    place_id = callback.data.replace("rate_", "")
    
    # پیدا کردن نام مکان
    place_name = None
    for category in CATEGORIES.values():
        for p in category["places"]:
            if p["id"] == place_id:
                place_name = p["name"]
                break
        if place_name:
            break
    
    if not place_name:
        await callback.answer("❌ مکان یافت نشد!", show_alert=True)
        return
    
    await state.set_state(ReviewState.waiting_for_rating)
    await state.update_data(place_id=place_id, place_name=place_name)
    
    text = f"⭐ <b>امتیاز شما به {place_name}:</b>"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="1️⃣", callback_data="rating_1"),
            InlineKeyboardButton(text="2️⃣", callback_data="rating_2"),
            InlineKeyboardButton(text="3️⃣", callback_data="rating_3"),
            InlineKeyboardButton(text="4️⃣", callback_data="rating_4"),
            InlineKeyboardButton(text="5️⃣", callback_data="rating_5"),
        ],
        [InlineKeyboardButton(text="❌ انصراف", callback_data=f"place_{place_id}")]
    ])
    
    await callback.message.edit_text(
        text, 
        reply_markup=keyboard, 
        parse_mode="HTML"
    )
    await callback.answer()


# ==================== نقشه همه مکان‌های یک دسته ====================

@router.callback_query(F.data.startswith("map_all_"))
async def show_all_on_map(callback: types.CallbackQuery):
    """ارسال موقعیت همه مکان‌های یک دسته"""
    
    cat_key = callback.data.replace("map_all_", "")
    category = CATEGORIES.get(cat_key)
    
    if not category:
        await callback.answer("❌ دسته‌بندی یافت نشد!", show_alert=True)
        return
    
    await callback.answer("📍 در حال ارسال موقعیت‌ها...")
    
    for place in category["places"]:
        if "coordinates" in place:
            lat, lon = place["coordinates"]
            await callback.message.answer_location(
                latitude=lat,
                longitude=lon
            )
            await callback.message.answer(
                f"📍 <b>{place['name']}</b>\n{place['name_fa']}",
                parse_mode="HTML"
            )


# ==================== دانلود PDF تور ====================

@router.callback_query(F.data == "download_tour_pdf")
async def download_tour_pdf(callback: types.CallbackQuery):
    """اطلاع‌رسانی برای PDF (در آینده پیاده‌سازی)"""
    
    await callback.answer(
        "📥 این قابلیت به‌زودی اضافه می‌شود!\n"
        "فعلاً از لینک گوگل مپ استفاده کنید.",
        show_alert=True
    )