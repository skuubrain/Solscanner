from flask import Flask, render_template, jsonify, request
from solana_tracker import WalletTracker
import os
import sys

app = Flask(__name__)
tracker = WalletTracker()

sys.stdout.flush()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/scan', methods=['POST'])
def scan_wallets():
    print("\n" + "="*70, flush=True)
    print("==> SCAN STARTED", flush=True)
    print("="*70, flush=True)
    
    solana_key = os.getenv('SOLANA_TRACKER_API_KEY', '')
    
    if not solana_key:
        return jsonify({'error': 'SOLANA_TRACKER_API_KEY not set'}), 500
    
    try:
        data = request.get_json() or {}
        num_tokens = data.get('num_tokens', 10)
        traders_per_token = data.get('traders_per_token', 10)
        min_buyers = data.get('min_buyers', 2)
        
        flagged_tokens = tracker.scan_trending_tokens(
            num_tokens=num_tokens,
            traders_per_token=traders_per_token,
            min_buyers=min_buyers
        )
        
        return jsonify({
            'flagged_tokens': flagged_tokens,
            'count': len(flagged_tokens)
        })
    except Exception as e:
        print(f"==> ERROR: {e}", flush=True)
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/wallets', methods=['GET'])
def get_wallets():
    return jsonify({
        'wallets': tracker.get_tracked_wallets(),
        'count': len(tracker.get_tracked_wallets())
    })

@app.route('/api/tokens/flagged', methods=['GET'])
def get_flagged_tokens():
    return jsonify({
        'tokens': tracker.get_flagged_tokens(),
        'count': len(tracker.get_flagged_tokens())
    })

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'healthy',
        'api_key': 'configured' if os.getenv('SOLANA_TRACKER_API_KEY') else 'missing'
    })

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
