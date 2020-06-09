#!/bin/sh

git checkout master -- schema/ifstate.conf.schema.json
generate-schema-doc --expand-buttons schema/ifstate.conf.schema.json schema/index.html
