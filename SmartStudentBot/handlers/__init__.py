# این فایل تمام روترها را اکسپورت می‌کند تا در main.py راحت استفاده شوند
from .cmd_start import router as start_router
# بعداً اضافه می‌شوند:
# from .weather_handler import router as weather_router
# from .news_handler import router as news_router
# ...

__all__ = ["start_router"]