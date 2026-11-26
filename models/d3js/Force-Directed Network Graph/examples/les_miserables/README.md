# Worked example: Les Misérables

Example data for the [d3.js Force-Directed Network Graph](../../README.md).
This is Donald E. Knuth's character network for Victor Hugo's *Les
Misérables*, from *The Stanford GraphBase* (1993). Two characters are linked
when they appear in the same chapter. It is the dataset behind D3's own
[force-directed graph example](https://observablehq.com/@d3/force-directed-graph/2),
so the two pages can be compared side by side.

| file | what |
|---|---|
| `nodes.csv`, `edges.csv` | 77 characters, 254 co-appearance links, weighted by shared chapters. |
| `params.json` | The model parameters used. |
| `Les_Miserables_Network.html` | The page `run_local.py` produces from this folder. |
| `source/build_data.py` | Builds the CSVs from `networkx.les_miserables_graph()`, the copy networkx ships. |

**What it teaches.**
* **Structure alone:** there is only one relationship type ("appears with"),
  so the communities come purely from who shares chapters with whom.
* **Weights:** this is the weighted example. `weight` is the number of
  chapters a pair shares. It sets link thickness and feeds PageRank and
  Louvain, so a pair that shares 15 chapters pulls harder than a single
  meeting.
* **Results:** Louvain finds 6 communities (weighted modularity 0.565).
  Valjean has the highest undirected PageRank and is linked to 36 of the
  other 76 characters. These figures hold at the versions in
  `../../requirements-reference.txt`. Delete the `weight` column and rerun to
  see the unweighted version: also 6 communities, but modularity 0.558 and
  different groups.

**Data notes.**
* Names keep Knuth's spelling, without accents, and with spaces added
  (`MlleBaptistine` → `Mlle Baptistine`).

Rebuild from the workflow folder:

```bash
python examples/les_miserables/source/build_data.py
python run_local.py examples/les_miserables
```
