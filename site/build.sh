#!/usr/bin/env bash
# Assemble the GitHub Pages site in _site/ from site/index.html and site/publish.txt.
# Fails if a listed source is missing or a landing-page link points at nothing.
set -euo pipefail
cd "$(dirname "$0")/.."
rm -rf _site && mkdir -p _site
cp site/index.html _site/index.html
touch _site/.nojekyll
while IFS= read -r line; do
  [[ -z "$line" || "$line" == \#* ]] && continue
  src="${line%% -> *}"; dest="${line##* -> }"
  [[ -f "$src" ]] || { echo "missing source: $src" >&2; exit 1; }
  mkdir -p "_site/$(dirname "$dest")"
  cp "$src" "_site/$dest"
  echo "published $dest"
done < site/publish.txt
# every relative link on the landing page must exist in _site/
grep -o 'href="[^"#:]*"' site/index.html | sed 's/href="//; s/"$//' | while IFS= read -r link; do
  [[ -f "_site/$link" ]] || { echo "landing page links to missing page: $link" >&2; exit 1; }
done
echo "site built in _site/"
