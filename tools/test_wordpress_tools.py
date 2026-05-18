from tools.wordpress_tools import wp_backup_tool, wp_add_security_headers_tool

client_id = "autosec-test"

print("\n=== Testing WordPress Tools ===\n")

print("Creating backup...")
backup_result = wp_backup_tool.run(client_id=client_id)
print(backup_result)

print("\nAdding security headers...")
headers_result = wp_add_security_headers_tool.run(client_id=client_id)
print(headers_result)

print("\n=== All tests complete ===")