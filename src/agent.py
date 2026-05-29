"""
===========================================
  AI AGENT CORE - agent.py
  Xử lý ngôn ngữ tự nhiên & điều phối tools
===========================================
"""

import os
import anthropic
from datetime import datetime, timedelta
from calendar_service import CalendarService
from sheets_service import SheetsService
from todoist_service import TodoistService

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

# ─── Định nghĩa Tools cho Claude ─────────────────────────────────
TOOLS = [
    {
        "name": "preview_calendar_event",
        "description": "Xem trước thông tin lịch hẹn để người dùng xác nhận TRƯỚC KHI tạo. LUÔN gọi tool này thay vì create_calendar_event khi người dùng muốn tạo lịch mới.",
        "input_schema": {
            "type": "object",
            "properties": {
                "title":       {"type": "string", "description": "Tiêu đề cuộc hẹn"},
                "date":        {"type": "string", "description": "Ngày (YYYY-MM-DD)"},
                "start_time":  {"type": "string", "description": "Giờ bắt đầu (HH:MM, 24h)"},
                "end_time":    {"type": "string", "description": "Giờ kết thúc (HH:MM, 24h)"},
                "description": {"type": "string", "description": "Ghi chú thêm"},
                "location":    {"type": "string", "description": "Địa điểm"},
            },
            "required": ["title", "date", "start_time"]
        }
    },
    {
        "name": "create_calendar_event",
        "description": "Tạo lịch hẹn lên Google Calendar. Chỉ gọi tool này SAU KHI người dùng đã xác nhận (ok/xác nhận/đồng ý).",
        "input_schema": {
            "type": "object",
            "properties": {
                "title":       {"type": "string", "description": "Tiêu đề cuộc hẹn"},
                "date":        {"type": "string", "description": "Ngày (YYYY-MM-DD)"},
                "start_time":  {"type": "string", "description": "Giờ bắt đầu (HH:MM, 24h)"},
                "end_time":    {"type": "string", "description": "Giờ kết thúc (HH:MM, 24h)"},
                "description": {"type": "string", "description": "Ghi chú thêm"},
                "location":    {"type": "string", "description": "Địa điểm"},
            },
            "required": ["title", "date", "start_time"]
        }
    },
    {
        "name": "get_calendar_events",
        "description": "Lấy danh sách lịch hẹn theo khoảng thời gian",
        "input_schema": {
            "type": "object",
            "properties": {
                "start_date": {"type": "string", "description": "Ngày bắt đầu (YYYY-MM-DD)"},
                "end_date":   {"type": "string", "description": "Ngày kết thúc (YYYY-MM-DD)"},
            },
            "required": ["start_date", "end_date"]
        }
    },
    {
        "name": "find_and_delete_event",
        "description": "Tìm và xóa/hủy lịch hẹn. Dùng khi người dùng muốn hủy hoặc xóa một sự kiện.",
        "input_schema": {
            "type": "object",
            "properties": {
                "keyword": {"type": "string", "description": "Từ khóa tên sự kiện cần tìm"},
                "date":    {"type": "string", "description": "Ngày sự kiện (YYYY-MM-DD), để trống nếu không biết"},
            },
            "required": ["keyword"]
        }
    },
    {
        "name": "confirm_delete_event",
        "description": "Xác nhận xóa lịch sau khi người dùng đồng ý. Cần event_id lấy từ find_and_delete_event.",
        "input_schema": {
            "type": "object",
            "properties": {
                "event_id":    {"type": "string", "description": "ID sự kiện cần xóa"},
                "event_title": {"type": "string", "description": "Tên sự kiện"},
            },
            "required": ["event_id"]
        }
    },
    {
        "name": "add_customer",
        "description": "Thêm khách hàng tiềm năng vào Google Sheets",
        "input_schema": {
            "type": "object",
            "properties": {
                "name":           {"type": "string", "description": "Tên khách hàng / công ty"},
                "phone":          {"type": "string", "description": "Số điện thoại"},
                "email":          {"type": "string", "description": "Email"},
                "need":           {"type": "string", "description": "Nhu cầu / sản phẩm quan tâm"},
                "status":         {"type": "string", "description": "Trạng thái: Mới | Đang tư vấn | Đã chốt | Không tiềm năng"},
                "note":           {"type": "string", "description": "Ghi chú thêm"},
                "contact_person": {"type": "string", "description": "Người liên hệ tại công ty"},
                "nav":            {"type": "string", "description": "Mức độ tiềm năng (NAV): Cao | Trung bình | Thấp"},
                "source":         {"type": "string", "description": "Nguồn KH: Facebook | Zalo | Giới thiệu | Website | Gọi trực tiếp | Khác"},
                "next_meeting":   {"type": "string", "description": "Ngày hẹn gặp tiếp theo"},
            },
            "required": ["name", "status"]
        }
    },
    {
        "name": "get_customers",
        "description": "Lấy danh sách khách hàng, lọc theo trạng thái, tiềm năng, nguồn hoặc tìm theo tên",
        "input_schema": {
            "type": "object",
            "properties": {
                "status":  {"type": "string", "description": "Lọc theo trạng thái"},
                "search":  {"type": "string", "description": "Tìm kiếm theo tên"},
                "nav":     {"type": "string", "description": "Lọc theo tiềm năng: Cao | Trung bình | Thấp"},
                "source":  {"type": "string", "description": "Lọc theo nguồn KH"},
            }
        }
    },
    {
        "name": "update_customer",
        "description": "Cập nhật thông tin hoặc trạng thái khách hàng",
        "input_schema": {
            "type": "object",
            "properties": {
                "name":         {"type": "string", "description": "Tên KH cần cập nhật"},
                "status":       {"type": "string", "description": "Trạng thái mới"},
                "note":         {"type": "string", "description": "Ghi chú cập nhật"},
                "nav":          {"type": "string", "description": "Mức tiềm năng mới"},
                "next_meeting": {"type": "string", "description": "Ngày hẹn gặp tiếp theo"},
            },
            "required": ["name"]
        }
    },
    {
        "name": "generate_report",
        "description": "Tạo báo cáo tổng hợp lịch làm việc và khách hàng",
        "input_schema": {
            "type": "object",
            "properties": {
                "period": {"type": "string", "description": "Kỳ báo cáo: week | month"},
            },
            "required": ["period"]
        }
    }    ,
    # ─── TODOIST TOOLS ───────────────────────────────────────────
    {
        "name": "todoist_get_tasks_today",
        "description": "Xem danh sách task hôm nay và task quá hạn trong Todoist",
        "input_schema": {"type": "object", "properties": {}}
    },
    {
        "name": "todoist_get_tasks_week",
        "description": "Xem danh sách task trong tuần này trong Todoist",
        "input_schema": {"type": "object", "properties": {}}
    },
    {
        "name": "todoist_add_task",
        "description": "Tạo task mới trong Todoist",
        "input_schema": {
            "type": "object",
            "properties": {
                "content":      {"type": "string", "description": "Tên task"},
                "description":  {"type": "string", "description": "Mô tả chi tiết task"},
                "due":          {"type": "string", "description": "Hạn chót (vd: hôm nay, ngày mai, thứ 6)"},
                "priority":     {"type": "string", "description": "Độ ưu tiên: p1 (khẩn) | p2 (cao) | p3 (trung bình) | p4 (thường)"},
                "project_name": {"type": "string", "description": "Tên project trong Todoist"},
                "labels":       {"type": "array", "items": {"type": "string"}, "description": "Nhãn gắn vào task"},
            },
            "required": ["content"]
        }
    },
    {
        "name": "todoist_complete_task",
        "description": "Đánh dấu hoàn thành một task trong Todoist",
        "input_schema": {
            "type": "object",
            "properties": {
                "keyword": {"type": "string", "description": "Từ khóa tên task cần hoàn thành"},
            },
            "required": ["keyword"]
        }
    },
    {
        "name": "todoist_add_comment",
        "description": "Thêm ghi chú/comment vào một task trong Todoist",
        "input_schema": {
            "type": "object",
            "properties": {
                "task_keyword": {"type": "string", "description": "Từ khóa tên task cần ghi chú"},
                "comment":      {"type": "string", "description": "Nội dung ghi chú"},
            },
            "required": ["task_keyword", "comment"]
        }
    },
    {
        "name": "todoist_get_comments",
        "description": "Xem tất cả ghi chú của một task trong Todoist",
        "input_schema": {
            "type": "object",
            "properties": {
                "task_keyword": {"type": "string", "description": "Từ khóa tên task cần xem ghi chú"},
            },
            "required": ["task_keyword"]
        }
    },
    {
        "name": "todoist_productivity_report",
        "description": "Xem báo cáo năng suất: task đã hoàn thành và còn lại hôm nay",
        "input_schema": {"type": "object", "properties": {}}
    },
    {
        "name": "todoist_get_projects",
        "description": "Xem danh sách tất cả project trong Todoist",
        "input_schema": {"type": "object", "properties": {}}
    },
]

