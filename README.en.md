<div align="center">

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/readme-invocation-card-dark.png">
  <source media="(prefers-color-scheme: light)" srcset="assets/readme-invocation-card-light.png">
  <img src="assets/readme-invocation-card-light.png" alt="Think It Through invocation card: the Thinking Light surrounds a clear opening above the Claude Code command /think-it-through." width="140">
</picture>

# Think It Through · 想清楚

**AI can get things done fast, but what's worth doing is still yours to decide.**

Before you start or commit more, think it through—then decide.

[![MIT License](https://img.shields.io/github/license/zemu2718/think-it-through-skill?style=flat-square)](LICENSE) [![Latest Release](https://img.shields.io/github/v/release/zemu2718/think-it-through-skill?style=flat-square&label=release)](https://github.com/zemu2718/think-it-through-skill/releases/latest) [![Validate](https://github.com/zemu2718/think-it-through-skill/actions/workflows/validate.yml/badge.svg?branch=main)](https://github.com/zemu2718/think-it-through-skill/actions/workflows/validate.yml?query=branch%3Amain)

[When to use it](#when-to-use-it) · [How it works](#how-it-works) · [Install](#install-and-use) · [Safe by default](#safe-by-default)

🌐 [简体中文](README.md)

</div>

## What you get

- **A clear direction:** before you start, whether to move forward or validate first; once underway, whether to continue, adjust, pause, or stop.
- **A small real-world test:** what to try first, what to watch for, and whether the result supports the current direction.
- **A rationale you can revisit:** what you were deciding, why this direction made sense, what remains unknown, and what should make you change course.

## When to use it

**A simple rule:** pause before an important commitment—and reassess after real results arrive instead of automatically continuing.

| Decision moment | Questions you can bring |
| --- | --- |
| **Before starting** | Is this project worth doing, and what should be validated before full development? |
| **Before choosing a path** | Which option is more likely to achieve the real goal, and what information could change the choice? |
| **Before committing resources** | Should we develop, hire, buy, launch, promote, partner, or make a harder-to-reverse promise? |
| **Before doubling down** | Does the evidence justify investing more time or budget, expanding the scope, or taking on more reputational risk? |
| **After results arrive** | Given what happened, should we continue, adjust, pause, or stop? |

You do not need the full process for factual lookup, low-risk execution after a decision is made, pure creation, or technical review and research that involves no key choice from you.

In an emergency, take protective action first. Consult an appropriate qualified professional for medical, legal, investment, and other specialized matters.

## How it works

1. **Clarify the choice in front of you.** Start with what you want to do and the outcome you want to achieve or protect. Treat a proposed product, feature, or custom build as one candidate solution—not as proof that the underlying problem is settled.
2. **Find the information most likely to change that choice.** Separate facts, guesses, assumptions, and unknowns, then ask one question that could change your direction or how much you commit.
3. **Confirm key answers in the right way.** You decide your goals, limits, and risk tolerance. Confirm other people's commitments with the people making them, test customer demand by real behavior, and consult a qualified professional on specialized matters. Before a major commitment, start from real tasks and desired outcomes, check existing products, platform capabilities, tool combinations, and process changes, then verify the strongest realistic paths.
4. **Reassess using real results.** Explain when the current judgment applies and what would change it, then design one small, low-cost test that can be stopped if needed. Reassess when the result comes back. If the strongest realistic alternative has not been reasonably checked or tried, limit the next step to validation rather than a full build.

### Methods it may use

**It always starts with basic analysis.** It checks whether the choice in front of you actually helps achieve your goal, separates facts, guesses, assumptions, and unknowns, and finds the question most likely to change the judgment.

When useful, it can also draw on two core methods:

- **Two-sided Steelman:** compare the current direction and its strongest alternative using the same standards, rather than looking only for reasons to support your existing view.
- **Pre-mortem:** assume the path eventually failed, then work backward to likely causes, the earliest warning signs, and ways to limit the damage.

<details>
<summary><strong>See seven additional methods</strong></summary>

- **Object Calibration:** clarify who uses it, who pays, who is affected, and who bears the consequences so you know whose problem you are solving.
- **System Bottleneck:** when several problems affect one another, separate surface symptoms from the key issue holding back the whole system.
- **Stage Fit:** check whether outside conditions have changed and whether an approach that worked before still fits now.
- **Resource Leverage:** when time, money, or capability is limited, decide where resources matter most and how far you are willing to commit.
- **Boundary Contracts:** make responsibilities, contributions, decision rights, commitments, and exit conditions clear, including how you will know whether each was met.
- **Communication Fit:** once the judgment is clear, decide whom to address, what evidence to use, which channel fits, and how to collect feedback.
- **Evidence Loop:** compare the original goal and assumptions with what actually happened, then decide whether to continue, adjust, pause, or stop.

</details>

You do not need to learn or choose these methods in advance. It recommends only the approaches your current question needs and asks you to confirm before using them.

If research or input from another Agent or someone with relevant knowledge could help, it explains why and asks for your consent first.

## Install and use

**Install:** Send this message to the Agent you already use:

```text
Install this Skill for me: https://github.com/zemu2718/think-it-through-skill
```

Or run this command in your terminal:

```bash
npx skills add zemu2718/think-it-through-skill
```

Whichever route you choose, completing the installation does not mean the Skill is ready to use in your current tool. If you run into trouble, see the [installation guide](docs/installation.en.md) and [compatibility notes](docs/compatibility-and-evidence.en.md).

**Get started:** If you use Claude Code, enter this after installation:

```text
/think-it-through
```

Then describe an idea you have, a choice you are facing, or something you are unsure about.

## Safe by default

Unless you explicitly approve a specific action, it does not:

- **access the network**;
- **access private data**;
- **involve additional Agents**;
- **write files or save anything remotely**;
- **take external action**, such as sending, publishing, purchasing, deleting, or contacting someone.

If it needs any of these actions, it explains what it wants to do and asks first. Agreeing to one action does not mean you agree to any other action.

### Learn more

- **Installation and compatibility:** [installation](docs/installation.en.md) · [compatibility and evidence](docs/compatibility-and-evidence.en.md)
- **Understand the boundaries:** [product](PRODUCT.md) **[Chinese]** · [normative contract](REQUIREMENTS.md) **[Chinese]** · [security](SECURITY.md)
- **Help improve it:** [contributing](CONTRIBUTING.md) · [report an issue](https://github.com/zemu2718/think-it-through-skill/issues/new?template=install-or-runtime-feedback.yml)

If Think It Through helps, consider giving the project a Star.

Think It Through is released under the [MIT License](LICENSE). See [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md) and the [third-party audit](docs/third-party-audit.md) for adapted sources.
