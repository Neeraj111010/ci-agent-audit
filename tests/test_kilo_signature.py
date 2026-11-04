"""Kilo's agent command and approval flag must not match unrelated operations."""

import re

import pytest

from ci_agent_audit.rules import _match_cli_signatures
from ci_agent_audit.signatures_loader import load_signatures


@pytest.mark.parametrize(
    "command",
    [
        'kilo run "$BODY"',
        'npx @kilocode/cli run "$BODY"',
        'npx @kilocode/cli@1.0.0 run "$BODY"',
    ],
)
def test_kilo_run_commands(command):
    assert "kilo-code" in {
        s.id for s in _match_cli_signatures(command, load_signatures())
    }


@pytest.mark.parametrize(
    "command",
    [
        "kilo auth login",
        "kilo agent list",
        "npx @kilocode/cli auth login",
        "npx @kilocode/cli@1.0.0 auth login",
        "kilo run --help",
    ],
)
def test_kilo_management_commands_are_not_agent_sinks(command):
    assert "kilo-code" not in {
        s.id for s in _match_cli_signatures(command, load_signatures())
    }


@pytest.mark.parametrize(
    ("command", "unsafe"),
    [
        ('kilo run --auto "fix tests"', True),
        ('npx @kilocode/cli run --auto "fix tests"', True),
        ('npx @kilocode/cli@1.0.0 run --auto "fix tests"', True),
        ('kilo run --automatic "fix tests"', False),
        ('kilo run "review"\ngh pr merge --auto', False),
    ],
)
def test_auto_flag_is_tied_to_kilo_run(command, unsafe):
    signature = next(s for s in load_signatures() if s.id == "kilo-code")
    assert (
        any(re.search(p.pattern, command) for p in signature.dangerous_arg_patterns)
        is unsafe
    )
