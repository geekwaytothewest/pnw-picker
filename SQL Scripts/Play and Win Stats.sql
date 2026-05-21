--Summary of all plays for a collection id
select g."name", AVG(p.rating) as "ratingAverage", COUNT(p.rating > 0) as "ratingsCount", COUNT(p."attendeeId") as "playerCount", COUNT(DISTINCT(co.id)) as "playCount" from "CheckOut" co
left outer join "Copy" c on c.id = co."copyId"
left outer join "Game" g on g.id = c."gameId"
left outer join "Player" p on p."checkOutId" = co.id
where c."collectionId" = 14
group by g."name", c."gameId"
order by "ratingAverage" desc;

--Total plays for a convention
select  from "CheckOut" co
join "Attendee" a on a.id = co."attendeeId"
where a."conventionId" = 273

--Total players for a convention
select  from "CheckOut" co
join "Attendee" a on a.id = co."attendeeId"
join "Player" p on p."checkOutId" = co.id
where a."conventionId" = 273

--Total checkout time for a convention
select select EXTRACT(EPOCH FROM SUM(co."checkIn" - co."checkOut")) / 3600 as "totalHours" from "CheckOut" co
join "Attendee" a on a.id = co."attendeeId"
where a."conventionId" = 273
and co."checkIn" is not null

--Total checkout time for a convention with players
select EXTRACT(EPOCH FROM SUM(co."checkIn" - co."checkOut")) / 3600 as "totalHours" from "CheckOut" co
join "Attendee" a on a.id = co."attendeeId"
join "Player" p on p."checkOutId" = co.id
where a."conventionId" = 273
and co."checkIn" is not null