import fastProxy
import os

print("[TEST] Testing with minimal parameters...")
proxies1 = fastProxy.fetch_proxies(c=4, t=5)
print(f"[TEST] Found {len(proxies1)} proxies with minimal params")

print("\n[TEST] Testing with all features enabled...")
proxies2 = fastProxy.fetch_proxies(c=4, t=5, g=True, a=True)
print(f"[TEST] Found {len(proxies2)} proxies with all features")

# Check if CSV was generated
if os.path.exists('proxy_list/working_proxies.csv'):
    print("\n[TEST] CSV file generated successfully")
    with open('proxy_list/working_proxies.csv', 'r') as f:
        lines = f.readlines()
        print(f"[TEST] CSV contains {len(lines)-1} proxies")
