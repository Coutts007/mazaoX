"""Architecture guard (ADR-002/004): what one domain app may use from another.

Rules, enforced on every module under apps/ (tests included unless stated):
1. A domain never imports another domain's models.
2. Across domains only these modules may be imported: services, selectors, contracts, and identity.permissions.
   (Never api, models, matching, media, handlers, ... of another domain.)
3. In non-test code, a name used from another domain's services/selectors must be listed in that module's __all__
   (the module's public contract).
4. `core` never imports any domain app.
Domains talk to notifications and audit only through events (core.events), never by importing them.
"""

import ast
import importlib
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[2]
APPS_DIR = BACKEND / "apps"
ALLOWED_MODULES = {"services", "selectors", "contracts"}
ALLOWED_EXTRA = {("identity", "permissions")}
# Only these domains may be reached by publishing events; nobody imports their services for that purpose.
EVENT_ONLY = {"notifications": {"notify"}, "audit": {"record"}}


def _modules():
    for path in sorted(APPS_DIR.rglob("*.py")):
        rel = path.relative_to(APPS_DIR)
        if len(rel.parts) < 2 or "migrations" in rel.parts:
            continue
        yield path, rel, rel.parts[0], "tests" in rel.parts or path.name.startswith("test_") or path.name == "conftest.py"


def _cross_imports(tree, own):
    """Yield (module_path_parts, imported_names, node) for every import of another domain."""
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            parts = node.module.split(".")
            if parts[0] != "apps" or len(parts) < 2:
                continue
            if len(parts) == 2:  # from apps.orders import selectors
                if parts[1] != own:
                    for alias in node.names:
                        yield [*parts, alias.name], [], node, alias
            elif parts[1] != own:
                yield parts, [a.name for a in node.names], node, None
        elif isinstance(node, ast.Import):
            for alias in node.names:
                parts = alias.name.split(".")
                if parts[0] == "apps" and len(parts) >= 3 and parts[1] != own:
                    yield parts, [], node, alias


def _public_names(domain, module):
    mod = importlib.import_module(f"apps.{domain}.{module}")
    return set(getattr(mod, "__all__", ()))


@pytest.fixture(scope="module")
def django_ready():
    import django
    django.setup()


def test_domains_do_not_import_each_others_models_or_internals():
    problems = []
    for path, rel, own, is_test in _modules():
        tree = ast.parse(path.read_text())
        for parts, _names, node, _alias in _cross_imports(tree, own):
            if len(parts) < 3:
                problems.append(f"{rel}:{node.lineno} imports {'.'.join(parts)}")
                continue
            domain, module = parts[1], parts[2]
            if module == "models":
                problems.append(f"{rel}:{node.lineno} imports {domain}.models")
            elif is_test:
                continue
            elif module not in ALLOWED_MODULES and (domain, module) not in ALLOWED_EXTRA:
                problems.append(f"{rel}:{node.lineno} imports internal module {domain}.{module}")
    assert problems == []


def test_cross_domain_names_are_in_the_public_contract(django_ready):
    problems = []
    for path, rel, own, is_test in _modules():
        if is_test:
            continue
        tree = ast.parse(path.read_text())
        aliases = {}  # local alias -> (domain, module)
        for parts, names, node, alias in _cross_imports(tree, own):
            if len(parts) == 3 and parts[2] in ("services", "selectors") and alias is not None:
                aliases[alias.asname or alias.name] = (parts[1], parts[2])  # from apps.x import services
            elif len(parts) == 3 and parts[2] in ("services", "selectors"):
                for name in names:  # from apps.x.services import name
                    if name not in _public_names(parts[1], parts[2]):
                        problems.append(f"{rel}:{node.lineno} uses {parts[1]}.{parts[2]}.{name}, which is not in __all__")
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id in aliases:
                domain, module = aliases[node.value.id]
                if node.attr not in _public_names(domain, module):
                    problems.append(f"{rel}:{node.lineno} uses {domain}.{module}.{node.attr}, which is not in __all__")
    assert problems == []


def test_business_domains_reach_notifications_and_audit_only_through_events():
    problems = []
    for path, rel, own, is_test in _modules():
        if is_test or own in ("notifications", "audit"):
            continue
        for parts, names, node, alias in _cross_imports(ast.parse(path.read_text()), own):
            if len(parts) >= 3 and parts[1] in EVENT_ONLY and parts[2] in ("services",):
                problems.append(f"{rel}:{node.lineno} imports {parts[1]}.services; publish an event instead")
    assert problems == []


def test_core_does_not_depend_on_domain_apps():
    problems = []
    for path in sorted((BACKEND / "core").rglob("*.py")):
        if "tests" in path.parts or "migrations" in path.parts:
            continue
        for node in ast.walk(ast.parse(path.read_text())):
            module = getattr(node, "module", None) if isinstance(node, ast.ImportFrom) else None
            names = [a.name for a in node.names] if isinstance(node, ast.Import) else []
            if (module and module.startswith("apps")) or any(n.startswith("apps") for n in names):
                problems.append(f"{path.relative_to(BACKEND)}:{node.lineno}")
    assert problems == []
