-- Find attendees recorded as a player on multiple simultaneous checkouts.
-- Returns one row per overlapping pair; review actual timestamps to assess severity.
SELECT
    a."badgeName",
    a."legalName",
    p1."attendeeId",
    COUNT(*)                                              AS overlapping_pairs,
    ROUND(SUM(EXTRACT(EPOCH FROM (
        LEAST(co1."checkIn", co2."checkIn") -
        GREATEST(co1."checkOut", co2."checkOut")
    )) / 60)::numeric, 1)                                AS total_overlap_minutes
FROM "Player" p1
JOIN "Player" p2 ON p1."attendeeId" = p2."attendeeId"
    AND p1."checkOutId" < p2."checkOutId"
JOIN "CheckOut" co1 ON p1."checkOutId" = co1.id
JOIN "CheckOut" co2 ON p2."checkOutId" = co2.id
JOIN "Copy" copy1 ON co1."copyId" = copy1.id
JOIN "Copy" copy2 ON co2."copyId" = copy2.id
JOIN "Attendee" a ON p1."attendeeId" = a.id
WHERE copy1."collectionId" = :collection_id
  AND copy2."collectionId" = :collection_id
  AND co1."checkIn" IS NOT NULL
  AND co2."checkIn" IS NOT NULL
  AND co1."checkOut" < co2."checkIn"
  AND co1."checkIn" > co2."checkOut"
GROUP BY a."badgeName", a."legalName", p1."attendeeId"
ORDER BY total_overlap_minutes DESC;
