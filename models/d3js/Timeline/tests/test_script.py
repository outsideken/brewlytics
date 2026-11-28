"""Behaviour of the brew script on small, generic data."""

import json
import re
import shutil
import subprocess

import pandas as pd
import pytest

from conftest import HERE, PARAMS, page_data


def test_template_runs(template_events, run):
    out, stats, page = run(template_events)
    s = stats['Overall Stats']
    assert s['# of Events'] == len(template_events)
    assert s['# of Groups'] == 3
    assert stats['Parameters']['Timeline Title'] == 'Test timeline'
    assert list(out.table.columns) == ['Group', 'Events', 'First', 'Last', 'Kinds']
    assert '<title>Test timeline</title>' in page


@pytest.mark.parametrize('given, expected', [
    ('My Timeline.png', 'My_Timeline.html'),
    ('timeline', 'timeline.html'),
])
def test_filename(template_events, run, given, expected):
    out, _, _ = run(template_events, {**PARAMS, 'Timeline Filename': given})
    assert out.resource == expected


## --- time values ----------------------------------------------------------

@pytest.mark.parametrize('text, iso, precision', [
    ('1610', '1610-01-01', 'year'),
    ('1610.0', '1610-01-01', 'year'),          # a numeric column read as float
    ('950', '0950-01-01', 'year'),             # padded, so text order is time order
    ('1846-09', '1846-09-01', 'month'),
    ('1846-09-23', '1846-09-23', 'day'),
    ('2024-01-08T14:03:00Z', '2024-01-08T14:03:00', 'datetime'),
    ('2024-01-08T16:03:00+02:00', '2024-01-08T14:03:00', 'datetime'),   # converted to UTC
])
def test_times_are_read(run, text, iso, precision):
    _, _, page = run(pd.DataFrame({'item': ['x'], 'time': [text]}))
    e = page_data(page)['events'][0]
    assert (e['time'], e['precision']) == (iso, precision)


@pytest.mark.parametrize('bad', ['soon', '1846-13', '23/09/1846', ''])
def test_bad_time_is_named(run, bad):
    events = pd.DataFrame({'item': ['fine', 'broken'], 'time': ['2020', bad]})
    with pytest.raises(ValueError, match=r"time must be .*: broken \("):
        run(events)


def test_first_and_last_keep_their_precision(template_events, run):
    out, stats, _ = run(template_events)
    assert (stats['Overall Stats']['First'], stats['Overall Stats']['Last']) == ('2024-01-08', '2025')
    build = out.table.set_index('Group').loc['Build']
    assert (build['First'], build['Last']) == ('2024-03-15', '2024-06-12 14:00:00')


## --- rows, kinds, eras -----------------------------------------------------

def test_group_order_parameter(template_events, run):
    out, _, page = run(template_events, {**PARAMS, 'Group Order': ['Launch', 'Nowhere']})
    assert list(out.table['Group']) == ['Launch', 'Planning', 'Build']   # then by earliest event
    assert page_data(page)['groups'] == ['Launch', 'Planning', 'Build']


def test_without_group_every_event_shares_one_row(run):
    out, _, _ = run(pd.DataFrame({'item': ['a', 'b'], 'time': ['2001', '2002']}))
    assert list(out.table['Group']) == ['all'] and list(out.table['Events']) == [2]


def test_kinds_are_ordered_by_count(template_events, run):
    _, stats, page = run(template_events)
    assert page_data(page)['kinds'] == ['Decision', 'Meeting', 'Milestone', 'Release']
    assert stats['Overall Stats']['Events by Kind'] == {'Decision': 3, 'Meeting': 2, 'Milestone': 2, 'Release': 2}


def test_eras_are_embedded(template_events, run):
    eras = [{'label': 'Open', 'start': '2024-06'}, {'label': 'Closed', 'start': '2024-01-01', 'end': '2024-02-01'}]
    _, _, page = run(template_events, {**PARAMS, 'Eras': eras})
    assert page_data(page)['eras'] == [{'label': 'Open', 'start': '2024-06-01', 'end': None},
                                       {'label': 'Closed', 'start': '2024-01-01', 'end': '2024-02-01'}]


def test_bad_era_is_named(template_events, run):
    with pytest.raises(ValueError, match=r"Eras need a start .*\['Broken'\]"):
        run(template_events, {**PARAMS, 'Eras': [{'label': 'Broken', 'start': 'whenever'}]})


def test_emphasis_is_counted_and_embedded(template_events, run):
    _, stats, page = run(template_events)
    assert stats['Overall Stats']['# of Emphasised'] == 3
    assert sorted(e['item'] for e in page_data(page)['events'] if e['emphasis']) == ['Beta', 'Launch', 'Project started']


## --- Schema -------------------------------------------------------------

RENAMES = {'item': 'what', 'time': 'when', 'group': 'lane', 'kind': 'type'}


def test_schema_maps_renamed_columns(template_events, run):
    _, plain, a = run(template_events)
    _, mapped, b = run(template_events.rename(columns=RENAMES), {**PARAMS, 'Schema': {'events': RENAMES}})
    assert mapped['Overall Stats'] == plain['Overall Stats']
    assert page_data(a)['events'] == page_data(b)['events']


def test_schema_constant_fills_every_row(template_events, run):
    _, stats, _ = run(template_events.drop(columns='kind'), {**PARAMS, 'Schema': {'events': {'kind': {'value': 'task'}}}})
    assert stats['Overall Stats']['Events by Kind'] == {'task': len(template_events)}


def test_missing_required_column_is_named(template_events, run):
    with pytest.raises(ValueError, match=r"no column \['time'\]"):
        run(template_events.drop(columns='time'))


