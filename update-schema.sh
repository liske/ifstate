#!/bin/sh

git checkout master -- schema/ifstate.conf.json
generate-schema-doc schema/ifstate.conf.json schema/index.html
