from uuid import uuid4


def new_session_id() -> str:
    return uuid4().hex


def new_message_id() -> str:
    return uuid4().hex


def new_task_id() -> str:
    return uuid4().hex


def new_permission_request_id() -> str:
    return uuid4().hex
