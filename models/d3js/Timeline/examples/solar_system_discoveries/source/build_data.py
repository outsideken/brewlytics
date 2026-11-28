"""Build events.csv for the Solar System discoveries timeline.

The facts come from the Force-Directed Network Graph's Solar System example
(its nodes.csv and edges.csv), where every discovery edge cites the English
Wikipedia page that supports it. This script turns each discovered body into
one event:

* body, discovered (year), system (the timeline row);
* method: how it was found, from the discoverer's node type;
* major: Y for planets and dwarf planets;
* discovered_by, note, source.

    python source/build_data.py        # rewrites ../events.csv
"""

import csv
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
NETWORK = HERE.parents[3] / 'Force-Directed Network Graph' / 'examples' / 'solar_system'

METHOD = {'Person': 'Ground-based telescope', 'Spacecraft': 'Spacecraft', 'Space telescope': 'Space telescope'}
MAJOR = {'Planet', 'Dwarf planet'}


def read(name):
    with open(NETWORK / name, encoding='utf-8', newline='') as f:
        return list(csv.DictReader(f))


def system_of(body, node, orbits, region):
    """The timeline row: the planet a moon orbits, or where a Sun-orbiting body sits."""
    parent = orbits.get(body)
    if parent != 'sun':
        return node[parent]['name'] if node[parent]['type'] == 'Planet' else 'Beyond Neptune'
    if region.get(body) == 'asteroid-belt':
        return 'Asteroid belt'
    return node[body]['name'] if node[body]['type'] == 'Planet' else 'Beyond Neptune'


def sentence(text):
    """Capitalise only the first letter (str.capitalize would lowercase names)."""
    return text[:1].upper() + text[1:]


def and_list(names):
    return names[0] if len(names) == 1 else ', '.join(names[:-1]) + ' and ' + names[-1]


def build():
    node = {r['id']: r for r in read('nodes.csv')}
    edges = read('edges.csv')
    orbits = {e['from_id']: e['to_id'] for e in edges if e['relationship'] == 'orbits'}
    region = {e['from_id']: e['to_id'] for e in edges if e['relationship'] == 'member_of'}
    found = defaultdict(list)
    for e in edges:
        if e['relationship'] == 'discovered':
            found[e['to_id']].append(e)

    rows = []
    for body, discoveries in found.items():
        year, _, _ = discoveries[0]['detail'].partition(';')
        assert all(d['detail'].startswith(year) for d in discoveries), body
        notes = [d['detail'].partition(';')[2].strip() for d in discoveries]
        by = [node[d['from_id']]['name'] for d in discoveries]
        methods = {METHOD[node[d['from_id']]['type']] for d in discoveries}
        assert len(methods) == 1, body
        rows.append({'body': node[body]['name'], 'discovered': year.strip(),
                     'system': system_of(body, node, orbits, region),
                     'method': methods.pop(), 'major': 'Y' if node[body]['type'] in MAJOR else '',
                     'discovered_by': and_list(by),
                     'note': sentence('; '.join(n for n in notes if n)),
                     'source': discoveries[0]['source']})
    rows.sort(key=lambda r: (int(r['discovered']), r['body']))
    return rows


def main(out_dir=None):
    out = Path(out_dir) if out_dir else HERE.parent
    rows = build()
    with open(out / 'events.csv', 'w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print('%d events -> %s' % (len(rows), out / 'events.csv'))


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else None)
