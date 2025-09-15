<?php
// server should keep session data for AT LEAST 1 hour
ini_set('session.gc_maxlifetime', 3600*24*7);
// each client should remember their session id for EXACTLY 1 hour
session_set_cookie_params(3600*24*7);
// Start the session to check if the user is logged in
session_start();

require 'guionbotdb.php';  // Include the database connection for guionbotdb
include 'tbrequests.php';
include 'gvariables.php';
include 'tbheader.php';

// Check if the user is logged in and if the user is an admin
$isAdmin = isset($_SESSION['admin']) && $_SESSION['admin'];

// Check if a TB id and a round are given in URL, otherwise redirect to index
if (!isset($_GET['id'])) {
    error_log("No id: redirect to index.php");
    header("Location: index.php");
    exit();
}
$tb_id = $_GET['id'];
$round = get_round_from_get($tb_id);
$tb = get_tb_from_id($tb_id);
$guild_id = $tb['guild_id'];
$guild_name = $tb['guild_name'];
$zones = get_tb_round_zones($tb_id, $round);

list($isMyGuild, $isMyGuildConfirmed, $isBonusGuild, $isOfficer) = set_session_rights_for_guild($guild_id);

//Get TB infos
// Prepare the SQL query
$query = "SELECT guild_id, tb_id";
$query .= " FROM tb_history";
$query .= " WHERE tb_history.id=".$tb_id;
//error_log("query = ".$query);
try {
    // Prepare the SQL query
    $stmt = $conn_guionbot->prepare($query);
    $stmt->execute();

    // Fetch all the results as an associative array
    $db_data = $stmt->fetchAll(PDO::FETCH_ASSOC);
    $tb_full_id = $db_data[0]['tb_id'];
    $guild_id = $db_data[0]['guild_id'];

} catch (PDOException $e) {
    error_log("Error fetching TB data: " . $e->getMessage());
    echo "Error fetching TB data: " . $e->getMessage();
    header("Location: index.php");
    exit();
}

// Get existing zone commands
$query = "SELECT zone_id, cmdMsg, cmdCmd";
$query .= " FROM tb_orders";
$query .= " WHERE guild_id='".$guild_id."'";
$query .= " AND tb_type=(SELECT SUBSTRING_INDEX(tb_id, ':', 1) FROM tb_history WHERE id=".$tb_id.")";
//error_log("query = ".$query);
$tb_orders = array();
try {
    // Prepare the SQL query
    $stmt = $conn_guionbot->prepare($query);
    $stmt->execute();

    // Fetch all the results as an associative array
    $db_orders = $stmt->fetchAll(PDO::FETCH_ASSOC);

    foreach($db_orders as $db_order) {
        $tb_orders[$db_order['zone_id']] = $db_order;
    }

} catch (PDOException $e) {
    error_log("Error fetching guild data: " . $e->getMessage());
    echo "Error fetching orders: " . $e->getMessage();
}

?>

<!DOCTYPE html>
<html>
<head>
    <title>GuiOn bot for SWGOH</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="stylesheet" href="basic.css">
    <link rel="stylesheet" href="navbar.css">
    <link rel="stylesheet" href="tables.css">
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

<?php display_tb_header($guild_id, $guild_name, $tb, $round, $zones, $isMyGuild, $isMyGuildConfirmed, $isOfficer, $isBonusGuild, $isAdmin); ?>

<?php include 'tbnavbar.php'; ?>

<?php
    $string = file_get_contents("../DATA/tb_definition.json");
    $dict_tb = json_decode($string, true);
    print_r('<br/>');
?>

<div id="resume" class="active">
    <div class="row">

<?php
function input_order($zone_id, $input_name, $tb_orders) {
    if (!isset($tb_orders[$zone_id])) {
        $tb_orders[$zone_id] = array();
        $tb_orders[$zone_id]['cmdMsg'] = '';
        $tb_orders[$zone_id]['cmdCmd'] = 1;
    }
        
    echo '<div id="input-'.$zone_id.'">';
    echo '<label for="msg-'.$zone_id.'" style="font-size:18px">'.$input_name.': </label>';
    echo '<input type="text" id="msg-'.$zone_id.'" style="width: 300px" maxlength="75" value="'.$tb_orders[$zone_id]['cmdMsg'].'"/>';
    echo '<br/>';
    echo '<input type="radio" name="radio-'.$zone_id.'" id="None-'.$zone_id.'" value="1" '.($tb_orders[$zone_id]['cmdCmd']==1?'checked':'').'/>';
    echo '<label for="None-'.$zone_id.'">None</label>';
    echo '<input type="radio" name="radio-'.$zone_id.'" id="Focus-'.$zone_id.'" value="2" '.($tb_orders[$zone_id]['cmdCmd']==2?'checked':'').'/>';
    echo '<label for="Focus-'.$zone_id.'">Focus</label>';
    echo '<input type="radio" name="radio-'.$zone_id.'" id="Forbidden-'.$zone_id.'" value="3" '.($tb_orders[$zone_id]['cmdCmd']==3?'checked':'').'/>';
    echo '<label for="Forbidden-'.$zone_id.'">Forbidden</label>';
    echo '</div>';
}
?>

