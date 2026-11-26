#!/bin/sh
# Print the newest of the versions given as arguments, in SemVer order: a release sorts after its
# own pre-releases (0.1.0 > 0.1.0-rc.2) and numeric pre-release parts compare as numbers
# (rc.10 > rc.2). `sort -V` gets the first one wrong. A leading "v" is allowed and kept.
# deploy/lib/common.sh (version_gt) uses the same key on servers; change both together.
#
#   scripts/newest-version.sh 0.1.0-rc.2 0.1.0      prints 0.1.0
set -eu
printf '%s\n' "$@" | awk '
    function key(pre,   i, k, ids, out) {
        if (pre == "") return "~"
        k = split(pre, ids, ".")
        out = ""
        for (i = 1; i <= k; i++)
            out = out (ids[i] ~ /^[0-9]+$/ ? sprintf("0%09d", ids[i]) : "1" ids[i]) "."
        return out
    }
    NF {
        v = $0; sub(/^v/, "", v)
        pre = ""; dash = index(v, "-")
        if (dash) { pre = substr(v, dash + 1); v = substr(v, 1, dash - 1) }
        split(v, n, ".")
        printf "%09d%09d%09d%s %s\n", n[1], n[2], n[3], key(pre), $0
    }
' | LC_ALL=C sort | tail -n 1 | awk '{ print $2 }'
