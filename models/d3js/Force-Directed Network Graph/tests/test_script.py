"""Behaviour of the brew script on small, generic data."""

import re
import shutil
import subprocess

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
    logo = HERE / 'example' / 'The_Simpsons_logo.svg'
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
