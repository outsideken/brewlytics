# Worked example: Henry VIII, his wives and lineage

Example data for the [d3.js Force-Directed Network Graph](../../README.md).
It covers Henry VIII's six marriages, the wives' parents and siblings,
Henry's own parents and siblings, his children, the Tudor succession through
to James VI and I, and the three popes who shaped his marriages.

| file | what |
|---|---|
| `nodes.csv`, `edges.csv` | 47 people, 80 relationships, written by hand. These CSVs are the source; there is no build script. |
| `params.json` | The model parameters used. |
| `Henry_VIII_Network.html` | The page `run_local.py` produces from this folder. |
| `Coat_of_Arms_of_Henry_VIII_of_England_(1509-1547).png` | Header image: Henry VIII's coat of arms, by Sodacan, from [Wikimedia Commons](https://commons.wikimedia.org/wiki/File:Coat_of_Arms_of_Henry_VIII_of_England_(1509-1547).svg). Licensed **CC BY-SA 3.0** ([licence](https://creativecommons.org/licenses/by-sa/3.0/)) or GFDL 1.2+, and so is this copy; it is *not* covered by this repo's CC0. **Changed:** rendered from the 1.9 MB SVG to a 168 × 168 px PNG (3× its on-page size), so the page stays small. The page credits it in the Data Sources line. Coats of arms are insignia, and their use is restricted in some countries independently of copyright. |

**What it teaches.**
* **A family tree drawn as a network:** parents, siblings and spouses, plus
  three smaller categories:
  * *succession*: who succeeded whom;
  * *politics*: Thomas Cromwell brokering the Anne of Cleves marriage, and
    Edward Seymour as Lord Protector;
  * *church*:
    * Julius II's 1503 dispensation that let Henry marry his brother's widow;
    * Clement VII refusing to annul that marriage, then excommunicating Henry;
    * Paul III's final excommunication in 1538.

    Clement VII was born a Medici; the family is in the Florentine families
    example.
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
  PageRank. Louvain finds 6 communities (modularity 0.562) at the versions in
  `../../requirements-reference.txt`, and each is a recognisable faction:
  * Henry with the popes, his mistress Elizabeth Blount and their son;
  * his parents and sisters, with the sisters' Scottish, French and Brandon
    marriages;
  * Catherine of Aragon's family, joined with Mary I and the later monarchs
    through the succession;
  * the Seymours, who pull in Catherine Parr through her last husband,
    Thomas Seymour;
  * the Boleyns and the Howards together, since the Duke of Norfolk was uncle
    to two of the wives;
  * Cleves, with Cromwell.
* **Communities shift when the data changes:** before the three popes were
  added there were 7 communities, and Henry's sisters, Aragon and the Scottish
  line were split differently. Louvain optimises the whole graph, so three new
  nodes can reshuffle groups that they never touch.

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
