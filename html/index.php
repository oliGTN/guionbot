<?php
// server should keep session data for AT LEAST 1 hour
ini_set('session.gc_maxlifetime', 3600*24*7);
// each client should remember their session id for EXACTLY 1 hour
session_set_cookie_params(3600*24*7);
// Start the session to check if the user is logged in
session_start();

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
$query = "SELECT name, id, players, gp, lastUpdated, NOT isnull(guild_bots.allyCode) AS bot";
$query .= " FROM guilds";
$query .= " LEFT JOIN guild_bot_infos ON (guild_bot_infos.guild_id=guilds.id)";
$query .= " LEFT JOIN guild_bots ON (guild_bots.guild_id=guilds.id)";
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
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <title>GuiOn bot for SWGOH</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="stylesheet" href="basic.css">
    <link rel="stylesheet" href="navbar.css">
    <link rel="stylesheet" href="tables.css">
    <link rel="stylesheet" href="main.1.008.css">
    <link rel="stylesheet" href="https://fonts.googleapis.com/icon?family=Material+Icons">
</head>
  <style>
    /* Styles de la pagination */
    .pagination {
      display: flex;
      justify-content: center;
      list-style: none;
      margin-top: 20px;
      padding: 0;
    }
    .pagination li {
      margin: 0 5px;
    }
    .pagination li a,
    .pagination li span {
      display: block;
      padding: 8px 12px;
      text-decoration: none;
      border: 1px solid #dee2e6;
      border-radius: 4px;
    }
    .pagination li a {
      color: #007bff;
      background-color: #fff;
      transition: background-color 0.3s;
      cursor: pointer;
    }
    .pagination li a:hover {
      background-color: #e9ecef;
    }
    .pagination li a.active {
      background-color: #007bff;
      color: #fff;
      border-color: #007bff;
    }
    .pagination li a.disabled {
      pointer-events: none;
      color: #6c757d;
      background-color: #fff;
      border-color: #dee2e6;
      cursor: default;
    }
    .pagination li span.ellipsis {
      color: #6c757d;
      border: none;
      background: transparent;
    }
  </style>
<body>
<div class="site-container">
<div class="site-pusher">


    <!-- Navigation Bar -->
    <?php include 'navbar.php' ; ?>
    
    <div class="site-content">
    <div class="container">

    <h2>Guilds</h2>
    
    <!-- Search Form -->
    <div class="search-box">
    <form method="POST" action="index.php" class="search-form">
		<input type="text" placeholder="Search guild" value="" id="search" name="search" autocomplete="off" class="browser-default" ">
		<svg class="search-border" version="1.1" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"
			  xmlns:a="http://ns.adobe.com/AdobeSVGViewerExtensions/3.0/" x="0px" y="0px" viewBox="0 0 671 111" style="enable-background:new 0 0 671 111;"
			  xml:space="preserve">
            <path class="border" d="M335.5,108.5h-280c-29.3,0-53-23.7-53-53v0c0-29.3,23.7-53,53-53h280"/>
			<path class="border" d="M335.5,108.5h280c29.3,0,53-23.7,53-53v0c0-29.3-23.7-53-53-53h-280"/>
        </svg>
    </form>
    </div>
    
    <!-- Table to display guild names and lastUpdated, with clickable sortable headers -->
    <div class="card">
    <table class="highlight">
        <thead>
            <tr>
                <?php $current_sort = isset($_GET['sort']) ? $_GET['sort'] : 'name'; ?>
                <th class="<?php echo ($current_sort === 'bot') ? 'active-sort' : ''; ?>"><a href="index.php?sort=bot&order=<?php echo $next_order; ?>&page=1">Bot</a></th>
                <th class="<?php echo ($current_sort === 'name') ? 'active-sort' : ''; ?>"><a href="index.php?sort=name&order=<?php echo $next_order; ?>&page=1">Name</a></th>
                <th class="<?php echo ($current_sort === 'players') ? 'active-sort' : ''; ?>"><a href="index.php?sort=players&order=<?php echo $next_order; ?>&page=1">Players</a></th>
                <th class="<?php echo ($current_sort === 'gp') ? 'active-sort' : ''; ?> text-right" style="text-align:right"><a href="index.php?sort=gp&order=<?php echo $next_order; ?>&page=1">GP</a></th>
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
                    echo "\t\t\t\t<td style='text-align:right' class='hide-on-large-only'>" . round($guild['gp']/1000000, 1) . "M</td>\n";
                    echo "\t\t\t\t<td style='text-align:right' class='hide-on-med-and-down'>" . number_format($guild['gp'], 0, '.', ' ') . "</td>\n";
                    echo "\t\t\t\t<td>" . $guild['lastUpdated'] . "</td></tr>\n";
                }
            } else {
                echo "<tr><td colspan='2'>No guilds found.</td></tr>";
            }
            ?>
        </tbody>
    </table>
    </div>
    
    <!-- Pagination Controls -->
    <ul class="pagination" id="pagination"></ul>

    </div>
    </div>
    <div class="site-cache" id="site-cache" onclick="document.body.classList.toggle('with--sidebar')"></div>

