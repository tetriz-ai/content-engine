# Visual walkthrough

Five scenes give discovery and writing equal space: configured sources feed one signal bank,
independent signals form an evidence-graded theme, a person approves the theme and format,
Blog and Editorial Draft prepare the writing, and a draft arrives with its evidence and review package.

The opening shows HN, Reddit, Product Hunt, X, news search, Medium/Substack,
competitor RSS, vendor blogs and pasted LinkedIn posts. Access and configuration
are required; LinkedIn is never scraped. Google Trends and Semrush appear separately
as optional demand context, not additional corroborating origins. The config template
and canonical command define these routes.

The posts, cards and drafts are illustrations, not a live scan or shipped dashboard.
The fictional [CI-flakiness theme](../../../packages/content-engine/examples/theme-example-ci-flakiness.md)
grounds the evidence scene. STRONG is a model judgment, not an independent fact check.
Each format needs approval; the fictional theme approves Blog, LinkedIn and video. Publishing stays manual.

[saved-answer.txt](saved-answer.txt) retains a real run of the
[saved-answer example](../../../examples/draft-without-an-api-key/). That helper writes
a fixed response file. It does not execute the full Blog → Editorial Draft editorial
pipeline or a live model. The animation explains that workflow without claiming
that execution happened.

Use Python 3.12, install the optional `.github/assets/requirements.txt` in a temporary
environment, then from the repo root:

```sh
examples/draft-without-an-api-key/run.sh > .github/assets/demo/saved-answer.txt
python .github/assets/render-visual-demo.py --preview-dir /tmp/content-demo
```

The artwork and animation are code-drawn from `story.json`. No font or third-party
artwork is bundled. Rendering uses Arial or DejaVu Sans and separately installed
Pillow (MIT-CMU); it changes no engine or scanner dependencies. Inspect all five
keyframes and the animation before committing.

The README uses a static first-frame preview. Open its linked GIF to play the animation.
Regenerate the preview after rendering:

```sh
python -c "from PIL import Image; im = Image.open('.github/assets/demo.gif'); im.seek(0); im.convert('RGB').save('.github/assets/demo-static.png', optimize=True)"
```
