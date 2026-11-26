# d3.js Force-Directed Network Graph

Turn a **nodes** table and an **edges** table into an interactive d3.js
force-directed network graph, from a brewlytics **Python Script** functional.
The script computes the graph statistics with networkx (PageRank, degree,
Louvain communities). It writes one self-contained `.html` page that people
can download from `outputs.resource` and open in any browser.

The method is the lesson; the data is interchangeable. Four worked examples
use the same unchanged script. Open any example's `.html` page to see the
result:

| example | nodes | relationships | what it shows |
|---|---|---|---|
| [The Simpsons](examples/simpsons/) | 336 | 536 | A large, mixed graph: characters, places and organisations, 29 relationship types. |
| [Les Misérables](examples/les_miserables/) | 77 | 254 | Knuth's chapter co-appearance network, the data behind D3's own force-graph example. One relationship type, so the communities come from structure alone. |
| [Florentine families](examples/florentine_families/) | 16 | 35 | Padgett's marriage and business ties. A small classic for centrality: see where the Medici land. Shows two relationships on one pair, and an isolated node. |
| [Henry VIII](examples/henry_viii/) | 44 | 76 | Henry VIII's six wives, their families, and the Tudor succession. A family tree as a network, with every fact linked to its Wikipedia source. |

## What a force-directed graph is

A node-link diagram whose layout is a small physics simulation
([d3-force](https://d3js.org/d3-force)). Links pull connected nodes together
like springs, every node pushes every other away (charge), and a collision
force stops circles from overlapping. The simulation runs until it settles,
so tightly connected groups end up near each other without anyone placing
them. D3's own
[force-directed graph example](https://observablehq.com/@d3/force-directed-graph/2)
is the minimal version of what this page does.

## Files

| file | what |
|---|---|
| `d3_force_network_graph.py` | **Paste into the brew Python Script functional.** Dataset-agnostic. |
| `run_local.py` | Runs that script unchanged on your machine, with a stand-in `brewlytics` module. |
| `template/` | Minimal `nodes.csv`, `edges.csv` and `params.json` showing every column. Start your own data here. |
| `examples/` | Worked examples, one folder each: data, `params.json`, sample page, README, and the `source/` used to build the data where there is one. |
| `tests/` | pytest suite; CI runs it on every pull request. |
| `requirements*.txt` | What the script needs; the exact `reference` pins and the oldest supported `floor`. |

## Run locally

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt pytest
.venv/bin/python run_local.py                        # template/ -> template/network_graph.html
.venv/bin/python run_local.py examples/henry_viii    # -> examples/henry_viii/Henry_VIII_Network.html
.venv/bin/python -m pytest tests
```

A data folder holds `nodes.csv`, `edges.csv`, `params.json` (the model
parameters) and, optionally, one image to use as the header logo.

## Data model

**nodes**: `id, name, type, aliases, deceased, notes`

* `id`: a stable slug that edges refer to (`alex`, `acme`). Names can be
  edited freely; ids keep misspellings from splitting one node into two.
* `type`: free text (Person, Organisation, Place…).
* `aliases`, `notes`: `; `-separated. Search matches aliases too.
* `deceased`: `Y` or blank; drawn as a ring.

**edges**: `from_id, to_id, relationship, category, directed, status, role, detail, source` (+ optional `label`)

* One row per fact, read from → to.
* `relationship`: the abstract type (`parent_of`, `works_at`). It is used for
  statistics and filtering. `category` groups relationships for the
  show/hide chips.
* `label`: the short text drawn on the link ("former analyst at"). If the
  column is missing, the page shows `relationship`.
* `directed`: `False` for symmetric relationships (`sibling_of`,
  `friend_of`). Arrows are drawn only on directed links.
* `status`, `role`: qualifiers (former, step, founder…). `detail`: free text
  shown in the tooltip and table.
* `source`: a URL per fact, shown as a link.

Extra columns are ignored, so working columns can stay in the CSVs.

## Brew model wiring

```
CSV to Table (nodes) ─┐
CSV to Table (edges) ─┼─► Python Script (d3_force_network_graph.py) ─► Network Stats (JSON)
String to JSON (params) ┤                                            ─► Network Table
image resource (opt.) ─┘                                            ─► Network Graph (.html)
```

* **`inputs.tables`**: nodes and edges, in either order. Each is found by its
  columns.
* **`inputs.list`**: one JSON string per parameter:
  * **Network Graphic Title**
  * **Network Graphic Filename**: spaces become `_`, and the extension is
    forced to `.html`.
  * **Data Sources** (optional): `{"label": "url", …}`, shown as links under
    the title.
* **`inputs.resources`** (optional): the first `.svg/.png/.jpg/.webp/.gif` is
  embedded beside the title as a data URI, so the page stays one file.
* **Bad data stops the run.** An edge id missing from the nodes table, or a
  duplicated node id, raises a `ValueError` that names the ids.

| brew output | from | contents |
|---|---|---|
| Network Stats | `outputs.string` | `Overall Stats` (density, counts, highest PageRank and degree, # of communities, modularity) + the `Parameters` used |
| Network Table | `outputs.table` | one row per node: Node, Type, Aliases, Deceased, Community, Community Hub, Pagerank (Undirected), Pagerank, Degree, In Degree, Out Degree |
| Network Graph | `outputs.resource` | the downloadable d3 page |

## The page

* **Node size**: PageRank computed **ignoring edge direction**. Directed
  PageRank inflates dead ends: nodes that many links point to but that point
  nowhere. The directed value stays in the table and the tooltip.
* **Colour**: Louvain community (seed 7), named after its best-connected
  member. The 7 largest communities use ColorBrewer Dark2; the rest are grey.
* **Link labels**: drawn for the hovered or pinned node's links, and for
  every visible link once zoomed to 2.5× or more. Labels stay upright and a
  constant size on screen.
* **Controls**:
  * category chips show or hide relationship categories;
  * search matches names and aliases;
  * hover previews a node, and a click pins it.
* **Table view** (collapsed by default): the relationships currently shown,
  following the chips and the pinned node. Click a column header to sort.
* **Learning line**: "Built with d3.js" links to d3js.org, the d3-force docs
  and D3's example. The version shown comes from the same `D3_VERSION`
  constant as the CDN link.
* **Safe links**: URLs from the data become links only if they are absolute
  `http://` or `https://`. `javascript:`, `data:` and relative URLs are shown
  as text or dropped, so a shared page can't run script hidden in a link.
* **Fit to view**: once the layout settles, the view zooms to fit the whole
  graph, unless the viewer has already zoomed or panned. *Reset view* fits it
  again.
* **Pairs with several relationships** share one link. The tooltip and table
  list each relationship, and the category chips hide a link only when all of
  its relationships are hidden.
* d3 7.9.0 is loaded from cdn.jsdelivr.net, and light/dark mode follows the
  viewer's system setting.

## Reproducibility

Louvain is randomised. The fixed seed makes the communities repeatable **for
the same data and the same networkx version**. Changing the data, or brew
upgrading networkx, can merge, split or renumber communities, and so change
the colours. CI therefore checks the exact example numbers only at the
versions in `requirements-reference.txt`. On the oldest supported versions
(`requirements-floor.txt`, networkx 2.8.8) it checks everything else.
