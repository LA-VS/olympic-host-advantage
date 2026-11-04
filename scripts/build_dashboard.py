"""Rebuild the database and write the interactive dashboard to docs/index.html.

GitHub Pages serves docs/ from the main branch, so the committed page is the live dashboard.
"""

from olympic_hosts.build import build
from olympic_hosts.dashboard import write_dashboard
from olympic_hosts.paths import REPO_ROOT

if __name__ == "__main__":
    build()
    print(f"Wrote {write_dashboard(REPO_ROOT / 'docs' / 'index.html')}")
