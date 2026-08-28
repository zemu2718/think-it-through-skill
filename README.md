<div align="center">
  <img src="assets/hero.png" alt="Think It Through — converging paths lead to one decision-changing question and a reversible real-world experiment" width="100%">

# 想清楚 · Think It Through

**Do not let AI flawlessly execute the wrong task.**

An open Agent Skill that first understands what you truly want to achieve or protect, finds the one answer most likely to change the decision, and turns it into one testable, bounded, reversible real-world experiment.

[简体中文](README.zh-CN.md) · [Product](PRODUCT.md) · [Requirements](REQUIREMENTS.md) · [Contributing](CONTRIBUTING.md)

</div>

> [!IMPORTANT]
> The current source contract is **v0.1.3**. Its real multi-turn model behavior, native-control rendering, and real-user UX evaluation have not been run; their status is `not_run`. A wireframe, Markdown, unit tests, and old scores are not substitutes for observed tool-call evidence. The published model-behavior evidence remains the frozen v0.1 snapshot. Automatic discovery also missed its frozen holdout gate (1/8 positive recall; 8/8 negative specificity), so invoke `/think-it-through` explicitly and do not present natural-language auto-loading or other-client compatibility as established.

## The problem

AI is very good at completing explicit requests. That becomes wasteful when the requested action does not serve the real goal:

- writing a launch plan before anyone has shown willingness to pay;
- continuing a project because stopping would make prior work feel wasted;
- optimizing a message when the partnership boundary itself is unclear;
- producing more options when one missing answer would reorder all of them.

Think It Through inserts a restrained checkpoint before consequential action:

```text
Surface task → Real objective → Decision question
```

It does not make the choice for you. It helps you see what you are really trying to resolve, what the current judgment depends on, and how reality can correct the direction without overcommitment.

## See the experience before installing

<img src="assets/demo-flow.svg" alt="Share the issue, choose a relevant direction or say it in your own words, clarify the real question and one key answer together, then take one step through a real-world experiment." width="100%">

```text
Hear me first
→ Give me easy directions, and let me say it my way
→ Help me clarify the real problem
→ Ask only one key question
→ Give me a clear but revisable judgment
→ Help me take only the next step
```

### 1. First, help you say what you really want

The Skill does not see a product idea and immediately assume revenue, growth, or a startup. When the objective is unclear, it handles only the largest current unknown. If the host provides `AskUserQuestion` or an equivalent selection tool, the Skill prioritizes an actual native multi-select and lets you use host free text to add or correct the objective.

```text
You: I want to build a chat app like QQ. What do you think?

Think It Through: You already have a product direction, but what you most want it
for will change the rest of the judgment. I will not assume that objective yet.

Native multi-select:
Select any that apply, or use host free text to add or correct. Which outcomes matter here?

☐ Practice and create a portfolio piece
☐ Solve a real problem for a particular group
☐ Try to turn it into income
☐ I have not worked that out yet
```

The checkboxes are a readable wireframe of native-control semantics, not Markdown the model should emit. When the control is available, the Skill must actually call it. Equivalent text choices appear only when the tool is unavailable, fails, or is declined. This is not a fixed button template; choices change with the issue and serve only the largest current unknown:

- a choice alone is accepted;
- matching choice and text are merged;
- when choice and text conflict, free text wins;
- rejecting the offered choices is accepted directly—no re-clicking;
- the product never creates its own “Other” option; host-provided `Other` is equal free-text input and is not counted as a product choice.

### 2. Only after the objective is clear, recommend how to think

The Skill decides internally whether basic analysis is enough, then considers two-sided steelmanning, a pre-mortem, and one specialist card that fills a distinct gap. After deduplication, it recommends only 0–3 useful angles rather than handing you a full method catalog.

What you see is “plain language (stable method name) + why it helps now”:

```text
- Make the current direction and strongest alternative as strong as possible,
  then test both with comparable evidence standards (Two-sided steelmanning):
  this avoids merely defending the current preference.

- Look ahead at how a candidate path is most likely to fail, then trace the
  earliest signals and controllable boundary (Pre-mortem): this avoids learning
  too late that the validation order was wrong.

Native multi-select:
Basic analysis is always included. Select any methods to keep, or use host free
text to add, remove, replace, or correct.

☐ Two-sided steelmanning
☐ Pre-mortem
☐ Object calibration
```

