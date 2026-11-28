# d3.js Timeline

Turn an **events** table into an interactive d3.js timeline, from a
brewlytics **Python Script** functional. Each event is a mark at its date.
Marks sit on one row per group, and their colour and shape show their kind.
The script writes one self-contained `.html` page that people can download
from `outputs.resource` and open in any browser.

The method is the lesson; the data is interchangeable. The worked example
uses the same unchanged script:

| example | events | groups | what it shows |
|---|---|---|---|
| [Solar System discoveries](examples/solar_system_discoveries/) | 38 | 7 | When each planet, dwarf planet and major moon was found, and how: through a telescope on the ground, by a spacecraft, or by Hubble. Three eras show up without being labelled. |

## What a timeline shows

Time runs left to right on a [d3 time scale](https://d3js.org/d3-scale/time),
so position means *when*, and nothing else. Grouping events into rows lets
you compare when things happened in parallel stories. Colour and shape (one
per kind, so it still reads in greyscale) show *how* or *what kind*. Zooming
along time ([d3-zoom](https://d3js.org/d3-zoom)) opens up crowded periods.

## Files

| file | what |
|---|---|
| `d3_timeline.py` | **Paste into the brew Python Script functional.** The same file runs locally and in CI. |
| `run_local.py` | Runs that script here with a stand-in `brewlytics` module. |
| `template/` | Minimal `events.csv` and `params.json` showing every column and parameter. Start your own data here. |
| `examples/` | Worked examples, one folder each: data, `params.json`, sample page, README, and the `source/` used to build the data. |
| `tests/` | pytest suite; CI runs it on every pull request. |
| `requirements*.txt` | What the script needs (pandas), the reference pins and the floor pins. |

## Run locally

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt pytest
.venv/bin/python run_local.py                                      # template/ -> template/timeline.html
.venv/bin/python run_local.py examples/solar_system_discoveries   # -> its Solar_System_Discoveries.html
.venv/bin/python -m pytest tests
```

A data folder holds `events.csv`, `params.json` (the model configuration)
and, optionally, one image to use as the header logo.

## Data model

One table, one row per event. These are the default column names; the
[Schema](#schema-your-own-column-names) maps them to yours. Only `item` and
`time` are required.

**events**: `item, time, group, kind, emphasis, detail, source`

* `item`: what happened or was found; the mark's name.
* `time`: a year (`1610`), a month (`1846-09`), a day (`1846-09-23`), or an
  ISO date-time (`2024-01-08T14:03:00Z`). Date-times with an offset are
  converted to UTC. The page prints each time at its own precision, so a
  year-only date never looks more exact than it is. Years before 1678 work
  (pandas timestamps can't hold them, so the script keeps times as text).
* `group`: the row. Blank or absent puts every event on one row, `all`.
* `kind`: the category for colour, shape and the show/hide chips. The 7
  most common kinds get ColorBrewer Dark2 and their own shape; the rest
  share grey circles.
* `emphasis`: `Y` or blank. Emphasised events get a larger mark and a label.
* `detail`: free text for the tooltip and table. `source`: a URL, shown as a
  link if it is absolute `http(s)`.

Extra columns are ignored, unless the Schema's `tooltip` lists them.

### Schema: your own column names

```json
"Schema": {
  "events": {"item": "body", "time": "discovered", "group": "system",
             "kind": "method", "emphasis": "major", "detail": "note"},
  "tooltip": ["discovered_by"]
}
```

* In `events`, the keys are the field names above.
  * A **string** names one of your columns.
  * Any other value is a **constant** for every row: `true`/`false`, a
    number, or `{"value": "text"}` for text.
* `tooltip`: extra columns shown in each event's tooltip, as `column: value`.
* Mistakes stop the run with a message: an unknown key or field, or a
  column the table doesn't have.

This works the same way as the Force-Directed Network Graph's Schema.

## Brew model wiring

```
CSV to Table (events) ─┐
model configuration ───┼─► Python Script (d3_timeline.py) ─► Timeline Stats (JSON)
image resource (opt.) ─┘                                  ─► Timeline Table
                                                          ─► Timeline (.html)
```

* **`inputs.tables`**: the events table (the first one wired).
* **`inputs.list`**: the model configuration as JSON. It can be one string
  holding the whole configuration (as in each `params.json`), or one string
  per parameter; the script merges them in order. The parameters:
  * **Timeline Title**
  * **Timeline Filename**: spaces become `_`, and the extension is forced to
    `.html`.
  * **Data Sources** (optional): `{"label": "url", …}`, shown as links under
    the title.
  * **Schema** (optional): your column names.
  * **Group Order** (optional): the rows, top first, e.g.
    `["Planning", "Build", "Launch"]`. Groups not listed follow, earliest
    first. Without it, rows are ordered by their earliest event.
  * **Eras** (optional): shaded bands with a label, e.g.
    `[{"label": "Beta period", "start": "2024-06-01", "end": "2024-09-02"}]`.
    Leave out `end` to run to the last event.
* **`inputs.resources`** (optional): the first `.svg/.png/.jpg/.webp/.gif` is
  embedded beside the title as a data URI, so the page stays one file.
* **Bad data stops the run.** A time or era that can't be read, or a Schema
  that names a missing column, raises a `ValueError` that names it.

| brew output | from | contents |
|---|---|---|
| Timeline Stats | `outputs.string` | `Overall Stats` (# of events, # of groups, first and last, # emphasised, events by kind) + the `Parameters` used |
| Timeline Table | `outputs.table` | one row per group, in row order: Group, Events, First, Last, Kinds |
| Timeline | `outputs.resource` | the downloadable d3 page |

## The page

* **Rows**: one per group, in the Group Order. Marks that would overlap are
  nudged up or down their row.
* **Marks**: colour and shape by kind; emphasised events are larger and
  labelled.
* **Eras**: shaded bands behind the rows, labelled at the top.
* **Controls**:
  * scroll or pinch to zoom in time, drag to pan, and **Reset view** to go
    back;
  * kind chips show or hide each kind;
  * hover previews an event, and a click pins it.
* **Table view** (collapsed by default): the events currently shown. Click a
  header to sort.
* **Links**: URLs from the data become links only if they are absolute
  `http://` or `https://`. Anything else (`javascript:`, `data:`, relative
  paths) is dropped, so a shared page can't run script hidden in a link.
* d3 7.9.0 is loaded from cdn.jsdelivr.net. Light and dark follow the
  viewer's system setting.

## Reproducibility

* The committed example page is exactly what `run_local.py` writes today; a
  test checks it.
* The example's `source/build_data.py` rebuilds its `events.csv`; a test
  checks that too.
* The reusable files (script, runner, template) carry no example's names; a
  test checks that as well.
