import os
import re
import time
import requests
from woocommerce import API
from instagrapi import Client

# ==========================================
# ۱. تنظیمات اختصاصی شما (فقط این ۴ خط را پر کنید)
# ==========================================
SITE_URL = "https://www.asansazeh.com"
WC_CONSUMER_KEY = "ck_YOUR_CONSUMER_KEY_HERE"       # کلید عمومی ووکامرس
WC_CONSUMER_SECRET = "cs_YOUR_CONSUMER_SECRET_HERE" # کلید خصوصی ووکامرس

IG_USERNAME = "your_instagram_username"            # نام کاربری پیج اینستاگرام (بدون @)
IG_PASSWORD = "your_instagram_password"            # رمز عبور پیج اینستاگرام

# ==========================================
# ۲. فایل‌های کمکی ربات (دست نزنید)
# ==========================================
HISTORY_FILE = "posted_ids.txt"
SESSION_FILE = "ig_session.json"
TEMP_IMAGE = "temp_product.jpg"

wcapi = API(
    url=SITE_URL,
    consumer_key=WC_CONSUMER_KEY,
    consumer_secret=WC_CONSUMER_SECRET,
    version="wc/v3",
    timeout=30
)

def get_posted_ids():
    if not os.path.exists(HISTORY_FILE):
        return set()
    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
        return set(line.strip() for line in f if line.strip())

def save_posted_id(product_id):
    with open(HISTORY_FILE, "a", encoding="utf-8") as f:
        f.write(f"{product_id}\n")

def clean_html(raw_html):
    text = re.sub(r'<.*?>', '', raw_html or '')
    return text.strip()

def fetch_next_product():
    posted_ids = get_posted_ids()
    page = 1
    while True:
        res = wcapi.get("products", params={"status": "publish", "per_page": 50, "page": page})
        if res.status_code != 200:
            print("خطا در خواندن محصولات سایت:", res.text)
            return None
        products = res.json()
        if not products:
            break
        for p in products:
            pid = str(p["id"])
            if pid not in posted_ids and p.get("images"):
                return p
        page += 1
    return None

def download_image(url):
    res = requests.get(url, timeout=30)
    if res.status_code == 200:
        with open(TEMP_IMAGE, "wb") as f:
            f.write(res.content)
        return True
    return False

def login_instagram():
    cl = Client()
    cl.delay_range = [2, 5]  # مکث طبیعی برای جلوگیری از حساسیت اینستاگرام
    if os.path.exists(SESSION_FILE):
        try:
            cl.load_settings(SESSION_FILE)
            cl.login(IG_USERNAME, IG_PASSWORD)
            return cl
        except Exception:
            pass
    cl.login(IG_USERNAME, IG_PASSWORD)
    cl.dump_settings(SESSION_FILE)
    return cl

def run_once():
    print("در حال جستجوی محصول جدید...")
    product = fetch_next_product()
    if not product:
        print("همه محصولات سایت قبلاً پست شده‌اند!")
        return

    pid = str(product["id"])
    name = product["name"]
    link = product["permalink"]
    price = product.get("price", "")
    image_url = product["images"][0]["src"]
    short_desc = clean_html(product.get("short_description", ""))[:350]

    price_text = f"💰 قیمت: {price} تومان\n\n" if price else ""

    caption = (
        f"📌 {name}\n\n"
        f"{short_desc}\n\n"
        f"{price_text}"
        f"📥 دانلود فایل و جزئیات بیشتر در سایت آسان‌سازه:\n"
        f"{link}\n\n"
        f"#عمران #معماری #مهندسی_عمران #آسان_سازه #فایل_آموزشی #سازه"
    )

    print(f"دانلود تصویر محصول: {name}")
    if not download_image(image_url):
        print("خطا در دانلود عکس محصول!")
        return

    try:
        print("در حال اتصال به اینستاگرام و ارسال پست...")
        cl = login_instagram()
        cl.photo_upload(TEMP_IMAGE, caption=caption)
        save_posted_id(pid)
        print(f"✅ محصول «{name}» با موفقیت در اینستاگرام منتشر شد!")
    except Exception as e:
        print("❌ خطا در ارسال به اینستاگرام:", e)
    finally:
        if os.path.exists(TEMP_IMAGE):
            os.remove(TEMP_IMAGE)

if __name__ == "__main__":
    run_once()
