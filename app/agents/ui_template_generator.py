from dataclasses import dataclass

from pydantic import ValidationError

from app.core.json_utils import extract_json_object
from app.core.prompt_loader import load_skill_file
from app.llm.factory import get_llm_client
from app.schemas.ui_template import UITemplate
from app.tools.ui_registry import list_supported_components
import logging
from app.core.config import settings


@dataclass
class TemplateGenerationAttempt:
    template: UITemplate | None
    raw_response: str
    error: str | None


def _build_base_system_prompt(current_template: UITemplate | None = None) -> str:
    skill_instructions = load_skill_file("skills/ui_customization_skill.md")
    supported_registry = list_supported_components()

    current_template_text = (
        current_template.model_dump_json(indent=2)
        if current_template is not None
        else "No current template provided."
    )

    return f"""
{skill_instructions}

You are generating a UI template for a React-based knowledge-base application.

You must obey these rules:

1. Return only valid JSON.
2. Do not return markdown.
3. Do not return explanations.
4. Do not include comments.
5. Do not generate raw HTML.
6. Do not generate JavaScript.
7. Do not generate React code.
8. Only use supported components and supported props.
9. The root component must be dashboardGrid.
10. The JSON must match this shape:

{{
  "page": "dashboard",
  "theme": {{
    "mode": "light | dark | system",
    "primary_color": "blue | purple | green | slate",
    "density": "compact | comfortable | spacious",
    "radius": "small | medium | large"
  }},
  "tree": {{
    "type": "dashboardGrid",
    "props": {{
      "columns": 1,
      "gap": "medium"
    }},
    "children": []
  }}
}}

Supported registry:
{supported_registry}

Current template:
{current_template_text}
"""


def _parse_template_response(raw_response: str) -> UITemplate:
    json_data = extract_json_object(raw_response)
    return UITemplate.model_validate(json_data)


def generate_ui_template_attempt(
    user_message: str,
    page: str,
    current_template: UITemplate | None = None,
) -> TemplateGenerationAttempt:
    system_prompt = _build_base_system_prompt(current_template)

    user_prompt = f"""
User request:
{user_message}

Page:
{page}

Generate the safest matching UI template JSON.
"""

    llm_client = get_llm_client()
    raw_response = llm_client.generate_text(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
    )
    
    logger = logging.getLogger(__name__)
    if settings.log_model_output:
        logger.debug(
            "model_raw_response",
            extra={
                "raw_response": raw_response,
            },
        )
    
    try:
        template = _parse_template_response(raw_response)
        return TemplateGenerationAttempt(
            template=template,
            raw_response=raw_response,
            error=None,
        )
    except (ValueError, ValidationError) as exc:
        return TemplateGenerationAttempt(
            template=None,
            raw_response=raw_response,
            error=str(exc),
        )


def repair_ui_template_attempt(
    user_message: str,
    page: str,
    invalid_response: str,
    validation_error: str,
    current_template: UITemplate | None = None,
) -> TemplateGenerationAttempt:
    system_prompt = _build_base_system_prompt(current_template)

    user_prompt = f"""
The previous model output was invalid.

Original user request:
{user_message}

Page:
{page}

Invalid model output:
{invalid_response}

Validation error:
{validation_error}

Repair the output.

Rules:
- Return only valid JSON.
- Do not return markdown.
- Do not explain the fix.
- Do not add unsupported components.
- Do not add unsupported props.
- Keep the user's design intention.
"""

    llm_client = get_llm_client()
    raw_response = llm_client.generate_text(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
    )
    logger = logging.getLogger(__name__)
    if settings.log_model_output:
        logger.debug(
            "model_raw_response",
            extra={
                "raw_response": raw_response,
            },
        )

    try:
        template = _parse_template_response(raw_response)
        return TemplateGenerationAttempt(
            template=template,
            raw_response=raw_response,
            error=None,
        )
    except (ValueError, ValidationError) as exc:
        return TemplateGenerationAttempt(
            template=None,
            raw_response=raw_response,
            error=str(exc),
        )