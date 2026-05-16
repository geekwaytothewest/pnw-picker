select g."name", AVG(p.rating) as "ratingAverage", COUNT(p.rating > 0) as "ratingsCount", COUNT(p."attendeeId") as "playerCount", COUNT(DISTINCT(co.id)) as "playCount" from "CheckOut" co
left outer join "Copy" c on c.id = co."copyId"
left outer join "Game" g on g.id = c."gameId"
left outer join "Player" p on p."checkOutId" = co.id
where c."collectionId" = 14
group by g."name", c."gameId"
order by "ratingAverage" desc