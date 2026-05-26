import logging

from typing_extensions import TypedDict
from langgraph.graph import START, END, StateGraph

from app.schemas.ui_template import (
    UICustomizationDraftResponse,
    UITemplate,
)
from app.tools.ui_validator import validate_ui_template


logger = logging.getLogger(__name__)

MAX_REPAIR_ATTEMPTS = 1


class UICustomizationState(TypedDict, total=False):
    agent_run_id: str
    user_id: str
    model_provider: str
    model_name: str

    user_message: str
    page: str

    draft_template: UITemplate | None
    raw_model_response: str
    generation_error: str | None

    repair_attempts: int
    validation_errors: list[str]

    response: UICustomizationDraftResponse


def generate_draft_template(state: UICustomizationState) -> dict:
    from app.agents.ui_template_generator import generate_ui_template_attempt

    logger.info(
        "agent_generation_started",
        extra={
            "page": state["page"],
            "model_provider": state["model_provider"],
            "model_name": state["model_name"],
            "message_length": len(state["user_message"]),
        },
    )

    attempt = generate_ui_template_attempt(
        user_message=state["user_message"],
        page=state["page"],
        current_template=None,
    )

    if attempt.error:
        logger.warning(
            "agent_generation_failed",
            extra={
                "error": attempt.error,
                "raw_response_length": len(attempt.raw_response or ""),
            },
        )
    else:
        logger.info(
            "agent_generation_succeeded",
            extra={
                "raw_response_length": len(attempt.raw_response or ""),
            },
        )

    return {
        "draft_template": attempt.template,
        "raw_model_response": attempt.raw_response,
        "generation_error": attempt.error,
        "repair_attempts": 0,
    }


def should_repair_or_validate(state: UICustomizationState) -> str:
    if state.get("draft_template") is not None:
        return "validate"

    repair_attempts = state.get("repair_attempts", 0)

    if repair_attempts < MAX_REPAIR_ATTEMPTS:
        return "repair"

    return "fail"


def repair_draft_template(state: UICustomizationState) -> dict:
    from app.agents.ui_template_generator import repair_ui_template_attempt

    logger.info(
        "agent_repair_started",
        extra={
            "repair_attempt": state.get("repair_attempts", 0) + 1,
            "previous_error": state.get("generation_error"),
        },
    )

    attempt = repair_ui_template_attempt(
        user_message=state["user_message"],
        page=state["page"],
        invalid_response=state.get("raw_model_response", ""),
        validation_error=state.get("generation_error") or "Unknown validation error.",
        current_template=None,
    )

    if attempt.error:
        logger.warning(
            "agent_repair_failed",
            extra={
                "repair_attempt": state.get("repair_attempts", 0) + 1,
                "error": attempt.error,
                "raw_response_length": len(attempt.raw_response or ""),
            },
        )
    else:
        logger.info(
            "agent_repair_succeeded",
            extra={
                "repair_attempt": state.get("repair_attempts", 0) + 1,
                "raw_response_length": len(attempt.raw_response or ""),
            },
        )

    return {
        "draft_template": attempt.template,
        "raw_model_response": attempt.raw_response,
        "generation_error": attempt.error,
        "repair_attempts": state.get("repair_attempts", 0) + 1,
    }


def validate_draft_template(state: UICustomizationState) -> dict:
    template = state.get("draft_template")

    if template is None:
        error = state.get("generation_error") or "Model did not generate a valid template."

        logger.warning(
            "agent_validation_failed",
            extra={
                "validation_error_count": 1,
                "validation_errors": [error],
            },
        )

        return {
            "validation_errors": [error],
        }

    validation_errors = validate_ui_template(template)

    if validation_errors:
        logger.warning(
            "agent_validation_failed",
            extra={
                "validation_error_count": len(validation_errors),
                "validation_errors": validation_errors,
            },
        )
    else:
        logger.info(
            "agent_validation_succeeded",
            extra={
                "component_count": count_template_nodes(template),
                "theme_mode": template.theme.mode,
                "theme_density": template.theme.density,
            },
        )

    return {"validation_errors": validation_errors}


def count_template_nodes(template: UITemplate) -> int:
    count = 0

    def walk(node):
        nonlocal count
        count += 1

        for child in node.children:
            walk(child)

    walk(template.tree)
    return count


def build_response(state: UICustomizationState) -> dict:
    validation_errors = state.get("validation_errors", [])
    attempts = state.get("repair_attempts", 0) + 1

    if validation_errors:
        response = UICustomizationDraftResponse(
            status="failed_validation",
            explanation="The generated UI template failed validation.",
            draft_template=None,
            validation_errors=validation_errors,
            agent_run_id=state["agent_run_id"],
            model_provider=state["model_provider"],
            model_name=state["model_name"],
            attempts=attempts,
        )

        logger.info(
            "agent_run_finished",
            extra={
                "status": "failed_validation",
                "attempts": attempts,
                "validation_error_count": len(validation_errors),
            },
        )

    else:
        response = UICustomizationDraftResponse(
            status="draft_created",
            explanation="A safe draft UI template was created. It has not been applied yet.",
            draft_template=state["draft_template"],
            validation_errors=[],
            agent_run_id=state["agent_run_id"],
            model_provider=state["model_provider"],
            model_name=state["model_name"],
            attempts=attempts,
        )

        logger.info(
            "agent_run_finished",
            extra={
                "status": "draft_created",
                "attempts": attempts,
            },
        )

    return {"response": response}


def build_failed_response(state: UICustomizationState) -> dict:
    attempts = state.get("repair_attempts", 0) + 1
    error = state.get("generation_error") or "Unknown generation error."

    response = UICustomizationDraftResponse(
        status="failed_validation",
        explanation="The model did not produce a valid UI template after repair.",
        draft_template=None,
        validation_errors=[error],
        agent_run_id=state["agent_run_id"],
        model_provider=state["model_provider"],
        model_name=state["model_name"],
        attempts=attempts,
    )

    logger.info(
        "agent_run_finished",
        extra={
            "status": "failed_generation",
            "attempts": attempts,
            "generation_error": error,
        },
    )

    return {"response": response}


def build_ui_customization_graph():
    graph = StateGraph(UICustomizationState)

    graph.add_node("generate_draft_template", generate_draft_template)
    graph.add_node("repair_draft_template", repair_draft_template)
    graph.add_node("validate_draft_template", validate_draft_template)
    graph.add_node("build_response", build_response)
    graph.add_node("build_failed_response", build_failed_response)

    graph.add_edge(START, "generate_draft_template")

    graph.add_conditional_edges(
        "generate_draft_template",
        should_repair_or_validate,
        {
            "validate": "validate_draft_template",
            "repair": "repair_draft_template",
            "fail": "build_failed_response",
        },
    )

    graph.add_conditional_edges(
        "repair_draft_template",
        should_repair_or_validate,
        {
            "validate": "validate_draft_template",
            "repair": "repair_draft_template",
            "fail": "build_failed_response",
        },
    )

    graph.add_edge("validate_draft_template", "build_response")
    graph.add_edge("build_response", END)
    graph.add_edge("build_failed_response", END)

    return graph.compile()


ui_customization_graph = build_ui_customization_graph()