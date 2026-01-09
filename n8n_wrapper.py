#!/usr/bin/env python3
from flask import Flask, request, jsonify
import os, sys, json

# This allows Render to read your Google Key from a secure variable
GOOGLE_CREDENTIALS = os.environ.get('GOOGLE_CREDENTIALS_JSON')

app = Flask(__name__)

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy'})

@app.route('/scrape', methods=['POST'])
def scrape():
    from multi_source_scraper_dynamic import DynamicCriteriaReader, MultiSourceScraper
    
    data = request.get_json(force=True)
    youtube_api_key = data.get('youtube_api_key')
    sheet_id = '1wWp9gLifWCeXKs3LHWW_IvtxtmkyPDcOekcYNs4wRPY'

    # Create a temporary file for the credentials
    with open('temp_key.json', 'w') as f:
        f.write(GOOGLE_CREDENTIALS)

    try:
        reader = DynamicCriteriaReader(sheet_id, 'temp_key.json')
        settings = reader.read_settings_tab()
        criteria = reader.parse_criteria(settings)

        scraper = MultiSourceScraper(criteria)
        results = scraper.scrape_youtube(youtube_api_key)

        return jsonify({
            'status': 'success',
            'total_strategies': len(results),
            'strategies': results
        })
    finally:
        if os.path.exists('temp_key.json'):
            os.remove('temp_key.json')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
