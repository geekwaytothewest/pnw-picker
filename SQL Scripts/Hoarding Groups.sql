-- Find groups of players who collectively checked out multiple games simultaneously.
-- Groups are identified by the INTERSECTION of players across overlapping checkout pairs,
-- so partial player list changes between checkouts are handled.
WITH overlapping_pairs AS (
    -- Find pairs of checkouts from the collection that overlap in time
    SELECT
        co1.id AS checkout1_id,
        co2.id AS checkout2_id,
        EXTRACT(EPOCH FROM (
            LEAST(co1."checkIn",  co2."checkIn") -
            GREATEST(co1."checkOut", co2."checkOut")
        )) / 60 AS overlap_minutes
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
    -- For each overlapping pair, find players who appear on BOTH checkouts
    SELECT
        op.checkout1_id,
        op.checkout2_id,
        op.overlap_minutes,
        p1."attendeeId",
        a."badgeName"
    FROM overlapping_pairs op
    JOIN "Player" p1 ON p1."checkOutId" = op.checkout1_id
    JOIN "Player" p2 ON p2."checkOutId" = op.checkout2_id
                    AND p2."attendeeId" = p1."attendeeId"
    JOIN "Attendee" a ON p1."attendeeId" = a.id
),
pair_groups AS (
    -- Aggregate shared players per pair into a group key
    -- Require at least 2 shared players to filter out coincidental single-player overlaps
    SELECT
        checkout1_id,
        checkout2_id,
        overlap_minutes,
        STRING_AGG(sp."attendeeId"::text, ',' ORDER BY sp."attendeeId") AS group_key,
        STRING_AGG(sp."badgeName",        ', ' ORDER BY sp."badgeName") AS player_names
    FROM shared_players sp
    GROUP BY checkout1_id, checkout2_id, overlap_minutes
    HAVING COUNT(*) >= 2
)
SELECT
    player_names                              AS hoarding_group,
    group_key                                 AS attendee_ids,
    COUNT(*)                                  AS simultaneous_checkout_pairs,
    ROUND(SUM(overlap_minutes)::numeric, 1)   AS total_overlap_minutes
FROM pair_groups
GROUP BY group_key, player_names
ORDER BY total_overlap_minutes DESC;
