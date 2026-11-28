"""
Build a d3.js timeline page from an events table (Brewlytics Python Script
functional).

The script reads one table of dated events, checks it, summarises each group,
and writes one self-contained interactive HTML page: one row per group, one
mark per event, coloured and shaped by kind. The page has CSS, JavaScript,
data and header image inline; only d3 is loaded from a CDN.

Inputs
------
inputs.tables[0] (or inputs.table) : pandas.DataFrame
    The events table, one row per event. The column names below are the
    defaults; the Schema parameter maps them to other names. Only ``item``
    and ``time`` are required. Other columns are ignored unless the Schema
    lists them in ``tooltip``.

    item : str
        What happened or was found; the mark's name.
    time : str
        When: a year (``1610``), ``YYYY-MM``, ``YYYY-MM-DD``, or an ISO
        date-time (``2024-01-08T14:03:00Z``; offsets are converted to UTC).
    group : str, optional
        The row the event sits on. Blank or absent puts every event on one
        row, ``all``.
    kind : str, optional
        Category for the mark's colour and shape, with a chip to show or
        hide it.
    emphasis : str, optional
        ``Y`` or blank. Emphasised events get a larger mark and a label.
    detail, source : str, optional
        Text for the tooltip and table; ``source`` is an absolute http(s) URL.
inputs.list : list of str
    JSON objects, merged in order. One string holding the whole
    configuration works, and so does one string per parameter.

    Timeline Title : str
        Page title.
    Timeline Filename : str
        Output file name; spaces become ``_`` and the extension is forced
        to ``.html``.
    Data Sources : str or dict, optional
        JSON ``{"label": "url", ...}``, shown as links under the title.
    Schema : str or dict, optional
        Which of your columns fills each field::

            {"events": {"item": "body", "time": "year", "kind": {"value": "survey"}},
             "tooltip": ["discovered_by"]}

        In ``events``, a string names a column; any other value (``true``,
        a number, or ``{"value": "text"}``) is a constant for every row.
        Unmapped fields use the default column name if the table has it.
        ``tooltip`` lists extra columns shown in the tooltip.
    Group Order : str or list, optional
        Row order, top first. Groups not listed follow, earliest first.
        Without it, rows are ordered by their earliest event.
    Eras : str or list, optional
        Shaded bands, ``[{"label": "...", "start": time, "end": time}]``;
        ``end`` may be left out to run to the last event.
inputs.resources : list of str, optional
    The first image (``.svg .png .jpg .jpeg .webp .gif``) is embedded beside
    the title. No image means no logo.

Outputs
-------
outputs.string : str
    Timeline Stats (JSON): ``{"Overall Stats": {...}, "Parameters": {...}}``.
outputs.table : pandas.DataFrame
    Timeline Table: one row per group (Group, Events, First, Last, Kinds), in
    row order.
outputs.resource : str
    Timeline: file name of the downloadable d3 page.

Raises
------
ValueError
    If the Schema has an unknown key or names a column the table lacks, or
    a time or era can't be read.

Notes
-----
Times are kept as ISO text with their precision (year, month, day or
date-time), so years before 1678, which pandas timestamps can't hold, work.
"""

from brewlytics import *

## for more information see the associated markdown file (info button)
## Or use help('brewlytics') to see help documentation in the print output

################################################################################
##
## D3.JS TIMELINE
##
################################################################################
## CHANGE LOG
##==============================================================================
## 2026-11-28 - Initial code: events table -> self-contained d3 timeline page;
##              Schema, Group Order, Eras and Data Sources parameters
##
################################################################################
################################################################################

import base64
import html
import json
import os
import re
from collections import Counter
from datetime import datetime, timezone

import pandas as pd

################################################################################
################################################################################
## SET RUN-TIME ENVIRONMENTAL VARIABLES
################################################################################
################################################################################

D3_VERSION = '7.9.0'
D3_URL = 'https://cdn.jsdelivr.net/npm/d3@%s/dist/d3.min.js' % D3_VERSION

IMAGE_TYPES = {'.svg': 'image/svg+xml', '.png': 'image/png', '.jpg': 'image/jpeg',
               '.jpeg': 'image/jpeg', '.webp': 'image/webp', '.gif': 'image/gif'}

EVENT_FIELDS = ['item', 'time', 'group', 'kind', 'emphasis', 'detail', 'source']
SCHEMA_KEYS = ['events', 'tooltip']
DEFAULT_GROUP = 'all'

YEAR = re.compile(r'^(\d{1,4})(?:\.0+)?$')          # 1610, or 1610.0 from a numeric column
MONTH = re.compile(r'^(\d{1,4})-(\d{2})$')           # 1610-01

