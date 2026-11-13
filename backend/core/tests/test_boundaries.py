"""Architecture guard (ADR-002): a domain app must never import another domain's models."""

import ast
from pathlib import Path

APPS_DIR = Path(__file__).resolve().parents[2] / "apps"


def _violations():
    found = []
    for path in APPS_DIR.rglob("*.py"):
        rel = path.relative_to(APPS_DIR)
        if len(rel.parts) < 2 or "migrations" in rel.parts:
            continue
        own = rel.parts[0]
        for node in ast.walk(ast.parse(path.read_text())):
            modules = []
            if isinstance(node, ast.ImportFrom) and node.module:
                modules.append(node.module)
                if node.module == "apps":
                    modules += [f"apps.{a.name}" for a in node.names]
            elif isinstance(node, ast.Import):
                modules += [a.name for a in node.names]
            for module in modules:
                parts = module.split(".")
                if parts[0] == "apps" and len(parts) >= 3 and parts[1] != own and parts[2] == "models":
                    found.append(f"{rel}: imports {module}")
    return found


def test_no_cross_domain_model_imports():
    assert _violations() == []