Combination semantics stay stable:

- **Add X** = keep the current combination and add X;
- **Remove X** = remove only X;
- **Replace Y with X** = remove Y and add X.

After confirmation, the Skill echoes the final combination naturally—for example, “Good, we’ll use object calibration + two-sided steelmanning”—instead of exposing an internal technical checklist. Adding background, opening an adjustment view, browsing candidates, or accepting a default selection is not confirmation.

### 3. Answer only one genuinely decisive question

The analysis does not simulate a panel or dump frameworks one by one. Every confirmed method must add distinct value, and all of it is synthesized into one question:

> Which single answer, if different, would most likely change the option ranking, direction, or whether to continue?

“What are your budget, deadline, and minimum return?” contains one question mark but needs three answers, so it fails the contract.

- when the answer set is naturally finite and mutually exclusive, an available host control is actually called as a native single-select with 2–4 product choices and host free text for adding or correcting;
- when the answer is open, the Skill does not call a selection control, invent candidate answers, or constrain your direct response;
- either way, there is one answer slot and one question mark at the end of the question; native question text is included in this check and option labels contain no question marks;
- the Skill may reuse numbers you supplied, but it cannot invent a sample size, deadline, amount, people count, ratio, success threshold, or future commitment length in stage A.

After asking, it stops and waits rather than answering on your behalf.

### 4. After your answer, get a judgment and one real-world experiment

Even if you answer “I don’t know,” answer partially, or decline to answer, the Skill does not start another questionnaire. It incorporates the uncertainty and uses one state appropriate to the work:

| Not yet executed | Already executed |
| --- | --- |
| Hold / Small test / Proceed conditionally / Proceed | Continue / Adjust / Pause / Stop |

The user-facing result is natural:

```text
Based on what we know, I recommend: …

The simple reason: …

### Do this one thing first

Action: …
Observe: …
Reassess: …

[This direction fits]
[The direction fits, but change the next step]
[I disagree]
[Set this aside]

You can also say what does not fit reality.
```

Action, observation, and reassessment test one hypothesis; they are not three tasks. Boundaries first reuse numbers you supplied. Every decision-relevant number introduced by the Skill must be labeled locally as a **suggested boundary**, **heuristic starting point**, or supported by a reliable source.

Feedback after the judgment is declarative. Stage B does not call `AskUserQuestion` or any equivalent question control and contains no question mark. It does not request more information or authorize a tool, private data access, or external action. A correction, new fact, or disagreement starts a new round; agreement or setting it aside ends the round and waits.

> [!NOTE]
> The interaction above is a **v0.1.3 specification wireframe**, not a model-generated transcript. Checkboxes and radio buttons represent expected native-control semantics; square brackets represent text fallback or declarative B feedback. Static content cannot prove that a tool was actually called or that real-model behavior or UX has passed.

## Methods stay transparent without becoming homework

Basic analysis always runs in the background. Method routing is the Skill’s selection mechanism, not another method for the user to choose. Beyond two-sided steelmanning and pre-mortem, the seven specialist cards are:

- separate users, payers, affected parties, and cost bearers (**Object calibration**);
- find the constraint that moves the whole system (**System bottleneck**);
- check whether an old strategy still fits current conditions (**Stage fit**);
- find where limited resources should concentrate and where commitment stops (**Resource leverage**);
- make responsibilities, inputs, decision rights, and exit terms testable (**Boundary contracts**);
- fit information, evidence, channel, and feedback to audience and purpose (**Communication fit**);
- use actual outcomes to revisit continue, adjust, pause, or stop (**Evidence loop**).

Usually no more than one specialist card is recommended; zero is a valid result. Stable names remain visible for transparency and precise adjustment, but users do not need to learn the catalog.

## How the hidden contract keeps the Skill restrained

R, A, B, and method routing stay backstage. They constrain the Skill rather than becoming user homework:

