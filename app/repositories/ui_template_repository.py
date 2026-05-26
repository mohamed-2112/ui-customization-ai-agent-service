import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import UITemplateDraftModel, UITemplateVersionModel
from app.schemas.ui_template import UITemplate


def save_ui_template_draft(
    db: Session,
    *,
    agent_run_id: str,
    user_id: str,
    page: str,
    template: UITemplate,
) -> UITemplateDraftModel:
    draft = UITemplateDraftModel(
        agent_run_id=uuid.UUID(agent_run_id),
        user_id=user_id,
        page=page,
        status="DRAFT",
        template_json=template.model_dump(mode="json"),
    )

    db.add(draft)
    db.commit()
    db.refresh(draft)

    return draft


def get_ui_template_draft_for_user(
    db: Session,
    *,
    draft_id: str,
    user_id: str,
) -> UITemplateDraftModel | None:
    stmt = select(UITemplateDraftModel).where(
        UITemplateDraftModel.id == uuid.UUID(draft_id),
        UITemplateDraftModel.user_id == user_id,
    )

    return db.scalar(stmt)


def get_next_template_version(
    db: Session,
    *,
    user_id: str,
    page: str,
) -> int:
    stmt = select(func.max(UITemplateVersionModel.version)).where(
        UITemplateVersionModel.user_id == user_id,
        UITemplateVersionModel.page == page,
    )

    current_max_version = db.scalar(stmt)

    if current_max_version is None:
        return 1

    return current_max_version + 1


def apply_ui_template_draft(
    db: Session,
    *,
    draft: UITemplateDraftModel,
) -> UITemplateVersionModel:
    if draft.template_json is None:
        raise ValueError("Draft does not contain a template.")

    if draft.status != "DRAFT":
        raise ValueError(f"Draft cannot be applied because its status is '{draft.status}'.")

    next_version = get_next_template_version(
        db,
        user_id=draft.user_id,
        page=draft.page,
    )

    applied_template = UITemplateVersionModel(
        source_draft_id=draft.id,
        user_id=draft.user_id,
        page=draft.page,
        version=next_version,
        status="APPLIED",
        template_json=draft.template_json,
    )

    draft.status = "APPLIED"

    db.add(applied_template)
    db.commit()
    db.refresh(applied_template)

    return applied_template


def get_active_ui_template_for_user(
    db: Session,
    *,
    user_id: str,
    page: str,
) -> UITemplateVersionModel | None:
    stmt = (
        select(UITemplateVersionModel)
        .where(
            UITemplateVersionModel.user_id == user_id,
            UITemplateVersionModel.page == page,
            UITemplateVersionModel.status == "APPLIED",
        )
        .order_by(UITemplateVersionModel.version.desc())
        .limit(1)
    )

    return db.scalar(stmt)