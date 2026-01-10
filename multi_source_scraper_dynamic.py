import os
import json
import re
from googleapiclient.discovery import build
from google.oauth2 import service_account
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
        except Exception as e:
            print(f"Transcript error for {video_id}: {e}")
            return None

    def extract_metrics_with_ai(self, transcript, title):
        prompt = f"""
        Analyze the following YouTube video title and transcript for a trading strategy.
        Extract the following metrics if mentioned:
        - CAGR (Annual Return %)
        - Sharpe Ratio
        - Max Drawdown (%)
        - Win Rate (%)
        
        Title: {title}
        Transcript: {transcript[:4000]}
        
        Return ONLY a JSON object like this:
        {{"cagr": 50.5, "sharpe": 1.2, "drawdown": 15.0, "win_rate": 65.0}}
        If a metric is not found, use null.
        """
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                response_format={ "type": "json_object" }
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            print(f"AI Extraction error: {e}")
            return {"cagr": None, "sharpe": None, "drawdown": None, "win_rate": None}

    def scrape_youtube(self, api_key):
        youtube = build('youtube', 'v3', developerKey=api_key)
        results = []
        keywords = self.criteria.get('keywords', 'trading strategy')
        
        for query in keywords.split(','):
            print(f"Searching for: {query.strip()}")
            request = youtube.search().list(
                q=query.strip(),
                part='snippet',
                maxResults=3, 
                type='video'
            )
            response = request.execute()

            for item in response['items']:
                video_id = item['id']['videoId']
                title = item['snippet']['title']
                print(f"Processing video: {title}")
                
                transcript = self.get_transcript(video_id)
                if not transcript:
                    print(f"No transcript for {title}, skipping.")
                    continue
                
                metrics = self.extract_metrics_with_ai(transcript, title)
                print(f"AI Extracted Metrics: {metrics}")
                
                if self.passes_filters(metrics):
                    results.append({
                        'title': title,
                        'url': f"https://youtube.com/watch?v={video_id}",
                        'metrics': metrics
                    } )
        return results

    def passes_filters(self, metrics):
        # If AI found nothing, we skip it
        if all(v is None for v in metrics.values()):
            return False
            
        # Compare against Google Sheet criteria (with safety defaults)
        min_cagr = float(self.criteria.get('Min CAGR (%)', 30))
        min_win_rate = float(self.criteria.get('Min Win Rate (%)', 45))
        
        # Check CAGR
        if metrics['cagr'] and metrics['cagr'] < min_cagr:
            return False
        
        # Check Win Rate
        if metrics['win_rate'] and metrics['win_rate'] < min_win_rate:
            return False
            
        return True
