"""
===========================================
  GOOGLE SHEETS SERVICE - sheets_service.py
  Quản lý danh sách khách hàng tiềm năng
===========================================
"""

import os
from datetime import datetime
import gspread
from credentials_helper import get_credentials

SPREADSHEET_ID = os.getenv("GOOGLE_SPREADSHEET_ID")
SHEET_NAME = "Khách hàng"

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# Cột trong spreadsheet (13 cột)
HEADERS = [
    "STT",                  # A
    "Tên KH / Công ty",     # B
    "Người liên hệ",        # C
    "SĐT",                  # D
    "Email",                # E
    "Nhu cầu",              # F
    "Tiềm năng (NAV)",      # G
    "Nguồn KH",             # H
    "Trạng thái",           # I
    "Ngày hẹn tiếp theo",   # J
    "Ghi chú",              # K
    "Ngày thêm",            # L
    "Cập nhật lần cuối",    # M
]

# Vị trí cột (1-indexed)
COL = {
    "stt": 1, "name": 2, "contact": 3, "phone": 4,
    "email": 5, "need": 6, "nav": 7, "source": 8,
    "status": 9, "next_meeting": 10, "note": 11,
    "created": 12, "updated": 13,
}

STATUS_LIST = ["Mới", "Đang tư vấn", "Đã chốt", "Không tiềm năng"]
STATUS_EMOJI = {
    "Mới": "🆕",
    "Đang tư vấn": "💬",
    "Đã chốt": "✅",
    "Không tiềm năng": "❌",
}

NAV_LIST = ["Cao", "Trung bình", "Thấp"]
NAV_EMOJI = {"Cao": "🔥", "Trung bình": "⚡", "Thấp": "🌱"}

SOURCE_LIST = ["Facebook", "Zalo", "Giới thiệu", "Website", "Gọi trực tiếp", "Khác"]


