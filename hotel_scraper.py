#!/usr/bin/env python3
"""
🏨 Otel Lead Scraper & Chatbot Filtresi
Türkiye genelindeki butik, resort ve tatil otellerini tarar.
- Otelin web sitesini inceler.
- Sitede canlı destek / chatbot (Tidio, Tawk.to, Crisp, Intercom vb.) VARSA otomatik ELER.
- Chatbot YOKSA resmi e-posta adresini (info@, rezervasyon@ vb.) ve telefonunu bulur.
- Sonuçları oteller_lead_listesi.csv dosyasına kaydeder.
"""

import os
import sys
import re
import csv
import time
import urllib.parse
from pathlib import Path
import requests
from bs4 import BeautifulSoup

# Windows konsol UTF-8 desteği
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Çıktı dosyası yolu
CURRENT_DIR = Path(__file__).resolve().parent
CSV_FILE = CURRENT_DIR / "oteller_lead_listesi.csv"

# ❌ CHATBOT VE CANLI DESTEK İMZALARI
# Bu scriptler veya ifadeler sitede varsa o otel doğrudan ELENİR!
CHATBOT_SIGNATURES = [
    r"tidio\.co",
    r"code\.tidio\.co",
    r"embed\.tawk\.to",
    r"widget\.intercom\.io",
    r"client\.crisp\.chat",
    r"cdn\.livechatinc\.com",
    r"static\.zdassets\.com",  # Zendesk
    r"code\.jivosite\.com",
    r"jivochat",
    r"widget\.smartsupp\.com",
    r"chatra\.io",
    r"freshchat",
    r"drift\.com",
    r"botpress",
    r"voiceflow",
    r"manychat",
    r"hubspot\.messages",
    r"webchat",
    r"wp-chatbot",
    r"collect\.chat"
]

# E-posta çıkarmada elenecek geçersiz uzantılar ve dummy domainler
INVALID_EMAIL_DOMAINS = [
    "example.com", "domain.com", "email.com", "wixpress.com", 
    "sentry.io", "googleapis.com", "schema.org", "w3.org"
]
INVALID_EMAIL_EXTENSIONS = [".png", ".jpg", ".jpeg", ".webp", ".svg", ".gif", ".css", ".js"]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


def check_has_chatbot(html_text: str) -> bool:
    """HTML kaynak kodunda canlı destek veya AI chatbot var mı kontrol eder."""
    html_lower = html_text.lower()
    for sig in CHATBOT_SIGNATURES:
        if re.search(sig, html_lower):
            return True
    return False


def extract_emails(html_text: str, base_domain: str = "") -> list:
    """Sayfa metninden ve mailto linklerinden geçerli e-postaları ayıklar."""
    emails = set()

    # 1. mailto: linklerinden çek
    soup = BeautifulSoup(html_text, "html.parser")
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if href.startswith("mailto:"):
            mail = href.replace("mailto:", "").split("?")[0].strip()
            if mail:
                emails.add(mail.lower())

    # 2. Regex ile metinden çek
    pattern = r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"
    matches = re.findall(pattern, html_text)
    for m in matches:
        m = m.lower().strip(".")
        # npm paketlerini filtrele (@1.2.3 vb.)
        if re.search(r"@\d+\.\d+", m):
            continue
        # TLD kontrolü (en az 2 harfli gerçek uzantı: .com, .net, .tr vb.)
        if not re.search(r"\.[a-zA-Z]{2,}$", m):
            continue
        # Geçersiz uzantı kontrolü
        if any(m.endswith(ext) for ext in INVALID_EMAIL_EXTENSIONS):
            continue
        # Geçersiz domain kontrolü
        domain = m.split("@")[-1]
        if any(inv in domain for inv in INVALID_EMAIL_DOMAINS):
            continue
        emails.add(m)

    # Otel için en uygun e-postaları önceliklendir (info, rezervasyon, contact vb.)
    priority_order = ["rezervasyon", "reservation", "booking", "info", "contact", "iletisim", "sales"]
    sorted_emails = sorted(
        list(emails),
        key=lambda e: next((i for i, p in enumerate(priority_order) if p in e), 99)
    )
    return sorted_emails


def extract_phone(soup: BeautifulSoup, html_text: str) -> str:
    """Otel telefon numarasını bulmaya çalışır."""
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if href.startswith("tel:"):
            return href.replace("tel:", "").strip()

    # TR telefon regex'i
    phone_pattern = r"(?:\+90|0)?\s*(?:\(?\d{3}\)?)\s*\d{3}\s*\d{2}\s*\d{2}"
    matches = re.findall(phone_pattern, html_text)
    if matches:
        return matches[0].strip()
    return ""


