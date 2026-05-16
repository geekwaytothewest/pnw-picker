select pa."badgeNumber", pa."badgeName" as "Badge Name", Count(pa."id")
from "CheckOut" co
left outer join "Copy" c on c.id = co."copyId"
left outer join "Attendee" coa on co."attendeeId" = coa.id 
left outer join "Player" p on co.id = p."checkOutId" 
left outer join "Attendee" pa on pa.id = p."attendeeId" 
left outer join "Game" g on g.id = c."gameId"
where c."collectionId" = 15
group by pa."badgeNumber", pa."badgeName"
order by Count(p."id") desc