</div>
</div>
<?php include 'sitefooter.php' ; ?>

    <!-- Pagination script -->
  <script>
    // Paramètres de pagination (exemple, à adapter selon tes données)
    let totalPages = <?php echo $total_pages;?>;
    let currentPage = <?php echo $page;?>;

    // Détermine le nombre maximum de pages à afficher selon la largeur de l'écran
    function getMaxVisiblePages() {
      const width = window.innerWidth;
      if (width < 576) return 3;     // Très petit écran
      else if (width < 768) return 5; // Petit écran
      else if (width < 992) return 7; // Écran moyen
      else return 9;                // Grand écran
    }

    // Génère la liste des pages avec les ellipsis
    function generatePagination(total, current, maxVisible) {
      let pages = [];
      if (total <= maxVisible) {
        for (let i = 1; i <= total; i++) {
          pages.push(i);
        }
      } else {
        pages.push(1);
        let left = current - Math.floor((maxVisible - 3) / 2);
        let right = current + Math.floor((maxVisible - 3) / 2);

        if (left < 2) {
          left = 2;
          right = left + maxVisible - 3;
        }
        if (right > total - 1) {
          right = total - 1;
          left = right - maxVisible + 3;
          if (left < 2) left = 2;
        }

        if (left > 2) pages.push("ellipsis");
        for (let i = left; i <= right; i++) {
          pages.push(i);
        }
        if (right < total - 1) pages.push("ellipsis");
        pages.push(total);
      }
      return pages;
    }

    // Met à jour l'affichage de la pagination
    function updatePagination() {
      const paginationContainer = document.getElementById("pagination");
      paginationContainer.innerHTML = ""; // On vide le conteneur

      const maxVisible = getMaxVisiblePages();
      const pages = generatePagination(totalPages, currentPage, maxVisible);

      // Bouton "Previous"
      const prevItem = document.createElement("li");
      const prevLink = document.createElement("a");
      prevLink.textContent = "Previous";
      if (currentPage === 1) {
        prevLink.classList.add("disabled");
      } else {
        prevLink.href = "#";
        prevLink_url = "index.php?sort=<?php echo $sort_column; ?>&order=<?php echo $sort_order; ?>&page=<?php echo $page-1; ?>";
        prevLink.href = prevLink_url;
        //prevLink.addEventListener("click", function(e) {
        //  e.preventDefault();
        //  currentPage--;
        //  updatePagination();
        //});
      }
      prevItem.appendChild(prevLink);
      paginationContainer.appendChild(prevItem);

      // Boutons des pages
      pages.forEach(function(page) {
        const li = document.createElement("li");
        if (page === "ellipsis") {
          const span = document.createElement("span");
          span.textContent = "...";
          span.classList.add("ellipsis");
          li.appendChild(span);
        } else {
          const a = document.createElement("a");
          a.textContent = page;
          if (page === currentPage) {
            a.classList.add("active");
          } else {
            a.href = "#";
            a_url = "index.php?sort=<?php echo $sort_column; ?>&order=<?php echo $sort_order; ?>&page="+page;
            a.href = a_url;
            //a.addEventListener("click", function(e) {
              //e.preventDefault();
              //currentPage = page;
              //updatePagination();
            //});
          }
          li.appendChild(a);
        }
        paginationContainer.appendChild(li);
      });

      // Bouton "Next"
      const nextItem = document.createElement("li");
      const nextLink = document.createElement("a");
      nextLink.textContent = "Next";
      if (currentPage === totalPages) {
        nextLink.classList.add("disabled");
      } else {
        nextLink.href = "#";
        nextLink_url = "index.php?sort=<?php echo $sort_column; ?>&order=<?php echo $sort_order; ?>&page=<?php echo $page+1; ?>";
        nextLink.href = nextLink_url;
        //nextLink.addEventListener("click", function(e) {
        //  e.preventDefault();
        //  currentPage++;
        //  updatePagination();
        //});
      }
      nextItem.appendChild(nextLink);
      paginationContainer.appendChild(nextItem);
    }

    // Mise à jour de la pagination au chargement et lors du redimensionnement
    window.addEventListener("resize", updatePagination);
    updatePagination();
  </script>

</body>
</html>
