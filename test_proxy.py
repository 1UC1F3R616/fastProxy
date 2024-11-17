import fastProxy

print("[TEST] Testing with minimal parameters...")
proxies1 = fastProxy.fetch_proxies(c=4, t=2)
print(f"[TEST] Found {len(proxies1)} proxies with minimal params")

print("\n[TEST] Testing with all features enabled...")
proxies2 = fastProxy.fetch_proxies(c=8, t=3, g=True, a=True)
print(f"[TEST] Found {len(proxies2)} proxies with all features")
