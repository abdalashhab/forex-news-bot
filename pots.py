# ==========================================
# 1. استدعاء كافة المكتبات (Imports)
# ==========================================
import os
import time
import requests
import feedparser
from bs4 import BeautifulSoup
from deep_translator import GoogleTranslator
from dotenv import load_dotenv
from PIL import Image
import pandas as pd

# ==========================================
# 2. الإعدادات والثوابت وترخيص البيئة (Configurations)
# ==========================================
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

RSS_SOURCES = {
    "FXStreet": "https://www.fxstreet.com/rss/news",
    "ForexFactory": "https://www.forexfactory.com/news.xml"
}

# الكلمات المفتاحية المطلوبة للفلترة (الذهب والعملات الأساسية)
TARGET_KEYWORDS = [
    "gold", "xauusd", "bullion", 
    "usd", "eur", "gbp", "jpy", 
    "fed", "federal reserve", "ecb", 
    "interest rate", "inflation", "cpi"
]

REQUEST_TIMEOUT = 15
MAX_SUMMARY_WORDS = 25

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

# ==========================================
# 3. الدوال والوظائف الخاصة (Functions)
# ==========================================

def is_relevant_news(title, summary):
    """دالة الفلترة: تفحص إذا كان الخبر متعلقاً بالذهب أو العملات الأساسية"""
    content_to_check = f"{title} {summary}".lower()
    for keyword in TARGET_KEYWORDS:
        if keyword in content_to_check:
            return True, keyword.upper()  # يرجع True مع الكلمة التي تم العثور عليها
    return False, None

def fetch_rss_data(url):
    feed = feedparser.parse(url)
    return feed.entries

def extract_image_url(summary_html):
    if not summary_html:
        return None
    soup = BeautifulSoup(summary_html, 'html.parser')
    img_tag = soup.find('img')
    if img_tag and 'src' in img_tag.attrs:
        return img_tag['src']
    return None

def shorten_text(text, max_words=25):
    words = text.split()
    if len(words) > max_words:
        return " ".join(words[:max_words]) + "..."
    return text

def translate_to_arabic(text):
    try:
        translated = GoogleTranslator(source='auto', target='ar').translate(text)
        return translated
    except Exception as e:
        print(f"حدث خطأ أثناء الترجمة: {e}")
        return text

def process_and_resize_image(image_url, output_path="temp.jpg"):
    try:
        response = requests.get(image_url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        if response.status_code == 200:
            with open(output_path, 'wb') as f:
                f.write(response.content)
            
            with Image.open(output_path) as img:
                img = img.resize((800, 450))
                img.save(output_path)
            return output_path
    except Exception as e:
        print(f"فشل معالجة الصورة: {e}")
    return None

def send_telegram_post(photo_path, caption):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
    try:
        with open(photo_path, 'rb') as photo:
            payload = {
                "chat_id": CHAT_ID,
                "caption": caption,
                "parse_mode": "Markdown"
            }
            files = {"photo": photo}
            response = requests.post(url, data=payload, files=files, timeout=REQUEST_TIMEOUT)
            return response.json()
    except Exception as e:
        print(f"خطأ في الاتصال بالتلجرام: {e}")
        return None

def send_telegram_text(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        payload = {
            "chat_id": CHAT_ID,
            "text": text,
            "parse_mode": "Markdown"
        }
        response = requests.post(url, data=payload, timeout=REQUEST_TIMEOUT)
        return response.json()
    except Exception as e:
        print(f"خطأ في إرسال الرسالة النصية: {e}")
        return None

def log_to_dataframe(title, summary, link, source, keyword):
    data = [{
        "Source": source,
        "Keyword_Found": keyword,
        "Title": title,
        "Summary": summary,
        "Link": link,
        "Timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }]
    df = pd.DataFrame(data)
    print("\n--- سجل الخبر المعالج والمفلتر (Pandas) ---")
    print(df[['Source', 'Keyword_Found', 'Title', 'Timestamp']])

# ==========================================
# 4. التنفيذ الرئيسي (Main Logic)
# ==========================================
if __name__ == "__main__":
    print("بدأ تشغيل المحرك المفلتر لأخبار الذهب والعملات الأساسية...")
    
    for source_name, rss_url in RSS_SOURCES.items():
        print(f"\n[+] جلب الأخبار من: {source_name}")
        entries = fetch_rss_data(rss_url)
        
        for entry in entries[:5]:  # فحص أول 5 أخبار من التغذية
            raw_summary = entry.summary if 'summary' in entry else entry.title
            clean_text = BeautifulSoup(raw_summary, 'html.parser').get_text()
            
            # 1. إيقاف التناقل وتطبيق الفلترة
            is_relevant, found_keyword = is_relevant_news(entry.title, clean_text)
            
            if not is_relevant:
                print(f"[-] تجاهل الخبر: لا يتضمن الذهب أو العملات الأساسية ({entry.title[:30]}...)")
                continue  # تخطي هذا الخبر والانتقال للخبر التالي
                
            print(f"[✓] تم رصد خبر مهم متعلق بـ [{found_keyword}]!")
            
            # 2. الاختصار والترجمة فقط للأخبار المفلترة
            shortened = shorten_text(clean_text, max_words=MAX_SUMMARY_WORDS)
            arabic_text = translate_to_arabic(shortened)
            
            # 3. توثيق البيانات عبر Pandas
            log_to_dataframe(entry.title, arabic_text, entry.link, source_name, found_keyword)
            
            # 4. معالجة الصورة وإعداد الرسالة
            img_url = extract_image_url(entry.summary) if 'summary' in entry else None
            local_image = process_and_resize_image(img_url) if img_url else None
            
            message = (
                f"🎯 **عاجل أسواق ({source_name}) | #{found_keyword}:**\n\n"
                f"{arabic_text}\n\n"
                f"🔗 [اقرأ الخبر كاملاً]({entry.link})"
            )
            
            # 5. الإرسال للتلجرام
            if local_image and os.path.exists(local_image):
                send_telegram_post(local_image, message)
                os.remove(local_image)
            else:
                send_telegram_text(message)
                
            print(f"تم إرسال خبر {found_keyword} بنجاح!")
            break  # إرسال أحدث خبر مفلتر واحد من كل مصدر ثم الخروج
