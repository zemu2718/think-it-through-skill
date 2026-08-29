<div align="center">
  <img src="assets/hero.png" alt="Think It Through — paths converge on one decision-changing answer, then one reassessable real-world evidence loop" width="100%">

# 想清楚 · Think It Through

**Do not let AI flawlessly execute the wrong task.**

An open Agent Skill that clarifies what you are actually trying to resolve, finds the one answer most likely to change the decision, escalates to evidence or independent participation only when it adds value and you authorize it, and ends with one synthesized judgment, one primary real-world evidence loop, and a copyable decision snapshot.

[简体中文](README.zh-CN.md) · [Product](PRODUCT.md) · [Requirements](REQUIREMENTS.md) · [Changelog](CHANGELOG.md) · [Contributing](CONTRIBUTING.md)

</div>

> [!IMPORTANT]
> **v0.2.0 is the current release.** The reliable entry point is explicit `/think-it-through` invocation in Claude Code. The text protocol is the cross-host baseline. Native controls, search, additional agents, private data, persistence, and external actions are used only when the current session exposes the capability, routing conditions are met, and the corresponding consent is granted; actual execution is established by traces and receipts. An Adapter defines protocol mapping, not native compatibility certification for that host.

## The problem

AI is very good at completing explicit requests. That becomes wasteful when the requested action does not serve the real objective:

- writing a launch plan before anyone has shown willingness to pay;
- continuing because stopping would make prior work feel wasted;
- optimizing a message when the partnership boundary is unclear;
- producing more options when one missing answer would reorder them;
- relying on model memory when a current market fact would reverse the choice—or producing a full research report when research would not;
- asking several agents to repeat one analysis and treating the majority as confidence.

Think It Through inserts a restrained decision-and-evidence protocol before and after consequential action:

```text
Surface task → Real objective → Decision question
→ One decision-sensitive answer
→ Evidence or participation only when needed and authorized
→ Judgment → Primary real-world evidence loop → Reassessment
```

It does not decide values for you, and it does not treat process, methods, or agent count as the result. It helps identify whether the missing input is your objective or boundary, a public fact, an independent challenge, a real person's commitment, or evidence that only behavior can provide.

## See the experience before installing

<img src="assets/demo-flow.svg" alt="Share the issue, align the objective, answer one decisive question, add evidence or participation only when needed and authorized, then receive a judgment, decision snapshot, and reassessment entry." width="100%">

```text
R-align: clarify what you want to achieve or protect
→ R-method: understand and confirm the minimum useful thinking angles
→ A: answer only one decision-changing question
→ Gate-routing: add evidence or participation only when needed and authorized
→ B: receive judgment, a primary evidence loop, a decision snapshot, and feedback
```

A Gate is conditional, not a mandatory fourth stage. The defaults are zero external calls, the current main agent only, a conversation-only snapshot, and no change to the external world.

### 1. First, clarify what you actually want

The Skill does not see a product idea and assume revenue, growth, or a startup. When the objective is unclear, it handles only the largest current unknown.

If the host provides `AskUserQuestion` or an equivalent tool, answer shape selects the surface:

- compatible directions → native multi-select;
- a genuinely finite mutually exclusive boundary → native single-select;
- an open answer that cannot be pre-enumerated → direct free text.

```text
You: I want to build a chat app like QQ. What do you think?

Think It Through: You already have a product direction, but what you want it to achieve will change the rest of the judgment.

I will not assume that objective yet.

Native multi-select:
Select any that apply, or add or correct in your own words.

Which outcomes do you mainly want from this?

☐ Practice and turn it into a portfolio piece
☐ Solve a specific problem for a group
☐ Explore commercial potential
☐ Build it for an existing team or community
```

The checkboxes are a readable wireframe of native-control semantics, not Markdown the model should emit. When the control is available, the Skill must actually call it. Ordinary numbered text appears only when the control is unavailable, fails, or is declined.

Free text wins when it conflicts with a selection. The product does not create an “Other” option; host-provided `Other` is alternative free input. Compatible objectives are merged without forcing a ranking. Another alignment question is allowed only when a real user-provided exclusive constraint would change the decision.

### 2. Once the objective is clear, understand and select methods in one place

Basic analysis is always included. The system then considers two-sided steelmanning, a pre-mortem, and at most one specialist card that fills a distinct gap. After deduplication, it presents only 0–3 useful angles.

Every formal candidate carries:

```text
stable ID + formal method name + recommendation state + current value
```

A native multi-select should read like this:

```text
Which additional thinking angles should this round keep?

☐ Object calibration (Recommended)
  Separate users, payers, and cost bearers to decide whose demand must be tested first.

☐ Two-sided steelmanning (Recommended)
  Test the current direction and strongest alternative with comparable evidence standards.
```

