<?php
// assumes that $tw_id is set

// Get the associated TW data
// Prepare the SQL query
$query = "SELECT guild_id, guilds.name AS guild_name,";
$query .= " away_guild_id, away_guild_name, homeScore, awayScore,";
$query .= " tw_history.lastUpdated AS lastUpdated FROM tw_history";
$query .= " JOIN guilds ON guilds.id = guild_id";
$query .= " WHERE tw_history.id=".$tw_id;
//error_log("query = ".$query);
try {
    // Prepare the SQL query
    $stmt = $conn_guionbot->prepare($query);
    $stmt->execute();

    // Fetch all the results as an associative array
    $tw_list = $stmt->fetchAll(PDO::FETCH_ASSOC);
    $tw = array_values($tw_list)[0];

} catch (PDOException $e) {
    error_log("Error fetching TW data: " . $e->getMessage());
    echo "Error fetching TW data: " . $e->getMessage();
}
$guild_id = $tw['guild_id'];

// Get potential scores from fights
$query = "SELECT side, sum(score)";
$query.= " FROM";
$query.= " (";
$query.= "     SELECT tw_zones.zone_name, tw_zones.side, size, count(tw_squads.id), is_beaten, fights,";
$query.= "     CASE";
$query.= "         WHEN isnull(is_beaten) THEN size*(CASE WHEN tw_zones.zone_name IN ('F1', 'F2') THEN 22 ELSE 20 END)";
$query.= "         ELSE CASE";
$query.= "             WHEN is_beaten=1 THEN 0";
$query.= "             ELSE CASE";
$query.= "                 WHEN fights=0 THEN count(tw_squads.id)*(CASE WHEN tw_zones.zone_name IN ('F1', 'F2') THEN 22 ELSE 20 END)";
$query.= "                 WHEN fights=1 THEN count(tw_squads.id)*(CASE WHEN tw_zones.zone_name IN ('F1', 'F2') THEN 17 ELSE 15 END)";
$query.= "                 ELSE count(tw_squads.id)*(CASE WHEN tw_zones.zone_name IN ('F1', 'F2') THEN 12 ELSE 10 END)";
$query.= "             END";
$query.= "         END";
$query.= "     END AS `score`";
$query.= "     FROM tw_zones";
$query.= "     LEFT JOIN tw_squads ON (tw_squads.tw_id=tw_zones.tw_id AND tw_squads.zone_name=tw_zones.zone_name AND tw_squads.side=tw_zones.side)";
$query.= "     WHERE tw_zones.tw_id=".$tw_id;
$query.= "     GROUP BY tw_zones.zone_name, tw_zones.side, is_beaten, fights";
$query.= " ) T GROUP BY side ORDER BY side";
//error_log("query = ".$query);
try {
    // Prepare the SQL query
    $stmt = $conn_guionbot->prepare($query);
    $stmt->execute();

    // Fetch all the results as an associative array
    $fight_scores = $stmt->fetchAll(PDO::FETCH_ASSOC);

} catch (PDOException $e) {
    error_log("Error fetching TW data: " . $e->getMessage());
    echo "Error fetching TW data: " . $e->getMessage();
}

// Get potential score from clearing zones
$query = "SELECT side, sum(score)";
$query.= " FROM";
$query.= " (";
$query.= "     SELECT zone_name, side, size, victories,";
$query.= "     CASE";
$query.= "         WHEN size>victories THEN (CASE WHEN zone_name IN ('F1', 'T4', 'B4') THEN 1260 ELSE 810 END)";
$query.= "         ELSE 0";
$query.= "     END AS `score`";
$query.= "     FROM tw_zones";
$query.= "     WHERE tw_id=".$tw_id;
$query.= " ) T GROUP BY side;";
//error_log("query = ".$query);
try {
    // Prepare the SQL query
    $stmt = $conn_guionbot->prepare($query);
    $stmt->execute();

    // Fetch all the results as an associative array
    $clear_scores = $stmt->fetchAll(PDO::FETCH_ASSOC);

} catch (PDOException $e) {
    error_log("Error fetching TW data: " . $e->getMessage());
    echo "Error fetching TW data: " . $e->getMessage();
}
$tw['awayPotentialScore'] = $tw['awayScore'];
$tw['awayPotentialScore'] += $fight_scores[1]['sum(score)'];
$tw['awayPotentialScore'] += $clear_scores[1]['sum(score)'];
$tw['homePotentialScore'] = $tw['homeScore'];
$tw['homePotentialScore'] += $fight_scores[0]['sum(score)'];
$tw['homePotentialScore'] += $clear_scores[0]['sum(score)'];

?>
