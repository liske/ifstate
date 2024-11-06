#!/bin/sh

# interface specific wrapper to run hooks
export IFS_SCRIPT="${script}"
export IFS_RUNDIR="${rundir}"

export IFS_IFNAME="${ifname}"
export IFS_INDEX="${index}"
export IFS_NETNS="${netns}"
export IFS_VRF="${vrf}"

# hook arguments
${args}


if [ -z "$$IFS_NETNS" ]; then
    if [ -z "$$IFS_VRF" ]; then
        # just exec the script
        exec "$$IFS_SCRIPT" "$$@"
    else
        # exec in VRF
        exec ip vrf exec "$$IFS_VRF" "$$IFS_SCRIPT" "$$@"
    fi
else
    if [ -z "$$IFS_VRF" ]; then
        # exec in NetNS
        exec ip netns exec "$$IFS_NETNS" "$$IFS_SCRIPT" "$$@"
    else
        # exec in NetNS->VRF
        exec ip netns exec "$$IFS_NETNS" ip vrf exec "$$IFS_VRF" "$$IFS_SCRIPT" "$$@"
    fi
fi
