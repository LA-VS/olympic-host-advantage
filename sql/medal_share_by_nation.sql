-- Top 10 nations per season by average medal share, with the number of Games attended.
WITH by_nation AS (
    SELECT season, nation_name, count(*) AS games, avg(medal_share) AS avg_share, sum(medals) AS medals
    FROM analysis_panel
    GROUP BY season, nation_name
)
SELECT season, nation_name, games, round(100 * avg_share, 2) AS avg_share_pct, medals
FROM by_nation
QUALIFY row_number() OVER (PARTITION BY season ORDER BY avg_share DESC) <= 10
ORDER BY season, avg_share_pct DESC;
