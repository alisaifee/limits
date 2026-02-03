#!/bin/bash
set -euo pipefail

make lint

# last tag that is a release
last_tag=$(git tag | grep -v 'v' | sort -Vr | head -n 1)
echo "Current version: $(uv run hatch version), last tag: $last_tag"

read -p "New version: " new_version

# Find the last changelog portion to insert before
last_portion=$(grep -P "^Changelog$" HISTORY.rst -5 | grep -P "^v\d+\.\d+" || true)

# Get git notes (from the 'next' ref)
notes=$(GIT_NOTES_REF=refs/notes/next git log "$last_tag"..HEAD --pretty=format:'%N' || true)

python - <<PY
import datetime

history_file = "HISTORY.rst"
new_version = "$new_version"
last_portion = """$last_portion"""
notes = """$notes"""

# Trim leading/trailing blank lines from notes but preserve internal spacing
notes = notes.strip("\n")

# Build the new changelog block
heading = f"v{new_version}"
sep = "-" * len(heading)
release_date = datetime.date.today().isoformat()

new_changelog = "\n".join([
    heading,
    sep,
    f"Release Date: {release_date}",
    "",
    notes,
    ""
]).strip("\n") + "\n\n"  # ensure one blank line at the end

# Read HISTORY.rst and insert new changelog
content = open(history_file).read()
if last_portion:
    updated = content.replace(last_portion, new_changelog + last_portion)
else:
    updated = new_changelog + content

with open(history_file + ".new", "w", newline="\n") as f:
    f.write(updated)
PY

mv HISTORY.rst.new HISTORY.rst

tmp_commits=$(mktemp)
git log "$last_tag"..HEAD --format='* %s (%h)%n%b' \
  | sed -E '/^\*/! s/(.*)/    \1/g' > "$tmp_commits"

vim -O HISTORY.rst "$tmp_commits"

rm "$tmp_commits"

if rst2html HISTORY.rst > /dev/null 2>&1; then
    echo "Tagging $new_version"
    git add HISTORY.rst
    git commit -m "Update changelog for ${new_version}"
    git tag -s "$new_version" -m "Tag version ${new_version}"
else
    echo "Changelog has errors. Skipping tag."
fi
