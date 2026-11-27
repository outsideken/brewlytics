"""
Build a d3.js force-directed network graph page from a nodes table and an
edges table (Brewlytics Python Script functional).

The script reads the two tables, validates them, computes graph statistics
with networkx, finds Louvain communities, and writes one self-contained
interactive HTML page. The page has CSS, JavaScript, data and header image
inline; only d3 is loaded from a CDN.

Inputs
------
inputs.tables : list of pandas.DataFrame
    The nodes table and the edges table, in either order. The edges table
    is the one with the ``from_id`` and ``to_id`` columns; the nodes table
    is the other one with an ``id`` column. Other columns are ignored
    unless the Schema lists them in ``tooltip``.

    The column names below are the defaults; the Schema parameter maps
    them to other names. Only ``id``, ``from_id`` and ``to_id`` are
    required.

    nodes : ``id`` (+ optional ``name, type, aliases, ring, notes``)
        ``name`` defaults to ``id``. ``aliases`` and ``notes`` are
        ``"; "``-separated. ``ring`` is ``Y`` or blank; ringed nodes are
        drawn with an outline, and ``ring_label`` says what it means.
    edges : ``from_id, to_id`` (+ optional ``relationship, label, category,
    directed, status, role, detail, source, weight``)
        One row per fact. ``label`` is the short text drawn on the link
        (defaults to ``relationship``). ``category`` defaults to
        ``relationship``. ``directed`` is True/False (default False);
        symmetric relationships (A relates to B the same way B relates to
        A) are False. ``weight`` is a positive number (blank = 1); with
        it, PageRank and Louvain are weighted and link width shows the
        weight. Without it, every relationship counts once.
inputs.list : list of str
    JSON objects, merged in order. One string holding the whole
    configuration works, and so does one string per parameter.

    Network Graphic Title : str
        Page title.
    Network Graphic Filename : str
        Output file name; spaces become ``_`` and the extension is forced
        to ``.html``.
    Data Sources : str or dict, optional
        JSON ``{"label": "url", ...}``, shown as links under the title.
    Schema : str or dict, optional
        Which of your columns fills each field::

            {"nodes": {"id": "body_id", "ring": "deceased"},
             "edges": {"from_id": "src", "to_id": "dst", "directed": true},
             "ring_label": "deceased",
             "tooltip": ["radius_km"]}

        In ``nodes`` and ``edges``, a string names a column; any other
        value (``true``, a number, or ``{"value": "text"}``) is a constant
        for every row. Unmapped fields use the default column name if the
        table has it. ``ring_label`` (default ``"flagged"``) names the
        ring in the legend, tooltip and Network Table. ``tooltip`` lists
        extra nodes-table columns shown in the tooltip.
inputs.resources : list of str, optional
    The first image (``.svg .png .jpg .jpeg .webp .gif``) is embedded beside
    the title. No image means no logo.

Outputs
-------
outputs.string : str
    Network Stats (JSON): ``{"Overall Stats": {...}, "Parameters": {...}}``.
outputs.table : pandas.DataFrame
    Network Table: one row per node (type, aliases, community, PageRank,
    degree centralities), highest undirected PageRank first.
outputs.resource : str
    Network Graph: file name of the downloadable d3 page.

Raises
------
ValueError
    If the Schema has an unknown key or names a column a table lacks, the
    nodes or edges table can't be identified, node ids are duplicated, an
    edge refers to an id that is not in the nodes table, or a weight is not
    a positive number.

Notes
-----
Node size on the page is PageRank computed on the undirected graph, because
directed PageRank inflates dead-end nodes. Louvain is randomised; ``SEED``
makes the communities repeatable for the same data.
"""

from brewlytics import *

## for more information see the associated markdown file (info button)
## Or use help('brewlytics') to see help documentation in the print output

################################################################################
##
## D3.JS FORCE-DIRECTED NETWORK GRAPH
##
################################################################################
## CHANGE LOG
##==============================================================================
## 2026-12-03 - Initial code
## 2019-12-04 - Added matplotlib creation of network plot
## 2020-03-31 - Updated code to incorporate model_data to allow other datasets;
##              added model_data functionality
## 2026-11-26 - Replaced the matplotlib PNG with an interactive d3 HTML page;
##              Louvain communities + modularity; undirected PageRank sizes the
##              nodes; Network Table = node stats; Network Stats (JSON) =
##              overall stats + parameters
##            - Reads the two-table schema (nodes + edges) from inputs.tables;
##              aliases, deceased and notes come from the nodes table, so the
##              column-name, Bidirectional Graph and Name Corrections
##              parameters are gone; each edge says if it is directed
##            - Data Sources parameter (links under the title); collapsible
##              table of the relationships currently shown; optional header
##              image from inputs.resources, embedded so the page stays one file
##            - numpy-style docstrings
##            - Optional edges `label` column drawn on the links (focused node,
##              or all when zoomed in); tooltip and table use it
##            - "Built with d3.js" line linking d3, d3-force docs and the
##              official force-directed graph example
##            - Links from data (source, Data Sources) only if absolute http(s);
##              blocks javascript:/data: URLs in a shared page
## 2026-11-27 - Optional Schema parameter maps fields to your own column
##              names (or constants); only id, from_id and to_id required
##            - `deceased` is now the generic `ring` field + ring_label
##            - Schema tooltip: extra node columns shown in the tooltip
##            - inputs.list may hold the whole configuration as one string
##
################################################################################
################################################################################

import base64
import html
import json
import os
from collections import Counter

import networkx as nx
from networkx.algorithms.community import louvain_communities, modularity

import pandas as pd

################################################################################
################################################################################
## SET RUN-TIME ENVIRONMENTAL VARIABLES
################################################################################
################################################################################

D3_VERSION = '7.9.0'
D3_URL = 'https://cdn.jsdelivr.net/npm/d3@%s/dist/d3.min.js' % D3_VERSION
SEED = 7  # Louvain is randomised; a fixed seed gives the same communities every run

IMAGE_TYPES = {'.svg': 'image/svg+xml', '.png': 'image/png', '.jpg': 'image/jpeg',
               '.jpeg': 'image/jpeg', '.webp': 'image/webp', '.gif': 'image/gif'}

NODE_FIELDS = ['id', 'name', 'type', 'aliases', 'ring', 'notes']
EDGE_FIELDS = ['from_id', 'to_id', 'relationship', 'label', 'category', 'directed',
               'status', 'role', 'detail', 'source', 'weight']
SCHEMA_KEYS = ['nodes', 'edges', 'ring_label', 'tooltip']
RING_LABEL = 'flagged'  # what a ringed node means, unless the Schema says

################################################################################
## FUNCTIONS
################################################################################

def read_model_data(json_strings):
    """
    Merge the model's JSON parameter strings into one dict.

    Parameters
    ----------
    json_strings : iterable of str
        One JSON object per parameter, e.g. ``'{"Network Graphic Title": "..."}'``
        (as produced by the String to JSON v3 functionals).

    Returns
    -------
    dict
        All parameters; a later string overrides an earlier key.
    """
    md = dict()
    for s in json_strings:
        md.update(json.loads(s))
    return md