################################################################################
################################################################################
## FUNCTIONS
################################################################################
################################################################################

def read_model_data(json_strings):
    """
    Merge the model's JSON configuration strings into one dict.

    Parameters
    ----------
    json_strings : iterable of str
        JSON objects: the whole configuration in one string, or one string
        per parameter.

    Returns
    -------
    dict
        All parameters; a later string overrides an earlier key.
    """
    md = dict()
    for s in json_strings:
        md.update(json.loads(s))
    return md


def as_json(value, empty):
    """
    Read a structured parameter that may arrive parsed or as JSON text.

    Parameters
    ----------
    value : dict, list, str or None
        The parameter value.
    empty : dict or list
        Returned when ``value`` is None or blank.

    Returns
    -------
    dict or list
        ``value`` itself, the parsed JSON, or ``empty``.
    """
    if isinstance(value, (dict, list)):
        return value
    if value is None or str(value).strip() == '':
        return empty
    return json.loads(value)


def html_filename(name):
    """
    Turn the Timeline Filename parameter into an ``.html`` file name.

    Parameters
    ----------
    name : str
        Requested file name, with or without an extension.

    Returns
    -------
    str
        Name with spaces replaced by ``_`` and the extension forced to
        ``.html``, e.g. ``'My Timeline.png'`` -> ``'My_Timeline.html'``.
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
        Path of the first file whose extension is in ``IMAGE_TYPES``.
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
        Table as delivered by brew, e.g. with a column ``'item{string}'``.

    Returns
    -------
    pandas.DataFrame
        Copy with columns renamed (``'item{string}'`` -> ``'item'``),
        missing values as ``''``, and every cell as trimmed text.
    """
    out = df.copy()
    out.columns = [column_name.split('{')[0] for column_name in out.columns]
    ## object first: filling '' into an all-blank (float) column is an error in later pandas
    return out.astype(object).fillna('').astype(str).apply(lambda c: c.str.strip())


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
        ``events`` (``{field: column name or constant}``) and ``tooltip``
        (list of column names).

    Raises
    ------
    ValueError
        Naming unknown keys or fields, ``item`` / ``time`` mapped to
        something other than a column name, or a constant without a value.
    """
    schema = as_json(value, {})
    events = as_json(schema.get('events'), {})
    tooltip = schema.get('tooltip') or []
    problems = ['unknown Schema keys: %s' % sorted(set(schema) - set(SCHEMA_KEYS)),
                'unknown events fields: %s' % sorted(set(events) - set(EVENT_FIELDS)),
                'must name a column: %s' % [f for f in ('item', 'time') if not isinstance(events.get(f, f), str)],
                'constants need a "value": %s' % sorted(f for f, v in events.items()
                                                         if isinstance(v, dict) and 'value' not in v)]
    problems = [p for p in problems if not p.endswith('[]')]
    if problems:
        raise ValueError('Schema: ' + '; '.join(problems) + '. Fields are %s.' % EVENT_FIELDS)
    return {'events': events, 'tooltip': [tooltip] if isinstance(tooltip, str) else list(tooltip)}


def select_columns(table, mapping, fields):
    """
    Rename a table's columns to the script's field names.

    Parameters
    ----------
    table : pandas.DataFrame
        The events table.
    mapping : dict
        ``{field: column name or constant}`` from the Schema. A string is a
        column name; ``{"value": x}``, a bool or a number is a constant.
    fields : list of str
        ``EVENT_FIELDS``.

    Returns
    -------
    pandas.DataFrame
        One text column per field that is mapped, or that the table has
        under its default name. Fields with neither are left out.

    Raises
    ------
    ValueError
        Naming the mapped or required columns the table doesn't have.
    """
    out = pd.DataFrame(index=table.index)
    missing = []
    for field in fields:
        spec = mapping.get(field, field)
        if isinstance(spec, str):
            if spec in table.columns:
                out[field] = table[spec]
            elif field in mapping or field in ('item', 'time'):
                missing.append(spec)
        else:
            value = spec['value'] if isinstance(spec, dict) else spec
            out[field] = '' if value is None else str(value)
    if missing:
        raise ValueError('The events table has no column %s. It has: %s' % (missing, list(table.columns)))
    return out


def add_defaults(events):
    """
    Fill in the optional fields the table doesn't have.

    Parameters
    ----------
    events : pandas.DataFrame
        From ``select_columns``.

    Returns
    -------
    pandas.DataFrame
        Copy with every field; a blank ``group`` becomes ``DEFAULT_GROUP``,
        the other missing fields are blank.
    """
    events = events.copy()
    for field in EVENT_FIELDS:
        if field not in events.columns:
            events[field] = ''
    events['group'] = events['group'].where(events['group'] != '', DEFAULT_GROUP)
    return events[EVENT_FIELDS]


def parse_time(text):
    """
    Read one time value.

    Parameters
    ----------
    text : str
        A year, ``YYYY-MM``, ``YYYY-MM-DD`` or ISO date-time.

    Returns
    -------
    iso : str
        ``YYYY-MM-DD`` (padded to 4-digit years), with ``THH:MM:SS`` in UTC
        for a date-time. Sortable as text.
    precision : str
        ``year``, ``month``, ``day`` or ``datetime``; how the page prints it.

    Raises
    ------
    ValueError
        If the text is none of those.
    """
    text = str(text).strip()
    m = YEAR.match(text)
    if m:
        return '%04d-01-01' % int(m.group(1)), 'year'
    m = MONTH.match(text)
    if m and 1 <= int(m.group(2)) <= 12:
        return '%04d-%s-01' % (int(m.group(1)), m.group(2)), 'month'
    if len(text) == 10:
        t = datetime.strptime(text, '%Y-%m-%d')
        return '%04d-%02d-%02d' % (t.year, t.month, t.day), 'day'
    t = datetime.fromisoformat(text.replace('Z', '+00:00'))
    if t.tzinfo is not None:
        t = t.astimezone(timezone.utc)
    ## built by hand: strftime('%Y') doesn't pad years below 1000 on every platform
    return '%04d-%02d-%02dT%02d:%02d:%02d' % (t.year, t.month, t.day, t.hour, t.minute, t.second), 'datetime'


def read_times(events):
    """
    Parse the ``time`` column.

    Parameters
    ----------
    events : pandas.DataFrame
        Events with a text ``time`` column.

    Returns
    -------
    pandas.DataFrame
        Copy with ``time`` as ISO text and a ``precision`` column.

    Raises
    ------
    ValueError
        Naming every event whose time can't be read.
    """
    parsed, bad = [], []
    for item, text in zip(events['item'], events['time']):
        try:
            parsed.append(parse_time(text))
        except ValueError:
            parsed.append(('', ''))
            bad.append('%s (%r)' % (item, text))
    if bad:
        raise ValueError('time must be a year, YYYY-MM, YYYY-MM-DD or ISO date-time: %s' % '; '.join(bad))
    out = events.copy()
    out['time'] = [p[0] for p in parsed]
    out['precision'] = [p[1] for p in parsed]
    return out


def read_eras(value):
    """
    Read the Eras parameter.

    Parameters
    ----------
    value : list, str or None
        ``[{"label": "...", "start": time, "end": time}, ...]``; ``end`` is
        optional.

    Returns
    -------
    list of dict
        ``{label, start, end}`` with ISO times; ``end`` is None when open.

    Raises
    ------
    ValueError
        Naming eras with a missing or unreadable start or end.
    """
    eras, bad = [], []
    for era in as_json(value, []):
        label = str(era.get('label', ''))
        try:
            start = parse_time(era['start'])[0]
            end = parse_time(era['end'])[0] if str(era.get('end') or '').strip() else None
        except (KeyError, ValueError):
            bad.append(label or str(era))
            continue
        eras.append({'label': label, 'start': start, 'end': end})
    if bad:
        raise ValueError('Eras need a start (and optional end) in a time format: %s' % bad)
    return eras


def group_order(events, preferred):
    """
    Decide the row order.

    Parameters
    ----------
    events : pandas.DataFrame
        Events with ISO ``time`` and ``group``.
    preferred : list of str
        The Group Order parameter; may be empty or name absent groups.

    Returns
    -------
    list of str
        The listed groups that have events, in the listed order, then the
        rest by their earliest event (ties by name).
    """
    first = events.groupby('group')['time'].min()
    listed = [g for g in preferred if g in first.index]
    rest = sorted((g for g in first.index if g not in listed), key=lambda g: (first[g], g))
    return listed + rest


def tooltip_values(table, columns):
    """
    Read the extra columns shown in each event's tooltip.

    Parameters
    ----------
    table : pandas.DataFrame
        The events table as given (before ``select_columns``).
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
        raise ValueError('Schema tooltip columns not in the events table: %s. It has: %s'
                         % (missing, list(table.columns)))
    return [[[c, v] for c, v in zip(columns, row) if v != ''] for row in table[columns].itertuples(index=False)]


