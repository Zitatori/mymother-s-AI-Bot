# data_store.py
import csv, os
from datetime import datetime, timezone

LOG_FILE = "/tmp/conversation_log.csv"

def save_message(role: str, text: str):
    """ユーザー/AIの発話をCSVに1行追記"""
    os.makedirs("/tmp", exist_ok=True)
    ts = datetime.now(timezone.utc).isoformat()
    with open(LOG_FILE, "a", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow([ts, role, text])

def read_log() -> str:
    """CSV全文をテキストで返す（UI表示やDL用）"""
    if not os.path.exists(LOG_FILE):
        return ""
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        return f.read()