def as_dict(value):
    """
    Read a dict parameter that may arrive as a dict or a JSON string.

    Parameters
    ----------
    value : dict, str or None
        The parameter value.

    Returns
    -------
    dict
        ``value`` itself, the parsed JSON, or ``{}`` when empty or None.
    """
    if isinstance(value, dict):
        return value
    if value is None or str(value).strip() == '':
        return dict()
    return json.loads(value)


def as_bool(value):
    """
    Read a True/False value that may arrive as a bool or a string.

    Parameters
    ----------
    value : bool or str
        ``True``/``False`` or text such as ``'true'``, ``'1'``, ``'yes'``, ``'Y'``.

    Returns
    -------
    bool
        True for ``true``, ``1``, ``yes`` or ``y`` (any case); otherwise False.
    """
    return str(value).strip().lower() in ('true', '1', 'yes', 'y')


def html_filename(name):
    """
    Turn the Network Graphic Filename parameter into an ``.html`` file name.

    Parameters
    ----------
    name : str
        Requested file name, with or without an extension.

    Returns
    -------
    str
        Name with spaces replaced by ``_`` and the extension forced to
        ``.html``, e.g. ``'My Network.png'`` -> ``'My_Network.html'``.
    """
    stem = os.path.splitext(name.strip().replace(' ', '_'))[0]
    return '%s.html' % stem


def find_image(resources):
    """
    Find the first image among the model's web resources.

    Parameters
    ----------
    resources : iterable of str
        Resource file paths (``inputs.resources``).

    Returns
    -------
    str or None
        Path of the first file whose extension is in ``IMAGE_TYPES``, or
        None if there is none.
    """
    for r in resources:
        if os.path.splitext(str(r))[1].lower() in IMAGE_TYPES:
            return str(r)
    return None


def image_data_uri(path):
    """
    Embed an image file as a ``data:`` URI so the page stays one file.

    Parameters
    ----------
    path : str
        Image file path; its extension must be in ``IMAGE_TYPES``.

    Returns
    -------
    str
        ``data:<media type>;base64,<content>``.
    """
    with open(path, 'rb') as f:
        encoded = base64.b64encode(f.read()).decode('ascii')
    return 'data:%s;base64,%s' % (IMAGE_TYPES[os.path.splitext(path)[1].lower()], encoded)


def strip_cv_types(df):
    """
    Remove Brewlytics column-type suffixes and normalise cell text.

    Parameters
    ----------
    df : pandas.DataFrame
        Table as delivered by brew, e.g. with a column ``'id{string}'``.

    Returns
    -------
    pandas.DataFrame
        Copy with columns renamed (``'id{string}'`` -> ``'id'``), missing
        values as ``''``, and every cell as trimmed text.
    """
    out = df.copy()
    out.columns = [column_name.split('{')[0] for column_name in out.columns]
    ## object first: filling '' into an all-blank (float) column is an error in later pandas
    return out.astype(object).fillna('').astype(str).apply(lambda c: c.str.strip())


def read_schema(value):
    """
    Read and check the Schema parameter.

    Parameters
    ----------
    value : dict, str or None
        The Schema parameter; None or blank means the default column names.

    Returns
    -------
    dict
        ``nodes`` and ``edges`` (``{field: column name or constant}``),
        ``ring_label`` (str) and ``tooltip`` (list of column names).

    Raises
    ------
    ValueError
        Naming unknown keys, or ``id`` / ``from_id`` / ``to_id`` mapped to
        something other than a column name.
    """
    schema = as_dict(value)
    nodes, edges = as_dict(schema.get('nodes')), as_dict(schema.get('edges'))
    tooltip = schema.get('tooltip') or []
    problems = ['unknown Schema keys: %s' % sorted(set(schema) - set(SCHEMA_KEYS))]
    problems.append('unknown nodes fields: %s' % sorted(set(nodes) - set(NODE_FIELDS)))
    problems.append('unknown edges fields: %s' % sorted(set(edges) - set(EDGE_FIELDS)))
    problems.append('must name a column: %s' % [f for m, f in [(nodes, 'id'), (edges, 'from_id'), (edges, 'to_id')]
                                                 if not isinstance(m.get(f, f), str)])
    problems.append('constants need a "value": %s' % sorted(f for m in (nodes, edges) for f, v in m.items()
                                                             if isinstance(v, dict) and 'value' not in v))
    problems = [p for p in problems if not p.endswith('[]')]
    if problems:
        raise ValueError('Schema: ' + '; '.join(problems) + '. Fields are nodes %s, edges %s.'
                         % (NODE_FIELDS, EDGE_FIELDS))
    return {'nodes': nodes, 'edges': edges,
            'ring_label': str(schema.get('ring_label') or RING_LABEL),
            'tooltip': [tooltip] if isinstance(tooltip, str) else list(tooltip)}


def pick_tables(tables, schema):
    """
    Find the nodes table and the edges table.

    Parameters
    ----------
    tables : list of pandas.DataFrame
        ``inputs.tables`` after ``strip_cv_types``, in any order.
    schema : dict
        From ``read_schema``.

    Returns
    -------
    nodes, edges : pandas.DataFrame
        The edges table is the one with the ``from_id`` and ``to_id``
        columns; the nodes table is the other one with the ``id`` column
        (each under its Schema name).

    Raises
    ------
    ValueError
        If either table is missing or ambiguous; names the columns looked
        for and the columns each table has.
    """
    ends = [schema['edges'].get('from_id', 'from_id'), schema['edges'].get('to_id', 'to_id')]
    node_id = schema['nodes'].get('id', 'id')
    edge_tables = [t for t in tables if set(ends) <= set(t.columns)]
    node_tables = [t for t in tables if node_id in t.columns and not any(t is e for e in edge_tables)]
    for found, what, cols in [(edge_tables, 'edges', ends), (node_tables, 'nodes', [node_id])]:
        if len(found) != 1:
            raise ValueError('Expected exactly one %s table with columns %s; found %d. Tables have: %s'
                             % (what, cols, len(found), [list(t.columns) for t in tables]))
    return node_tables[0], edge_tables[0]


def select_columns(table, mapping, fields):
    """
    Rename a table's columns to the script's field names.

    Parameters
    ----------
    table : pandas.DataFrame
        The nodes or edges table.
    mapping : dict
        ``{field: column name or constant}`` from the Schema. A string is a
        column name; ``{"value": x}``, a bool or a number is a constant.
    fields : list of str
        ``NODE_FIELDS`` or ``EDGE_FIELDS``.

    Returns
    -------
    pandas.DataFrame
        One text column per field that is mapped, or that the table has
        under its default name. Fields with neither are left out.

    Raises
    ------
    ValueError
        Naming the mapped columns the table doesn't have.
    """
    out = pd.DataFrame(index=table.index)
    missing = []
    for field in fields:
        spec = mapping.get(field, field)
        if isinstance(spec, str):
            if spec in table.columns:
                out[field] = table[spec]
            elif field in mapping:
                missing.append(spec)
        else:
            value = spec['value'] if isinstance(spec, dict) else spec
            out[field] = '' if value is None else str(value)
    if missing:
        raise ValueError('Schema names columns the table does not have: %s. It has: %s'
                         % (missing, list(table.columns)))
    return out


