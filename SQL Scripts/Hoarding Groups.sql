-- Find groups of players who collectively checked out multiple games simultaneously.
-- Groups are identified by having the exact same set of players on 2+ overlapping checkouts.
WITH checkout_player_groups AS (
    -- Build a sorted player-set key and readable name list for each checkout
    SELECT
        p."checkOutId",
        STRING_AGG(p."attendeeId"::text, ',' ORDER BY p."attendeeId") AS group_key,
        STRING_AGG(a."badgeName",       ', ' ORDER BY a."badgeName")  AS player_names
    FROM "Player" p
    JOIN "CheckOut" co  ON p."checkOutId"  = co.id
    JOIN "Copy"    copy ON co."copyId"     = copy.id
    JOIN "Attendee" a   ON p."attendeeId"  = a.id
    WHERE copy."collectionId" = :collection_id
      AND co."checkIn" IS NOT NULL
    GROUP BY p."checkOutId"
),
hoarding_pairs AS (
    -- Find pairs of checkouts with the same player group that overlap in time
    SELECT
        cpg1.group_key,
        cpg1.player_names,
        EXTRACT(EPOCH FROM (
            LEAST(co1."checkIn",  co2."checkIn") -
            GREATEST(co1."checkOut", co2."checkOut")
        )) / 60 AS overlap_minutes
    FROM checkout_player_groups cpg1
    JOIN checkout_player_groups cpg2
        ON  cpg1.group_key     = cpg2.group_key
        AND cpg1."checkOutId"  < cpg2."checkOutId"
    JOIN "CheckOut" co1 ON cpg1."checkOutId" = co1.id
    JOIN "CheckOut" co2 ON cpg2."checkOutId" = co2.id
    WHERE co1."checkOut" < co2."checkIn"
      AND co1."checkIn"  > co2."checkOut"
)
SELECT
    player_names                            AS hoarding_group,
    group_key                               AS attendee_ids,
    COUNT(*)                                AS simultaneous_checkout_pairs,
    ROUND(SUM(overlap_minutes)::numeric, 1) AS total_overlap_minutes
FROM hoarding_pairs
GROUP BY group_key, player_names
ORDER BY total_overlap_minutes DESC;
