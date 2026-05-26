from contextvars import ContextVar


request_id_context: ContextVar[str | None] = ContextVar(
    "request_id",
    default=None,
)

agent_run_id_context: ContextVar[str | None] = ContextVar(
    "agent_run_id",
    default=None,
)

user_id_context: ContextVar[str | None] = ContextVar(
    "user_id",
    default=None,
)


def get_request_id() -> str | None:
    return request_id_context.get()


def get_agent_run_id() -> str | None:
    return agent_run_id_context.get()


def get_user_id() -> str | None:
    return user_id_context.get()