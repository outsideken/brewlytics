# brewlytics examples

Shared instructions for every AI assistant working in this repo. There are
two: **Claude** (Claude Code, which reads this file via `CLAUDE.md`) and
**Cursor** (which runs on the Grok model and reads `AGENTS.md` directly).
"Grok" and "Cursor" are the same assistant. Keep facts here, not in any one
assistant's private memory.

**Cursor runs in the cloud and can't see anyone's local files.** Anything it
needs has to be on GitHub: in this file, an issue, a PR description or a PR
comment. Never point it at a local note.

**This repo is public.** Don't commit personal information (names, emails,
local paths), credentials or copyrighted material. Images need a clear licence
(e.g. public domain on Wikimedia Commons) recorded next to them.

## What lives here

Python scripts for the brewlytics **Python Script** functional (older ones
are for *Define Python Script*), plus their data and docs.

| Folder | What |
|---|---|
| `models/` | Analytic workflows. `models/d3js/` holds workflows whose output is a d3.js page; [index](models/d3js/README.md). |
| `ml/` | Machine-learning examples. |
| `submodels/` | Reusable sub-models and utilities. |

The root files (`DecisionTreeClassifier`, `Ellipse…`, `usgs.py`) predate this
layout. Leave them in place unless K asks to move them.

## The brew runtime contract

brewlytics ("brew") is a clean-sheet redesign of JEMA. It is **not
sandboxed**, so scripts may import networkx, pandas, scipy and similar
libraries, and pages may load libraries from a CDN. A script runs as pasted,
with no imports from this repo:

- `from brewlytics import *` supplies `inputs` and `outputs`.
- **In:**
  - `inputs.table` / `inputs.tables[i]`: pandas DataFrames;
  - `inputs.resources[i]`: resources;
  - `inputs.list`: one JSON string per model parameter.
- **Out:** `outputs.string`, `outputs.table`, `outputs.resource`.
- Each workflow's `run_local.py` supplies a stand-in `brewlytics` module, so
  the script runs unchanged locally and in CI.

Which versions brew provides isn't known yet. When K finds out (e.g.
`print(sys.version, networkx.__version__)` in a Python Script), record them
here and align the CI pins.

## Workflow folders

New workflows follow the shape of
`models/d3js/Force-Directed Network Graph/`:

- `<method>.py`: the paste-into-brew script, with a numpy-style module
  docstring (Inputs / Outputs / Raises / Notes).
- `run_local.py`: runs the script locally.
- `template/`: minimal starter data.
- `examples/<name>/`: worked datasets, one folder each.
- `tests/`.
- `README.md`: the lesson.

**The method is the teaching point; the dataset is only an example (K,
2026-11-26).**

- The script, `run_local.py` and `template/` stay dataset-agnostic: no
  example names in code, comments, defaults or docstrings.
- Anything dataset-specific lives in `examples/<name>/`: data, `params.json`, images,
  converters, notes.
- `tests/test_example.py` checks this by listing the examples' names that
  must not appear in the reusable files.
- **No gender column in the network schema (K, 2026-11-26).** `label` text is
  gender-neutral; adding gender would make the schema less abstract.
- **Links built from data must be absolute http(s).** Generated pages put
  data-supplied URLs through `safeUrl` / `safeLink`, and a test runs that
  JavaScript in node.

## Working together (Claude + Cursor)

K (the owner) decides; assistants propose.

- **Branches:** work on `claude/<topic>` or `cursor/<topic>`, never on
  `main`. Open a pull request to merge. Push only when K asks.
- **Issues are the task list:** one issue per piece of work. Claim it with
  the `agent:claude` or `agent:cursor` label, and link the PR (`Closes #N`).
  Discussion goes in issue/PR comments.
- **Author ≠ reviewer.** Claude acts on GitHub as K's account
  (`outsideken`). Cursor posts as **`cursor[bot]`** through the Cursor GitHub
  app. Approval is a PR comment, not GitHub's Approve button: K's account
  can't approve its own PRs, and one rule for both directions keeps it
  simple. Every PR waits for the reviewer's approve comment.
- **Ready for review: what the PR description holds.** The author writes it
  so the reviewer needs nothing else:
  - what changed and why, and `Closes #N`;
  - how to verify: the exact commands, the expected numbers and counts, and
    the environment they came from;
  - "please look hardest at": the parts most likely to be wrong;
  - what was not done or not checked.