def add_defaults(nodes, edges):
    """
    Fill in the optional fields a table doesn't have.

    Parameters
    ----------
    nodes, edges : pandas.DataFrame
        From ``select_columns``.

    Returns
    -------
    nodes, edges : pandas.DataFrame
        Copies with every field except ``weight``: ``name`` = ``id``,
        ``category`` = ``relationship`` (or ``all`` when that is blank),
        ``directed`` = False, the rest blank. ``weight`` stays absent when
        not given, so the graph is unweighted.
    """
    nodes, edges = nodes.copy(), edges.copy()
    if 'name' not in nodes.columns:
        nodes['name'] = nodes['id']
    for field in NODE_FIELDS:
        if field not in nodes.columns:
            nodes[field] = ''
    if 'directed' not in edges.columns:
        edges['directed'] = 'False'
    for field in EDGE_FIELDS:
        if field not in edges.columns and field not in ('category', 'weight'):
            edges[field] = ''
    if 'category' not in edges.columns:
        edges['category'] = edges['relationship'].where(edges['relationship'] != '', 'all')
    return nodes[NODE_FIELDS], edges[[f for f in EDGE_FIELDS if f in edges.columns]]


def tooltip_values(table, columns):
    """
    Read the extra columns shown in each node's tooltip.

    Parameters
    ----------
    table : pandas.DataFrame
        The nodes table as given (before ``select_columns``).
    columns : list of str
        Column names from the Schema's ``tooltip``.

    Returns
    -------
    list of list
        One list per row of ``[column, value]`` pairs, blank values left out.

    Raises
    ------
    ValueError
        Naming tooltip columns the table doesn't have.
    """
    missing = [c for c in columns if c not in table.columns]
    if missing:
        raise ValueError('Schema tooltip columns not in the nodes table: %s. It has: %s'
                         % (missing, list(table.columns)))
    return [[[c, v] for c, v in zip(columns, row) if v != ''] for row in table[columns].itertuples(index=False)]


def split_list(text):
    """
    Split a ``"; "``-separated cell into a list.

    Parameters
    ----------
    text : str
        e.g. ``'Alias One; Alias Two'``.

    Returns
    -------
    list of str
        Trimmed, non-empty items; ``[]`` for a blank cell.
    """
    return [s.strip() for s in text.split(';') if s.strip()]


def check_ids(nodes, edges):
    """
    Check that node ids are unique and every edge end is a node.

    Parameters
    ----------
    nodes : pandas.DataFrame
        Nodes table with an ``id`` column.
    edges : pandas.DataFrame
        Edges table with ``from_id`` and ``to_id`` columns.

    Raises
    ------
    ValueError
        Naming any duplicated node ids and any edge ids missing from the
        nodes table.
    """
    dupes = sorted(nodes['id'][nodes['id'].duplicated()].unique())
    unknown = sorted((set(edges['from_id']) | set(edges['to_id'])) - set(nodes['id']))
    problems = []
    if dupes:
        problems.append('duplicate node ids: %s' % dupes)
    if unknown:
        problems.append('edge ids not in the nodes table: %s' % unknown)
    if problems:
        raise ValueError('; '.join(problems))


def read_weights(edges):
    """
    Validate the optional ``weight`` column.

    Parameters
    ----------
    edges : pandas.DataFrame
        Edges table with a ``weight`` column (numbers or numeric strings).

    Returns
    -------
    pandas.Series
        Weights as floats; blank cells become 1.

    Raises
    ------
    ValueError
        Naming the edges (``from_id -> to_id``) whose weight is not a
        positive number.
    """
    raw = edges['weight'].astype(str).str.strip().replace({'': '1', 'nan': '1', 'None': '1'})
    weights = pd.to_numeric(raw, errors='coerce')
    bad = edges[~(weights > 0)]
    if len(bad):
        raise ValueError('weight must be a positive number: %s'
                         % ['%s -> %s (%s)' % (r.from_id, r.to_id, r.weight) for r in bad.itertuples()])
    return weights.astype(float)


def pair_weights(edges):
    """
    Total weight between each pair of nodes, ignoring direction.

    Parameters
    ----------
    edges : pandas.DataFrame
        Edges table with ``from_id``, ``to_id`` and a float ``weight``.

    Returns
    -------
    dict
        ``{(id, id) sorted: total weight}``. This is the weight of the one
        link the page draws between the pair.
    """
    totals = Counter()
    for e in edges.itertuples(index=False):
        totals[tuple(sorted((e.from_id, e.to_id)))] += e.weight
    return dict(totals)


def build_graph(nodes, edges):
    """
    Build the directed graph used for the statistics.

    Parameters
    ----------
    nodes : pandas.DataFrame
        Nodes table; every ``id`` becomes a node, including unlinked ones.
    edges : pandas.DataFrame
        Edges table with ``from_id``, ``to_id``, ``directed`` and, if the
        data is weighted, a float ``weight``.

    Returns
    -------
    networkx.DiGraph
        Graph keyed by node id. Undirected edges are added in both
        directions, so the directed statistics treat them as mutual.
        Several edges between the same pair collapse into one; with
        weights, their weights add up.
    """
    g = nx.DiGraph()
    for n in nodes.itertuples(index=False):
        g.add_node(n.id)
    for e in edges.itertuples(index=False):
        pairs = [(e.from_id, e.to_id)] if as_bool(e.directed) else [(e.from_id, e.to_id), (e.to_id, e.from_id)]
        for a, b in pairs:
            if 'weight' in edges.columns:
                g.add_edge(a, b, weight=g.edges[a, b]['weight'] + e.weight if g.has_edge(a, b) else e.weight)
            else:
                g.add_edge(a, b)
    return g


def highest(scores, name):
    """
    Describe the top-scoring node.

    Parameters
    ----------
    scores : dict
        ``{node id: score}``.
    name : dict
        ``{node id: display name}``.

    Returns
    -------
    str
        ``'<name> (<score>)'``; ties go to the id that sorts last.
    """
    score, node = sorted((s, str(n)) for n, s in scores.items())[-1]
    return '%s (%f)' % (name[node], score)


