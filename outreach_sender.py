#!/usr/bin/env python3
"""
🚀 Otel Outreach Gönderim Motoru
Gmail OAuth üzerinden günde maksimum 80 otele güvenli aralıklarla (90-150 sn)
soğuk satış e-postası gönderir. CSV üzerinde durumu 'Sent' olarak günceller.
"""

import os
import sys
import csv
import time
import random
import argparse
import base64
from datetime import datetime
from email.mime.text import MIMEText
from pathlib import Path

# Windows konsol UTF-8 desteği
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parents[2] if len(CURRENT_DIR.parents) >= 3 else CURRENT_DIR
CSV_FILE = CURRENT_DIR / "oteller_lead_listesi.csv"

# Merkezi Google Auth modülünü yükle
oauth_dir = PROJECT_ROOT / "_knowledge" / "credentials" / "oauth"
if oauth_dir.exists():
    sys.path.insert(0, str(oauth_dir))
else:
    sys.path.insert(0, str(CURRENT_DIR))

from google_auth import get_gmail_service
from email_generator import generate_hotel_email


def send_single_email(service, to_email: str, subject: str, body_html: str):
    """Gmail API üzerinden tek bir HTML e-posta gönderir."""
    msg = MIMEText(body_html, "html", "utf-8")
    msg["to"] = to_email
    msg["subject"] = subject
    
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")
    body = {"raw": raw}
    
    sent_message = service.users().messages().send(userId="me", body=body).execute()
    return sent_message


def is_valid_email(email: str) -> bool:
    """E-postanın geçerli bir alan adına sahip olup olmadığını denetler."""
    if not email or "@" not in email:
        return False
    parts = email.split("@")
    domain = parts[-1]
    # npm versiyonları veya geçersiz uzantıları engelle
    if not any(tld in domain for tld in [".com", ".net", ".org", ".tr", ".io", ".co", ".travel", ".de"]):
        return False
    return True


def run_outreach(limit: int = 80, test_email: str = None, min_delay: int = 90, max_delay: int = 150):
    """Günlük limit kadar otele e-posta gönderim döngüsünü yürütür."""
    if not CSV_FILE.exists():
        print(f"HATA: {CSV_FILE} bulunamadı! Önce otel tarayıcıyı çalıştırın.")
        return

    print("\n" + "=" * 65)
    print("🏨 OTEL AI OUTREACH GÖNDERİM MOTORU")
    print(f"Hedef Günlük Limit: {limit} E-posta | Güvenlik Aralığı: {min_delay}-{max_delay} sn")
    print("=" * 65 + "\n")

    # Gmail servisini al
    try:
        service = get_gmail_service("outreach")
        profile = service.users().getProfile(userId="me").execute()
        sender_email = profile.get("emailAddress", "Yetkili Hesap")
        print(f"✅ Gmail API Bağlantısı Aktif: {sender_email}\n")
    except Exception as e:
        print(f"❌ Gmail servisi başlatılamadı: {e}")
        return

    # Test modu kontrolü
    if test_email:
        print(f"🧪 TEST MODU: Belirtilen adrese tek bir deneme e-postası gönderiliyor -> {test_email}")
        preview = generate_hotel_email("Örnek Butik Otel", "Kapadokya / Göreme", "https://ornekotel.com")
        try:
            res = send_single_email(service, test_email, "[TEST] " + preview["subject"], preview["body_html"])
            print(f"🎉 Test e-postası başarıyla gönderildi! Message ID: {res.get('id')}")
        except Exception as e:
            print(f"❌ Test gönderimi başarısız: {e}")
        return

    # CSV'yi oku ve Pending olanları al
    rows = []
    with open(CSV_FILE, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for r in reader:
            rows.append(r)

    pending_indices = [
        i for i, r in enumerate(rows)
        if r.get("Outreach_Status", "").lower() == "pending" and is_valid_email(r.get("Email", ""))
    ]

    total_pending = len(pending_indices)
    if total_pending == 0:
        print("ℹ️ Gönderilecek bekleyen ('Pending') otel bulunamadı.")
        return

    print(f"📋 Toplam Gönderilmeyi Bekleyen Otel Sayısı: {total_pending}")
    targets = pending_indices[:limit]
    print(f"🚀 Bu oturumda gönderilecek hedef: {len(targets)} otel\n")

    sent_count = 0
    for idx, row_idx in enumerate(targets, 1):
        hotel = rows[row_idx]
        hotel_name = hotel["Hotel_Name"]
        region = hotel["Region"]
        website = hotel["Website"]
        email = hotel["Email"]

        print(f"[{idx}/{len(targets)}] ✉️ Gönderiliyor: {hotel_name} ({region}) -> {email} ...", end=" ", flush=True)

        try:
            email_data = generate_hotel_email(hotel_name, region, website)
            send_single_email(service, email, email_data["subject"], email_data["body_html"])

            # Durumu güncelle
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            rows[row_idx]["Outreach_Status"] = "Sent"
            rows[row_idx]["Outreach_Date"] = now_str
            rows[row_idx]["Personalized_Subject"] = email_data["subject"]
            sent_count += 1
            print("✅ BAŞARILI")

            # CSV'yi anlık kaydet (elektrik veya bağlantı kopmasında veri kaybını önler)
            with open(CSV_FILE, "w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)

            # Son gönderim değilse güvenli bekleme yap
            if idx < len(targets):
                wait_time = random.randint(min_delay, max_delay)
                print(f"   ⏳ Spam önleme koruması: {wait_time} saniye bekleniyor...\n")
                time.sleep(wait_time)

        except Exception as e:
            print(f"❌ HATA: {e}")
            rows[row_idx]["Outreach_Status"] = "Failed"
            rows[row_idx]["Notes"] = str(e)[:40]

    print("\n" + "=" * 65)
    print(f"🎉 GÖNDERİM TAMAMLANDI! Toplam Gönderilen: {sent_count} / {len(targets)}")
    print("=" * 65 + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Otel Outreach Gönderici")
    parser.add_argument("--limit", type=int, default=80, help="Gönderilecek maksimum otel sayısı (varsayılan: 80)")
    parser.add_argument("--test", type=str, default=None, help="Belirtilen adrese test e-postası atar")
    parser.add_argument("--fast", action="store_true", help="Geliştirme testi için kısa bekleme (5 sn)")
    args = parser.parse_args()

    min_d, max_d = (3, 6) if args.fast else (90, 150)
    run_outreach(limit=args.limit, test_email=args.test, min_delay=min_d, max_delay=max_d)