| Internal state | Required work | Waiting boundary |
| --- | --- | --- |
| **R-align** | Help express the real objective; use native multi-select when available, with host free text. | Wait for the user to add or correct the objective. |
| **R-method** | Recommend only after the objective is clear; use native multi-select for composable methods. | Wait for explicit adoption, adjustment, or basic-only choice. |
| **A** | Run confirmed angles; use single-select for finite mutually exclusive answers and free answer for open ones. | End with the single final question mark. |
| **B** | Absorb the answer; give one judgment and one experiment without a question control. | End the round; never execute automatically. |

For factual lookup, clear low-risk execution, pure creation, and entertainment, the Skill should stay out of the way. Urgent safety situations receive immediate protective guidance instead of a longer decision process.

## When it should trigger

The most reliable current path is explicit `/think-it-through`. It fits important choices that are uncertain, costly, hard to reverse, or already consuming resources:

- “Is this worth doing?”
- “I am stuck between A and B.”
- “Test this idea before I commit six months.”
- “Does the action I asked AI to perform actually serve my goal?”
- “Should I continue, adjust, pause, or stop?”
- “Find the one question that would change this decision.”
- “I need a decision-support skill with trade-off analysis, steelmanning, a pre-mortem, and a reversible experiment.”
- “还没想清楚 / 值不值得做 / A 还是 B / 帮我检验这个想法 / 下一步最该做什么。”

Useful directory search language includes **decision support**, **decision framing**, **trade-off analysis**, **pre-mortem**, **two-sided steelman**, **real-world experiment**, **reversible next step**, and **continue adjust pause stop**. This repository does not claim to appear for a particular query before external indexing is actually observed.

### When it should not trigger

- factual lookup or definitions of decision methods;
- a decided, clearly specified, low-risk, reversible execution task;
- pure creation or entertainment;
- code review, FMEA, research, or project planning without an unresolved user choice;
- urgent safety situations.

Precision matters as much as recall. A decision Skill that activates whenever “trade-off,” “pause,” or “pre-mortem” appears is not useful.

## Installation

### Personal — available in all local projects

```bash
git clone https://github.com/zemu2718/think-it-through-skill.git
test ! -e ~/.claude/skills/think-it-through
mkdir -p ~/.claude/skills
cp -R think-it-through-skill/skills/think-it-through ~/.claude/skills/
```

### Project — available only in one repository

Run from the target project root after cloning this repository:

```bash
test ! -e .claude/skills/think-it-through
mkdir -p .claude/skills
cp -R /path/to/think-it-through-skill/skills/think-it-through .claude/skills/
```

If `think-it-through` is already installed, remove or rename the existing directory first instead of merging versions. If the top-level `~/.claude/skills/` or `.claude/skills/` directory did not exist when the session started, restart Claude Code after creating it.

Invoke directly:

```text
/think-it-through
```

The Skill needs no network access, API key, account, executable script, or remote dependency. The source-directory approach follows Claude Code’s personal and project Skill locations. End-to-end client installation of the `.skill` archive and compatibility with other clients are not yet claimed.