When the host supports option descriptions, the value stays inside the same option. Otherwise it appears immediately next to the option. Text fallback still preserves the formal name, recommendation state, and current value. The body must not fully explain methods and then repeat names alone in the control.

`Recommended` is not confirmation. Only the selection submitted this round or explicit free text establishes the final combination:

- **Add X:** retain the current combination and add X;
- **Remove X:** remove only X;
- **Replace Y with X:** remove Y and add X.

A default selection, browsing candidates, a historical preference, or adding background is not confirmation. Unconfirmed or removed methods cannot run covertly.

### 3. Answer only one genuinely decisive question

Confirmed methods are synthesized instead of being reported card by card or staged as an expert panel:

> Which single answer, if different, would most likely change the option ranking, direction, or whether to continue?

- a naturally finite mutually exclusive answer actually uses native single-select;
- an open answer uses free text without invented candidates;
- either way, there is one independent answer slot, then the Skill waits;
- the Skill may reuse numbers you supplied, but stage A cannot invent a sample size, deadline, amount, people count, ratio, or success threshold.

### 4. Escalate evidence or participation only when it can change the judgment

After your answer, the Skill routes the remaining unknown to the right source:

| Unknown | Default treatment |
| --- | --- |
| Objective, boundary, or risk tolerance | Keep with the user; search and agents cannot answer it |
| Current public market, price, regulation, or policy fact | Consider the Evidence Gate |
| Non-duplicative, verifiable, stoppable independent work | Consider the Participation Gate |
| Authority, budget, commitment, customer behavior, professional responsibility | Draft a minimal request for the real person; do not send by default |
| Something only real response can reveal | Put it in the primary real-world evidence loop |

#### Evidence Gate

Before bounded research, one continuous consent unit states:

- the decision and the precise evidence question;
- market, region, time, and subject scope;
- stop condition and source requirements;
- provider, read-only status, and data boundary;
- relative cost, latency, and failure fallback.

Research runs only when an external fact would change ranking, continuation, or commitment; acquisition is bounded and worth its cost; and a specific capability consent is granted. Results retain sources, dates, supporting and opposing evidence, conflicts, and gaps. A refusal, failure, or unresolved source conflict preserves the unknown, lowers commitment, and continues to stage B rather than inventing an answer.

#### Participation Gate

The default is one main agent. Additional agents are proposed only for non-duplicative, verifiable, stoppable work with clear incremental value.

The user controls a **total participating-agent cap that includes the main agent**:

```text
Available additional cap = max(0, user total cap - 1)
Actual additional = min(independent tasks, user cap, product cap, host cap, cost budget)
Actual total = 1 + actually started additional agents
```

Before delegation, one choice unit shows the concrete tasks, main/additional/total counts, data scope, public-web and private-data status, relative cost and latency, and failure fallback. The user may accept, reduce the count, stay single-agent, or narrow the work in free text.

Additional agents receive minimum context and cannot recursively delegate. The main agent deduplicates sources, exposes conflicts, and synthesizes instead of voting. A receipt reports planned, started, completed, failed, and actual total counts.

Permission for multiple agents is not permission for public web access, private data, or external action.

### 5. Receive judgment, one primary evidence loop, and a snapshot

Even if you answer “I don’t know,” decline a Gate, or a capability fails, the Skill does not start another questionnaire or wait forever. It proceeds to stage B:

| Not yet executed | Already executed |
| --- | --- |
| Hold / Small test / Proceed conditionally / Proceed | Continue / Adjust / Pause / Stop |

A complete result naturally contains:

```text
Current judgment and recommended direction
→ Key basis and fact / inference / hypothesis / unknown boundaries
→ Validity conditions and reversal signals
→ One primary real-world evidence loop
→ A copyable decision snapshot
→ Four-way feedback
```

The primary evidence loop tests one core hypothesis without turning the answer into a stack of label-first fields:

```text
The test is whether the current version produces a real response that distinguishes the direction (core hypothesis).

Show the existing version and invite real payment without adding features (action for this round).

Record payment, explicit refusal, and refusal reasons; payment supports continuing while repeated refusal argues against it (signals to observe).

If payment appears, decide again whether to proceed; if refusals persist, stop new investment (reassessment condition).
```

The meaning comes first; the precise role appears at the end only where useful. The loop may contain necessary sequential actions or several participants when they test the same hypothesis under one boundary and reassessment point. It cannot bundle unrelated projects. Every decision-relevant number introduced by the Skill is labeled locally as a suggested boundary, heuristic starting point, or reliable sourced value.

Stage B produces a copyable conversation-only snapshot by default:

```markdown
## Decision snapshot

What we are deciding:
What you want to gain or protect:
Decision needed this round:
Thinking approaches used this round:
Best direction for now:
Why this direction fits:
Conditions that must hold:
What is already confirmed:
What the current evidence suggests:
What this judgment still assumes:
What remains unknown:
Where the evidence came from:
What would change the judgment:
What this round needs to learn:
What to do first:
Which real-world signals to watch:
When to decide again:
Participants and capabilities used:
Where this record is kept: this conversation only
```

