-- Each host's medal share at its home Games against its average share at all its other Games
-- in the same season.
WITH host_rows AS (
    SELECT p.nation_id, p.season, p.games_id, p.medal_share AS host_share, g.host_noc
    FROM analysis_panel AS p JOIN games AS g USING (games_id)
    WHERE p.host = 1
)
SELECT h.games_id, any_value(h.host_noc) AS host_noc, any_value(p.nation_name) AS host,
       round(100 * any_value(h.host_share), 2) AS host_share_pct,
       round(100 * avg(p.medal_share), 2) AS other_years_share_pct,
       round(any_value(h.host_share) / avg(p.medal_share), 2) AS ratio
FROM host_rows AS h
JOIN analysis_panel AS p
  ON p.nation_id = h.nation_id AND p.season = h.season AND p.games_id <> h.games_id
GROUP BY h.games_id
ORDER BY h.games_id;
