<?php
require_once(__DIR__ . '/../config.php');
check_admin_access();

$query = "SELECT s.*, 
                 (SELECT MAX(detected_at) FROM monitor_changes WHERE site_id = s.site_id) as last_change_time
          FROM monitor_sites s 
          ORDER BY s.created_at DESC";
$sites = sql_fetch($query);

json_response(true, '', $sites);
?>


