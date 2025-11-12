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

// ---- get DB data after handling potential POST commands, so that the page is up to date ----------
if ($isAdmin) {
    try {
        // Prepare the SQL query to fetch the specific guild associations from the DB table
        $query = "SELECT users.user_id AS user_id, users.name AS name, GROUP_CONCAT(guilds.name) AS guild_names FROM users";
        $query .= " LEFT JOIN user_guilds ON users.user_id=user_guilds.user_id";
        $query .= " LEFT JOIN guionbotdb.guilds ON guionbotdb.guilds.id=guild_id";
        $query .= " GROUP BY user_id ORDER BY users.name";
        //error_log($query);
        $stmt = $conn->prepare($query);
        $stmt->execute();

        // Fetch all the results as an associative array
        $db_data = $stmt->fetchAll(PDO::FETCH_ASSOC);

        $user_guilds = array();
        foreach($db_data as $line) {
            $user_name_id = $line['name']." (".$line['user_id'].")";
            $user_guilds[$user_name_id] = $line['guild_names'];
        }

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
    $db_data = $stmt->fetchAll(PDO::FETCH_ASSOC);

    $guilds = array();
    foreach($db_data as $line) {
        $guilds[$line['name']] = $line['id'];
    }

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
    <link rel="stylesheet" href="tokens.css">
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
                    <!-- token table, button, and modal -->
                    <table class="user-table">
                        <thead>
                            <tr>
                                <th></th>
                                <th>User name</th>
                                <th>Associated guilds</th>
                            </tr>
                        </thead>
                        <tbody id="userTableBody"/>
                    </table>
                    <button id="newUserButton" style="margin-top: 10px;">New User</button>
                    <div id="newUserModal" class="modal">
                        <div class="modal-content">
                            <h3>Add New User</h3>
                            <label for="userDropdown">Select User:</label>
                            <select id="userDropdown"></select>
                
                            <div class="modal-buttons">
                                <button id="newUserCancelButton">Cancel</button>
                                <button id="newUserOkButton">OK</button>
                            </div>
                        </div>
                    </div>
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

    <script>
        // --- Shared Data ---
<?php
        $js_list_txt = json_encode($guilds);
        echo "\t\tconst AVAILABLE_GUILDS = ".$js_list_txt.";\n";
        
        $js_list_txt = json_encode($user_guilds);
        echo "\t\tconst AVAILABLE_USERS = ".$js_list_txt.";\n";
?>
    
        // --- Global State ---
        let userGuildsMap = new Map();
        let usedUsers = new Set();

        // --- Shared Token Functions ---

        function createTokenElement(text, className, deleteHandler = deleteToken) {
            const token = document.createElement('span');
            token.className = className;
            token.dataset.value = text;
            token.dataset.testgui = 'guiOn toto';
            token.dataset.testOn = 'guiOn titi';
            token.innerHTML = `${text}<span class="token-delete" data-value="${text}">&times;</span>`;
            const deleteCross = token.querySelector('.token-delete');
            deleteCross.addEventListener('click', deleteHandler);
            return token;
        }
        
        // --- Dropdown Logic ---
        function renderDropdown(items, dropdownElement, selectCallback) {
            dropdownElement.innerHTML = '';
            if (items.length === 0) { dropdownElement.style.display = 'none'; return; }

            items.forEach(item => {
                const listItem = document.createElement('li');
                listItem.textContent = item;
                listItem.addEventListener('click', () => selectCallback(item));
                dropdownElement.appendChild(listItem);
            });
            dropdownElement.style.display = 'block';
        }

        // --- Table Logic ---
        newUserButton.addEventListener('click', showNewUserModal);
        newUserCancelButton.addEventListener('click', () => { newUserModal.style.display = 'none'; });
        newUserOkButton.addEventListener('click', () => {
            createUserRow(userDropdown.value, []);
            newUserModal.style.display = 'none';
        });

        function populateUserDropdown() {
            userDropdown.innerHTML = '';
            const availableUsers = Object.keys(AVAILABLE_USERS).filter(user => !usedUsers.has(user)).sort((a, b) => a.localeCompare(b, 'en', {'sensitivity': 'base'}));

            if (availableUsers.length === 0) {
                userDropdown.innerHTML = '<option disabled>No new users available</option>';
                newUserOkButton.disabled = true;
                return;
            }

            availableUsers.forEach(user => {
                const option = document.createElement('option');
                option.value = user;
                option.textContent = user;
                userDropdown.appendChild(option);
            });
            newUserOkButton.disabled = false;
        }

        function showNewUserModal() {
            populateUserDropdown();
            newUserModal.style.display = 'block';
        }

        function createUserRow(userName, initialGuilds) {
            if (!userName || usedUsers.has(userName)) return;

            usedUsers.add(userName);
            const userGuilds = new Set(initialGuilds);
            userGuildsMap.set(userName, userGuilds);

            const row = userTableBody.insertRow();
            row.dataset.username = userName;

            const cellDelete = row.insertCell();
            cellDelete.innerHTML = `<button class="delete-row-btn" data-username="${userName}">&times;</button>`;
            cellDelete.querySelector('.delete-row-btn').addEventListener('click', deleteUserRow);

            const cellName = row.insertCell();
            cellName.textContent = userName;

            const cellGuilds = row.insertCell();
            cellGuilds.className = 'guilds-cell';

            const guildsContainer = document.createElement('div');
            guildsContainer.className = 'guilds-container';

            const guildsInput = document.createElement('input');
            guildsInput.type = 'text';
            guildsInput.className = 'guilds-input';
            guildsInput.placeholder = 'Add guild...';

            const tableDropdown = document.createElement('ul');
            tableDropdown.className = 'table-autocomplete-dropdown';

            guildsContainer.appendChild(guildsInput);
            cellGuilds.appendChild(guildsContainer);
            cellGuilds.appendChild(tableDropdown);

            guildsInput.addEventListener('input', (e) => handleTableInput(e.target, tableDropdown, userName));
            guildsInput.addEventListener('focus', (e) => handleTableInput(e.target, tableDropdown, userName));

            document.addEventListener('click', (e) => {
                if (!cellGuilds.contains(e.target)) {
                    tableDropdown.style.display = 'none';
                }
            });

            initialGuilds.forEach(guild => {
                const token = createTokenElement(guild, 'token table-token', deleteTableToken);
                token.dataset.userName = userName;
                guildsContainer.insertBefore(token, guildsInput);
            });
        }

        function deleteUserRow(event) {
            const userName = event.target.dataset.username;
            const row = event.target.closest('tr');
            
            if (row && userName) {
                // first delete tokens in the row
                list_tokens = row.querySelectorAll('.token');
                console.log(list_tokens);
                list_tokens.forEach(token => {
                    deleteTableTokenFromToken(token);
                });
                row.remove();
                usedUsers.delete(userName);
                userGuildsMap.delete(userName);
            }
        }
        
        function handleTableInput(inputElement, dropdownElement, userName) {
            const query = inputElement.value.trim().toLowerCase();
            const userGuilds = userGuildsMap.get(userName) || new Set();

            if (query.length === 0) {
                dropdownElement.style.display = 'none';
                return;
            }

            const filteredItems = Object.keys(AVAILABLE_GUILDS).filter(guild => 
                guild.toLowerCase().includes(query) && !userGuilds.has(guild)
            );

            renderDropdown(filteredItems, dropdownElement, (guild) => selectGuildForUser(guild, inputElement, dropdownElement, userName));
        }

        function selectGuildForUser(guild, inputElement, dropdownElement, userName) {
            const userGuilds = userGuildsMap.get(userName);
            if (!userGuilds) return;

            const token = createTokenElement(guild, 'token table-token', deleteTableToken);
            token.dataset.userName = userName;

            const guildsContainer = inputElement.parentElement;
            guildsContainer.insertBefore(token, inputElement);

            userGuilds.add(guild);
            
            inputElement.value = '';
            dropdownElement.style.display = 'none';
            inputElement.focus();

            // POST request to reload the page (and update the DB)
            var userName_split = userName.split('(');
            var user_id = userName_split[userName_split.length-1].split(')')[0];

            var body_json = {
                associate_guild: true,
                user_id: user_id,
                guild_id: AVAILABLE_GUILDS[guild]
            };
            var err_code=0;
            var err_txt="";
            fetch("/dashboard_request.php", {
                method: "post",
                headers: {
                    'Accept': 'application/json',
                    'Content-Type': 'application/json'
                },

                //make sure to serialize your JSON body
                body: JSON.stringify(body_json)
            })
            .then((response) => {return response.json()})
            .then((data) => {
                //console.log(data);
                err_code = data['err_code'];
                err_txt = data['err_txt'];

                if (err_code!=0) {
                    window.alert("ERROR: "+err_txt);
                }
            });

        }

        function deleteTableToken(event) {
            const tokenElement = event.target.closest('.token'); // Find the parent token 
            
            if (!tokenElement) return; // Safety check

            return deleteTableTokenFromToken(tokenElement);
        }
            
        function deleteTableTokenFromToken(tokenElement) {
            const guildToDelete = tokenElement.dataset.value; // Get value from the token
            const userName = tokenElement.dataset.userName; 

            // Check if the userName was successfully retrieved before proceeding
            if (!userName) {
                console.error("User name missing on token element.");
                tokenElement.remove(); // Still remove the element if state tracking failed
                return;
            }
            
            // Proceed with deletion and state cleanup
            if (tokenElement) {
                // Remove from the user's specific state map
                const userGuilds = userGuildsMap.get(userName);
                if (userGuilds) {
                    userGuilds.delete(guildToDelete);
                }
                tokenElement.remove();
                
                // Try to refresh autocomplete if input has content after deletion
                const row = document.querySelector(`tr[data-username="${userName}"]`);
                if (row) {
                    const inputElement = row.querySelector('.guilds-input');
                    const dropdownElement = row.querySelector('.table-autocomplete-dropdown');
                    if (inputElement && dropdownElement && inputElement.value.length > 0) {
                        handleTableInput(inputElement, dropdownElement, userName);
                    }
                }
            }

            // POST request to reload the page (and update the DB)
            var userName_split = userName.split('(');
            var user_id = userName_split[userName_split.length-1].split(')')[0];

            var body_json = {
                deassociate_guild: true,
                user_id: user_id,
                guild_id: AVAILABLE_GUILDS[guildToDelete]
            };
            console.log(body_json);
            var err_code=0;
            var err_txt="";
            fetch("/dashboard_request.php", {
                method: "post",
                headers: {
                    'Accept': 'application/json',
                    'Content-Type': 'application/json'
                },

                //make sure to serialize your JSON body
                body: JSON.stringify(body_json)
            })
            .then((response) => {return response.json()})
            .then((data) => {
                //console.log(data);
                err_code = data['err_code'];
                err_txt = data['err_txt'];

                if (err_code!=0) {
                    window.alert("ERROR: "+err_txt);
                }
            });
        }

        // --- Initialization ---
        function initializePage() {
            // Initialize User Table with existing associations
            <?php
            // Loop through each player and display in a table row
            if (!empty($user_guilds)) {
                foreach ($user_guilds as $user_name => $guild_names) {
                    if($guild_names != "") {
                        $guild_list = explode(",", $guild_names);
                        $js_list_txt = '["'.implode('", "', $guild_list).'"]';
                        echo "createUserRow('".$user_name."', ".$js_list_txt.");\n";
                    }
                }
            }
            ?>

        }

        // Execute initialization when the window loads
        window.onload = initializePage;


    </script>
</html>
