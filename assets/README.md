# Visual assets

The repository uses an original geometric language called **Decision Thread**. Its primary symbol is the **Decision Hinge**: several surface inputs meet at a deliberate pause, one direction commits, and real results return to revise the judgment.

## Visual meaning

- converging inputs: surface tasks, objectives, constraints, and unknowns;
- a decision hinge: the answer that can change direction or commitment;
- one solid path: the current conditional judgment, not absolute certainty;
- a small dashed branch: optional evidence or participation, only when useful and authorized;
- a returning loop: real-world results can reopen the decision.

Shape, weight, line style, position, and labels carry meaning alongside color. No important state relies on color alone.

## Source of truth

[`manifest.json`](manifest.json) is the machine-readable asset inventory. It records each asset's role, language and theme variants, canvas, stable structure IDs, byte budget, and—where applicable—generator.

| Role | Editable source | Output |
| --- | --- | --- |
| Brand Mark | `brand-mark-light.svg`, `brand-mark-dark.svg` | the same SVG files |
| Decision Case | four `decision-case-*.svg` locale/theme variants | the same SVG files |
| Social Preview | `social-preview.svg` | `social-preview.png` |

The Brand Mark carries recognition at small sizes. The Decision Case visualizes one synthetic SaaS decision and requires an adjacent text equivalent in each README; it is not a testimonial, runtime transcript, or behavior evidence. Social Preview is a restrained sharing card, not an installation or compatibility matrix.

## Social Preview generation

`social-preview.svg` is the only editable source; do not hand-edit the PNG. Its wordmark and tagline use original SVG paths, not `<text>`, external fonts, remote resources, or embedded raster images.

Generate the PNG in a Python 3.12 environment with the pinned validation dependencies:

```bash
uv run --python 3.12 --with-requirements requirements-validation.txt \
  python scripts/render_assets.py
```

Check freshness without writing tracked files:

```bash
uv run --python 3.12 --with-requirements requirements-validation.txt \
  python scripts/render_assets.py --check
```

The renderer uses `resvg-py` with system fonts disabled. Pillow verifies the complete PNG stream, reopens and loads it, converts it to RGBA, and compares dimensions plus decoded pixel hashes. Different PNG compression is accepted when the pixels are identical.

A generated local PNG does not mean GitHub repository settings use it. Uploading it as the repository Social Preview remains an explicit external action.

## Accessibility and negative standards

All SVGs include `title` and `desc`. Brand Mark light/dark variants share geometry. Decision Case variants share non-text geometry and equivalent English/Chinese semantics. The optional Gate is dashed and secondary; the reassessment loop has a distinct returning shape.

The visual character is premium through restraint: deep ink, warm neutral space, disciplined teal, rare amber, clear hierarchy, and only meaning-bearing geometry.

Reject an asset if it:

- resembles a generic AI workflow, robot, neural network, or mandatory multi-Agent pipeline;
- makes the optional Gate look required or equally prominent;
- shows only an answer and omits real-world reassessment;
- uses color as the only status signal;
- invents a result, metric, user, testimonial, price, sample size, or deadline;
- embeds paragraph-length product copy or pseudo UI;
- uses gradients, glow, glass effects, stacked shadows, or decorative node clouds;
- needs zooming before its primary relationship is understandable;
- adds decoration whose removal would not change meaning.
