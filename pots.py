import os
import time
import threading
import requests
import feedparser
from http.server import HTTPServer, BaseHTTPRequestHandler

# ==========================================
# 1. خادم الصحة (Health Check) لـ Render
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
    server.serve_forever()

threading.Thread(target=run_health_check, daemon=True).start()

# ==========================================
# 2. إعدادات التلغرام والذاكرة
# ==========================================
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

# سجل حفظ روابط الأخبار لمنع الإرسال المكرر
seen_entries = set()

def send_telegram_text(message):
    if not BOT_TOKEN or not CHAT_ID:
        print(" [!] خطأ: لم يتم ضبط BOT_TOKEN أو CHAT_ID!")
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
        print(f" [!] خطأ أثناء الإرسال للتلغرام: {e}")

# ==========================================
# 3. دالة جلب جميع الأخبار العالمية (بدون فلترة)
# ==========================================
def fetch_all_global_news():
    # مصادر إخبارية عالمية متنوعة
    sources = {
        "FXStreet News": "https://www.fxstreet.com/rss/news",
        "ForexFactory": "https://www.forexfactory.com/news.xml",
        "Investing.com Forex": "https://www.investing.com/rss/news_1.rss",
        "Investing.com Commodities": "https://www.investing.com/rss/news_11.rss"
    }

    for source_name, rss_url in sources.items():
        try:
            feed = feedparser.parse(rss_url)
            # فحص أحدث 3 أخبار من كل مصدر في كل دورة
            for entry in feed.entries[:3]:
                link = entry.get("link", "")
                
                # إهمال الخبر إذا تم إرساله من قبل
                if link in seen_entries:
                    continue

                title = entry.get("title", "")

                # صياغة الرسالة الشاملة
                message = (
                    f"🌐 **خبر عالمي جديد ({source_name})**\n\n"
                    f"📌 **{title}**\n\n"
                    f"🔗 [اقرأ الخبر كاملاً]({link})"
                )

                # الإرسال المباشر للتلغرام
                send_telegram_text(message)
                print(f" [✓] تم إرسال: {title[:40]}...")

                # حفظ الرابط في الذاكرة
                seen_entries.add(link)

        except Exception as e:
            print(f" [!] تعذر جلب الأخبار من {source_name}: {e}")

# ==========================================
# 4. حلقة التشغيل الدائمة
# ==========================================
if __name__ == "__main__":
    print("... بدأ تشغيل مجس الأخبار العالمية الشامل")
    
    while True:
        try:
            print("... جاري جلب أحدث الأخبار العالمية من جميع المصادر")
            fetch_all_global_news()
        except Exception as e:
            print(f" [!] حدث خطأ أثناء التحديث: {e}")
        
        # الانتظار دقيقتين بين كل فحص لسرعة جلب التحديثات
        time.sleep(120)
