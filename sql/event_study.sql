-- Each host's medal share at the Games before, during and after hosting, as the change in
-- percentage points from its own average over the two Games furthest before hosting
-- (positions -3 and -2), which predate most of the home investment.
WITH seq AS (
    SELECT p.*, g.season_seq FROM analysis_panel AS p JOIN games AS g USING (games_id)
),
events AS (
    SELECT nation_id, season, games_id AS host_games, season_seq AS host_seq FROM seq WHERE host = 1
),
windowed AS (
    SELECT e.host_games, e.nation_id, s.season_seq - e.host_seq AS rel, s.medal_share
    FROM events AS e
    JOIN seq AS s ON s.nation_id = e.nation_id AND s.season = e.season
    WHERE s.season_seq - e.host_seq BETWEEN -3 AND 3
),
baseline AS (
    SELECT host_games, avg(medal_share) AS base, count(*) AS n_base
    FROM windowed WHERE rel IN (-3, -2) GROUP BY ALL
)
SELECT w.host_games, w.nation_id, w.rel, w.medal_share, b.base,
       100 * (w.medal_share - b.base) AS change_pp
FROM windowed AS w JOIN baseline AS b USING (host_games)
ORDER BY w.host_games, w.rel;
