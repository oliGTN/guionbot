<?php
// server should keep session data for AT LEAST 1 hour
ini_set('session.gc_maxlifetime', 3600*24*7);
// each client should remember their session id for EXACTLY 1 hour
session_set_cookie_params(3600*24*7);
// Start the session to check if the user is logged in
session_start();

require 'websitedb.php';  // Include the database connection for websitedb
require 'guionbotdb.php';  // Include the database connection for guionbotdb

// Check if the user is logged in
if (!isset($_SESSION['user_id'])) {
    error_log("no user_id, redirect to index.php");
    header("Location: index.php");
    exit();
}

// Check if the user is an admin
$isAdmin = isset($_SESSION['admin']) && $_SESSION['admin'];

// Handle guild association
if ($_SERVER['REQUEST_METHOD'] === 'POST' && isset($_POST['associate_guilds'])) {
    $user_id = $_POST['user_id'];
    $guild_ids = $_POST['guild_ids'];

    foreach ($guild_ids as $guild_id) {
        $check_stmt = $conn->prepare("SELECT * FROM user_guilds WHERE user_id = :user_id AND guild_id = :guild_id");
        $check_stmt->execute(['user_id' => $user_id, 'guild_id' => $guild_id]);
        if (!$check_stmt->fetch()) {
            $insert_stmt = $conn->prepare("INSERT INTO user_guilds (user_id, guild_id) VALUES (:user_id, :guild_id)");
            $insert_stmt->execute(['user_id' => $user_id, 'guild_id' => $guild_id]);
        }
    }
    echo "<script>alert('Guild(s) successfully associated with the user.');</script>";
}
if ($_SERVER['REQUEST_METHOD'] === 'POST' && isset($_POST['deassociate_guilds'])) {
    $user_id = $_POST['user_id'];
    $guild_ids = $_POST['guild_ids'];

    foreach ($guild_ids as $guild_id) {
        $query = "DELETE FROM user_guilds WHERE user_id = :user_id AND guild_id = :guild_id";
        //error_log($query.' '.$user_id.' '.$guild_id);
        $stmt = $conn->prepare($query);
        $stmt->execute(['user_id' => $user_id, 'guild_id' => $guild_id]);
    }
    echo "<script>alert('Guild(s) successfully de-associated with the user.');</script>";
}

// ---- get DB data after handling potential POST commands, so that the page is up to date ----------
if ($isAdmin) {
    try {
        // Prepare the SQL query to fetch the specific guild associations from the DB table
        $query = "SELECT users.user_id AS user_id, users.name AS name, GROUP_CONCAT(CONCAT(' ',guilds.name)) AS guild_names FROM users";
        $query .= " LEFT JOIN user_guilds ON users.user_id=user_guilds.user_id";
        $query .= " LEFT JOIN guionbotdb.guilds ON guionbotdb.guilds.id=guild_id";
        $query .= " GROUP BY user_id ORDER BY users.name";
        //error_log($query);
        $stmt = $conn->prepare($query);
        $stmt->execute();

        // Fetch all the results as an associative array
        $user_guilds = $stmt->fetchAll(PDO::FETCH_ASSOC);

    } catch (PDOException $e) {
        echo "Error fetching users: " . $e->getMessage();
    }
} 
    try {
        // Prepare the SQL query to fetch the user infos
        $query = "SELECT id, name FROM guilds";
        $query .= " WHERE id IN ('".implode("','", array_keys($_SESSION['user_guilds']))."')";
        $query .= " ORDER BY name;";
        //error_log($query);
        $stmt = $conn_guionbot->prepare($query);
        $stmt->execute();

        // Fetch all the results as an associative array
        $my_guilds = $stmt->fetchAll(PDO::FETCH_ASSOC);

    } catch (PDOException $e) {
        echo "Error fetching my_guilds: " . $e->getMessage();
    }
    try {
        // Prepare the SQL query to fetch the user infos
        $query = "SELECT id, name FROM guilds";
        $query .= " WHERE id IN ('".implode("','", $_SESSION['user_bonus_guilds'])."')";
        $query .= " ORDER BY name;";
        //error_log($query);
        $stmt = $conn_guionbot->prepare($query);
        $stmt->execute();

        // Fetch all the results as an associative array
        $my_bonus_guilds = $stmt->fetchAll(PDO::FETCH_ASSOC);

    } catch (PDOException $e) {
        echo "Error fetching my_bonus_guilds: " . $e->getMessage();
    }
    
