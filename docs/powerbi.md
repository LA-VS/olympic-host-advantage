# Power BI report

GitHub cannot render a `.pbix` file, so the report is committed as `reports/olympic_host_advantage.pbix`
with screenshots of each page in `reports/figures/powerbi_*.png`.

## Data

Run `uv run python scripts/export_powerbi.py`. It rebuilds the database and writes one CSV per table to
`data/processed/powerbi/`. In Power BI Desktop, use Get data, Text/CSV, and load all seven files.

## Model view

Create these relationships (single direction, many to one):

| From (many) | To (one) |
|---|---|
| `medal_result[games_id]` | `games[games_id]` |
| `medal_result[nation_id]` | `nation[nation_id]` |
| `participation[games_id]` | `games[games_id]` |
| `participation[nation_id]` | `nation[nation_id]` |
| `noc_map[nation_id]` | `nation[nation_id]` |
| `analysis_panel[games_id]` | `games[games_id]` |
| `analysis_panel[nation_id]` | `nation[nation_id]` |

`nation_year_economics` joins to `nation[iso3]`; leave it unrelated unless a page needs it, because
`analysis_panel` already carries GDP and population at each Games year.

## Measures

```
Medals = SUM ( analysis_panel[medals] )
Medals awarded = SUM ( analysis_panel[medals_awarded] )
Medal share = DIVIDE ( [Medals], [Medals awarded] )
Host medal share = CALCULATE ( [Medal share], analysis_panel[host] = 1 )
Usual medal share = CALCULATE ( AVERAGE ( analysis_panel[medal_share] ), analysis_panel[host] = 0 )
Host uplift = DIVIDE ( [Host medal share], [Usual medal share] )
```

## Pages

1. **Host advantage.** Card with the headline (hosts win 65% more medals, 95% CI 45% to 88%).
   Clustered bar of `Host medal share` against `Usual medal share` by host Games, sorted by `Host uplift`.
   Slicer on `games[season]`.
2. **Nation explorer.** Slicer on `nation[nation_name]`. Line chart of `Medal share` by `games[year]` with
   the host years marked (conditional formatting on `analysis_panel[host]`). Table of medals by Games.
3. **Data model.** A screenshot of the model view, and a table of `noc_map` rows with a note, so viewers can
   see the lineage decisions.
