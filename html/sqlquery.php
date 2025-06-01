<?php
// server should keep session data for AT LEAST 1 hour
ini_set('session.gc_maxlifetime', 3600*24*7);
// each client should remember their session id for EXACTLY 1 hour
session_set_cookie_params(3600*24*7);
// Start the session to check if the user is logged in
session_start();

require 'guionbotdb.php';  // Include the database connection for guionbotdb

// Check if the user is logged in
if (!isset($_SESSION['user_id'])) {
    error_log("no user_id, redirect to index.php");
    header("Location: index.php");
    exit();
}

// Check if the user is allowed
$sql_select = isset($_SESSION['sql_select']) && $_SESSION['sql_select'];

if (! $sql_select) {
    error_log("Not allowed, redirect to dashboard.php");
    header("Location: dashboard.php");
    exit();
}


// Handle POST for SQL query
if ($_SERVER['REQUEST_METHOD'] === 'POST' && isset($_POST['sql_query'])) {
    $query = $_POST['sql_query'];

    //Force a limit
    $limited_query = 'SELECT * FROM ('.$query.') AS query LIMIT 0, 200';


    //execute the query
    try {
        $stmt = $conn_guionbot->prepare($limited_query);
        $stmt->execute();
        $sql_results = $stmt->fetchAll(PDO::FETCH_ASSOC);
    } catch (PDOException $e) {
        echo '<script> alert("Error executing query: ' . $e->getMessage().'");</script>';
    }
    //error_log(print_r($sql_results, true));
} else {
    $query = '';
}

?>


<!DOCTYPE html>
<html lang="en">
<head>
    <title>GuiOn bot for SWGOH</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="stylesheet" href="basic.css">
    <link rel="stylesheet" href="tables.css">
    <link rel="stylesheet" href="navbar.css">
    <link rel="stylesheet" href="main.1.008.css">
    <link rel="stylesheet" href="https://fonts.googleapis.com/icon?family=Material+Icons">
</head>
<body>
<div class="site-container">
<div class="site-pusher">

    <!-- Navigation Bar -->
    <?php include 'navbar.php' ; ?>

    <!-- Dashboard Content -->
    <div class="site-content">
    <div class="container">

        <h2>guionbot DB consult</h2>

            <div class="card">
                    <form method="POST" action="sqlquery.php">
                    <input type="text" placeholder="SQL query" value="<?php echo $query; ?>" id="sql_query" name="sql_query" width="100%">
                    </form>
            </div>
        
            <div class="card">
                <b>Information</b>
                <ul>
                <li>- All queries are limited to 200 resuts by default</li>
                <li>- look for these tables: roster, players</li>
                <li>- <i>defId</i> column in <i>roster</i> table is the same as <i>base_id</i> <a href="https://swgoh.gg/api/characters/">here</a> (characters) or <a href="https://swgoh.gg/api/ships/">here</a> (ships).</li>
                </ul>
    
            </div>


            <div class="card">
            <table>
                <?php
                if (!empty($sql_results)) {
                    echo '<tr>';
                        foreach (array_keys($sql_results[0]) as $sql_column) {
                            echo '<th>'.$sql_column.'</th>';
                        }
                    echo '</tr>';
                    // Loop through each guild and display in a table row
                    foreach ($sql_results as $sql_result) {
                        echo '<tr>';
                        foreach (array_keys($sql_result) as $sql_column) {
                            echo '<td>'.$sql_result[$sql_column].'</td>';
                        }
                        echo '</tr>';
                    }

                } else {
                    echo "<tr><td>No results</td></tr>";
                }
                ?>
            </table>
            </div>

    </div> <!-- container -->
    </div> <!-- site-content -->
    <div class="site-cache" id="site-cache" onclick="document.body.classList.toggle('with--sidebar')"></div>

</div>
</div>
</body>
</html>
