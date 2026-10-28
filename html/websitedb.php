<?php
$host = 'localhost';
$dbname = 'websitedb';
include '/home/pi/GuionBot/SERVER_SECRETS/websitedb_secret.php';

try {
    $conn = new PDO("mysql:host=$host;dbname=$dbname", $username, $password);
    $conn->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
} catch (PDOException $e) {
    die("Connection failed: " . $e->getMessage());
}
?>
