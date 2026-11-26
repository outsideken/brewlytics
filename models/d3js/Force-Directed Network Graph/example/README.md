# Worked example: The Simpsons

Example data for the [d3.js Force-Directed Network Graph](../README.md). It
comes from the original 2019 brewlytics model *The Simpsons: A Network Graph Example*,
which drew a networkx/matplotlib PNG for the now-retired Mission Presenter.

| file | what |
|---|---|
| `nodes.csv`, `edges.csv` | 336 nodes, 536 relationships in the workflow's two-table schema. |
| `params.json` | The model parameters used (title, filename, Data Sources). |
| `The_Simpsons_logo.svg` | Header image: the *The Simpsons* text logo from [Wikimedia Commons](https://commons.wikimedia.org/wiki/File:The_Simpsons_yellow_logo.svg), with the viewBox cropped to the lettering (`0 120 1920 848`). Public domain as a simple text logo, but still a trademark: no endorsement is implied. |
| `The_Simpsons_Network.html` | The page `run_local.py` produces from this folder. |
| `source/` | The original one-table export, the corrected copy, and `convert_schema.py`, which turns the corrected copy into `nodes.csv` + `edges.csv`. |

Result: 14 Louvain communities (modularity 0.709). The highest undirected
PageRank is Springfield Elementary School. Those figures hold at the versions
in `../requirements-reference.txt`; see *Reproducibility* in the main README.

## Rebuilding the data

```bash
python source/convert_schema.py     # rewrites nodes.csv + edges.csv
python ../run_local.py              # rewrites The_Simpsons_Network.html
```

`convert_schema.py` is specific to this dataset. It holds:

* `LABELS`: the mapping from the export's free-text labels to the 29
  relationships;
* the rules that generate the gender-neutral `label` text (`BASE_LABELS`,
  `LABEL_OVERRIDES`, `COMBO_LABELS`, `STORY_LABELS`);
* the node-type rules;
* sourced per-row fixes (`ROW_SOURCES`, `ROW_OVERRIDES`, `EXTRA_EDGES`).

All 733 source rows are accounted for: 52 aliases, 11 notes and 670 edge
labels. The CSVs keep two review columns, `type_rule` and `original_labels`;
the brew script ignores them.

## Corrections made to the original export

* **Name fixes** (10 names, 20 cells): Mona Flander, Barney Gumble, Moe
  Szyslak, L. T.Smash, Mom & Pop Hardware, "Bleeding Gums" Hibbert,
  Springlfield MENSA, Unammed Son, Channel 6 → Channel 6 News, Juillard →
  Juilliard School of Music.
* **Dewey vs Dewey Largo**: two people. Per the Simpsons Wiki (Dewey Largo
  page), Largo's ex-boyfriend is also called Dewey ("Flaming Moe"), so both
  nodes stay. **Geoffrey**, Largo's current boyfriend, was added from the same
  page.
* **Clean-up**: 5 trailing spaces trimmed, 2 × *Fomerly* → *Formerly*, and a
  blank row dropped.
* **Spelling** (14 cells): Springfiled Speedway, Wharton Busines School,
  Reverand (×2), acceptence, pronouced, Puched, tomove, Plantiff, Myster,
  Restaruant, "Invited To to", Sedish, tatto.
* **Mapping fixes**:
  * *Nanny for* → nanny `works_for` child (it was reversed).
  * *Boss of* → `works_for`.
  * *Loves* / *Biggest Fan* → `likes`.
  * *Mentored* / *Learned Jazz from* → `mentor_of`.
* **Row 273**: `Bernice Hibbert · Brother of · Bernice Hibbert` → `Chester
  Dupree · Brother of · Bernice Hibbert` (Simpsons Wiki, Bernice Hibbert
  page).
* **Jub-Jub** (Simpsons Wiki, Jub-Jub Bouvier page): Selma *Adopted* →
  `has_pet`; Aunt Gladys → former owner, deceased; Jacqueline Bouvier added as
  a former owner.

Rows checked against a wiki page carry its URL in `source` (9 edges so far).

**Still to review:** node types (sort `nodes.csv` by `type_rule`) and the
label mapping. Drop the review columns once they're checked.
