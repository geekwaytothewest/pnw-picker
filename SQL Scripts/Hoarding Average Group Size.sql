-- Average number of games being hoarded simultaneously per checkout.
-- For each checkout in a qualifying hoarding pair, counts how many other
-- qualifying checkouts overlap with it (+1 for itself = total games out at once).
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
qualifying_pairs AS (
    -- Only pairs with 2+ shared players
    SELECT op.checkout1_id, op.checkout2_id
    FROM overlapping_pairs op
    JOIN "Player" p1 ON p1."checkOutId" = op.checkout1_id
    JOIN "Player" p2 ON p2."checkOutId" = op.checkout2_id
                    AND p2."attendeeId" = p1."attendeeId"
    GROUP BY op.checkout1_id, op.checkout2_id
    HAVING COUNT(*) >= 2
),
checkout_concurrent_counts AS (
    -- Count qualifying overlaps for each checkout from both sides of each pair
    SELECT checkout1_id AS checkout_id, COUNT(*) AS concurrent_others
    FROM qualifying_pairs
    GROUP BY checkout1_id

    UNION ALL

    SELECT checkout2_id AS checkout_id, COUNT(*) AS concurrent_others
    FROM qualifying_pairs
    GROUP BY checkout2_id
),
per_checkout AS (
    -- Take the max in case a checkout appears on both sides; +1 includes itself
    SELECT checkout_id, MAX(concurrent_others) + 1 AS games_out_simultaneously
    FROM checkout_concurrent_counts
    GROUP BY checkout_id
)
SELECT
    ROUND(AVG(games_out_simultaneously)::numeric, 1) AS avg_games_hoarded_simultaneously,
    MIN(games_out_simultaneously)                    AS min_simultaneous,
    MAX(games_out_simultaneously)                    AS max_simultaneous,
    COUNT(*)                                         AS qualifying_checkouts
FROM per_checkout;