def test_schema_missing_column_is_named(template_events, run):
    with pytest.raises(ValueError, match=r"no column \['lane'\]"):
        run(template_events, {**PARAMS, 'Schema': {'events': {'group': 'lane'}}})


@pytest.mark.parametrize('schema, message', [
    ({'colours': {}}, r"unknown Schema keys: \['colours'\]"),
    ({'events': {'size': 'n'}}, r"unknown events fields: \['size'\]"),
    ({'events': {'time': 2020}}, r"must name a column: \['time'\]"),
    ({'events': {'kind': {'text': 'x'}}}, r'constants need a "value": \[.kind.\]'),
])
def test_bad_schema_is_named(template_events, run, schema, message):
    with pytest.raises(ValueError, match=message):
        run(template_events, {**PARAMS, 'Schema': schema})


def test_tooltip_shows_extra_columns(template_events, run):
    template_events['owner'] = ['Ana'] + [''] * (len(template_events) - 1)
    _, _, page = run(template_events, {**PARAMS, 'Schema': {'tooltip': ['owner']}})
    extra = {e['item']: e['extra'] for e in page_data(page)['events']}
    assert extra['Project started'] == [['owner', 'Ana']] and extra['Launch'] == []
    with pytest.raises(ValueError, match=r"tooltip columns not in the events table: \['cost'\]"):
        run(template_events, {**PARAMS, 'Schema': {'tooltip': ['cost']}})


## --- the brew contract -----------------------------------------------------

def test_one_config_string_matches_one_per_parameter(template_events, tmp_path, monkeypatch):
    """brew may pass the whole configuration as one JSON string, or one string per parameter."""
    import run_local
    config = {**PARAMS, 'Data Sources': {'Example': 'https://example.org/'}, 'Group Order': ['Build']}
    real = run_local.fake_brewlytics
    outs = []
    for strings in ([json.dumps(config)], [json.dumps({k: v}) for k, v in config.items()]):
        def fake(tables, params, resources=(), strings=strings):
            mod = real(tables, params, resources)
            mod.inputs.list = strings
            return mod
        monkeypatch.setattr(run_local, 'fake_brewlytics', fake)
        outs.append(run_local.run([template_events], {}, (), tmp_path / str(len(outs))).string)
    assert outs[0] == outs[1]
    assert json.loads(outs[0])['Parameters'] == config


def test_all_blank_column_is_read_as_text(template_events, run):
    """A column pandas reads as all-NaN floats is filled as text, without a pandas warning."""
    import warnings
    template_events['detail'] = float('nan')
    with warnings.catch_warnings():
        warnings.filterwarnings('error', message='.*fill value.*')
        _, _, page = run(template_events)
    assert {e['detail'] for e in page_data(page)['events']} == {''}


def test_brew_type_suffixes_are_removed(template_events, run):
    out, _, _ = run(template_events.rename(columns={'item': 'item{string}', 'time': 'time{string}'}))
    assert out.table['Events'].sum() == len(template_events)


## --- page safety ----------------------------------------------------------

def test_no_image_means_no_logo(template_events, run):
    assert '<img class="logo"' not in run(template_events)[2]


def test_data_cannot_close_the_script_tag(template_events, run):
    template_events.loc[0, 'detail'] = '</script><script>alert(1)</script>'
    _, _, page = run(template_events)
    assert '</script><script>alert(1)' not in page
    assert page_data(page)['events'][0]['detail'] == '</script><script>alert(1)</script>'


def test_title_is_escaped(template_events, run):
    _, _, page = run(template_events, {**PARAMS, 'Timeline Title': '<b>Bold</b> & co'})
    assert '<title>&lt;b&gt;Bold&lt;/b&gt; &amp; co</title>' in page


URLS = {
    'https://example.org/a?b=1': 'https://example.org/a?b=1',
    'http://example.org/': 'http://example.org/',
    'javascript:alert(1)': None,
    'data:text/html,<b>x</b>': None,
    '/relative/path': None,
    '//example.org/protocol-relative': None,
    '': None,
}


@pytest.mark.skipif(shutil.which('node') is None, reason='node is not installed')
def test_safe_url_allows_only_http_and_https(template_events, run):
    _, _, page = run(template_events)
    js = re.search(r'(const esc = .*?\nconst safeLink = [^\n]*\n)', page, re.DOTALL).group(1)
    probe = js + 'const cases = %s;\nconsole.log(JSON.stringify(cases.map((u) => [safeUrl(u), safeLink(u, "t")])));' \
        % json.dumps(list(URLS))
    got = json.loads(subprocess.run(['node', '-e', probe], capture_output=True, text=True, check=True).stdout)
    for (url, expected), (safe, link) in zip(URLS.items(), got):
        assert safe == expected, url
        if expected is None:
            assert link == '', url
        else:
            assert link.startswith('<a href="http') and 'rel="noopener"' in link, url


@pytest.mark.skipif(shutil.which('node') is None, reason='node is not installed')
def test_page_dates_keep_early_years(template_events, run):
    """The page's toDate keeps years below 100 and before 1678 as written."""
    _, _, page = run(template_events)
    js = re.search(r'(function toDate\(iso\) \{.*?\n\})', page, re.DOTALL).group(1)
    probe = js + '\nconsole.log(JSON.stringify(["0050-03-02", "1610-01-01", "2024-01-08T14:03:00"]' \
                 '.map((t) => toDate(t).toISOString())));'
    got = json.loads(subprocess.run(['node', '-e', probe], capture_output=True, text=True, check=True).stdout)
    assert got == ['0050-03-02T00:00:00.000Z', '1610-01-01T00:00:00.000Z', '2024-01-08T14:03:00.000Z']