try {
    // Prepare the SQL query to fetch all guilds from the DB table
    $stmt = $conn_guionbot->prepare("SELECT id, name FROM guilds ORDER BY name");
    $stmt->execute();

    // Fetch all the results as an associative array
    $guilds = $stmt->fetchAll(PDO::FETCH_ASSOC);

} catch (PDOException $e) {
    echo "Error fetching guilds: " . $e->getMessage();
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

        <h2>Welcome to Your Dashboard</h2>

        <?php if ($isAdmin): ?>
            <div class="card">
                <p style="color:green;display:inline">You are logged in as an administrator</p>
            </div>

            <div class="card">
                <!-- Table to display user names -->
                <h3>Admin panel</h3>
                <div class="card">
                    <table>
                        <tr>
                            <th>user</th>
                            <th>associated guilds</th>
                        </tr>
                        <?php
                        // Loop through each player and display in a table row
                        if (!empty($user_guilds)) {
                            foreach ($user_guilds as $user) {
                                if ($user['guild_names'] != '') {
                                    echo "<tr><td>" . $user['name'] . " (".$user['user_id'].")</td><td>" . htmlspecialchars($user['guild_names']) . "</td></tr>";
                                }
                            }
                        } else {
                            echo "<tr><td colspan='2'>No association found.</td></tr>";
                        }
                        ?>
                    </table>
                </div>

                <div class="card">
                    <form method="POST" action="">
                        <label for="user_id">Select User:</label><br>
                        <select name="user_id" id="user_id" required>
                            <?php foreach ($user_guilds as $user): ?>
                                <option value="<?php echo $user['user_id']; ?>"><?php echo htmlspecialchars($user['name']); ?></option>
                            <?php endforeach; ?>
                        </select><br>

                        <label for="guild_ids">Select Guild(s):</label><br>
                        <select name="guild_ids[]" id="guild_ids" multiple required>
                            <?php foreach ($guilds as $guild): ?>
                                <option value="<?php echo $guild['id']; ?>"><?php echo htmlspecialchars($guild['name']); ?></option>
                            <?php endforeach; ?>
                        </select><br>

                        <button type="submit" name="associate_guilds">Associate Guilds</button>
                        <button type="submit" name="deassociate_guilds">De-associate Guilds</button>
                    </form>
                </div>
            </div>
        
        <?php else: ?>
            <div class="card">
                <p style="color:green;display:inline">You are logged in as a user: <?php echo $_SESSION['user_name'] ?></p>
            </div>

        <?php endif; ?>
            <div class="card">
            <table>
                <tr>
                    <th>My guilds</th>
                </tr>
                <?php
                // Loop through each guild and display in a table row
                if (!empty($my_guilds)) {
                    foreach ($my_guilds as $user_guild) {
                        echo "<tr><td><a href='g.php?gid=".$user_guild['id']."'>" . htmlspecialchars($user_guild['name']) . "</a></td></tr>";
                    }
                } else {
                    echo "<tr><td colspan='2'>No guild found.</td></tr>";
                }
                ?>
            </table>
            </div>

            <?php if (!empty($my_bonus_guilds)): ?>
            <div class="card">
            <table>
                <tr>
                    <th>My bonus guilds</th>
                </tr>
                <?php
                // Loop through each guild and display in a table row
                    foreach ($my_bonus_guilds as $user_guild) {
                        echo "<tr><td><a href='g.php?gid=".$user_guild['id']."'>" . htmlspecialchars($user_guild['name']) . "</a></td></tr>";
                    }
                ?>
            </table>
            </div>
            <?php endif; ?> <!-- !empty($my_bonus_guilds) -->
    </div> <!-- container -->
    </div> <!-- site-content -->
    <div class="site-cache" id="site-cache" onclick="document.body.classList.toggle('with--sidebar')"></div>

</div>
</div>
</body>
</html>
