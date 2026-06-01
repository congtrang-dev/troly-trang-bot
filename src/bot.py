"""
===========================================
  TELEGRAM AI AGENT - bot.py
  Bao gồm: handlers + báo cáo tự động 8h sáng
===========================================
"""

import os
import logging
import asyncio
import pytz
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)
from agent import AIAgent

load_dotenv()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")  # ID của bạn để nhận báo cáo tự động

agent = AIAgent()
VN_TZ = pytz.timezone("Asia/Ho_Chi_Minh")

# ─── Báo cáo tự động 8h sáng ─────────────────────────────────────
async def send_morning_report(app: Application):
    """Gửi báo cáo tự động mỗi 8h sáng giờ VN"""
    if not CHAT_ID:
        logger.warning("⚠️ Chưa cấu hình TELEGRAM_CHAT_ID")
        return
    try:
        now_vn = datetime.now(VN_TZ)
        today_str = now_vn.strftime("%d/%m/%Y")
        weekday = ["Thứ 2","Thứ 3","Thứ 4","Thứ 5","Thứ 6","Thứ 7","Chủ nhật"][now_vn.weekday()]

        # Lấy lịch hẹn hôm nay
        calendar_report = await agent.get_today_events()

        # Lấy task hôm nay từ Todoist
        task_report = await agent.todoist.get_tasks_today()

        message = (
            f"☀️ *Báo cáo buổi sáng - {weekday} {today_str}*\n"
            f"━━━━━━━━━━━━━━━━━━\n\n"
            f"{calendar_report}\n\n"
            f"━━━━━━━━━━━━━━━━━━\n\n"
            f"{task_report}\n\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"💪 Chúc bạn một ngày làm việc hiệu quả!"
        )

        await app.bot.send_message(
            chat_id=CHAT_ID,
            text=message,
            parse_mode="Markdown"
        )
        logger.info(f"✅ Đã gửi báo cáo sáng {today_str}")

    except Exception as e:
        logger.error(f"❌ Lỗi gửi báo cáo sáng: {e}")


async def schedule_morning_report(app: Application):
    """Vòng lặp kiểm tra giờ và gửi báo cáo lúc 8:00 sáng VN"""
    sent_today = None
    while True:
        try:
            now_vn = datetime.now(VN_TZ)
            today_date = now_vn.strftime("%Y-%m-%d")

            # Gửi lúc 8:00 sáng, chỉ gửi 1 lần mỗi ngày
            if now_vn.hour == 8 and now_vn.minute == 0 and sent_today != today_date:
                await send_morning_report(app)
                sent_today = today_date

            await asyncio.sleep(30)  # Kiểm tra mỗi 30 giây
        except Exception as e:
            logger.error(f"Schedule error: {e}")
            await asyncio.sleep(60)


# ─── Handler: /start ─────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    welcome = (
        f"👋 Xin chào *{user.first_name}*!\n\n"
        "Tôi là trợ lý AI giúp bạn:\n"
        "📅 *Quản lý lịch hẹn* Google Calendar\n"
        "👥 *Ghi chú khách hàng* tiềm năng\n"
        "📋 *Quản lý task* Todoist\n"
        "📊 *Báo cáo* tự động mỗi 8h sáng\n\n"
        "Nhắn tin tự nhiên như:\n"
        "• _\"Tạo lịch gặp anh Minh ngày mai 2pm\"_\n"
        "• _\"Thêm task: Gọi khách hàng, hạn ngày mai\"_\n"
        "• _\"Danh sách khách hàng tiềm năng\"_\n\n"
        "Gõ /help để xem tất cả lệnh 🚀"
    )
    keyboard = [
        [InlineKeyboardButton("📅 Lịch hôm nay", callback_data="view_today"),
         InlineKeyboardButton("📋 Task hôm nay", callback_data="view_tasks")],
        [InlineKeyboardButton("👥 Danh sách KH", callback_data="list_customers"),
         InlineKeyboardButton("📊 Báo cáo", callback_data="report")],
    ]
    await update.message.reply_text(
        welcome, parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ─── Handler: /help ──────────────────────────────────────────────
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "📖 *Danh sách lệnh:*\n\n"
        "*/start* - Màn hình chào mừng\n"
        "*/today* - Lịch hẹn hôm nay\n"
        "*/week* - Lịch tuần này\n"
        "*/tasks* - Task hôm nay (Todoist)\n"
        "*/customers* - Danh sách khách hàng\n"
        "*/report* - Báo cáo tổng hợp\n"
        "*/morning* - Xem báo cáo sáng ngay\n\n"
        "💬 *Nhắn tự nhiên:*\n"
        "• _\"Gặp chị Lan 3pm thứ 6\"_\n"
        "• _\"Thêm task: Gọi KH, hạn ngày mai, ưu tiên cao\"_\n"
        "• _\"Xong task gọi khách hàng\"_\n"
        "• _\"Ghi chú task ABC: đã gửi báo giá\"_\n"
        "• _\"Thêm KH: Tên, SĐT, nhu cầu\"_\n"
    )
    await update.message.reply_text(help_text, parse_mode="Markdown")


