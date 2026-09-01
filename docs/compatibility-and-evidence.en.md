# Compatibility and evidence

[简体中文](compatibility-and-evidence.md)

This document explains public status. It is not a second compatibility or behavior contract. Machine-readable facts live in [`compatibility/profile.json`](../compatibility/profile.json) and [`compatibility/runtime-support.json`](../compatibility/runtime-support.json); see [`REQUIREMENTS.md`](../REQUIREMENTS.md) and [`SECURITY.md`](../SECURITY.md) for normative behavior, safety, and acceptance boundaries.

## Current release

The stable release is [`v0.3.0`](https://github.com/zemu2718/think-it-through-skill/releases/tag/v0.3.0), backed by an immutable Git tag, a GitHub Release, the downloadable [`think-it-through.skill`](https://github.com/zemu2718/think-it-through-skill/releases/download/v0.3.0/think-it-through.skill), and [`SHA256SUMS`](https://github.com/zemu2718/think-it-through-skill/releases/download/v0.3.0/SHA256SUMS). Maintained development continues on [`main`](https://github.com/zemu2718/think-it-through-skill/tree/main/skills/think-it-through).

Release status describes a reviewed product contract and deterministic acceptance path; it does not certify every client or promote unrun compatibility levels.

## Understanding L0–L5

“Open format,” “installer discovery,” “exact installation,” “runtime loading,” “model behavior,” and “native capabilities” are different claims.

| Level | What it means | Current public status |
| --- | --- | --- |
| L0 | Format validation | `not_run` in the public runtime matrix |
| L1 | Installer discovery | `not_run` |
| L2 | Exact installation | `not_run` |
| L3 | Real runtime loading | `not_run` |
| L4 | Real text behavior | `not_run` |
| L5 | Real native capabilities | `not_run` |

[`compatibility/profile.json`](../compatibility/profile.json) defines levels, allowed evidence types, and promotion policy. [`compatibility/runtime-support.json`](../compatibility/runtime-support.json) records per-runtime status under [`runtime-support.schema.json`](../compatibility/runtime-support.schema.json) and [`evidence.schema.json`](../compatibility/evidence.schema.json).

## Installer targets are not runtime validation

v0.3.0 provides a portable text baseline for hosts that load an Agent Skills directory and follow text instructions. Eight installer target mappings are maintained for Claude Code, Codex, Cursor, Gemini CLI, Hermes Agent, OpenClaw, OpenCode, and CodeBuddy / WorkBuddy. Unlisted compatible hosts can use the same text contract through their own Skill-directory convention.

A mapping, successful file copy, or portable contract is not a verified runtime. Static CI, schemas, fixtures, graders, and diagrams can establish contracts; they cannot prove a real model run, natural-language discovery, or native host experience.

## Discovery and contextual checkpoints

Automatic discovery is not the reliable entry point: the frozen v0.1 holdout scored **9/16 overall—1/8 positives triggered, while 8/8 negatives stayed out**. See the exact [trigger evidence and limitations](../benchmarks/trigger-v0.1/README.md). Historical [v0.1 behavior evidence](../benchmarks/behavior-v0.1/README.md) covers only three fixed scenarios with one run per configuration; it does not establish v0.2.0 or v0.3.0 behavior.

The v0.3.0 formal contract defines a lightweight contextual checkpoint only when the Skill is already loaded, no formal flow is active, and a conversation crosses into project initiation, direction selection, major investment, continued escalation, or result reassessment. Real multi-turn status remains `not_run`; the contract does not prove natural-language discovery, automatic loading, or reliable mid-conversation triggering. Explicit `/think-it-through` in Claude Code remains the reliable entry.

## How feedback becomes evidence

Use the [installation and runtime feedback form](https://github.com/zemu2718/think-it-through-skill/issues/new?template=install-or-runtime-feedback.yml) for public, reproducible observations. Include the exact release tag or source commit from `git rev-parse HEAD`, runtime name and version, OS, install method and destination, minimal reproduction steps, and expected versus actual behavior. Redact API keys, tokens, private conversations, private file content, and personal paths.

A report is a lead for reproduction and improvement. It can update [`compatibility/runtime-support.json`](../compatibility/runtime-support.json) only after it is bound to an exact source revision and runtime version, reproduced where needed, redacted, reviewed, and accepted as approved evidence. Report vulnerabilities privately through [`SECURITY.md`](../SECURITY.md).

## Machine sources

- Compatibility levels and evidence policy: [`compatibility/profile.json`](../compatibility/profile.json)
- Current runtime status: [`compatibility/runtime-support.json`](../compatibility/runtime-support.json)
- Status and evidence schemas: [`runtime-support.schema.json`](../compatibility/runtime-support.schema.json), [`evidence.schema.json`](../compatibility/evidence.schema.json)
- Frozen discovery evidence: [`benchmarks/trigger-v0.1/`](../benchmarks/trigger-v0.1/README.md)
- Frozen historical behavior evidence: [`benchmarks/behavior-v0.1/`](../benchmarks/behavior-v0.1/README.md)
- Normative behavior, safety, and acceptance contract: [`REQUIREMENTS.md`](../REQUIREMENTS.md)
