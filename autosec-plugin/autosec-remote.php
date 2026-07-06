<?php
/**
 * Plugin Name: AutoSec Remote Fix
 * Description: Secure REST API endpoint for AutoSec AI to fix security issues remotely.
 * Version: 1.0
 * Author: Nikhil Murmu
 */

// Prevent direct access
if (!defined('ABSPATH')) exit;

// =============================================================================
// 1. Admin settings page (where the client enters their AutoSec API key)
// =============================================================================
add_action('admin_menu', 'autosec_add_admin_page');
function autosec_add_admin_page() {
    add_options_page(
        'AutoSec Remote',
        'AutoSec Remote',
        'manage_options',
        'autosec-remote',
        'autosec_admin_page_html'
    );
}

function autosec_admin_page_html() {
    if (isset($_POST['autosec_api_key'])) {
        update_option('autosec_api_key', sanitize_text_field($_POST['autosec_api_key']));
        echo '<div class="notice notice-success"><p>API key saved.</p></div>';
    }
    $api_key = get_option('autosec_api_key', '');
    ?>
    <div class="wrap">
        <h1>AutoSec Remote Fix</h1>
        <p>Enter your AutoSec API key to allow secure remote fixes.</p>
        <form method="post">
            <label>AutoSec API Key</label>
            <input type="text" name="autosec_api_key" value="<?php echo esc_attr($api_key); ?>" style="width: 400px;" />
            <?php submit_button('Save'); ?>
        </form>
    </div>
    <?php
}

// =============================================================================
// 2. Register the REST API endpoint
// =============================================================================
add_action('rest_api_init', 'autosec_register_routes');
function autosec_register_routes() {
    register_rest_route('autosec/v1', '/fix', array(
        'methods' => 'POST',
        'callback' => 'autosec_handle_fix',
        'permission_callback' => 'autosec_check_permission'
    ));
}

// =============================================================================
// 3. Security: verify the request signature (HMAC with API key)
// =============================================================================
function autosec_check_permission($request) {
    $api_key = get_option('autosec_api_key', '');
    if (empty($api_key)) return new WP_Error('not_configured', 'API key not set', array('status' => 401));

    $sent_signature = $request->get_header('X-Autosec-Signature');
    if (empty($sent_signature)) return new WP_Error('missing_signature', 'Signature missing', array('status' => 401));

    $body = $request->get_body();
    $expected = hash_hmac('sha256', $body, $api_key);

    if (!hash_equals($expected, $sent_signature)) {
        return new WP_Error('invalid_signature', 'Invalid signature', array('status' => 403));
    }
    return true;
}

// =============================================================================
// 4. Action dispatcher – runs the requested fix
// =============================================================================
function autosec_handle_fix($request) {
    $params = $request->get_json_params();
    $action = $params['action'] ?? '';

    switch ($action) {
        case 'add_headers':
            return autosec_add_security_headers();
        case 'update_plugin':
            return autosec_update_plugin($params['plugin_slug'] ?? '');
        case 'backup_db':
            return autosec_backup_database();
        default:
            return new WP_Error('unknown_action', 'Unknown action', array('status' => 400));
    }
}

// =============================================================================
// 5. Individual fix functions
// =============================================================================

function autosec_add_security_headers() {
    // Write headers to .htaccess
    $htaccess = ABSPATH . '.htaccess';
    $headers = "\n# Added by AutoSec AI\n<IfModule mod_headers.c>\n";
    $headers .= 'Header always set Strict-Transport-Security "max-age=31536000; includeSubDomains"' . "\n";
    $headers .= 'Header always set Content-Security-Policy "default-src \'self\'"' . "\n";
    $headers .= 'Header always set X-Frame-Options "SAMEORIGIN"' . "\n";
    $headers .= 'Header always set X-Content-Type-Options "nosniff"' . "\n";
    $headers .= 'Header always set Referrer-Policy "strict-origin-when-cross-origin"' . "\n";
    $headers .= 'Header always set Permissions-Policy "geolocation=(), microphone=(), camera=()"' . "\n";
    $headers .= "</IfModule>\n";

    if (file_put_contents($htaccess, $headers, FILE_APPEND | LOCK_EX)) {
        return array('status' => 'success', 'message' => 'Security headers added');
    }
    return new WP_Error('write_failed', 'Could not write to .htaccess', array('status' => 500));
}

function autosec_update_plugin($slug) {
    if (empty($slug)) return new WP_Error('missing_slug', 'Plugin slug required', array('status' => 400));

    if (!function_exists('get_plugins')) require_once ABSPATH . 'wp-admin/includes/plugin.php';
    $plugins = get_plugins();
    $file = '';
    foreach ($plugins as $path => $data) {
        if (strpos($path, $slug . '/') === 0 || strpos($path, $slug . '.php') !== false) {
            $file = $path;
            break;
        }
    }

    if (!$file) return new WP_Error('not_found', 'Plugin not found', array('status' => 404));

    include_once ABSPATH . 'wp-admin/includes/class-wp-upgrader.php';
    include_once ABSPATH . 'wp-admin/includes/plugin-install.php';

    $upgrader = new Plugin_Upgrader(new Automatic_Upgrader_Skin());
    $result = $upgrader->upgrade($file);

    if (is_wp_error($result)) return $result;
    return array('status' => 'success', 'message' => "Plugin $slug updated");
}

function autosec_backup_database() {
    global $wpdb;
    $tables = $wpdb->get_results("SHOW TABLES", ARRAY_N);
    $dump = '';
    foreach ($tables as $table) {
        $table_name = $table[0];
        $rows = $wpdb->get_results("SELECT * FROM `$table_name`", ARRAY_A);
        if (!empty($rows)) {
            $dump .= "DROP TABLE IF EXISTS `$table_name`;\n";
            $row2 = $wpdb->get_row("SHOW CREATE TABLE `$table_name`", ARRAY_N);
            $dump .= $row2[1] . ";\n";
            foreach ($rows as $row) {
                $values = array_map(function($val) use ($wpdb) { return $wpdb->prepare('%s', $val); }, $row);
                $dump .= "INSERT INTO `$table_name` VALUES (" . implode(',', $values) . ");\n";
            }
        }
    }

    $backup_dir = WP_CONTENT_DIR . '/autosec-backups';
    if (!file_exists($backup_dir)) mkdir($backup_dir, 0755, true);
    $filename = $backup_dir . '/backup-' . current_time('mysql') . '.sql';
    file_put_contents($filename, $dump);

    return array('status' => 'success', 'file' => $filename);
}