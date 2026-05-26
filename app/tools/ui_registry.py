SUPPORTED_COMPONENTS = {
    "dashboardGrid": {
        "description": "Main dashboard grid layout.",
        "allowed_props": {
            "columns": [1, 2, 3],
            "gap": ["small", "medium", "large"],
        },
    },
    "profileCard": {
        "description": "Shows user profile summary.",
        "allowed_props": {
            "variant": ["default", "compact", "detailed"],
            "show_avatar": [True, False],
        },
    },
    "knowledgeSummaryCard": {
        "description": "Shows knowledge base summary.",
        "allowed_props": {
            "variant": ["default", "minimal", "detailed"],
            "show_tags": [True, False],
        },
    },
    "recentActivityCard": {
        "description": "Shows recent user activity.",
        "allowed_props": {
            "variant": ["default", "minimal", "timeline"],
            "limit": "integer from 1 to 20",
        },
    },
    "quickActionsCard": {
        "description": "Shows quick actions.",
        "allowed_props": {
            "variant": ["default", "minimal"],
            "actions": ["addKnowledge", "viewProfile", "openSearch"],
        },
    },
}


SUPPORTED_THEME_TOKENS = {
    "mode": ["light", "dark", "system"],
    "primary_color": ["blue", "purple", "green", "slate"],
    "density": ["compact", "comfortable", "spacious"],
    "radius": ["small", "medium", "large"],
}


def list_supported_components() -> dict:
    return {
        "components": SUPPORTED_COMPONENTS,
        "theme_tokens": SUPPORTED_THEME_TOKENS,
    }