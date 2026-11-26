"""Shared fixtures: run the brew script through run_local.py's stand-in module."""

import json
import sys
from pathlib import Path

import pandas as pd
import pytest

HERE = Path(__file__).resolve().parent.parent          # the workflow folder
sys.path.insert(0, str(HERE))

import run_local  # noqa: E402


def pytest_configure(config):
    config.addinivalue_line(
        'markers', 'reference: exact results that hold only at the versions in '
                   'requirements-reference.txt (Louvain output changes between networkx releases)')


def read(folder, name):
    return pd.read_csv(Path(folder) / name, dtype=str, keep_default_na=False)


@pytest.fixture
def template_tables():
    """Fresh copies of the template nodes + edges tables."""
    return read(HERE / 'template', 'nodes.csv'), read(HERE / 'template', 'edges.csv')


@pytest.fixture
def run(tmp_path):
    """Run the script on (nodes, edges); return (outputs, stats dict, page text)."""
    def _run(nodes, edges, params=None, resources=()):
        params = params or {'Network Graphic Title': 'Test graph',
                            'Network Graphic Filename': 'test graph'}
        out = run_local.run([edges, nodes], params, resources, tmp_path)
        page = (tmp_path / out.resource).read_text(encoding='utf-8')
        return out, json.loads(out.string), page
    return _run
