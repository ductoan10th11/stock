import json
import os
import urllib.request

API = "https://api.telegram.org"


def configured() -> bool:
    return bool(os.environ.get("TELEGRAM_BOT_TOKEN") and os.environ.get("TELEGRAM_CHAT_ID"))


def admin_id() -> int:
    """The owner's private chat; its id is also the owner's user id, which is what approvals are checked against."""
    return int(os.environ["TELEGRAM_CHAT_ID"])


def call(method: str, *, http_timeout: float = 15, **params):
    request = urllib.request.Request(
        f"{API}/bot{os.environ['TELEGRAM_BOT_TOKEN']}/{method}",
        data=json.dumps(params).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=http_timeout) as response:
        return json.load(response)["result"]


def send_to(chat_id: int, text: str, buttons: list[list[dict]] | None = None) -> None:
    params = {"chat_id": chat_id, "text": text}
    if buttons:
        params["reply_markup"] = {"inline_keyboard": buttons}
    call("sendMessage", **params)


def send(text: str) -> None:
    send_to(admin_id(), text)
