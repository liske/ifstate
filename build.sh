#!/bin/sh

# build directory
tempdir=$(mktemp -d)
trap 'git worktree remove "$tempdir"; rm -rf -- "$tempdir"' EXIT

# get current commit
commit=$(git describe --always)

# get pages branch
git worktree add "$tempdir" pages

# rebuild jekyll site
jekyll build --destination "$tempdir"

# commit & push site
( cd "$tempdir" && git add -A && git commit -m "rebuild at $(date -Is) from $commit"; )
git push origin pages
