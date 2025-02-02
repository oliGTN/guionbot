<?php
session_start();  // Start the session to check if the user is logged in
require 'guionbotdb.php';  // Include the database connection for guionbotdb

// Check if the user is logged in and if the user is an admin
$isAdmin = isset($_SESSION['admin']) && $_SESSION['admin'];

// --------------- PAGINATION -----------
// Number of results per page
$limit = 25;
// Get the current page number from the URL, default is 1
$page = isset($_GET['page']) && is_numeric($_GET['page']) ? (int) $_GET['page'] : 1;
// Calculate the offset for the SQL query
$offset = ($page - 1) * $limit;
// Initialize search term
$search_term = '';
// Check if a search term has been submitted
if (isset($_POST['search'])) {
    $search_term = $_POST['search'];
    $page = 1;  // Reset to first page on new search
}
// Count total number of guilds for pagination
$count_query = "SELECT COUNT(*) FROM guilds";
if ($search_term) {
    $count_query .= " WHERE name LIKE :search_term";
}
$count_stmt = $conn_guionbot->prepare($count_query);
if ($search_term) {
    $count_stmt->bindValue(':search_term', '%' . $search_term . '%');
}
$count_stmt->execute();
$total_guilds = $count_stmt->fetchColumn();
// Calculate the total number of pages
$total_pages = ceil($total_guilds / $limit);

// --------------- SORTING BY COLUMN -----------
// Get sort parameters from URL or set default
$valid_columns = ['bot', 'name', 'players', 'gp', 'lastUpdated'];
$sort_column = isset($_GET['sort']) && in_array($_GET['sort'], $valid_columns) ? $_GET['sort'] : 'name';
$sort_order = isset($_GET['order']) && strtolower($_GET['order']) === 'desc' ? 'DESC' : 'ASC';

// Toggle sort order for next click
$next_order = $sort_order === 'ASC' ? 'desc' : 'asc';

//-------------- PREPARE THE QUERY for guilds
// Prepare the SQL query to get guilds with pagination
$query = "SELECT name, id, players, gp, lastUpdated, NOT isnull(bot_allyCode) AS bot FROM guilds LEFT JOIN guild_bot_infos ON (guild_bot_infos.guild_id=guilds.id)";
if ($search_term) {
    $query .= " WHERE name LIKE :search_term";
}
$query .= " ORDER BY $sort_column $sort_order LIMIT :limit OFFSET :offset";

try {
    // Prepare the SQL query to fetch the guild names and lastUpdated columns from the guilds table
    $stmt = $conn_guionbot->prepare($query);
    if ($search_term) {
        $stmt->bindValue(':search_term', '%' . $search_term . '%');
    }
    $stmt->bindValue(':limit', $limit, PDO::PARAM_INT);
    $stmt->bindValue(':offset', $offset, PDO::PARAM_INT);
    $stmt->execute();

    // Fetch all the results as an associative array
    $guilds = $stmt->fetchAll(PDO::FETCH_ASSOC);

} catch (PDOException $e) {
    echo "Error fetching data: " . $e->getMessage();
}
?>

<!DOCTYPE html>
<html>
<head>
    <title>Home</title>
    <link rel="stylesheet" href="basic.css">
    <link rel="stylesheet" href="navbar.css">
    <link rel="stylesheet" href="tables.css">
</head>
<body>

    <!-- Navigation Bar -->
    <?php include 'navbar.php' ; ?>
    
    <h2>Guilds</h2>
    
    <!-- Search Form -->
    <form method="POST" action="index.php">
        <label for="search">Search Guilds:</label>
        <input type="text" name="search" value="<?php echo htmlspecialchars($search_term); ?>" placeholder="Enter guild name" />
        <button type="submit">Search</button>
    </form>
    
    <h3>Guild List</h3>

    <!-- Table to display guild names and lastUpdated, with clickable sortable headers -->
    <table>
        <thead>
            <tr>
                <?php $current_sort = isset($_GET['sort']) ? $_GET['sort'] : 'name'; ?>
                <th class="<?php echo ($current_sort === 'bot') ? 'active-sort' : ''; ?>"><a href="index.php?sort=bot&order=<?php echo $next_order; ?>&page=1">Bot</a></th>
                <th class="<?php echo ($current_sort === 'name') ? 'active-sort' : ''; ?>"><a href="index.php?sort=name&order=<?php echo $next_order; ?>&page=1">Name</a></th>
                <th class="<?php echo ($current_sort === 'players') ? 'active-sort' : ''; ?>"><a href="index.php?sort=players&order=<?php echo $next_order; ?>&page=1">Players</a></th>
                <th class="<?php echo ($current_sort === 'gp') ? 'active-sort' : ''; ?>"><a href="index.php?sort=gp&order=<?php echo $next_order; ?>&page=1">GP</a></th>
                <th class="<?php echo ($current_sort === 'lastUpdated') ? 'active-sort' : ''; ?>"><a href="index.php?sort=lastUpdated&order=<?php echo $next_order; ?>&page=1">Last Updated</a></th>
            </tr>
        </thead>
        <tbody>
            <?php
            echo "\n";
            // Loop through each guild and display in a table row
            if (!empty($guilds)) {
                foreach ($guilds as $guild) {
                    $botDisplay = $guild['bot'] ? 'Y' : '';
                    $playerClass = ($guild['players'] < 50) ? 'incomplete-guild' : '';
                    $playerDisplay = is_null($guild['players']) ? '?' : $guild['players'];
                    echo "\t\t\t<tr><td>" . $botDisplay . "</td>\n";
                    echo "\t\t\t\t<td><a href='/g.php?gid=".$guild['id']."'>" . htmlspecialchars($guild['name']) . "</a></td>\n";
                    echo "\t\t\t\t<td class='$playerClass'>$playerDisplay/50</td>\n";
                    echo "\t\t\t\t<td style='text-align:right'>" . number_format($guild['gp'], 0, '.', ' ') . "</td>\n";
                    echo "\t\t\t\t<td>" . $guild['lastUpdated'] . "</td></tr>\n";
                }
            } else {
                echo "<tr><td colspan='2'>No guilds found.</td></tr>";
            }
            ?>
        </tbody>
    </table>
    
    <!-- Pagination Controls -->
    <div class="pagination">
        <?php if ($page > 1): ?>
            <a href="index.php?page=<?php echo $page - 1; ?>">Previous</a>
        <?php else: ?>
            <a class="disabled">Previous</a>
        <?php endif; ?>

        <?php for ($i = 1; $i <= $total_pages; $i++): ?>
            <a href="index.php?page=<?php echo $i; ?>" class="<?php echo ($i == $page) ? 'active' : ''; ?>">
                <?php echo $i; ?>
            </a>
        <?php endfor; ?>

        <?php if ($page < $total_pages): ?>
            <a href="index.php?page=<?php echo $page + 1; ?>">Next</a>
        <?php else: ?>
            <a class="disabled">Next</a>
        <?php endif; ?>
    </div>
</body>
</html>