# ─── Handler: /today ─────────────────────────────────────────────
async def today(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⏳ Đang tải lịch hôm nay...")
    result = await agent.get_today_events()
    await update.message.reply_text(result, parse_mode="Markdown")


# ─── Handler: /week ──────────────────────────────────────────────
async def week(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⏳ Đang tải lịch tuần này...")
    result = await agent.get_week_events()
    await update.message.reply_text(result, parse_mode="Markdown")


# ─── Handler: /tasks ─────────────────────────────────────────────
async def tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⏳ Đang tải task hôm nay...")
    result = await agent.todoist.get_tasks_today()
    await update.message.reply_text(result, parse_mode="Markdown")


# ─── Handler: /customers ─────────────────────────────────────────
async def customers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⏳ Đang tải danh sách khách hàng...")
    result = await agent.get_customers()
    await update.message.reply_text(result, parse_mode="Markdown")


# ─── Handler: /report ────────────────────────────────────────────
async def report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⏳ Đang tạo báo cáo...")
    result = await agent.generate_report()
    await update.message.reply_text(result, parse_mode="Markdown")


# ─── Handler: /morning - Xem báo cáo sáng ngay ──────────────────
async def morning(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⏳ Đang tạo báo cáo buổi sáng...")
    await send_morning_report(context.application)


# ─── Handler: Tin nhắn thường ────────────────────────────────────
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    user_id = str(update.effective_user.id)
    await update.message.reply_text("🤔 Đang xử lý...")

    try:
        response = await agent.process_message(user_message, user_id)
        await update.message.reply_text(response, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Error: {e}")
        await update.message.reply_text(f"❌ Có lỗi xảy ra: {str(e)}")


# ─── Handler: Inline buttons ─────────────────────────────────────
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "view_today":
        result = await agent.get_today_events()
    elif query.data == "view_tasks":
        result = await agent.todoist.get_tasks_today()
    elif query.data == "list_customers":
        result = await agent.get_customers()
    elif query.data == "report":
        result = await agent.generate_report()
    else:
        return

    await query.message.reply_text(result, parse_mode="Markdown")


# ─── Khởi động bot ───────────────────────────────────────────────
def main():
    if not TELEGRAM_TOKEN:
        raise ValueError("❌ Thiếu TELEGRAM_TOKEN!")

    app = Application.builder().token(TELEGRAM_TOKEN).build()

    # Đăng ký handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("today", today))
    app.add_handler(CommandHandler("week", week))
    app.add_handler(CommandHandler("tasks", tasks))
    app.add_handler(CommandHandler("customers", customers))
    app.add_handler(CommandHandler("report", report))
    app.add_handler(CommandHandler("morning", morning))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Chạy scheduler báo cáo sáng song song
    async def post_init(app):
        asyncio.create_task(schedule_morning_report(app))

    app.post_init = post_init

    logger.info("🚀 Bot đang chạy...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
