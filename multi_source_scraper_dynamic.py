import os
import json
import requests
from googleapiclient.discovery import build
from youtube_transcript_api import YouTubeTranscriptApi
from openai import OpenAI

class MultiSourceScraper:
    def __init__(self, criteria):
        self.criteria = criteria
        self.client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

    def get_transcript(self, video_id):
        try:
            transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
            return " ".join([t['text'] for t in transcript_list])
        except Exception:
            return None

    def extract_full_details(self, text, title, source="YouTube"):
        # This prompt is mapped exactly to your 17 columns
        prompt = f"""
        Analyze this {source} content for a trading strategy.
        Extract data for these specific columns:
        - Strategy Name, Upload Date, Link, Channel, Strategy Type, Asset Class, Specific Tickers, 
        - Market Regime, Trading Hours, Win Rate (%), CAGR (%), Max Drawdown (%), 
        - Sharpe Ratio, Profit Factor, Description.

        Content: {text[:7000]}
        
        Return ONLY a JSON object with these exact keys:
        {{"name": "", "date": "", "link": "", "channel": "", "type": "", "asset": "", "tickers": "", "regime": "", "hours": "", "win": null, "cagr": null, "drawdown": null, "sharpe": null, "profit_factor": null, "description": ""}}
        """
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                response_format={ "type": "json_object" }
            )
            return json.loads(response.choices[0].message.content)
        except Exception:
            return None

    def scrape_youtube(self, api_key):
        youtube = build('youtube', 'v3', developerKey=api_key)
        results = []
        keywords = self.criteria.get('keywords', 'trading strategy')
        for query in keywords.split(','):
            request = youtube.search().list(q=query.strip(), part='snippet', maxResults=3, type='video')
            response = request.execute()
            for item in response['items']:
                video_id = item['id']['videoId']
                transcript = self.get_transcript(video_id)
                if transcript:
                    details = self.extract_full_details(transcript, item['snippet']['title'])
                    if details:
                        details['link'] = f"https://youtube.com/watch?v={video_id}"
                        details['date'] = item['snippet']['publishedAt']
                        results.append(details )
        return results

    def scrape_option_alpha(self):
        # Placeholder for Option Alpha API or Web Scraping logic
        print("Scraping Option Alpha...")
        return []

    def scrape_quantconnect(self):
        # Placeholder for QuantConnect League scraping logic
        print("Scraping QuantConnect League...")
        return []

    def run_all(self, youtube_api_key):
        all_results = []
        if self.criteria.get('YouTube Enabled') == 'Y':
            all_results.extend(self.scrape_youtube(youtube_api_key))
        if self.criteria.get('Option Alpha Enabled') == 'Y':
            all_results.extend(self.scrape_option_alpha())
        if self.criteria.get('QuantConnect Enabled') == 'Y':
            all_results.extend(self.scrape_quantconnect())
        return all_results
