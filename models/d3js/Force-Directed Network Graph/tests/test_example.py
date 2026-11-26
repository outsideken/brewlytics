"""The worked example: its numbers, its sample page and its rebuildable data."""

import importlib.util
import json
import re
from pathlib import Path

import pytest

import run_local
from conftest import HERE

EXAMPLE = HERE / 'example'


@pytest.fixture(scope='module')
def example(tmp_path_factory):
    out_dir = tmp_path_factory.mktemp('example')
    out = run_local.run_folder(EXAMPLE, out_dir)
    return out, json.loads(out.string)['Overall Stats'], out_dir


def test_example_counts(example):
    _, stats, _ = example
    assert stats['# of Nodes'] == 336
    assert stats['# of Relationships'] == 536
    assert stats['Highest Pagerank (Undirected)'].startswith('Springfield Elementary School')


@pytest.mark.reference
def test_example_communities(example):
    """Louvain output depends on the networkx version, so this is checked at the reference pins only."""
    _, stats, _ = example
    assert stats['# of Communities'] == 14
    assert stats['Modularity'] == pytest.approx(0.709160, abs=5e-7)


def test_example_table(example):
    out, _, _ = example
    assert len(out.table) == 336
    assert list(out.table.columns) == ['Node', 'Type', 'Aliases', 'Deceased', 'Community',
                                       'Community Hub', 'Pagerank (Undirected)', 'Pagerank',
                                       'Degree', 'In Degree', 'Out Degree']


@pytest.mark.reference
def test_committed_sample_page_is_current(example):
    """example/The_Simpsons_Network.html must be what the committed script + data produce."""
    out, _, out_dir = example
    assert out.resource == 'The_Simpsons_Network.html'
    fresh = (out_dir / out.resource).read_text(encoding='utf-8')
    committed = (EXAMPLE / out.resource).read_text(encoding='utf-8')
    assert fresh == committed, 'rerun `python run_local.py` and commit the page'


def test_converter_rebuilds_committed_csvs(tmp_path):
    path = EXAMPLE / 'source' / 'convert_schema.py'
    spec = importlib.util.spec_from_file_location('convert_schema', path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.main(tmp_path)
    for name in ('nodes.csv', 'edges.csv'):
        assert (tmp_path / name).read_bytes() == (EXAMPLE / name).read_bytes(), name


# Words from the example data that must never appear in the reusable files.
EXAMPLE_WORDS = re.compile(r'simpson|springfield|homer|bart|marge|lisa|maggie|burns|flanders|bouvier',
                           re.IGNORECASE)


@pytest.mark.parametrize('name', ['d3_force_network_graph.py', 'run_local.py',
                                  'template/nodes.csv', 'template/edges.csv', 'template/params.json'])
def test_reusable_files_are_dataset_agnostic(name):
    hits = sorted({m.group(0).lower() for m in EXAMPLE_WORDS.finditer((HERE / name).read_text())})
    assert not hits, 'example-specific words in %s: %s' % (name, hits)
