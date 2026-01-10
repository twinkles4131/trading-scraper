    def extract_full_details(self, transcript, title):
        prompt = f"""
        You are an expert Quant Trader. Analyze this YouTube transcript for a trading strategy.
        
        GOAL: Determine if this is a high-quality, profitable trading strategy.
        
        EXTRACT:
        - Strategy Name: (e.g. 'EMA Cross with RSI')
        - Market Regime: (e.g. 'Trending', 'Ranging')
        - Entry/Exit Rules: (Be specific about indicators used)
        - Performance: (Look for ANY mention of Win Rate, CAGR, ROI, or Profit Factor. If they say 'high win rate', estimate it or note it.)
        - Quality Score: (On a scale of 1-10, how detailed and professional is this strategy?)

        Title: {title}
        Transcript: {transcript[:7000]}

        Return ONLY a JSON object:
        {{
            "name": "string",
            "regime": "string",
            "entry": "string",
            "exit": "string",
            "win": "string", 
            "cagr": "string",
            "drawdown": "string",
            "sharpe": "string",
            "quality_score": 8,
            "description": "Brief summary of why this strategy is good"
        }}
        """
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "system", "content": "You are a professional trading strategy analyst."},
                          {"role": "user", "content": prompt}],
                response_format={ "type": "json_object" }
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            print(f"DEBUG: AI Error: {e}")
            return None
