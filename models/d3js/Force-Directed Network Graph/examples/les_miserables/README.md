# Worked example: Les Misérables

Example data for the [d3.js Force-Directed Network Graph](../../README.md).
This is Donald E. Knuth's character network for Victor Hugo's *Les
Misérables*, from *The Stanford GraphBase* (1993). Two characters are linked
when they appear in the same chapter. It is the dataset behind D3's own
[force-directed graph example](https://observablehq.com/@d3/force-directed-graph/2),
so the two pages can be compared side by side.

| file | what |
|---|---|
| `nodes.csv`, `edges.csv` | 77 characters, 254 co-appearance links. |
| `params.json` | The model parameters used. |
| `Les_Miserables_Network.html` | The page `run_local.py` produces from this folder. |
| `source/build_data.py` | Builds the CSVs from `networkx.les_miserables_graph()`, the copy networkx ships. |

**What it teaches.** There is only one relationship type ("appears with"), so
the communities come purely from who shares chapters with whom. Louvain finds
6 communities (modularity 0.558). Valjean has the highest undirected PageRank
and is linked to 36 of the other 76 characters. These figures hold at the
versions in `../../requirements-reference.txt`.

**Data notes.**
* Names keep Knuth's spelling, without accents, and with spaces added
  (`MlleBaptistine` → `Mlle Baptistine`).
* Knuth's data counts how many chapters each pair shares. The workflow's
  schema has no weight column, so the count goes into each link's `detail`
  ("co-appear in 8 chapters") and doesn't affect the layout or statistics. A
  weighted version would need an optional `weight` column in the schema.

Rebuild from the workflow folder:

```bash
python examples/les_miserables/source/build_data.py
python run_local.py examples/les_miserables
```
