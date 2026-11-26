# Worked example: Florentine families

Example data for the [d3.js Force-Directed Network Graph](../../README.md).
These are the marriage and business ties among 16 leading families of early
15th-century Florence, from John F. Padgett and Christopher K. Ansell,
"Robust Action and the Rise of the Medici, 1400–1434", *American Journal of
Sociology* 98(6), 1993. It is a standard dataset for teaching centrality: the
Medici were not the richest or most powerful family on paper, but they sat
between the others.

| file | what |
|---|---|
| `nodes.csv`, `edges.csv` | 16 families, 35 ties: 20 marriage, 15 business. |
| `params.json` | The model parameters used. |
| `Florentine_Families_Network.html` | The page `run_local.py` produces from this folder. |
| `source/PADGETT.DAT` | The data as distributed with UCINET. Copied from the Pajek data mirror, [bavla/Nets](https://github.com/bavla/Nets/blob/master/data/Pajek/ucinet/PADGETT.DAT). |
| `source/build_data.py` | Reads the two matrices (`PADGM` marriage, `PADGB` business) and writes the CSVs. |

**What it teaches.**
* **Centrality:** the Medici have the highest undirected PageRank and the
  highest degree. Pin them (click) to see how many families they tie
  together.
* **Two relationships on one pair:** 8 pairs have both a marriage tie and a
  business tie. They share one link that lists both. Toggle the *marriage* and
  *business* chips to see each network on its own.
* **An isolated node:** the Pucci have no ties of either kind. They stay on the
  page as a lone node.
* Louvain finds 4 communities (modularity 0.316) at the versions in
  `../../requirements-reference.txt`.

**Cross-check.** The 20 marriage ties match `networkx.florentine_families_graph()`
exactly.

Rebuild from the workflow folder:

```bash
python examples/florentine_families/source/build_data.py
python run_local.py examples/florentine_families
```
