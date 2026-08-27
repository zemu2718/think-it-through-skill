<div align="center">
  <img src="assets/hero.png" alt="Think It Through — converging paths lead to one decision-changing question and a reversible next step" width="100%">

# 想清楚 · Think It Through

**Do not let AI flawlessly execute the wrong task.**

An open Agent Skill that uncovers the real objective, finds the one answer most likely to change the decision, and turns it into one testable, bounded, reversible next step.

[简体中文](README.zh-CN.md) · [Product](PRODUCT.md) · [Requirements](REQUIREMENTS.md) · [Contributing](CONTRIBUTING.md)

</div>

> [!IMPORTANT]
> The core Skill, behavior evaluation, generated PNG assets, package inspection, unpacked quick validation, official `skills-ref` validation, and isolated Claude Code source installation are complete. Automatic discovery did **not** pass its frozen holdout (1/8 positive recall; 8/8 negative specificity), and end-to-end `.skill` archive installation in a client is not verified. For v0.1, invoke `/think-it-through` explicitly; do not present automatic loading or other-client compatibility as established.

## The problem

AI is very good at completing explicit requests. That becomes wasteful when the requested action does not serve the real goal:

- writing a launch plan before anyone has shown willingness to pay;
- continuing a project because stopping would make prior work feel wasted;
- optimizing a message when the partnership boundary itself is unclear;
- producing more options when one missing answer would reorder all of them.

Think It Through inserts a deliberate checkpoint before consequential action:

```text
Surface task → Real objective → Decision question
```

It does not make the choice for you. It helps you see what you are actually choosing, what could overturn the current view, and how to learn without overcommitting.

## See the interaction before installing

<img src="assets/demo-flow.svg" alt="R: recommend an analysis and wait. A: run only confirmed methods and ask exactly one question. B: give one conditional judgment and one bounded next step." width="100%">

| Stage | What the Skill does | Waiting boundary |
| --- | --- | --- |
| **R — Recommend** | Reframes the surface task, tentative real objective, and decision question; recommends the smallest useful analysis. | Waits for your explicit confirmation or adjustment. |
| **A — Analyze** | Runs basic analysis plus only the methods you confirmed; finds the highest-sensitivity variable. | Ends with exactly one independent question. |
| **B — Judge** | Absorbs your answer—even “I don't know”—and gives one conditional judgment plus one bounded next step. | Ends the round; it does not execute for you. |

The [SaaS validation transcript](skills/think-it-through/examples/saas-validation.md) and [partnership-boundary transcript](skills/think-it-through/examples/partnership-boundary.md) are exact `with_skill` outputs from the fixed behavior evaluation—not rewritten success stories.

<details>
<summary><strong>Short real transcript: from “write a launch plan” to a payment test</strong></summary>

**User:** I built a scheduling SaaS for small businesses. No unfamiliar customer has paid. I wanted a launch plan and another three months of development. Should I do that?

**R:** The Skill tentatively reframes the choice as “continue development and promotion, or first test whether the current version solves a problem worth paying for,” recommends three methods, presents four routes, and waits.

**User:** Proceed as recommended.

**A:** It compares the strongest competing judgments, traces the failure mechanism, and ends with one question: how many of ten matched unfamiliar businesses would need to pay at a real acceptable price to justify three more months?

**User:** If fewer than two pay, I will not continue development.

**B — Small test:** For seven days, offer the unchanged version at one real price to ten matched businesses with no prior relationship. Reassess on day seven: at least two payments support conditional progression; fewer than two stop the three-month commitment.

[Read the exact Chinese transcript and formal grades →](benchmarks/behavior-v0.1/eval-1-saas-misalignment/with_skill/transcript.md)

</details>

## What makes it different

### One question means one answer slot

The question in stage A is not a disguised questionnaire. “What are your budget, deadline, and minimum return?” has one question mark but three independent answers, so it fails the contract.

The Skill asks instead:

> Which single answer, if different, would most likely change the option ranking, direction, or whether to continue?

### Methods require your confirmation

Basic analysis is always present. Optional methods are recommended only when they add independent value:

- **Two-sided steelmanning** — test the strongest competing judgments using comparable evidence standards;
- **Pre-mortem** — trace a concrete future failure through 1–3 causal chains and early signals;
- **Neutral specialist cards** — clarify objects, bottlenecks, stage fit, resource leverage, boundaries, communication fit, or evidence from work already done.

