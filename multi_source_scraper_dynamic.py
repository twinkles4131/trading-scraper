import os
import json
import traceback
from flask import Flask, request, jsonify
from googleapiclient.discovery import build
from youtube_transcript_api import YouTubeTranscriptApi
from openai import OpenAI
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)

class MultiSourceScraper:
    def __init__(self, criteria):
        self.criteria = criteria
        # Modern OpenAI initialization (NO 'proxies' keyword)
       import httpx  # Add this import at the top of the file if not already there

import httpx  # Add this import at the top of the file if not already there

self.client = OpenAI(
    api_key=os.environ.get("OPENAI_API_KEY"),
    http_client=httpx.Client(
        timeout=60.0,  # Increase if API calls are slow
        follow_redirects=True
    )
)
    http_client=httpx.Client(
        timeout=60.0,  # Increase if API calls are slow
        follow_redirects=True
    )
)
        # Debug: Confirm API key loaded
        print("DEBUG: OpenAI client initialized with key:", bool(os.environ.get("OPENAI_API_KEY")))

    def get_transcript(self, video_id):
        try:
            transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
            text = " ".join([t['text'] for t in transcript_list])
            print(f"DEBUG: Successfully got transcript for {video_id} ({len(text)} chars)")
            return text
        except Exception as e:
            print(f"DEBUG: Transcript error for {video_id}: {e}")
            return None

    def extract_full_details(self, text, title, source):
        prompt = f"""
        You are an expert Quant Trader. Analyze this {source} content for a trading strategy.
        GOAL: Determine if this is a high-quality, profitable trading strategy.
        EXTRACT: Strategy Name, Market Regime, Entry Rules, Exit Rules, Win Rate (%), CAGR (%), Max Drawdown (%), Sharpe Ratio.
        Title: {title}
        Content: {text[:7000]}
        Return ONLY a JSON object with keys: name, regime, entry, exit, win, cagr, drawdown, sharpe, quality_score, description.
        If a value is unknown, use "Not mentioned".
        """
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a professional trading analyst. Always return JSON."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"}
            )
            data = json.loads(response.choices[0].message.content)
            print(f"DEBUG: AI Analysis for '{title}': {data}")
            return data
        except Exception as e:
            print(f"DEBUG: AI Error for '{title}': {e}")
            return None

    def scrape_youtube(self, api_key):
        if not self.criteria.get('YouTube Enabled', True):
            print("DEBUG: YouTube disabled")
            return []

        youtube = build('youtube', 'v3', developerKey=api_key)
        results = []
        keywords = self.criteria.get('Keywords', 'trading strategy').split(',')

        for query in keywords:
            clean_query = query.strip()
            print(f"DEBUG: Searching YouTube for: '{clean_query}'")
            try:
                request = youtube.search().list(
                    q=clean_query,
                    part='snippet',
                    maxResults=3,
                    type='video',
                    relevanceLanguage=self.criteria.get('YouTube Language', 'en')
                )
                response = request.execute()

                for item in response.get('items', []):
                    video_id = item['id']['videoId']
                    title = item['snippet']['title']

                    transcript = self.get_transcript(video_id)
                    if not transcript:
                        continue

                    details = self.extract_full_details(transcript, title, 'YouTube')
                    if details:
                        details['link'] = f"https://youtube.com/watch?v={video_id}"
                        details['date'] = item['snippet']['publishedAt']
                        details['channel'] = item['snippet']['channelTitle']
                        details['source'] = 'YouTube'
                        if self.filter_strategy(details):
                            results.append(details)
            except Exception as e:
                print(f"DEBUG: YouTube search error for '{clean_query}': {e}")

        print(f"DEBUG: YouTube strategies found: {len(results)}")
        return results

    def scrape_option_alpha(self):
        if not self.criteria.get('Option Alpha Enabled', True):
            print("DEBUG: Option Alpha disabled")
            return []

        results = []
        base_url = 'https://optionalpha.com/blog'
        keywords = self.criteria.get('Keywords', 'trading strategy').split(',')

        for query in keywords:
            clean_query = query.strip()
            print(f"DEBUG: Searching Option Alpha for: '{clean_query}'")
            search_url = f"{base_url}?search={clean_query.replace(' ', '%20')}"
            try:
                response = requests.get(search_url)
                soup = BeautifulSoup(response.text, 'html.parser')

                articles = soup.find_all('article', class_='blog-post', limit=3)
                for article in articles:
                    title_elem = article.find('h2')
                    if not title_elem:
                        continue
                    title = title_elem.text.strip()

                    link_elem = article.find('a', class_='blog-post__link')
                    if not link_elem:
                        continue
                    link = f"https://optionalpha.com{link_elem['href']}"

                    content_response = requests.get(link)
                    content_soup = BeautifulSoup(content_response.text, 'html.parser')
                    content = ' '.join(p.text for p in content_soup.find_all('p'))

                    if not content:
                        continue

                    details = self.extract_full_details(content, title, 'Option Alpha')
                    if details:
                        details['link'] = link
                        details['date'] = 'Unknown'
                        details['channel'] = 'Option Alpha'
                        details['source'] = 'Option Alpha'
                        if self.filter_strategy(details):
                            results.append(details)
            except Exception as e:
                print(f"DEBUG: Option Alpha error for '{clean_query}': {e}")

        print(f"DEBUG: Option Alpha strategies found: {len(results)}")
        return results

    def scrape_quantconnect(self):
        if not self.criteria.get('QuantConnect Enabled', True):
            print("DEBUG: QuantConnect disabled")
            return []

        results = []
        base_url = 'https://www.quantconnect.com/forum'
        keywords = self.criteria.get('Keywords', 'trading strategy').split(',')

        for query in keywords:
            clean_query = query.strip()
            print(f"DEBUG: Searching QuantConnect for: '{clean_query}'")
            search_url = f"{base_url}/search?query={clean_query.replace(' ', '%20')}"
            try:
                response = requests.get(search_url)
                soup = BeautifulSoup(response.text, 'html.parser')

                posts = soup.find_all('div', class_='discussion-item', limit=3)
                for post in posts:
                    title_elem = post.find('h3')
                    if not title_elem:
                        continue
                    title = title_elem.text.strip()

                    link_elem = post.find('a', class_='discussion-link')
                    if not link_elem:
                        continue
                    link = f"https://www.quantconnect.com{link_elem['href']}"

                    content_response = requests.get(link)
                    content_soup = BeautifulSoup(content_response.text, 'html.parser')
                    content = ' '.join(p.text for p in content_soup.find_all('div', class_='post-content'))

                    if not content:
                        continue

                    details = self.extract_full_details(content, title, 'QuantConnect')
                    if details:
                        details['link'] = link
                        details['date'] = 'Unknown'
                        details['channel'] = 'QuantConnect Forum'
                        details['source'] = 'QuantConnect'
                        if self.filter_strategy(details):
                            results.append(details)
            except Exception as e:
                print(f"DEBUG: QuantConnect error for '{clean_query}': {e}")

        print(f"DEBUG: QuantConnect strategies found: {len(results)}")
        return results

    def filter_strategy(self, details):
        min_cagr = float(self.criteria.get('Min CAGR (%)', 0))
        min_sharpe = float(self.criteria.get('Min Sharpe', 0))
        max_dd = float(self.criteria.get('Max Drawdown (%)', 100))
        min_win = float(self.criteria.get('Min Win Rate (%)', 0))
        min_trades = float(self.criteria.get('Min Trades Per Year', 0))

        strategy_cagr = float(details.get('cagr', 'Not mentioned').replace('%', '')) if details.get('cagr') != 'Not mentioned' else 0
        strategy_sharpe = float(details.get('sharpe', 'Not mentioned')) if details.get('sharpe') != 'Not mentioned' else 0
        strategy_dd = float(details.get('drawdown', 'Not mentioned').replace('%', '')) if details.get('drawdown') != 'Not mentioned' else 0
        strategy_win = float(details.get('win', 'Not mentioned').replace('%', '')) if details.get('win') != 'Not mentioned' else 0

        if (strategy_cagr >= min_cagr and
            strategy_sharpe >= min_sharpe and
            strategy_dd <= max_dd and
            strategy_win >= min_win):
            return True
        return False

    def run_all(self, youtube_api_key):
        strategies = []
        strategies += self.scrape_youtube(youtube_api_key)
        strategies += self.scrape_option_alpha()
        strategies += self.scrape_quantconnect()
        return strategies


@app.route('/scrape', methods=['POST'])
def scrape_endpoint():
    try:
        data = request.get_json(force=True)
        print("DEBUG: Full incoming data:", data)

        api_key = data.get('youtube_api_key')
        criteria = data.get('criteria', {})

        if not api_key:
            return jsonify({"status": "error", "message": "youtube_api_key is required"}), 400

        scraper = MultiSourceScraper(criteria)
        strategies = scraper.run_all(api_key)

        return jsonify({
            "status": "success",
            "strategies": strategies
        })

    except Exception as e:
        error_msg = traceback.format_exc()
        print("CRITICAL ERROR:", error_msg)
        return jsonify({
            "status": "error",
            "message": str(e),
            "traceback": error_msg
        }), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
