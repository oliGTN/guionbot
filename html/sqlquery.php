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
    $query = trim($_POST['sql_query']);

    // prevent ending ;
    if (substr($query, -1)==';') {
        $query = substr($query, 0, strlen($query)-1);
    }

    // //Force a limit
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

<script>
function download(file, text) {

    //creating an invisible element

    let element = document.createElement('a');
    element.setAttribute('href',
        'data:text/plain;charset=utf-8, '
        + encodeURIComponent(text));
    element.setAttribute('download', file);
    document.body.appendChild(element);
    element.click();

    document.body.removeChild(element);
}

function fct_download() {
    csv_content = "";

    sql_table = document.getElementById("sql-results");
    sql_rows = sql_table.getElementsByClassName("sql-row");
    for (i = 0; i < sql_rows.length; i++) {
        sql_row = sql_rows[i];
        sql_columns = sql_row.getElementsByClassName("sql-column");
        for (j = 0; j < sql_columns.length; j++) {
            sql_column = sql_columns[j];
            csv_content = csv_content + sql_column.innerHTML + ";";
        }
        csv_content = csv_content + "\n"
    }
    //console.log(csv_content);
    download("sqlresults.csv", csv_content);
}
</script>

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
                <ul style="list-style-type:disc;">
                    <li>- All queries are limited to 200 resuts by default</li>
                    <li>- look for these tables: roster, players</li>
                    <li>- <i>defId</i> column in <i>roster</i> table is the same as <i>base_id</i> <a href="https://swgoh.gg/api/characters/">here</a> (characters) or <a href="https://swgoh.gg/api/ships/">here</a> (ships).</li>
                    <li>- <i>relic_currentTier</i> column is 2 higher than actual relic of the character (relic_currentTer=5 > character is R3).</li>
                    <li>- statistics:
                        <ul style="list-style-type:disc;">
                            <li>&nbsp;- stat1=Health</li>
                            <li>&nbsp;- stat5=Speed</li>
                            <li>&nbsp;- stat6=PhysicalDamages</li>
                            <li>&nbsp;- stat7=SpecialDamages</li>
                            <li>&nbsp;- stat8=Armor</li>
                            <li>&nbsp;- stat14=CritChances</li>
                            <li>&nbsp;- stat15=SpecialCritDamages</li>
                            <li>&nbsp;- stat16=PhysicalCritDamages</li>
                            <li>&nbsp;- stat17=Potency</li>
                            <li>&nbsp;- stat18=Tenacity</li>
                            <li>&nbsp;- stat28=Protection</li>
                        </ul>
                    </li>
                </ul>
            </div>

            <button type="button" id="btn_download" onclick="fct_download();">download</button>

            <div class="card">
            <table id="sql-results">
                <?php
                if (!empty($sql_results)) {
                    echo '<tr class="sql-row">';
                        foreach (array_keys($sql_results[0]) as $sql_column) {
                            echo '<th class="sql-column">'.$sql_column.'</th>';
                        }
                    echo '</tr>';
                    // Loop through each guild and display in a table row
                    foreach ($sql_results as $sql_result) {
                        echo '<tr class="sql-row">';
                        foreach (array_keys($sql_result) as $sql_column) {
                            echo '<td class="sql-column">'.$sql_result[$sql_column].'</td>';
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