You can accept the recommendation, change it, use basic analysis only, or add background. Adding background never silently confirms a method.

### The outcome is a decision, not a framework dump

After your answer, the Skill uses exactly one state:

| Not yet executed | Already executed |
| --- | --- |
| Hold / Small test / Proceed conditionally / Proceed | Continue / Adjust / Pause / Stop |

The next step is one action with a time or cost bound, success signal, stop or pivot condition, and re-evaluation point—not a new backlog.

## When it should trigger

Use `/think-it-through`, or describe the issue naturally, when an important choice is uncertain, costly, hard to reverse, or already consuming resources:

- “Is this worth doing?”
- “I am stuck between A and B.”
- “Test this idea before I commit six months.”
- “Does the action I asked AI to perform actually serve my goal?”
- “Should I continue, adjust, pause, or stop?”
- “Find the one question that would change this decision.”
- “I need a decision-support skill with trade-off analysis, steelmanning, a pre-mortem, and a reversible next step.”
- “还没想清楚 / 值不值得做 / A 还是 B / 帮我检验这个想法 / 下一步最该做什么。”

These phrases are also useful search language for Skill directories: **decision support**, **decision framing**, **trade-off analysis**, **pre-mortem**, **two-sided steelman**, **reversible next step**, and **continue adjust pause stop**. This repository does **not** claim to appear in a particular external index before that is observed after publication.

The Skill is designed for product and business, career, team, partnership, relationship boundaries, high-cost choices, and review of work already in motion.

### When it should not trigger

It should stay out of the way for:

- factual lookup or a definition of a decision method;
- clear, low-risk, reversible execution after the decision is made;
- pure creation or entertainment;
- code review, FMEA, research, or project planning without an unresolved user choice;
- urgent safety situations—give immediate protective guidance instead.

This boundary matters as much as recall. A decision Skill that activates on every use of “trade-off”, “pause”, or “pre-mortem” is not useful.

## Installation

The verified source layout below follows Claude Code's documented personal and project Skill locations. The folder name becomes the direct command, while `description` enables automatic loading for matching requests.

### Personal — available in all local projects

```bash
git clone https://github.com/zemu2718/think-it-through-skill.git
test ! -e ~/.claude/skills/think-it-through
mkdir -p ~/.claude/skills
cp -R think-it-through-skill/skills/think-it-through ~/.claude/skills/
```

### Project — available only in one repository

Run this from that repository root after cloning this repository beside or within your workspace:

```bash
test ! -e .claude/skills/think-it-through
mkdir -p .claude/skills
cp -R /path/to/think-it-through-skill/skills/think-it-through .claude/skills/
```

If `think-it-through` is already installed, remove or rename that existing directory first rather than merging two versions. Claude Code detects edits to an existing Skill directory live. If the top-level `~/.claude/skills/` or `.claude/skills/` directory did not exist when the session started, restart Claude Code after creating it.

Invoke it directly:

```text
/think-it-through
```

Or ask naturally—for example, “I am about to invest six months in this idea; help me test whether that serves the real goal.”

The Skill itself requires no network access, API key, account, executable script, or remote dependency. It is currently verified only as a source Skill in **local Claude Code 2.1.245** using an isolated project copy of the documented directory layout: both explicit `/think-it-through` invocation and a matching natural-language request loaded the Skill and stopped at stage R. The `.skill` archive has been built, inspected, unpacked, and quick-validated, but end-to-end archive installation and other clients are not yet claimed.

