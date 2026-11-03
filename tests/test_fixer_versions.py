"""Signature-driven remediation must preserve refs whose ordering is unknown."""

import pytest

from ci_agent_audit.fixer import apply_fixes_to_file, apply_fixes_to_text
from ci_agent_audit.signatures_loader import parse_signature_dict


def signature(minimum="2.3.4"):
    return parse_signature_dict(
        {
            "id": "example",
            "name": "Example",
            "vendor": "Example",
            "description": "Synthetic test action",
            "action_prefixes": ["example/agent", "example/renamed-agent"],
            "min_safe_version": minimum,
        }
    )


@pytest.mark.parametrize("prefix", ["example/agent", "example/renamed-agent"])
@pytest.mark.parametrize("version", ["1.99.99", "v2.3.3", "V2.0.0"])
def test_fixer_upgrades_signature_minimum(prefix, version):
    source = f"uses: '{prefix}@{version}' # keep comment\n"
    fixed, notes = apply_fixes_to_text(source, [signature()])
    assert fixed == f"uses: '{prefix}@v2.3.4' # keep comment\n"
    assert len(notes) == 1
    assert apply_fixes_to_text(fixed, [signature()]) == (fixed, [])


@pytest.mark.parametrize(
    "version",
    [
        "main",
        "v2",
        "v2.3",
        "0123456789abcdef",
        "v2.3.4",
        "v3.0.0",
        "v2.3.3-rc.1",
        "v2.3.3+build",
        "release/2.3.3",
        "v2.3.3/branch",
    ],
)
def test_fixer_leaves_unordered_and_safe_refs(version):
    source = f"uses: example/agent@{version}\n"
    assert apply_fixes_to_text(source, [signature()]) == (source, [])


def test_fixer_does_not_match_another_owner():
    source = "uses: other/example/agent@v1.0.0\n"
    assert apply_fixes_to_text(source, [signature()]) == (source, [])


@pytest.mark.parametrize("minimum", [None, "main", "2.3", "2.3.4-rc.1"])
def test_fixer_skips_unusable_minimum(minimum):
    source = "uses: example/agent@v1.0.0\n"
    assert apply_fixes_to_text(source, [signature(minimum)]) == (source, [])


def test_file_fixer_uses_supplied_signatures_and_preserves_crlf(tmp_path):
    path = tmp_path / "workflow.yml"
    path.write_bytes(b"uses: example/agent@v1.0.0\r\n")
    modified, notes = apply_fixes_to_file(path, [signature()])
    assert modified and notes
    assert path.read_bytes() == b"uses: example/agent@v2.3.4\r\n"


def test_cli_fix_uses_extra_signatures(tmp_path, capsys):
    from ci_agent_audit.cli import main

    signatures = tmp_path / "signatures"
    signatures.mkdir()
    (signatures / "example.yaml").write_text(
        "id: example\nname: Example\nvendor: Example\ndescription: Test\n"
        "action_prefixes: [example/agent]\nmin_safe_version: '2.3.4'\n"
    )
    workflow = tmp_path / "workflow.yml"
    workflow.write_text(
        "jobs:\n  test:\n    steps:\n      - uses: example/agent@v1.0.0\n"
    )
    main(["scan", str(workflow), "--fix", "--signatures-dir", str(signatures)])
    assert "example/agent@v2.3.4" in workflow.read_text()
    assert "[FIXED]" in capsys.readouterr().err
