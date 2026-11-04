"""Build data/processed/olympics.duckdb from raw and reference data."""

from olympic_hosts.build import build

if __name__ == "__main__":
    print(f"Built {build()}")
