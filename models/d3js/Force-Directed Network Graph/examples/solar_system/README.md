# Worked example: the Solar System

Example data for the [d3.js Force-Directed Network Graph](../../README.md):
the Sun, the planets, the dwarf planets, the major moons and a few small
bodies, plus the spacecraft that explored them and the astronomers who
discovered them.

| file | what |
|---|---|
| `nodes.csv`, `edges.csv` | 89 nodes (55 bodies, rings and regions; 15 spacecraft and a telescope; 18 astronomers), 159 relationships, written by hand. These CSVs are the source; there is no build script. |
| `params.json` | The model parameters used. |
| `Solar_System_Network.html` | The page `run_local.py` produces from this folder. |

**What it teaches: a network is more than its hierarchy.**
* **Orbits alone would be a tree.** Every moon `orbits` a planet and every
  planet `orbits` the Sun. Louvain would just return the planet systems.
  Toggle every chip off except *orbit* to see that tree.
* **Other kinds of tie cut across it:**
  * *exploration*: `flew_by`, `orbited`, `landed_on` and `sampled`, with
    the years in `detail`;
  * *discovery*: who `discovered` each body, and when;
  * *resonance*: orbital resonances, plus the Janus–Epimetheus orbit swap,
    Pluto and Charon's mutual tidal lock and Prometheus shepherding the F
    ring;
  * *region*: the asteroid belt, the Kuiper belt and the scattered disc;
  * *naming*: spacecraft and the Kuiper belt `named_after` astronomers.
* **Louvain finds six communities** (modularity 0.615, at the versions in
  `../../requirements-reference.txt`). Planet systems seed most of them, but
  the other ties decide the borders:
  * **Uranus and Neptune share one.** Voyager 2 visited both, and William
    Herschel, William Lassell and Gerard Kuiper discovered moons of both.
  * **Hyperion joins them, not Saturn**, through its three discoverers: the
    two Bonds and Lassell.
  * **Mars takes the asteroid belt.** Dawn flew past Mars on the way to Vesta
    and Ceres, and Rosetta flew past Mars on the way to its comet.
  * **Mercury and Venus join Earth**, through gravity-assist flybys
    (MESSENGER, Galileo, Cassini) and the missions that mapped them.
  * **Pluto, the Kuiper belt and the Hubble Space Telescope stay with the
    Sun.** Hubble found Nix, Hydra and Arrokoth.
* **Names repeat across node types.** Galileo, Cassini and Huygens are each
  an astronomer *and* a spacecraft. The `named_after` edge links each pair
  of nodes.
* **Two kinds of hub.** On the undirected graph, Saturn has the highest
  PageRank (it has the most moons here, plus Cassini). On the directed
  graph, the Sun is highest, because every `orbits` link points inwards.

**Sources.** Every relationship links to the English Wikipedia page that
supports it (`source` column). The claims were checked against those pages
on 2026-11-27. Notes:
* **Resonance ratios read from → to**, and `detail` spells them out: "Io
  orbits twice for each Europa orbit". Mimas–Tethys is written 4:2, as
  Wikipedia gives it, not 2:1.
* **Pandora is not linked to the F ring.** It was once thought to shepherd
  the ring's outer edge, but recent studies say it does not (see its node
  note).
* **Credit for some discoveries is shared or disputed:**
  * Mike Brown discovered Eris and Makemake with Chad Trujillo and David
    Rabinowitz, who are not nodes.
  * Haumea has no discoverer edge, because credit for it is disputed.
  * Le Verrier `predicted` Neptune and Galle `discovered` it.
* **Moon counts change**, so the data includes only the major named moons.
  Saturn and Jupiter each have many more.
* **`deceased` is set for the astronomers who have died.** Their nodes get the
  ring. It is blank for bodies and spacecraft.