def graph_stats(g, u, name):
    """
    Compute overall and per-node network statistics.

    Parameters
    ----------
    g : networkx.DiGraph
        Graph from ``build_graph``.
    u : networkx.Graph
        Undirected graph from ``undirected``.
    name : dict
        ``{node id: display name}``, used in the "Highest ..." entries.

    Returns
    -------
    overall_stats : dict
        Density, ``# of Nodes``, ``# of Edges`` (directed), and
        ``Highest <measure>`` for Pagerank, Pagerank (Undirected), Degree,
        In Degree and Out Degree.
    node_stats : dict
        ``{node id: {measure: value}}`` for the same five measures
        (networkx centralities: In Degree and Out Degree run 0-1; Degree is
        their sum on this directed graph, so it runs 0-2). PageRank uses
        the edge weights when there are any; degree counts neighbours.
    """
    pagerank = nx.pagerank(g)
    pagerank_u = nx.pagerank(u)
    degree = nx.degree_centrality(g)
    in_degree = nx.in_degree_centrality(g)
    out_degree = nx.out_degree_centrality(g)

    overall_stats = {'Density': nx.density(g),
                     '# of Nodes': g.number_of_nodes(),
                     '# of Edges': g.number_of_edges()}
    for label, scores in [('Pagerank', pagerank), ('Pagerank (Undirected)', pagerank_u),
                          ('Degree', degree), ('In Degree', in_degree), ('Out Degree', out_degree)]:
        overall_stats['Highest %s' % label] = highest(scores, name)

    node_stats = {n: {'Pagerank (Undirected)': pagerank_u[n],
                      'Pagerank': pagerank[n],
                      'Degree': degree[n],
                      'In Degree': in_degree[n],
                      'Out Degree': out_degree[n]} for n in g}
    return overall_stats, node_stats


def undirected(g, weights=None):
    """
    Undirected copy of a graph without self-loops.

    Parameters
    ----------
    g : networkx.DiGraph
    weights : dict, optional
        ``{(id, id) sorted: weight}`` from ``pair_weights``. None leaves the
        graph unweighted.

    Returns
    -------
    networkx.Graph
        Used for undirected PageRank and community detection. With
        ``weights``, each pair carries the total weight of every
        relationship between them, whatever its direction.
    """
    u = nx.Graph(g)
    u.remove_edges_from(list(nx.selfloop_edges(u)))
    if weights is not None:
        for a, b in u.edges():
            u.edges[a, b]['weight'] = weights[tuple(sorted((a, b)))]
    return u


def communities(u, seed=SEED):
    """
    Find Louvain communities.

    Parameters
    ----------
    u : networkx.Graph
        Undirected graph from ``undirected``.
    seed : int, default SEED
        Random seed; the same seed and data give the same communities.

    Returns
    -------
    list of set
        Communities of node ids, largest first (ties by smallest id).
    """
    return sorted(louvain_communities(u, seed=seed), key=lambda c: (-len(c), min(c)))


def community_lookup(u, comms, name):
    """
    Map each node to its community rank and hub.

    Parameters
    ----------
    u : networkx.Graph
        Undirected graph, used for each member's degree.
    comms : list of set
        Communities from ``communities``, largest first.
    name : dict
        ``{node id: display name}``.

    Returns
    -------
    dict
        ``{node id: (rank, hub name)}``. Rank 0 is the largest community;
        the hub is its best-connected member.
    """
    group = dict()
    for rank, members in enumerate(comms):
        hub = max(members, key=lambda n: (u.degree(n), n))
        for n in members:
            group[n] = (rank, name[hub])
    return group


def node_table(nodes, node_stats, group, ring_label=RING_LABEL):
    """
    Build the Network Table output.

    Parameters
    ----------
    nodes : pandas.DataFrame
        Nodes table.
    node_stats : dict
        From ``graph_stats``.
    group : dict
        From ``community_lookup``.
    ring_label : str, default RING_LABEL
        Header of the ring column, capitalised (``deceased`` -> ``Deceased``).

    Returns
    -------
    pandas.DataFrame
        One row per node: Node, Type, Aliases, the ring column, Community
        (1 = largest), Community Hub, then the five statistics; highest
        undirected PageRank first.
    """
    rows = [{'Node': n.name,
             'Type': n.type,
             'Aliases': n.aliases,
             ring_label[:1].upper() + ring_label[1:]: n.ring,
             'Community': group[n.id][0] + 1,
             'Community Hub': group[n.id][1],
             **node_stats[n.id]} for n in nodes.itertuples(index=False)]
    return (pd.DataFrame(rows)
              .sort_values(['Pagerank (Undirected)', 'Node'], ascending=[False, True])
              .reset_index(drop=True))


def number(x):
    """Whole floats as ints (8.0 -> 8), so the page shows 8, not 8.0."""
    return int(x) if float(x).is_integer() else float(x)


def graph_payload(nodes, edges, overall_stats, node_stats, group, sources, ring_label=RING_LABEL, extras=None):
    """
    Assemble the data embedded in the page.

    Parameters
    ----------
    nodes, edges : pandas.DataFrame
        The two input tables.
    overall_stats : dict
        Shown in the page header.
    node_stats : dict
        From ``graph_stats``; shown in tooltips and used for node size.
    group : dict
        From ``community_lookup``; used for node colour and legend.
    sources : dict
        ``{label: url}`` from the Data Sources parameter.
    ring_label : str, default RING_LABEL
        What a ringed node means; shown in the legend and tooltip.
    extras : list of list, optional
        From ``tooltip_values``, one entry per nodes row.

    Returns
    -------
    dict
        ``overall``, ``sources`` (list of ``{label, url}``), ``ring_label``
        (None when no node is ringed), ``nodes`` and ``links``. There is one link per connected pair, holding every edge
        between the two nodes in ``rels``; with weights, the link's
        ``weight`` is their total.
    """
    weighted = 'weight' in edges.columns
    links = dict()
    for e in edges.itertuples(index=False):
        key = tuple(sorted((e.from_id, e.to_id)))
        link = links.setdefault(key, {'source': key[0], 'target': key[1], 'rels': []})
        if weighted:
            link['weight'] = number(link.get('weight', 0) + e.weight)
        link['rels'].append({'from': e.from_id, 'to': e.to_id,
                             'weight': number(e.weight) if weighted else None,
                             'relationship': e.relationship.replace('_', ' '),
                             'label': e.label or e.relationship.replace('_', ' '),
                             'category': e.category, 'directed': as_bool(e.directed),
                             'status': e.status, 'role': e.role, 'detail': e.detail,
                             'source': e.source})
    link_count = Counter()
    for a, b in links:
        link_count[a] += 1
        link_count[b] += 1

    node_rows = [{'id': n.id, 'name': n.name, 'type': n.type,
                  'aliases': split_list(n.aliases), 'ring': as_bool(n.ring),
                  'notes': split_list(n.notes), 'extra': extra,
                  'group': group[n.id][0], 'hub': group[n.id][1],
                  'links': link_count[n.id], 'stats': node_stats[n.id]}
                 for n, extra in zip(nodes.itertuples(index=False), extras or [[]] * len(nodes))]
    ringed = any(row['ring'] for row in node_rows)
    return {'overall': overall_stats, 'sources': [{'label': k, 'url': v} for k, v in sources.items()],
            'ring_label': ring_label if ringed else None,
            'nodes': node_rows, 'links': list(links.values())}


