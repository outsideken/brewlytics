# Worked example: when did we find them?

Example data for the [d3.js Timeline](../../README.md): when each planet,
dwarf planet and major moon in the Solar System was discovered, and how.

| file | what |
|---|---|
| `events.csv` | 38 events, one per discovered body. Built by `source/build_data.py`. |
| `source/build_data.py` | Builds `events.csv` from the Force-Directed Network Graph's [Solar System example](../../../Force-Directed%20Network%20Graph/examples/solar_system/), so the facts live in one place. |
| `params.json` | The model configuration: title, filename, data source, Schema, Group Order and one era. |
| `Solar_System_Discoveries.html` | The page `run_local.py` produces from this folder. |

**The data keeps its own column names.** `events.csv` has `body`,
`discovered`, `system`, `method`, `major`, `discovered_by`, `note` and
`source`. The Schema in `params.json` maps them to the timeline's fields,
and adds `discovered_by` to the tooltip.

* `system` is the row: the planet a moon orbits, the asteroid belt, or
  "Beyond Neptune" for Pluto, Eris, Makemake, Arrokoth and their moons.
* `method` is the kind, taken from who made the discovery: an astronomer
  (ground-based telescope), a spacecraft, or the Hubble Space Telescope.
* `major` (emphasis) marks the planets and dwarf planets.

**What it teaches: three eras show up without being labelled.**
* **The telescope era, 1610–1899.** Galileo's four moons of Jupiter, then
  Huygens, Cassini, Herschel and Lassell, then Hall, Barnard and Pickering.
  25 of the 38 bodies here were found by 1899.
* **The long quiet, 1900–1950.** Pluto in 1930, and Miranda and Nereid found
  by Gerard Kuiper in 1948 and 1949, are the only finds.
* **The space age.** The one shaded era starts with Sputnik 1 on 4 October
  1957. After it, new shapes appear alongside the telescope finds: Voyager's moons of Saturn and
  Neptune, and Hubble's finds beyond Neptune. Zoom into 2005 to see the
  busiest year here: Eris, Makemake, Dysnomia, Nix and Hydra.

**What it doesn't show.** The data is the 38 bodies chosen for the network
graph, not every known moon. Since 2000, ground-based surveys have found
many dozens of small moons around Jupiter and well over a hundred around
Saturn, and none of them are here. Earth, the Moon and the planets known
since antiquity (Mercury, Venus, Mars, Jupiter, Saturn) have no discovery
date, so they aren't plotted.

**Sources.** Every event links to the English Wikipedia page that supports
it, inherited from the network graph example, where the claims were
checked on 2026-11-27. The page header links Wikipedia's timeline of
discovery of Solar System planets and their moons.
