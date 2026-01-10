import os
import json
from googleapiclient.discovery import build
from google.oauth2 import service_account
from youtube_transcript_api import YouTubeTranscriptApi
from openai import OpenAI

class DynamicCriteriaReader:
    def __init__(self, sheet_id, credentials_path):
        self.sheet_id = sheet_id
        self.creds = service_account.Credentials.from_service_account_file(
            credentials_path, 
            scopes=['https://www.googleapis.com/auth/spreadsheets.readonly']
         )
        self.service = build('sheets', 'v4', credentials=self.creds)

    def read_settings_tab(self):
        range_name = 'Settings!A:B'
        result = self.service.spreadsheets().values().get(
            spreadsheetId=self.sheet_id, range=range_name).execute()
        return result.get('values', [])

    def parse_criteria(self, rows):
        criteria = {}
        for row in rows:
            if len(row) >= 2:
                criteria[row[0]] = row[1]
        return criteria

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
        keywords = self.criteria.get('YouTube Keywords', 'trading strategy')
        for query in keywords.split(','):
            request = youtube.search().list(q=query.strip(), part='snippet', maxResults=2, type='video')
            response = request.execute()
            for item in response['items']:
                video_id = item['id']['videoId']
                transcript = self.get_transcript(video_id)
                if transcript:
                    details = self.extract_full_details(transcript, item['snippet']['title'])
                    if details:
                        details['link'] = f"https://youtube.com/watch?v={video_id}"
                        details['date'] = item['snippet']['publishedAt']
                        details['channel'] = item['snippet']['channelTitle']
                        results.append(details )
        return results

    def run_all(self, youtube_api_key):
        all_results = []
        if self.criteria.get('YouTube Enabled') == 'Y':
            all_results.extend(self.scrape_youtube(youtube_api_key))
        # Option Alpha and QuantConnect logic can be added here later
        return all_results
