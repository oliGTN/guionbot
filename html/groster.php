<?php
// server should keep session data for AT LEAST 1 hour
ini_set('session.gc_maxlifetime', 3600*24*7);
// each client should remember their session id for EXACTLY 1 hour
session_set_cookie_params(3600*24*7);
// Start the session to check if the user is logged in
session_start();

require 'guionbotdb.php';  // Include the database connection for guionbotdb
include 'gvariables.php';

// Check if the user is logged in and if the user is an admin
$isAdmin = isset($_SESSION['admin']) && $_SESSION['admin'];

// Check if a guild is given in URL, otherwise redirect to index
if (!isset($_GET['gid'])) {
    error_log("Redirect to index.php");
    header("Location: index.php");
    exit();
}

$guild_id = $_GET['gid'];

// define $isMyGuild, $isOfficer FROM $guild_id
list($isMyGuild, $isMyGuildConfirmed, $isBonusGuild, $isOfficer) = set_session_rights_for_guild($guild_id);

// Get list of all units
$dict_units_string = file_get_contents("../DATA/unitsList_dict.json");
$full_dict_units = json_decode($dict_units_string, true);
$dict_units = array();
foreach($full_dict_units as $unit_id => $unit) {
    $unit_name = $unit['name'];
    if($unit['combatType'] == 1) {
        $unit_ship = false;
    } else {
        $unit_ship = true;
    }
    $dict_units[$unit_name] = [$unit_id, $unit['combatType']];
}

// Get the Journey Guide from DB
try {
    $query = "SELECT substr(guild_teams.name, 1, length(guild_teams.name)-3) AS name,";
    $query .= " guild_team_roster.unit_id,";
    $query .= " concat(rarity_reco, '*', gear_reco) AS star_gear_relic";
    $query .= " FROM guild_teams";
    $query .= " JOIN guild_subteams ON guild_subteams.team_id = guild_teams.id";
    $query .= " JOIN guild_team_roster ON guild_team_roster.subteam_id = guild_subteams.id";
    $query .= " WHERE guild_teams.name IN(";
    $query .= " 	SELECT name FROM";
    $query .= " 	(";
    $query .= " 		SELECT guild_teams.name, guild_subteams.minimum, count(*) AS count FROM guild_teams";
    $query .= " 		JOIN guild_subteams ON guild_subteams.team_id = guild_teams.id";
    $query .= " 		JOIN guild_team_roster ON guild_team_roster.subteam_id = guild_subteams.id";
    $query .= " 		WHERE isnull(guild_id)";
    $query .= " 		GROUP BY guild_teams.name, guild_subteams.name";
    $query .= " 	) T";
    $query .= " 	GROUP BY name";
    $query .= " 	HAVING sum(minimum) = sum(count)";
    $query .= " )";
    //error_log($query);
    $stmt = $conn_guionbot->prepare($query);
    $stmt->execute();

    // Fetch all the results as an associative array
    $db_data = $stmt->fetchAll(PDO::FETCH_ASSOC);

    $journey_guide = array();
    foreach ($db_data as $line) {
        $journey_unit_id = $line['name'];
        $journey_unit_name = $full_dict_units[$journey_unit_id]['name'];
        $unit_id = $line['unit_id'];
        $unit_name = $full_dict_units[$unit_id]['name'];
        $star_gear_relic = $line['star_gear_relic'];
        if (!isset($journey_guide[$journey_unit_name])) {
            $journey_guide[$journey_unit_name] = array();
        }
        array_push($journey_guide[$journey_unit_name], array($unit_name, $star_gear_relic));
    }
} catch (PDOException $e) {
    error_log("Error fetching journey guide data: " . $e->getMessage());
    echo "Error fetching journey guide data: " . $e->getMessage();
    $journey_guide = array();
}


?>