def show_time(iso, precision):
    """
    Print an ISO time at its own precision.

    Parameters
    ----------
    iso : str
        From ``parse_time``.
    precision : str
        ``year``, ``month``, ``day`` or ``datetime``.

    Returns
    -------
    str
        ``'1610'``, ``'1610-03'``, ``'1610-03-02'`` or ``'2024-01-08 14:03:00'``
        (UTC), so a year-only date doesn't look more exact than it is.
    """
    if precision == 'year':
        return str(int(iso[:4]))
    if precision == 'month':
        return '%d-%s' % (int(iso[:4]), iso[5:7])
    if precision == 'day':
        return '%d-%s' % (int(iso[:4]), iso[5:10])
    return '%d-%s' % (int(iso[:4]), iso[5:].replace('T', ' '))


def first_and_last(events):
    """``show_time`` of the earliest and the latest event."""
    ordered = events.sort_values(['time', 'item'])
    return [show_time(r.time, r.precision) for r in (ordered.iloc[0], ordered.iloc[-1])]


def group_table(events, order):
    """
    Build the Timeline Table output.

    Parameters
    ----------
    events : pandas.DataFrame
        Events with ISO ``time``, ``group`` and ``kind``.
    order : list of str
        From ``group_order``.

    Returns
    -------
    pandas.DataFrame
        One row per group in row order: Group, Events, First and Last (at
        each time's precision), Kinds (``"kind: n; ..."``, most first).
    """
    rows = []
    for g in order:
        e = events[events['group'] == g]
        kinds = Counter(k for k in e['kind'] if k)
        first, last = first_and_last(e)
        rows.append({'Group': g, 'Events': len(e), 'First': first, 'Last': last,
                     'Kinds': '; '.join('%s: %d' % kv for kv in sorted(kinds.items(), key=lambda kv: (-kv[1], kv[0])))})
    return pd.DataFrame(rows, columns=['Group', 'Events', 'First', 'Last', 'Kinds'])


