"""
===========================================
  TELEGRAM AI AGENT - Quản lý công việc
  Bot chính - bot.py
===========================================
"""

import os
from dotenv import load_dotenv
load_dotenv()
import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)
from agent import AIAgent

# ─── Cấu hình logging ───────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ─── Load biến môi trường ────────────────────────────────────────
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

# Khởi tạo AI Agent
agent = AIAgent()

# ─── Handler: /start ─────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    welcome = (
        f"👋 Xin chào *{user.first_name}*!\n\n"
        "Tôi là trợ lý AI giúp bạn:\n"
        "📅 *Quản lý lịch hẹn* Google Calendar\n"
        "👥 *Ghi chú khách hàng* tiềm năng\n"
        "📊 *Báo cáo* lịch làm việc & danh sách KH\n\n"
        "Bạn có thể nhắn tin tự nhiên như:\n"
        "• _\"Tạo lịch gặp anh Minh ngày mai 2pm\"_\n"
        "• _\"Thêm khách hàng: Công ty ABC, liên hệ Hoa, SĐT 0909...\"_\n"
        "• _\"Báo cáo lịch tuần này\"_\n"
        "• _\"Danh sách khách hàng tiềm năng\"_\n\n"
        "Gõ /help để xem tất cả lệnh 🚀"
    )
    keyboard = [
        [InlineKeyboardButton("📅 Xem lịch hôm nay", callback_data="view_today")],
        [InlineKeyboardButton("👥 Danh sách KH", callback_data="list_customers"),
         InlineKeyboardButton("📊 Báo cáo", callback_data="report")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(welcome, parse_mode="Markdown", reply_markup=reply_markup)


# ─── Handler: /help ──────────────────────────────────────────────
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "📖 *Danh sách lệnh:*\n\n"
        "*/start* - Màn hình chào mừng\n"
        "*/today* - Lịch hẹn hôm nay\n"
        "*/week* - Lịch tuần này\n"
        "*/customers* - Danh sách khách hàng\n"
        "*/report* - Báo cáo tổng hợp\n"
        "*/help* - Xem hướng dẫn này\n\n"
        "💬 *Hoặc nhắn tin tự nhiên:*\n"
        "• Tạo lịch hẹn: _\"Gặp chị Lan 3pm thứ 6\"_\n"
        "• Thêm KH: _\"Thêm KH: Tên, SĐT, nhu cầu\"_\n"
        "• Tìm KH: _\"Tìm khách hàng tên Minh\"_\n"
        "• Cập nhật: _\"KH Công ty ABC đã chốt hợp đồng\"_\n"
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


# ─── Handler: Tin nhắn thường (AI xử lý) ────────────────────────
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    await update.message.reply_text("🤔 Đang xử lý...")

    try:
        response = await agent.process_message(user_message)
        await update.message.reply_text(response, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Error processing message: {e}")
        await update.message.reply_text(
            "❌ Có lỗi xảy ra. Vui lòng thử lại!\n"
            f"Chi tiết: {str(e)}"
        )


# ─── Handler: Inline buttons ─────────────────────────────────────
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "view_today":
        result = await agent.get_today_events()
        await query.message.reply_text(result, parse_mode="Markdown")
    elif query.data == "list_customers":
        result = await agent.get_customers()
        await query.message.reply_text(result, parse_mode="Markdown")
    elif query.data == "report":
        result = await agent.generate_report()
        await query.message.reply_text(result, parse_mode="Markdown")


# ─── Khởi động bot ───────────────────────────────────────────────
def main():
    if not TELEGRAM_TOKEN:
        raise ValueError("❌ Thiếu TELEGRAM_TOKEN trong biến môi trường!")

    app = Application.builder().token(TELEGRAM_TOKEN).build()

    # Đăng ký handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("today", today))
    app.add_handler(CommandHandler("week", week))
    app.add_handler(CommandHandler("customers", customers))
    app.add_handler(CommandHandler("report", report))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("🚀 Bot đang chạy...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
