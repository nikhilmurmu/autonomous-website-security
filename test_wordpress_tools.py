from tools.wordpress_tools import wp_plugin_update_tool, wp_add_security_headers_tool

client_id = "autosec-test"

print("\n=== Testing WordPress Tools ===\n")

# First install a test plugin (optional, but recommended)
import subprocess
import os
env = os.environ.copy()
env["PATH"] = r"C:\Users\nikhi\AppData\Roaming\Local\lightning-services\mysql-8.0.35+4\bin\win64\bin;" + env["PATH"]
subprocess.run([
    r"C:\Users\nikhi\AppData\Roaming\Local\lightning-services\php-8.2.29+0\bin\win64\php.exe",
    r"C:\Users\nikhi\autonomous-website-security\wp-cli.phar",
    r"--path=C:\Users\nikhi\Local Sites\autosec-test\app\public",
    "plugin", "install", "hello-dolly", "--activate"
], env=env)

print("\nUpdating Hello Dolly plugin...")
update_result = wp_plugin_update_tool.run(client_id=client_id, plugin_slug="hello-dolly")
print(update_result)

print("\nAdding security headers...")
headers_result = wp_add_security_headers_tool.run(client_id=client_id)
print(headers_result)

print("\n=== All tests complete ===")