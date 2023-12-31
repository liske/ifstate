#!/bin/sh

# This script fetches to most recent schema and changelog from the master branch.

echo "Updating schema..."
git checkout master -- schema/ifstate.conf.schema.json
generate-schema-doc --config-file schema/config.yaml schema/ifstate.conf.schema.json schema/index.html


echo "Updating changelog..."
git checkout master -- CHANGELOG.md
cat <<EOF > changelog.md
---
title: ChangeLog
layout: page
permalink: changelog/
---

EOF

tail -n +3 CHANGELOG.md | \
    sed -e 's/^## /# ifstate /' | \
    sed -re 's@(#([0-9]+))@[\1](https://codeberg.org/liske/ifstate/issues/\2)@' | \
    sed -re 's@([0-9a-f]{7})@[\1](https://codeberg.org/liske/ifstate/commit/\1)@' \
    >> changelog.md
rm -f CHANGELOG.md
git restore --staged CHANGELOG.md