def render_html(payload, title, image_uri=None, d3_url=D3_URL):
    """
    Render the self-contained page.

    Parameters
    ----------
    payload : dict
        From ``graph_payload``; embedded as JSON.
    title : str
        Page title (HTML-escaped).
    image_uri : str, optional
        ``data:`` URI of the header image; None means no logo.
    d3_url : str, default D3_URL
        Where the page loads d3 from.

    Returns
    -------
    str
        Complete HTML document with CSS, JavaScript, data and image inline.
    """
    data = json.dumps(payload, ensure_ascii=False).replace('</', '<\\/')
    logo = '<img class="logo" src="%s" alt="">' % image_uri if image_uri else ''
    page = (PAGE.replace('__CSS__', PAGE_CSS)
                .replace('__JS__', PAGE_JS)
                .replace('__D3__', d3_url)
                .replace('__D3VERSION__', D3_VERSION)
                .replace('__TITLE__', html.escape(title))
                .replace('__LOGO__', logo))
    return page.replace('__DATA__', data)


################################################################################
## PAGE TEMPLATE
################################################################################

PAGE = '''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title>
<style>__CSS__</style>
</head>
<body>
<header>
  __LOGO__
  <div>
    <h1>__TITLE__</h1>
    <p class="sources" id="sources"></p>
    <p class="sources">Built with <a href="https://d3js.org/" target="_blank" rel="noopener">d3.js</a> v__D3VERSION__ &middot;
      layout: <a href="https://d3js.org/d3-force" target="_blank" rel="noopener">d3-force</a> &middot;
      <a href="https://observablehq.com/@d3/force-directed-graph/2" target="_blank" rel="noopener">force-directed graph example</a></p>
    <p class="sub" id="stats"></p>
  </div>
</header>
<div class="controls">
  <input id="search" type="search" list="names" placeholder="Find a name or alias..." aria-label="Find a name">
  <datalist id="names"></datalist>
  <button id="reset">Reset view</button>
</div>
<div class="chips" id="cats" aria-label="Relationship categories"></div>
<div class="legend" id="legend"></div>
<div id="chart"><div id="tip" class="tip" hidden></div></div>
<p class="hint">Node size = PageRank, ignoring link direction; colour = Louvain community, named after its best-connected member;
<span id="ring-hint"></span>arrows show one-way relationships; link labels show for the focused node, or everywhere once zoomed in.
Drag a node to move it &middot; scroll or pinch to zoom &middot; hover a node, or click to pin it &middot; click a category to hide or show it.</p>
<details id="table-wrap">
  <summary>Table view <span id="table-count"></span></summary>
  <div class="table-scroll"><table id="table">
    <thead><tr>
      <th data-key="fromName">From</th><th data-key="label">Relationship</th><th data-key="toName">To</th>
      <th data-key="category">Category</th><th data-key="weight" class="w">Weight</th><th data-key="detail">Detail</th><th data-key="source">Source</th>
    </tr></thead>
    <tbody></tbody>
  </table></div>
</details>
<script id="graph-data" type="application/json">__DATA__</script>
<script src="__D3__"></script>
<script>__JS__</script>
</body>
</html>
'''

PAGE_CSS = '''
:root {
  --bg: #fcfcfb; --ink: #1f1f1e; --ink-2: #55554f; --ink-3: #8a8a83;
  --rule: #e4e4df; --link: #c4c4bd; --tip-bg: #ffffff;
  /* ColorBrewer Dark2 */
  --g-0: #1b9e77; --g-1: #d95f02; --g-2: #7570b3; --g-3: #e7298a;
  --g-4: #66a61e; --g-5: #e6ab02; --g-6: #a6761d; --g-other: #b3b3ad;
  color-scheme: light;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --bg: #1a1a19; --ink: #ecece8; --ink-2: #b4b4ad; --ink-3: #7d7d77;
    --rule: #33332f; --link: #4a4a45; --tip-bg: #262624; --g-other: #5f5f5a; color-scheme: dark;
  }
}
:root[data-theme="dark"] {
  --bg: #1a1a19; --ink: #ecece8; --ink-2: #b4b4ad; --ink-3: #7d7d77;
  --rule: #33332f; --link: #4a4a45; --tip-bg: #262624; --g-other: #5f5f5a; color-scheme: dark;
}
* { box-sizing: border-box; }
body {
  margin: 0 auto; padding: 24px 16px; max-width: 1400px; background: var(--bg); color: var(--ink);
  font: 14px/1.45 system-ui, -apple-system, "Segoe UI", sans-serif;
}
header { display: flex; align-items: center; gap: 16px; }
.logo { height: 56px; width: auto; flex: none; }
@media (max-width: 600px) { header { flex-direction: column; align-items: flex-start; gap: 8px; } .logo { height: 44px; } }
h1 { font-size: 20px; margin: 0 0 4px; font-weight: 600; }
.sub { margin: 0; color: var(--ink-2); }
.controls { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; margin: 16px 0 8px; }
#search {
  font: inherit; font-size: 13px; color: var(--ink); background: var(--bg);
  border: 1px solid var(--rule); border-radius: 6px; padding: 4px 10px; min-width: 16rem;
}
button {
  font: inherit; font-size: 13px; color: var(--ink-2); background: none;
  border: 1px solid var(--rule); border-radius: 999px; padding: 3px 10px; cursor: pointer;
}
.chips { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 8px; }
.chips button.on { color: var(--ink); border-color: var(--ink-3); }
.chips button:not(.on) { text-decoration: line-through; opacity: 0.55; }
.legend { display: flex; flex-wrap: wrap; gap: 4px 16px; font-size: 13px; color: var(--ink-2); margin-bottom: 8px; }
.legend span::before {
  content: ""; display: inline-block; width: 10px; height: 10px; border-radius: 50%;
  background: var(--c); margin-right: 6px; vertical-align: -1px;
}
#chart { position: relative; width: 100%; height: 75vh; min-height: 420px; }
#chart svg { width: 100%; height: 100%; display: block; cursor: grab; }
.link { stroke: var(--link); stroke-width: 1.1; }
#table.unweighted .w { display: none; }
.arrow { fill: var(--link); }
.node circle { stroke: var(--bg); stroke-width: 1.2; cursor: pointer; }
.node.ring circle { stroke: var(--ink-2); stroke-width: 1.5; }
.link-label { fill: var(--ink-2); text-anchor: middle; pointer-events: none;
              paint-order: stroke; stroke: var(--bg); stroke-linejoin: round; }  /* size + halo set in JS */
.node text { fill: var(--ink-2); pointer-events: none; paint-order: stroke; stroke: var(--bg); }  /* size + halo set in JS */
.node.lit text { display: inline !important; fill: var(--ink); }
.dim { opacity: 0.12; }
.off { display: none; }
.hint { font-size: 12px; color: var(--ink-3); margin: 8px 0 0; }
.tip {
  position: absolute; top: 8px; right: 8px; width: min(380px, calc(100% - 16px)); max-height: calc(100% - 16px);
  overflow: auto; background: var(--tip-bg); color: var(--ink); border: 1px solid var(--rule);
  border-radius: 6px; padding: 8px 12px; font-size: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.08);
}
.tip b { font-weight: 600; font-size: 13px; }
.tip .meta, .tip .notes { color: var(--ink-2); margin-top: 2px; }
.tip ul { margin: 6px 0 0; padding-left: 16px; }
.tip i { color: var(--ink-2); }
.tip a { color: inherit; }
.sources { margin: 0 0 4px; font-size: 13px; color: var(--ink-2); }
.sources a { color: inherit; }
details { margin-top: 16px; border-top: 1px solid var(--rule); padding-top: 8px; }
summary { cursor: pointer; font-weight: 600; }
summary span { font-weight: normal; color: var(--ink-3); }
.table-scroll { max-height: 60vh; overflow: auto; margin-top: 8px; }
table { border-collapse: collapse; width: 100%; font-size: 12px; }
th { position: sticky; top: 0; background: var(--bg); text-align: left; font-weight: 600;
     padding: 4px 8px; border-bottom: 1px solid var(--rule); cursor: pointer; white-space: nowrap; }
th.asc::after { content: " \\25b4"; } th.desc::after { content: " \\25be"; }
td { padding: 3px 8px; vertical-align: top; }
tbody tr:hover { background: var(--rule); }
td a { color: inherit; }
'''

