#!/usr/bin/env python3
"""
👀 Otel Gelen Yanıt Takipçisi & Telegram Bildirici
Gmail kutusunu dinler, otellerden gelen yanıtları yakalar,
OpenAI ile analizi yapıp Abdullah'ın Telegram'ına anında sıcak lead bildirimi atar.
"""

import os
import sys
import time
import json
import base64
import requests
from pathlib import Path
from dotenv import load_dotenv

# Windows konsol UTF-8 desteği
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parents[2] if len(CURRENT_DIR.parents) >= 3 else CURRENT_DIR
MASTER_ENV = PROJECT_ROOT / "_knowledge" / "credentials" / "master.env"

if MASTER_ENV.exists():
    load_dotenv(MASTER_ENV)

# Merkezi Google Auth modülü
oauth_dir = PROJECT_ROOT / "_knowledge" / "credentials" / "oauth"
if oauth_dir.exists():
    sys.path.insert(0, str(oauth_dir))
else:
    sys.path.insert(0, str(CURRENT_DIR))

from google_auth import get_gmail_service

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


def send_telegram_alert(message: str) -> bool:
    """Telegram üzerinden yöneticiye anlık bildirim iletir."""
    if not TELEGRAM_BOT_TOKEN or not ADMIN_CHAT_ID:
        print("⚠️ Telegram token veya Chat ID tanımlı değil, terminale yazdırılıyor.")
        return False
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": ADMIN_CHAT_ID,
            "text": message,
            "parse_mode": "HTML"
        }
        resp = requests.post(url, json=payload, timeout=10)
        return resp.status_code == 200
    except Exception as e:
        print(f"Telegram gönderim hatası: {e}")
        return False


def analyze_reply_with_ai(from_email: str, subject: str, message_body: str) -> dict:
    """Gelen e-postanın niyetini ve yanıt taslağını GPT-4o-mini ile analiz eder."""
    if not OPENAI_API_KEY:
        return {
            "intent": "Müşteri Dönüş Yaptı (AI Analizi Devre Dışı)",
            "action": "Otelle iletişime geçin ve demo panelini paylaşın."
        }
    try:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)

        prompt = f"""
Gelen E-posta Gönderen: {from_email}
Konu: {subject}
İçerik: {message_body}

Bir otel yetkilisinden aldığımız bu yanıtı analiz et.
1. Niyet nedir? (Örn: Demo İstiyor / Fiyat Soruyor / İlgilenmiyor / Teknik Soru)
2. Bu otele ne cevap vermeliyiz? (Kısa 2-3 cümlelik samimi ve profesyonel Türkçe yanıt önerisi).

JSON formatında yanıt ver:
{{"intent": "...", "suggested_action": "...", "reply_draft": "..."}}
        """

        res = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.3
        )
        return json.loads(res.choices[0].message.content)
    except Exception:
        return {
            "intent": "Müşteri Yanıt Verdi",
            "suggested_action": "Otel yetkilisine demo linkini iletin.",
            "reply_draft": "Merhaba, ilginiz için teşekkür ederiz. Canlı demo linkimiz..."
        }


