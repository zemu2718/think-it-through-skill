# Visual assets

The repository uses an original geometric language called **Decision Thread**. Its purpose is to make one product relationship visible without turning the README into a diagram of the internal contract.

## Visual meaning

- several incoming paths: surface tasks, objectives, constraints, and unknowns;
- a decision hinge: one question that can change direction or commitment;
- one main path: the current conditional judgment, not an absolute answer;
- a dashed side branch: optional evidence or participation, used only when needed and authorized;
- a returning loop: real-world results can trigger reassessment.

Line shape, weight, position, and labels carry meaning alongside color. No important state relies on color alone.

## Files and budgets

| Asset | Source | Output | Budget |
| --- | --- | --- | ---: |
| README hero | `hero-light.svg`, `hero-dark.svg` | same files | 40 KiB each |
| English flow | `demo-flow.svg` | same file | 30 KiB |
| Chinese flow | `demo-flow.zh-CN.svg` | same file | 30 KiB |
| Social preview | `social-preview.svg` | `social-preview.png` | 400 KiB PNG |

The light and dark heroes use the same geometry. SVGs include `title` and `desc`, use no scripts, remote resources, embedded raster images, external fonts, or heavy filters. The README keeps a text equivalent near every informational diagram.

## Social Preview export

`social-preview.svg` is the editable source. The PNG is exported on macOS with the system SVG renderer, then optimized with ImageMagick 7.1.2-25:

```bash
sips -s format png assets/social-preview.svg --out assets/social-preview.png
magick assets/social-preview.png -strip -define png:compression-level=9 \
  assets/social-preview.png
```

After export, verify the 1280×640 dimensions, file size, text edges, safe-area cropping, and colors. A local PNG does not mean GitHub repository settings use it.

## Originality and negative standards

These assets use repository-authored paths, text, layout, and colors. They do not copy third-party characters, images, object metaphors, compositions, prompts, or style specifications.

Reject an asset if it:

- looks like a generic AI workflow or mandatory multi-agent pipeline;
- makes the optional Gate look like a required stage;
- shows only an answer and omits the real-world reassessment loop;
- uses color as the only status signal;
- embeds paragraph-length product copy;
- needs zooming before its primary relationship is understandable;
- adds decorative elements whose removal would not change meaning.
