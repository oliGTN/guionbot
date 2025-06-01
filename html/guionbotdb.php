<?php
$host = 'localhost'; // Or the appropriate host for your database
$dbname = 'guionbotdb';
include 'websitedb_secret.php'; // defines $username and $password

try {
    // Create a PDO connection to guionbotdb
    $conn_guionbot = new PDO("mysql:host=$host;dbname=$dbname", $username, $password);
    // Set the PDO error mode to exception
    $conn_guionbot->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
} catch (PDOException $e) {
    echo "Connection failed: " . $e->getMessage();
}
?>