def get_target_hotel_domains() -> set:
    """CSV dosyasındaki hedef otellerin domain ve e-postalarını toplar."""
    csv_file = CURRENT_DIR / "oteller_lead_listesi.csv"
    targets = set()
    if not csv_file.exists():
        return targets
    try:
        import csv
        with open(csv_file, "r", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                mail = r.get("Email", "").lower().strip()
                if mail:
                    targets.add(mail)
                    domain = mail.split("@")[-1]
                    targets.add(domain)
    except Exception:
        pass
    return targets


def send_auto_reply(service, to_email: str, in_reply_to_subject: str, hotel_name: str = ""):
    """Otele demo linki ve şeffaf fiyatlandırmayı içeren otomatik yanıt gönderir."""
    subject = in_reply_to_subject if in_reply_to_subject.lower().startswith("re:") else f"Re: {in_reply_to_subject}"
    
    body_html = f"""
    <div style="font-family: 'Segoe UI', Arial, sans-serif; font-size: 15px; line-height: 1.6; color: #222222; max-width: 600px; margin: 0 auto; border: 1px solid #e2e8f0; border-radius: 8px; padding: 24px; background-color: #ffffff;">
        <p style="margin-top: 0;">Sayın Yetkili,</p>
        
        <p>İlginiz ve geri dönüşünüz için çok teşekkür ederiz!</p>
        
        <p>
            Oteliniz için hazırladığımız çalışan canlı demo panelini aşağıdaki bağlantıdan hemen test edebilirsiniz:
        </p>
        
        <div style="text-align: center; margin: 24px 0;">
            <a href="https://otel-ai-asistan.up.railway.app" style="background-color: #2563eb; color: #ffffff; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: 600; display: inline-block;">
                👉 Canlı Demo Panelini İnceleyin
            </a>
        </div>
        
        <div style="background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px; padding: 16px; margin: 20px 0;">
            <h4 style="margin: 0 0 10px 0; color: #1e293b;">💰 Şeffaf Fiyatlandırma & Paket Detayları:</h4>
            <ul style="margin: 0; padding-left: 20px; color: #334155;">
                <li><strong>Aylık Abonelik:</strong> <strong>3.500 TL / ay</strong> (Sabit fiyat, gizli maliyet yok).</li>
                <li><strong>Kurulum:</strong> <strong>ÜCRETSİZ</strong>.</li>
                <li><strong>Ücretsiz Deneme:</strong> <strong>7 Gün Boyunca Tamamen Ücretsiz Deneyebilirsiniz</strong>. Memnun kalmazsanız hiçbir taahhüt veya ücret yoktur.</li>
                <li><strong>Özellikler:</strong> 7/24 kesintisiz 5 dilde (TR, EN, RU, AR, DE) anlık misafir yanıtlama, komisyonsuz doğrudan rezervasyon talebi toplama.</li>
            </ul>
        </div>
        
        <p>
            Sistemi kendi web sitenize eklemek sadece <strong>1 satırlık hazır bir kod</strong> eklemekten ibarettir (web yöneticiniz 2 dakikada ekleyebilir).
        </p>
        
        <p>
            Oteliniz için <strong>7 günlük ücretsiz deneme kurulumunu</strong> bugün başlatmamızı isterseniz, bu e-postayı <em>"Başlatalım"</em> şeklinde onaylamanız yeterlidir.
        </p>
        
        <hr style="border: none; border-top: 1px solid #e2e8f0; margin: 20px 0 16px 0;">
        
        <p style="margin-bottom: 0; font-size: 14px; color: #64748b;">
            Saygılarımla,<br>
            <strong>Abdullah</strong><br>
            Yapay Zeka Otomasyon Sistemleri
        </p>
    </div>
    """
    
    from email.mime.text import MIMEText
    import base64
    
    msg = MIMEText(body_html, "html", "utf-8")
    msg["to"] = to_email
    msg["subject"] = subject
    
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")
    service.users().messages().send(userId="me", body={"raw": raw}).execute()
    print(f"🚀 Otomatik demo ve fiyat teklifi başarıyla iletildi: {to_email}")


def check_unread_replies(service):
    """Gelen kutusundaki okunmamış yanıtları kontrol eder."""
    print("🔍 Gelen kutusu taranıyor...", flush=True)
    results = service.users().messages().list(userId="me", q="is:unread", maxResults=20).execute()
    messages = results.get("messages", [])

    if not messages:
        print("ℹ️ Yeni okunmamış yanıt yok.")
        return

    hotel_targets = get_target_hotel_domains()
    outreach_keywords = ["canlı destek", "rezervasyon", "otel", "ai asistan", "demo"]

    for msg_meta in messages:
        msg_id = msg_meta["id"]
        msg = service.users().messages().get(userId="me", id=msg_id, format="full").execute()
        
        headers = msg.get("payload", {}).get("headers", [])
        subject = next((h["value"] for h in headers if h["name"].lower() == "subject"), "(Konusuz)")
        from_email = next((h["value"] for h in headers if h["name"].lower() == "from"), "(Bilinmiyor)")
        snippet = msg.get("snippet", "")

        from_lower = from_email.lower()
        sub_lower = subject.lower()

        # Kendimiz veya sistem/bülten maillerini doğrudan atla
        if any(ign in from_lower for ign in ["mevlutkonuskan", "google", "no-reply", "noreply", "kariyer", "pazarama", "skool", "serpapi"]):
            continue

        # Filtre: Gönderen otel listemizde mi VEYA konu/içerik outreach ile mi alakalı?
        is_hotel_match = any(t in from_lower for t in hotel_targets)
        is_subject_match = any(kw in sub_lower for kw in outreach_keywords)

        if not (is_hotel_match or is_subject_match):
            continue

        print(f"\n🔔 OTELDEN YANIT ALINDI!\n  Kimden: {from_email}\n  Konu: {subject}\n  Özet: {snippet}\n")

        # Yapay zeka ile analiz et
        ai_res = analyze_reply_with_ai(from_email, subject, snippet)
        intent = ai_res.get("intent", "Otel Yanıtı")

        # 1. Otomatik Demo ve Fiyat Teklifini Gönder
        try:
            clean_email = from_email.split("<")[-1].replace(">", "").strip() if "<" in from_email else from_email.strip()
            send_auto_reply(service, clean_email, subject)
            auto_reply_status = "✅ Otomatik Demo Linki & 3.500 TL/Ay Teklifi İletildi!"
        except Exception as e:
            auto_reply_status = f"⚠️ Otomatik yanıt gönderilemedi: {e}"

        # 2. Telegram Bildirimi Formatı
        tg_text = (
            f"🏨 <b>YENİ OTEL MÜŞTERİ YANITI!</b>\n\n"
            f"👤 <b>Kimden:</b> <code>{from_email}</code>\n"
            f"📌 <b>Konu:</b> {subject}\n"
            f"💬 <b>Gelen Mesaj:</b> <i>{snippet}</i>\n\n"
            f"🎯 <b>Niyet:</b> {intent}\n"
            f"⚡ <b>Yapılan İşlem:</b> {auto_reply_status}\n\n"
            f"💰 <b>Teklif Edilen Fiyat:</b> 3.500 TL/Ay (7 Gün Ücretsiz Deneme)\n"
            f"🚀 <i>Müşteri sıcak, tebrikler!</i>"
        )

        send_telegram_alert(tg_text)
        print("📲 Telegram bildirimi yöneticinin telefonuna iletildi.")

        # Okundu olarak işaretle
        service.users().messages().modify(
            userId="me", id=msg_id, body={"removeLabelIds": ["UNREAD"]}
        ).execute()


def watch_inbox_loop(interval_seconds: int = 120):
    """Belirli aralıklarla arka planda gelen kutusunu sürekli dinler."""
    print("\n" + "=" * 65)
    print("👀 OTEL YANIT DİNLEYİCİSİ DEVREDE (7/24)")
    print(f"Tarama Aralığı: Her {interval_seconds} saniyede bir")
    print("=" * 65 + "\n")

    service = get_gmail_service("outreach")

    while True:
        try:
            check_unread_replies(service)
        except Exception as e:
            print(f"Hata oluştu: {e}")
        time.sleep(interval_seconds)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Gelen E-posta Dinleyici")
    parser.add_argument("--once", action="store_true", help="Tek seferlik tara ve çık")
    parser.add_argument("--interval", type=int, default=120, help="Döngü aralığı saniye (varsayılan: 120)")
    args = parser.parse_args()

    if args.once:
        service = get_gmail_service("outreach")
        check_unread_replies(service)
    else:
        watch_inbox_loop(args.interval)