def overall_stats(events, order):
    """
    Summarise the whole timeline.

    Parameters
    ----------
    events : pandas.DataFrame
        Events with ISO ``time``, ``kind`` and ``emphasis``.
    order : list of str
        From ``group_order``.

    Returns
    -------
    dict
        ``# of Events``, ``# of Groups``, ``First`` and ``Last`` (at their
        precision),
        ``# of Emphasised`` and ``Events by Kind``.
    """
    kinds = Counter(k for k in events['kind'] if k)
    first, last = first_and_last(events)
    return {'# of Events': len(events),
            '# of Groups': len(order),
            'First': first,
            'Last': last,
            '# of Emphasised': int(sum(as_bool(v) for v in events['emphasis'])),
            'Events by Kind': dict(sorted(kinds.items(), key=lambda kv: (-kv[1], kv[0])))}


def kind_order(events):
    """Kinds, most events first (ties by name); colour and shape follow this order."""
    kinds = Counter(k for k in events['kind'] if k)
    return [k for k, _ in sorted(kinds.items(), key=lambda kv: (-kv[1], kv[0]))]


def timeline_payload(events, order, eras, stats, sources, extras=None):
    """
    Assemble the data embedded in the page.

    Parameters
    ----------
    events : pandas.DataFrame
        Events after ``read_times``.
    order : list of str
        Row order, from ``group_order``.
    eras : list of dict
        From ``read_eras``.
    stats : dict
        From ``overall_stats``; shown in the page header.
    sources : dict
        ``{label: url}`` from the Data Sources parameter.
    extras : list of list, optional
        From ``tooltip_values``, one entry per events row.

    Returns
    -------
    dict
        ``overall``, ``sources``, ``groups``, ``kinds``, ``eras`` and
        ``events`` (sorted by time, then item).
    """
    rows = [{'item': e.item, 'time': e.time, 'precision': e.precision, 'group': e.group,
             'kind': e.kind, 'emphasis': as_bool(e.emphasis), 'detail': e.detail,
             'source': e.source, 'extra': extra}
            for e, extra in zip(events.itertuples(index=False), extras or [[]] * len(events))]
    rows.sort(key=lambda r: (r['time'], r['item']))
    return {'overall': stats, 'sources': [{'label': k, 'url': v} for k, v in sources.items()],
            'groups': order, 'kinds': kind_order(events), 'eras': eras, 'events': rows}


