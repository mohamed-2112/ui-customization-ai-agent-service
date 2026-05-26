from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


PageName = Literal["dashboard"]

ThemeMode = Literal["light", "dark", "system"]
PrimaryColor = Literal["blue", "purple", "green", "slate"]
Density = Literal["compact", "comfortable", "spacious"]
Radius = Literal["small", "medium", "large"]

ComponentType = Literal[
    "dashboardGrid",
    "profileCard",
    "knowledgeSummaryCard",
    "recentActivityCard",
    "quickActionsCard",
]


class ThemeConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: ThemeMode = "system"
    primary_color: PrimaryColor = "blue"
    density: Density = "comfortable"
    radius: Radius = "medium"


class DashboardGridProps(BaseModel):
    model_config = ConfigDict(extra="forbid")

    columns: Literal[1, 2, 3] = 2
    gap: Literal["small", "medium", "large"] = "medium"


class ProfileCardProps(BaseModel):
    model_config = ConfigDict(extra="forbid")

    variant: Literal["default", "compact", "detailed"] = "default"
    show_avatar: bool = True


class KnowledgeSummaryCardProps(BaseModel):
    model_config = ConfigDict(extra="forbid")

    variant: Literal["default", "minimal", "detailed"] = "default"
    show_tags: bool = True


class RecentActivityCardProps(BaseModel):
    model_config = ConfigDict(extra="forbid")

    variant: Literal["default", "minimal", "timeline"] = "default"
    limit: int = Field(default=5, ge=1, le=20)


class QuickActionsCardProps(BaseModel):
    model_config = ConfigDict(extra="forbid")

    variant: Literal["default", "minimal"] = "default"
    actions: list[Literal["addKnowledge", "viewProfile", "openSearch"]] = Field(
        default_factory=lambda: ["addKnowledge", "openSearch"]
    )


COMPONENT_PROPS_MODELS = {
    "dashboardGrid": DashboardGridProps,
    "profileCard": ProfileCardProps,
    "knowledgeSummaryCard": KnowledgeSummaryCardProps,
    "recentActivityCard": RecentActivityCardProps,
    "quickActionsCard": QuickActionsCardProps,
}


class UINode(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: ComponentType
    props: dict[str, Any] = Field(default_factory=dict)
    children: list["UINode"] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_props_for_component(self) -> "UINode":
        props_model = COMPONENT_PROPS_MODELS[self.type]

        validated_props = props_model.model_validate(self.props)

        # Normalize props after validation.
        # This means defaults are added automatically.
        self.props = validated_props.model_dump()

        return self


class UITemplate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    page: PageName
    theme: ThemeConfig
    tree: UINode


class UICustomizationDraftRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: str = Field(min_length=3, max_length=1000)
    page: PageName = "dashboard"


class UICustomizationDraftResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["draft_created", "failed_validation"]
    explanation: str
    draft_template: UITemplate | None = None
    validation_errors: list[str] = Field(default_factory=list)

    agent_run_id: str
    draft_id: str | None = None

    model_provider: str
    model_name: str
    attempts: int = 1
    
    
class UIDraftDetailsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    draft_id: str
    agent_run_id: str
    user_id: str
    page: PageName
    status: str
    template: UITemplate


class UIApplyDraftResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["applied"]
    message: str
    draft_id: str
    applied_template_id: str
    page: PageName
    version: int
    template: UITemplate
    
    
class UIActiveTemplateResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    active_template_id: str
    user_id: str
    page: PageName
    status: str
    version: int
    template: UITemplate