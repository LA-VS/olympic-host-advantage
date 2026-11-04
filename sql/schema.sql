-- Normalised schema. {raw} and {ref} are replaced with data folder paths by build.py.
-- Replaces the original coursework design of one table per Games with identical columns.

CREATE OR REPLACE TABLE nation AS
SELECT DISTINCT entity AS nation_id, entity_name AS nation_name, NULLIF(iso3, '') AS iso3, kind
FROM read_csv('{ref}/noc_map.csv', all_varchar = true);

CREATE OR REPLACE TABLE noc_map AS
SELECT noc, CAST(from_year AS INTEGER) AS from_year, CAST(to_year AS INTEGER) AS to_year,
       entity AS nation_id, note
FROM read_csv('{ref}/noc_map.csv', all_varchar = true);

CREATE OR REPLACE TABLE games AS
SELECT g.games_id, g.year, g.season, g.city, g.host_noc, m.nation_id AS host_nation_id,
       coalesce(starts_with(g.note, 'Future Games'), false) AS future,
       row_number() OVER (PARTITION BY g.season ORDER BY g.year) AS season_seq
FROM read_csv('{ref}/hosts.csv', all_varchar = false) AS g
LEFT JOIN noc_map AS m ON m.noc = g.host_noc AND g.year BETWEEN m.from_year AND m.to_year;

CREATE OR REPLACE TABLE medal_result AS
SELECT r.games_id, r.noc, m.nation_id, r.gold, r.silver, r.bronze,
       r.gold + r.silver + r.bronze AS total
FROM read_csv('{raw}/medal_tables/*.csv') AS r
JOIN games AS g USING (games_id)
LEFT JOIN noc_map AS m ON m.noc = r.noc AND g.year BETWEEN m.from_year AND m.to_year;

CREATE OR REPLACE TABLE participation AS
SELECT DISTINCT p.games_id, m.nation_id
FROM read_csv('{raw}/participants.csv') AS p
JOIN games AS g USING (games_id)
JOIN noc_map AS m ON m.noc = p.noc AND g.year BETWEEN m.from_year AND m.to_year
UNION
SELECT DISTINCT games_id, nation_id FROM medal_result;

CREATE OR REPLACE TABLE nation_year_economics AS
SELECT iso3, year, gdp_usd, population
FROM read_csv('{raw}/world_bank.csv')
WHERE iso3 IN (SELECT iso3 FROM nation WHERE iso3 IS NOT NULL);