Official Claude Code reference: [Extend Claude with skills](https://code.claude.com/docs/en/slash-commands).

## Evaluation and evidence boundaries

The repository separates three questions:

1. **Discovery:** does the description auto-trigger and avoid close non-examples?
2. **Behavior after loading:** does a real model obey the multi-turn contract?
3. **User experience:** does the conversation actually help users align objectives, correct misunderstandings, and reach actionable judgment?

### Frozen v0.1 behavior snapshot

The results below bind only three fixed, three-turn v0.1 scenarios. Each was run once with the Skill and once against an independent no-Skill baseline. They do not establish v0.1.3 behavior.

| Metric | With Skill | Without Skill | Delta |
| --- | ---: | ---: | ---: |
| Contract assertion pass rate | **100.0%** | 57.4% | +0.43 |
| 20-point semantic rubric | **98.3%** | 38.3% | +0.60 |
| Runs passing the full semantic gate | **3/3** | 0/3 | — |

Exact transcripts, per-assertion evidence, rubric evidence, SHA-256 bindings, and aggregate JSON are in [`benchmarks/behavior-v0.1/`](benchmarks/behavior-v0.1/). The [SaaS validation](skills/think-it-through/examples/saas-validation.md) and [partnership-boundary](skills/think-it-through/examples/partnership-boundary.md) files preserve the same v0.1 outputs verbatim; their transcript bodies were not rewritten into v0.1.3 examples.

> [!CAUTION]
> This is a contract-regression snapshot, not a general answer-quality ranking or evidence of statistical significance. There is one run per scenario/configuration. The runtime-reported model name was not independently verified through API metadata, and comparable token and timing data were unavailable.

### v0.1.3 static contract and UX scenarios

v0.1.3 includes a mechanical grader, versioned fixtures, and an independent nine-dimension UX rubric. These define and regress the contract; they are not model outputs or real-user results. UX status is explicitly `not_run`:

- [`ux-evals.json`](skills/think-it-through/evals/ux-evals.json)
- [`ux-rubric.md`](skills/think-it-through/evals/ux-rubric.md)

Deterministic checks use Python 3.12 and PyYAML:

```bash
uv run --python 3.12 --with pyyaml python -m unittest discover -s scripts -p 'test_*.py' -v
uv run --python 3.12 --with pyyaml python scripts/validate_repo.py
```

The frozen discovery holdout passed **9/16 overall**: all eight negatives stayed inactive, but only one of eight positives loaded the Skill, missing the gate. The result was not fed back into the same-version description. Details are in [`benchmarks/trigger-v0.1/`](benchmarks/trigger-v0.1/).

## Safety, privacy, and control

Think It Through is an instruction-only Skill. It does not need web access or private data by default.

It treats these as independent permissions:

1. invoke a capability or tool;
2. access private data;
3. act externally—send, publish, purchase, delete, or modify.

One never implies another. Confirming a thinking angle, clicking a control, or selecting stage-B feedback is not permission to use tools, access data, or act externally.

The Skill:

- does not replace medical, legal, investment, or emergency professional help;
- does not provide manipulation, deception, intimidation, tracking, or coercion tactics;
- distinguishes confirmed facts, reasonable inferences, hypotheses, and unknowns;
- keeps the final choice and every external action with you.

See [`SECURITY.md`](SECURITY.md) and [`skills/think-it-through/references/safety-boundaries.md`](skills/think-it-through/references/safety-boundaries.md).

## Transparent method provenance

Seven specialist method cards are neutral adaptations of selected MIT-licensed files from a fixed revision of `SamadhiFire/xinqingnian-maoxuan-skill`. Character imitation, political and military framing, coercive tactics, and unsupported authority claims were removed. Three other candidate repositories were reviewed and not adopted.

Every adopted card records its repository, fixed commit, exact file, license, and material changes. Read [`docs/third-party-audit.md`](docs/third-party-audit.md) and [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md).

## Project structure

```text
skills/think-it-through/
├── SKILL.md                    # Core state contract
├── references/                 # Interaction, analysis, methods, safety, authorization
├── examples/                   # Frozen v0.1 exact transcripts
├── evals/                      # Behavior, UX, trigger, and routing definitions
├── LICENSE
└── THIRD_PARTY_NOTICES.md

benchmarks/behavior-v0.1/       # Public transcripts and frozen behavior evidence
benchmarks/trigger-v0.1/        # Discovery results, including the failed holdout
scripts/                        # Versioned grading, tests, validation, packaging
assets/                         # Original project visuals
```

The single maintenance source is `skills/think-it-through/`. A project-level `.claude/skills/think-it-through/` is only a local installation copy. Temporary workspaces, viewers, caches, and development configuration are excluded from the package.

## Contributing

Useful contributions include realistic decision cases, close trigger negatives, more natural and restrained language, method-routing tests, accessibility improvements, and reproducible validation fixes. New frameworks or personas need distinct decision value—not a longer feature list.

Start with [`CONTRIBUTING.md`](CONTRIBUTING.md). Report security issues privately through [`SECURITY.md`](SECURITY.md).

## License

Think It Through is released under the [MIT License](LICENSE). Third-party attribution is retained in [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md).