PAGE_JS = '''
const data = JSON.parse(document.getElementById("graph-data").textContent);
const N_COLOURS = 7; // biggest communities get Dark2; the rest share the "other" grey
const colour = (g) => (g < N_COLOURS ? `var(--g-${g})` : "var(--g-other)");
const f3 = d3.format(".3f");
const esc = (s) => String(s).replace(/[&<>"]/g, (ch) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[ch]));
// URLs from the data become links only if they are absolute http(s); anything else
// (javascript:, data:, relative paths) is shown as plain text or dropped.
const safeUrl = (u) => {
  try { const p = new URL(String(u)); return p.protocol === "http:" || p.protocol === "https:" ? p.href : null; }
  catch (err) { return null; }
};
const safeLink = (u, text) => { const s = safeUrl(u); return s ? `<a href="${esc(s)}" target="_blank" rel="noopener">${esc(text)}</a>` : ""; };

const o = data.overall;
d3.select("#stats").text(
  `${o["# of Nodes"]} nodes \\u00b7 ${data.links.reduce((s, l) => s + l.rels.length, 0)} relationships \\u00b7 density ${f3(o.Density)} \\u00b7 ` +
  `${o["# of Communities"]} communities (modularity ${f3(o.Modularity)}) \\u00b7 highest PageRank: ${o["Highest Pagerank (Undirected)"]}`);

// ring meaning in the hint line, only when some node is ringed
d3.select("#ring-hint").text(data.ring_label ? `ringed node = ${data.ring_label}; ` : "");

// data sources under the title
d3.select("#sources").html(data.sources.length
  ? "Data: " + data.sources.map((s) => safeLink(s.url, s.label) || esc(s.label)).join(" \\u00b7 ")
  : null);

// legend: top communities by hub name, then "other"
const comms = d3.rollups(data.nodes, (v) => ({ hub: v[0].hub, n: v.length }), (d) => d.group).sort((a, b) => a[0] - b[0]);
const legend = comms.slice(0, N_COLOURS).map(([g, v]) => ({ g, text: `${v.hub} (${v.n})` }));
if (comms.length > N_COLOURS) {
  legend.push({ g: N_COLOURS, text: `${comms.length - N_COLOURS} smaller communities (${d3.sum(comms.slice(N_COLOURS), ([, v]) => v.n)})` });
}
d3.select("#legend").selectAll("span").data(legend).join("span").style("--c", (d) => colour(d.g)).text((d) => d.text);

const nodes = data.nodes.map((d) => ({ ...d }));
const links = data.links.map((d) => ({ ...d }));
const byId = new Map(nodes.map((n) => [n.id, n]));
const nameOf = (id) => byId.get(id).name;

// search: names and aliases
const lookup = new Map();
nodes.forEach((n) => { lookup.set(n.name, n.id); n.aliases.forEach((a) => { if (!lookup.has(a)) lookup.set(a, n.id); }); });
d3.select("#names").selectAll("option").data([...lookup.keys()].sort(d3.ascending)).join("option").attr("value", (d) => d);

// category chips
const catCounts = d3.rollups(links.flatMap((l) => l.rels), (v) => v.length, (r) => r.category).sort((a, b) => b[1] - a[1]);
const activeCats = new Set(catCounts.map(([c]) => c));
d3.select("#cats").selectAll("button").data(catCounts).join("button").attr("class", "on")
  .text(([c, n]) => `${c} (${n})`)
  .on("click", function (_, [c]) {
    activeCats.has(c) ? activeCats.delete(c) : activeCats.add(c);
    d3.select(this).classed("on", activeCats.has(c));
    applyCats();
  });

const size = (d) => d.stats["Pagerank (Undirected)"];
const pr = d3.scaleSqrt().domain([0, d3.max(nodes, size)]).range([2.5, 20]);
const rad = (d) => pr(size(d));
const rank = new Map([...nodes].sort((a, b) => size(b) - size(a)).map((d, i) => [d.id, i]));

const chart = document.getElementById("chart");
const svg = d3.select(chart).insert("svg", "#tip");
const defs = svg.append("defs");
[["arrow-end", "M0,-4L8,0L0,4", 8], ["arrow-start", "M8,-4L0,0L8,4", 0]].forEach(([id, d, refX]) =>
  defs.append("marker").attr("id", id).attr("viewBox", "0 -4 8 8").attr("refX", refX)
    .attr("markerWidth", 6).attr("markerHeight", 6).attr("orient", "auto")
    .append("path").attr("class", "arrow").attr("d", d));

// a link shows an arrow at an end when some visible one-way relationship points there
const visibleRels = (l) => l.rels.filter((r) => activeCats.has(r.category));
const arrowTo = (l, end) => visibleRels(l).some((r) => r.directed && r.to === end) && !visibleRels(l).some((r) => !r.directed);

const g = svg.append("g");
const link = g.append("g").selectAll("line").data(links).join("line").attr("class", "link");
// optional weights: thicker links for heavier pairs (inline style, so it beats the CSS default)
const weighted = links.some((l) => l.weight != null);
if (weighted) {
  const width = d3.scaleSqrt().domain(d3.extent(links, (l) => l.weight)).range([1, 6]);
  link.style("stroke-width", (l) => width(l.weight));
}
d3.select("#table").classed("unweighted", !weighted);
const node = g.append("g").selectAll("g").data(nodes, (d) => d.id).join("g")
  .attr("class", (d) => "node" + (d.ring ? " ring" : ""));
node.append("circle").attr("r", rad).attr("fill", (d) => colour(d.group));
node.append("text").attr("x", (d) => rad(d) + 3).attr("y", 4).text((d) => d.name);

function applyCats() {
  link.classed("off", (l) => visibleRels(l).length === 0)
    .attr("marker-end", (l) => (arrowTo(l, l.target.id ?? l.target) ? "url(#arrow-end)" : null))
    .attr("marker-start", (l) => (arrowTo(l, l.source.id ?? l.source) ? "url(#arrow-start)" : null));
  if (pinned) focus(pinned);
  else updateLinkLabels();
  renderTable();
}

// table view: the relationships currently shown (active categories; only the
// pinned node's when one is pinned). Hidden by default; drawn only while open.
const tableWrap = document.getElementById("table-wrap");
let sortKey = "fromName", sortAsc = true;
function tableRows() {
  const pick = pinned ? links.filter((l) => l.source.id === pinned.id || l.target.id === pinned.id) : links;
  return pick.flatMap(visibleRels).map((r) => ({
    ...r, fromName: nameOf(r.from), toName: nameOf(r.to),
  }));
}
function renderTable() {
  const rows = tableRows();
  d3.select("#table-count").text(`(${rows.length} relationships${pinned ? " of " + pinned.name : ""})`);
  if (!tableWrap.open) return;
  rows.sort((a, b) => (sortAsc ? 1 : -1) * d3.ascending(a[sortKey], b[sortKey]));
  d3.selectAll("#table th").classed("asc", function () { return this.dataset.key === sortKey && sortAsc; })
    .classed("desc", function () { return this.dataset.key === sortKey && !sortAsc; });
  d3.select("#table tbody").selectAll("tr").data(rows).join("tr").html((r) =>
    `<td>${esc(r.fromName)}</td><td>${esc(r.label)}</td><td>${esc(r.toName)}</td><td>${esc(r.category)}</td>` +
    `<td class="w">${r.weight ?? ""}</td><td>${esc(r.detail)}</td><td>${safeLink(r.source, "link")}</td>`);
}
tableWrap.addEventListener("toggle", renderTable);
d3.selectAll("#table th").on("click", function () {
  const key = this.dataset.key;
  sortAsc = key === sortKey ? !sortAsc : true;
  sortKey = key;
  renderTable();
});

// link labels: the focused node's links always; every visible link once zoomed in.
// Drawn between the links and the nodes; kept upright; constant size on screen.
const LINK_LABEL_ZOOM = 2.5;
let focusId = null;
const linkLabel = g.insert("g", function () { return node.node().parentNode; })
  .selectAll("text").data(links).join("text").attr("class", "link-label").attr("dy", -3);
const linkText = (l) => [...new Set(visibleRels(l).map((r) => r.label))].join(" \\u00b7 ");
function updateLinkLabels() {
  linkLabel.text(linkText).attr("font-size", 10 / k).attr("stroke-width", 3 / k).attr("dy", -3 / k).attr("display", (l) => {
    if (!visibleRels(l).length) return "none";
    if (focusId) return l.source.id === focusId || l.target.id === focusId ? null : "none";
    return k >= LINK_LABEL_ZOOM ? null : "none";
  });
  placeLinkLabels();
}
function placeLinkLabels() {  // midpoint of the link, rotated along it, kept upright
  linkLabel.filter(function () { return this.getAttribute("display") !== "none"; })
    .attr("transform", (d) => {
      let a = (Math.atan2(d.target.y - d.source.y, d.target.x - d.source.x) * 180) / Math.PI;
      if (a > 90) a -= 180;
      if (a < -90) a += 180;
      return `translate(${(d.source.x + d.target.x) / 2},${(d.source.y + d.target.y) / 2}) rotate(${a})`;
    });
}

// node labels: top PageRank always, more as you zoom in
let k = 0.6;
const showLabels = () => node.select("text")
  .attr("display", (d) => (rank.get(d.id) < 15 * k * k ? null : "none"))
  .attr("font-size", 11 / Math.max(k, 1))   // same size on screen once zoomed in
  .attr("stroke-width", 3 / Math.max(k, 1));

let viewerMoved = false;   // once the viewer zooms or pans, never re-fit on their behalf
const zoom = d3.zoom().scaleExtent([0.2, 6]).on("zoom", (e) => {
  if (e.sourceEvent) viewerMoved = true;
  g.attr("transform", e.transform);
  if (e.transform.k !== k) { k = e.transform.k; showLabels(); updateLinkLabels(); }
});
svg.call(zoom).on("click", (e) => { if (e.target === svg.node()) clear(); });

const sim = d3.forceSimulation(nodes)
  .force("link", d3.forceLink(links).id((d) => d.id).distance(35))
  .force("charge", d3.forceManyBody().strength(-70))
  .force("collide", d3.forceCollide().radius((d) => rad(d) + 2))
  .force("x", d3.forceX().strength(0.06))
  .force("y", d3.forceY().strength(0.06))
  .on("tick", () => {
    link.each(function (d) {
      const s = d.source, t = d.target;
      const dx = t.x - s.x, dy = t.y - s.y, len = Math.hypot(dx, dy) || 1;
      const offT = arrowTo(d, t.id) ? rad(t) + 1.5 : 0, offS = arrowTo(d, s.id) ? rad(s) + 1.5 : 0;
      d3.select(this)
        .attr("x1", s.x + (dx / len) * offS).attr("y1", s.y + (dy / len) * offS)
        .attr("x2", t.x - (dx / len) * offT).attr("y2", t.y - (dy / len) * offT);
    });
    node.attr("transform", (d) => `translate(${d.x},${d.y})`);
    placeLinkLabels();
  });

function resize() {
  const { width, height } = chart.getBoundingClientRect();
  svg.attr("viewBox", [-width / 2, -height / 2, width, height]);
}
resize();
window.addEventListener("resize", resize);
svg.call(zoom.transform, d3.zoomIdentity.scale(k));
showLabels();

// zoom to fit the whole graph: small graphs get bigger, large ones smaller
function fitView(duration) {
  const { width, height } = chart.getBoundingClientRect();
  const pad = 40;
  const x0 = d3.min(nodes, (d) => d.x - rad(d)), x1 = d3.max(nodes, (d) => d.x + rad(d));
  const y0 = d3.min(nodes, (d) => d.y - rad(d)), y1 = d3.max(nodes, (d) => d.y + rad(d));
  const s = Math.max(0.2, Math.min(2, (width - 2 * pad) / (x1 - x0 || 1), (height - 2 * pad) / (y1 - y0 || 1)));
  const t = d3.zoomIdentity.scale(s).translate(-(x0 + x1) / 2, -(y0 + y1) / 2);
  (duration ? svg.transition().duration(duration) : svg).call(zoom.transform, t);
}
sim.on("end.fit", () => {
  sim.on("end.fit", null);              // only the first time the layout settles
  if (!viewerMoved) fitView(600);
});

// focus: hover previews, click pins
const tip = d3.select("#tip");
let pinned = null;

function relLine(r) {
  const src = r.source && safeUrl(r.source) ? " " + safeLink(r.source, "source") : "";
  const detail = r.detail && r.detail !== r.label ? ` <span class="meta">\\u2014 ${esc(r.detail)}</span>` : "";
  const weight = r.weight != null ? ` <span class="meta">(weight ${r.weight})</span>` : "";
  return `<li>${esc(nameOf(r.from))} <i>${esc(r.label)}</i> ${esc(nameOf(r.to))}` + weight + detail + src + "</li>";
}

function focus(d) {
  focusId = d.id;
  updateLinkLabels();
  const mine = links.filter((l) => (l.source.id === d.id || l.target.id === d.id) && visibleRels(l).length);
  const keep = new Set(mine.flatMap((l) => [l.source.id, l.target.id]));
  keep.add(d.id);
  node.classed("dim", (n) => !keep.has(n.id)).classed("lit", (n) => keep.has(n.id));
  link.classed("dim", (l) => !mine.includes(l));
  const rels = mine.flatMap(visibleRels).sort((a, b) => d3.ascending(a.category, b.category) || d3.ascending(a.from !== d.id, b.from !== d.id));
  const s = d.stats;
  tip.attr("hidden", null).html(
    `<b>${esc(d.name)}</b>` +
    `<div class="meta">${esc(d.type)}${d.ring ? " \\u00b7 " + esc(data.ring_label) : ""} \\u00b7 ${d.links} connections \\u00b7 community: ${esc(d.hub)}</div>` +
    (d.aliases.length ? `<div class="meta">Also known as: ${d.aliases.map(esc).join(", ")}</div>` : "") +
    (d.extra.length ? `<div class="meta">${d.extra.map(([k, v]) => esc(k) + ": " + esc(v)).join(" \\u00b7 ")}</div>` : "") +
    `<div class="meta">PageRank ${f3(s["Pagerank (Undirected)"])} (directed ${f3(s.Pagerank)}) \\u00b7 degree ${f3(s.Degree)} \\u00b7 in ${f3(s["In Degree"])} \\u00b7 out ${f3(s["Out Degree"])}</div>` +
    (d.notes.length ? `<div class="notes">${d.notes.map(esc).join("<br>")}</div>` : "") +
    `<ul>${rels.map(relLine).join("")}</ul>`);
}
function clear() {
  const was = pinned;
  pinned = null;
  node.classed("dim", false).classed("lit", false);
  link.classed("dim", false);
  tip.attr("hidden", true);
  focusId = null;
  updateLinkLabels();
  if (was) renderTable();
}
function pin(d) {
  pinned = d;
  focus(d);
  renderTable();
}

node
  .on("mouseenter", (_, d) => { if (!pinned) focus(d); })
  .on("mouseleave", () => { if (!pinned) clear(); })
  .on("click", (e, d) => { e.stopPropagation(); pin(d); })
  .call(d3.drag()
    .on("start", (e, d) => { if (!e.active) sim.alphaTarget(0.3).restart(); d.fx = d.x; d.fy = d.y; })
    .on("drag", (e, d) => { d.fx = e.x; d.fy = e.y; })
    .on("end", (e, d) => { if (!e.active) sim.alphaTarget(0); d.fx = null; d.fy = null; }));

d3.select("#search").on("change", function () {
  const d = byId.get(lookup.get(this.value));
  if (!d) return;
  pin(d);
  svg.transition().duration(600).call(zoom.transform, d3.zoomIdentity.scale(2).translate(-d.x, -d.y));
});

d3.select("#reset").on("click", () => {
  clear();
  d3.select("#search").property("value", "");
  fitView(400);
});

applyCats();
'''

