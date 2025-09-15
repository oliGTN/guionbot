<?php
require 'guionbotdb.php';  // Include the database connection for guionbotdb

function get_round_from_get($tb_id) {
    global $conn_guionbot;

    if (!isset($_GET['round'])) {
        // Get the max round
        // Prepare the SQL query
        $query = "SELECT current_round";
        $query .= " FROM tb_history";
        $query .= " WHERE tb_history.id=".$tb_id;
        error_log("query = ".$query);
        try {
            // Prepare the SQL query
            $stmt = $conn_guionbot->prepare($query);
            $stmt->execute();

            // Fetch all the results as an associative array
            $rounds = $stmt->fetchAll(PDO::FETCH_ASSOC);
            if (count($rounds)==0) {
                error_log("Unknown TB id: redirect to index.php");
                header("Location: index.php");
                exit();
            }
            $round = $rounds[0]['current_round'];

        } catch (PDOException $e) {
            error_log("Error fetching guild data: " . $e->getMessage());
            echo "Error fetching guild data: " . $e->getMessage();
            $round = 1;
        }
    } else {
        $round = $_GET['round'];
    }
    return $round;
}

function get_tb_round_score($tb_id, $round) {
    global $conn_guionbot;

    // Prepare the SQL query
    $query = "SELECT sum(score_strikes) AS strikes, sum(score_platoons) AS platoons,";
    $query .= " sum(score_deployed) AS deployed,";
    $query .= " availableShipDeploy, availableCharDeploy, availableMixDeploy,";
    $query .= " remainingShipPlayers, remainingCharPlayers, remainingMixPlayers,";
    $query .= " deploymentType, totalPlayers";
    $query .= " FROM tb_player_score";
    $query .= " JOIN tb_phases ON tb_phases.tb_id = tb_player_score.tb_id";
    $query .= " AND tb_phases.round = tb_player_score.round";
    $query .= " WHERE tb_player_score.tb_id=".$tb_id." AND tb_player_score.round=".$round;
    //error_log("query = ".$query);
    try {
        // Prepare the SQL query to fetch the zone information
        $stmt = $conn_guionbot->prepare($query);
        $stmt->execute();

        // Fetch all the results as an associative array
        $round_score = $stmt->fetchAll(PDO::FETCH_ASSOC)[0];
    //print_r($round_score);

    } catch (PDOException $e) {
        error_log("Error fetching round data: " . $e->getMessage());
        echo "Error fetching round data: " . $e->getMessage();
    }

    return $round_score;
}

function get_tb_players($tb_id, $round, $sort_column, $sort_order) {
    global $conn_guionbot;

    if ($sort_column == 'deployment') {
        $sort_column_sql = 'deployed_gp/gp';
    } else {
        $sort_column_sql = $sort_column;
    }
    // Prepare the SQL query
    $query = "SELECT name, allyCode, deployed_gp,";
    $query .= " tb_player_score.gp AS gp, tb_player_score.ship_gp AS ship_gp, tb_player_score.char_gp AS char_gp,";
    $query .= " score_strikes+score_deployed as score, strikes, waves";
    $query .= " FROM tb_player_score";
    $query .= " JOIN players ON players.playerId=tb_player_score.player_id";
    $query .= " WHERE tb_id=".$tb_id." AND round=".$round;
    $query .= " ORDER BY $sort_column_sql $sort_order";
    //error_log("query = ".$query);
    try {
        // Prepare the SQL query to fetch the zone information
        $stmt = $conn_guionbot->prepare($query);
        $stmt->execute();

        // Fetch all the results as an associative array
        $tb_players = $stmt->fetchAll(PDO::FETCH_ASSOC);

    } catch (PDOException $e) {
        error_log("Error fetching player data: " . $e->getMessage());
        echo "Error fetching player data: " . $e->getMessage();
    }

    return $tb_players;
}

