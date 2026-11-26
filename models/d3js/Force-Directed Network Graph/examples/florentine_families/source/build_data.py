"""Build nodes.csv + edges.csv for the Florentine families example.

Data: John F. Padgett's Florentine families network (Padgett & Ansell,
"Robust Action and the Rise of the Medici, 1400-1434", *American Journal of
Sociology* 98(6), 1993), as distributed with UCINET in ``PADGETT.DAT``. The
copy here comes from the Pajek data mirror,
https://github.com/bavla/Nets/blob/master/data/Pajek/ucinet/PADGETT.DAT.

The file holds two symmetric 16 x 16 matrices over the same families:
``PADGM`` (marriage ties) and ``PADGB`` (business ties: credit, partnerships,
joint ownership). Each tie becomes one edge, so a pair of families tied both
ways has two edges, one per category. The Pucci have no ties of either kind
and appear as an isolated node.

    python examples/florentine_families/source/build_data.py           # rewrites the example CSVs
    python examples/florentine_families/source/build_data.py OUT_DIR   # writes them elsewhere
"""

import csv
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE / 'PADGETT.DAT'
OUT_DIR = HERE.parent
NODE_COLUMNS = ['id', 'name', 'type', 'aliases', 'deceased', 'notes']
EDGE_COLUMNS = ['from_id', 'to_id', 'relationship', 'label', 'category', 'directed',
                'status', 'role', 'detail', 'source']
SOURCE_URL = 'https://github.com/bavla/Nets/blob/master/data/Pajek/ucinet/PADGETT.DAT'

## UCINET truncates labels to 9 characters; full family names
NAMES = {'ACCIAIUOL': 'Acciaiuoli', 'CASTELLAN': 'Castellani', 'LAMBERTES': 'Lamberteschi',
         'TORNABUON': 'Tornabuoni'}
## matrix label -> (relationship, label, category)
TIES = {'PADGM': ('marriage_tie', 'marriage tie', 'marriage'),
        'PADGB': ('business_tie', 'business tie', 'business')}


def read_dl(path):
    """Parse a UCINET DL file (FULLMATRIX, several levels) -> (labels, {level: matrix})."""
    lines = [l.strip() for l in Path(path).read_text(encoding='utf-8').splitlines() if l.strip()]
    n = int(lines[1].split()[0].split('=')[1])
    labels = lines[lines.index('ROW LABELS:') + 1:][:n]
    i = lines.index('LEVEL LABELS:') + 1
    levels = lines[i:lines.index('DATA:')]
    rows = [[int(x) for x in l.split()] for l in lines[lines.index('DATA:') + 1:]]
    assert len(rows) == n * len(levels), 'expected %d matrix rows' % (n * len(levels))
    return labels, {lv: rows[k * n:(k + 1) * n] for k, lv in enumerate(levels)}


def write(path, columns, rows):
    with open(path, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=columns)
        w.writeheader()
        w.writerows(rows)


def main(out_dir=OUT_DIR):
    out_dir = Path(out_dir)
    labels, matrices = read_dl(SRC)
    names = [NAMES.get(l, l.title()) for l in labels]
    ids = [n.lower() for n in names]
    nodes = [dict(id=i, name=n, type='Family', aliases='', deceased='', notes='')
             for i, n in sorted(zip(ids, names))]
    edges = []
    for level, m in matrices.items():
        rel, label, cat = TIES[level]
        for a in range(len(m)):
            for b in range(len(m)):
                assert m[a][b] == m[b][a], '%s is not symmetric at %s/%s' % (level, labels[a], labels[b])
                if a < b and m[a][b]:
                    x, y = sorted((ids[a], ids[b]))
                    edges.append(dict(from_id=x, to_id=y, relationship=rel, label=label, category=cat,
                                      directed=False, status='', role='', detail='', source=SOURCE_URL))
    edges.sort(key=lambda e: (e['category'], e['from_id'], e['to_id']))
    write(out_dir / 'nodes.csv', NODE_COLUMNS, nodes)
    write(out_dir / 'edges.csv', EDGE_COLUMNS, edges)
    print('%d nodes, %d edges (%s)' % (len(nodes), len(edges),
          ', '.join('%s %d' % (c, sum(e['category'] == c for e in edges)) for c in ('marriage', 'business'))))


if __name__ == '__main__':
    main(*sys.argv[1:2])
