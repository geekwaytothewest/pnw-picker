-- Worst individual offenders across all hoarding groups.
-- Counts how many overlapping checkout pairs each attendee appears in as a shared player.
WITH overlapping_pairs AS (
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
      AND DATE(co1."checkOut" AT TIME ZONE 'America/Chicago') = DATE(co1."checkIn" AT TIME ZONE 'America/Chicago')
      AND DATE(co2."checkOut" AT TIME ZONE 'America/Chicago') = DATE(co2."checkIn" AT TIME ZONE 'America/Chicago')
),
shared_players AS (
    SELECT
        op.checkout1_id,
        op.checkout2_id,
        op.overlap_minutes,
        p1."attendeeId"
    FROM overlapping_pairs op
    JOIN "Player" p1 ON p1."checkOutId" = op.checkout1_id
                    AND p1."wantToWin" = true
    JOIN "Player" p2 ON p2."checkOutId" = op.checkout2_id
                    AND p2."attendeeId" = p1."attendeeId"
),
qualifying_pairs AS (
    -- Only include pairs where at least 2 players are shared (same threshold as Hoarding Groups)
    SELECT checkout1_id, checkout2_id, overlap_minutes, "attendeeId"
    FROM shared_players
    WHERE (checkout1_id, checkout2_id) IN (
        SELECT checkout1_id, checkout2_id
        FROM shared_players
        GROUP BY checkout1_id, checkout2_id
        HAVING COUNT(*) >= 2
    )
)
SELECT
    a."badgeName"                              AS badge_name,
    a."badgeNumber"                            AS badge_number,
    a."legalName"                              AS legal_name,
    qp."attendeeId",
    COUNT(*)                                   AS hoarding_pair_appearances,
    ROUND(SUM(qp.overlap_minutes)::numeric, 1) AS total_overlap_minutes
FROM qualifying_pairs qp
JOIN "Attendee" a ON qp."attendeeId" = a.id
GROUP BY a."badgeName", a."badgeNumber", a."legalName", qp."attendeeId"
ORDER BY total_overlap_minutes DESC;
