import os
import time
import threading
import requests
import feedparser
from bs4 import BeautifulSoup
from http.server import HTTPServer, BaseHTTPRequestHandler

# ==========================================
# 1. إعداد خادم الصحة (Health Check) لـ Render
# ==========================================
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

    def log_message(self, format, *args):
        return

def run_health_check():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    print(f" [✓] تم تشغيل خادم الاستجابة على المنفذ: {port}")
    server.serve_forever()

# تشغيل خادم الصحة في Thread منفصل بداخل الخلفية
threading.Thread(target=run_health_check, daemon=True).start()

# ==========================================
# 2. إعدادات البوت ومتغيرات البيئة
# ==========================================
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

# القائمة المؤقتة لحفظ الأخبار المنسوخة لمنع التكرار
seen_entries = set()

def send_telegram_text(message):
    """إرسال رسالة نصية للتلغرام"""
    if not BOT_TOKEN or not CHAT_ID:
        print(" [!] خطأ: لم يتم ضبط BOT_TOKEN أو CHAT_ID في متغيرات البيئة!")
        return
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "Markdown",
        "disable_web_page_preview": False
    }
    try:
        response = requests.post(url, data=payload, timeout=10)
        response.raise_for_status()
    except Exception as e:
        print(f" [!] خطأ في إرسال الرسالة إلى التلغرام: {e}")

def send_telegram_post(photo_path, caption):
    """إرسال صورة مع نص للتلغرام"""
    if not BOT_TOKEN or not CHAT_ID:
        print(" [!] خطأ: لم يتم ضبط BOT_TOKEN أو CHAT_ID!")
        return
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
    try:
        with open(photo_path, "rb") as photo:
            payload = {
                "chat_id": CHAT_ID,
                "caption": caption,
                "parse_mode": "Markdown"
            }
            files = {"photo": photo}
            response = requests.post(url, data=payload, files=files, timeout=15)
            response.raise_for_status()
    except Exception as e:
        print(f" [!] تعذر إرسال الصورة ({e})، يتم الإرسال كنص فقط...")
        send_telegram_text(caption)

# ==========================================
# 3. دالة جلب الأخبار وتصليحها
# ==========================================
def check_and_send_news():
    """دالة فحص مصادر الأخبار ومعالجتها وإرسالها"""
    
    # قائمة مصادر RSS
    sources = {
        "FXStreet": "https://www.fxstreet.com/rss/news",
        "ForexFactory": "https://www.forexfactory.com/news.xml"
    }

    # الكلمات المفتاحية المطلوبة
    keywords = ["gold", "xauusd", "fed", "inflation", "cpi", "dollar", "powell", "interest rate"]

    for source_name, rss_url in sources.items():
        print(f" [+] جلب الأخبار من: {source_name}")
        try:
            feed = feedparser.parse(rss_url)
            for entry in feed.entries[:5]:  # فحص أحدث 5 أخبار فقط
                link = entry.get("link", "")
                
                # تخطي الخبر إذا تم إرساله سابقاً
                if link in seen_entries:
                    continue

                title = entry.get("title", "")
                title_lower = title.lower()

                # التثبت من وجود كلمة مفتاحية
                found_keyword = None
                for kw in keywords:
                    if kw in title_lower:
                        found_keyword = kw
                        break

                if found_keyword:
                    # صياغة النص النهائي للخبر
                    message = (
                        f"🚨 **عاجل أسواق ({source_name})** | #{found_keyword.upper()}\n\n"
                        f"📌 **{title}**\n\n"
                        f"🔗 [اقرأ الخبر كاملاً]({link})"
                    )

                    # إرسال الخبر للتلغرام
                    send_telegram_text(message)
                    print(f" [✓] تم إرسال خبر ({found_keyword}) بنجاح!")
                    
                    # حفظ الخبر لمنع تكراره
                    seen_entries.add(link)
                    
                    # الخروج من حلقة المصدر بعد إرسال أحدث خبر مفلتر
                    break

        except Exception as e:
            print(f" [!] خطأ أثناء فحص المصدر {source_name}: {e}")

# ==========================================
# 4. حلقة التشغيل الدائمة للبوت
# ==========================================
if __name__ == "__main__":
    print("... بدأ تشغيل المحرك المفلتر لأخبار الذهب والعملات الأساسية")
    
    while True:
        try:
            print("... جاري فحص الأخبار")
            check_and_send_news()
        except Exception as e:
            print(f" [!] حدث خطأ عام في الحلقة الرئيسية: {e}")
        
        # الانتظار 5 دقائق (300 ثانية) قبل إعادة الفحص
        time.sleep(300)