<!DOCTYPE html>
<html>
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

    <div class="site-content">
    <div class="container">

    <!-- Guild header -->
    <?php include 'gheader.php' ; ?>

    <!-- START OF page specific content -->

    <!-- input field for characters -->
    <div class="card">
        <label for="journeyDropdown">Select Journey Guide:</label><select id="journeyDropdown"></select>
    </div> <!-- class="card" -->
    <div class="card">
        <h3>List of units</h3>
        <div id="modalTokenContainer" class="modal-trigger-container">
            <input type="text" id="modalTriggerInput" placeholder="Click here to add a unit..." readonly>
        </div>
    </div> <!-- class="card" -->

    <div id="dataModal" class="modal">
        <div class="modal-content">
            <h3>Select unit and gear</h3>
            <label for="unitDropdown">Select Unit:</label><select id="unitDropdown"></select>
            <label for="gearDropdown">Select Gear:</label><select id="gearDropdown"></select>
            <label for="starDropdown">Select Stars:</label><select id="starDropdown"></select>
            <div class="modal-buttons">
                <button id="cancelButton">Cancel</button>
                <button id="okButton">OK</button>
            </div>
        </div>
    </div>

    <br/>
    <div class="card">
        <table id="roster-table" class="highlight" style="table-layout:fixed; width:100%">
            <thead>
                <tr/>
            </thead>
            <tbody/>
        </table>
    </div> <!-- class="card" -->

    <!-- END OF page specific content -->
    </div> <!-- container -->
    </div> <!-- site-content -->
    <div class="site-cache" id="site-cache" onclick="document.body.classList.toggle('with--sidebar')"></div>
    
