"""Download medal tables, participant lists and World Bank data into data/raw.

By default each Wikipedia page is fetched at the revision pinned in the manifests, so the data
are identical to the committed copy. Pass --latest to take the current revision of every page
and record new revision ids.
"""

import sys

from olympic_hosts.fetch import fetch_medal_tables, fetch_participants, fetch_world_bank

if __name__ == "__main__":
    pinned = "--latest" not in sys.argv
    print(fetch_medal_tables(pinned=pinned)[["games_id", "revid"]].to_string(index=False))
    print(f"{len(fetch_participants(pinned=pinned))} participant rows")
    print(f"{len(fetch_world_bank())} World Bank rows")
