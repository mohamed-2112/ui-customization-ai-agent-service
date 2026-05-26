import uuid

from sqlalchemy.orm import Session

from app.db.models import AgentRunModel


def create_agent_run(
    db: Session,
    *,
    agent_run_id: str,
    user_id: str,
    page: str,
    model_provider: str,
    model_name: str,
    message_length: int,
) -> AgentRunModel:
    agent_run = AgentRunModel(
        id=uuid.UUID(agent_run_id),
        user_id=user_id,
        page=page,
        model_provider=model_provider,
        model_name=model_name,
        status="STARTED",
        attempts=1,
        message_length=message_length,
    )

    db.add(agent_run)
    db.commit()
    db.refresh(agent_run)

    return agent_run


def update_agent_run_result(
    db: Session,
    *,
    agent_run_id: str,
    status: str,
    attempts: int,
    validation_errors: list[str] | None = None,
    generation_error: str | None = None,
) -> None:
    agent_run = db.get(AgentRunModel, uuid.UUID(agent_run_id))

    if agent_run is None:
        raise ValueError(f"Agent run not found: {agent_run_id}")

    agent_run.status = status
    agent_run.attempts = attempts
    agent_run.validation_errors = validation_errors
    agent_run.generation_error = generation_error

    db.commit()