################################################################################
## MODEL DATA
################################################################################

md = read_model_data(inputs.list)

network_graphic_title = md['Network Graphic Title']
network_graphic_filename = html_filename(md['Network Graphic Filename'])
data_sources = as_dict(md.get('Data Sources'))  # {"Source name": "https://...", ...}
schema = read_schema(md.get('Schema'))  # your column names; none = the default names
header_image = find_image(getattr(inputs, 'resources', None) or [])  # no resources wired = no image

################################################################################
## BODY
################################################################################

## Find the nodes and edges tables by their columns (wiring order doesn't matter),
## then rename your columns to the field names and fill in the optional fields
tables = [strip_cv_types(t) for t in inputs.tables]
nodes_in, edges_in = pick_tables(tables, schema)
nodes, edges = add_defaults(select_columns(nodes_in, schema['nodes'], NODE_FIELDS),
                            select_columns(edges_in, schema['edges'], EDGE_FIELDS))
extras = tooltip_values(nodes_in, schema['tooltip'])
check_ids(nodes, edges)
weighted = 'weight' in edges.columns  # optional; without it every relationship counts once
if weighted:
    edges['weight'] = read_weights(edges)

name = dict(zip(nodes['id'], nodes['name']))
g = build_graph(nodes, edges)
u = undirected(g, pair_weights(edges) if weighted else None)
overall_stats, node_stats = graph_stats(g, u, name)

