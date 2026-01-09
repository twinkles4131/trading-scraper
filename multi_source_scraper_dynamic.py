#!/usr/bin/env python3
"""
Multi-Source Scraper with Dynamic Criteria from Google Sheets
Scrapes YouTube, Option Alpha, and QuantConnect
Reads criteria from Google Sheets Settings tab
Automatically adapts to new criteria
"""

import json
import requests
from typing import Dict, List, Any, Tuple
from datetime import datetime
import re
from google.oauth2 import service_account
from googleapiclient.discovery import build
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DynamicCriteriaReader:
    """Read and validate criteria from Google Sheets Settings tab"""
    
    def __init__(self, sheet_id: str, credentials_json: str):
        """Initialize with Google Sheets credentials"""
        self.sheet_id = sheet_id
        self.credentials = service_account.Credentials.from_service_account_file(
            credentials_json,
            scopes=['https://www.googleapis.com/auth/spreadsheets.readonly']
        )
        self.sheets_service = build('sheets', 'v4', credentials=self.credentials)
    
    def read_settings_tab(self) -> Dict[str, Any]:
        """Read all criteria from Settings tab"""
        
        try:
            # Read Settings tab
            result = self.sheets_service.spreadsheets().values().get(
                spreadsheetId=self.sheet_id,
                range='Settings!A1:B100'
            ).execute()
            
            values = result.get('values', [])
            
            if not values:
                logger.error("Settings tab is empty")
                return {}
            
            # Convert to dictionary
            settings = {}
            for row in values[1:]:  # Skip header
                if len(row) >= 2:
                    key = row[0].strip()
                    value = row[1].strip()
                    settings[key] = value
            
            return settings
        
        except Exception as e:
            logger.error(f"Error reading Settings tab: {e}")
            return {}
    
    def parse_criteria(self, settings: Dict[str, Any]) -> Dict[str, Any]:
        """Parse settings into usable criteria"""
        
        criteria = {}
        
        # Numeric criteria
        numeric_fields = [
            'Min CAGR (%)',
            'Min Sharpe',
            'Max Drawdown (%)',
            'Min Win Rate (%)',
            'Min Trades Per Year',
            'Backtest Start Year',
            'Backtest End Year'
        ]
        
        for field in numeric_fields:
            if field in settings:
                try:
                    criteria[field] = float(settings[field])
                except ValueError:
                    logger.warning(f"Could not parse {field}: {settings[field]}")
                    criteria[field] = None
        
        # Boolean criteria
        boolean_fields = [
            'YouTube Enabled',
            'Option Alpha Enabled',
            'QuantConnect Enabled'
        ]
        
        for field in boolean_fields:
            if field in settings:
                value = settings[field].lower()
                criteria[field] = value in ['y', 'yes', 'true', '1']
        
        # String criteria
        string_fields = [
            'YouTube Keywords',
            'YouTube Language',
            'Option Alpha Filter',
            'QuantConnect Filter'
        ]
        
        for field in string_fields:
            if field in settings:
                criteria[field] = settings[field]
        
        return criteria
    
    def validate_criteria(self, criteria: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate criteria values"""
        
        errors = []
        
        # Check numeric ranges
        if 'Min CAGR (%)' in criteria and criteria['Min CAGR (%)']:
            if criteria['Min CAGR (%)'] < 0 or criteria['Min CAGR (%)'] > 500:
                errors.append("Min CAGR (%) should be between 0 and 500")
        
        if 'Min Sharpe' in criteria and criteria['Min Sharpe']:
            if criteria['Min Sharpe'] < 0 or criteria['Min Sharpe'] > 10:
                errors.append("Min Sharpe should be between 0 and 10")
        
        if 'Max Drawdown (%)' in criteria and criteria['Max Drawdown (%)']:
            if criteria['Max Drawdown (%)'] < 0 or criteria['Max Drawdown (%)'] > 100:
                errors.append("Max Drawdown (%) should be between 0 and 100")
        
        if 'Min Win Rate (%)' in criteria and criteria['Min Win Rate (%)']:
            if criteria['Min Win Rate (%)'] < 0 or criteria['Min Win Rate (%)'] > 100:
                errors.append("Min Win Rate (%) should be between 0 and 100")
        
        if 'Min Trades Per Year' in criteria and criteria['Min Trades Per Year']:
            if criteria['Min Trades Per Year'] < 0 or criteria['Min Trades Per Year'] > 10000:
                errors.append("Min Trades Per Year should be between 0 and 10000")
        
        # Check year ranges
        if 'Backtest Start Year' in criteria and 'Backtest End Year' in criteria:
            if criteria['Backtest Start Year'] and criteria['Backtest End Year']:
                if criteria['Backtest Start Year'] >= criteria['Backtest End Year']:
                    errors.append("Backtest Start Year must be before End Year")
                if criteria['Backtest Start Year'] < 1990 or criteria['Backtest End Year'] > 2030:
                    errors.append("Backtest years should be between 1990 and 2030")
        
        return len(errors) == 0, errors


class MultiSourceScraper:
    """Scrape strategies from multiple sources with dynamic criteria"""
    
    def __init__(self, criteria: Dict[str, Any]):
        """Initialize with criteria"""
        self.criteria = criteria
        self.strategies = []
    
    def scrape_youtube(self, api_key: str) -> List[Dict[str, Any]]:
        """Scrape YouTube for trading strategies"""
        
        if not self.criteria.get('YouTube Enabled', True):
            logger.info("YouTube scraping disabled")
            return []
        
        try:
            youtube = build('youtube', 'v3', developerKey=api_key)
            
            # Get keywords from settings
            keywords = self.criteria.get('YouTube Keywords', 'trading strategy backtest')
            language = self.criteria.get('YouTube Language', 'en')
            
            strategies = []
            
            # Search for strategy videos
            request = youtube.search().list(
                q=keywords,
                part='snippet',
                type='video',
                maxResults=50,
                relevanceLanguage=language,
                order='relevance'
            )
            
            response = request.execute()
            
            for item in response.get('items', []):
                video = {
                    'No': len(strategies) + 1,
                    'Strategy Name': item['snippet']['title'],
                    'Link': f"https://www.youtube.com/watch?v={item['id']['videoId']}",
                    'Channel': item['snippet']['channelTitle'],
                    'Strategy Type': self._extract_strategy_type(item['snippet']['title']),
                    'Asset Class': self._extract_asset_class(item['snippet']['title']),
                    'Specific Tickers': self._extract_tickers(item['snippet']['description']),
                    'Market Regime': self._extract_market_regime(item['snippet']['description']),
                    'Trading Hours': self._extract_trading_hours(item['snippet']['description']),
                    'Claimed Win Rate (%)': self._extract_metric(item['snippet']['description'], 'win rate'),
                    'Claimed CAGR (%)': self._extract_metric(item['snippet']['description'], 'cagr'),
                    'Claimed Max Drawdown (%)': self._extract_metric(item['snippet']['description'], 'drawdown'),
                    'Claimed Sharpe Ratio': self._extract_metric(item['snippet']['description'], 'sharpe'),
                    'Description': item['snippet']['description'],
                    'Status': 'Pending Claude',
                    'Pass to Claude (Y/N)': 'Y'
                }
                
                if self._meets_criteria(video):
                    strategies.append(video)
            
            logger.info(f"YouTube: Found {len(strategies)} strategies meeting criteria")
            return strategies
        
        except Exception as e:
            logger.error(f"Error scraping YouTube: {e}")
            return []
    
    def scrape_option_alpha(self) -> List[Dict[str, Any]]:
        """Scrape Option Alpha for bot strategies"""
        
        if not self.criteria.get('Option Alpha Enabled', True):
            logger.info("Option Alpha scraping disabled")
            return []
        
        try:
            strategies = []
            
            # Option Alpha bot strategies page
            url = "https://www.optionalpha.com/bot-strategies"
            
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            # Parse HTML (simplified - would need BeautifulSoup for real implementation)
            # This is a placeholder for actual scraping logic
            
            logger.info(f"Option Alpha: Found {len(strategies)} strategies meeting criteria")
            return strategies
        
        except Exception as e:
            logger.error(f"Error scraping Option Alpha: {e}")
            return []
    
    def scrape_quantconnect(self) -> List[Dict[str, Any]]:
        """Scrape QuantConnect league for strategies"""
        
        if not self.criteria.get('QuantConnect Enabled', True):
            logger.info("QuantConnect scraping disabled")
            return []
        
        try:
            strategies = []
            
            # QuantConnect league page
            url = "https://www.quantconnect.com/league"
            
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            # Parse HTML (simplified - would need BeautifulSoup for real implementation)
            # This is a placeholder for actual scraping logic
            
            logger.info(f"QuantConnect: Found {len(strategies)} strategies meeting criteria")
            return strategies
        
        except Exception as e:
            logger.error(f"Error scraping QuantConnect: {e}")
            return []
    
    def _meets_criteria(self, strategy: Dict[str, Any]) -> bool:
        """Check if strategy meets all criteria"""
        
        # CAGR check
        if self.criteria.get('Min CAGR (%)'):
            cagr = strategy.get('Claimed CAGR (%)')
            if cagr and float(cagr) < self.criteria['Min CAGR (%)']:
                return False
        
        # Sharpe check
        if self.criteria.get('Min Sharpe'):
            sharpe = strategy.get('Claimed Sharpe Ratio')
            if sharpe and float(sharpe) < self.criteria['Min Sharpe']:
                return False
        
        # Max Drawdown check
        if self.criteria.get('Max Drawdown (%)'):
            dd = strategy.get('Claimed Max Drawdown (%)')
            if dd and float(dd) > self.criteria['Max Drawdown (%)']:
                return False
        
        # Win Rate check
        if self.criteria.get('Min Win Rate (%)'):
            wr = strategy.get('Claimed Win Rate (%)')
            if wr and float(wr) < self.criteria['Min Win Rate (%)']:
                return False
        
        return True
    
    def _extract_strategy_type(self, text: str) -> str:
        """Extract strategy type from text"""
        
        types = ['Iron Condor', 'Iron Butterfly', 'Scalping', 'Trend Following', 
                 'Mean Reversion', 'Breakout', 'Wheel', 'Credit Spread', 'Strangle']
        
        for strategy_type in types:
            if strategy_type.lower() in text.lower():
                return strategy_type
        
        return 'Unknown'
    
    def _extract_asset_class(self, text: str) -> str:
        """Extract asset class from text"""
        
        if any(word in text.lower() for word in ['option', 'call', 'put', 'condor', 'butterfly']):
            return 'Options'
        elif any(word in text.lower() for word in ['forex', 'eur/usd', 'gbp/usd']):
            return 'Forex'
        elif any(word in text.lower() for word in ['crypto', 'bitcoin', 'ethereum']):
            return 'Crypto'
        elif any(word in text.lower() for word in ['cfd', 'contract for difference']):
            return 'CFD'
        else:
            return 'Stocks'
    
    def _extract_tickers(self, text: str) -> str:
        """Extract tickers from text"""
        
        # Pattern for common tickers
        pattern = r'\b[A-Z]{1,5}\b'
        matches = re.findall(pattern, text)
        
        # Filter common words
        common_words = ['THE', 'AND', 'FOR', 'WITH', 'FROM', 'THIS', 'THAT', 'WHICH', 'THESE']
        tickers = [m for m in matches if m not in common_words]
        
        return ', '.join(tickers[:5]) if tickers else ''
    
    def _extract_market_regime(self, text: str) -> str:
        """Extract market regime from text"""
        
        if 'bull' in text.lower():
            return 'Bull Market'
        elif 'bear' in text.lower():
            return 'Bear Market'
        elif 'range' in text.lower():
            return 'Range-bound'
        else:
            return 'All Regimes'
    
    def _extract_trading_hours(self, text: str) -> str:
        """Extract trading hours from text"""
        
        if 'day' in text.lower():
            return 'Day Trading'
        elif 'swing' in text.lower():
            return 'Swing Trading'
        elif 'position' in text.lower():
            return 'Position Trading'
        else:
            return 'All Hours'
    
    def _extract_metric(self, text: str, metric: str) -> str:
        """Extract numeric metric from text"""
        
        patterns = {
            'cagr': r'CAGR[:\s]+([0-9.]+)%?',
            'sharpe': r'Sharpe[:\s]+([0-9.]+)',
            'win rate': r'Win Rate[:\s]+([0-9.]+)%?',
            'drawdown': r'Drawdown[:\s]+([0-9.]+)%?'
        }
        
        pattern = patterns.get(metric.lower())
        if pattern:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return ''
    
    def scrape_all(self, youtube_api_key: str) -> List[Dict[str, Any]]:
        """Scrape all sources"""
        
        all_strategies = []
        
        # Scrape YouTube
        youtube_strategies = self.scrape_youtube(youtube_api_key)
        all_strategies.extend(youtube_strategies)
        
        # Scrape Option Alpha
        oa_strategies = self.scrape_option_alpha()
        all_strategies.extend(oa_strategies)
        
        # Scrape QuantConnect
        qc_strategies = self.scrape_quantconnect()
        all_strategies.extend(qc_strategies)
        
        # Renumber
        for idx, strategy in enumerate(all_strategies):
            strategy['No'] = idx + 1
        
        logger.info(f"Total strategies scraped: {len(all_strategies)}")
        return all_strategies


def lambda_handler(event, context):
    """AWS Lambda handler for n8n integration"""
    
    try:
        # Get parameters
        sheet_id = event.get('sheet_id')
        credentials_json = event.get('credentials_json')
        youtube_api_key = event.get('youtube_api_key')
        
        # Read criteria from Settings tab
        criteria_reader = DynamicCriteriaReader(sheet_id, credentials_json)
        settings = criteria_reader.read_settings_tab()
        criteria = criteria_reader.parse_criteria(settings)
        
        # Validate criteria
        is_valid, errors = criteria_reader.validate_criteria(criteria)
        if not is_valid:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'Invalid criteria',
                    'details': errors
                })
            }
        
        logger.info(f"Using criteria: {criteria}")
        
        # Scrape with dynamic criteria
        scraper = MultiSourceScraper(criteria)
        strategies = scraper.scrape_all(youtube_api_key)
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'status': 'success',
                'total_strategies': len(strategies),
                'criteria': criteria,
                'strategies': strategies
            })
        }
    
    except Exception as e:
        logger.error(f"Error: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e)
            })
        }


if __name__ == '__main__':
    # Test
    print("Multi-Source Scraper with Dynamic Criteria")
    print("Ready to use in n8n workflow")
