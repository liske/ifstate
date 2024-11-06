#!/bin/sh

# interface specific wrapper to run hooks.

export IFS_SCRIPT="${script}"
export IFS_RUNDIR="${rundir}"

export IFS_IFNAME="${ifname}"
export IFS_INDEX="${index}"
export IFS_NETNS="${netns}"

# hook arguments
${args}

if [ -z "$$IFS_NETNS" ]; then
    exec "$$IFS_SCRIPT" "$$@"
else
    exec ip netns exec "$$IFS_NETNS" "$$IFS_SCRIPT" "$$@"
fi
