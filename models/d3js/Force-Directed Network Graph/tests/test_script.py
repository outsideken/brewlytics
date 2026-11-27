"""Behaviour of the brew script on small, generic data."""

import re
import shutil
import subprocess

import pandas as pd
import pytest

from conftest import HERE


def test_template_runs(template_tables, run):
    nodes, edges = template_tables
    out, stats, page = run(nodes, edges)
    assert stats['Overall Stats']['# of Nodes'] == len(nodes)
    assert stats['Overall Stats']['# of Relationships'] == len(edges)
    assert stats['Parameters']['Network Graphic Title'] == 'Test graph'
    assert len(out.table) == len(nodes)
    assert '<title>Test graph</title>' in page


def test_table_order_does_not_matter(template_tables, run, tmp_path):
    import run_local
    nodes, edges = template_tables
    params = {'Network Graphic Title': 't', 'Network Graphic Filename': 'a'}
    a = run_local.run([nodes, edges], params, (), tmp_path / 'a')
    b = run_local.run([edges, nodes], params, (), tmp_path / 'b')
    assert a.string == b.string


@pytest.mark.parametrize('given, expected', [
    ('The Simple Network.png', 'The_Simple_Network.html'),
    ('graph', 'graph.html'),
    ('my.graph.html', 'my.graph.html'),
])
def test_filename(template_tables, run, given, expected):
    nodes, edges = template_tables
    out, _, _ = run(nodes, edges, {'Network Graphic Title': 't', 'Network Graphic Filename': given})
    assert out.resource == expected


def test_unknown_edge_id_is_named(template_tables, run):
    nodes, edges = template_tables
    edges.loc[0, 'to_id'] = 'nobody'
    with pytest.raises(ValueError, match=r"edge ids not in the nodes table: \['nobody'\]"):
        run(nodes, edges)


def test_duplicate_node_id_is_named(template_tables, run):
    nodes, edges = template_tables
    nodes.loc[1, 'id'] = nodes.loc[0, 'id']
    with pytest.raises(ValueError, match=nodes.loc[0, 'id']):
        run(nodes, edges)


def test_label_column_is_optional(template_tables, run):
    nodes, edges = template_tables
    out, _, page = run(nodes, edges.drop(columns='label'))
    assert len(out.table) == len(nodes)


def test_no_image_means_no_logo(template_tables, run):
    nodes, edges = template_tables
    _, _, page = run(nodes, edges)
    assert '<img class="logo"' not in page


def test_image_is_embedded_inline(template_tables, run):
    nodes, edges = template_tables
    logo = HERE / 'examples' / 'simpsons' / 'The_Simpsons_logo.svg'
    _, _, page = run(nodes, edges, resources=[str(logo)])
    assert '<img class="logo" src="data:image/svg+xml;base64,' in page


def test_data_cannot_close_the_script_tag(template_tables, run):
    nodes, edges = template_tables
    edges.loc[0, 'detail'] = '</script><script>alert(1)</script>'
    _, _, page = run(nodes, edges)
    assert '</script><script>alert(1)' not in page


def test_title_is_escaped(template_tables, run):
    nodes, edges = template_tables
    _, _, page = run(nodes, edges, {'Network Graphic Title': '<b>x</b>', 'Network Graphic Filename': 't'})
    assert '<b>x</b>' not in page


# ---------------------------------------------------------------------------
# safeUrl / safeLink: run the page's own JavaScript in node.

URLS = {
    'https://example.org/ok': 'https://example.org/ok',
    'http://example.org/': 'http://example.org/',
    'HTTPS://EXAMPLE.ORG/x': 'https://example.org/x',
    '  https://example.org/pad  ': 'https://example.org/pad',
    'javascript:alert(1)': None,
    'JavaScript:alert(1)': None,
    ' javascript:alert(1)': None,
    'java\tscript:alert(1)': None,
    'data:text/html,<script>alert(1)</script>': None,
    'vbscript:msgbox(1)': None,
    'file:///etc/passwd': None,
    'relative/page.html': None,
    '//example.org/protocol-relative': None,
    '': None,
}


@pytest.mark.skipif(shutil.which('node') is None, reason='node is not installed')
def test_safe_url_allows_only_http_and_https(template_tables, run):
    nodes, edges = template_tables
    _, _, page = run(nodes, edges)
    js = re.search(r'(const esc = .*?\nconst safeLink = [^\n]*\n)', page, re.DOTALL).group(1)
    import json
    probe = js + 'const cases = %s;\nconsole.log(JSON.stringify(cases.map((u) => [safeUrl(u), safeLink(u, "t")])));' \
        % json.dumps(list(URLS))
    got = json.loads(subprocess.run(['node', '-e', probe], capture_output=True, text=True, check=True).stdout)
    for (url, expected), (safe, link) in zip(URLS.items(), got):
        assert safe == expected, url
        if expected is None:
            assert link == '', url
        else:
            assert link.startswith('<a href="https://') or link.startswith('<a href="http://'), url
            assert 'rel="noopener"' in link


