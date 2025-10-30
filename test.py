import os
import requests

solana_key = os.getenv('SOLANA_TRACKER_API_KEY', '')
helius_key = os.getenv('HELIUS_API_KEY', '')

print("="*70)
print("TESTING API KEYS")
print("="*70)
print(f"SOLANA_TRACKER_API_KEY: {'SET' if solana_key else 'MISSING'}")
print(f"HELIUS_API_KEY: {'SET' if helius_key else 'MISSING'}")

if solana_key:
    print(f"Key preview: {solana_key[:15]}...")
    
    # Test 1: Search for tokens
    print("\nTest 1: Searching for trending tokens...")
    url = "https://data.solanatracker.io/search"
    headers = {'x-api-key': solana_key}
    params = {'sortBy': 'volume_24h', 'sortOrder': 'desc', 'limit': 5}
    
    response = requests.get(url, headers=headers, params=params, timeout=20)
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        tokens = data.get('data', [])
        print(f"✓ Found {len(tokens)} tokens")
        if tokens:
            token = tokens[0]
            print(f"  Example: {token.get('symbol')} - ${token.get('volume_24h', 0):,.0f} volume")
            
            # Test 2: Get top traders for this token
            token_address = token.get('mint')
            if token_address:
                print(f"\nTest 2: Getting top traders for {token.get('symbol')}...")
                url2 = f"https://data.solanatracker.io/tokens/{token_address}/top-traders"
                response2 = requests.get(url2, headers=headers, timeout=20)
                print(f"Status: {response2.status_code}")
                
                if response2.status_code == 200:
                    traders_data = response2.json()
                    traders = traders_data.get('data', []) if isinstance(traders_data, dict) else traders_data
                    print(f"✓ Found {len(traders)} top traders")
                else:
                    print(f"✗ Error: {response2.text[:200]}")
    else:
        print(f"✗ Error: {response.text[:200]}")

if helius_key:
    print(f"\nTest 3: Testing Helius API...")
    # Test with a known wallet
    test_wallet = "6VbvSP1F3HBECMbQjhXxKKUxmE4CWhGWxSY5f5q8Qhqj"
    url = f"https://api.helius.xyz/v0/addresses/{test_wallet}/balances"
    params = {'api-key': helius_key}
    
    response = requests.get(url, params=params, timeout=15)
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        tokens = data.get('tokens', [])
        print(f"✓ Helius API works - found {len(tokens)} tokens in test wallet")
    else:
        print(f"✗ Error: {response.status_code}")

print("\n" + "="*70)
