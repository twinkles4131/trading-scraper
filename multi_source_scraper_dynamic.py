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
            # Corrected method to fetch transcripts
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
            # Try to find English transcript (manual or auto-generated)
            transcript = transcript_list.find_transcript(['en'])
            text = " ".join([t['text'] for t in transcript.fetch()])
            print(f"DEBUG: Successfully got transcript for {video_id} ({len(text)} chars)")
            return text
        except Exception as e:
            print(f"DEBUG: Transcript error for {video_id}: {e}")
            return None

    def extract_full_details(self, transcript, title):
        prompt = f"""
        You are an expert Quant Trader. Analyze this YouTube transcript for a trading strategy.
        GOAL: Determine if this is a high-quality, profitable trading strategy.
        EXTRACT: Strategy Name, Market Regime, Entry Rules, Exit Rules, Win Rate (%), CAGR (%), Max Drawdown (%), Sharpe Ratio.
        Title: {title}
        Transcript: {transcript[:7000]}
        Return ONLY a JSON object with keys: name, regime, entry, exit, win, cagr, drawdown, sharpe, quality_score, description.
        If a value is unknown, use "Not mentioned".
        """
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "system", "content": "You are a professional trading analyst. Always return JSON."},
                          {"role": "user", "content": prompt}],
                response_format={ "type": "json_object" }
            )
            data = json.loads(response.choices[0].message.content)
            print(f"DEBUG: AI Analysis for '{title}': {data}")
            return data
        except Exception as e:
            print(f"DEBUG: AI Error for '{title}': {e}")
            return None

    def scrape_youtube(self, api_key):
        youtube = build('youtube', 'v3', developerKey=api_key)
        results = []
        # Use the correct key from your Google Sheet
        keywords = self.criteria.get('YouTube Keywords', 'trading strategy')
        
        for query in keywords.split(','):
            clean_query = query.strip()
            print(f"DEBUG: Searching YouTube for: '{clean_query}'")
            request = youtube.search().list(q=clean_query, part='snippet', maxResults=3, type='video')
            response = request.execute()
            
            for item in response['items']:
                video_id = item['id']['videoId']
                title = item['snippet']['title']
                
                transcript = self.get_transcript(video_id)
                if not transcript:
                    continue
                
                details = self.extract_full_details(transcript, title)
                if details:
                    details['link'] = f"https://youtube.com/watch?v={video_id}"
                    details['date'] = item['snippet']['publishedAt']
                    details['channel'] = item['snippet']['channelTitle']
                    results.append(details)
        
        print(f"DEBUG: Total strategies found: {len(results)}")
        return results

    def run_all(self, youtube_api_key):
        return self.scrape_youtube(youtube_api_key)