# ─── System Prompt ────────────────────────────────────────────────
SYSTEM_PROMPT = """Bạn là trợ lý AI thông minh giúp quản lý công việc và khách hàng qua Telegram.

NGÀY GIỜ HIỆN TẠI: {current_datetime}
HÔM NAY: {today} | NGÀY MAI: {tomorrow}

NHIỆM VỤ:
- Hiểu yêu cầu bằng tiếng Việt tự nhiên
- Gọi đúng tool để thực thi
- Phản hồi ngắn gọn, rõ ràng bằng tiếng Việt
- Dùng emoji phù hợp để dễ đọc

QUY TẮC QUAN TRỌNG:
1. TẠO LỊCH: LUÔN gọi preview_calendar_event TRƯỚC, đợi người dùng xác nhận mới gọi create_calendar_event
2. XÓA LỊCH: Gọi find_and_delete_event để tìm, hiển thị kết quả cho người dùng xác nhận, rồi mới gọi confirm_delete_event
3. Nếu người dùng nói "ok", "xác nhận", "đúng rồi" sau khi preview → thực thi luôn
4. Nếu người dùng nói "hủy", "không", "thôi" → bỏ qua, không thực thi
5. Trạng thái KH: Mới | Đang tư vấn | Đã chốt | Không tiềm năng
6. Tiềm năng (NAV): Cao | Trung bình | Thấp
7. Giờ kết thúc mặc định = giờ bắt đầu + 1 tiếng

FORMAT PHẢN HỒI:
- Dùng Markdown (bold, italic)
- Emoji ở đầu mỗi mục
- Ngắn gọn, súc tích
"""


