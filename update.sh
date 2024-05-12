#!/bin/sh -e

# This script fetches schemas and changelog from the master branch.

release_tag=$(git tag -l "*.*.*"|sort -n|tail -n 1)
version_dir=$(echo "$release_tag"|cut -d. -f1,2)
major_dir=$(echo "$release_tag"|cut -d. -f1)

echo "Updating schema for $release_tag..."
mkdir -p "schema/$version_dir"
rm -f schema/ifstate.conf.schema.json "schema/$version_dir/ifstate.conf.schema.json"
git checkout "tags/$release_tag" -- schema/ifstate.conf.schema.json
git mv schema/ifstate.conf.schema.json "schema/$version_dir/ifstate.conf.schema.json"
generate-schema-doc --config-file schema/config.yaml "schema/$version_dir/ifstate.conf.schema.json" "schema/$version_dir/index.html"
ln -vfns "$version_dir" "schema/$major_dir"

echo "Restore legacy schema file..."
cp schema/1/ifstate.conf.schema.json schema/ifstate.conf.schema.json

echo "Updating changelog..."
git checkout "tags/$release_tag" -- CHANGELOG.md
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

echo "Update schema page..."

cat <<EOF > schema.md
---
title: Schema
layout: page
---

The \`ifstatecli\` command uses a config file based on *Yaml* and must comply to
the provided *JSON Schema*. It is possible to include values from external files
(i.e. private keys) using the provided \`!include\` tag.
EOF

for release in $(find schema -mindepth 1 -maxdepth 1 -type d -name '*.*'|cut -d/ -f2|sort -rn); do
cat <<EOF >> schema.md

- ifstate $release
  - [schema description](schema/$release/)
  - [ifstate.conf.schema.json](schema/$release/ifstate.conf.schema.json)
EOF
done
