-- One row per nation per Games it took part in, for nations that won at least one medal
-- in that season between 1960 and 2026. Zero medals therefore means "took part, won nothing";
-- boycotts, bans and nations that did not yet exist are simply absent.

CREATE OR REPLACE VIEW analysis_panel AS
WITH
-- 2012 Summer has no participant list on Wikipedia; all 204 NOCs took part, so a nation
-- counts as present if it took part in 2008 or 2016.
participated AS (
    SELECT games_id, nation_id FROM participation
    UNION
    SELECT '2012S', nation_id FROM participation WHERE games_id IN ('2008S', '2016S')
),
medals AS (
    SELECT games_id, nation_id, sum(total) AS medals, sum(gold) AS golds
    FROM medal_result GROUP BY ALL
),
games_totals AS (
    SELECT games_id, sum(total) AS medals_awarded FROM medal_result GROUP BY ALL
),
season_winners AS (
    SELECT DISTINCT g.season, m.nation_id
    FROM medal_result AS m JOIN games AS g USING (games_id) WHERE m.total > 0
),
hosts AS (
    SELECT season, season_seq, host_nation_id FROM games
)
SELECT
    p.nation_id,
    n.nation_name,
    g.games_id,
    g.year,
    g.season,
    coalesce(m.medals, 0) AS medals,
    coalesce(m.golds, 0) AS golds,
    t.medals_awarded,
    coalesce(m.medals, 0) / t.medals_awarded AS medal_share,
    (g.host_nation_id = p.nation_id)::INTEGER AS host,
    coalesce((nxt.host_nation_id = p.nation_id), false)::INTEGER AS next_host,
    coalesce((prv.host_nation_id = p.nation_id), false)::INTEGER AS prev_host,
    e.gdp_usd,
    e.population
FROM participated AS p
JOIN games AS g ON g.games_id = p.games_id AND NOT g.future
JOIN nation AS n ON n.nation_id = p.nation_id AND n.kind = 'nation'
JOIN season_winners AS w ON w.season = g.season AND w.nation_id = p.nation_id
JOIN games_totals AS t ON t.games_id = g.games_id
LEFT JOIN medals AS m ON m.games_id = g.games_id AND m.nation_id = p.nation_id
LEFT JOIN hosts AS nxt ON nxt.season = g.season AND nxt.season_seq = g.season_seq + 1
LEFT JOIN hosts AS prv ON prv.season = g.season AND prv.season_seq = g.season_seq - 1
-- Economics from the Games year, or the latest earlier year with data (up to 2 years back),
-- because the World Bank series lag the 2026 Games.
LEFT JOIN LATERAL (
    SELECT x.gdp_usd, x.population
    FROM nation_year_economics AS x
    WHERE x.iso3 = n.iso3 AND x.year BETWEEN g.year - 2 AND g.year
      AND x.gdp_usd IS NOT NULL AND x.population IS NOT NULL
    ORDER BY x.year DESC
    LIMIT 1
) AS e ON true;
