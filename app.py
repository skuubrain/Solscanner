from flask import Flask, render_template, jsonify, request
from solana_tracker import WalletTracker
from apscheduler.schedulers.background import BackgroundScheduler
import os
import atexit
import sys

app = Flask(__name__)
tracker = WalletTracker()

# Force output to flush immediately
sys.stdout.flush()

scheduler = None

def init_scheduler():
    global scheduler
    if scheduler is None and os.environ.get('SCHEDULER_ENABLED', 'true').lower() == 'true':
        scheduler = BackgroundScheduler()
        scheduler.start()
        atexit.register(lambda: scheduler.shutdown())

        def scheduled_scan():
            with app.app_context():
                print("Running scheduled top trader scan...", flush=True)
                try:
                    flagged = tracker.scan_top_traders(num_traders=50, min_buyers=2)
                    print(f"Scan complete. Found {len(flagged)} flagged tokens.", flush=True)
                except Exception as e:
                    print(f"Error during scheduled scan: {e}", flush=True)

        scheduler.add_job(func=scheduled_scan, trigger="interval", minutes=30)
        print("Scheduler initialized and started.", flush=True)

init_scheduler()

@app.route('/')
def index():
    print("==> Homepage accessed", flush=True)
    return render_template('index.html')

@app.route('/api/wallets', methods=['GET'])
def get_wallets():
    print("==> API: Get wallets called", flush=True)
    wallets = tracker.get_tracked_wallets()
    print(f"==> Returning {len(wallets)} wallets", flush=True)
    return jsonify({
        'wallets': wallets,
        'count': len(wallets)
    })

@app.route('/api/scan', methods=['POST'])
def scan_wallets():
    print("\n" + "="*70, flush=True)
    print("==> API: SCAN ENDPOINT CALLED", flush=True)
    print("="*70, flush=True)
    
    # Check API keys
    solana_key = os.getenv('SOLANA_TRACKER_API_KEY', '')
    helius_key = os.getenv('HELIUS_API_KEY', '')
    
    print(f"==> SOLANA_TRACKER_API_KEY: {'SET ✓' if solana_key else 'MISSING ✗'}", flush=True)
    print(f"==> HELIUS_API_KEY: {'SET ✓' if helius_key else 'MISSING ✗'}", flush=True)
    
    if not solana_key:
        error_msg = "SOLANA_TRACKER_API_KEY is not set in environment variables"
        print(f"==> ERROR: {error_msg}", flush=True)
        return jsonify({'error': error_msg}), 500
    
    try:
        data = request.get_json() or {}
        num_traders = data.get('num_traders', 50)
        min_buyers = data.get('min_buyers', 2)
        
        print(f"==> Scan parameters: {num_traders} traders, min {min_buyers} buyers", flush=True)
        print(f"==> Starting scan...", flush=True)
        
        flagged_tokens = tracker.scan_top_traders(num_traders=num_traders, min_buyers=min_buyers)
        
        print(f"==> Scan completed successfully", flush=True)
        print(f"==> Found {len(flagged_tokens)} flagged tokens", flush=True)
        
        return jsonify({
            'flagged_tokens': flagged_tokens,
            'count': len(flagged_tokens),
            'scanned_wallets': len(tracker.get_tracked_wallets())
        })
    except Exception as e:
        print(f"==> ERROR in scan endpoint: {e}", flush=True)
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/tokens/flagged', methods=['GET'])
def get_flagged_tokens():
    print("==> API: Get flagged tokens called", flush=True)
    tokens = tracker.get_flagged_tokens()
    print(f"==> Returning {len(tokens)} flagged tokens", flush=True)
    return jsonify({
        'tokens': tokens,
        'count': len(tokens)
    })

@app.route('/api/health', methods=['GET'])
def health_check():
    solana_key = os.getenv('SOLANA_TRACKER_API_KEY', '')
    helius_key = os.getenv('HELIUS_API_KEY', '')
    
    return jsonify({
        'status': 'healthy',
        'tracked_wallets': len(tracker.get_tracked_wallets()),
        'flagged_tokens': len(tracker.get_flagged_tokens()),
        'api_keys': {
            'solana_tracker': 'configured' if solana_key else 'missing',
            'helius': 'configured' if helius_key else 'missing'
        }
    })

@app.route('/api/test', methods=['GET'])
def test_api():
    """Test endpoint to verify API keys work"""
    print("\n==> TEST ENDPOINT CALLED", flush=True)
    
    solana_key = os.getenv('SOLANA_TRACKER_API_KEY', '')
    
    if not solana_key:
        return jsonify({
            'success': False,
            'error': 'SOLANA_TRACKER_API_KEY not set'
        })
    
    # Try to fetch top traders
    try:
        import requests
        url = "https://data.solanatracker.io/top-traders"
        headers = {'x-api-key': solana_key}
        params = {'page': 1, 'sortBy': 'total', 'onlyRealized': False}
        
        print(f"==> Testing API call to: {url}", flush=True)
        response = requests.get(url, headers=headers, params=params, timeout=15)
        
        print(f"==> Response status: {response.status_code}", flush=True)
        
        if response.status_code == 200:
            data = response.json()
            traders_count = len(data.get('data', []) or data if isinstance(data, list) else [])
            return jsonify({
                'success': True,
                'message': f'API key works! Found {traders_count} top traders',
                'status_code': response.status_code
            })
        else:
            return jsonify({
                'success': False,
                'error': f'API returned status {response.status_code}',
                'response': response.text[:500]
            })
            
    except Exception as e:
        print(f"==> Error testing API: {e}", flush=True)
        return jsonify({
            'success': False,
            'error': str(e)
        })

if __name__ == '__main__':
    print("\n" + "="*70, flush=True)
    print("STARTING SOLANA TOP TRADER SCANNER", flush=True)
    print("="*70, flush=True)
    
    solana_key = os.getenv('SOLANA_TRACKER_API_KEY', '')
    helius_key = os.getenv('HELIUS_API_KEY', '')
    
    print(f"Environment Check:", flush=True)
    print(f"  SOLANA_TRACKER_API_KEY: {'SET ✓' if solana_key else 'MISSING ✗'}", flush=True)
    print(f"  HELIUS_API_KEY: {'SET ✓' if helius_key else 'MISSING ✗'}", flush=True)
    
    if solana_key:
        print(f"  API Key Preview: {solana_key[:10]}...", flush=True)
    
    print("="*70 + "\n", flush=True)
    
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