</div>
</div>
</body>

    <script>
        // Constants
        AVAILABLE_GUIDE = <?php echo json_encode($journey_guide);?>;
        AVAILABLE_UNITS = <?php echo json_encode($dict_units);?>;
        AVAILABLE_GEARS = ['G1', 'G2', 'G3', 'G4', 'G5', 'G6', 'G7', 'G8', 'G9', 'G10', 'G11', 'G12', 'G13', 'R1', 'R2', 'R3', 'R4', 'R5', 'R6', 'R7', 'R8', 'R9']
        AVAILABLE_STARS = ['1', '2', '3', '4', '5', '6', '7']

        // Global state
        let modalTokens = new Set();
        
        // Journey elements
        const journeyDropdown = document.getElementById('journeyDropdown');

        // Modal elements
        const modalTriggerInput = document.getElementById('modalTriggerInput');
        const modalTokenContainer = document.getElementById('modalTokenContainer');
        const dataModal = document.getElementById('dataModal');
        const unitDropdown = document.getElementById('unitDropdown');
        const gearDropdown = document.getElementById('gearDropdown');
        const starDropdown = document.getElementById('starDropdown');
        const okButton = document.getElementById('okButton');
        const cancelButton = document.getElementById('cancelButton');

        // Journey logics
        function handleJourneySelection(event) {
            var journey_name = journeyDropdown.value;
            if (journey_name == 'custom') return;

            deleteAllTokens();
            var journey_guide = AVAILABLE_GUIDE[journey_name];
            //console.log(journey_guide);

            // Create tokens except the last one, without refresh of table
            for (var i=0; i<journey_guide.length-1; i++) {
                var journey_unit = journey_guide[i];
                var token_name = journey_unit[0] + ' (' + journey_unit[1] + ')';
                createTokenFromText(token_name, refreshTable=false);
            }
            var journey_unit = journey_guide[i];
            var token_name = journey_unit[0] + ' (' + journey_unit[1] + ')';
            createTokenFromText(token_name, refreshTable=true);
        }
        
        
        // Modal logics
        function showDataModal() {
            // Filter guilds that haven't been selected yet with any value
            const availableModalItems = Object.keys(AVAILABLE_UNITS).filter(unit_name => {
                return !Array.from(modalTokens).some(token => token.startsWith(unit_name + ' ('));
            }).sort((a, b) => a.localeCompare(b, 'fr', {'sensitivity': 'base'}));

            populateUnitDropdown(availableModalItems);

            if (availableModalItems.length > 0) {
                 dataModal.style.display = 'block';
            } else {
                 alert("All available units have been selected!");
            }
        }
        
        function populateUnitDropdown(units) {
            unitDropdown.innerHTML = ''; // Clear previous options
             units.forEach(unit => {
                const option = document.createElement('option');
                option.value = unit;
                option.textContent = unit;
                unitDropdown.appendChild(option);
            });
        }

        function get_unit_list_from_modalTokens() {
            var units_list = [];
            modalTokens.forEach(unit_def => {
                var unit_def_split = unit_def.split('(');
                var star_gear_relic = unit_def_split[unit_def_split.length-1].split(')')[0]
                var rarity = star_gear_relic.split('*')[0];
                var gear_relic = star_gear_relic.split('*')[1];
                var gear;
                var relic;

                if (gear_relic == '') {
                    // empty, for ships
                    gear=null;
                    relic=null;
                } else if (gear_relic.substring(0,1) == 'G') {
                    gear = parseInt(gear_relic.substring(1,3));
                    relic = 0;
                } else {
                    gear=13;
                    relic = parseInt(gear_relic.substring(1,3));
                }
                var unit_name_with_blank = unit_def_split.slice(0, unit_def_split.length-1).join('(');
                var unit_name = unit_name_with_blank.substring(0, unit_name_with_blank.length-1);
                var unit_id = AVAILABLE_UNITS[unit_name][0];
                units_list.push({
                    "unit_id" : unit_id,
                    "unit_name" : unit_name,
                    "rarity": rarity,
                    "gear": gear,
                    "relic": relic
                });
            });
            return units_list;
        }

        function handleModalOk(refreshTable=true) {
            const unit = unitDropdown.value;
            const gear = gearDropdown.value;
            const rarity = starDropdown.value;
            
            if (!unit || !gear || !rarity) {
                alert("Please select a unit, a gear and stars.");
                return;
            }

            const tokenText = unit+' ('+rarity+'*'+gear+')';
            
            if (modalTokens.has(tokenText)) {
                 alert("This unit/gear/stars combination has already been selected.");
                 return;
            }

            createTokenFromText(tokenText, refreshTAble=refreshTable);
            journeyDropdown.value = 'custom';

            dataModal.style.display = 'none';

        }

        function createTokenFromText(tokenText, refreshTable=true) {
            // Create and insert the new token
            const token = createTokenElement(tokenText, 'token');
            modalTokenContainer.insertBefore(token, modalTriggerInput);
            modalTokens.add(tokenText);
            if (refreshTable) refreshRosterTable();
        }

        function get_dict_roster_from_units_list(units_list) {
            var body_json = {
                "request_type": 'guild_roster',
                "guild_id": '<?php echo $guild_id;?>', 
                "units_list": units_list
            };

            return fetch("/groster_request.php", {
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
                var err_code = data['err_code'];
                var err_txt = data['err_txt'];

                if (err_code!=0) {
                    window.alert("ERROR: "+err_txt);
                    return {};
                } else {
                    const dict_roster = {};
                    const guild_roster = data['roster'] || [];
                    guild_roster.forEach(line => {
                        name = line['name'];
                        defId = line['defId'];
                        rarity = line['rarity'];
                        gear = line['gear'];
                        relic = line['relic'];

                        if(!(name in dict_roster)) {
                            dict_roster[name] = {};
                        }
                        dict_roster[name][defId] = [rarity, gear, relic];
                    });

                    return dict_roster;
                }
            });
        }

        function update_roster_table(units_list, dict_roster) {
            var roster_table = document.getElementById('roster-table');

            // first the header row
            var headers = roster_table.getElementsByTagName('thead')[0];
            var header_row = headers.getElementsByTagName('tr')[0];
            header_row.remove()
            header_row = document.createElement('tr');

            var new_th = document.createElement('th');
            new_th.innerHTML = 'Player';
            new_th.style.width = '150px';
            new_th.addEventListener('click', function() {sortTable(0, true);});
            header_row.appendChild(new_th);

            // one column by unit
            units_list.forEach(unit => {
                new_th = document.createElement('th');
                new_th.style.textAlign = 'center';

                var new_img = document.createElement('img');

                new_img.src='IMAGES/CHARACTERS/'+unit['unit_id']+'.png';
                new_img.style.width='100%';
                new_img.style.maxWidth='100px';

                new_th.appendChild(new_img);
                header_row.appendChild(new_th);
            });

            new_th = document.createElement('th');
            new_th.innerHTML = 'Progress %';
            new_th.style.width = '100px';
            new_th.addEventListener('click', function() {sortTable(units_list.length+1, false);});
            header_row.appendChild(new_th);

            // then the player lines
            var table_body = roster_table.getElementsByTagName('tbody')[0];
            table_body.remove();
            table_body = document.createElement('tbody');

            // Empty table if no units
            if (units_list.length == 0) {
                // reinitialize empty table
                headers.appendChild(header_row);
                roster_table.appendChild(table_body);
                return;
            }

            for (const [player_name, player_roster] of Object.entries(dict_roster)) {
                var new_tr = document.createElement('tr');
                table_body.appendChild(new_tr);

                var new_td = document.createElement('td');
                new_td.innerHTML = player_name;
                new_td.style.overflow = 'hidden';
                new_tr.appendChild(new_td);

                var list_progress = [];
                units_list.forEach(unit => {
                    new_td = document.createElement('td');
                    new_td.style.textAlign = 'center';
                    new_td.style.overflow = 'hidden';
                    new_tr.appendChild(new_td);

                    unit_id = unit['unit_id'];
                    var gear_relic = "";
                    var unit_level = 0;
                    var unit_exists = false;
                    if (unit_id in player_roster) {
                        var rarity = parseInt(player_roster[unit_id][0]);
                        var gear = player_roster[unit_id][1];
                        if (gear == null) {
                            gear_relic='';
                            unit_level = parseInt(rarity);
                            new_td.innerHTML = rarity+String.fromCodePoint(0x2B50)
                        } else {
                            gear = parseInt(gear);
                            var relic = parseInt(player_roster[unit_id][2]);
                            if (relic == 0) {
                                gear_relic = "G" + gear;
                                unit_level = parseInt(gear);
                            } else {
                                gear_relic = "R" + relic;
                                unit_level = 13+parseInt(relic);
                            }
                            new_td.innerHTML = gear_relic;
                        }
                        unit_exists = true;
                    } else {
                        new_td.innerHTML = '';
                    }
                        
                    var target_level = 0;
                    var target_rarity = unit['rarity'];
                    target_gear = unit['gear'];
                    target_relic = unit['relic'];
                    if (target_gear == null) {
                        gear_relic='';
                        target_level = parseInt(target_rarity);
                    } else {
                        if (target_relic == 0) {
                            target_level = target_gear;
                        } else {
                            target_level = 13+target_relic;
                        }
                    }

                    var unit_progress = Math.min(unit_level/target_level, 1);
                    list_progress.push(unit_progress);
                
                    if (!unit_exists) {
                        new_td.style.backgroundColor = "darkred";
                    } else if (unit_progress == 1.0) {
                        new_td.style.backgroundColor = "green";
                    } else if (unit_progress >= .8) {
                        new_td.style.backgroundColor = "orange";
                    } else if (!unit_exists) {
                        new_td.style.backgroundColor = "darkred";
                    } else {
                        new_td.style.backgroundColor = "red";
                    }



                });

                // Progress
                const sum_progress = list_progress.reduce((partialSum, a) => partialSum + a, 0);
                new_td = document.createElement('td');
                var global_progress = Math.round(100*sum_progress/list_progress.length, 0);
                new_td.innerHTML = Math.round(100*sum_progress/list_progress.length, 0);
                new_tr.appendChild(new_td);

                // set color for global progress
                if (global_progress == 100) {
                    new_td.style.backgroundColor = "green";
                } else if (global_progress >= 80) {
                    new_td.style.backgroundColor = "orange";
                } else {
                    new_td.style.backgroundColor = "red";
                }
                new_td.style.fontWeight = "bold";
            }

            headers.appendChild(header_row);
            roster_table.appendChild(table_body);

        }


        // --- Shared Token Functions ---

        function createTokenElement(text, className) {
            const token = document.createElement('span');
            token.className = className;
            token.dataset.value = text;
            token.innerHTML = `${text}<span class="token-delete" data-value="${text}">&times;</span>`;
            const deleteCross = token.querySelector('.token-delete');
            deleteCross.addEventListener('click', deleteToken);
            return token;
        }

        function deleteAllTokens() {
            var tokens = modalTokenContainer.getElementsByClassName('token');
            if (tokens.length == 0) return;

            while (tokens.length > 1) {
                token = tokens[0];
                deleteTokenFromElement(token, refreshTable=false);
            }
            // Now delete the last one and refresh the table
            token = tokens[0];
            deleteTokenFromElement(token, refreshTable=true);
        }

        function deleteToken(event, refreshTable=true) {
            const tokenElement = event.target.closest('.token');
            deleteTokenFromElement(tokenElement, refreshTable=refreshTable);

            journeyDropdown.value = 'custom';
        }

        function deleteTokenFromElement(tokenElement, refreshTable=true) {
            const valueToDelete = tokenElement.dataset.value;

            if (tokenElement) {
                tokenElement.remove();
                modalTokens.delete(valueToDelete);

                if (refreshTable) refreshRosterTable();
            }
        }

        function refreshRosterTable() {
            // Create list of units to search in the guild
            var units_list = get_unit_list_from_modalTokens();

            if (units_list.length > 0) {
                // POST request to get the unit status in the guild
                get_dict_roster_from_units_list(units_list)
                    .then((dict_roster) => {
                        // update HTML table
                        update_roster_table(units_list, dict_roster);
                    });
            } else {
                update_roster_table([], {});
            }
        }


        // Initialization
        function initializePage() {
            // create event listeners
            modalTriggerInput.addEventListener('click', showDataModal);
            cancelButton.addEventListener('click', () => { dataModal.style.display = 'none'; });
            okButton.addEventListener('click', handleModalOk);
            journeyDropdown.addEventListener('change', handleJourneySelection);
            
            // Populate Modal dropdowns
            Object.keys(AVAILABLE_UNITS).forEach(unit => unitDropdown.add(new Option(unit, unit)));
            AVAILABLE_GEARS.forEach(value => gearDropdown.add(new Option(value, value)));
            gearDropdown.value='G13';
            AVAILABLE_STARS.forEach(value => starDropdown.add(new Option(value+String.fromCodePoint(0x2B50), value)));
            starDropdown.value=7;
                    
            var list_journeys = Object.keys(AVAILABLE_GUIDE).sort((a, b) => a.localeCompare(b, 'fr', {'sensitivity': 'base'}));
            journeyDropdown.add(new Option('custom', 'custom'));
            list_journeys.forEach(value => journeyDropdown.add(new Option(value, value)));

            // initialize empty roster table
            update_roster_table([], {});
        }

        // Global click handler to close dropdowns/modals
        document.addEventListener('click', (e) => {
            const isInsideDataModal = dataModal.contains(e.target);

            if (!isInsideDataModal && e.target !== modalTriggerInput) {
                // If click is outside modal and not on the trigger input
                dataModal.style.display = 'none';
            }
        });
    
        // Code to sort the table
        // source: https://www.w3schools.com/howto/howto_js_sort_table.asp
