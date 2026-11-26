"""The worked examples: their numbers, their sample pages and their rebuildable data."""

import importlib.util
import json
import re

import pytest

import run_local
from conftest import HERE

EXAMPLES = HERE / 'examples'

## One entry per example folder. Louvain numbers hold only at the reference pins.
EXPECTED = {
    'simpsons': dict(nodes=336, relationships=536, top='Springfield Elementary School',
                     page='The_Simpsons_Network.html', communities=14, modularity=0.709160),
    'les_miserables': dict(nodes=77, relationships=254, top='Valjean',
                           page='Les_Miserables_Network.html', communities=6, modularity=0.565416),
    'florentine_families': dict(nodes=16, relationships=35, top='Medici',
                                page='Florentine_Families_Network.html', communities=4, modularity=0.316187),
    'star_trek': dict(nodes=56, relationships=124, top='Star Trek: The Next Generation',
                      page='Star_Trek_Network.html', communities=4, modularity=0.549070),
    'henry_viii': dict(nodes=47, relationships=80, top='Henry VIII',
                       page='Henry_VIII_Network.html', communities=6, modularity=0.561899),
}


def test_every_example_has_expectations():
    folders = {p.name for p in EXAMPLES.iterdir() if p.is_dir()}
    assert folders == set(EXPECTED), 'add the new example to EXPECTED'


@pytest.fixture(scope='module', params=sorted(EXPECTED))
def example(request, tmp_path_factory):
    name = request.param
    out_dir = tmp_path_factory.mktemp(name)
    out = run_local.run_folder(EXAMPLES / name, out_dir)
    return name, out, json.loads(out.string)['Overall Stats'], out_dir


def test_example_counts(example):
    name, out, stats, _ = example
    want = EXPECTED[name]
    assert stats['# of Nodes'] == want['nodes']
    assert stats['# of Relationships'] == want['relationships']
    assert stats['Highest Pagerank (Undirected)'].startswith(want['top'] + ' (')
    assert len(out.table) == want['nodes']
    assert out.resource == want['page']


@pytest.mark.reference
def test_example_communities(example):
    """Louvain output depends on the networkx version, so this is checked at the reference pins only."""
    name, _, stats, _ = example
    assert stats['# of Communities'] == EXPECTED[name]['communities']
    assert stats['Modularity'] == pytest.approx(EXPECTED[name]['modularity'], abs=5e-7)


def test_example_table_columns(example):
    _, out, _, _ = example
    assert list(out.table.columns) == ['Node', 'Type', 'Aliases', 'Deceased', 'Community',
                                       'Community Hub', 'Pagerank (Undirected)', 'Pagerank',
                                       'Degree', 'In Degree', 'Out Degree']


DATA_TAG = re.compile(r'(<script id="graph-data" type="application/json">)(.*?)(</script>)', re.DOTALL)


def split_page(page):
    """Return (page with the data replaced by a marker, the embedded data as Python objects)."""
    m = DATA_TAG.search(page)
    return page[:m.start(2)] + '__DATA__' + page[m.end(2):], json.loads(m.group(2))


def same_data(a, b, path='data'):
    """Compare embedded data; floats may differ in the last digits between platforms' BLAS."""
    if isinstance(a, float) or isinstance(b, float):
        assert a == pytest.approx(b, rel=1e-9, abs=1e-12), path
    elif isinstance(a, dict):
        assert a.keys() == b.keys(), path
        for k in a:
            same_data(a[k], b[k], '%s.%s' % (path, k))
    elif isinstance(a, list):
        assert len(a) == len(b), path
        for i, (x, y) in enumerate(zip(a, b)):
            same_data(x, y, '%s[%d]' % (path, i))
    else:
        assert a == b, path


@pytest.mark.reference
def test_committed_sample_page_is_current(example):
    """Each example's committed page must be what the committed script + data produce.

    Markup, CSS and JS must match exactly. The embedded data must match too, but
    floats only to 1e-9 relative: PageRank's last digits differ between macOS and
    Linux builds of numpy/scipy.
    """
    name, out, _, out_dir = example
    fresh_page, fresh_data = split_page((out_dir / out.resource).read_text(encoding='utf-8'))
    old_page, old_data = split_page((EXAMPLES / name / out.resource).read_text(encoding='utf-8'))
    assert fresh_page == old_page, 'rerun `python run_local.py examples/%s` and commit the page' % name
    same_data(fresh_data, old_data)


BUILDERS = sorted(p for p in EXAMPLES.glob('*/source/*.py'))


@pytest.mark.parametrize('builder', BUILDERS, ids=lambda p: p.parent.parent.name)
def test_builder_rebuilds_committed_csvs(builder, tmp_path):
    """An example whose CSVs are generated must be reproducible from its source/ script."""
    spec = importlib.util.spec_from_file_location(builder.stem, builder)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.main(tmp_path)
    for name in ('nodes.csv', 'edges.csv'):
        assert (tmp_path / name).read_bytes() == (builder.parent.parent / name).read_bytes(), name


# Words from the example data that must never appear in the reusable files.
EXAMPLE_WORDS = re.compile(r'simpson|springfield|homer|bart|marge|lisa|maggie|burns|flanders|bouvier'
                           r'|valjean|cosette|javert|thenardier|medici|strozzi|padgett'
                           r'|tudor|boleyn|seymour|cleves|aragon'
                           r'|trek|picard|janeway|sisko|enterprise|klingon', re.IGNORECASE)


@pytest.mark.parametrize('name', ['d3_force_network_graph.py', 'run_local.py',
                                  'template/nodes.csv', 'template/edges.csv', 'template/params.json'])
def test_reusable_files_are_dataset_agnostic(name):
    hits = sorted({m.group(0).lower() for m in EXAMPLE_WORDS.finditer((HERE / name).read_text())})
    assert not hits, 'example-specific words in %s: %s' % (name, hits)


# Relationship wording must be gender-neutral (AGENTS.md). Titles of office
# ("Lord Protector") are names, not relationship wording, so they're not listed.
# "aunt/uncle of" is the accepted paired form; a bare "aunt" or "uncle" is not.
GENDERED = re.compile(r'\b(girlfriend|boyfriend|husband|wife|wives|widow|widower|mother|father|son|daughter'
                      r'|brother|sister|grandfather|grandmother|grandson|granddaughter|paternal|maternal'
                      r'|nephew|niece|mistress)\b|(?<!/)\buncle\b|\baunt\b(?!/)', re.IGNORECASE)


@pytest.mark.parametrize('name', sorted(EXPECTED))
def test_labels_and_roles_are_gender_neutral(name):
    import csv
    hits = []
    with open(EXAMPLES / name / 'edges.csv', encoding='utf-8') as f:
        for r in csv.DictReader(f):
            for col in ('label', 'role'):
                if GENDERED.search(r.get(col) or ''):
                    hits.append('%s -> %s %s=%r' % (r['from_id'], r['to_id'], col, r[col]))
    assert not hits, hits