def analyze_hotel_website(url: str) -> dict:
    """
    Otelin web sitesini tarar:
    - Chatbot var mı kontrol eder.
    - Ana sayfa ve iletişim sayfasından e-posta/telefon çıkarır.
    """
    if not url.startswith("http"):
        url = "https://" + url

    result = {
        "website": url,
        "has_chatbot": False,
        "email": "",
        "phone": "",
        "status": "error"
    }

    try:
        resp = requests.get(url, headers=HEADERS, timeout=12, verify=False)
        if resp.status_code != 200:
            result["status"] = f"http_{resp.status_code}"
            return result

        html = resp.text
        # 1. Chatbot Kontrolü
        if check_has_chatbot(html):
            result["has_chatbot"] = True
            result["status"] = "has_chatbot_skipped"
            return result

        soup = BeautifulSoup(html, "html.parser")
        domain = urllib.parse.urlparse(url).netloc
        emails = extract_emails(html, domain)
        phone = extract_phone(soup, html)

        # Ana sayfada e-posta bulunamadıysa iletişim sayfasına bak
        if not emails:
            contact_links = []
            for a in soup.find_all("a", href=True):
                href = a["href"].lower()
                if any(k in href for k in ["iletisim", "contact", "ulasim", "bize-ulasin"]):
                    full_url = urllib.parse.urljoin(url, a["href"])
                    if full_url != url:
                        contact_links.append(full_url)

            for c_url in contact_links[:2]:
                try:
                    c_resp = requests.get(c_url, headers=HEADERS, timeout=8, verify=False)
                    if c_resp.status_code == 200:
                        # İletişim sayfasında chatbot var mı bak
                        if check_has_chatbot(c_resp.text):
                            result["has_chatbot"] = True
                            result["status"] = "has_chatbot_skipped"
                            return result
                        c_emails = extract_emails(c_resp.text, domain)
                        if c_emails:
                            emails.extend(c_emails)
                            break
                except Exception:
                    continue

        if emails:
            result["email"] = emails[0]
            result["phone"] = phone
            result["status"] = "valid_lead"
        else:
            result["status"] = "no_email_found"

    except Exception as e:
        result["status"] = f"connection_error: {str(e)[:30]}"

    return result


def init_csv():
    """CSV dosyasını başlıklarıyla hazırlar (mevcutsa korur)."""
    if not CSV_FILE.exists():
        with open(CSV_FILE, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                "Hotel_Name", "Region", "Website", "Email", "Phone",
                "Has_Chatbot", "Outreach_Status", "Outreach_Date", "Personalized_Subject", "Notes"
            ])


def get_existing_websites():
    """Zaten taranmış siteleri döndürür (mükerrerliği önler)."""
    if not CSV_FILE.exists():
        return set()
    sites = set()
    with open(CSV_FILE, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("Website"):
                sites.add(row["Website"].lower().rstrip("/"))
    return sites


def append_lead(hotel_name: str, region: str, website: str, email: str, phone: str, status: str = "Pending"):
    """Yeni geçerli lead'i CSV'ye ekler."""
    with open(CSV_FILE, "a", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            hotel_name, region, website, email, phone,
            "False", status, "", "", "Scraped & Verified (No Chatbot)"
        ])


