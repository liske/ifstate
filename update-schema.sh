#!/bin/sh

git checkout master -- schema/ifstate.conf.schema.json
generate-schema-doc --config-file schema/config.yaml schema/ifstate.conf.schema.json schema/index.html
