#!/usr/bin/env python3
"""
🔐 Merkezi Google OAuth Modülü
Tüm Antigravity projeleri Google servislerine (Gmail, Sheets, Drive)
bu modül üzerinden erişir.
"""

import os
import json
from pathlib import Path
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

OAUTH_DIR = Path(__file__).resolve().parent

SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/spreadsheets",
]


def get_credentials(account: str = "outreach") -> Credentials:
    """Belirtilen hesap için geçerli Google OAuth credentials döner."""
    token_file = OAUTH_DIR / f"gmail-{account}-token.json"
    env_token = os.environ.get(f"GOOGLE_{account.upper()}_TOKEN_JSON")

    creds = None

    # 1. Yerel token dosyasından oku
    if token_file.exists():
        creds = Credentials.from_authorized_user_file(str(token_file), SCOPES)
    # 2. Environment variable'dan oku (Production / Railway için)
    elif env_token:
        try:
            token_info = json.loads(env_token)
            creds = Credentials.from_authorized_user_info(token_info, SCOPES)
        except Exception:
            pass

    if not creds:
        raise FileNotFoundError(
            f"Google OAuth token bulunamadı: {token_file}\n"
            f"Lütfen 'python auth_helper.py auth {account}' komutu ile yetkilendirme yapın."
        )

    # Süresi dolmuşsa otomatik yenile
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        # Güncel token'ı kaydet
        if token_file.exists():
            with open(token_file, "w", encoding="utf-8") as f:
                f.write(creds.to_json())

    return creds


def get_gmail_service(account: str = "outreach"):
    """Gmail API servisi döner."""
    creds = get_credentials(account)
    return build("gmail", "v1", credentials=creds)


def get_sheets_service(account: str = "outreach"):
    """Google Sheets API servisi döner."""
    creds = get_credentials(account)
    return build("sheets", "v4", credentials=creds)


def get_drive_service(account: str = "outreach"):
    """Google Drive API servisi döner."""
    creds = get_credentials(account)
    return build("drive", "v3", credentials=creds)