comms = communities(u)
group = community_lookup(u, comms, name)
overall_stats.update({'Weighted': weighted,
                      '# of Relationships': len(edges),
                      '# of Communities': len(comms),
                      'Modularity': modularity(u, comms)})

node_stats_table = node_table(nodes, node_stats, group, schema['ring_label'])
payload = graph_payload(nodes, edges, overall_stats, node_stats, group, data_sources,
                        schema['ring_label'], extras)

with open(network_graphic_filename, 'w', encoding='utf-8') as f:
    f.write(render_html(payload, network_graphic_title,
                        image_data_uri(header_image) if header_image else None))

################################################################################
## OUTPUTS
################################################################################

## Network Stats (JSON): overall stats, plus the parameters this run used
outputs.string = json.dumps({'Overall Stats': overall_stats,
                             'Parameters': md}, indent=4)

## Network Table: one row per node
outputs.table = node_stats_table

## Network Graph (downloadable d3 page)
outputs.resource = network_graphic_filename

################################################################################
## SUMMARY
################################################################################

print('%d nodes, %d relationships (%d directed graph edges)'
      % (len(nodes), len(edges), overall_stats['# of Edges']))
print('Graph Density: %f' % (overall_stats['Density']))
print('Weighted: %s' % ('yes (PageRank and Louvain use the weight column)' if weighted else 'no'))
print()
for key in ['Pagerank (Undirected)', 'Pagerank', 'Degree', 'In Degree', 'Out Degree']:
    print('Highest %s: %s' % (key, overall_stats['Highest %s' % key]))
print()
print('# of Communities: %d (Louvain, seed %d)' % (overall_stats['# of Communities'], SEED))
print('Modularity: %f' % (overall_stats['Modularity']))
print()
print('Header image: %s' % (header_image or 'none'))
print('Wrote %s' % network_graphic_filename)
print()
print(node_stats_table.head(10).to_string(index=False))
