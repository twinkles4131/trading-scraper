import os
import json
import traceback
import httpx
from flask import Flask, request, jsonify
import requests
from bs4 import BeautifulSoup
import praw
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

class MultiSourceScraper:
    def __init__(self, criteria):
        self.criteria = criteria
        # Initialize OpenAI client for Claude (via OpenAI-compatible API)
        self.client = OpenAI(
            api_key=os.environ.get("OPENAI_API_KEY"),
            http_client=httpx.Client(
                timeout=60.0,
                follow_redirects=True
            )
        )
        # Reddit API Setup
        self.reddit = praw.Reddit(
            client_id=os.getenv("REDDIT_CLIENT_ID"),
            client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
            user_agent="TradingScraper/1.0"
        )

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
                model="gpt-4.1-mini",
                messages=[
                    {"role": "system", "content": "You are a professional trading analyst. Always return JSON."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"}
            )
            data = json.loads(response.choices[0].message.content)
            return data
        except Exception as e:
            print(f"DEBUG: AI Error for '{title}': {e}")
            return None

    def scrape_reddit(self):
        if not self.criteria.get('Reddit Enabled', True):
            return []
        
        results = []
        subreddits = ["algotrading", "options"]
        for sub in subreddits:
            try:
                for submission in self.reddit.subreddit(sub).hot(limit=5):
                    if any(keyword in submission.title.lower() for keyword in ["strategy", "backtest", "cagr"]):
                        details = self.extract_full_details(submission.selftext, submission.title, f"Reddit: r/{sub}")
                        if details:
                            details['link'] = f"https://reddit.com{submission.permalink}"
                            details['source'] = f"Reddit: r/{sub}"
                            if self.filter_strategy(details):
                                results.append(details)
            except Exception as e:
                print(f"DEBUG: Reddit error for r/{sub}: {e}")
        return results

    def scrape_blogs(self):
        if not self.criteria.get('Blogs Enabled', True):
            return []
        
        results = []
        # Example blog URLs - in a real scenario, these could be dynamic
        blog_urls = ["https://www.quantifiedstrategies.com/blog/"]
        for url in blog_urls:
            try:
                response = requests.get(url)
                soup = BeautifulSoup(response.text, 'html.parser')
                for article in soup.find_all('article', limit=3):
                    title = article.find('h2').text.strip()
                    link = article.find('a')['href']
                    content_resp = requests.get(link)
                    content_soup = BeautifulSoup(content_resp.text, 'html.parser')
                    content = ' '.join(p.text for p in content_soup.find_all('p'))
                    details = self.extract_full_details(content, title, "Blog")
                    if details:
                        details['link'] = link
                        details['source'] = "Blog"
                        if self.filter_strategy(details):
                            results.append(details)
            except Exception as e:
                print(f"DEBUG: Blog error for {url}: {e}")
        return results

    def scrape_quantconnect(self):
        # Placeholder for QuantConnect API integration
        return [{"source": "QuantConnect", "name": "Sample QC Strategy", "cagr": "15%", "sharpe": "1.2", "drawdown": "10%", "win": "60%", "quality_score": 8, "description": "Sample strategy from QuantConnect"}]

    def scrape_option_alpha(self):
        # Placeholder for Option Alpha community/templates
        return [{"source": "Option Alpha", "name": "Sample OA Strategy", "cagr": "12%", "sharpe": "1.1", "drawdown": "8%", "win": "55%", "quality_score": 7, "description": "Sample strategy from Option Alpha"}]

    def filter_strategy(self, details):
        min_cagr = float(self.criteria.get('Min CAGR (%)', 0))
        min_sharpe = float(self.criteria.get('Min Sharpe', 0))
        max_dd = float(self.criteria.get('Max Drawdown (%)', 100))
        
        try:
            cagr = float(str(details.get('cagr', '0')).replace('%', '')) if details.get('cagr') != 'Not mentioned' else 0
            sharpe = float(details.get('sharpe', '0')) if details.get('sharpe') != 'Not mentioned' else 0
            dd = float(str(details.get('drawdown', '100')).replace('%', '')) if details.get('drawdown') != 'Not mentioned' else 100
            
            return cagr >= min_cagr and sharpe >= min_sharpe and dd <= max_dd
        except:
            return False

    def run_all(self):
        strategies = []
        strategies += self.scrape_reddit()
        strategies += self.scrape_blogs()
        strategies += self.scrape_quantconnect()
        strategies += self.scrape_option_alpha()
        return strategies