function sortTable(n, is_text) {
  var table, rows, switching, i, x, y, shouldSwitch, dir, switchcount = 0;
  table = document.getElementById("roster-table");
  switching = true;
  // Set the sorting direction to ascending:
  dir = "desc";
  /* Make a loop that will continue until
  no switching has been done: */
  while (switching) {
    // Start by saying: no switching is done:
    switching = false;
    rows = table.rows;
    if (typeof(rows) == 'undefined') return;
    /* Loop through all table rows (except the
    first, which contains table headers): */
    for (i = 1; i < (rows.length - 1); i++) {
      // Start by saying there should be no switching:
      shouldSwitch = false;
      /* Get the two elements you want to compare,
      one from current row and one from the next: */
      x = rows[i].getElementsByTagName("TD")[n];
      y = rows[i + 1].getElementsByTagName("TD")[n];
      /* Check if the two rows should switch place,
      based on the direction, asc or desc: */
      if (dir == "asc") {
        if (is_text) {
            // Text comparison
            var bool_compare = (x.innerHTML.toLowerCase() > y.innerHTML.toLowerCase());
        } else {
            // Number comparison
            var bool_compare = (Number(x.innerHTML) > Number(y.innerHTML));
        }
        if (bool_compare) {
          // If so, mark as a switch and break the loop:
          shouldSwitch = true;
          break;
        }
      } else if (dir == "desc") {
        if (is_text) {
            // Text comparison
            var bool_compare = (x.innerHTML.toLowerCase() < y.innerHTML.toLowerCase());
        } else {
            // Number comparison
            var bool_compare = (Number(x.innerHTML) < Number(y.innerHTML));
        }
        if (bool_compare) {
          // If so, mark as a switch and break the loop:
          shouldSwitch = true;
          break;
        }
      }
    }
    if (shouldSwitch) {
      /* If a switch has been marked, make the switch
      and mark that a switch has been done: */
      rows[i].parentNode.insertBefore(rows[i + 1], rows[i]);
      switching = true;
      // Each time a switch is done, increase this count by 1:
      switchcount ++;
    } else {
      /* If no switching has been done AND the direction is "desc",
      set the direction to "asc" and run the while loop again. */
      if (switchcount == 0 && dir == "desc") {
        dir = "asc";
        switching = true;
      }
    }
  }
}

        // Execute initialization when the window loads
        window.onload = initializePage;


    </script>

<?php include 'sitefooter.php' ; ?>
</html>