function get_tb_from_id($tb_id) {
    global $conn_guionbot;

    $query = "SELECT guild_id, guilds.name AS guild_name, tb_name,";
    $query .= " start_date, tb_history.lastUpdated,";
    $query .= " current_round, max(round) AS max_round, tb_zones.tb_id AS tb_id";
    $query .= " FROM tb_history";
    $query .= " JOIN tb_zones ON tb_zones.tb_id=tb_history.id";
    $query .= " JOIN guilds ON guilds.id=tb_history.guild_id";
    $query .= " WHERE tb_zones.tb_id=".$tb_id;
    //error_log("query = ".$query);
    try {
        // Prepare the SQL query
        $stmt = $conn_guionbot->prepare($query);
        $stmt->execute();

        // Fetch all the results as an associative array
        $tb_list = $stmt->fetchAll(PDO::FETCH_ASSOC);
        $tb = array_values($tb_list)[0];

    } catch (PDOException $e) {
        error_log("Error fetching guild data: " . $e->getMessage());
        echo "Error fetching guild data: " . $e->getMessage();
    }

    return $tb;
}

function get_tb_round_zones($tb_id, $round) {
    global $conn_guionbot;

    $query = "SELECT zone_name, zone_id, zone_phase, score_step1, score_step2, score_step3,";
    $query .= " score, estimated_platoons, estimated_strikes, estimated_deployments,";
    $query .= " recon1_filled, recon2_filled, recon3_filled,";
    $query .= " recon4_filled, recon5_filled, recon6_filled, recon_cmdMsg";
    $query .= " FROM tb_zones";
    $query .= " WHERE tb_id=".$tb_id." AND round=".$round;
    $query .= " ORDER BY CASE WHEN INSTR(zone_name, 'DS')>0 THEN 0 WHEN INSTR(zone_name, 'MS')>0 THEN 1 ELSE 2 END + CASE WHEN is_bonus THEN 0.5 ELSE 0 END";
    //error_log("query = ".$query);
    try {
        // Prepare the SQL query to fetch the zone information
        $stmt = $conn_guionbot->prepare($query);
        $stmt->execute();

        // Fetch all the results as an associative array
        $zones = $stmt->fetchAll(PDO::FETCH_ASSOC);

    } catch (PDOException $e) {
        error_log("Error fetching zone data: " . $e->getMessage());
        echo "Error fetching zone data: " . $e->getMessage();
    }

    return $zones;
}

function get_tb_round_stars($tb_id, $round) {
    global $conn_guionbot;

    $query = "SELECT sum(case";
    $query .= " WHEN score>=score_step3 then CASE WHEN SUBSTRING(tb_zones.zone_name, -1, 1)='b' THEN 1 ELSE 3 END";
    $query .= " WHEN score>=score_step2 then CASE WHEN SUBSTRING(tb_zones.zone_name, -1, 1)='b' THEN 0 ELSE 2 END";
    $query .= " WHEN score>=score_step1 then CASE WHEN SUBSTRING(tb_zones.zone_name, -1, 1)='b' THEN 0 ELSE 1 END";
    $query .= " ELSE 0 END) AS stars";
    $query .= " FROM tb_zones";

    $query .= " JOIN (";
    $query .= "   SELECT tb_zones.tb_id AS tb_id, zone_name, max(round) AS max_round";
    $query .= "   FROM tb_zones";
    $query .= "   JOIN tb_history ON tb_zones.tb_id=tb_history.id";
    $query .= "   WHERE tb_zones.tb_id=".$tb_id;
    $query .= "   GROUP BY tb_id, zone_name";
    $query .= " ) T ON T.tb_id=tb_zones.tb_id AND T.zone_name = tb_zones.zone_name AND T.max_round = tb_zones.round";
    $query .= " WHERE tb_zones.tb_id=".$tb_id." AND round<=".$round;
    //error_log("query = ".$query);
    try {
        // Prepare the SQL query to fetch the zone information
        $stmt = $conn_guionbot->prepare($query);
        $stmt->execute();

        // Fetch all the results as an associative array
        $round_stars = $stmt->fetchAll(PDO::FETCH_ASSOC)[0]['stars'];

    } catch (PDOException $e) {
        error_log("Error fetching TB data: " . $e->getMessage());
        echo "Error fetching TB data: " . $e->getMessage();
    }

    return $round_stars;
}

?>

