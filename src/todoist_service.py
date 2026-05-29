"""
===========================================
  TODOIST SERVICE - todoist_service.py
  Todoist API v1 (2026+)
===========================================
"""

import os
import requests
from datetime import datetime

TODOIST_TOKEN = os.getenv("TODOIST_API_TOKEN")
BASE_URL = "https://api.todoist.com/api/v1"

PRIORITY_EMOJI = {1: "🔴", 2: "🟠", 3: "🟡", 4: "🟢"}
PRIORITY_NAME  = {1: "Khẩn cấp", 2: "Cao", 3: "Trung bình", 4: "Thường"}


class TodoistService:
    def __init__(self):
        if not TODOIST_TOKEN:
            print("⚠️ Chưa cấu hình TODOIST_API_TOKEN")
        self.headers = {
            "Authorization": f"Bearer {TODOIST_TOKEN}",
            "Content-Type": "application/json",
        }

    def _get(self, endpoint: str, params: dict = None):
        try:
            r = requests.get(
                f"{BASE_URL}/{endpoint}",
                headers=self.headers,
                params=params,
                timeout=15
            )
            print(f"Todoist GET {endpoint}: {r.status_code}")
            if r.status_code == 200:
                return r.json()
            print(f"Todoist GET error body: {r.text[:300]}")
            return None
        except Exception as e:
            print(f"Todoist GET exception: {e}")
            return None

    def _post(self, endpoint: str, data: dict = None):
        try:
            r = requests.post(
                f"{BASE_URL}/{endpoint}",
                headers=self.headers,
                json=data or {},
                timeout=15
            )
            print(f"Todoist POST {endpoint}: {r.status_code} | {r.text[:200]}")
            if r.status_code in [200, 201, 204]:
                try:
                    return r.json()
                except:
                    return {"ok": True}
            return None
        except Exception as e:
            print(f"Todoist POST exception: {e}")
            return None

    # ─── 1. XEM TASK HÔM NAY ─────────────────────────────────────
    async def get_tasks_today(self) -> str:
        data = self._get("tasks", {"filter": "today | overdue"})

        # v1 trả về dict có key 'results' hoặc list
        if data is None:
            return "❌ Không thể kết nối Todoist. Kiểm tra lại API Token."

        tasks = data.get("results", data) if isinstance(data, dict) else data
        if not tasks:
            return "✅ *Không có task nào hôm nay!* 🎉"

        today_str = datetime.now().strftime("%Y-%m-%d")
        overdue, today_tasks = [], []

        for t in tasks:
            due = t.get("due") or {}
            due_date = due.get("date", "")
            if due_date and due_date < today_str:
                overdue.append(t)
            else:
                today_tasks.append(t)

        lines = [f"📋 *Task hôm nay ({len(tasks)} task):*\n"]

        if overdue:
            lines.append("⚠️ *Quá hạn:*")
            for t in overdue:
                p = PRIORITY_EMOJI.get(t.get("priority", 4), "🟢")
                lines.append(f"  • {p} {t['content']}")

        if today_tasks:
            lines.append("\n📅 *Hôm nay:*")
            for t in today_tasks:
                p = PRIORITY_EMOJI.get(t.get("priority", 4), "🟢")
                due = t.get("due") or {}
                time_str = ""
                if due.get("datetime"):
                    try:
                        dt = datetime.fromisoformat(due["datetime"].replace("Z", "+00:00"))
                        time_str = f" ⏰ {dt.strftime('%H:%M')}"
                    except:
                        pass
                lines.append(f"  • {p} *{t['content']}*{time_str}")

        return "\n".join(lines)

    # ─── 2. XEM TASK TUẦN NÀY ────────────────────────────────────
    async def get_tasks_week(self) -> str:
        data = self._get("tasks", {"filter": "7 days"})
        if data is None:
            return "❌ Không thể kết nối Todoist"

        tasks = data.get("results", data) if isinstance(data, dict) else data
        if not tasks:
            return "✅ *Không có task nào trong tuần!*"

        lines = [f"📋 *Task tuần này ({len(tasks)} task):*\n"]
        grouped = {}
        for t in tasks:
            due = t.get("due") or {}
            due_date = due.get("date", "Không có hạn")
            grouped.setdefault(due_date, []).append(t)

        for date in sorted(grouped.keys()):
            if date == "Không có hạn":
                label = "📌 Không có hạn"
            else:
                try:
                    dt = datetime.strptime(date, "%Y-%m-%d")
                    weekday = ["T2","T3","T4","T5","T6","T7","CN"][dt.weekday()]
                    label = f"📅 {weekday} {dt.strftime('%d/%m')}"
                except:
                    label = f"📅 {date}"
            lines.append(f"\n{label}:")
            for t in grouped[date]:
                p = PRIORITY_EMOJI.get(t.get("priority", 4), "🟢")
                lines.append(f"  • {p} {t['content']}")

        return "\n".join(lines)

    # ─── 3. TẠO TASK ─────────────────────────────────────────────
    async def add_task(self, content: str, description: str = "",
                       due: str = "", priority: str = "p4",
                       project_name: str = "", labels: list = None) -> str:
        # priority: p1-p4 → số 1-4
        try:
            priority_num = int(priority[1]) if priority and priority.startswith("p") else 4
        except:
            priority_num = 4

        data = {
            "content": content,
            "priority": priority_num,
        }
        if description:
            data["description"] = description
        if due:
            data["due_string"] = due
            data["due_lang"] = "vi"
        if labels:
            data["labels"] = labels

        # Tìm project
        if project_name:
            projects = self._get("projects")
            if projects:
                plist = projects.get("results", projects) if isinstance(projects, dict) else projects
                for p in plist:
                    if project_name.lower() in p.get("name", "").lower():
                        data["project_id"] = p["id"]
                        break

        task = self._post("tasks", data)
        if not task:
            return "❌ Không thể tạo task. Vui lòng thử lại!"

        p_emoji = PRIORITY_EMOJI.get(priority_num, "🟢")
        p_name = PRIORITY_NAME.get(priority_num, "Thường")
        return (
            f"✅ *Đã tạo task!*\n\n"
            f"{p_emoji} *{content}*\n"
            f"⏰ Hạn: {due or 'Chưa đặt'}\n"
            f"📊 Ưu tiên: {p_name}"
        )

    # ─── 4. HOÀN THÀNH TASK ──────────────────────────────────────
    async def complete_task(self, keyword: str) -> str:
        data = self._get("tasks")
        if not data:
            return "❌ Không thể lấy danh sách task"

        tasks = data.get("results", data) if isinstance(data, dict) else data
        keyword_lower = keyword.lower()
        matched = [t for t in tasks if keyword_lower in t.get("content", "").lower()]

        if not matched:
            return f"🔍 Không tìm thấy task chứa *'{keyword}'*"

        if len(matched) == 1:
            task = matched[0]
            result = self._post(f"tasks/{task['id']}/close")
            if result is not None:
                return f"✅ *Đã hoàn thành:*\n\n~~{task['content']}~~"
            return "❌ Không thể hoàn thành task"

        lines = [f"🔍 Tìm thấy *{len(matched)} task* khớp:\n"]
        for i, t in enumerate(matched[:5], 1):
            p = PRIORITY_EMOJI.get(t.get("priority", 4), "🟢")
            lines.append(f"  *{i}.* {p} {t['content']}")
        lines.append("\nNhắn cụ thể hơn để hoàn thành đúng task nhé!")
        return "\n".join(lines)

    # ─── 5. GHI CHÚ THEO TASK ────────────────────────────────────
    async def add_comment(self, task_keyword: str, comment: str) -> str:
        data = self._get("tasks")
        if not data:
            return "❌ Không thể lấy danh sách task"

        tasks = data.get("results", data) if isinstance(data, dict) else data
        matched = [t for t in tasks if task_keyword.lower() in t.get("content", "").lower()]

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
        data = self._get("tasks")
        if not data:
            return "❌ Không thể lấy danh sách task"

        tasks = data.get("results", data) if isinstance(data, dict) else data
        matched = [t for t in tasks if task_keyword.lower() in t.get("content", "").lower()]

        if not matched:
            return f"🔍 Không tìm thấy task *'{task_keyword}'*"

        task = matched[0]
        comments_data = self._get("comments", {"task_id": task["id"]})

        if not comments_data:
            return f"📌 Task *{task['content']}*\n\n💬 Chưa có ghi chú nào"

        comments = comments_data.get("results", comments_data) if isinstance(comments_data, dict) else comments_data
        if not comments:
            return f"📌 Task *{task['content']}*\n\n💬 Chưa có ghi chú nào"

        lines = [f"📌 *{task['content']}*\n\n💬 *Ghi chú ({len(comments)}):*"]
        for c in comments:
            lines.append(f"\n  • {c.get('content', '')}")
        return "\n".join(lines)

    # ─── 6. BÁO CÁO NĂNG SUẤT ───────────────────────────────────
    async def get_productivity_report(self) -> str:
        data = self._get("tasks", {"filter": "today | overdue"})
        if not data:
            return "❌ Không thể kết nối Todoist"

        open_tasks = data.get("results", data) if isinstance(data, dict) else data
        open_count = len(open_tasks)

        lines = ["📊 *Báo cáo năng suất hôm nay:*\n"]
        lines.append(f"📋 Task cần làm hôm nay: *{open_count} task*")

        if open_tasks:
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

            lines.append(f"\n⚡ *Danh sách cần làm:*")
            for t in open_tasks[:5]:
                p = PRIORITY_EMOJI.get(t.get("priority", 4), "🟢")
                lines.append(f"  • {p} {t['content']}")

        return "\n".join(lines)

    # ─── 7. XEM DỰ ÁN ───────────────────────────────────────────
    async def get_projects(self) -> str:
        data = self._get("projects")
        if not data:
            return "❌ Không thể lấy danh sách dự án"

        projects = data.get("results", data) if isinstance(data, dict) else data
        if not projects:
            return "📁 Chưa có dự án nào"

        lines = [f"📁 *Danh sách dự án ({len(projects)}):*\n"]
        for p in projects:
            lines.append(f"  • 📂 *{p.get('name', '?')}*")
        return "\n".join(lines)