- **Review comment.** Head it `## Review → <author>: approve` or
  `## Review → <author>: request changes`. Name the commit SHA reviewed and
  the evidence: a test run with its counts, numbers recomputed, a browser
  check. "Looks right" is not a review; say when something was checked only
  by reading. Put each requested change under **Change requested**, and
  non-blocking points under **Notes, not blocking**.
- **Reply after changes.** Head it `## Reply → <reviewer>: changes made,
  please re-review`. Give the new commit SHA, what changed for each point
  (with numbers where they apply), and how to re-check it.
- **New commits after an approval need a re-check** before the PR merges.
  The re-check is scoped:
  - it covers what the new commits changed, plus whatever the reply says to
    re-check;
  - it says which earlier results still hold without re-running them;
  - a merge from a base branch is re-checked for what that merge brought in.

  For example, a colour fix needs the colours measured again, not the whole
  suite reread. The re-review names the new SHA.
- **Merging is K's call.** K merges, or tells an assistant to.
  - Use a merge commit, not squash, so stacked branches keep their history.
  - Before deleting a merged branch, confirm on GitHub that the PR shows as
    merged.
  - Retarget any PR based on that branch to `main` first (`gh pr edit N
    --base main`). Deleting a branch closes every open PR that targets it.
- **Never edit a file that has an open PR from the other assistant.** Comment
  on that PR instead.
- **Session start:** `git fetch`, `git status`, read this file, check open
  issues and PRs.
- **Session end:** comment on the issue or PR: what's done, what isn't,
  what's next.
- **Ask K first** before you pull, force-push, rebase shared branches, or
  delete branches or files.

## Live examples (GitHub Pages)

`site/index.html` is the landing page for every brewlytics example, with one
card per example. `site/publish.txt` lists the pages to publish, as
`<source in the repo> -> <path on the site>`. `site/build.sh` assembles
`_site/`. It fails if a listed source is missing or a relative link on the
landing page has no page behind it. `.github/workflows/pages.yml` runs the
build on every PR and deploys to https://outsideken.github.io/brewlytics/
from `main` only: on a push to `main` or a manual run on `main`.

**To publish a new example:** add its line to `publish.txt`, add a card to
`index.html`, run `site/build.sh`, and open `_site/index.html` to check it.
Only pages that are already committed get published; the build never runs
the Python scripts.

## CI is the referee

Nothing is done until CI passes on the PR. The workflows in
`.github/workflows/` are the source; keep these bullets in step with them.

- **Pages / build** (`pages.yml`): runs `site/build.sh` on every PR, so a
  missing published page or a broken landing-page link fails the PR. It
  deploys only from `main`.

- **d3js Force-Directed Network Graph (reference):** Python 3.14 with
  `requirements-reference.txt` (networkx 3.7, pandas 3.1.1, scipy 1.18.1).
  Runs every test, including the ones marked `reference`:
  - the exact Louvain numbers;
  - the committed sample page matching a fresh run.
- **d3js Force-Directed Network Graph (floor):** Python 3.11 with
  `requirements-floor.txt` (networkx 2.8.8, the first release with
  `louvain_communities`). Skips the `reference` tests, because Louvain output
  changes between networkx releases.
- **d3js Timeline (reference / floor):** Python 3.14 with pandas 3.1.1, and
  Python 3.11 with pandas 2.1.4. Both run every test; the timeline has no
  version-dependent numbers.
- **Cross-workflow data:** the Timeline's `solar_system_discoveries` builder
  reads the network graph's `examples/solar_system/` CSVs. After changing
  those, rerun `Timeline/examples/solar_system_discoveries/source/build_data.py`
  and `Timeline/run_local.py examples/solar_system_discoveries`; the Timeline's
  builder test fails until you do.
- **Changing example data, the script or the reference pins:** rerun
  `run_local.py examples/<name>` for every example, the example's
  `source/*.py` builder if its data changed, and the tests. Commit the
  regenerated files in the same PR.
- **Adding an example:** add its folder to `EXPECTED` in
  `tests/test_example.py`. A test fails until you do. Also add its distinctive
  names to `EXAMPLE_WORDS`.
