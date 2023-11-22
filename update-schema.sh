#!/bin/sh

git checkout master -- schema/ifstate.conf.schema.json
generate-schema-doc --no-link-to-reused-ref --expand-buttons --config template_name=js_offline schema/ifstate.conf.schema.json schema/index.html