# ─── ÖRNEK HEDEF HAVUZ (TÜRKİYE GENELİ SEÇKİN BUTİK OTELLER) ──────────────────
PRESET_HOTEL_CANDIDATES = [
    # Kapadokya Butik & Mağara Otelleri
    {"name": "Mithra Cave Hotel", "region": "Kapadokya / Göreme", "url": "https://mithracavehotel.com"},
    {"name": "Sultan Cave Suites", "region": "Kapadokya / Göreme", "url": "https://sultancavesuites.com"},
    {"name": "Koza Cave Hotel", "region": "Kapadokya / Göreme", "url": "https://kozacavehotel.com"},
    {"name": "Artemis Cave Suites", "region": "Kapadokya / Göreme", "url": "https://artemiscavesuites.com"},
    {"name": "Taskonaklar Cave Hotel", "region": "Kapadokya / Uçhisar", "url": "https://taskonaklar.com"},
    {"name": "Dere Suites Cappadocia", "region": "Kapadokya / Ürgüp", "url": "https://deresuites.com"},
    {"name": "Museum Hotel Cappadocia", "region": "Kapadokya / Uçhisar", "url": "https://museumhotel.com.tr"},
    
    # Ege / Akdeniz Butik Otelleri
    {"name": "Caresse Luxury Resort", "region": "Bodrum / Muğla", "url": "https://caresse.com.tr"},
    {"name": "Ada Hotel Bodrum", "region": "Bodrum / Türkbükü", "url": "https://adahotel.com"},
    {"name": "Lissiya Hotel", "region": "Fethiye / Faralya", "url": "https://lissiyahotel.com"},
    {"name": "Perdue Hotel", "region": "Fethiye / Faralya", "url": "https://perdue.com.tr"},
    {"name": "Nautical Hotel", "region": "Fethiye / Faralya", "url": "https://nautical.com.tr"},
    {"name": "Lukka Exclusive Hotel", "region": "Kaş / Çukurbağ", "url": "https://lukkahotel.com"},
    {"name": "Radisson Blu Resort Cesme", "region": "Çeşme / İzmir", "url": "https://radissonhotels.com"},
    {"name": "Alavya Hotel", "region": "Alaçatı / Çeşme", "url": "https://alavya.com.tr"},
    
    # Sapanca / Doğa / Bungalov Otelleri
    {"name": "Richmond Nua Wellness Spa", "region": "Sapanca / Sakarya", "url": "https://richmondnua.com"},
    {"name": "Sapanca Alfa Suites", "region": "Sapanca / Sakarya", "url": "https://sapancaalfasuites.com"},
    {"name": "Villa Geyik Sapanca", "region": "Sapanca / Sakarya", "url": "https://villageyik.com"},
    {"name": "Ridos Thermal Hotel", "region": "İkizdere / Rize", "url": "https://ridos.com.tr"},
    {"name": "Gazelle Resort & Spa", "region": "Bolu / Karacasu", "url": "https://gazelleresort.com"},

    # İstanbul Şehir & Tarihi Butik Otelleri
    {"name": "Sirkeci Mansion Hotel", "region": "İstanbul / Sirkeci", "url": "https://sirkecimansion.com"},
    {"name": "Hotel Sultania", "region": "İstanbul / Sultanahmet", "url": "https://hotelsultania.com"},
    {"name": "White House Hotel Istanbul", "region": "İstanbul / Sultanahmet", "url": "https://whitehousehotelistanbul.com"},
    {"name": "The Bank Hotel Istanbul", "region": "İstanbul / Karaköy", "url": "https://thebankhotelistanbul.com"},
    {"name": "Pera Palace Hotel", "region": "İstanbul / Beyoğlu", "url": "https://perapalace.com"}
]


def run_scraper(candidates: list = None):
    """Tarayıcıyı çalıştırır, chatbotu olmayanları listeye kaydeder."""
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    init_csv()
    existing_sites = get_existing_websites()
    target_list = candidates or PRESET_HOTEL_CANDIDATES

    print("\n🔍 OTEL LEAD TARAYICI & CHATBOT DENETÇİSİ BAŞLATILDI")
    print("=" * 65)
    print("Kural: Sitede Canlı Destek / AI Chatbot VARSA doğrudan ELENECEK.")
    print("=" * 65 + "\n")

    added_count = 0
    skipped_chatbot = 0
    skipped_no_email = 0

    for hotel in target_list:
        clean_url = hotel["url"].lower().rstrip("/")
        if clean_url in existing_sites:
            print(f"⏩ [ZATEN KAYITLI] {hotel['name']} ({hotel['region']})")
            continue

        print(f"⏳ Taranıyor: {hotel['name']} -> {hotel['url']} ...", end=" ", flush=True)
        res = analyze_hotel_website(hotel["url"])

        if res["has_chatbot"]:
            print(f"❌ [ATLANDI: CHATBOT VAR] Sitede canlı destek tespit edildi!")
            skipped_chatbot += 1
        elif res["status"] == "valid_lead":
            append_lead(
                hotel_name=hotel["name"],
                region=hotel["region"],
                website=res["website"],
                email=res["email"],
                phone=res["phone"]
            )
            print(f"✅ [UYGUN LEAD EKLENDİ] Mail: {res['email']} | Tel: {res['phone'] or 'Belirtilmemiş'}")
            added_count += 1
            existing_sites.add(clean_url)
        else:
            print(f"⚠️ [ATLANDI: {res['status']}] E-posta bulunamadı.")
            skipped_no_email += 1

        time.sleep(0.5)

    print("\n" + "=" * 65)
    print(f"📊 TARAMA RAPORU:")
    print(f"  • Yeni Eklenen Uygun Oteller: {added_count}")
    print(f"  • Chatbot Bulunduğu İçin Elenen: {skipped_chatbot}")
    print(f"  • E-posta Bulunamadığı İçin Elenen: {skipped_no_email}")
    print(f"  • Toplam Lead Dosyası: {CSV_FILE}")
    print("=" * 65 + "\n")


if __name__ == "__main__":
    run_scraper()
