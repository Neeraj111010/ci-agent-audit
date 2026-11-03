# PR-Agent workflow validation

Validation for [#23](https://github.com/layer8labs8/ci-agent-audit/issues/23),
run on 2026-11-03 against scanner commit
`55ec551660a403bbc1212f1e1ab6d6b3eaa02d0b` (0.1.4).

Only the scanner ran. No sampled workflow, PR-Agent process, container, or
model was started. Project names and original workflow contents are omitted
as requested by the issue; the benchmark examples are made up.

## Public workflow snapshots

Seven workflow files from seven public repositories were read at fixed
commits. This is a small convenience sample, not an accuracy estimate.

| Sample | Invocation | Result |
| --- | --- | --- |
| 01 | `the-pr-agent/pr-agent@v0.41.0`, step env configuration | Recognized |
| 02 | `uses: docker://pragent/pr-agent@sha256:...` | Not recognized |
| 03 | `the-pr-agent/pr-agent@main`, static extra instructions in env | Recognized |
| 04 | Shell script that invokes the agent separately | Not recognized; custom scripts are a documented limit |
| 05 | `Codium-ai/pr-agent@main`, reusable workflow with step env | Recognized |
| 06 | `qodo-ai/pr-agent@main`, step env configuration | Recognized |
| 07 | `qodo-ai/pr-agent@main`, step env configuration | Recognized |

The five recognized snapshots had no AIA001 or AIA002 findings. Manual
inspection found no explicit untrusted-text interpolation into their agent
instructions and no `--auto_approve` flag. The other findings were version,
permission, or egress warnings (AIA004–AIA006). Those warnings are not evidence
of a successful attack. AIA001 being quiet does not establish that fetched PR
content is safe: the scanner does not inspect the agent's internals.

## Controlled variants

These are modified copies or synthetic examples, separate from the seven
unchanged snapshots:

- Adding `github.event.pull_request.body` to
  `env.pr_reviewer.extra_instructions` in each of the five recognized
  workflows produced AIA001.
- Replacing the owner in otherwise identical input with `The-PR-Agent`,
  `qodo-ai`, or `Codium-ai` produced the same rule IDs, severities, job,
  and tool ID.
- Synthetic `pr-agent` CLI input carrying comment text and
  `--auto_approve` produced AIA001 and AIA002.
- Static instructions, a trusted PR number, the CLI without dangerous flags,
  and untrusted env on an unrelated preceding step stayed quiet for
  AIA001/AIA002. The benchmark allows the separate egress warning AIA006.
- Passing PR text through a previous step output into the action's env
  produced AIA001.

No AIA001/AIA002 false alarm was observed in those controls. This is not a
claim about all other rules or workflow forms. CLI checks were synthetic;
neither a real CLI-based workflow nor PR-Agent's flag semantics was executed.

## Reproducible misses

Three new `gap: true` cases capture AIA001 misses:

- `pr-agent-workflow-env-instructions`: untrusted instructions supplied in
  workflow-level `env:`, inherited by the action.
- `pr-agent-job-env-instructions`: the same input supplied in job-level
  `env:`.
- `pr-agent-docker-action`: a direct Docker action with untrusted instructions
  in step env. The synthetic tag form reproduces the unrecognized Docker
  action shape seen in sample 02, which used a digest.

The inherited cases use `PR_REVIEWER__EXTRA_INSTRUCTIONS`, the nested
environment configuration form supported by PR-Agent's Dynaconf settings.
The scanner already tracks workflow/job env taint, but the action env sink
loop inspects only variables declared on the step. The Docker form does not
match any action prefix. These cases expose scanner gaps; they do not claim
an exploitable vulnerability in a sampled project.

The scanner engine is unchanged. Marking the misses as gaps keeps them in
the reported recall rather than presenting them as passing detections.

## Run the checks

After installing the development dependencies from CONTRIBUTING.md:

```bash
pytest -q
python -m ci_agent_audit.cli validate-signatures
python tools/run_benchmark.py
python -m ci_agent_audit.cli scan .github/workflows --fail-on medium
```

The added cases are part of the normal benchmark tests. Nine are covered
cases (five positive and four negative controls); three are known gaps.
The full benchmark has 105 cases, 80 expected rule detections found,
7 missed, and no forbidden findings: 92.0% recall and 100% precision on
this self-authored dataset. Adding misses lowers recall without changing
scanner behavior.
