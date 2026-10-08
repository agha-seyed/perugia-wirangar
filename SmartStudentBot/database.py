import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient
from config import settings

logger = logging.getLogger(__name__)

class DatabaseManager:
    """مدیریت جامع و یکپارچه دیتابیس MongoDB با سیستم فال‌بک خودکار"""
    
    def __init__(self):
        self.client: Optional[AsyncIOMotorClient] = None
        self.db = None
        
        # کالکشن‌ها
        self.users = None
        self.consults = None
        self.roommates = None
        self.tickets = None
        self.market = None
        self.events = None
        self.reviews = None
        
        # فال‌بک حافظه‌ای در صورت در دسترس نبودن موقت مونگو
        self._memory_store: Dict[str, Dict[str, Any]] = {
            "users": {},
            "consults": {},
            "roommates": {},
            "tickets": {},
            "market": {},
            "events": {},
            "reviews": {}
        }

    async def connect(self):
        """اتصال ایمن به پایگاه داده"""
        if not settings.MONGO_URI:
            logger.warning("⚠️ MONGO_URI is not set. Database will operate with in-memory fallback.")
            return
            
        uri = settings.MONGO_URI
        try:
            self.client = AsyncIOMotorClient(uri, serverSelectionTimeoutMS=1500)
            await self.client.admin.command('ping')
            db_name = getattr(settings, "DB_NAME", None) or os.getenv("DB_NAME") or os.getenv("DB") or "smart_student_bot"
            try:
                self.db = self.client.get_default_database()
            except Exception:
                self.db = self.client.get_database(db_name)
            if self.db is None:
                self.db = self.client.get_database(db_name)
            logger.info(f"✅ Successfully connected to MongoDB database: '{self.db.name}'")
        except Exception as e:
            if "mongo:" in uri:
                fallback_uri = uri.replace("mongo:", "localhost:")
                try:
                    self.client = AsyncIOMotorClient(fallback_uri, serverSelectionTimeoutMS=1500)
                    await self.client.admin.command('ping')
                    try:
                        self.db = self.client.get_default_database()
                    except Exception:
                        self.db = self.client.get_database(db_name)
                    if self.db is None:
                        self.db = self.client.get_database(db_name)
                    logger.info(f"🔄 Connected to MongoDB via host fallback: {fallback_uri}")
                except Exception:
                    logger.warning("⚠️ MongoDB is not accessible. Running with robust memory fallbacks.")
                    self.client = None
                    return
            else:
                logger.warning(f"⚠️ MongoDB is not accessible ({e}). Running with robust memory fallbacks.")
                self.client = None
                return

        try:
            self.users = self.db.get_collection("users")
            self.consults = self.db.get_collection("consults")
            self.roommates = self.db.get_collection("roommates")
            self.tickets = self.db.get_collection("tickets")
            self.market = self.db.get_collection("market")
            self.events = self.db.get_collection("events")
            self.reviews = self.db.get_collection("reviews")
            
            # ایجاد ایندکس‌های کلیدی برای پرفورمنس بالا
            await self.users.create_index("telegram_id", unique=True)
            await self.consults.create_index("consult_id", unique=True)
            await self.consults.create_index("telegram_id")
            await self.roommates.create_index("ad_id", unique=True)
            await self.roommates.create_index("user_id")
            await self.roommates.create_index("is_active")
            await self.tickets.create_index("ticket_id", unique=True)
            await self.tickets.create_index("user_id")
            await self.market.create_index("item_id", unique=True)
            await self.market.create_index("user_id")
            await self.events.create_index("event_id", unique=True)
            await self.reviews.create_index([("place", 1), ("user_id", 1)])
            
            logger.info("✅ Successfully connected to MongoDB collections and created indexes.")
        except Exception as e:
            logger.error(f"❌ Error setting up collections/indexes: {e}")

    async def close(self):
        """بستن ایمن اتصال دیتابیس"""
        if self.client:
            self.client.close()
            logger.info("🔌 MongoDB connection closed.")

    # ══════════════════════════════════════════
    # ۱. مدیریت کاربران (Users)
    # ══════════════════════════════════════════
    async def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """دریافت پروفایل کاربر با تلگرام آی‌دی"""
        if self.users is not None:
            try:
                return await self.users.find_one({"telegram_id": user_id}, {"_id": 0})
            except Exception as e:
                logger.error(f"Error fetching user {user_id}: {e}")
        return self._memory_store["users"].get(str(user_id))

    async def upsert_user(self, user_id: int, user_data: Dict[str, Any]) -> bool:
        """ثبت یا بروزرسانی پروفایل کاربر"""
        user_data["telegram_id"] = user_id
        user_data["updated_at"] = datetime.now().isoformat()
        if self.users is not None:
            try:
                await self.users.update_one(
                    {"telegram_id": user_id},
                    {"$set": user_data, "$setOnInsert": {"created_at": datetime.now().isoformat()}},
                    upsert=True
                )
                return True
            except Exception as e:
                logger.error(f"Error upserting user {user_id}: {e}")
        
        # ذخیره در فال‌بک
        if str(user_id) not in self._memory_store["users"]:
            self._memory_store["users"][str(user_id)] = {}
        self._memory_store["users"][str(user_id)].update(user_data)
        return True

    async def add_user_xp(self, user_id: int, xp_amount: int) -> int:
        """افزودن امتیاز XP به کاربر برای سیستم گیمیفیکیشن"""
        current_user = await self.get_user(user_id)
        current_xp = current_user.get("xp", 150) if current_user else 150
        new_xp = current_xp + xp_amount
        await self.upsert_user(user_id, {"xp": new_xp})
        return new_xp

    # ══════════════════════════════════════════
    # ۲. مدیریت هم‌اتاقی و مسکن (Roommates)
    # ══════════════════════════════════════════
    async def save_roommate_ad(self, ad_data: Dict[str, Any]) -> bool:
        """ذخیره یا بروزرسانی آگهی مسکن/هم‌اتاقی"""
        ad_id = str(ad_data.get("id") or ad_data.get("ad_id") or f"ad_{int(datetime.now().timestamp())}")
        ad_data["ad_id"] = ad_id
        ad_data["id"] = ad_id
        if "is_active" not in ad_data:
            ad_data["is_active"] = True
            
        if self.roommates is not None:
            try:
                await self.roommates.update_one(
                    {"ad_id": ad_id},
                    {"$set": ad_data},
                    upsert=True
                )
                return True
            except Exception as e:
                logger.error(f"Error saving roommate ad {ad_id}: {e}")
                
        self._memory_store["roommates"][ad_id] = ad_data
        return True

    async def get_active_roommate_ads(self, area: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """دریافت آگهی‌های فعال هم‌اتاقی"""
        query: Dict[str, Any] = {"is_active": True}
        if area and area != "all":
            query["area"] = area
            
        if self.roommates is not None:
            try:
                cursor = self.roommates.find(query, {"_id": 0}).sort("date", -1).limit(limit)
                return await cursor.to_list(length=limit)
            except Exception as e:
                logger.error(f"Error fetching roommate ads: {e}")
                
        ads = list(self._memory_store["roommates"].values())
        filtered = [a for a in ads if a.get("is_active", True)]
        if area and area != "all":
            filtered = [a for a in filtered if a.get("area") == area]
        return sorted(filtered, key=lambda x: str(x.get("date", "")), reverse=True)[:limit]

    async def get_user_roommate_ads(self, user_id: int) -> List[Dict[str, Any]]:
        """دریافت آگهی‌های ثبت شده توسط کاربر خاص"""
        if self.roommates is not None:
            try:
                cursor = self.roommates.find({"user_id": user_id}, {"_id": 0}).sort("date", -1)
                return await cursor.to_list(length=50)
            except Exception as e:
                logger.error(f"Error fetching user roommate ads: {e}")
                
        return [a for a in self._memory_store["roommates"].values() if a.get("user_id") == user_id]

    async def delete_roommate_ad(self, ad_id: str, user_id: int) -> bool:
        """غیرفعال یا حذف کردن آگهی هم‌اتاقی"""
        if self.roommates is not None:
            try:
                res = await self.roommates.update_one(
                    {"ad_id": ad_id, "user_id": user_id},
                    {"$set": {"is_active": False}}
                )
                return res.modified_count > 0
            except Exception as e:
                logger.error(f"Error deleting ad {ad_id}: {e}")
                
        if ad_id in self._memory_store["roommates"]:
            self._memory_store["roommates"][ad_id]["is_active"] = False
            return True
        return False

    # ══════════════════════════════════════════
    # ۳. مدیریت مشاوره‌ها (Consults)
    # ══════════════════════════════════════════
    async def save_consult(self, consult_id: str, data: Dict[str, Any]) -> bool:
        """ذخیره یا بروزرسانی فرم مشاوره"""
        data["consult_id"] = consult_id
        if self.consults is not None:
            try:
                await self.consults.update_one(
                    {"consult_id": consult_id},
                    {"$set": data},
                    upsert=True
                )
                return True
            except Exception as e:
                logger.error(f"Error saving consult {consult_id}: {e}")
                
        self._memory_store["consults"][consult_id] = data
        return True

    async def get_consult(self, consult_id: str) -> Optional[Dict[str, Any]]:
        """دریافت اطلاعات یک فرم مشاوره"""
        if self.consults is not None:
            try:
                return await self.consults.find_one({"consult_id": consult_id}, {"_id": 0})
            except Exception as e:
                logger.error(f"Error loading consult {consult_id}: {e}")
        return self._memory_store["consults"].get(consult_id)

    async def get_user_consults(self, user_id: int) -> List[Dict[str, Any]]:
        """دریافت تمام مشاوره‌های ثبت شده توسط یک کاربر"""
        if self.consults is not None:
            try:
                cursor = self.consults.find({"telegram_id": user_id}, {"_id": 0}).sort("created_at", -1)
                return await cursor.to_list(length=50)
            except Exception as e:
                logger.error(f"Error loading user consults: {e}")
                
        return [c for c in self._memory_store["consults"].values() if c.get("telegram_id") == user_id]

    # ══════════════════════════════════════════
    # ۴. مدیریت تیکت‌های پشتیبانی (Tickets / Feedbacks)
    # ══════════════════════════════════════════
    async def save_ticket(self, ticket_id: str, data: Dict[str, Any]) -> bool:
        """ذخیره یا آپدیت تیکت پشتیبانی"""
        data["ticket_id"] = ticket_id
        if "id" not in data:
            data["id"] = ticket_id
            
        if self.tickets is not None:
            try:
                await self.tickets.update_one(
                    {"ticket_id": ticket_id},
                    {"$set": data},
                    upsert=True
                )
                return True
            except Exception as e:
                logger.error(f"Error saving ticket {ticket_id}: {e}")
                
        self._memory_store["tickets"][ticket_id] = data
        return True

    async def get_ticket(self, ticket_id: str) -> Optional[Dict[str, Any]]:
        """دریافت یک تیکت بر اساس شناسه"""
        if self.tickets is not None:
            try:
                return await self.tickets.find_one({"ticket_id": ticket_id}, {"_id": 0})
            except Exception as e:
                logger.error(f"Error loading ticket {ticket_id}: {e}")
        return self._memory_store["tickets"].get(ticket_id)

    async def get_user_tickets(self, user_id: int) -> List[Dict[str, Any]]:
        """دریافت تیکت‌های کاربر"""
        if self.tickets is not None:
            try:
                cursor = self.tickets.find({"user_id": user_id}, {"_id": 0}).sort("created_at", -1)
                return await cursor.to_list(length=50)
            except Exception as e:
                logger.error(f"Error fetching user tickets: {e}")
                
        return [t for t in self._memory_store["tickets"].values() if t.get("user_id") == user_id]

    # ══════════════════════════════════════════
    # ۵. مدیریت بازارچه دانشجویی (Market)
    # ══════════════════════════════════════════
    async def save_market_item(self, item_data: Dict[str, Any]) -> bool:
        """ذخیره آیتم در بازارچه"""
        item_id = str(item_data.get("id") or item_data.get("item_id") or f"mkt_{int(datetime.now().timestamp())}")
        item_data["item_id"] = item_id
        item_data["id"] = item_id
        if "created_at" not in item_data:
            item_data["created_at"] = datetime.now().isoformat()
            
        if self.market is not None:
            try:
                await self.market.update_one(
                    {"item_id": item_id},
                    {"$set": item_data},
                    upsert=True
                )
                return True
            except Exception as e:
                logger.error(f"Error saving market item: {e}")
                
        self._memory_store["market"][item_id] = item_data
        return True

    async def get_market_items(self, limit: int = 50, skip: int = 0) -> List[Dict[str, Any]]:
        """دریافت آیتم‌های بازارچه"""
        if self.market is not None:
            try:
                cursor = self.market.find({"status": {"$ne": "sold"}}, {"_id": 0}).sort("created_at", -1).skip(skip).limit(limit)
                items = await cursor.to_list(length=limit)
                if items:
                    return items
            except Exception as e:
                logger.error(f"Error loading market items: {e}")
                
        mem_items = list(self._memory_store["market"].values())
        if not mem_items:
            # داده‌های پیش‌فرض تستی بازارچه
            default_items = [
                {
                    "item_id": "m1", "title": "کتاب گرامر ایتالیایی Nuovo Espresso A1", 
                    "price": 15, "category": "books", "description": "بسیار تمیز با تمرین‌های دست‌نخورده",
                    "contact": "@student_perugia", "created_at": "2025-01-15"
                },
                {
                    "item_id": "m2", "title": "دوچرخه شهری دنده‌ای مناسب پروجا", 
                    "price": 45, "category": "transport", "description": "سالم و تست شده با قفل نو",
                    "contact": "@bike_seller", "created_at": "2025-01-18"
                },
                {
                    "item_id": "m3", "title": "بخاری برقی روغنی دلونگی (کم‌مصرف)", 
                    "price": 25, "category": "home", "description": "عالی برای فصل زمستان در خانه دانشجویی",
                    "contact": "@home_tools", "created_at": "2025-01-20"
                }
            ]
            for it in default_items:
                self._memory_store["market"][it["item_id"]] = it
            return default_items
        return sorted(mem_items, key=lambda x: str(x.get("created_at", "")), reverse=True)[skip:skip+limit]

    # ══════════════════════════════════════════
    # ۶. مدیریت رویدادها (Events)
    # ══════════════════════════════════════════
    async def save_event(self, event_data: Dict[str, Any]) -> bool:
        """ذخیره رویداد جدید"""
        event_id = str(event_data.get("event_id") or f"ev_{int(datetime.now().timestamp())}")
        event_data["event_id"] = event_id
        if self.events is not None:
            try:
                await self.events.update_one(
                    {"event_id": event_id},
                    {"$set": event_data},
                    upsert=True
                )
                return True
            except Exception as e:
                logger.error(f"Error saving event: {e}")
                
        self._memory_store["events"][event_id] = event_data
        return True

    async def get_events(self) -> List[Dict[str, Any]]:
        """دریافت لیست رویدادهای دانشگاهی و دورهمی‌ها"""
        if self.events is not None:
            try:
                cursor = self.events.find({}, {"_id": 0}).sort("date", 1)
                items = await cursor.to_list(length=50)
                if items:
                    return items
            except Exception as e:
                logger.error(f"Error loading events: {e}")
                
        mem_events = list(self._memory_store["events"].values())
        if not mem_events:
            # رویدادهای پیش‌فرض فرهنگی و دانشجویی
            default_events = [
                {
                    "event_id": "e1", "title": "دورهمی هفتگی تبادل زبان و فرهنگ (Aperitivo Tandem)",
                    "date": "پنج‌شنبه‌ها ساعت ۱۸:۳۰", "location": "Piazza IV Novembre",
                    "description": "فرصت عالی برای تقویت مکالمه ایتالیایی و آشنایی با دانشجویان بین‌المللی"
                },
                {
                    "event_id": "e2", "title": "تور پیاده‌روی رایگان در مرکز تاریخی و Rocca Paolina",
                    "date": "شنبه آینده ساعت ۱۱:۰۰", "location": "Giardini Carducci",
                    "description": "آشنایی با تاریخ شگفت‌انگیز اتروسک‌ها و پروجا قرون وسطی"
                },
                {
                    "event_id": "e3", "title": "کارگاه آموزشی نحوه تکمیل مدارک بورس ADiSU و ISEE",
                    "date": "سه‌شنبه ساعت ۱۶:۰۰", "location": "آنلاین / دانشگاه پروجا",
                    "description": "پاسخ به سوالات متداول دانشجویان پیرامون خوابگاه، سلف و قسط‌های بورس"
                }
            ]
            for ev in default_events:
                self._memory_store["events"][ev["event_id"]] = ev
            return default_events
        return mem_events

    # ══════════════════════════════════════════
    # ۷. مدیریت نظرات و امتیازات مکان‌ها (Places Reviews)
    # ══════════════════════════════════════════
    async def save_place_review(self, place_name: str, user_id: int, review_data: Dict[str, Any]) -> bool:
        """ثبت نظر کاربر درباره یک مکان"""
        review_id = f"{place_name}_{user_id}"
        review_data["review_id"] = review_id
        review_data["place"] = place_name
        review_data["user_id"] = user_id
        review_data["created_at"] = datetime.now().isoformat()
        
        if self.reviews is not None:
            try:
                await self.reviews.update_one(
                    {"place": place_name, "user_id": user_id},
                    {"$set": review_data},
                    upsert=True
                )
                return True
            except Exception as e:
                logger.error(f"Error saving review: {e}")
                
        self._memory_store["reviews"][review_id] = review_data
        return True

    async def get_place_reviews(self, place_name: str) -> List[Dict[str, Any]]:
        """دریافت نظرات یک مکان مشخص"""
        if self.reviews is not None:
            try:
                cursor = self.reviews.find({"place": place_name}, {"_id": 0}).sort("created_at", -1)
                return await cursor.to_list(length=50)
            except Exception as e:
                logger.error(f"Error fetching reviews for {place_name}: {e}")
                
        return [r for r in self._memory_store["reviews"].values() if r.get("place") == place_name]

    async def get_place_avg_rating(self, place_name: str) -> tuple:
        """محاسبه میانگین امتیاز یک مکان (میانگین, تعداد)"""
        reviews = await self.get_place_reviews(place_name)
        if not reviews:
            return 0.0, 0
        ratings = [r["rating"] for r in reviews if "rating" in r]
        if not ratings:
            return 0.0, 0
        return round(sum(ratings) / len(ratings), 1), len(ratings)

# ساخت یک نمونه سراسری (Singleton)
db_manager = DatabaseManager()