Official Claude Code reference: [Extend Claude with skills](https://code.claude.com/docs/en/slash-commands).

## Evaluation

The repository tests two separate questions:

1. **Discovery:** does the description trigger for consequential decision-support requests and avoid close non-examples?
2. **Behavior after loading:** does the Skill obey the multi-turn R → A → B contract better than a no-skill baseline?

### Current behavior snapshot

Three fixed, three-turn scenarios were each run once with the Skill and once against a strictly independent no-Skill baseline.

| Metric | With Skill | Without Skill | Delta |
| --- | ---: | ---: | ---: |
| Contract assertion pass rate | **100.0%** | 57.4% | +0.43 |
| 20-point semantic rubric | **98.3%** | 38.3% | +0.60 |
| Runs passing the full semantic gate | **3/3** | 0/3 | — |

The full semantic gate requires no serious failure, at least 18/20, and full marks for question quality, stage-B judgment, and user control/safety. Exact transcripts, per-assertion evidence, rubric evidence, SHA-256 bindings, and aggregate JSON are in [`benchmarks/behavior-v0.1/`](benchmarks/behavior-v0.1/).

> [!CAUTION]
> This is a regression snapshot, not a general answer-quality ranking or evidence of statistical significance. There is only one run per scenario/configuration. The runtime-reported model name was not independently verified through API metadata. Comparable token and timing data were unavailable and are not reported. The no-Skill outputs often contained useful advice; the measured difference is specifically about the documented R → A → B product contract and rubric.

Behavior fixtures additionally cover background-without-confirmation, method cancellation, “I don't know”, executed work, anti-manipulation, factual and low-risk bypasses, emergencies, external-capability degradation, independent permission scopes, and all seven specialist-card routing boundaries.

Deterministic repository checks use Python 3.12 and PyYAML:

```bash
uv run --python 3.12 --with pyyaml python -m unittest discover -s scripts -p 'test_*.py' -v
uv run --python 3.12 --with pyyaml python scripts/validate_repo.py
```

Automatic discovery was run once on the 16-case dev set, then the seven dev failures informed one description revision. A second dev run was not allowed because it would exceed the session-wide 50-agent limit. The revised description was frozen at SHA-256 `f89f3d1f…e4c6f3d3` before the untouched 16-case holdout ran. Holdout passed **9/16 overall**: all eight negatives stayed inactive, but only one of eight positives loaded the Skill. This misses the discovery gate, and the holdout was not fed back into v0.1 tuning. Exact results and limitations are in [`benchmarks/trigger-v0.1/`](benchmarks/trigger-v0.1/).

## Safety, privacy, and control

Think It Through is an instruction-only Skill. It does not need to browse the web or read private data by default.

It treats these as independent permissions:

1. invoke a capability or tool;
2. access private data;
3. act externally—send, publish, purchase, delete, or modify.

One never implies another. Confirming an analysis method is not tool permission. Permission to browse is not permission to read private files or contact anyone. A request made before analysis is not automatically reused as authorization after the judgment.

The Skill:

- does not replace medical, legal, investment, or emergency professional help;
- does not provide manipulation, deception, intimidation, tracking, or coercion tactics;
- distinguishes confirmed facts, reasonable inferences, hypotheses, and unknowns;
- keeps the final choice and any external action with you.

See [`SECURITY.md`](SECURITY.md) and [`skills/think-it-through/references/safety-boundaries.md`](skills/think-it-through/references/safety-boundaries.md).

## Transparent method provenance

Seven specialist method cards are neutral adaptations of selected MIT-licensed files from a fixed revision of `SamadhiFire/xinqingnian-maoxuan-skill`. Character imitation, political and military framing, coercive tactics, and unsupported authority claims were removed. Three other candidate repositories were reviewed and not adopted.

Every adopted card records its repository, fixed commit, exact file, license, and material changes. Read [`docs/third-party-audit.md`](docs/third-party-audit.md) and [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md).

## Project structure

```text
skills/think-it-through/
├── SKILL.md                    # Core state contract
├── references/                 # Analysis, methods, safety, authorization
├── examples/                   # Exact passing multi-turn transcripts
├── evals/                      # Behavior, trigger, and routing definitions
├── LICENSE
└── THIRD_PARTY_NOTICES.md

benchmarks/behavior-v0.1/       # Public transcripts and formal behavior evidence
benchmarks/trigger-v0.1/        # Automatic-discovery results, including failed holdout
scripts/                        # Deterministic grading and validation
assets/                         # Original project visuals
```

Temporary evaluation workspaces, the local viewer, caches, and packaged release artifacts are intentionally excluded from source control.

## Contributing

Useful contributions are realistic decision cases, close trigger negatives, simpler instructions, method-routing tests, accessibility improvements, and reproducible validation fixes. New frameworks or personas need evidence of independent decision value—not a longer feature list.

Start with [`CONTRIBUTING.md`](CONTRIBUTING.md). Report security issues privately through [`SECURITY.md`](SECURITY.md).

## License

Think It Through is released under the [MIT License](LICENSE). Third-party attribution is retained in [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md).
