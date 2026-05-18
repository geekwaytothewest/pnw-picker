-- Export unique games from a collection for use with hoarding-bgg-compare.js.
-- Run this query and export the results as a CSV file.
SELECT DISTINCT
    g.id   AS "gameId",
    g.name AS "name"
FROM "Game" g
JOIN "Copy" copy ON copy."gameId" = g.id
WHERE copy."collectionId" = :collection_id
ORDER BY g.name;
