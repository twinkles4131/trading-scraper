#!/usr/bin/env python3
from flask import Flask, request, jsonify
import os
import traceback
from multi_source_scraper_dynamic import MultiSourceScraper  # Only import the scraper class

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

        # Debug prints to confirm data arrives correctly
        print("DEBUG: Received criteria keys:", list(criteria.keys()))
        print("DEBUG: Min CAGR (%):", criteria.get("Min CAGR (%)"))
        print("DEBUG: Keywords preview:", criteria.get("Keywords", "")[:150])

        # Create the scraper with the criteria received from n8n
        scraper = MultiSourceScraper(criteria)
        results = scraper.run_all(youtube_api_key)

        return jsonify({
            'status': 'success',
            'total_strategies': len(results),
            'strategies': results
        })

    except Exception as e:
        error_msg = traceback.format_exc()
        print("CRITICAL ERROR in /scrape:", error_msg)
        return jsonify({
            'status': 'error',
            'message': str(e),
            'traceback': error_msg  # For debugging; remove in production
        }), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
