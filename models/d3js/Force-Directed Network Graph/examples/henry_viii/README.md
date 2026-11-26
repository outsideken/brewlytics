# Worked example: Henry VIII, his wives and lineage

Example data for the [d3.js Force-Directed Network Graph](../../README.md).
It covers Henry VIII's six marriages, the wives' parents and siblings,
Henry's own parents and siblings, his children, and the Tudor succession
through to James VI and I.

| file | what |
|---|---|
| `nodes.csv`, `edges.csv` | 44 people, 76 relationships, written by hand. These CSVs are the source; there is no build script. |
| `params.json` | The model parameters used. |
| `Henry_VIII_Network.html` | The page `run_local.py` produces from this folder. |

**What it teaches.**
* **A family tree drawn as a network:** parents, siblings and spouses, plus
  two smaller categories: *succession* (who succeeded whom) and *politics*
  (Thomas Cromwell brokering the Anne of Cleves marriage; Edward Seymour as
  Lord Protector).
* **Status and detail:** the marriages carry the vocabulary from the Simpsons
  example:
  * `annulled`: Catherine of Aragon, Anne Boleyn, Anne of Cleves;
  * `widowed`: Jane Seymour, Catherine Parr;
  * `ended`: Catherine Howard, executed.

  Dates and circumstances are in `detail`.
* **Sources:** every relationship links to the English Wikipedia page that
  supports it (`source` column). The facts were checked against those pages on
  2026-11-26.
* **Communities that mean something:** Henry VIII has the highest undirected
  PageRank. Louvain finds 7 communities (modularity 0.551) at the versions in
  `../../requirements-reference.txt`, and each is a recognisable faction:
  * Henry's own family;
  * the Seymours, who pull in Catherine Parr through her last husband,
    Thomas Seymour;
  * the Boleyns and the Howards together, since the Duke of Norfolk was uncle
    to two of the wives;
  * Cleves, with Cromwell;
  * Aragon;
  * the Scottish line;
  * the later monarchs, joined by the succession.

**Data notes.**
* `deceased` is left blank. Everyone here is long dead, so the ring would mark
  every node and mean nothing. Executions and deaths are in `notes`.
* Labels are gender-neutral, as in the other examples ("parent of", "spouse
  of", "lover of" for the two mistresses).
* Catherine of Aragon's annulment was reversed under Mary I. Sources disagree
  on whether Catherine Howard's marriage was formally annulled before her
  execution, so it is recorded as `ended`.

Rebuild the page from the workflow folder:

```bash
python run_local.py examples/henry_viii
```
