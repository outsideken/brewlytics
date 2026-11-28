"""Run d3_timeline.py locally, unchanged, with a stand-in `brewlytics` module.

The stand-in plays the brew model around the Python Script functional:

* ``inputs.tables``: ``events.csv`` from the data folder, as a CSV to Table
  functional would supply it.
* ``inputs.list``: the folder's ``params.json`` as one JSON string, the
  whole model configuration in one parameter.
* ``inputs.resources``: every image file in the folder (the script uses the
  first one as the header logo). No image means no logo.

The page is written into the data folder unless ``--out`` says otherwise.

    python run_local.py                    # the minimal starter data in template/
    python run_local.py examples/<name>    # one of the worked examples
    python run_local.py my_data --out web  # your own events/params
"""

import argparse
import json
import os
import sys
import types
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
SCRIPT = HERE / 'd3_timeline.py'
IMAGES = {'.svg', '.png', '.jpg', '.jpeg', '.webp', '.gif'}


def fake_brewlytics(tables, params, resources=()):
    """Return a module with brew's ``inputs`` / ``outputs`` shape."""
    mod = types.ModuleType('brewlytics')
    mod.inputs = types.SimpleNamespace(list=[json.dumps(params)],
                                       tables=list(tables), resources=list(resources))
    mod.outputs = types.SimpleNamespace()
    mod.__all__ = ['inputs', 'outputs']
    return mod


def read_params(folder):
    """Read the folder's ``params.json`` (the model configuration); ``{}`` if there is none."""
    path = Path(folder) / 'params.json'
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}


def run(tables, params, resources=(), out_dir='.'):
    """Execute the brew script in ``out_dir`` and return its ``outputs``."""
    mod = fake_brewlytics(tables, params, resources)
    sys.modules['brewlytics'] = mod
    cwd = os.getcwd()
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    os.chdir(out_dir)
    try:
        exec(compile(SCRIPT.read_text(encoding='utf-8'), str(SCRIPT), 'exec'), {'__name__': '__main__'})
    finally:
        os.chdir(cwd)
        sys.modules.pop('brewlytics', None)
    return mod.outputs


def run_folder(folder, out_dir=None):
    """Run the script on a data folder holding events.csv, params.json and an optional image."""
    folder = Path(folder).resolve()
    events = pd.read_csv(folder / 'events.csv', dtype=str, keep_default_na=False)
    images = sorted(str(p) for p in folder.iterdir() if p.suffix.lower() in IMAGES)
    return run([events], read_params(folder), images, out_dir or folder)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('folder', nargs='?', default=str(HERE / 'template'),
                    help='folder with events.csv and params.json (default: template/)')
    ap.add_argument('--out', help='where to write the page (default: the data folder)')
    args = ap.parse_args()
    out = run_folder(args.folder, args.out)
    print('\n--- outputs.string (Timeline Stats JSON) ---\n' + out.string)
    print('\n--- outputs.table (Timeline Table) ---')
    print('%d rows; columns: %s' % (len(out.table), list(out.table.columns)))
    print('\n--- outputs.resource ---\n' + out.resource)


if __name__ == '__main__':
    main()
