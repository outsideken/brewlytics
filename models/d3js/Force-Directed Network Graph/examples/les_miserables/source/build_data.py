"""Build nodes.csv + edges.csv for the Les Misérables example.

Data: Donald E. Knuth's character co-appearance network for Victor Hugo's
*Les Misérables*, from *The Stanford GraphBase* (1993), as shipped by
networkx (``networkx.les_miserables_graph``). Two characters are linked when
they appear in the same chapter; the edge weight counts those chapters.

That count goes into the optional ``weight`` column, so PageRank and
Louvain are weighted and heavier pairs get thicker links. Names keep Knuth's
spelling, with spaces added (``MlleBaptistine`` -> ``Mlle Baptistine``).

    python examples/les_miserables/source/build_data.py           # rewrites the example CSVs
    python examples/les_miserables/source/build_data.py OUT_DIR   # writes them elsewhere
"""

import csv
import re
import sys
from pathlib import Path

import networkx as nx

OUT_DIR = Path(__file__).resolve().parent.parent
NODE_COLUMNS = ['id', 'name', 'type', 'aliases', 'deceased', 'notes']
EDGE_COLUMNS = ['from_id', 'to_id', 'relationship', 'label', 'category', 'directed',
                'status', 'role', 'detail', 'source', 'weight']


def display_name(knuth):
    """``MlleBaptistine`` -> ``Mlle Baptistine``; ``Child1`` -> ``Child 1``."""
    return re.sub(r'(?<=[a-z])(?=[A-Z0-9])', ' ', knuth)


def slug(text):
    return re.sub(r'[^a-z0-9]+', '-', text.lower()).strip('-')


def write(path, columns, rows):
    with open(path, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=columns)
        w.writeheader()
        w.writerows(rows)


def main(out_dir=OUT_DIR):
    out_dir = Path(out_dir)
    g = nx.les_miserables_graph()
    ids = {n: slug(display_name(n)) for n in g}
    assert len(set(ids.values())) == len(ids), 'duplicate ids'
    nodes = [dict(id=ids[n], name=display_name(n), type='Character', aliases='', deceased='', notes='')
             for n in sorted(g, key=lambda n: ids[n])]
    edges = []
    for a, b, d in g.edges(data=True):
        a, b = sorted((ids[a], ids[b]))       # symmetric: from_id < to_id, as in the other examples
        w = int(d['weight'])
        edges.append(dict(from_id=a, to_id=b, relationship='appears_with', label='appears with',
                          category='co-appearance', directed=False, status='', role='',
                          detail='', source='', weight=w))
    edges.sort(key=lambda e: (e['from_id'], e['to_id']))
    write(out_dir / 'nodes.csv', NODE_COLUMNS, nodes)
    write(out_dir / 'edges.csv', EDGE_COLUMNS, edges)
    print('%d nodes, %d edges' % (len(nodes), len(edges)))


if __name__ == '__main__':
    main(*sys.argv[1:2])
