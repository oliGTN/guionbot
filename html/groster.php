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
            <div class="modal-buttons">
                <button id="cancelButton">Cancel</button>
                <button id="okButton">OK</button>
            </div>
        </div>
    </div>

    <br/>
    <div class="card">
        <table id="roster-table" class="highlight">
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
        AVAILABLE_UNITS = <?php echo json_encode($dict_units);?>;
        AVAILABLE_GEARS = ['G1', 'G2', 'G3', 'G4', 'G5', 'G6', 'G7', 'G8', 'G9', 'G10', 'G11', 'G12', 'G13', 'R1', 'R2', 'R3', 'R4', 'R5', 'R6', 'R7', 'R8', 'R9']

        // Global state
        let modalTokens = new Set();
        
        // Modal elements
        const modalTriggerInput = document.getElementById('modalTriggerInput');
        const modalTokenContainer = document.getElementById('modalTokenContainer');
        const dataModal = document.getElementById('dataModal');
        const unitDropdown = document.getElementById('unitDropdown');
        const gearDropdown = document.getElementById('gearDropdown');
        const okButton = document.getElementById('okButton');
        const cancelButton = document.getElementById('cancelButton');

        // Modal logics
        function showDataModal() {
            // Filter guilds that haven't been selected yet with any value
            const availableModalItems = Object.keys(AVAILABLE_UNITS).filter(unit_name => {
                return !Array.from(modalTokens).some(token => token.startsWith(unit_name + ' ('));
            }).sort((a, b) => a.localeCompare(b, 'fr', {'sensitivity': 'base'}));

            populateItemDropdown(availableModalItems);

            if (availableModalItems.length > 0) {
                 dataModal.style.display = 'block';
            } else {
                 alert("All available units have been selected!");
            }
        }
        
        function populateItemDropdown(items) {
            unitDropdown.innerHTML = ''; // Clear previous options
             items.forEach(item => {
                const option = document.createElement('option');
                option.value = item;
                option.textContent = item;
                unitDropdown.appendChild(option);
            });
        }

        function get_unit_list_from_modalTokens() {
            var units_list = [];
            modalTokens.forEach(name_gear => {
                var name_gear_split = name_gear.split('(');
                var gear_relic = name_gear_split[name_gear_split.length-1].split(')')[0]
                var gear;
                var relic;

                if (gear_relic.substring(0,1) == 'G') {
                    gear = parseInt(gear_relic.substring(1,2));
                    relic = 0;
                } else {
                    gear=13;
                    relic = parseInt(gear_relic.substring(1,2));
                }
                var unit_name_with_blank = name_gear_split.slice(0, name_gear_split.length-1).join('(');
                var unit_name = unit_name_with_blank.substring(0, unit_name_with_blank.length-1);
                var unit_id = AVAILABLE_UNITS[unit_name][0];
                units_list.push({
                    "unit_id" : unit_id,
                    "unit_name" : unit_name,
                    "gear": gear,
                    "relic": relic
                });
            });
            return units_list;
        }

        function handleModalOk() {
            const item = unitDropdown.value;
            const value = gearDropdown.value;
            
            if (!item || !value) {
                alert("Please select both an element and a value.");
                return;
            }

            const tokenText = `${item} (${value})`;
            
            if (modalTokens.has(tokenText)) {
                 alert("This item/value combination has already been selected.");
                 return;
            }

            // Create and insert the new token
            const token = createTokenElement(tokenText, 'token modal-token');
            modalTokenContainer.insertBefore(token, modalTriggerInput);
            
            modalTokens.add(tokenText);
            dataModal.style.display = 'none';

            // Create list of units to search in the guild
            var units_list = get_unit_list_from_modalTokens();

            // POST request to get the unit status in the guild
            get_dict_roster_from_units_list(units_list)
                .then((dict_roster) => {
                    // update HTML table
                    update_roster_table(units_list, dict_roster);
                });

        }

        function get_dict_roster_from_units_list(units_list) {
            var body_json = {
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
                    console.log(data);
                    guild_roster.forEach(line => {
                        name = line['name'];
                        defId = line['defId'];
                        gear = line['gear'];
                        relic = line['relic'];

                        if(!(name in dict_roster)) {
                            dict_roster[name] = {};
                        }
                        dict_roster[name][defId] = [gear, relic];
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
            headers.appendChild(header_row);

            var new_th = document.createElement('th');
            new_th.innerHTML = 'Player';
            header_row.appendChild(new_th);

            // one column by unit
            units_list.forEach(unit => {
                new_th = document.createElement('th');
                new_th.innerHTML = unit['unit_name'];
                header_row.appendChild(new_th);
            });

            new_th = document.createElement('th');
            new_th.innerHTML = 'Progress %';
            header_row.appendChild(new_th);

            // then the player lines
            var table_body = roster_table.getElementsByTagName('tbody')[0];
            table_body.remove();
            table_body = document.createElement('tbody');
            roster_table.appendChild(table_body);

            // Empty table if no units
            console.log(units_list);
            console.log(units_list.length);
            if (units_list.length == 0) {
                // reinitialize empty table
                console.log('empty units_list');
                return;
            }

            for (const [player_name, player_roster] of Object.entries(dict_roster)) {
                console.log(player_name);
                var new_tr = document.createElement('tr');
                table_body.appendChild(new_tr);

                var new_td = document.createElement('td');
                new_td.innerHTML = player_name;
                new_tr.appendChild(new_td);

                var list_progress = [];
                units_list.forEach(unit => {
                    new_td = document.createElement('td');
                    new_tr.appendChild(new_td);

                    unit_id = unit['unit_id'];
                    var gear_relic = "";
                    var gear_relic_int = 0;
                    if (unit_id in player_roster) {
                        var gear = parseInt(player_roster[unit_id][0]);
                        var relic = parseInt(player_roster[unit_id][1]);
                        if (relic == 0) {
                            gear_relic = "G" + gear;
                            gear_relic_int = parseInt(gear);
                        } else {
                            gear_relic = "R" + relic;
                            gear_relic_int = 13+parseInt(relic);
                        }
                    }
                    
                    var target_gear_relic_int = 0;
                    target_gear = unit['gear'];
                    target_relic = unit['relic'];
                    if (target_relic == 0) {
                        target_gear_relic_int = target_gear;
                    } else {
                        target_gear_relic_int = 13+target_relic;
                    }
                    unit_progress = Math.min(gear_relic_int/target_gear_relic_int, 1);
                    list_progress.push(unit_progress);
                
                    if (unit_progress == 1.0) {
                        new_td.style.backgroundColor = "green";
                    } else if (unit_progress >= .8) {
                        new_td.style.backgroundColor = "orange";
                    } else {
                        new_td.style.backgroundColor = "red";
                    }

                    new_td.innerHTML = gear_relic;

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
            }


        }


        // --- Shared Token Functions ---

        function createTokenElement(text, className, deleteHandler = deleteToken) {
            const token = document.createElement('span');
            token.className = className;
            token.dataset.value = text;
            token.innerHTML = `${text}<span class="token-delete" data-value="${text}">&times;</span>`;
            const deleteCross = token.querySelector('.token-delete');
            deleteCross.addEventListener('click', deleteHandler);
            return token;
        }

        function deleteToken(event) {
            const valueToDelete = event.target.dataset.value;
            const tokenElement = event.target.closest('.token');

            if (tokenElement) {
                tokenElement.remove();
                if (tokenElement.classList.contains('modal-token')) {
                    modalTokens.delete(valueToDelete);
                }

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
        }


        // Initialization
        function initializePage() {
            // create event listeners
            modalTriggerInput.addEventListener('click', showDataModal);
            cancelButton.addEventListener('click', () => { dataModal.style.display = 'none'; });
            okButton.addEventListener('click', handleModalOk);
            
            // Populate Modal dropdowns
            Object.keys(AVAILABLE_UNITS).forEach(item => unitDropdown.add(new Option(item, item)));
            AVAILABLE_GEARS.forEach(value => gearDropdown.add(new Option(value, value)));

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

        // Execute initialization when the window loads
        window.onload = initializePage;


    </script>

<?php include 'sitefooter.php' ; ?>
</html>
