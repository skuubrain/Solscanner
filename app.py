from flask import Flask, render_template, jsonify, request
from solana_tracker import WalletTracker
from apscheduler.schedulers.background import BackgroundScheduler
import os
import atexit

app = Flask(__name__)
tracker = WalletTracker()

scheduler = None

def init_scheduler():
    global scheduler
    if scheduler is None and os.environ.get('SCHEDULER_ENABLED', 'true').lower() == 'true':
        scheduler = BackgroundScheduler()
        scheduler.start()
        atexit.register(lambda: scheduler.shutdown())
        
        def scheduled_scan():
            with app.app_context():
                print("Running scheduled wallet scan...")
                try:
                    tracker.scan_trending_wallets()
                    print(f"Scan complete. Tracking {len(tracker.get_tracked_wallets())} wallets.")
                except Exception as e:
                    print(f"Error during scheduled scan: {e}")
        
        scheduler.add_job(func=scheduled_scan, trigger="interval", minutes=15)
        print("Scheduler initialized and started.")

init_scheduler()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/wallets', methods=['GET'])
def get_wallets():
    wallets = tracker.get_tracked_wallets()
    return jsonify({
        'wallets': wallets,
        'count': len(wallets)
    })

@app.route('/api/track', methods=['POST'])
def track_wallet():
    data = request.get_json()
    wallet_address = data.get('wallet_address')
    
    if not wallet_address:
        return jsonify({'error': 'Wallet address is required'}), 400
    
    try:
        wallet_data = tracker.track_wallet(wallet_address)
        return jsonify(wallet_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/scan', methods=['POST'])
def scan_wallets():
    try:
        scanned = tracker.scan_trending_wallets()
        return jsonify({
            'scanned_wallets': scanned,
            'count': len(scanned)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/tokens/flagged', methods=['GET'])
def get_flagged_tokens():
    tokens = tracker.get_flagged_tokens()
    return jsonify({
        'tokens': tokens,
        'count': len(tokens)
    })

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'healthy',
        'tracked_wallets': len(tracker.get_tracked_wallets()),
        'flagged_tokens': len(tracker.get_flagged_tokens())
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