def page_data(page):
    import json
    return json.loads(re.search(r'<script id="graph-data" type="application/json">(.*?)</script>',
                                page, re.DOTALL).group(1))


def test_two_relationships_between_one_pair_share_a_link(template_tables, run):
    nodes, edges = template_tables
    extra = edges.iloc[[0]].assign(relationship='colleague_of', label='colleague of', category='work')
    _, stats, page = run(nodes, pd.concat([edges, extra], ignore_index=True))
    assert stats['Overall Stats']['# of Relationships'] == len(edges) + 1
    pair = [l for l in page_data(page)['links'] if {l['source'], l['target']} == {'alex', 'blair'}]
    assert len(pair) == 1 and sorted(r['category'] for r in pair[0]['rels']) == ['family', 'work']


def test_isolated_node_is_kept(template_tables, run):
    nodes, edges = template_tables
    nodes = pd.concat([nodes, nodes.iloc[[0]].assign(id='loner', name='Loner')], ignore_index=True)
    out, _, page = run(nodes, edges)
    assert 'Loner' in set(out.table['Node'])
    assert 'loner' in {n['id'] for n in page_data(page)['nodes']}


# ---------------------------------------------------------------------------
# Optional weight column

def test_weight_column_is_optional(template_tables, run):
    nodes, edges = template_tables
    _, stats, page = run(nodes, edges.drop(columns='weight'))
    assert stats['Overall Stats']['Weighted'] is False
    assert all('weight' not in l for l in page_data(page)['links'])


def test_blank_weight_counts_as_one(template_tables, run):
    nodes, edges = template_tables
    assert edges.loc[5, 'weight'] == ''              # the template leaves one blank
    _, stats, page = run(nodes, edges)
    assert stats['Overall Stats']['Weighted'] is True
    link = [l for l in page_data(page)['links'] if {l['source'], l['target']} == {'blair', 'casey'}][0]
    assert link['weight'] == 1


@pytest.mark.parametrize('bad', ['0', '-2', 'heavy'])
def test_bad_weight_is_named(template_tables, run, bad):
    nodes, edges = template_tables
    edges.loc[0, 'weight'] = bad
    with pytest.raises(ValueError, match=r'weight must be a positive number: \[.alex -> blair'):
        run(nodes, edges)


def test_link_weight_is_the_pair_total(template_tables, run):
    nodes, edges = template_tables
    extra = edges.iloc[[0]].assign(relationship='colleague_of', label='colleague of', category='work', weight='4')
    _, _, page = run(nodes, pd.concat([edges, extra], ignore_index=True))
    link = [l for l in page_data(page)['links'] if {l['source'], l['target']} == {'alex', 'blair'}][0]
    assert link['weight'] == 7 and sorted(r['weight'] for r in link['rels']) == [3, 4]


def test_weights_change_pagerank(template_tables, run):
    nodes, edges = template_tables
    plain, _, _ = run(nodes, edges.drop(columns='weight'))
    heavy = edges.assign(weight='1')
    heavy.loc[heavy['to_id'] == 'city', 'weight'] = '50'
    weighted, _, _ = run(nodes, heavy)
    pr = lambda out: dict(zip(out.table['Node'], out.table['Pagerank (Undirected)']))
    assert pr(weighted)['Example City'] > pr(plain)['Example City']


def test_equal_weights_match_unweighted(template_tables, run):
    """Weight 1 everywhere gives the same statistics as no weight column."""
    nodes, edges = template_tables
    _, plain, _ = run(nodes, edges.drop(columns='weight'))
    _, ones, _ = run(nodes, edges.assign(weight='1'))
    a, b = plain['Overall Stats'], ones['Overall Stats']
    assert a.pop('Weighted') is False and b.pop('Weighted') is True
    assert a == b


## --- Schema: your own column names --------------------------------------

PARAMS = {'Network Graphic Title': 't', 'Network Graphic Filename': 'g'}
RENAMES_N = {'id': 'key', 'name': 'Label', 'ring': 'flag'}
RENAMES_E = {'from_id': 'src', 'to_id': 'dst', 'relationship': 'rel', 'directed': 'one_way'}


def with_schema(**schema):
    return {**PARAMS, 'Schema': schema}


