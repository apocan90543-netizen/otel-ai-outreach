#!/usr/bin/env python3
import time
import os
import threading
from outreach_sender import run_outreach
from reply_watcher import watch_inbox_loop

print("🚀 Railway 7/24 Otel Müşteri Kazanım Servisi Başlatıldı!")

# Yanıt dinleyiciyi ayrı bir thread'de başlat
watcher_thread = threading.Thread(target=watch_inbox_loop, kwargs={"interval_seconds": 120}, daemon=True)
watcher_thread.start()

# Gönderim döngüsü: Her gün 80 otele güvenli aralıklarla gönder
while True:
    try:
        print("📨 Günlük e-posta gönderim turu başlıyor...")
        run_outreach(limit=80, min_delay=90, max_delay=150)
    except Exception as e:
        print(f"Gönderim hatası: {e}")
    
    print("⏳ Günlük kota tamamlandı. 12 saat bekleniyor...")
    time.sleep(43200)  # 12 saat bekle
