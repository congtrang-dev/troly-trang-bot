"""
===========================================
  GOOGLE SHEETS SERVICE - sheets_service.py
  Quản lý danh sách khách hàng tiềm năng
===========================================
"""

import os
from datetime import datetime
import gspread
from google.oauth2 import service_account

CREDENTIALS_FILE = os.getenv("GOOGLE_CREDENTIALS_FILE", "credentials.json")
SPREADSHEET_ID = os.getenv("GOOGLE_SPREADSHEET_ID")
SHEET_NAME = "Khách hàng"

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# Cột trong spreadsheet
HEADERS = [
    "STT", "Tên KH / Công ty", "Người liên hệ", "SĐT",
    "Email", "Nhu cầu", "Trạng thái", "Ghi chú", "Ngày thêm", "Cập nhật lần cuối"
]

STATUS_LIST = ["Mới", "Đang tư vấn", "Đã chốt", "Không tiềm năng"]
STATUS_EMOJI = {
    "Mới": "🆕",
    "Đang tư vấn": "💬",
    "Đã chốt": "✅",
    "Không tiềm năng": "❌",
}


class SheetsService:
    def __init__(self):
        try:
            creds = service_account.Credentials.from_service_account_file(
                CREDENTIALS_FILE, scopes=SCOPES
            )
            self.gc = gspread.authorize(creds)
            self.spreadsheet = self.gc.open_by_key(SPREADSHEET_ID)
            self._ensure_sheet()
        except Exception as e:
            print(f"⚠️ Không thể kết nối Google Sheets: {e}")
            self.spreadsheet = None
            self.sheet = None

    def _ensure_sheet(self):
        """Tạo sheet nếu chưa có, thêm header"""
        try:
            self.sheet = self.spreadsheet.worksheet(SHEET_NAME)
        except gspread.WorksheetNotFound:
            self.sheet = self.spreadsheet.add_worksheet(SHEET_NAME, rows=1000, cols=10)
            self.sheet.append_row(HEADERS)
            # Format header
            self.sheet.format("A1:J1", {
                "backgroundColor": {"red": 0.2, "green": 0.5, "blue": 0.9},
                "textFormat": {"bold": True, "foregroundColor": {"red": 1, "green": 1, "blue": 1}},
            })

    def _get_all_customers(self) -> list[dict]:
        if not self.sheet:
            return []
        try:
            records = self.sheet.get_all_records()
            return records
        except:
            return []

    def _get_next_stt(self) -> int:
        records = self._get_all_customers()
        if not records:
            return 1
        return len(records) + 1

    async def add_customer(self, name: str, status: str = "Mới",
                           phone: str = "", email: str = "",
                           need: str = "", note: str = "",
                           contact_person: str = "") -> str:
        if not self.sheet:
            return "❌ Chưa cấu hình Google Sheets"
        try:
            now = datetime.now().strftime("%d/%m/%Y %H:%M")
            stt = self._get_next_stt()

            row = [
                stt, name, contact_person, phone,
                email, need, status, note, now, now
            ]
            self.sheet.append_row(row)

            emoji = STATUS_EMOJI.get(status, "📋")
            return (
                f"✅ *Đã thêm khách hàng!*\n\n"
                f"👤 *{name}*\n"
                f"🏷️ Người liên hệ: {contact_person or 'Chưa có'}\n"
                f"📞 SĐT: {phone or 'Chưa có'}\n"
                f"📧 Email: {email or 'Chưa có'}\n"
                f"💼 Nhu cầu: {need or 'Chưa rõ'}\n"
                f"{emoji} Trạng thái: *{status}*\n"
                f"📝 Ghi chú: {note or 'Không có'}"
            )
        except Exception as e:
            return f"❌ Lỗi thêm KH: {str(e)}"

    async def get_customers(self, status: str = None, search: str = None) -> str:
        if not self.sheet:
            return "❌ Chưa cấu hình Google Sheets"
        try:
            records = self._get_all_customers()
            if not records:
                return "👥 *Chưa có khách hàng nào*\n\nNhắn để thêm KH mới: _\"Thêm KH: Tên, SĐT, nhu cầu\"_"

            # Lọc theo status
            if status:
                records = [r for r in records if r.get("Trạng thái", "").lower() == status.lower()]

            # Tìm kiếm theo tên
            if search:
                search_lower = search.lower()
                records = [r for r in records if
                           search_lower in str(r.get("Tên KH / Công ty", "")).lower() or
                           search_lower in str(r.get("Người liên hệ", "")).lower()]

            if not records:
                return f"🔍 Không tìm thấy khách hàng phù hợp"

            # Nhóm theo trạng thái
            grouped = {}
            for r in records:
                st = r.get("Trạng thái", "Khác")
                grouped.setdefault(st, []).append(r)

            lines = [f"👥 *Danh sách khách hàng ({len(records)} KH):*\n"]

            for st in STATUS_LIST:
                if st not in grouped:
                    continue
                emoji = STATUS_EMOJI.get(st, "📋")
                lines.append(f"\n{emoji} *{st}* ({len(grouped[st])} KH):")
                for r in grouped[st]:
                    name = r.get("Tên KH / Công ty", "?")
                    phone = r.get("SĐT", "")
                    need = r.get("Nhu cầu", "")
                    phone_str = f" | 📞 {phone}" if phone else ""
                    need_str = f"\n    💼 {need}" if need else ""
                    lines.append(f"  • *{name}*{phone_str}{need_str}")

            return "\n".join(lines)

        except Exception as e:
            return f"❌ Lỗi lấy danh sách KH: {str(e)}"

    async def update_customer(self, name: str, status: str = None, note: str = None) -> str:
        if not self.sheet:
            return "❌ Chưa cấu hình Google Sheets"
        try:
            records = self.sheet.get_all_records()
            name_lower = name.lower()

            # Tìm dòng cần cập nhật
            row_idx = None
            for i, r in enumerate(records):
                if name_lower in str(r.get("Tên KH / Công ty", "")).lower():
                    row_idx = i + 2  # +2 vì header ở row 1, records bắt đầu từ row 2
                    break

            if row_idx is None:
                return f"❌ Không tìm thấy khách hàng tên *{name}*"

            now = datetime.now().strftime("%d/%m/%Y %H:%M")
            updates = []

            if status:
                self.sheet.update_cell(row_idx, 7, status)  # Cột G - Trạng thái
                updates.append(f"Trạng thái → *{status}*")

            if note:
                old_note = records[row_idx - 2].get("Ghi chú", "")
                new_note = f"{old_note}\n[{now}] {note}".strip()
                self.sheet.update_cell(row_idx, 8, new_note)  # Cột H - Ghi chú
                updates.append(f"Ghi chú mới: _{note}_")

            self.sheet.update_cell(row_idx, 10, now)  # Cột J - Cập nhật lần cuối

            found_name = records[row_idx - 2].get("Tên KH / Công ty", name)
            emoji = STATUS_EMOJI.get(status, "✏️") if status else "✏️"
            return (
                f"{emoji} *Đã cập nhật KH: {found_name}*\n\n"
                + "\n".join(f"  • {u}" for u in updates)
            )

        except Exception as e:
            return f"❌ Lỗi cập nhật KH: {str(e)}"

    async def get_report(self) -> str:
        if not self.sheet:
            return "❌ Chưa cấu hình Google Sheets"
        try:
            records = self._get_all_customers()
            total = len(records)
            if total == 0:
                return "📊 *Báo cáo KH:* Chưa có dữ liệu"

            # Thống kê theo trạng thái
            stats = {}
            for r in records:
                st = r.get("Trạng thái", "Khác")
                stats[st] = stats.get(st, 0) + 1

            lines = [f"📊 *Báo cáo khách hàng:*\n"]
            lines.append(f"👥 Tổng số KH: *{total}*\n")

            for st in STATUS_LIST:
                count = stats.get(st, 0)
                emoji = STATUS_EMOJI.get(st, "📋")
                pct = round(count / total * 100) if total > 0 else 0
                bar = "▓" * (pct // 10) + "░" * (10 - pct // 10)
                lines.append(f"{emoji} {st}: *{count}* ({pct}%)\n  {bar}")

            # Tỉ lệ chuyển đổi
            chot = stats.get("Đã chốt", 0)
            conversion = round(chot / total * 100) if total > 0 else 0
            lines.append(f"\n🎯 Tỉ lệ chuyển đổi: *{conversion}%* ({chot}/{total})")

            return "\n".join(lines)

        except Exception as e:
            return f"❌ Lỗi tạo báo cáo: {str(e)}"