class SheetsService:
    def __init__(self):
        try:
            creds = get_credentials(SCOPES)
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
            # Nếu sheet trống thì thêm header
            if not self.sheet.row_values(1):
                self._setup_headers()
        except gspread.WorksheetNotFound:
            self.sheet = self.spreadsheet.add_worksheet(SHEET_NAME, rows=1000, cols=13)
            self._setup_headers()

    def _setup_headers(self):
        self.sheet.append_row(HEADERS)
        self.sheet.format("A1:M1", {
            "backgroundColor": {"red": 0.13, "green": 0.37, "blue": 0.87},
            "textFormat": {
                "bold": True,
                "foregroundColor": {"red": 1, "green": 1, "blue": 1},
                "fontSize": 11,
            },
            "horizontalAlignment": "CENTER",
        })
        # Freeze header row
        self.sheet.freeze(rows=1)

    def _get_all_customers(self) -> list[dict]:
        if not self.sheet:
            return []
        try:
            return self.sheet.get_all_records()
        except:
            return []

    def _get_next_stt(self) -> int:
        records = self._get_all_customers()
        return len(records) + 1

    async def add_customer(self, name: str, status: str = "Mới",
                           phone: str = "", email: str = "",
                           need: str = "", note: str = "",
                           contact_person: str = "", nav: str = "",
                           source: str = "", next_meeting: str = "") -> str:
        if not self.sheet:
            return "❌ Chưa cấu hình Google Sheets"
        try:
            now = datetime.now().strftime("%d/%m/%Y %H:%M")
            stt = self._get_next_stt()

            row = [
                stt,            # A - STT
                name,           # B - Tên KH
                contact_person, # C - Người liên hệ
                phone,          # D - SĐT
                email,          # E - Email
                need,           # F - Nhu cầu
                nav,            # G - Tiềm năng (NAV)
                source,         # H - Nguồn KH
                status,         # I - Trạng thái
                next_meeting,   # J - Ngày hẹn tiếp
                note,           # K - Ghi chú
                now,            # L - Ngày thêm
                now,            # M - Cập nhật lần cuối
            ]
            self.sheet.append_row(row)

            status_emoji = STATUS_EMOJI.get(status, "📋")
            nav_emoji = NAV_EMOJI.get(nav, "")
            return (
                f"✅ *Đã thêm khách hàng!*\n\n"
                f"👤 *{name}*\n"
                f"🏷️ Người liên hệ: {contact_person or 'Chưa có'}\n"
                f"📞 SĐT: {phone or 'Chưa có'}\n"
                f"📧 Email: {email or 'Chưa có'}\n"
                f"💼 Nhu cầu: {need or 'Chưa rõ'}\n"
                f"{nav_emoji} Tiềm năng: *{nav or 'Chưa đánh giá'}*\n"
                f"📣 Nguồn KH: {source or 'Chưa có'}\n"
                f"{status_emoji} Trạng thái: *{status}*\n"
                f"📅 Hẹn tiếp: {next_meeting or 'Chưa có'}\n"
                f"📝 Ghi chú: {note or 'Không có'}"
            )
        except Exception as e:
            return f"❌ Lỗi thêm KH: {str(e)}"

    async def get_customers(self, status: str = None, search: str = None,
                            nav: str = None, source: str = None) -> str:
        if not self.sheet:
            return "❌ Chưa cấu hình Google Sheets"
        try:
            records = self._get_all_customers()
            if not records:
                return "👥 *Chưa có khách hàng nào*\n\nNhắn để thêm KH mới: _\"Thêm KH: Tên, SĐT, nhu cầu\"_"

            # Lọc
            if status:
                records = [r for r in records if r.get("Trạng thái", "").lower() == status.lower()]
            if nav:
                records = [r for r in records if r.get("Tiềm năng (NAV)", "").lower() == nav.lower()]
            if source:
                records = [r for r in records if r.get("Nguồn KH", "").lower() == source.lower()]
            if search:
                s = search.lower()
                records = [r for r in records if
                           s in str(r.get("Tên KH / Công ty", "")).lower() or
                           s in str(r.get("Người liên hệ", "")).lower()]

            if not records:
                return "🔍 Không tìm thấy khách hàng phù hợp"

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
                    nav_val = r.get("Tiềm năng (NAV)", "")
                    source_val = r.get("Nguồn KH", "")
                    next_m = r.get("Ngày hẹn tiếp theo", "")

                    nav_str = f" {NAV_EMOJI.get(nav_val, '')} {nav_val}" if nav_val else ""
                    phone_str = f" | 📞 {phone}" if phone else ""
                    source_str = f" | 📣 {source_val}" if source_val else ""
                    next_str = f"\n    📅 Hẹn tiếp: {next_m}" if next_m else ""

                    lines.append(f"  • *{name}*{nav_str}{phone_str}{source_str}{next_str}")

            return "\n".join(lines)

        except Exception as e:
            return f"❌ Lỗi lấy danh sách KH: {str(e)}"

    async def update_customer(self, name: str, status: str = None, note: str = None,
                               nav: str = None, next_meeting: str = None) -> str:
        if not self.sheet:
            return "❌ Chưa cấu hình Google Sheets"
        try:
            records = self.sheet.get_all_records()
            name_lower = name.lower()

            row_idx = None
            for i, r in enumerate(records):
                if name_lower in str(r.get("Tên KH / Công ty", "")).lower():
                    row_idx = i + 2
                    break

            if row_idx is None:
                return f"❌ Không tìm thấy khách hàng tên *{name}*"

            now = datetime.now().strftime("%d/%m/%Y %H:%M")
            updates = []

            if status:
                self.sheet.update_cell(row_idx, COL["status"], status)
                updates.append(f"Trạng thái → *{status}*")
            if nav:
                self.sheet.update_cell(row_idx, COL["nav"], nav)
                updates.append(f"Tiềm năng → *{nav}*")
            if next_meeting:
                self.sheet.update_cell(row_idx, COL["next_meeting"], next_meeting)
                updates.append(f"Hẹn tiếp → *{next_meeting}*")
            if note:
                old_note = records[row_idx - 2].get("Ghi chú", "")
                new_note = f"{old_note}\n[{now}] {note}".strip()
                self.sheet.update_cell(row_idx, COL["note"], new_note)
                updates.append(f"Ghi chú: _{note}_")

            self.sheet.update_cell(row_idx, COL["updated"], now)

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

            # Thống kê trạng thái
            stats = {}
            nav_stats = {}
            source_stats = {}

            for r in records:
                st = r.get("Trạng thái", "Khác")
                stats[st] = stats.get(st, 0) + 1
                nav = r.get("Tiềm năng (NAV)", "Chưa đánh giá")
                nav_stats[nav] = nav_stats.get(nav, 0) + 1
                src = r.get("Nguồn KH", "Khác")
                source_stats[src] = source_stats.get(src, 0) + 1

            lines = [f"📊 *Báo cáo khách hàng:*\n"]
            lines.append(f"👥 Tổng số KH: *{total}*\n")

            # Theo trạng thái
            lines.append("*Theo trạng thái:*")
            for st in STATUS_LIST:
                count = stats.get(st, 0)
                emoji = STATUS_EMOJI.get(st, "📋")
                pct = round(count / total * 100) if total > 0 else 0
                bar = "▓" * (pct // 10) + "░" * (10 - pct // 10)
                lines.append(f"{emoji} {st}: *{count}* ({pct}%)\n  {bar}")

            # Theo tiềm năng
            lines.append("\n*Theo tiềm năng (NAV):*")
            for nav in NAV_LIST:
                count = nav_stats.get(nav, 0)
                emoji = NAV_EMOJI.get(nav, "")
                lines.append(f"{emoji} {nav}: *{count}* KH")

            # Theo nguồn
            lines.append("\n*Theo nguồn KH:*")
            for src, count in sorted(source_stats.items(), key=lambda x: -x[1]):
                lines.append(f"📣 {src}: *{count}* KH")

            # Tỉ lệ chuyển đổi
            chot = stats.get("Đã chốt", 0)
            conversion = round(chot / total * 100) if total > 0 else 0
            lines.append(f"\n🎯 Tỉ lệ chuyển đổi: *{conversion}%* ({chot}/{total})")

            return "\n".join(lines)

        except Exception as e:
            return f"❌ Lỗi tạo báo cáo: {str(e)}"
