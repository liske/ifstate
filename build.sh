#!/bin/sh

# build directory
tempdir=$(mktemp -d)
builddir=$(mktemp -d)
trap 'git worktree remove "$tempdir"; rm -rf -- "$tempdir";  rm -rf -- "$builddir"' EXIT

# get current commit
commit=$(git describe --always)

# rebuild jekyll site
echo $builddir
read
jekyll clean --destination "$builddir"
read
jekyll build --destination "$builddir"
read

# sync into 'pages' branch
git worktree add "$tempdir" pages
rsync -rAv --delete --exclude .git --exclude .domains "$builddir/" "$tempdir/"

# commit & push site
( cd "$tempdir" && git add -A && git commit -m "rebuild at $(date -Is) from $commit"; )
git push origin pages
