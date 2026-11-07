import pytest

from app.services import bot, subscribers, telegram

ADMIN, STRANGER = 100, 200
USER = {"id": STRANGER, "username": "someone", "first_name": "An"}


@pytest.fixture
def api(monkeypatch):
    calls = []
    monkeypatch.setattr(telegram, "admin_id", lambda: ADMIN)
    monkeypatch.setattr(telegram, "send_to", lambda chat_id, text, buttons=None: calls.append(("send", chat_id, text, buttons)))
    monkeypatch.setattr(telegram, "call", lambda method, **params: calls.append((method, params)))
    return calls


def start(user):
    bot.handle_update({"update_id": 1, "message": {"chat": {"type": "private"}, "from": user, "text": "/start"}})


def decision(sender, data):
    bot.handle_update({"update_id": 2, "callback_query": {
        "id": "cb", "from": {"id": sender}, "data": data,
        "message": {"chat": {"id": ADMIN}, "message_id": 5, "text": "Yêu cầu nhận báo cáo paper trading"}}})


def test_start_asks_the_owner_with_accept_and_reject_side_by_side(api):
    start(USER)
    assert subscribers.get(STRANGER)["status"] == "pending"
    to_user, to_owner = api
    assert to_user[1] == STRANGER
    assert to_owner[1] == ADMIN and "@someone" in to_owner[2]
    (row,) = to_owner[3]
    assert [button["text"] for button in row] == ["Accept", "Reject"]
    assert [button["callback_data"] for button in row] == [f"approve:{STRANGER}", f"reject:{STRANGER}"]


def test_accept_subscribes_the_user_and_tells_them(api):
    start(USER)
    api.clear()
    decision(ADMIN, f"approve:{STRANGER}")
    assert subscribers.approved() == [STRANGER]
    assert api[-1][:2] == ("send", STRANGER) and api[-1][2] == bot.ACCEPTED
    assert any(call[0] == "editMessageText" for call in api)


def test_reject_keeps_the_user_out(api):
    start(USER)
    decision(ADMIN, f"reject:{STRANGER}")
    assert subscribers.approved() == [] and subscribers.get(STRANGER)["status"] == "rejected"
    assert api[-1][2] == bot.REJECTED


def test_only_the_owner_can_decide(api):
    start(USER)
    decision(STRANGER, f"approve:{STRANGER}")
    assert subscribers.get(STRANGER)["status"] == "pending"


def test_a_decided_request_cannot_be_flipped_and_repeat_start_does_not_ask_again(api):
    start(USER)
    decision(ADMIN, f"approve:{STRANGER}")
    decision(ADMIN, f"reject:{STRANGER}")
    assert subscribers.get(STRANGER)["status"] == "approved"
    api.clear()
    start(USER)
    assert [call[1] for call in api] == [STRANGER]


def test_the_owner_is_subscribed_without_asking_anyone(api):
    start({"id": ADMIN, "username": "owner"})
    assert subscribers.approved() == [ADMIN]
    assert [call[1] for call in api] == [ADMIN]


def test_poll_loop_acknowledges_updates_and_handles_them(api, monkeypatch):
    import asyncio

    polls = []

    def get_updates(method, **params):
        polls.append(params)
        if len(polls) == 1:
            return [{"update_id": 41, "message": {"chat": {"type": "private"}, "from": USER, "text": "/start"}}]
        raise asyncio.CancelledError

    monkeypatch.setattr(telegram, "call", get_updates)
    with pytest.raises(asyncio.CancelledError):
        asyncio.run(bot.poll_loop())
    assert polls[0]["offset"] is None and polls[1]["offset"] == 42
    assert subscribers.get(STRANGER)["status"] == "pending"