<?php
    if (($isMyGuildConfirmed&$isOfficer)|$isAdmin) {
    if (!empty($zones)) {
        foreach ($zones as $zone) {
            $zone_id = $zone['zone_id'];
?>
                <div class="col s12 m12 l4">
                    <div class="valign-wrapper full-line">
                    <h4><?php echo $zone['zone_name'].' - <small>'.$dict_tb[$zone_id]['fullname']?></small></h4>
                    </div>
                    <div class="card zone">
                        <form target="_blank" onSubmit="tbmsg_send(event);">
                            <?php input_order($zone_id, 'Deployment', $tb_orders); ?>
                            <br/>
                            <?php input_order($zone_id.'_recon01', 'Platoons', $tb_orders); ?>
<?php
            $n_strike=1;
            foreach ($dict_tb[$zone_id]['strikes'] as $strike_id => $strike) {
                            echo '<br/>';
                            input_order($zone_id.'_'.$strike_id, 'Strike#'.$n_strike.($strike[2]=='COMBAT_SHIP'?'&#x2708;':'&#x1fa96;'), $tb_orders);
                            $n_strike+=1;
            }
            $n_covert=1;
            foreach ($dict_tb[$zone_id]['coverts'] as $covert_id => $covert) {
                            echo '<br/>';
                            input_order($zone_id.'_'.$covert_id, 'Special#'.$n_covert, $tb_orders);
                            $n_covert+=1;
            }
?>
                            <br/>
                            <input type="submit" id="btn-<?php echo $zone_id; ?>" value="Send"/>
            
                        </form>
                    </div>
                </div>



<?php
        }
    } // empty zones
    } else { //not guild officer
        echo "You need to be an officer of the guild";
    }

?>
    </div>
</div>

    </div> <!-- container -->
    </div> <!-- site-content -->
    <div class="site-cache" id="site-cache" onclick="document.body.classList.toggle('with--sidebar')"></div>
</div>
</div>
</body>
<?php include 'sitefooter.php' ; ?>
</html>

<script>

function tbmsg_send (e) {
    e.preventDefault();
    origin_form = e.srcElement;
    let cmd_list = origin_form.getElementsByTagName('div');

    list_orders = [];
    var btn_id;
    for(let i=0;i<cmd_list.length;i++){
        cmd = cmd_list[i];
        let zone_id = cmd.getAttribute('id').split('-')[1];
        if (i==0) {
            btn_id = 'btn-'+zone_id;
            document.getElementById(btn_id).disabled=true;
        }
        let msg_id = 'msg-'+zone_id;
        let msg = document.getElementById(msg_id).value;
        let radio_name = 'radio-'+zone_id;
        let radio_selection = document.querySelector('input[name="'+radio_name+'"]:checked')
        if (radio_selection==null) {
            radio_value=1;
        } else {
            radio_value=radio_selection.value;
        }

        my_order = {
            zone_id: zone_id,
            zone_msg: msg,
            zone_cmd: radio_value
        };

        list_orders.push(my_order);

    };
    //console.log(list_orders);

    setTimeout(send_order.bind(null, btn_id, list_orders), 10*list_orders.length);

    return false;
}

function send_order(btn_id, list_orders) {
    var body_json = {
        guild_id: '<?php echo $guild_id; ?>',
        tb_id: '<?php echo $tb_full_id; ?>',
        list_orders: list_orders
    };
    var err_code=0;
    var err_txt="";
    return fetch("/tbzmsg.php", {
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

        document.getElementById(btn_id).disabled = false;
        if (err_code==0) {
            window.alert("Orders correcty sent to the game");
        } else {
            window.alert("ERROR: "+err_txt);
        }
    });
}

</script>

