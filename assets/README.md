# Visual assets

The repository uses **Thinking Light / Clarity Aperture** as its primary visual identity. Adjustable observation frames represent the work of thinking; their alignment creates a clear opening, while a small pivot keeps the current view open to revision.

**Decision Thread** is the secondary explanatory grammar: a surface request can follow an execution-first or decision-first path, an optional Gate stays visibly conditional, and real results return for reassessment. The Decision Hinge remains the turn inside that grammar, not the entire brand.

## Visual meaning

- observation frames: several relevant views held at once rather than collapsed too early;
- clarity aperture and channel: alignment makes the underlying decision visible;
- a small pivot: the current understanding remains correctable;
- two weighted paths: execution-first versus decision-first movement;
- a small dashed branch: optional evidence or participation, only when useful and authorized;
- a returning loop: real-world results can reopen the decision.

Shape, weight, line style, position, and labels carry meaning alongside color. No important state relies on color alone.

## Source of truth

[`manifest.json`](manifest.json) is the machine-readable asset inventory. It records each asset's role, language and theme variants, canvas, stable structure IDs, byte budget, and—where applicable—canonical source hash and deterministic generator.

| Role | Editable or canonical source | Output |
| --- | --- | --- |
| README Invocation Card | `readme-invocation-card-light.png`, `readme-invocation-card-dark.png` | the same canonical PNG files |
| Social Preview | `social-preview.svg` | `social-preview.png` |

The README Invocation Card is the compact opening brand and invocation experience. Social Preview is a restrained sharing card, not an installation or compatibility matrix. Product inputs in the READMEs are localized text, not managed visual assets.

All top-level SVG and PNG files under `assets/` must be declared by the manifest. Do not keep a second canonical copy under `output/` or reference exploration files from public documentation.

## README Invocation Card provenance

`readme-invocation-card-light.png` and `readme-invocation-card-dark.png` are independently hash-pinned 600×600 RGBA canonical raster originals selected by the project owner. They preserve the repository's Thinking Light subject, place the reliable Claude Code invocation `/think-it-through` inside a compact terminal card, and keep the area outside the rounded card transparent. The reverse-skill README was referenced only for first-image use and compact badge intent; no composition or brand element was copied.

Neither variant is generated from the other, and neither is an output of `scripts/render_assets.py`. Do not re-encode or hand-optimize these files casually. If either is intentionally replaced, update its SHA-256, dimensions, pixel mode, provenance, byte budget, both READMEs, tests, and validation rules together.

## Generated raster workflow

`social-preview.png` is the manifest-declared derived file. Do not hand-edit it. Edit `social-preview.svg`, then regenerate the declared output in the pinned Python 3.12 environment:

```bash
uv run --python 3.12 --with-requirements requirements-validation.txt \
  python scripts/render_assets.py
```

Check freshness without writing tracked files:

```bash
uv run --python 3.12 --with-requirements requirements-validation.txt \
  python scripts/render_assets.py --check
```

The Social Preview source uses original SVG paths for the wordmark and tagline, not `<text>`, external fonts, remote resources, or embedded raster images. `resvg-py` renders it with system fonts disabled. Pillow completely decodes the generated PNG, then compares dimensions and decoded pixel hashes. Different PNG compression is accepted when decoded pixels are identical. Source and output byte limits are defined in the manifest. The generator neither writes nor freshness-checks the canonical README Invocation Card variants.

Locally generated PNGs prove only that repository outputs are fresh. Uploading Social Preview to GitHub repository settings is a separate external action, and local generation must not be described as if that action had occurred.

## Accessibility and negative standards

All SVGs include `title` and `desc`. The optional Gate is dashed and secondary; the reassessment loop has a distinct returning shape. README images use localized, meaningful alt text.

The visual character is premium through restraint: deep ink, warm neutral space, graphite, disciplined teal, rare amber, clear hierarchy, and only meaning-bearing geometry. Natural continuous shading, grooves, and one contact shadow in the README Invocation Card express physical form; they are not decorative effects.

Reject an asset if it:

- resembles a generic AI workflow, robot, neural network, or mandatory multi-Agent pipeline;
- makes the optional Gate look required or equally prominent;
- shows only an answer and omits real-world reassessment;
- uses color as the only status signal;
- invents a result, metric, user, testimonial, price, sample size, or deadline;
- embeds paragraph-length product copy or pseudo UI;
- uses decorative gradients, glow, glass effects, stacked shadows, or decorative node clouds;
- needs zooming before its primary relationship is understandable;
- adds decoration whose removal would not change meaning.
