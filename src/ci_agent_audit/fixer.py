"""Deterministic auto-fix engine (`--fix`) for common AI CI/CD workflow misconfigurations."""

from __future__ import annotations

from pathlib import Path
import re

import yaml

from ci_agent_audit.models import ActionSignature
from ci_agent_audit.signatures_loader import load_signatures


def apply_fixes_to_file(
    file_path: Path, signatures: list[ActionSignature] | None = None
) -> tuple[bool, list[str]]:
    """Apply safe, deterministic fixes to a workflow file and return (modified, applied_descriptions)."""
    # Bytes keep the file's own line endings, which text mode would normalize on Windows
    original = file_path.read_bytes().decode("utf-8")
    updated, descriptions = apply_fixes_to_text(original, signatures)
    if updated != original:
        file_path.write_bytes(updated.encode("utf-8"))
        return True, descriptions
    return False, []


def apply_fixes_to_text(
    content: str, signatures: list[ActionSignature] | None = None
) -> tuple[str, list[str]]:
    """Apply deterministic security remediations to workflow YAML text."""
    descriptions: list[str] = []
    text = content
    newline = "\r\n" if "\r\n" in content else "\n"

    # Fix 1 (AIA004): Only upgrade explicit three-component release versions.
    # Branches, SHAs, floating tags and prereleases need a human decision.
    for signature in load_signatures() if signatures is None else signatures:
        minimum = signature.min_safe_version
        if not minimum or not re.fullmatch(r"[vV]?\d+\.\d+\.\d+", minimum):
            continue
        target = minimum.lstrip("vV")
        minimum_parts = tuple(int(part) for part in target.split("."))

        def _upgrade_action(match: re.Match[str]) -> str:
            prefix, version = match.group(1), match.group(2)
            parts = tuple(int(part) for part in version.lstrip("vV").split("."))
            if parts < minimum_parts:
                descriptions.append(
                    f"Upgraded vulnerable {prefix}@{version} to @v{target} (AIA004)"
                )
                return f"{prefix}@v{target}"
            return match.group(0)

        for prefix in signature.action_prefixes:
            text = re.sub(
                r"(?<![\w./-])("
                + re.escape(prefix)
                + r")@([vV]?\d+\.\d+\.\d+)(?=[\s'\"#,\]}]|$)",
                _upgrade_action,
                text,
            )

    # Fix 2 (AIA003): Remove wildcard allowed_non_write_users / allowed_bots: "*"
    wildcard_users_re = re.compile(
        r"^([ \t]*(allowed_non_write_users|allowed_bots)[ \t]*:[ \t]*)(?:['\"]\*['\"]|\*)([ \t]*(?:#[^\r\n]*)?)(\r?)$",
        re.MULTILINE,
    )

    def _clear_wildcard(match: re.Match[str]) -> str:
        descriptions.append(
            f"Cleared insecure `{match.group(2)}: '*'` wildcard (AIA003)"
        )
        return f'{match.group(1)}""{match.group(3)} # Fixed by ci-agent-audit (AIA003){match.group(4)}'

    text = wildcard_users_re.sub(_clear_wildcard, text)

    # Fix 3 (AIA005): Replace `permissions: write-all` with least-privilege `contents: read`
    write_all_re = re.compile(
        r"^([ \t]*)permissions[ \t]*:[ \t]*['\"]?write-all['\"]?[ \t]*(?=\r?$)",
        re.MULTILINE | re.IGNORECASE,
    )

    def _scope_permissions(match: re.Match[str]) -> str:
        descriptions.append(
            "Replaced `permissions: write-all` with `contents: read` (AIA005)"
        )
        indent = match.group(1)
        return f"{indent}permissions:{newline}{indent}  contents: read"

    text = write_all_re.sub(_scope_permissions, text)

    # Never hand back a workflow that the fixes turned into invalid YAML
    try:
        yaml.safe_load(text)
    except yaml.YAMLError:
        return content, []

    return text, descriptions
