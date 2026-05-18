-- Compare hoarding incidents against BGG expected play times.
-- For each group's hoarding session, sums min/max playtimes from BGG and compares
-- to the actual window (first checkOut to last checkIn).
-- A 4-hour gap between checkouts splits a group's activity into separate incidents.
WITH overlapping_pairs AS (
    SELECT
        co1.id AS checkout1_id,
        co2.id AS checkout2_id
    FROM "CheckOut" co1
    JOIN "Copy" copy1 ON co1."copyId" = copy1.id
    JOIN "CheckOut" co2 ON co2.id > co1.id
    JOIN "Copy" copy2 ON co2."copyId" = copy2.id
    WHERE copy1."collectionId" = :collection_id
      AND copy2."collectionId" = :collection_id
      AND co1."checkIn" IS NOT NULL
      AND co2."checkIn" IS NOT NULL
      AND co1."checkOut" < co2."checkIn"
      AND co1."checkIn"  > co2."checkOut"
),
shared_players AS (
    SELECT op.checkout1_id, op.checkout2_id
    FROM overlapping_pairs op
    JOIN "Player" p1 ON p1."checkOutId" = op.checkout1_id
    JOIN "Player" p2 ON p2."checkOutId" = op.checkout2_id
                    AND p2."attendeeId" = p1."attendeeId"
    GROUP BY op.checkout1_id, op.checkout2_id
    HAVING COUNT(*) >= 2
),
pair_groups AS (
    SELECT
        sp.checkout1_id,
        sp.checkout2_id,
        STRING_AGG(p1."attendeeId"::text, ',' ORDER BY p1."attendeeId") AS group_key,
        STRING_AGG(a."badgeName",         ', ' ORDER BY a."badgeName")  AS player_names
    FROM shared_players sp
    JOIN "Player" p1 ON p1."checkOutId" = sp.checkout1_id
    JOIN "Player" p2 ON p2."checkOutId" = sp.checkout2_id
                    AND p2."attendeeId" = p1."attendeeId"
    JOIN "Attendee" a ON p1."attendeeId" = a.id
    GROUP BY sp.checkout1_id, sp.checkout2_id
),
group_checkouts AS (
    SELECT group_key, player_names, checkout1_id AS checkout_id FROM pair_groups
    UNION
    SELECT group_key, player_names, checkout2_id AS checkout_id FROM pair_groups
),
checkout_details AS (
    SELECT
        gc.group_key,
        gc.player_names,
        gc.checkout_id,
        co."checkOut",
        co."checkIn",
        g.name       AS game_name,
        g."minTime",
        g."maxTime"
    FROM group_checkouts gc
    JOIN "CheckOut" co   ON gc.checkout_id  = co.id
    JOIN "Copy"    copy  ON co."copyId"     = copy.id
    JOIN "Game"    g     ON copy."gameId"   = g.id
),
incident_labels AS (
    -- Increment incident counter when gap from previous checkout in same group > 4 hours
    SELECT *,
        SUM(
            CASE WHEN "checkOut" - LAG("checkOut", 1, "checkOut") OVER (
                PARTITION BY group_key ORDER BY "checkOut"
            ) > INTERVAL '4 hours' THEN 1 ELSE 0 END
        ) OVER (
            PARTITION BY group_key ORDER BY "checkOut"
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) AS incident_num
    FROM checkout_details
)
SELECT
    player_names                                                        AS hoarding_group,
    incident_num,
    MIN("checkOut")                                                     AS incident_start,
    MAX("checkIn")                                                      AS incident_end,
    ROUND((EXTRACT(EPOCH FROM (MAX("checkIn") - MIN("checkOut"))) / 60)::numeric, 0)
                                                                        AS window_minutes,
    COUNT(DISTINCT checkout_id)                                         AS games_checked_out,
    STRING_AGG(DISTINCT game_name, ', ')                               AS games,
    COALESCE(SUM("minTime"), 0)                                        AS bgg_sum_min_playtime,
    COALESCE(SUM("maxTime"), 0)                                        AS bgg_sum_max_playtime,
    CASE
        WHEN COALESCE(SUM("minTime"), 0) >
             EXTRACT(EPOCH FROM (MAX("checkIn") - MIN("checkOut"))) / 60
        THEN 'impossible — not enough time even at minimum playtimes'
        WHEN COALESCE(SUM("maxTime"), 0) >
             EXTRACT(EPOCH FROM (MAX("checkIn") - MIN("checkOut"))) / 60
        THEN 'unlikely — only fits if every game ran short'
        ELSE 'possible — enough time to play all sequentially'
    END                                                                 AS verdict
FROM incident_labels
GROUP BY group_key, player_names, incident_num
ORDER BY window_minutes DESC;
