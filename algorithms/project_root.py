from pathlib import Path


PROJECT_MARKERS = (
    "AGENTS.md",
    "rules/algorithm_sources.json",
    "scripts/verify_environment.sh",
)


def resolve_project_root(anchor: Path) -> Path:
    for candidate in (anchor.resolve(), *anchor.resolve().parents):
        if all((candidate / marker).exists() for marker in PROJECT_MARKERS):
            return candidate
    raise RuntimeError("could not resolve AI BLUE CHIP STOCKS project root")


ROOT = resolve_project_root(Path(__file__).resolve())
