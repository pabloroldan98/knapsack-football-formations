<?php
/**
 * Test IONOS MySQL connection via PDO.
 * Upload this + config.php to IONOS hosting and open in browser to verify.
 */
require_once __DIR__ . '/config.php';

try {
    $dsn = 'mysql:host=' . DB_HOST . ';port=' . DB_PORT . ';dbname=' . DB_NAME . ';charset=utf8mb4';
    $pdo = new PDO($dsn, DB_USER, DB_PASS, [
        PDO::ATTR_ERRMODE            => PDO::ERRMODE_EXCEPTION,
        PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
        PDO::ATTR_EMULATE_PREPARES   => false,
    ]);
    echo '<p style="color:green;">Conexion OK — servidor: ' . $pdo->getAttribute(PDO::ATTR_SERVER_VERSION) . '</p>';
} catch (PDOException $e) {
    echo '<p style="color:red;">Error: ' . htmlspecialchars($e->getMessage()) . '</p>';
}
