from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent


def load_skill_file(relative_path: str) -> str:
    skill_path = BASE_DIR / relative_path

    if not skill_path.exists():
        raise FileNotFoundError(f"Skill file not found: {skill_path}")

    return skill_path.read_text(encoding="utf-8")