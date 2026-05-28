"""
===========================================
  GOOGLE CALENDAR SERVICE - calendar_service.py
===========================================
"""

import os
from datetime import datetime, timedelta
from google.oauth2 import service_account
from googleapiclient.discovery import build

CALENDAR_ID = os.getenv("GOOGLE_CALENDAR_ID", "primary")
CREDENTIALS_FILE = os.getenv("GOOGLE_CREDENTIALS_FILE", "credentials.json")
SCOPES = ["https://www.googleapis.com/auth/calendar"]


class CalendarService:
    def __init__(self):
        try:
            creds = service_account.Credentials.from_service_account_file(
                CREDENTIALS_FILE, scopes=SCOPES
            )
            self.service = build("calendar", "v3", credentials=creds)
        except Exception as e:
            print(f"⚠️ Không thể kết nối Google Calendar: {e}")
            self.service = None

    async def preview_event(self, title: str, date: str, start_time: str,
                            end_time: str = None, description: str = "",
                            location: str = "") -> dict:
        """Trả về thông tin preview để confirm trước khi tạo"""
        if not end_time:
            start_dt = datetime.strptime(f"{date} {start_time}", "%Y-%m-%d %H:%M")
            end_dt = start_dt + timedelta(hours=1)
            end_time = end_dt.strftime("%H:%M")

        date_fmt = datetime.strptime(date, "%Y-%m-%d").strftime("%d/%m/%Y")
        weekday = ["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "Chủ nhật"][
            datetime.strptime(date, "%Y-%m-%d").weekday()
        ]

        return {
            "title": title,
            "date": date,
            "start_time": start_time,
            "end_time": end_time,
            "description": description,
            "location": location,
            "preview_text": (
                f"📋 *Xác nhận tạo lịch hẹn:*\n\n"
                f"📌 *{title}*\n"
                f"📅 {weekday}, {date_fmt}\n"
                f"⏰ {start_time} – {end_time}\n"
                f"📍 {location or 'Chưa có địa điểm'}\n"
                f"📝 {description or 'Không có ghi chú'}\n\n"
                f"✅ Nhắn *'xác nhận'* hoặc *'ok'* để tạo\n"
                f"❌ Nhắn *'hủy'* hoặc *'không'* để bỏ qua"
            )
        }

    async def create_event(self, title: str, date: str, start_time: str,
                           end_time: str = None, description: str = "",
                           location: str = "") -> str:
        if not self.service:
            return "❌ Chưa cấu hình Google Calendar"
        try:
            if not end_time:
                start_dt = datetime.strptime(f"{date} {start_time}", "%Y-%m-%d %H:%M")
                end_dt = start_dt + timedelta(hours=1)
                end_time = end_dt.strftime("%H:%M")

            event = {
                "summary": title,
                "location": location,
                "description": description,
                "start": {
                    "dateTime": f"{date}T{start_time}:00",
                    "timeZone": "Asia/Ho_Chi_Minh",
                },
                "end": {
                    "dateTime": f"{date}T{end_time}:00",
                    "timeZone": "Asia/Ho_Chi_Minh",
                },
                "reminders": {
                    "useDefault": False,
                    "overrides": [{"method": "popup", "minutes": 30}],
                },
            }

            created = self.service.events().insert(
                calendarId=CALENDAR_ID, body=event
            ).execute()

            link = created.get("htmlLink", "")
            date_fmt = datetime.strptime(date, "%Y-%m-%d").strftime("%d/%m/%Y")
            weekday = ["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "Chủ nhật"][
                datetime.strptime(date, "%Y-%m-%d").weekday()
            ]
            return (
                f"✅ *Đã tạo lịch hẹn!*\n\n"
                f"📌 *{title}*\n"
                f"📅 {weekday}, {date_fmt}\n"
                f"⏰ {start_time} – {end_time}\n"
                f"📍 {location or 'Chưa có địa điểm'}\n"
                f"📝 {description or ''}\n"
                f"🔗 [Xem trên Google Calendar]({link})"
            )
        except Exception as e:
            return f"❌ Lỗi tạo lịch: {str(e)}"

    async def find_events(self, keyword: str = "", date: str = "") -> list:
        """Tìm kiếm sự kiện theo từ khóa hoặc ngày"""
        if not self.service:
            return []
        try:
            if date:
                time_min = f"{date}T00:00:00+07:00"
                time_max = f"{date}T23:59:59+07:00"
            else:
                today = datetime.now()
                time_min = today.strftime("%Y-%m-%dT00:00:00+07:00")
                end = (today + timedelta(days=30)).strftime("%Y-%m-%d")
                time_max = f"{end}T23:59:59+07:00"

            result = self.service.events().list(
                calendarId=CALENDAR_ID,
                timeMin=time_min,
                timeMax=time_max,
                singleEvents=True,
                orderBy="startTime",
                maxResults=20,
                q=keyword if keyword else None,
            ).execute()

            return result.get("items", [])
        except Exception as e:
            print(f"Lỗi tìm lịch: {e}")
            return []

    async def delete_event(self, event_id: str, event_title: str = "") -> str:
        """Xóa sự kiện theo ID"""
        if not self.service:
            return "❌ Chưa cấu hình Google Calendar"
        try:
            self.service.events().delete(
                calendarId=CALENDAR_ID,
                eventId=event_id
            ).execute()
            return f"🗑️ *Đã hủy lịch thành công!*\n\n📌 ~~{event_title}~~"
        except Exception as e:
            return f"❌ Lỗi hủy lịch: {str(e)}"

    async def find_and_confirm_delete(self, keyword: str, date: str = "") -> dict:
        """Tìm lịch cần xóa và trả về thông tin để confirm"""
        events = await self.find_events(keyword=keyword, date=date)

        if not events:
            return {
                "found": False,
                "text": f"🔍 Không tìm thấy lịch nào có từ khóa *'{keyword}'*"
            }

        if len(events) == 1:
            ev = events[0]
            start = ev["start"].get("dateTime", ev["start"].get("date"))
            if "T" in start:
                dt = datetime.fromisoformat(start)
                date_str = dt.strftime("%d/%m/%Y")
                time_str = dt.strftime("%H:%M")
                weekday = ["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "Chủ nhật"][dt.weekday()]
            else:
                dt = datetime.strptime(start, "%Y-%m-%d")
                date_str = dt.strftime("%d/%m/%Y")
                time_str = "Cả ngày"
                weekday = ["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "Chủ nhật"][dt.weekday()]

            title = ev.get("summary", "Không có tiêu đề")
            return {
                "found": True,
                "single": True,
                "event_id": ev["id"],
                "event_title": title,
                "text": (
                    f"🗑️ *Xác nhận hủy lịch:*\n\n"
                    f"📌 *{title}*\n"
                    f"📅 {weekday}, {date_str} | ⏰ {time_str}\n\n"
                    f"✅ Nhắn *'xác nhận'* hoặc *'ok'* để hủy\n"
                    f"❌ Nhắn *'không'* để giữ lại"
                )
            }
        else:
            # Nhiều kết quả → liệt kê để chọn
            lines = [f"🔍 Tìm thấy *{len(events)} lịch* khớp, bạn muốn hủy cái nào?\n"]
            for i, ev in enumerate(events[:5], 1):
                start = ev["start"].get("dateTime", ev["start"].get("date"))
                if "T" in start:
                    dt = datetime.fromisoformat(start)
                    info = f"{dt.strftime('%d/%m/%Y')} {dt.strftime('%H:%M')}"
                else:
                    info = datetime.strptime(start, "%Y-%m-%d").strftime("%d/%m/%Y")
                title = ev.get("summary", "?")
                lines.append(f"  *{i}.* {title} — {info}")
            lines.append("\nNhắn số thứ tự (vd: *'hủy lịch 2'*) để chọn")
            return {
                "found": True,
                "single": False,
                "events": events[:5],
                "text": "\n".join(lines)
            }

    async def get_events(self, start_date: str, end_date: str) -> str:
        if not self.service:
            return "❌ Chưa cấu hình Google Calendar"
        try:
            time_min = f"{start_date}T00:00:00+07:00"
            time_max = f"{end_date}T23:59:59+07:00"

            result = self.service.events().list(
                calendarId=CALENDAR_ID,
                timeMin=time_min,
                timeMax=time_max,
                singleEvents=True,
                orderBy="startTime",
                maxResults=50,
            ).execute()

            events = result.get("items", [])
            if not events:
                start_fmt = datetime.strptime(start_date, "%Y-%m-%d").strftime("%d/%m/%Y")
                end_fmt = datetime.strptime(end_date, "%Y-%m-%d").strftime("%d/%m/%Y")
                period = start_fmt if start_date == end_date else f"{start_fmt} – {end_fmt}"
                return f"📅 *Không có lịch hẹn nào* trong {period}"

            lines = [f"📅 *Lịch hẹn ({len(events)} cuộc):*\n"]
            current_date = ""

            for ev in events:
                start = ev["start"].get("dateTime", ev["start"].get("date"))
                if "T" in start:
                    dt = datetime.fromisoformat(start)
                    date_str = dt.strftime("%d/%m/%Y")
                    time_str = dt.strftime("%H:%M")
                    weekday = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"][dt.weekday()]
                else:
                    dt = datetime.strptime(start, "%Y-%m-%d")
                    date_str = dt.strftime("%d/%m/%Y")
                    time_str = "Cả ngày"
                    weekday = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"][dt.weekday()]

                if date_str != current_date:
                    lines.append(f"\n📆 *{weekday} {date_str}*")
                    current_date = date_str

                summary = ev.get("summary", "Không có tiêu đề")
                location = ev.get("location", "")
                loc_str = f" 📍 {location}" if location else ""
                lines.append(f"  • {time_str} – *{summary}*{loc_str}")

            return "\n".join(lines)

        except Exception as e:
            return f"❌ Lỗi lấy lịch: {str(e)}"

    async def get_report(self, period: str = "week") -> str:
        today = datetime.now()
        if period == "week":
            start = today.strftime("%Y-%m-%d")
            end = (today + timedelta(days=6)).strftime("%Y-%m-%d")
            label = "tuần này"
        else:
            start = today.replace(day=1).strftime("%Y-%m-%d")
            import calendar
            last_day = calendar.monthrange(today.year, today.month)[1]
            end = today.replace(day=last_day).strftime("%Y-%m-%d")
            label = f"tháng {today.month}/{today.year}"

        events_text = await self.get_events(start, end)
        return f"📊 *Báo cáo lịch {label}:*\n\n{events_text}"
