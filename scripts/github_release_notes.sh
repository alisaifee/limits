#!/bin/bash

TAG=$(echo $GITHUB_REF | cut -d / -f 3)
git format-patch -1 $TAG --stdout | grep -P '^\+' | \
    sed '1,4d' | \
    sed -E 's/^\+(.*)/\1/' | \
    grep -v "Release Date" | \
    # Convert top-level bullets (*) to headers (##)
    sed -E -e 's/^\* (.*)/## \1/' | \
    # Convert indented sub-bullets to Markdown '- '
    sed -E -e 's/^  \* /- /'  | \
    # Remove any remaining 2-space indentation
    sed -E -e 's/^  //' | \
    # Convert inline code ``like_this`` to Markdown `like_this`
    sed -E -e 's/``([^`]*)``/`\1`/g' | \
    # Convert Sphinx roles :role:`text` or :role:`~path.to.Class` to just `text`
    sed -E -e 's/:([a-z]+):`~?([^`]*)`/`\2`/g' | \
    # Convert full links `text <url>`_ to Markdown [text](url)
    sed -E -e 's/`([^`]*) <(https?:\/\/[^>]*)>`_/\[\1\](\2)/g'
