import os
import time
import threading
import requests
import feedparser
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from dotenv import load_dotenv
from deep_translator import GoogleTranslator

# تحميل ملف .env إن وجد
env_path = Path(__file__).resolve().parent / '.env'
load_dotenv(dotenv_path=env_path)

# ==========================================
# 1. خادم الصحة (Health Check)
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
# 2. التوكن والآيدي مباشرة (ضع بياناتك هنا)
# ==========================================
BOT_TOKEN = os.environ.get("BOT_TOKEN") or "8672262564:AAE_SGfQ_EjhCgY-sBAe4ByjZLJ9XgdBQeY"
CHAT_ID = os.environ.get("CHAT_ID") or "@ForexNewsAlerts2026"

translator = GoogleTranslator(source='auto', target='ar')
seen_entries = set()

def translate_text(text):
    try:
        if not text:
            return ""
        return translator.translate(text)
    except Exception as e:
        print(f" [!] Translation warning: {e}")
        return text

def send_telegram_text(message):
    if not BOT_TOKEN or not CHAT_ID:
        print(" [!] ERROR: BOT_TOKEN or CHAT_ID is missing!")
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
        print(f" [!] Telegram Send Error: {e}")

# ==========================================
# 3. جلب الأخبار العامة وترجمتها
# ==========================================
def fetch_translated_news():
    sources = {
        "BBC World": "http://feeds.bbci.co.uk/news/world/rss.xml",
        "Al Jazeera English": "https://www.aljazeera.com/xml/rss/all.xml",
        "CNN World": "http://rss.cnn.com/rss/edition_world.rss",
        "Sky News": "http://feeds.skynews.com/feeds/rss/world.xml",
        "Euronews": "https://www.euronews.com/rss?format=xml",
        "DW News": "https://rss.dw.com/rdf/rss-en-world",
        "الجزيرة": "https://www.aljazeera.net/aljazeerarss/a7c18663-4211-4944-946b-4d352217d74f/73d0e1b4-532f-45ef-b135-bfd3d2cf8101",
        "BBC عربي": "http://feeds.bbci.co.uk/arabic/rss.xml",
        "RT Arabic": "https://arabic.rt.com/rss/"
    }

    for source_name, rss_url in sources.items():
        try:
            feed = feedparser.parse(rss_url)
            for entry in feed.entries[:3]:
                link = entry.get("link", "")
                
                if link in seen_entries:
                    continue

                original_title = entry.get("title", "")
                translated_title = translate_text(original_title)

                message = (
                    f"🌍 **خبر عاجل ({source_name})**\n\n"
                    f"📌 **{translated_title}**\n\n"
                    f"🔗 [اقرأ التفاصيل بالكامل]({link})"
                )

                send_telegram_text(message)
                print(f" [✓] Sent: {original_title[:30]}...")
                
                seen_entries.add(link)
                time.sleep(2)

        except Exception as e:
            print(f" [!] Error fetching from {source_name}: {e}")

# ==========================================
# 4. حلقة التكرار الرئيسية
# ==========================================
if __name__ == "__main__":
    print("... News Translation Bot started")
    
    while True:
        try:
            print("... Checking & Translating new updates")
            fetch_translated_news()
        except Exception as e:
            print(f" [!] Loop error: {e}")
        
        time.sleep(180)
