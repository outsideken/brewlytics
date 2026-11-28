"""The worked examples: their numbers, their sample pages and their rebuildable data."""

import importlib.util
import json
import re

import pytest

import run_local
from conftest import HERE, page_data

EXAMPLES = HERE / 'examples'

## One entry per example folder.
EXPECTED = {
    'solar_system_discoveries': dict(events=38, groups=7, first='1610', last='2014',
                                     page='Solar_System_Discoveries.html',
                                     kinds={'Ground-based telescope': 32, 'Space telescope': 3, 'Spacecraft': 3}),
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


def test_example_numbers(example):
    name, out, stats, _ = example
    want = EXPECTED[name]
    assert (stats['# of Events'], stats['# of Groups']) == (want['events'], want['groups'])
    assert (stats['First'], stats['Last']) == (want['first'], want['last'])
    assert stats['Events by Kind'] == want['kinds']
    assert out.resource == want['page']


def test_committed_sample_page_is_current(example):
    """The page in the example folder is what the script writes today."""
    name, out, _, out_dir = example
    committed = (EXAMPLES / name / out.resource).read_text(encoding='utf-8')
    fresh = (out_dir / out.resource).read_text(encoding='utf-8')
    assert committed == fresh, 'rerun: python run_local.py examples/%s' % name


@pytest.mark.parametrize('builder', sorted(EXAMPLES.glob('*/source/build_data.py')), ids=lambda p: p.parent.parent.name)
def test_builder_rebuilds_committed_csv(builder, tmp_path):
    spec = importlib.util.spec_from_file_location('build_data', builder)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.main(tmp_path)
    assert (tmp_path / 'events.csv').read_text(encoding='utf-8') == \
        (builder.parent.parent / 'events.csv').read_text(encoding='utf-8')


## The reusable files carry no example's names (the method is the lesson; the data is interchangeable).
EXAMPLE_WORDS = re.compile(r'solar|planet|moon|jupiter|saturn|neptune|pluto|voyager|hubble|galileo|telescope',
                           re.IGNORECASE)


@pytest.mark.parametrize('name', ['d3_timeline.py', 'run_local.py', 'template/events.csv', 'template/params.json'])
def test_reusable_files_are_dataset_agnostic(name):
    hits = sorted({m.group(0).lower() for m in EXAMPLE_WORDS.finditer((HERE / name).read_text())})
    assert not hits, 'example-specific words in %s: %s' % (name, hits)


def test_example_page_embeds_its_eras(example):
    name, out, _, out_dir = example
    params = json.loads((EXAMPLES / name / 'params.json').read_text(encoding='utf-8'))
    data = page_data((out_dir / out.resource).read_text(encoding='utf-8'))
    assert [e['label'] for e in data['eras']] == [e['label'] for e in params.get('Eras', [])]
