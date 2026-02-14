<?php
require_once(__DIR__ . '/../config.php');

// Enable error reporting
error_reporting(E_ALL);
ini_set('display_errors', 1);

echo "Testing save_phones logic...\n";

$conn = db_connect();
if (!$conn) {
    die("DB Connection Failed\n");
}

// 1. 유효한 site_id 가져오기
$site_query = "SELECT site_id, site_name FROM monitor_sites LIMIT 1";
$site_result = sql_query($site_query);

if ($site_result) {
    $site_id = $site_result['site_id'];
    $site_name_db = $site_result['site_name'];
    echo "Found valid site_id: $site_id ($site_name_db)\n";
} else {
    // 사이트가 없으면 테스트용 사이트 생성
    echo "No sites found. Creating test site...\n";
    $insert_site = "INSERT INTO monitor_sites (site_name, site_url, check_interval, is_active) VALUES ('Test Site For Phone', 'http://test-phone.com', 60, 1)";
    if (sql_exec($insert_site)) {
        $site_id = sql_insert_id();
        echo "Created test site with ID: $site_id\n";
    } else {
        die("Failed to create test site. Cannot proceed.\n");
    }
}

$staff_name = "부천 에이전시";
$phone_number = "010-8173-6996";

// 1. Regex Check
$pattern = '/^0\d{1,2}-\d{3,4}-\d{4}$/';
if (preg_match($pattern, $phone_number)) {
    echo "Regex Match: SUCCESS\n";
} else {
    echo "Regex Match: FAILED for $phone_number\n";
}

// 2. Manual Insert Test
$staff_name_esc = mysqli_real_escape_string($conn, $staff_name);
$phone_number_esc = mysqli_real_escape_string($conn, $phone_number);

$query = "INSERT INTO staff_phones 
          (site_id, staff_name, phone_number, extracted_at, updated_at)
          VALUES 
          ($site_id, '$staff_name_esc', '$phone_number_esc', NOW(), NOW())
          ON DUPLICATE KEY UPDATE 
          phone_number = '$phone_number_esc',
          updated_at = NOW()";

echo "Query: $query\n";

if (sql_exec($query)) {
    echo "Insert/Update: SUCCESS\n";
    echo "Insert ID: " . sql_insert_id() . "\n";
} else {
    echo "Insert/Update: FAILED\n";
    echo "Error: " . mysqli_error($conn) . "\n";
}

// 3. Check Table Schema
echo "\nChecking table schema...\n";
$result = sql_query("DESCRIBE staff_phones");
while ($row = mysqli_fetch_assoc($result)) {
    echo $row['Field'] . " - " . $row['Type'] . "\n";
}

?>

