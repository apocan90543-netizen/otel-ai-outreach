#!/usr/bin/env python3
"""
✉️ Otel Kişiselleştirilmiş Satış E-postası Üretici
OpenAI GPT-4o-mini kullanarak her otele özel, yüksek dönüşümlü soğuk satış e-postası hazırlar.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Windows konsol UTF-8 desteği
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parents[2]
MASTER_ENV = PROJECT_ROOT / "_knowledge" / "credentials" / "master.env"

if MASTER_ENV.exists():
    load_dotenv(MASTER_ENV)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


def generate_hotel_email(hotel_name: str, region: str, website: str = "", sender_name: str = "Abdullah") -> dict:
    """
    Otel için özel konu ve e-posta gövdesi oluşturur.
    OpenAI API varsa GPT-4o-mini ile dinamik yazar, yoksa mükemmel şablon döner.
    """
    subject = f"{hotel_name} için 7/24 Web Canlı Destek & Rezervasyon AI Asistanı"

    # OpenAI ile kişiselleştirme dene
    if OPENAI_API_KEY:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=OPENAI_API_KEY)

            system_prompt = (
                "Sen butik ve resort otellere 7/24 web canlı destek ve rezervasyon yapay zeka asistanı hizmeti "
                "sunan başarılı bir B2B satış ve otomasyon danışmanısın. Amacın otel genel müdürü veya rezervasyon "
                "yöneticisini etkileyerek 2 dakikalık bir demo incelemesini sağlamak. "
                "Ton: Saygılı, kurumsal, samimi, abartısız, doğrudan fayda odaklı Türkçe. "
                "Em-dash (uzun çizgi) kullanma. Kısa ve net paragraflar yaz."
            )

            user_prompt = f"""
Hedef Otel: {hotel_name}
Bölge/Konum: {region}
Web Sitesi: {website}
Gönderen: {sender_name} (AI Otomasyon Danışmanı)

Bu otel için kısa, vurucu ve profesyonel bir soğuk satış e-postası yaz.
E-postada şu kilit noktaları geçir:
1. Web sitelerinde şu anda gece-gündüz anlık yanıt veren bir canlı destek/asistan bulunmadığını (müşteri kaybı önleme).
2. Geliştirdiğimiz AI asistanın oda tipleri, fiyatlar, kahvaltı, transfer ve kuralları 5 dilde (TR, EN, RU, AR, DE) anında yanıtladığını.
3. Resepsiyonun telefon ve WhatsApp yükünü hafifletirken doğrudan komisyonsuz rezervasyon talebi topladığını.
4. {hotel_name} için çalışan örnek bir canlı demo hazırladığımızı ve 7 gün ücretsiz deneyebileceklerini.

Çıktıyı SADECE geçerli bir HTML formatında ver (inline CSS'li şık modern e-posta tasarımı, <html> ve <body> etiketleri olmadan temiz div içinde).
İlk satıra 'SUBJECT: <Konu Başlığı>' yaz.
            """

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=800
            )

            content = response.choices[0].message.content.strip()
            if "SUBJECT:" in content:
                parts = content.split("SUBJECT:", 1)[1].split("\n", 1)
                custom_subject = parts[0].strip()
                html_body = parts[1].strip() if len(parts) > 1 else content
                return {"subject": custom_subject, "body_html": html_body}

        except Exception as e:
            # Hata durumunda aşağıdaki kanıtlanmış şablona düşer
            pass

    # Yüksek dönüşümlü varsayılan HTML şablonu (Fallback)
    html_template = f"""
    <div style="font-family: 'Segoe UI', Arial, sans-serif; font-size: 15px; line-height: 1.6; color: #222222; max-width: 600px; margin: 0 auto; border: 1px solid #e5e7eb; border-radius: 8px; padding: 24px; background-color: #ffffff;">
        <p style="margin-top: 0;">Sayın <strong>{hotel_name}</strong> Yetkilisi,</p>
        
        <p>
            Web sitenizi incelediğimde, <strong>{region}</strong> bölgesindeki seçkin konseptinizi ve sunduğunuz konaklama deneyimini takdirle karşıladım.
        </p>
        
        <p>
            Ancak fark ettiğim üzere, web sitenizi özellikle gece saatlerinde veya farklı ülkelerden ziyaret eden potansiyel misafirlerinizin sorularını (oda tipleri, güncel fiyatlar, kahvaltı, transfer, kurallar) anında karşılayacak <strong>7/24 aktif bir canlı destek asistanı</strong> bulunmuyor. Bu durum, bilgi alamayan ziyaretçilerin doğrudan OTA platformlarına (Booking vb.) yönelmesine ve yüksek komisyon ödenmesine neden olabiliyor.
        </p>
        
        <div style="background-color: #f8fafc; border-left: 4px solid #3b82f6; padding: 14px 18px; margin: 18px 0; border-radius: 4px;">
            <p style="margin: 0; font-weight: 600; color: #1e3a8a;">Oteller için geliştirdiğimiz 7/24 Yapay Zeka Misafir Temsilcisi:</p>
            <ul style="margin: 8px 0 0 0; padding-left: 20px; color: #334155;">
                <li><strong>5 Dilde Anında Yanıt:</strong> Türkçe, İngilizce, Rusça, Arapça ve Almanca 0.3 saniyede akıcı iletişim.</li>
                <li><strong>Komisyonsuz Rezervasyon:</strong> Misafirlerin iletişim ve tarih bilgilerini toplayıp doğrudan resepsiyonunuza iletir.</li>
                <li><strong>İş Yükünü Azaltma:</strong> Resepsiyon ekibinizin sürekli aynı sorulara cevap verme yükünü %70 hafifletir.</li>
            </ul>
        </div>
        
        <p>
            <strong>{hotel_name}</strong> için örnek olarak hazırladığımız çalışan canlı demo panelini 2 dakika incelemek veya sistemimizi <strong>7 gün boyunca ücretsiz denemek</strong> ister misiniz?
        </p>
        
        <p>
            Sizin için uygunsa bu e-postayı <em>"Evet, detayları görelim"</em> şeklinde yanıtlamanız yeterlidir; demo linkini ve detayları hemen paylaşabilirim.
        </p>
        
        <hr style="border: none; border-top: 1px solid #e5e7eb; margin: 24px 0 16px 0;">
        
        <p style="margin-bottom: 0; font-size: 14px; color: #475569;">
            Saygılarımla,<br>
            <strong>{sender_name}</strong><br>
            <span style="color: #64748b;">Yapay Zeka Otomasyon Sistemleri</span>
        </p>
    </div>
    """

    return {
        "subject": subject,
        "body_html": html_template.strip()
    }


if __name__ == "__main__":
    demo = generate_hotel_email("Mithra Cave Hotel", "Kapadokya / Göreme", "https://mithracavehotel.com")
    print("\n--- ÖRNEK E-POSTA KONUSU ---")
    print(demo["subject"])
    print("\n--- ÖRNEK E-POSTA GÖVDESİ (İLK 300 KARAKTER) ---")
    print(demo["body_html"][:300] + "...")
