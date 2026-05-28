"""
===========================================
  CREDENTIALS HELPER - credentials_helper.py
  Đọc Google credentials từ file hoặc biến môi trường
===========================================
"""

import os
import json
import tempfile
from google.oauth2 import service_account

def get_credentials(scopes: list):
    """
    Ưu tiên đọc từ biến môi trường GOOGLE_CREDENTIALS_JSON (dùng trên Railway)
    Nếu không có thì đọc từ file credentials.json (dùng local)
    """
    credentials_json = os.getenv("GOOGLE_CREDENTIALS_JSON")

    if credentials_json:
        # Đọc từ biến môi trường (Railway)
        try:
            info = json.loads(credentials_json)
            return service_account.Credentials.from_service_account_info(
                info, scopes=scopes
            )
        except Exception as e:
            raise Exception(f"Lỗi đọc GOOGLE_CREDENTIALS_JSON: {e}")
    else:
        # Đọc từ file local
        credentials_file = os.getenv("GOOGLE_CREDENTIALS_FILE", "credentials.json")
        return service_account.Credentials.from_service_account_file(
            credentials_file, scopes=scopes
        )