These reader-facing fields map one-to-one to the canonical DecisionRecord; assumptions and unknowns remain separate. Writing it to a file or remote store requires a concrete destination and consent. The Skill does not persist hidden chain-of-thought. A later round can use a pasted old or new snapshot to distinguish judgment error, execution deviation, resource mismatch, and changed conditions.

### 6. Four-way feedback routes what happens next

After the full judgment, experiment, and snapshot, stage B actually calls one native single-select:

```text
○ This direction fits
○ Adjust the next step
○ I disagree with this judgment
○ Set it aside for now
```

The question only routes feedback on completed content; it does not ask for a budget, deadline, or new evidence. The Skill uses `native-note` only after actually observing an independent note submitted alongside the selection. Otherwise, the user can send a regular follow-up message. Host `Other` is not a separate note, and conflicting free text still wins.

Feedback never executes the experiment or authorizes a capability, participation/delegation, private data, persistence, or external action. If the native control is unavailable, fails, or is declined, the fallback uses ordinary numbered text—not fake checkboxes or radio controls.

> [!NOTE]
> The interaction above is a readable protocol illustration. In an actual session, the Skill uses only the controls and capabilities that the host exposes, and records capability calls through traces and receipts.

## Four permissions remain independent

```text
capability_call
≠ participation_delegation
≠ private_data_access
≠ external_action
```

Each capability also records `available / unavailable / unknown` and `ready / requires_approval / requires_auth / failed`. `unknown` cannot be treated as available. Actual calls produce receipts, including refusals, failures, and unfinished work.

An agent cannot answer a real person's values, authority, commitment, customer behavior, or licensed professional responsibility. Human participation defaults to a forwardable draft. Sending, inviting, creating a group, scheduling, or contacting anyone requires separate external-action consent.

## How it works across hosts

| Adapter | v0.2.0 support boundary |
| --- | --- |
| Text | Cross-host baseline; preserves the complete core without native controls, search, agents, or persistence |
| Claude Code | Official release entry via explicit `/think-it-through`; maps only capabilities observed in the current session |
| ChatGPT | Skill-only and text semantic mapping; does not certify native controls, tools, agents, or persistence |

An Adapter may change the interaction surface, not the state, authorization, waiting, judgment, or fallback semantics. A capability that a product may support is not proof that it is enabled in this session.

## Methods stay transparent without becoming homework

Basic analysis always runs. Beyond two-sided steelmanning and pre-mortem, the seven specialist cards are:

- separate users, payers, affected parties, and cost bearers (**Object calibration**);
- find the constraint that moves the whole system (**System bottleneck**);
- check whether an old strategy still fits current conditions (**Stage fit**);
- concentrate limited resources and define the commitment boundary (**Resource leverage**);
- make responsibilities, inputs, decision rights, and exit terms testable (**Boundary contracts**);
- fit information, evidence, channel, and feedback to audience and purpose (**Communication fit**);
- use actual outcomes to revisit continue, adjust, pause, or stop (**Evidence loop**).

Usually no more than one specialist card is recommended; zero is valid. Research, multiple agents, human participation, persistence, and host adaptation belong to evidence, participation, or capability layers—not the method registry.

## When to use it

The v0.2.0 release entry point is:

```text
/think-it-through
```

It fits consequential choices that are uncertain, costly, hard to reverse, or already consuming resources:

- “Is this worth doing?”
- “I am stuck between A and B.”
- “Test this idea before I commit six months.”
- “Does the action I asked AI to perform serve the actual objective?”
- “Should I continue, adjust, pause, or stop?”
- “Which current market facts would really change this decision?”
- “If extra agents are useful, explain the cost and boundary before proposing them.”

It should stay out of the way for factual lookup, method definitions, clear low-risk execution, pure creation or entertainment, code review/FMEA/research/planning without an unresolved user choice, and urgent situations that need immediate protective guidance.

## Installation

### Personal

```bash
git clone https://github.com/zemu2718/think-it-through-skill.git
test ! -e ~/.claude/skills/think-it-through
mkdir -p ~/.claude/skills
cp -R think-it-through-skill/skills/think-it-through ~/.claude/skills/
```

### Project

Run from the target project root:

```bash
test ! -e .claude/skills/think-it-through
mkdir -p .claude/skills
cp -R /path/to/think-it-through-skill/skills/think-it-through .claude/skills/
```

If it is already installed, remove or rename the old directory instead of merging versions. Restart Claude Code if the top-level Skill directory did not exist when the session started.