class AIAgent:
    def __init__(self):
        self.client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        self.calendar = CalendarService()
        self.sheets = SheetsService()
        self.todoist = TodoistService()
        self.conversation_history = {}
        # Lưu pending action chờ confirm
        self.pending_actions = {}

    def _get_system_prompt(self):
        now = datetime.now()
        tomorrow = now + timedelta(days=1)
        return SYSTEM_PROMPT.format(
            current_datetime=now.strftime("%d/%m/%Y %H:%M"),
            today=now.strftime("%Y-%m-%d"),
            tomorrow=tomorrow.strftime("%Y-%m-%d"),
        )

    async def _execute_tool(self, tool_name: str, tool_input: dict, user_id: str = "default") -> str:
        try:
            if tool_name == "preview_calendar_event":
                preview = await self.calendar.preview_event(**tool_input)
                # Lưu pending action để dùng khi confirm
                self.pending_actions[user_id] = {
                    "type": "create_event",
                    "data": tool_input
                }
                return preview["preview_text"]

            elif tool_name == "create_calendar_event":
                return await self.calendar.create_event(**tool_input)

            elif tool_name == "get_calendar_events":
                return await self.calendar.get_events(
                    tool_input["start_date"], tool_input["end_date"]
                )

            elif tool_name == "find_and_delete_event":
                result = await self.calendar.find_and_confirm_delete(
                    keyword=tool_input.get("keyword", ""),
                    date=tool_input.get("date", "")
                )
                if result["found"] and result.get("single"):
                    # Lưu pending delete
                    self.pending_actions[user_id] = {
                        "type": "delete_event",
                        "event_id": result["event_id"],
                        "event_title": result["event_title"],
                    }
                return result["text"]

            elif tool_name == "confirm_delete_event":
                return await self.calendar.delete_event(
                    event_id=tool_input["event_id"],
                    event_title=tool_input.get("event_title", "")
                )

            elif tool_name == "add_customer":
                return await self.sheets.add_customer(**tool_input)

            elif tool_name == "get_customers":
                return await self.sheets.get_customers(
                    status=tool_input.get("status"),
                    search=tool_input.get("search"),
                    nav=tool_input.get("nav"),
                    source=tool_input.get("source"),
                )

            elif tool_name == "update_customer":
                return await self.sheets.update_customer(**tool_input)

            elif tool_name == "generate_report":
                cal_result = await self.calendar.get_report(tool_input["period"])
                kh_result = await self.sheets.get_report()
                return f"{cal_result}\n\n{kh_result}"

            elif tool_name == "todoist_get_tasks_today":
                return await self.todoist.get_tasks_today()

            elif tool_name == "todoist_get_tasks_week":
                return await self.todoist.get_tasks_week()

            elif tool_name == "todoist_add_task":
                return await self.todoist.add_task(
                    content=tool_input["content"],
                    description=tool_input.get("description", ""),
                    due=tool_input.get("due", ""),
                    priority=tool_input.get("priority", "p4"),
                    project_name=tool_input.get("project_name", ""),
                    labels=tool_input.get("labels", []),
                )

            elif tool_name == "todoist_complete_task":
                return await self.todoist.complete_task(tool_input["keyword"])

            elif tool_name == "todoist_add_comment":
                return await self.todoist.add_comment(
                    task_keyword=tool_input["task_keyword"],
                    comment=tool_input["comment"],
                )

            elif tool_name == "todoist_get_comments":
                return await self.todoist.get_comments(tool_input["task_keyword"])

            elif tool_name == "todoist_productivity_report":
                return await self.todoist.get_productivity_report()

            elif tool_name == "todoist_get_projects":
                return await self.todoist.get_projects()


            else:
                return f"❌ Tool '{tool_name}' không tồn tại"

        except Exception as e:
            return f"❌ Lỗi khi thực thi {tool_name}: {str(e)}"

    def _is_confirm(self, msg: str) -> bool:
        confirm_words = ["ok", "oke", "okay", "xác nhận", "đúng", "đồng ý", "yes", "có", "tạo đi", "hủy đi", "xóa đi"]
        return any(w in msg.lower() for w in confirm_words)

    def _is_cancel(self, msg: str) -> bool:
        cancel_words = ["không", "hủy", "thôi", "bỏ", "cancel", "no", "dừng"]
        return any(w in msg.lower() for w in cancel_words)

    async def process_message(self, user_message: str, user_id: str = "default") -> str:
        # ── Xử lý pending action (chờ confirm) ──────────────────
        if user_id in self.pending_actions:
            pending = self.pending_actions[user_id]

            if self._is_confirm(user_message):
                del self.pending_actions[user_id]

                if pending["type"] == "create_event":
                    return await self.calendar.create_event(**pending["data"])

                elif pending["type"] == "delete_event":
                    return await self.calendar.delete_event(
                        event_id=pending["event_id"],
                        event_title=pending["event_title"]
                    )

            elif self._is_cancel(user_message):
                del self.pending_actions[user_id]
                return "↩️ Đã hủy thao tác. Có gì khác tôi có thể giúp bạn không?"

        # ── Xử lý tin nhắn thông thường qua Claude ──────────────
        if user_id not in self.conversation_history:
            self.conversation_history[user_id] = []

        # Chỉ lấy các tin nhắn text thuần (không có tool messages)
        clean_history = []
        for msg in self.conversation_history[user_id][-6:]:
            if isinstance(msg.get("content"), str):
                clean_history.append(msg)

        messages = clean_history + [{"role": "user", "content": user_message}]

        max_iterations = 5
        for _ in range(max_iterations):
            response = self.client.messages.create(
                model="claude-sonnet-4-5",
                max_tokens=2000,
                system=self._get_system_prompt(),
                tools=TOOLS,
                messages=messages,
            )

            if response.stop_reason == "tool_use":
                messages.append({"role": "assistant", "content": response.content})

                tool_results = []
                for block in response.content:
                    if block.type == "tool_use":
                        result = await self._execute_tool(block.name, block.input, user_id)
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result,
                        })

                messages.append({"role": "user", "content": tool_results})

            else:
                final_text = ""
                for block in response.content:
                    if hasattr(block, "text"):
                        final_text += block.text

                # Chỉ lưu text thuần vào history
                self.conversation_history[user_id] = clean_history + [
                    {"role": "user", "content": user_message},
                    {"role": "assistant", "content": final_text}
                ]
                return final_text or "✅ Đã thực hiện xong!"

        return "⚠️ Quá trình xử lý quá phức tạp. Vui lòng thử lại!"

    # ─── Shortcut methods ─────────────────────────────────────────
    async def get_today_events(self) -> str:
        today = datetime.now().strftime("%Y-%m-%d")
        return await self.calendar.get_events(today, today)

    async def get_week_events(self) -> str:
        today = datetime.now()
        start = today.strftime("%Y-%m-%d")
        end = (today + timedelta(days=6)).strftime("%Y-%m-%d")
        return await self.calendar.get_events(start, end)

    async def get_customers(self) -> str:
        return await self.sheets.get_customers()

    async def generate_report(self) -> str:
        cal = await self.calendar.get_report("week")
        kh = await self.sheets.get_report()
        return f"{cal}\n\n{kh}"
