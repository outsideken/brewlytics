"""Shared fixtures: run the brew script through run_local.py's stand-in module."""

import json
import sys
from pathlib import Path

import pandas as pd
import pytest

HERE = Path(__file__).resolve().parent.parent          # the workflow folder
sys.path.insert(0, str(HERE))

import run_local  # noqa: E402

PARAMS = {'Timeline Title': 'Test timeline', 'Timeline Filename': 'test timeline'}


def read(folder, name='events.csv'):
    return pd.read_csv(Path(folder) / name, dtype=str, keep_default_na=False)


@pytest.fixture
def template_events():
    """A fresh copy of the template events table."""
    return read(HERE / 'template')


@pytest.fixture
def run(tmp_path):
    """Run the script on an events table; return (outputs, stats dict, page text)."""
    def _run(events, params=None, resources=()):
        out = run_local.run([events], params or PARAMS, resources, tmp_path)
        page = (tmp_path / out.resource).read_text(encoding='utf-8')
        return out, json.loads(out.string), page
    return _run


def page_data(page):
    """The data embedded in a page."""
    import re
    return json.loads(re.search(r'<script id="timeline-data" type="application/json">(.*?)</script>',
                                page, re.DOTALL).group(1))