def test_schema_maps_renamed_columns(template_tables, run):
    """Renamed columns plus a Schema give exactly the stats of the default names."""
    nodes, edges = template_tables
    _, plain, _ = run(nodes, edges, PARAMS)
    _, mapped, _ = run(nodes.rename(columns=RENAMES_N), edges.rename(columns=RENAMES_E),
                       with_schema(nodes=RENAMES_N, edges=RENAMES_E))
    assert mapped['Overall Stats'] == plain['Overall Stats']


def test_only_ids_and_ends_are_required(run):
    nodes = pd.DataFrame({'id': ['a', 'b', 'c']})
    edges = pd.DataFrame({'from_id': ['a', 'b'], 'to_id': ['b', 'c']})
    out, stats, page = run(nodes, edges)
    data = page_data(page)
    assert stats['Overall Stats']['# of Edges'] == 4                # undirected by default: both ways
    assert [n['name'] for n in data['nodes']] == ['a', 'b', 'c']    # name defaults to id
    assert {r['category'] for l in data['links'] for r in l['rels']} == {'all'}
    assert data['ring_label'] is None and 'Flagged' in out.table.columns


def test_schema_constant_fills_every_row(template_tables, run):
    nodes, edges = template_tables
    _, stats, page = run(nodes, edges.drop(columns='directed'), with_schema(edges={'directed': True}))
    assert stats['Overall Stats']['# of Edges'] == len(edges)      # every edge one way
    _, _, page = run(nodes, edges, with_schema(edges={'category': {'value': 'tie'}}))
    assert {r['category'] for l in page_data(page)['links'] for r in l['rels']} == {'tie'}


def test_schema_missing_column_is_named(template_tables, run):
    nodes, edges = template_tables
    with pytest.raises(ValueError, match=r"does not have: \['strength'\]"):
        run(nodes, edges, with_schema(edges={'weight': 'strength'}))


@pytest.mark.parametrize('schema, message', [
    ({'colours': {}}, r"unknown Schema keys: \['colours'\]"),
    ({'nodes': {'size': 'radius'}}, r"unknown nodes fields: \['size'\]"),
    ({'edges': {'from_id': True}}, r"must name a column: \['from_id'\]"),
    ({'edges': {'category': {'text': 'x'}}}, r'constants need a "value": \[.category.\]'),
])
def test_bad_schema_is_named(template_tables, run, schema, message):
    nodes, edges = template_tables
    with pytest.raises(ValueError, match=message):
        run(nodes, edges, with_schema(**schema))


def test_ring_label_names_the_ring(template_tables, run):
    nodes, edges = template_tables
    out, _, page = run(nodes, edges, with_schema(ring_label='mission ended'))
    assert 'Mission ended' in out.table.columns
    data = page_data(page)
    assert data['ring_label'] == 'mission ended'
    assert [n['id'] for n in data['nodes'] if n['ring']] == ['casey']


def test_tooltip_shows_extra_columns(template_tables, run):
    nodes, edges = template_tables
    nodes['founded'] = ['', '', '', '', '1999', '']
    _, _, page = run(nodes, edges, with_schema(tooltip=['founded']))
    extra = {n['id']: n['extra'] for n in page_data(page)['nodes']}
    assert extra['acme'] == [['founded', '1999']] and extra['alex'] == []
    with pytest.raises(ValueError, match=r"tooltip columns not in the nodes table: \['size'\]"):
        run(nodes, edges, with_schema(tooltip=['size']))


def test_one_config_string_matches_one_per_parameter(template_tables, tmp_path, monkeypatch):
    """brew may pass the whole configuration as one JSON string, or one string per parameter."""
    import json
    import run_local
    nodes, edges = template_tables
    config = {**PARAMS, 'Data Sources': {'Example': 'https://example.org/'}, 'Schema': {'ring_label': 'x'}}
    real = run_local.fake_brewlytics
    outs = []
    for strings in ([json.dumps(config)], [json.dumps({k: v}) for k, v in config.items()]):
        def fake(tables, params, resources=(), strings=strings):
            mod = real(tables, params, resources)
            mod.inputs.list = strings
            return mod
        monkeypatch.setattr(run_local, 'fake_brewlytics', fake)
        outs.append(run_local.run([nodes, edges], {}, (), tmp_path / str(len(outs))).string)
    assert outs[0] == outs[1]
    assert json.loads(outs[0])['Parameters'] == config


def test_all_blank_column_is_read_as_text(template_tables, run):
    """A column pandas reads as all-NaN floats is filled as text, without a pandas warning."""
    import warnings
    nodes, edges = template_tables
    nodes['aliases'] = float('nan')
    with warnings.catch_warnings():
        warnings.filterwarnings('error', message='.*fill value.*')
        out, _, _ = run(nodes, edges)
    assert set(out.table['Aliases']) == {''}
