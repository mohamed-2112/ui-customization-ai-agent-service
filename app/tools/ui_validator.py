from app.schemas.ui_template import UINode, UITemplate


MAX_TREE_DEPTH = 4
MAX_TREE_NODES = 20


def validate_ui_template(template: UITemplate) -> list[str]:
    errors: list[str] = []

    if template.page != "dashboard":
        errors.append("Only the dashboard page is currently supported.")

    if template.tree.type != "dashboardGrid":
        errors.append("The root component must be 'dashboardGrid'.")

    node_count = 0

    def validate_node(node: UINode, depth: int, path: str) -> None:
        nonlocal node_count

        node_count += 1

        if node_count > MAX_TREE_NODES:
            errors.append(f"Template has too many nodes. Maximum is {MAX_TREE_NODES}.")
            return

        if depth > MAX_TREE_DEPTH:
            errors.append(f"Template is too deeply nested at {path}.")
            return

        if node.type != "dashboardGrid" and node.children:
            errors.append(
                f"Component '{node.type}' at {path} cannot have children."
            )

        for index, child in enumerate(node.children):
            validate_node(child, depth + 1, f"{path}.children[{index}]")

    validate_node(template.tree, depth=1, path="tree")

    return errors