The core Skill needs no network access, API key, account, or executable script. It can use an existing host's search, private-data, agent, or persistence capability only when the current issue passes the Gate and the user grants the corresponding consent. The release archive contains the same 28 runtime source files described under [Project structure](#project-structure); source-directory installation remains the documented Claude Code path.

Official Claude Code reference: [Extend Claude with skills](https://code.claude.com/docs/en/slash-commands).

## Evaluation and evidence boundaries

The repository evaluates four separate questions:

1. **Discovery:** does the description load and avoid close negatives?
2. **Behavior after loading:** does a real model obey the multi-turn, Gate, consent, and fallback contract?
3. **Core UX:** does the conversation support alignment, correction, understanding, and action?
4. **Enhancement UX:** do research, participation, cross-host behavior, solution delivery, and reassessment add real value?

### Frozen v0.1 behavior snapshot

These results bind only three fixed v0.1 scenarios and do not establish v0.2.0 behavior:

| Metric | With Skill | Without Skill | Delta |
| --- | ---: | ---: | ---: |
| Contract assertion pass rate | **100.0%** | 57.4% | +0.43 |
| 20-point semantic rubric | **98.3%** | 38.3% | +0.60 |
| Runs passing the full semantic gate | **3/3** | 0/3 | — |

Exact transcripts, scores, and SHA-256 bindings are in [`benchmarks/behavior-v0.1/`](benchmarks/behavior-v0.1/). The frozen discovery holdout is **9/16**; see [`benchmarks/trigger-v0.1/`](benchmarks/trigger-v0.1/).

### v0.2.0 contract validation

The current grader, versioned fixtures, ten-dimension 20-point core UX rubric, and eight-dimension 16-point enhancement rubric keep the release contract mechanically reviewable:

- [`ux-evals.json`](skills/think-it-through/evals/ux-evals.json)
- [`ux-rubric.md`](skills/think-it-through/evals/ux-rubric.md)
- [`enhancement-rubric.md`](skills/think-it-through/evals/enhancement-rubric.md)

```bash
uv run --python 3.12 --with pyyaml python -m unittest discover -s scripts -p 'test_*.py' -v
uv run --python 3.12 --with pyyaml python scripts/validate_repo.py
```

Contract validation and session execution are intentionally separate: repository checks establish the packaged protocol, while a capability call in a particular session is established only by its observation, consent, trace, and receipt. New native-host compatibility claims require versioned loading, interaction, execution, and fallback evidence.

## Safety and privacy

- zero external calls, one main agent, and a conversation-only snapshot by default;
- no substitution for medical, legal, investment, or emergency professional help;
- no manipulation, deception, intimidation, tracking, or coercion tactics;
- facts, inferences, hypotheses, and unknowns remain distinct;
- the final choice and every external action remain with the user.

See [`SECURITY.md`](SECURITY.md) and [`safety-boundaries.md`](skills/think-it-through/references/safety-boundaries.md).

## Transparent method provenance

Seven specialist cards are neutral adaptations of selected MIT-licensed files from a fixed revision of `SamadhiFire/xinqingnian-maoxuan-skill`. Each records repository, fixed commit, exact file, license, and material changes. Three other candidate repositories were audited and not adopted.

See [`docs/third-party-audit.md`](docs/third-party-audit.md) and [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md).

## Project structure

```text
skills/think-it-through/
├── SKILL.md                    # Current-host entry and compact state contract
├── core/                       # Portable protocol and JSON Schemas
├── policies/                   # Evidence and participation routing
├── adapters/                   # Text, Claude Code, and ChatGPT
├── references/                 # Analysis, interaction, methods, safety, provenance
├── evals/                      # Current fixtures, UX, and trigger definitions; not packaged
├── LICENSE
└── THIRD_PARTY_NOTICES.md

benchmarks/behavior-v0.1/       # Frozen behavior evidence
benchmarks/trigger-v0.1/        # Frozen discovery evidence
docs/                           # Versioned product architecture and third-party audit
scripts/                        # Versioned grading, tests, validation, packaging
assets/                         # Original project visuals
CHANGELOG.md                    # Release status and version history
```

The single maintenance source is `skills/think-it-through/`. A project-level `.claude/skills/think-it-through/` is only a local installation copy. Distribution contains 28 source files: the runtime entry, core, policies, adapters, required references, licenses, and notices. It excludes evals, benchmarks, historical transcripts, workspaces, caches, and local configuration.

## Contributing

Useful contributions include realistic decisions, close trigger negatives, method-routing cases, bounded Evidence and Participation scenarios, cross-host conformance, real UX review, and reproducible validation fixes. A new framework, persona, or capability must demonstrate distinct decision value rather than lengthening the feature list.

Start with [`CONTRIBUTING.md`](CONTRIBUTING.md). Report security issues privately through [`SECURITY.md`](SECURITY.md).

## License

Think It Through is released under the [MIT License](LICENSE). Third-party attribution is retained in [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md).