def render_html(payload, title, image_uri=None, d3_url=D3_URL):
    """
    Render the self-contained page.

    Parameters
    ----------
    payload : dict
        From ``timeline_payload``; embedded as JSON.
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
      scale: <a href="https://d3js.org/d3-scale/time" target="_blank" rel="noopener">d3-scale (time)</a> &middot;
      zoom: <a href="https://d3js.org/d3-zoom" target="_blank" rel="noopener">d3-zoom</a></p>
    <p class="sub" id="stats"></p>
  </div>
</header>
<div class="controls">
  <div class="chips" id="kinds" aria-label="Kinds"></div>
  <button id="reset">Reset view</button>
</div>
<div id="chart"><div id="tip" class="tip" hidden></div></div>
<p class="hint">One row per group; one mark per event, coloured and shaped by kind; larger, labelled marks are emphasised events.
Scroll or pinch to zoom in time &middot; drag to pan &middot; hover a mark, or click to pin it &middot; click a kind to hide or show it.</p>
<details id="table-wrap">
  <summary>Table view <span id="table-count"></span></summary>
  <div class="table-scroll"><table id="table">
    <thead><tr>
      <th data-key="time">When</th><th data-key="item">Item</th><th data-key="group">Group</th>
      <th data-key="kind">Kind</th><th data-key="detail">Detail</th><th data-key="source">Source</th>
    </tr></thead>
    <tbody></tbody>
  </table></div>
</details>
<script id="timeline-data" type="application/json">__DATA__</script>
<script src="__D3__"></script>
<script>__JS__</script>
</body>
</html>
'''

PAGE_CSS = '''
:root {
  --bg: #fcfcfb; --ink: #1f1f1e; --ink-2: #55554f; --ink-3: #6e6e68;
  --rule: #e4e4df; --band: #f1f1ec; --tip-bg: #ffffff;
  /* ColorBrewer Dark2 */
  --k-0: #1b9e77; --k-1: #d95f02; --k-2: #7570b3; --k-3: #e7298a;
  --k-4: #66a61e; --k-5: #e6ab02; --k-6: #a6761d; --k-other: #8a8a83;
  color-scheme: light;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --bg: #1a1a19; --ink: #ecece8; --ink-2: #b4b4ad; --ink-3: #9a9a93;
    --rule: #33332f; --band: #242422; --tip-bg: #262624; --k-other: #7d7d77; color-scheme: dark;
  }
}
:root[data-theme="dark"] {
  --bg: #1a1a19; --ink: #ecece8; --ink-2: #b4b4ad; --ink-3: #9a9a93;
  --rule: #33332f; --band: #242422; --tip-bg: #262624; --k-other: #7d7d77; color-scheme: dark;
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
.sources { margin: 0 0 4px; font-size: 13px; color: var(--ink-2); }
.sources a { color: inherit; }
.controls { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; margin: 16px 0 8px; }
button {
  font: inherit; font-size: 13px; color: var(--ink-2); background: none;
  border: 1px solid var(--rule); border-radius: 999px; padding: 3px 10px; cursor: pointer;
}
.chips { display: flex; flex-wrap: wrap; gap: 6px; }
.chips button svg { vertical-align: -1px; margin-right: 5px; }
.chips button.on { color: var(--ink); border-color: var(--ink-3); }
.chips button:not(.on) { text-decoration: line-through; opacity: 0.55; }
#chart { position: relative; width: 100%; }
#chart svg { width: 100%; display: block; cursor: grab; touch-action: none; }
.row-label { fill: var(--ink-2); font-size: 12px; text-anchor: end; }
.row-line { stroke: var(--rule); }
.era rect { fill: var(--band); }
.era text { fill: var(--ink-3); font-size: 11px; }
.axis text { fill: var(--ink-3); font-size: 11px; }
.axis path, .axis line { stroke: var(--rule); }
.mark { stroke: var(--bg); stroke-width: 1.5; cursor: pointer; }
.mark.pinned { stroke: var(--ink); }
.mark-label { fill: var(--ink); font-size: 11px; pointer-events: none;
              paint-order: stroke; stroke: var(--bg); stroke-width: 3px; stroke-linejoin: round; }
.hint { font-size: 12px; color: var(--ink-3); margin: 8px 0 0; }
.tip {
  position: absolute; top: 8px; right: 8px; width: min(340px, calc(100% - 16px));
  background: var(--tip-bg); color: var(--ink); border: 1px solid var(--rule);
  border-radius: 6px; padding: 8px 12px; font-size: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.08);
}
.tip b { font-weight: 600; font-size: 13px; }
.tip .meta { color: var(--ink-2); margin-top: 2px; }
.tip a { color: inherit; }
details { margin-top: 16px; border-top: 1px solid var(--rule); padding-top: 8px; }
summary { cursor: pointer; font-weight: 600; }
summary span { font-weight: normal; color: var(--ink-3); }
.table-scroll { overflow-x: auto; }
table { border-collapse: collapse; width: 100%; font-size: 12px; margin-top: 8px; }
th, td { text-align: left; padding: 4px 8px; border-bottom: 1px solid var(--rule); vertical-align: top; }
th { cursor: pointer; color: var(--ink-2); font-weight: 600; white-space: nowrap; }
td a { color: inherit; }
'''

PAGE_JS = r'''
const data = JSON.parse(document.getElementById("timeline-data").textContent);
const N_KINDS = 7; // the most common kinds get Dark2 and their own shape; the rest share grey circles
const SHAPES = [d3.symbolCircle, d3.symbolTriangle, d3.symbolSquare, d3.symbolDiamond,
                d3.symbolCross, d3.symbolStar, d3.symbolWye];
const kindIndex = new Map(data.kinds.map((k, i) => [k, i]));
const colour = (k) => { const i = kindIndex.get(k); return i === undefined || i >= N_KINDS ? "var(--k-other)" : `var(--k-${i})`; };
const shape = (k) => { const i = kindIndex.get(k); return i === undefined || i >= N_KINDS ? d3.symbolCircle : SHAPES[i]; };
const esc = (s) => String(s).replace(/[&<>"]/g, (ch) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[ch]));
// URLs from the data become links only if they are absolute http(s); anything else
// (javascript:, data:, relative paths) is shown as plain text or dropped.
const safeUrl = (u) => {
  try { const p = new URL(String(u)); return p.protocol === "http:" || p.protocol === "https:" ? p.href : null; }
  catch (err) { return null; }
};
const safeLink = (u, text) => { const s = safeUrl(u); return s ? `<a href="${esc(s)}" target="_blank" rel="noopener">${esc(text)}</a>` : ""; };

// ISO text -> Date in UTC; setUTCFullYear keeps years below 100 as written
function toDate(iso) {
  const [day, clock] = iso.split("T");
  const [y, m, d] = day.split("-").map(Number);
  const [hh, mm, ss] = (clock || "0:0:0").split(":").map(Number);
  const t = new Date(0);
  t.setUTCFullYear(y, m - 1, d);
  t.setUTCHours(hh, mm, ss, 0);
  return t;
}
const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
function when(e) {
  const t = toDate(e.time), y = t.getUTCFullYear();
  if (e.precision === "year") return String(y);
  if (e.precision === "month") return `${MONTHS[t.getUTCMonth()]} ${y}`;
  if (e.precision === "day") return `${t.getUTCDate()} ${MONTHS[t.getUTCMonth()]} ${y}`;
  return e.time.replace("T", " ").slice(0, 16) + " UTC";
}

const events = data.events.map((e) => ({ ...e, date: toDate(e.time) }));
const o = data.overall;
const yearOf = (t) => t.split("-")[0];
const span = yearOf(o.First) === yearOf(o.Last) ? yearOf(o.First) : `${yearOf(o.First)}\u2013${yearOf(o.Last)}`;
d3.select("#stats").text(`${o["# of Events"]} events \u00b7 ${o["# of Groups"]} groups \u00b7 ${span}` +
  (data.kinds.length ? ` \u00b7 ${data.kinds.length} kinds` : ""));
d3.select("#sources").html(data.sources.length
  ? "Data: " + data.sources.map((s) => safeLink(s.url, s.label) || esc(s.label)).join(" \u00b7 ")
  : null);

// kind chips
const active = new Set(data.kinds.concat([""]));
const counts = d3.rollup(events, (v) => v.length, (e) => e.kind);
d3.select("#kinds").selectAll("button").data(data.kinds).join("button").attr("class", "on")
  .html((k) => `<svg width="10" height="10" viewBox="-5 -5 10 10"><path d="${d3.symbol(shape(k), 40)()}" fill="${colour(k)}"/></svg>${esc(k)} (${counts.get(k)})`)
  .on("click", function (ev, k) {
    if (active.has(k)) active.delete(k); else active.add(k);
    d3.select(this).classed("on", active.has(k));
    draw(); table();
  });

// layout
const ROW = 46, M = { top: 22, right: 20, bottom: 28 };
const chart = d3.select("#chart");
const svg = chart.append("svg");
const rowOf = new Map(data.groups.map((g, i) => [g, i]));
const height = M.top + M.bottom + ROW * data.groups.length;
svg.attr("height", height);
const labelWidth = Math.min(200, 12 + d3.max(data.groups, (g) => g.length) * 7);
const extent = d3.extent(events, (e) => e.date);
const DAY = 864e5;
const pad = extent[1] - extent[0] ? Math.max((extent[1] - extent[0]) * 0.03, DAY) : 365 * DAY;   // 3% each side; a year if all at once
const x0 = d3.scaleUtc().domain([new Date(+extent[0] - pad), new Date(+extent[1] + pad)]);
let x = x0.copy();

const gEras = svg.append("g");
const gRows = svg.append("g");
const gAxis = svg.append("g").attr("class", "axis");
const gMarks = svg.append("g");
const gLabels = svg.append("g");
const clip = svg.append("defs").append("clipPath").attr("id", "plot").append("rect");
[gEras, gMarks, gLabels].forEach((g) => g.attr("clip-path", "url(#plot)"));

const rowY = (g) => M.top + ROW * rowOf.get(g) + ROW / 2;
const size = (e) => (e.emphasis ? 120 : 52);

// place marks on their row, nudged up or down so neighbours don't overlap
function dodge(list) {
  const R = 4.5, STEP = 2 * R, placed = new Map();   // R: radius of a plain mark
  for (const e of list) {
    const px = x(e.date), row = placed.get(e.group) || [];
    let off = 0;
    for (const k of [0, -1, 1, -2, 2]) {          // slots up and down the row, nearest first
      const tryOff = k * STEP;
      if (Math.abs(tryOff) > ROW / 2 - R) continue;
      if (!row.some((p) => Math.abs(p.x - px) < STEP && Math.abs(p.off - tryOff) < STEP)) { off = tryOff; break; }
    }
    row.push({ x: px, off });
    placed.set(e.group, row);
    e.y = rowY(e.group) + off;
  }
}

let width = 0, pinned = null;
const tip = d3.select("#tip");
function show(e) {
  const src = e.source && safeUrl(e.source) ? `<div class="meta">${safeLink(e.source, "source")}</div>` : "";
  const extra = e.extra.length ? `<div class="meta">${e.extra.map(([k, v]) => esc(k) + ": " + esc(v)).join(" \u00b7 ")}</div>` : "";
  tip.attr("hidden", null).html(
    `<b>${esc(e.item)}</b><div class="meta">${esc(when(e))} \u00b7 ${esc(e.group)}${e.kind ? " \u00b7 " + esc(e.kind) : ""}</div>` +
    extra + (e.detail ? `<div class="meta">${esc(e.detail)}</div>` : "") + src);
}
function hide() { if (!pinned) tip.attr("hidden", true); }

function draw() {
  width = chart.node().clientWidth;
  const left = labelWidth;
  x.range([left, width - M.right]);
  x0.range([left, width - M.right]);
  svg.attr("viewBox", `0 0 ${width} ${height}`);
  clip.attr("x", left).attr("y", 0).attr("width", width - M.right - left).attr("height", height);

  const top = M.top, bottom = height - M.bottom;
  const eras = gEras.selectAll("g").data(data.eras).join((en) => { const g = en.append("g").attr("class", "era"); g.append("rect"); g.append("text"); return g; });
  eras.select("rect").attr("x", (d) => x(toDate(d.start))).attr("y", top - 16)
    .attr("width", (d) => Math.max(0, (d.end ? x(toDate(d.end)) : width) - x(toDate(d.start)))).attr("height", bottom - top + 16);
  // era labels start at the band's left edge, kept inside the plot
  eras.select("text").attr("x", (d) => Math.max(left, x(toDate(d.start))) + 4).attr("y", top - 5).text((d) => d.label);

  gRows.selectAll("g").data(data.groups).join((en) => { const g = en.append("g"); g.append("line").attr("class", "row-line"); g.append("text").attr("class", "row-label"); return g; })
    .call((g) => g.select("line").attr("x1", left).attr("x2", width - M.right).attr("y1", rowY).attr("y2", rowY))
    .call((g) => g.select("text").attr("x", left - 10).attr("y", (d) => rowY(d) + 4).text((d) => d));

  gAxis.attr("transform", `translate(0,${bottom})`).call(d3.axisBottom(x).ticks(Math.max(2, Math.floor((width - left) / 90))).tickSizeOuter(0));

  const shown = events.filter((e) => active.has(e.kind));
  dodge(shown);
  gMarks.selectAll("path").data(shown, (e) => e.item + e.time).join("path")
    .attr("class", (e) => "mark" + (e === pinned ? " pinned" : ""))
    .attr("d", (e) => d3.symbol(shape(e.kind), size(e))())
    .attr("fill", (e) => colour(e.kind))
    .attr("transform", (e) => `translate(${x(e.date)},${e.y})`)
    .on("mouseenter", (ev, e) => { if (!pinned) show(e); })
    .on("mouseleave", hide)
    .on("click", (ev, e) => { ev.stopPropagation(); pinned = pinned === e ? null : e; if (pinned) show(e); else hide(); draw(); });
  // labels sit to the right of their mark, or to the left near the right edge
  const flip = (e) => x(e.date) > width - M.right - 110;
  const inView = (e) => x(e.date) >= left && x(e.date) <= width - M.right;
  gLabels.selectAll("text").data(shown.filter((e) => e.emphasis && inView(e)), (e) => e.item + e.time).join("text")
    .attr("class", "mark-label").attr("x", (e) => x(e.date) + (flip(e) ? -9 : 9)).attr("y", (e) => e.y - 7)
    .attr("text-anchor", (e) => (flip(e) ? "end" : "start"))
    .text((e) => `${e.item} ${when(e)}`);
}

// zoom and pan along time only
const zoom = d3.zoom().scaleExtent([1, 5000])
  .filter((ev) => !ev.button && ev.type !== "dblclick")
  .on("zoom", (ev) => { x = ev.transform.rescaleX(x0); draw(); });
svg.call(zoom);
svg.on("click", () => { if (pinned) { pinned = null; hide(); draw(); } });
d3.select("#reset").on("click", () => svg.transition().duration(400).call(zoom.transform, d3.zoomIdentity));
window.addEventListener("resize", () => { zoom.translateExtent([[labelWidth, 0], [chart.node().clientWidth - M.right, height]]); draw(); });
zoom.extent([[labelWidth, 0], [chart.node().clientWidth - M.right, height]]).translateExtent([[labelWidth, 0], [chart.node().clientWidth - M.right, height]]);

// table view: the events currently shown
let sortKey = "time", sortDir = 1;
d3.selectAll("#table th").on("click", function () {
  const k = this.dataset.key;
  sortDir = k === sortKey ? -sortDir : 1; sortKey = k; table();
});
function table() {
  const rows = events.filter((e) => active.has(e.kind))
    .sort((a, b) => sortDir * d3.ascending(String(a[sortKey]), String(b[sortKey])) || d3.ascending(a.time, b.time));
  d3.select("#table-count").text(`(${rows.length})`);
  d3.select("#table tbody").selectAll("tr").data(rows).join("tr").html((e) =>
    `<td>${esc(when(e))}</td><td>${esc(e.item)}</td><td>${esc(e.group)}</td><td>${esc(e.kind)}</td>` +
    `<td>${esc(e.detail)}</td><td>${safeLink(e.source, "link")}</td>`);
}

draw();
table();
'''

################################################################################
## MODEL DATA
################################################################################

md = read_model_data(inputs.list)

timeline_title = md['Timeline Title']
timeline_filename = html_filename(md['Timeline Filename'])
data_sources = as_json(md.get('Data Sources'), {})       # {"Source name": "https://...", ...}
schema = read_schema(md.get('Schema'))                    # your column names; none = the default names
preferred_order = as_json(md.get('Group Order'), [])      # row order, top first
eras = read_eras(md.get('Eras'))                          # shaded bands
header_image = find_image(getattr(inputs, 'resources', None) or [])  # no resources wired = no image

################################################################################
## BODY
################################################################################

## The events table: the first of inputs.tables, or inputs.table
wired = list(getattr(inputs, 'tables', None) or [])
table_in = strip_cv_types(wired[0] if wired else inputs.table)
events = add_defaults(select_columns(table_in, schema['events'], EVENT_FIELDS))
extras = tooltip_values(table_in, schema['tooltip'])
events = read_times(events)

order = group_order(events, [str(g) for g in preferred_order])
stats = overall_stats(events, order)
group_stats_table = group_table(events, order)
payload = timeline_payload(events, order, eras, stats, data_sources, extras)

with open(timeline_filename, 'w', encoding='utf-8') as f:
    f.write(render_html(payload, timeline_title, image_data_uri(header_image) if header_image else None))

################################################################################
## OUTPUTS
################################################################################

## Timeline Stats (JSON): overall stats, plus the parameters this run used
outputs.string = json.dumps({'Overall Stats': stats, 'Parameters': md}, indent=4)

## Timeline Table: one row per group
outputs.table = group_stats_table

## Timeline (downloadable d3 page)
outputs.resource = timeline_filename

################################################################################
## SUMMARY
################################################################################

print('%d events in %d groups, %s to %s' % (stats['# of Events'], stats['# of Groups'],
                                             stats['First'], stats['Last']))
print('Events by kind: %s' % (stats['Events by Kind'] or 'no kinds'))
print('Eras: %s' % ([e['label'] for e in eras] or 'none'))
print('Header image: %s' % (header_image or 'none'))
print('Wrote %s' % timeline_filename)
print()
print(group_stats_table.to_string(index=False))
