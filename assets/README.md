# Visual assets

The repository uses **Thinking Light / Clarity Aperture** as its primary visual identity. Adjustable observation frames represent the work of thinking; their alignment creates a clear opening, while a small pivot keeps the current view open to revision.

**Decision Thread** remains a secondary explanatory grammar for diagrams: a surface request can follow an execution-first or decision-first path, an optional Gate stays visibly conditional, and real results return for reassessment. It is not part of the current Social Preview composition and must not become a second primary mark.

## Visual meaning

- observation frames: several relevant views held at once rather than collapsed too early;
- clarity aperture and channel: alignment makes the underlying decision visible;
- a small pivot: the current understanding remains correctable;
- in explanatory diagrams only, two weighted paths distinguish execution-first from decision-first movement;
- in explanatory diagrams only, a dashed branch marks optional evidence or participation;
- in explanatory diagrams only, a returning loop shows that real results can reopen the decision.

Shape, weight, line style, position, and labels carry meaning alongside color. No important state relies on color alone.

## Source of truth

[`manifest.json`](manifest.json) is the machine-readable asset inventory. It records each asset's role, language and theme variants, canvas, composition, byte budget, canonical source hash, dependencies, and deterministic generator.

| Role | Editable or canonical source | Generated output |
| --- | --- | --- |
| README Invocation Card | `readme-invocation-card-dark.png` | `readme-invocation-card-light.png` |
| Social Preview | `social-preview.svg` plus the canonical dark card subject | `social-preview.png` |

The README Invocation Card is the compact opening brand and invocation experience. Social Preview is a restrained sharing card with positioning on the left and the same three-dimensional Thinking Light on the right; it is not an installation or compatibility matrix. Product inputs in the READMEs are localized text, not managed visual assets.

All top-level SVG and PNG files under `assets/` must be declared by the manifest. Do not keep a second canonical subject under `output/` or reference exploration files from public documentation.

## Canonical Thinking Light provenance

`readme-invocation-card-dark.png` is the single hash-pinned 600×600 RGBA canonical raster source selected by the project owner. It fixes the Thinking Light's scale, position, frame geometry, base width, pivot placement, material, and the compact terminal-card invocation `/think-it-through`. The area outside the rounded card remains transparent. The reverse-skill README was referenced only for first-image use and compact badge intent; no composition or brand element was copied.

Do not casually re-encode or hand-optimize the canonical dark PNG. If it is intentionally replaced, update its SHA-256, dimensions, pixel mode, crop and anchor geometry, provenance, byte budget, README use, generated outputs, tests, and validation rules together.

`readme-invocation-card-light.png` is not a second original. The renderer rebuilds the light card surface and controlled contact shadow, then composites the exact dark-source subject at the manifest's fixed 1:1 anchor. This keeps the subject, base, pivots, aperture, and command baseline aligned across themes.

## Generated raster workflow

`readme-invocation-card-light.png` and `social-preview.png` are manifest-declared derived files. Do not hand-edit them. Edit only the relevant source—`social-preview.svg` for the sharing layout or the canonical dark PNG through an intentional source-replacement change—then regenerate both declared outputs in the pinned Python 3.12 environment:

```bash
uv run --python 3.12 --with-requirements requirements-validation.txt \
  python scripts/render_assets.py
```

Check freshness without writing tracked files:

```bash
uv run --python 3.12 --with-requirements requirements-validation.txt \
  python scripts/render_assets.py --check
```

The Social Preview SVG uses original paths for its wordmark and stable layout markers, not `<text>`, external fonts, remote resources, or embedded raster images. `resvg-py` renders that SVG with system fonts disabled. Pillow then extracts the Thinking Light from the canonical dark card, composites it at 1:1 scale, and draws the short positioning and invocation copy with its bundled default font. Pillow also fully decodes both generated PNGs and compares dimensions and decoded pixel hashes. Different PNG compression is accepted when decoded pixels are identical. Source and output byte limits are defined in the manifest. The generator writes only the light Invocation Card and Social Preview; it never writes the canonical dark source.

Locally generated PNGs prove only that repository outputs are fresh. Uploading Social Preview to GitHub repository settings is a separate external action, and local generation must not be described as if that action had occurred.

## Accessibility and negative standards

The SVG includes `title`, `desc`, and accurate `aria-label` metadata for the positioning and invocation regions. README images use localized, meaningful alt text. The Social Preview retains meaningful readable copy in its generated PNG while its SVG source remains independent of system fonts.

The visual character is premium through restraint: neutral black, warm neutral space, graphite, disciplined teal, rare amber, clear hierarchy, and only meaning-bearing geometry. Natural continuous shading, grooves, and one contact shadow express physical form; they are not decorative effects.

Reject an asset if it:

- draws a second Thinking Light or changes its geometry between themes;
- restores the old Social Preview's Decision Thread, optional Gate, reassessment loop, or pixel tagline;
- resembles a generic AI workflow, robot, neural network, or mandatory multi-Agent pipeline;
- uses color as the only status signal;
- invents a result, metric, user, testimonial, price, sample size, or deadline;
- embeds paragraph-length product copy or pseudo UI;
- uses decorative gradients, glow, glass effects, stacked shadows, or decorative node clouds;
- needs zooming before its primary relationship is understandable;
- adds decoration whose removal would not change meaning.
