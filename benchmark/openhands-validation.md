# OpenHands workflow validation

Validation for [#22](https://github.com/layer8labs8/ci-agent-audit/issues/22),
run on 2026-11-04 against scanner commit
`948337374b10760451f6ca80b726e66adfb4feae` (0.1.4).

Eight workflow files from seven public repositories were read at fixed
commits. Only the scanner ran: no sampled workflow, OpenHands process,
container, or model was started. The sample is small and selected for
invocation variety, not an estimate of accuracy across GitHub. Project
names and original workflow contents are omitted as requested by the
issue. All added benchmark workflows are made up.

## Unchanged public snapshots

“Recognized” means that the scanner's action/CLI matcher identifies an
`openhands-resolver` step. It does not require a finding: a recognized
agent can produce no warnings for a particular trigger, permission, or gate.

| Sample | Invocation | Recognition and findings |
| --- | --- | --- |
| 01 | `OpenHands/extensions/plugins/pr-review@<commit>` | Recognized; no findings |
| 02 | `OpenHands/extensions/plugins/qa-changes@main` | Recognized; AIA004 |
| 03 | `OpenHands/extensions/plugins/vulnerability-remediation@main` | Recognized; AIA004 |
| 04 | `OpenHands/extensions/plugins/issue-duplicate-checker@<commit>` | Not recognized, consistent with the current Cloud exclusion; no findings |
| 05 | Job-level `uses: All-Hands-AI/OpenHands/.github/workflows/openhands-resolver.yml@main` | Not followed or recognized; no findings |
| 06 | The same remote reusable-workflow form in another repository | Not followed or recognized; no findings |
| 07 | Two `uv run openhands --headless --always-approve ... --file ...` commands | Neither CLI step recognized; no findings |
| 08 | Two direct `openhands --headless ... -t "..."` commands | Both CLI steps recognized; no findings, including no AIA002 |

AIA004 in samples 02 and 03 is the warning for a moving action reference.
It is not evidence of a successful attack. No sampled workflow produced
AIA001 or AIA002. This does not establish that implicit PR/issue fetches,
prompt files, downloaded specifications, or agent behavior are safe: those
were not executed or fully traced.

No unchanged `release-notes` caller was found in the release-notes code
search used for this sample. Its existing synthetic
`openhands-release-notes-in-shell` case still detects AIA010. The four
plugin names are covered by that case, the existing `pr-review` case,
and the new `qa-changes` and `vulnerability-remediation` cases; this is
synthetic coverage, not four kinds of real-world validation.

## CLI misses and controls

Removing only `uv run` from a separate copy of sample 07 makes both CLI
steps recognizable. It still does not produce AIA002 for the approval
flags. The scanner's runner prefix list does not include `uv run`, and
its OpenHands dangerous-argument signature only contains `--no-sandbox`.

The upstream CLI's [confirmation argument definitions](https://github.com/OpenHands/OpenHands-CLI/blob/283c6ac3610f4299f405f7389f65766dcb83e12a/openhands_cli/argparsers/util.py)
define `--always-approve` and its alias `--yolo` as approval bypasses.
The [main parser](https://github.com/OpenHands/OpenHands-CLI/blob/283c6ac3610f4299f405f7389f65766dcb83e12a/openhands_cli/argparsers/main_parser.py)
also documents that `--headless` auto-approves actions and accepts initial
text via `--task`/`-t` or a file via `--file`/`-f`. These source checks support
the expected scanner warnings; the CLI itself was not run.

Four new `gap: true` cases isolate the misses:

- `openhands-cli-through-uv-run`: AIA001 is missed for an untrusted task
  behind the `uv run` wrapper. The paired direct command is detected.
- `openhands-cli-always-approve`: AIA002 is missed for `--always-approve`.
- `openhands-cli-yolo`: AIA002 is missed for its `--yolo` alias.
- `openhands-cli-headless`: AIA002 is missed for headless auto-approval.

The flag cases use static tasks so AIA001 does not hide a missing AIA002.
The `uv run` and alias cases are controlled examples: the unchanged sample
07 used prompt files, not inline issue text, and no sampled workflow used
`--yolo`. The cases expose scanner limitations, not demonstrated attacks
against the sampled projects.

Six new covered cases check the two other plugin names and direct CLI
task text, step env, a file written by a preceding step, and a step output.
The plugin cases use declared token inputs and expect AIA006 on a synthetic
public issue trigger without a gate or egress restriction. They forbid
AIA001/AIA002/AIA009; a plain plugin call does not show explicit attacker
text flowing into instructions in the caller's YAML. No invented `prompt`
input is added to plugins that do not declare one.

Three negative controls cover a static task, help/version queries, and
unrelated text in a preceding step's env. They produce no forbidden
findings; the static agent runs allow the separate AIA006 warning.
This is not a false-positive estimate for other inputs or rules.

## Remote reusable workflows and Cloud

The two real reusable-workflow callers do not explicitly forward issue
body text through `with:`. Their quiet results cannot demonstrate whether
an input would be safe inside the remote workflow. The existing synthetic
`remote-reusable-workflow` benchmark was rerun: it still misses AIA001
when issue body text is forwarded as a task to a remote workflow. The
scanner does not download remote workflows, even when a job's `uses:`
starts with a known OpenHands repository name. That name alone does not
reveal the callee's inputs, guards, or permissions, so this contribution
records the existing limitation without adding a generic warning or
pretending to have analyzed the remote implementation.

The [Cloud dispatcher action definition](https://github.com/OpenHands/extensions/blob/60f8f85c253314c7d815adf96ff5a7d41376ddcc/plugins/issue-duplicate-checker/action.yml)
confirms that `issue-duplicate-checker` calls OpenHands Cloud through a
helper script. Keeping it outside the runner-agent signature avoids
implying local agent execution. This exclusion is not a safety claim:
token scope, cloud instructions, and returned model text may deserve
separate coverage. Defining that Cloud threat model and signature is a
follow-up decision; no “safe Cloud workflow” benchmark is added here.

## Reproduce the regression checks

After installing the development dependencies from CONTRIBUTING.md:

```bash
pytest -q
python -m ci_agent_audit.cli validate-signatures
python tools/run_benchmark.py
python -m ci_agent_audit.cli scan .github/workflows --fail-on medium
```

The contribution adds 13 cases: six covered positives, three negative
controls, and four known misses. The full benchmark now has 122 cases,
91 expected detections found, seven missed, and no forbidden findings:
92.9% recall and 100% precision on this self-authored dataset. The prior
109-case dataset had three misses and 96.6% recall. The lower recall comes
from adding known misses; the scanner engine and signatures are unchanged.
Tests for `gap: true` cases pass by reproducing a miss, not by detecting it.

The original public snapshots are intentionally not committed. The
synthetic benchmark is reproducible without network access; this report
records the dated, fixed-snapshot observations rather than claiming that
the original sample selection can be recreated from the report alone.
