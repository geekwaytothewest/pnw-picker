-- Diagnostic: show all checkouts for a specific attendee regardless of collection.
-- If this returns results but the main query does not, the collection filter is the issue.
SELECT
    p."checkOutId",
    co."checkOut"         AS start,
    co."checkIn"          AS end,
    co."copyId",
    copy."collectionId",
    ROUND((EXTRACT(EPOCH FROM (co."checkIn" - co."checkOut")) / 60)::numeric, 1) AS duration_minutes
FROM "Player" p
JOIN "CheckOut" co ON p."checkOutId" = co.id
LEFT JOIN "Copy" copy ON co."copyId" = copy.id
WHERE p."attendeeId" = 9905
ORDER BY co."checkOut";
