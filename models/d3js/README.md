# d3.js workflows for brewlytics

Python Script workflows whose output is an interactive [d3.js](https://d3js.org/)
page: one self-contained `.html` file, written to `outputs.resource`, that
anyone can download and open in a browser.

| workflow | what it shows | example |
|---|---|---|
| [Force-Directed Network Graph](Force-Directed%20Network%20Graph/) | Entities and their relationships, laid out by d3-force, sized by PageRank, coloured by Louvain community | The Simpsons, Les Misérables, Florentine families, Henry VIII |

Each workflow folder has the same shape:

* a dataset-agnostic script to paste into brew;
* `run_local.py`, which runs that script locally;
* a `template/` of starter data;
* `examples/`, which work the method through on real datasets;
* tests, which CI runs on every pull request.
