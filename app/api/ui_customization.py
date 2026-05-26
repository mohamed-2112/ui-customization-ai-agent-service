import logging
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.request_context import agent_run_id_context, user_id_context
from app.db.session import get_db_session
from app.repositories.agent_run_repository import (
    create_agent_run,
    update_agent_run_result,
)

from app.repositories.ui_template_repository import (
    apply_ui_template_draft,
    get_active_ui_template_for_user,
    get_ui_template_draft_for_user,
    save_ui_template_draft,
)

from app.schemas.ui_template import (
    UIActiveTemplateResponse,
    UIApplyDraftResponse,
    UICustomizationDraftRequest,
    UICustomizationDraftResponse,
    UIDraftDetailsResponse,
    UITemplate,
    PageName,
)

from app.security.internal_auth import (
    InternalAuthContext,
    get_internal_auth_context,
)

from app.workflows.ui_customization_workflow import ui_customization_graph


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agent/ui-customization", tags=["UI Customization Agent"])



def parse_template_from_db(template_json: dict) -> UITemplate:
    return UITemplate.model_validate(template_json)

@router.post("/draft", response_model=UICustomizationDraftResponse)
def create_ui_customization_draft(
    request: UICustomizationDraftRequest,
    db: Session = Depends(get_db_session),
    auth: InternalAuthContext = Depends(get_internal_auth_context),
) -> UICustomizationDraftResponse:
    agent_run_id = str(uuid4())
    user_id = auth.user_id

    agent_token = agent_run_id_context.set(agent_run_id)
    user_token = user_id_context.set(user_id)

    try:
        logger.info(
            "agent_run_started",
            extra={
                "page": request.page,
                "message_length": len(request.message),
                "model_provider": settings.llm_provider,
                "model_name": settings.hf_model,
                "auth_mode": auth.auth_mode,
            },
        )

        create_agent_run(
            db,
            agent_run_id=agent_run_id,
            user_id=user_id,
            page=request.page,
            model_provider=settings.llm_provider,
            model_name=settings.hf_model,
            message_length=len(request.message),
        )

        result = ui_customization_graph.invoke(
            {
                "agent_run_id": agent_run_id,
                "user_id": user_id,
                "model_provider": settings.llm_provider,
                "model_name": settings.hf_model,
                "user_message": request.message,
                "page": request.page,
            }
        )

        response: UICustomizationDraftResponse = result["response"]

        update_agent_run_result(
            db,
            agent_run_id=agent_run_id,
            status=response.status,
            attempts=response.attempts,
            validation_errors=response.validation_errors,
            generation_error=None,
        )

        if response.status == "draft_created" and response.draft_template is not None:
            draft = save_ui_template_draft(
                db,
                agent_run_id=agent_run_id,
                user_id=user_id,
                page=request.page,
                template=response.draft_template,
            )

            response.draft_id = str(draft.id)

            logger.info(
                "ui_template_draft_saved",
                extra={
                    "draft_id": response.draft_id,
                    "page": request.page,
                },
            )

        return response

    except Exception as exc:
        logger.exception(
            "agent_run_unhandled_error",
            extra={
                "agent_run_id": agent_run_id,
                "page": request.page,
            },
        )

        try:
            update_agent_run_result(
                db,
                agent_run_id=agent_run_id,
                status="failed_internal_error",
                attempts=1,
                validation_errors=None,
                generation_error=str(exc),
            )
        except Exception:
            logger.exception("failed_to_update_agent_run_after_error")

        raise HTTPException(
            status_code=500,
            detail={
                "message": "Failed to generate UI customization draft.",
                "agent_run_id": agent_run_id,
            },
        ) from exc

    finally:
        agent_run_id_context.reset(agent_token)
        user_id_context.reset(user_token)
        
        
        
@router.get("/drafts/{draft_id}", response_model=UIDraftDetailsResponse)
def get_ui_customization_draft(
    draft_id: UUID,
    db: Session = Depends(get_db_session),
    auth: InternalAuthContext = Depends(get_internal_auth_context),
) -> UIDraftDetailsResponse:
    user_id = auth.user_id

    user_token = user_id_context.set(user_id)

    try:
        draft = get_ui_template_draft_for_user(
            db,
            draft_id=str(draft_id),
            user_id=user_id,
        )

        if draft is None:
            raise HTTPException(
                status_code=404,
                detail="Draft not found.",
            )

        if draft.template_json is None:
            raise HTTPException(
                status_code=500,
                detail="Draft exists but does not contain a template.",
            )

        template = parse_template_from_db(draft.template_json)

        return UIDraftDetailsResponse(
            draft_id=str(draft.id),
            agent_run_id=str(draft.agent_run_id),
            user_id=draft.user_id,
            page=draft.page,
            status=draft.status,
            template=template,
        )

    finally:
        user_id_context.reset(user_token)


@router.post("/drafts/{draft_id}/apply", response_model=UIApplyDraftResponse)
def apply_ui_customization_draft(
    draft_id: UUID,
    db: Session = Depends(get_db_session),
    auth: InternalAuthContext = Depends(get_internal_auth_context),
) -> UIApplyDraftResponse:
    user_id = auth.user_id

    user_token = user_id_context.set(user_id)

    try:
        draft = get_ui_template_draft_for_user(
            db,
            draft_id=str(draft_id),
            user_id=user_id,
        )

        if draft is None:
            raise HTTPException(
                status_code=404,
                detail="Draft not found.",
            )

        if draft.status != "DRAFT":
            raise HTTPException(
                status_code=409,
                detail=f"Draft cannot be applied because its status is '{draft.status}'.",
            )

        try:
            applied_template = apply_ui_template_draft(
                db,
                draft=draft,
            )

        except ValueError as exc:
            raise HTTPException(
                status_code=400,
                detail=str(exc),
            ) from exc

        template = parse_template_from_db(applied_template.template_json)

        logger.info(
            "ui_template_draft_applied",
            extra={
                "draft_id": str(draft.id),
                "applied_template_id": str(applied_template.id),
                "page": applied_template.page,
                "version": applied_template.version,
                "auth_mode": auth.auth_mode,
            },
        )

        return UIApplyDraftResponse(
            status="applied",
            message="The UI template draft was applied successfully.",
            draft_id=str(draft.id),
            applied_template_id=str(applied_template.id),
            page=applied_template.page,
            version=applied_template.version,
            template=template,
        )

    finally:
        user_id_context.reset(user_token)
        
        
        

@router.get("/pages/{page}/active", response_model=UIActiveTemplateResponse)
def get_active_ui_template(
    page: PageName,
    db: Session = Depends(get_db_session),
    auth: InternalAuthContext = Depends(get_internal_auth_context),
) -> UIActiveTemplateResponse:
    user_id = auth.user_id

    user_token = user_id_context.set(user_id)

    try:
        active_template = get_active_ui_template_for_user(
            db,
            user_id=user_id,
            page=page,
        )

        if active_template is None:
            raise HTTPException(
                status_code=404,
                detail=f"No active UI template found for page '{page}'.",
            )

        template = parse_template_from_db(active_template.template_json)

        logger.info(
            "active_ui_template_fetched",
            extra={
                "active_template_id": str(active_template.id),
                "page": active_template.page,
                "version": active_template.version,
                "auth_mode": auth.auth_mode,
            },
        )

        return UIActiveTemplateResponse(
            active_template_id=str(active_template.id),
            user_id=active_template.user_id,
            page=active_template.page,
            status=active_template.status,
            version=active_template.version,
            template=template,
        )

    finally:
        user_id_context.reset(user_token)