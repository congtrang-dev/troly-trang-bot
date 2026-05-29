"""
===========================================
  TODOIST SERVICE - todoist_service.py
  Quản lý task, ghi chú, dự án qua Todoist API
===========================================
"""

import os
import requests
from datetime import datetime

TODOIST_TOKEN = os.getenv("TODOIST_API_TOKEN")
BASE_URL = "https://api.todoist.com/rest/v2"  # v2 is correct

PRIORITY_MAP = {
    "p1": "🔴 Khẩn cấp", "p2": "🟠 Cao", "p3": "🟡 Trung bình", "p4": "🟢 Thường"
}
PRIORITY_EMOJI = {"p1": "🔴", "p2": "🟠", "p3": "🟡", "p4": "🟢"}


class TodoistService:
    def __init__(self):
        if not TODOIST_TOKEN:
            print("⚠️ Chưa cấu hình TODOIST_API_TOKEN")
        self.headers = {
            "Authorization": f"Bearer {TODOIST_TOKEN}",
            "Content-Type": "application/json",
        }

    def _get(self, endpoint: str, params: dict = None) -> list | dict | None:
        try:
            r = requests.get(f"{BASE_URL}/{endpoint}", headers=self.headers, params=params, timeout=10)
            print(f"Todoist GET {endpoint}: status={r.status_code}")
            r.raise_for_status()
            return r.json()
        except Exception as e:
            print(f"Todoist GET error [{endpoint}]: {e}")
            return None

    def _post(self, endpoint: str, data: dict) -> dict | None:
        try:
            r = requests.post(f"{BASE_URL}/{endpoint}", headers=self.headers, json=data, timeout=10)
            print(f"Todoist POST {endpoint}: status={r.status_code}, body={r.text[:200]}")
            r.raise_for_status()
            return r.json()
        except Exception as e:
            print(f"Todoist POST error [{endpoint}]: {e}")
            return None

    def _close(self, task_id: str) -> bool:
        try:
            r = requests.post(f"{BASE_URL}/tasks/{task_id}/close", headers=self.headers, timeout=10)
            return r.status_code in [200, 204]
        except:
            return False

    # ─── 1. XEM TASK ─────────────────────────────────────────────
    async def get_tasks_today(self) -> str:
        tasks = self._get("tasks", {"filter": "today | overdue"})
        if tasks is None:
            return "❌ Không thể kết nối Todoist"
        if not tasks:
            return "✅ *Không có task nào hôm nay!* Bạn rảnh rỗi 🎉"

        lines = [f"📋 *Task hôm nay ({len(tasks)} task):*\n"]
        overdue, today = [], []

        for t in tasks:
            due = t.get("due", {})
            due_str = due.get("date", "") if due else ""
            today_str = datetime.now().strftime("%Y-%m-%d")
            if due_str and due_str < today_str:
                overdue.append(t)
            else:
                today.append(t)

        if overdue:
            lines.append("⚠️ *Quá hạn:*")
            for t in overdue:
                p = PRIORITY_EMOJI.get(f"p{t.get('priority', 4)}", "🟢")
                lines.append(f"  • {p} ~~{t['content']}~~")

        if today:
            lines.append("\n📅 *Hôm nay:*")
            for t in today:
                p = PRIORITY_EMOJI.get(f"p{t.get('priority', 4)}", "🟢")
                due_time = ""
                if t.get("due", {}) and t["due"].get("datetime"):
                    dt = datetime.fromisoformat(t["due"]["datetime"].replace("Z", "+00:00"))
                    due_time = f" ⏰ {dt.strftime('%H:%M')}"
                lines.append(f"  • {p} *{t['content']}*{due_time}")

        return "\n".join(lines)

    async def get_tasks_week(self) -> str:
        tasks = self._get("tasks", {"filter": "7 days"})
        if tasks is None:
            return "❌ Không thể kết nối Todoist"
        if not tasks:
            return "✅ *Không có task nào trong tuần!*"

        lines = [f"📋 *Task tuần này ({len(tasks)} task):*\n"]
        grouped = {}
        for t in tasks:
            due = t.get("due", {})
            due_date = due.get("date", "Không có hạn") if due else "Không có hạn"
            grouped.setdefault(due_date, []).append(t)

        for date in sorted(grouped.keys()):
            if date == "Không có hạn":
                label = "📌 Không có hạn"
            else:
                try:
                    dt = datetime.strptime(date, "%Y-%m-%d")
                    weekday = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"][dt.weekday()]
                    label = f"📅 {weekday} {dt.strftime('%d/%m')}"
                except:
                    label = f"📅 {date}"

            lines.append(f"\n{label}:")
            for t in grouped[date]:
                p = PRIORITY_EMOJI.get(f"p{t.get('priority', 4)}", "🟢")
                lines.append(f"  • {p} {t['content']}")

        return "\n".join(lines)

    # ─── 2. TẠO TASK ─────────────────────────────────────────────
    async def add_task(self, content: str, description: str = "",
                       due: str = "", priority: str = "p4",
                       project_name: str = "", labels: list = None) -> str:
        priority_num = int(priority[1]) if priority and len(priority) > 1 else 4
        data = {"content": content, "priority": priority_num}
        if description:
            data["description"] = description
        if due:
            data["due_string"] = due
        if labels:
            data["labels"] = labels

        # Tìm project nếu có
        if project_name:
            projects = self._get("projects")
            if projects:
                for p in projects:
                    if project_name.lower() in p["name"].lower():
                        data["project_id"] = p["id"]
                        break

        task = self._post("tasks", data)
        if not task:
            return "❌ Không thể tạo task"

        p_emoji = PRIORITY_EMOJI.get(priority, "🟢")
        due_str = f"\n⏰ Hạn: {due}" if due else ""
        desc_str = f"\n📝 {description}" if description else ""
        return (
            f"✅ *Đã tạo task!*\n\n"
            f"{p_emoji} *{content}*"
            f"{due_str}"
            f"{desc_str}"
        )

    # ─── 3. HOÀN THÀNH TASK ──────────────────────────────────────
    async def complete_task(self, keyword: str) -> str:
        tasks = self._get("tasks", {"filter": "today | 7 days"})
        if not tasks:
            tasks = self._get("tasks")

        if not tasks:
            return "❌ Không thể lấy danh sách task"

        keyword_lower = keyword.lower()
        matched = [t for t in tasks if keyword_lower in t["content"].lower()]

        if not matched:
            return f"🔍 Không tìm thấy task chứa từ khóa *'{keyword}'*"

        if len(matched) == 1:
            task = matched[0]
            success = self._close(task["id"])
            if success:
                return f"✅ *Đã hoàn thành task:*\n\n~~{task['content']}~~"
            return "❌ Không thể hoàn thành task"

        lines = [f"🔍 Tìm thấy *{len(matched)} task* khớp:\n"]
        for i, t in enumerate(matched[:5], 1):
            p = PRIORITY_EMOJI.get(f"p{t.get('priority', 4)}", "🟢")
            lines.append(f"  *{i}.* {p} {t['content']}")
        lines.append("\nNhắn cụ thể hơn để hoàn thành đúng task nhé!")
        return "\n".join(lines)

    # ─── 4. GHI CHÚ THEO TASK ────────────────────────────────────
    async def add_comment(self, task_keyword: str, comment: str) -> str:
        tasks = self._get("tasks")
        if not tasks:
            return "❌ Không thể lấy danh sách task"

        keyword_lower = task_keyword.lower()
        matched = [t for t in tasks if keyword_lower in t["content"].lower()]

        if not matched:
            return f"🔍 Không tìm thấy task *'{task_keyword}'*"

        task = matched[0]
        now = datetime.now().strftime("%d/%m/%Y %H:%M")
        result = self._post("comments", {
            "task_id": task["id"],
            "content": f"[{now}] {comment}"
        })

        if result:
            return (
                f"💬 *Đã thêm ghi chú!*\n\n"
                f"📌 Task: *{task['content']}*\n"
                f"📝 Ghi chú: _{comment}_"
            )
        return "❌ Không thể thêm ghi chú"

    async def get_comments(self, task_keyword: str) -> str:
        tasks = self._get("tasks")
        if not tasks:
            return "❌ Không thể lấy danh sách task"

        keyword_lower = task_keyword.lower()
        matched = [t for t in tasks if keyword_lower in t["content"].lower()]

        if not matched:
            return f"🔍 Không tìm thấy task *'{task_keyword}'*"

        task = matched[0]
        comments = self._get("comments", {"task_id": task["id"]})

        if not comments:
            return f"📌 Task *{task['content']}*\n\n💬 Chưa có ghi chú nào"

        lines = [f"📌 *{task['content']}*\n\n💬 *Ghi chú ({len(comments)}):*"]
        for c in comments:
            lines.append(f"\n  • {c['content']}")

        return "\n".join(lines)

    # ─── 5. TẠO TASK TỰ ĐỘNG TỪ KHÁCH HÀNG ──────────────────────
    async def create_customer_followup(self, customer_name: str,
                                        phone: str = "", need: str = "",
                                        due: str = "trong 3 ngày") -> str:
        content = f"Follow up: {customer_name}"
        description = f"SĐT: {phone}\nNhu cầu: {need}" if phone or need else ""

        data = {
            "content": content,
            "description": description,
            "due_string": due,
            "priority": 2,  # Ưu tiên cao
            "labels": ["khach-hang"],
        }
        task = self._post("tasks", data)
        if task:
            return f"📌 *Đã tạo task follow up:* {customer_name}"
        return ""

    # ─── 6. BÁO CÁO NĂNG SUẤT ───────────────────────────────────
    async def get_productivity_report(self) -> str:
        # Task còn lại hôm nay + quá hạn
        open_tasks = self._get("tasks", {"filter": "today | overdue"})
        all_tasks = self._get("tasks")

        open_count = len(open_tasks) if open_tasks else 0
        total = len(all_tasks) if all_tasks else 0

        lines = ["📊 *Báo cáo năng suất hôm nay:*\n"]
        lines.append(f"📋 Task cần làm hôm nay: *{open_count} task*")
        lines.append(f"📁 Tổng task đang mở: *{total} task*")

        if open_tasks:
            # Phân loại theo priority
            urgent = [t for t in open_tasks if t.get("priority") == 1]
            high   = [t for t in open_tasks if t.get("priority") == 2]

            if urgent:
                lines.append(f"\n🔴 *Khẩn cấp ({len(urgent)}):*")
                for t in urgent[:3]:
                    lines.append(f"  • {t['content']}")
            if high:
                lines.append(f"\n🟠 *Ưu tiên cao ({len(high)}):*")
                for t in high[:3]:
                    lines.append(f"  • {t['content']}")

            lines.append(f"\n⚡ *Cần làm ngay:*")
            for t in open_tasks[:5]:
                p = PRIORITY_EMOJI.get(f"p{5 - t.get('priority', 4)}", "🟢")
                lines.append(f"  • {p} {t['content']}")

        return "\n".join(lines)

    # ─── 7. XEM DỰ ÁN ───────────────────────────────────────────
    async def get_projects(self) -> str:
        projects = self._get("projects")
        if not projects:
            return "❌ Không thể lấy danh sách dự án"

        lines = [f"📁 *Danh sách dự án ({len(projects)}):*\n"]
        for p in projects:
            lines.append(f"  • 📂 *{p['name']}*")
        return "\n".join(lines)
