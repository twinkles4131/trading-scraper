#!/usr/bin/env python3
from flask import Flask, request, jsonify
import os
from multi_source_scraper_dynamic import MultiSourceScraper  # only this import needed now

app = Flask(__name__)

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy'})

@app.route('/scrape', methods=['POST'])
def scrape():
    try:
        data = request.get_json(force=True)
        if not data:
            return jsonify({'status': 'error', 'message': 'No JSON body received'}), 400

        youtube_api_key = data.get('youtube_api_key')
        criteria = data.get('criteria', {})

        if not youtube_api_key:
            return jsonify({'status': 'error', 'message': 'youtube_api_key is required'}), 400

        print("DEBUG: Received criteria keys:", list(criteria.keys()))
        print("DEBUG: YouTube Enabled:", criteria.get('YouTube Enabled'))
        print("DEBUG: Keywords preview:", criteria.get('Keywords', '')[:100])

        # Instantiate and run the scraper with the received criteria
        scraper = MultiSourceScraper(criteria)
        results = scraper.run_all(youtube_api_key)

        return jsonify({
            'status': 'success',
            'total_strategies': len(results),
            'strategies': results
        })

    except Exception as e:
        import traceback
        error_msg = traceback.format_exc()
        print("CRITICAL ERROR in /scrape:", error_msg)
        return jsonify({
            'status': 'error',
            'message': str(e),
            'traceback': error_msg  # only for dev; remove in production if security concern
        }), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
