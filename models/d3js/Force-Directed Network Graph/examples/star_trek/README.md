# Worked example: Star Trek crews

Example data for the [d3.js Force-Directed Network Graph](../../README.md):
the main crews of four Star Trek TV series, *The Original Series*, *The Next
Generation*, *Deep Space Nine* and *Voyager*. It covers their ships and
station, the characters who cross between series, and a few families and
romances. Films and later series are out of scope.

| file | what |
|---|---|
| `nodes.csv`, `edges.csv` | 56 nodes (46 characters, 4 series, 6 ships and stations), 124 relationships, written by hand. These CSVs are the source; there is no build script. |
| `params.json` | The model parameters used. |
| `Star_Trek_Network.html` | The page `run_local.py` produces from this folder. |

**What it teaches: bridges between communities.**
* **The data has three kinds of node:** characters, the series they appear in
  (`appears_in`: main, recurring or guest, with episodes in `detail`), and
  the ships they serve on (`serves_on`, with the post as `role`). Toggle the
  *cast* chip off to see only the crews and families.
* **Louvain finds the four series** (4 communities, modularity 0.549, at the
  versions in `../../requirements-reference.txt`) without being told which
  character belongs to which show. Crossover characters land where most of
  their links are: Worf, Q, Lwaxana Troi and Alexander with *Deep Space Nine*;
  O'Brien and Keiko with *The Next Generation*.
* **Crossovers are the bridges.** Ranked by betweenness centrality, measured
  separately with `networkx.betweenness_centrality` (the page doesn't show
  it), the top characters are:
  * **Quark**: his scene in the *Voyager* pilot "Caretaker" links *Deep
    Space Nine* to *Voyager*;
  * **Sulu**: "Flashback" puts him in *Voyager* as captain of the
    Excelsior, where Tuvok served under him;
  * **Q**: appears in three series.

  Pin one of them to see the two crews it joins.
* The series nodes have the highest PageRank (*The Next Generation* is top),
  because every character links to at least one. That is a property of a
  graph that mixes node types: a hub can be a category, not a person.

**Sources.** Every relationship links to the English Wikipedia page that
supports it (`source` column). The crossovers, families, marriages and posts
were checked against those pages on 2026-11-26. Notes:
* Odo's marriage to Lwaxana Troi ("The Muse") is recorded as brief (`ended`).
  The pages say only that it voided Jeyal's claim to her unborn child.
* Dukat is the station's *former commanding officer*, from when it was Terok
  Nor.
* Jadzia and Ezri Dax are linked as successive hosts of the Dax symbiont.

No logo is included. Star Trek names and logos are trademarks of their
owners; this example uses only facts about the shows, linked to their
sources.
