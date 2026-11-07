"""Telegram bot: /start asks the owner for approval, an approved user then receives the daily report."""

from __future__ import annotations

import asyncio
import logging

from app.services import subscribers, telegram

logger = logging.getLogger("uvicorn.error")

POLL_SECONDS = 10
RETRY_SECONDS = 5

WAITING = "Đã gửi yêu cầu đến quản trị viên. Bạn sẽ nhận được tin khi được duyệt."
ACCEPTED = "Yêu cầu đã được chấp nhận. Bạn sẽ nhận báo cáo biến động tài khoản paper trading mỗi ngày giao dịch."
REJECTED = "Yêu cầu của bạn đã bị từ chối."
REPLIES = {"approved": "Bạn đã đăng ký nhận báo cáo.", "pending": "Yêu cầu của bạn đang chờ duyệt.", "rejected": REJECTED}


def display_name(user: dict) -> str:
    name = user.get("first_name") or "Người dùng"
    return f"{name} (@{user['username']})" if user.get("username") else name


def ask_owner(user: dict) -> None:
    chat_id = user["id"]
    telegram.send_to(
        telegram.admin_id(),
        f"Yêu cầu nhận báo cáo paper trading\nNgười dùng: {display_name(user)}\nID: {chat_id}",
        buttons=[[{"text": "Accept", "callback_data": f"approve:{chat_id}"}, {"text": "Reject", "callback_data": f"reject:{chat_id}"}]],
    )


def on_start(user: dict) -> None:
    chat_id = user["id"]
    if chat_id == telegram.admin_id():
        subscribers.set_status(chat_id, "approved", user)
        telegram.send_to(chat_id, "Bạn là quản trị viên, báo cáo hằng ngày sẽ gửi cho bạn.")
        return
    known = subscribers.get(chat_id)
    if known:
        telegram.send_to(chat_id, REPLIES[known["status"]])
        return
    subscribers.set_status(chat_id, "pending", user)
    telegram.send_to(chat_id, WAITING)
    ask_owner(user)


def on_decision(callback: dict) -> None:
    if callback["from"]["id"] != telegram.admin_id():
        telegram.call("answerCallbackQuery", callback_query_id=callback["id"], text="Bạn không có quyền duyệt.", show_alert=True)
        return
    action, _, raw_id = callback["data"].partition(":")
    chat_id = int(raw_id)
    known = subscribers.get(chat_id)
    message = callback["message"]
    if action not in ("approve", "reject") or known is None or known["status"] != "pending":
        telegram.call("answerCallbackQuery", callback_query_id=callback["id"], text="Yêu cầu này đã được xử lý.")
        return
    approve = action == "approve"
    subscribers.set_status(chat_id, "approved" if approve else "rejected", known)
    telegram.call("answerCallbackQuery", callback_query_id=callback["id"], text="Đã chấp nhận." if approve else "Đã từ chối.")
    telegram.call(
        "editMessageText", chat_id=message["chat"]["id"], message_id=message["message_id"],
        text=f"{message['text']}\n\n{'Đã chấp nhận' if approve else 'Đã từ chối'}",
    )
    telegram.send_to(chat_id, ACCEPTED if approve else REJECTED)


def handle_update(update: dict) -> None:
    message = update.get("message")
    if message and message.get("chat", {}).get("type") == "private" and (message.get("text") or " ").split()[0].split("@")[0] == "/start":
        on_start(message["from"])
    elif "callback_query" in update:
        on_decision(update["callback_query"])


async def poll_loop() -> None:
    offset = None
    while True:
        try:
            updates = await asyncio.to_thread(
                telegram.call, "getUpdates", http_timeout=POLL_SECONDS + 10, offset=offset, timeout=POLL_SECONDS,
                allowed_updates=["message", "callback_query"],
            )
        except Exception:
            logger.exception("telegram polling failed")
            await asyncio.sleep(RETRY_SECONDS)
            continue
        for update in updates:
            offset = update["update_id"] + 1
            try:
                await asyncio.to_thread(handle_update, update)
            except Exception:
                logger.exception("telegram update %s failed", update["update_id"])
