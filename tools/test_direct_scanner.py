from tools.scanner_direct import scan_website_direct, generate_scan_summary
import json

# Scan a test website
result = scan_website_direct("https://example.com")

# Print raw JSON
print("\n" + "="*50)
print("RAW JSON OUTPUT:")
print(json.dumps(result, indent=2))

# Print summary
print("\n" + "="*50)
print("HUMAN-READABLE SUMMARY:")
print(generate_scan_summary(result))