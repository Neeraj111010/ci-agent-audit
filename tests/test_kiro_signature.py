"""Kiro's short legacy alias must only identify an actual chat command."""

import pytest

from ci_agent_audit.rules import _match_cli_signatures
from ci_agent_audit.signatures_loader import load_signatures


@pytest.mark.parametrize(
    "command",
    [
        'kiro-cli chat --no-interactive "$BODY"',
        'q chat --trust-all-tools "$BODY"',
        'kiro chat "$BODY"',
    ],
)
def test_kiro_chat_entry_points(command):
    assert "kiro-cli" in {
        s.id for s in _match_cli_signatures(command, load_signatures())
    }


@pytest.mark.parametrize(
    "command",
    [
        'q -H "SELECT * FROM data.csv"',
        "q login",
        "kiro-cli login",
        "kiro-cli settings chat.enableWorkflows true",
        'python tools/q/run.py "$BODY"',
    ],
)
def test_non_agent_commands_are_not_kiro(command):
    assert "kiro-cli" not in {
        s.id for s in _match_cli_signatures(command, load_signatures())
    }
