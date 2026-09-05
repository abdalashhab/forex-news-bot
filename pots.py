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

# ذاكرة لمنع التكرار والحماية من حظر تلغرام
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
# 3. جلب الأخبار اللحظية مع منع التكرار
# ==========================================
def fetch_realtime_news():
    sources = {
        "BBC World": "http://feeds.bbci.co.uk/news/world/rss.xml",
        "Al Jazeera English": "https://www.aljazeera.com/xml/rss/all.xml"
    }

    for source_name, rss_url in sources.items():
        try:
            feed = feedparser.parse(rss_url)
            for entry in feed.entries[:3]:
                link = entry.get("link", "")
                
                # تخطي الخبر إذا تم إرساله مسبقاً
                if link in seen_entries:
                    continue

                title = entry.get("title", "")

                message = (
                    f"🌍 **تحديث عاجل ({source_name})**\n\n"
                    f"📌 **{title}**\n\n"
                    f"🔗 [اقرأ الخبر كاملًا]({link})"
                )

                send_telegram_text(message)
                print(f" [✓] تم إرسال خبر جديد: {title[:40]}...")
                
                # حفظ الرابط في الذاكرة
                seen_entries.add(link)
                time.sleep(1) # تأخير ثانية لحماية البوت

        except Exception as e:
            print(f" [!] تعذر جلب الأخبار من {source_name}: {e}")

# ==========================================
# 4. حلقة التشغيل الفورية (فحص كل 60 ثانية)
# ==========================================
if __name__ == "__main__":
    print("... بدأ تشغيل البوت المباشر للأخبار العاجلة")
    
    while True:
        try:
            print("... جاري فحص الأخبار الجديدة")
            fetch_realtime_news()
        except Exception as e:
            print(f" [!] حدث خطأ أثناء التحديث: {e}")
        
        # فحص المصادر كل دقيقة
        time.sleep(60)
