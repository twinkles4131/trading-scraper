#!/usr/bin/env python3
from flask import Flask, request, jsonify
import os, sys

BASE_DIR = os.path.expanduser(
    '~/Library/Mobile Documents/com~apple~CloudDocs/Desktop/trading strategies n8n'
)
sys.path.insert(0, BASE_DIR)

from multi_source_scraper_dynamic import DynamicCriteriaReader, MultiSourceScraper

SHEET_ID = '1wWp9gLifWCeXKs3LHWW_IvtxtmkyPDcOekcYNs4wRPY'
SERVICE_ACCOUNT = os.path.join(
    BASE_DIR,
    'trading-strategy-scrapper-f6d261f30304 (service key).json'
)

app = Flask(__name__)

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy'})

@app.route('/scrape', methods=['POST'])
def scrape():
    data = request.get_json(force=True)
    youtube_api_key = data.get('youtube_api_key')

    reader = DynamicCriteriaReader(SHEET_ID, SERVICE_ACCOUNT)
    settings = reader.read_settings_tab()
    criteria = reader.parse_criteria(settings)

    scraper = MultiSourceScraper(criteria)
    results = scraper.scrape_youtube(youtube_api_key)

    return jsonify({
        'status': 'success',
        'total_strategies': len(results),
        'strategies': results
    })

if __name__ == '__main__':
    print("Server running on http://0.0.0.0:5000")
    app.run(host='0.0.0.0', port=5000)
