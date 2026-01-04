"""
Stock Screener based on 10 EMA (Exponential Moving Average)

This script analyzes stocks to identify those that:
- Are in an uptrend (price above 10 EMA)
- Recently pulled back to touch/test the 10 EMA (within last 5 trading days)
- Show consolidation around the 10 EMA
- Current price is within 0-10% above the 10 EMA
"""

import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
import logging
import os
import sys
import time

# Configure logging
DEBUG_MODE = os.getenv('DEBUG', 'false').lower() == 'true'
logging.basicConfig(
    level=logging.DEBUG if DEBUG_MODE else logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration from environment variables
INPUT_CSV = os.getenv('INPUT_CSV', 'Futures Stocks List.csv')
PROXIMITY_PERCENTAGE = float(os.getenv('PROXIMITY_PERCENTAGE', '10'))  # Default 10%
LOOKBACK_DAYS = int(os.getenv('LOOKBACK_DAYS', '7'))  # Days to check for EMA touch (increased from 5 to 7)
CONSOLIDATION_VOLATILITY_THRESHOLD = float(os.getenv('CONSOLIDATION_VOLATILITY_THRESHOLD', '0.05'))  # Default 5%
EMA_TOUCH_TOLERANCE = float(os.getenv('EMA_TOUCH_TOLERANCE', '0.05'))  # Default 5%
DATA_DAYS = 60  # Days of historical data to fetch
EMA_PERIOD = 10  # EMA period
API_DELAY = 0.5  # Delay between API calls to avoid rate limiting

# Statistics tracking
stats = {
    'total_analyzed': 0,
    'failed_uptrend': 0,
    'failed_proximity': 0,
    'failed_ema_touch': 0,
    'failed_consolidation': 0,
    'passed_all': 0,
    'data_errors': 0
}


def calculate_ema(prices, period):
    """
    Calculate Exponential Moving Average with validation.
    
    EMA formula: EMA = (Close - Previous EMA) * (2 / (period + 1)) + Previous EMA
    
    Args:
        prices: pandas Series of closing prices
        period: EMA period
        
    Returns:
        pandas Series of EMA values
    """
    if len(prices) < period:
        raise ValueError(f"Insufficient data: need at least {period} data points, got {len(prices)}")
    
    ema = prices.ewm(span=period, adjust=False).mean()
    
    # Validate EMA values
    if ema.isna().all() or (ema == 0).all():
        raise ValueError("EMA calculation resulted in invalid values (NaN or zero)")
    
    return ema


def check_ema_touch(prices, ema_values, lookback_days=7):
    """
    Check if price touched or came close to EMA in the last N days.
    
    A "touch" is defined as:
    - Price low came within EMA_TOUCH_TOLERANCE (default 5%) of EMA, OR
    - Price crossed the EMA (was below it at some point)
    
    Args:
        prices: DataFrame with High, Low, Close columns
        ema_values: Series of EMA values
        lookback_days: Number of recent days to check
        
    Returns:
        tuple: (touched: bool, last_touch_date: str or None, touch_distance: float)
    """
    if len(prices) < lookback_days:
        return False, None, None
    
    recent_data = prices.tail(lookback_days)
    recent_ema = ema_values.tail(lookback_days)
    
    last_touch_date = None
    min_distance = float('inf')
    
    for i, (idx, row) in enumerate(recent_data.iterrows()):
        ema_val = recent_ema.iloc[i]
        if ema_val == 0 or pd.isna(ema_val):
            continue
            
        # Calculate distance from EMA (as percentage)
        low_distance = abs(row['Low'] - ema_val) / ema_val
        
        # Check if low came within EMA_TOUCH_TOLERANCE of EMA
        if low_distance <= EMA_TOUCH_TOLERANCE:
            # Always update to the most recent touch date
            last_touch_date = idx.strftime('%Y-%m-%d')
            if low_distance < min_distance:
                min_distance = low_distance
        
        # Check if price crossed below EMA (actual crossing is strongest signal)
        if row['Close'] <= ema_val:
            # Crossing below EMA is the best touch signal
            last_touch_date = idx.strftime('%Y-%m-%d')
            min_distance = 0
    
    touched = last_touch_date is not None
    return touched, last_touch_date, min_distance if touched else None


def check_consolidation(prices, ema_values, period=10):
    """
    Check if price shows consolidation behavior around EMA.
    
    Consolidation is identified by:
    - Low volatility (ATR relative to price) - threshold increased from 0.03 to 0.05
    - Price staying relatively close to EMA (within 20% on average)
    - EMA is rising (uptrend confirmation)
    
    Args:
        prices: DataFrame with High, Low, Close columns
        ema_values: Series of EMA values
        period: Period to check for consolidation
        
    Returns:
        tuple: (is_consolidating: bool, volatility_ratio: float, avg_distance: float, ema_rising: bool)
    """
    if len(prices) < period:
        return False, None, None, False
    
    recent_data = prices.tail(period)
    recent_ema = ema_values.tail(period)
    
    # Calculate Average True Range (ATR) as a measure of volatility
    high_low = recent_data['High'] - recent_data['Low']
    atr = high_low.mean()
    
    # Calculate average price
    avg_price = recent_data['Close'].mean()
    
    # Volatility ratio (ATR / average price)
    volatility_ratio = atr / avg_price if avg_price > 0 else 1
    
    # Check if price stayed relatively close to EMA (within 20% on average)
    ema_distances = abs(recent_data['Close'] - recent_ema) / recent_ema
    avg_distance = ema_distances.mean()
    
    # Check if EMA is rising (uptrend confirmation)
    ema_rising = recent_ema.iloc[-1] > recent_ema.iloc[0]
    
    # Consolidation criteria: low volatility AND staying close to EMA AND EMA rising
    is_consolidating = (
        volatility_ratio < CONSOLIDATION_VOLATILITY_THRESHOLD and 
        avg_distance < 0.20 and 
        ema_rising
    )
    
    return is_consolidating, volatility_ratio, avg_distance, ema_rising


def analyze_stock(symbol, company_name):
    """
    Analyze a single stock based on EMA criteria with comprehensive logging.
    
    Args:
        symbol: Stock ticker symbol
        company_name: Company name
        
    Returns:
        tuple: (result: dict or None, debug_info: dict)
    """
    debug_info = {
        'Stock Symbol': symbol,
        'Company Name': company_name,
        'Current Price': None,
        '10 EMA': None,
        'In Uptrend': False,
        'Distance %': None,
        'EMA Touched': False,
        'Touch Date': None,
        'Touch Distance %': None,
        'Is Consolidating': False,
        'Volatility Ratio': None,
        'Avg Distance from EMA': None,
        'EMA Rising': False,
        'Final Result': 'FAIL',
        'Failure Reason': None
    }
    
    try:
        logger.info(f"Analyzing {symbol} - {company_name}")
        stats['total_analyzed'] += 1
        
        # Fetch historical data with retry logic
        max_retries = 3
        hist = None
        for attempt in range(max_retries):
            try:
                stock = yf.Ticker(symbol)
                end_date = datetime.now()
                start_date = end_date - timedelta(days=DATA_DAYS + 30)  # Extra buffer
                
                # Get historical data
                hist = stock.history(start=start_date, end=end_date)
                if not hist.empty:
                    break
                    
            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning(f"Attempt {attempt + 1} failed for {symbol}, retrying...")
                    time.sleep(1)  # Wait before retry
                else:
                    raise e
        
        if hist is None or hist.empty or len(hist) < EMA_PERIOD + 5:
            logger.warning(f"Insufficient data for {symbol}")
            stats['data_errors'] += 1
            debug_info['Failure Reason'] = 'Insufficient data'
            return None, debug_info
        
        # Calculate 10 EMA with validation
        try:
            hist['EMA_10'] = calculate_ema(hist['Close'], EMA_PERIOD)
        except ValueError as e:
            logger.warning(f"EMA calculation failed for {symbol}: {str(e)}")
            stats['data_errors'] += 1
            debug_info['Failure Reason'] = f'EMA calculation error: {str(e)}'
            return None, debug_info
        
        # Get most recent data
        current_price = hist['Close'].iloc[-1]
        current_ema = hist['EMA_10'].iloc[-1]
        
        # Validate EMA value
        if pd.isna(current_ema) or current_ema == 0:
            logger.warning(f"Invalid EMA value for {symbol}: {current_ema}")
            stats['data_errors'] += 1
            debug_info['Failure Reason'] = 'Invalid EMA value'
            return None, debug_info
        
        debug_info['Current Price'] = round(current_price, 2)
        debug_info['10 EMA'] = round(current_ema, 2)
        
        # Check if current price is above EMA (uptrend)
        in_uptrend = current_price > current_ema
        debug_info['In Uptrend'] = in_uptrend
        
        if not in_uptrend:
            logger.debug(f"{symbol}: ❌ Not in uptrend (price {current_price:.2f} <= EMA {current_ema:.2f})")
            stats['failed_uptrend'] += 1
            debug_info['Failure Reason'] = 'Not in uptrend'
            return None, debug_info
        
        # Calculate distance from EMA
        distance_pct = ((current_price - current_ema) / current_ema) * 100
        debug_info['Distance %'] = round(distance_pct, 2)
        
        # Check if within proximity range (0-10% above EMA)
        if distance_pct > PROXIMITY_PERCENTAGE:
            logger.debug(f"{symbol}: ❌ Too far from EMA ({distance_pct:.2f}% > {PROXIMITY_PERCENTAGE}%)")
            stats['failed_proximity'] += 1
            debug_info['Failure Reason'] = f'Too far from EMA ({distance_pct:.2f}%)'
            return None, debug_info
        
        # Check for recent EMA touch
        touched, last_touch_date, touch_distance = check_ema_touch(
            hist[['High', 'Low', 'Close']],
            hist['EMA_10'],
            LOOKBACK_DAYS
        )
        
        debug_info['EMA Touched'] = touched
        debug_info['Touch Date'] = last_touch_date
        if touch_distance is not None:
            debug_info['Touch Distance %'] = round(touch_distance * 100, 2)
        
        if not touched:
            logger.debug(f"{symbol}: ❌ No recent EMA touch in last {LOOKBACK_DAYS} days")
            stats['failed_ema_touch'] += 1
            debug_info['Failure Reason'] = f'No EMA touch in last {LOOKBACK_DAYS} days'
            return None, debug_info
        
        # Check for consolidation
        is_consolidating, volatility_ratio, avg_distance, ema_rising = check_consolidation(
            hist[['High', 'Low', 'Close']],
            hist['EMA_10']
        )
        
        debug_info['Is Consolidating'] = is_consolidating
        if volatility_ratio is not None:
            debug_info['Volatility Ratio'] = round(volatility_ratio, 4)
        if avg_distance is not None:
            debug_info['Avg Distance from EMA'] = round(avg_distance * 100, 2)
        debug_info['EMA Rising'] = ema_rising
        
        if not is_consolidating:
            if volatility_ratio is not None and volatility_ratio >= CONSOLIDATION_VOLATILITY_THRESHOLD:
                reason = f'High volatility ({volatility_ratio:.4f} >= {CONSOLIDATION_VOLATILITY_THRESHOLD})'
            elif avg_distance is not None and avg_distance >= 0.20:
                reason = f'Too far from EMA on average ({avg_distance*100:.2f}%)'
            elif not ema_rising:
                reason = 'EMA not rising'
            else:
                reason = 'Not consolidating'
            
            logger.debug(f"{symbol}: ❌ {reason}")
            stats['failed_consolidation'] += 1
            debug_info['Failure Reason'] = reason
            return None, debug_info
        
        # Stock passed all criteria
        stats['passed_all'] += 1
        debug_info['Final Result'] = 'PASS'
        
        logger.info(f"✅ {symbol} PASSED all criteria!")
        if DEBUG_MODE:
            logger.debug(f"  Price: {current_price:.2f}, EMA: {current_ema:.2f}, Distance: {distance_pct:.2f}%")
            logger.debug(f"  Touch Date: {last_touch_date}, Volatility: {volatility_ratio:.4f}")
            logger.debug(f"  Avg Distance: {avg_distance*100:.2f}%, EMA Rising: {ema_rising}")
        
        result = {
            'Stock Symbol': symbol,
            'Company Name': company_name,
            'Current Price': round(current_price, 2),
            '10 EMA': round(current_ema, 2),
            'Distance from EMA (%)': round(distance_pct, 2),
            'Last Touch Date': last_touch_date,
            'Volatility Ratio': round(volatility_ratio, 4),
            'Analysis Date': datetime.now().strftime('%Y-%m-%d')
        }
        
        return result, debug_info
        
    except Exception as e:
        logger.error(f"Error analyzing {symbol}: {str(e)}")
        stats['data_errors'] += 1
        debug_info['Failure Reason'] = f'Error: {str(e)}'
        return None, debug_info


def get_ticker_mapping():
    """
    Map company names to NSE ticker symbols.
    
    Returns:
        dict: Mapping of company name keywords to ticker symbols
    """
    # Common NSE ticker symbols for major Indian stocks
    mapping = {
        'Reliance': 'RELIANCE',
        'HDFC Bank': 'HDFCBANK',
        'Bharti Airtel': 'BHARTIARTL',
        'Tata Consultancy': 'TCS',
        'ICICI Bank': 'ICICIBANK',
        'State Bank': 'SBIN',
        'Infosys': 'INFY',
        'Bajaj Finance': 'BAJFINANCE',
        'Larsen': 'LT',
        'Hindustan Unilever': 'HINDUNILVR',
        'LIC': 'LICI',
        'Maruti': 'MARUTI',
        'Mahindra': 'M&M',
        'HCL Tech': 'HCLTECH',
        'ITC': 'ITC',
        'Kotak': 'KOTAKBANK',
        'Sun Pharma': 'SUNPHARMA',
        'Axis Bank': 'AXISBANK',
        'Titan': 'TITAN',
        'Asian Paints': 'ASIANPAINT',
        'Wipro': 'WIPRO',
        'Adani Enterprises': 'ADANIENT',
        'Tata Motors': 'TATAMOTORS',
        'Power Grid': 'POWERGRID',
        'Nestle': 'NESTLEIND',
        'Coal India': 'COALINDIA',
        'Tata Steel': 'TATASTEEL',
        'Bajaj Auto': 'BAJAJ-AUTO',
        'NTPC': 'NTPC',
        'ONGC': 'ONGC',
        'JSW Steel': 'JSWSTEEL',
        'Tech Mahindra': 'TECHM',
        'Hindalco': 'HINDALCO',
        'UltraTech': 'ULTRACEMCO',
        'Shriram Finance': 'SHRIRAMFIN',
        'Tata Power': 'TATAPOWER',
        'Grasim': 'GRASIM',
        'IndusInd Bank': 'INDUSINDBK',
        'Britannia': 'BRITANNIA',
        'Hero MotoCorp': 'HEROMOTOCO',
        'Bharat Electronics': 'BEL',
        'Eicher': 'EICHERMOT',
        'Adani Ports': 'ADANIPORTS',
        'Adani Power': 'ADANIPOWER',
        'Adani Green': 'ADANIGREEN',
        'SBI Life': 'SBILIFE',
        'HDFC Life': 'HDFCLIFE',
        'Cipla': 'CIPLA',
        'Zomato': 'ZOMATO',
        "Divi's": 'DIVISLAB',
        'Dr Reddy': 'DRREDDY',
        'Apollo': 'APOLLOHOSP',
        'Godrej Consumer': 'GODREJCP',
        'Pidilite': 'PIDILITIND',
        'Siemens': 'SIEMENS',
        'Havells': 'HAVELLS',
        'ABB': 'ABB',
        'Indian Oil': 'IOC',
        'Bharat Petroleum': 'BPCL',
        'Hindustan Petroleum': 'HINDPETRO',
        'Vedanta': 'VEDL',
        'Trent': 'TRENT',
        'DLF': 'DLF',
        'Berger Paints': 'BERGEPAINT',
    }
    return mapping


def read_stock_list(filename):
    """
    Read stock list from CSV file.
    
    Args:
        filename: Path to CSV file
        
    Returns:
        list: List of tuples (symbol, company_name)
    """
    try:
        df = pd.read_csv(filename)
        
        # Get ticker mapping
        ticker_map = get_ticker_mapping()
        
        # Extract company names and map to tickers
        stocks = []
        for idx, row in df.iterrows():
            company_name = row['Name']
            
            # Try to find ticker from mapping
            ticker = None
            for key, value in ticker_map.items():
                if key.lower() in company_name.lower():
                    ticker = value
                    break
            
            # If no mapping found, try to derive from company name
            if not ticker:
                # Extract potential ticker from first significant word
                words = company_name.split()
                if words:
                    # Use first word as base, clean up common suffixes
                    ticker = words[0].upper()
                    # If it's a common word, try second word
                    if ticker in ['THE', 'M/S', 'SHRI', 'SRI']:
                        ticker = words[1].upper() if len(words) > 1 else ticker
            
            # Add .NS suffix for NSE (National Stock Exchange of India)
            symbol = f"{ticker}.NS"
            
            stocks.append((symbol, company_name))
        
        logger.info(f"Loaded {len(stocks)} stocks from {filename}")
        return stocks
        
    except Exception as e:
        logger.error(f"Error reading stock list: {str(e)}")
        sys.exit(1)


def main():
    """Main execution function."""
    # Reset statistics at the start of each run
    stats['total_analyzed'] = 0
    stats['failed_uptrend'] = 0
    stats['failed_proximity'] = 0
    stats['failed_ema_touch'] = 0
    stats['failed_consolidation'] = 0
    stats['passed_all'] = 0
    stats['data_errors'] = 0
    
    logger.info("=" * 70)
    logger.info("Starting Stock Screener - 10 EMA Analysis")
    logger.info(f"Configuration:")
    logger.info(f"  Proximity Percentage: {PROXIMITY_PERCENTAGE}%")
    logger.info(f"  Lookback Days: {LOOKBACK_DAYS}")
    logger.info(f"  Consolidation Volatility Threshold: {CONSOLIDATION_VOLATILITY_THRESHOLD}")
    logger.info(f"  EMA Touch Tolerance: {EMA_TOUCH_TOLERANCE * 100}%")
    logger.info(f"  Data Days: {DATA_DAYS}")
    logger.info(f"  Debug Mode: {DEBUG_MODE}")
    logger.info("=" * 70)
    
    # Read stock list
    stock_list = read_stock_list(INPUT_CSV)
    
    # Analyze stocks
    results = []
    debug_results = []
    total_stocks = len(stock_list)
    
    for i, (symbol, company_name) in enumerate(stock_list, 1):
        logger.info(f"Progress: {i}/{total_stocks}")
        result, debug_info = analyze_stock(symbol, company_name)
        
        # Add to debug results
        debug_results.append(debug_info)
        
        # Add to results if passed
        if result:
            results.append(result)
        
        # Rate limiting - add small delay between API calls
        if i < total_stocks:
            time.sleep(API_DELAY)
    
    # Print statistics summary
    logger.info("=" * 70)
    logger.info("SCREENING STATISTICS")
    logger.info("=" * 70)
    logger.info(f"Total stocks analyzed: {stats['total_analyzed']}")
    logger.info(f"Failed - Data errors: {stats['data_errors']}")
    logger.info(f"Failed - Not in uptrend: {stats['failed_uptrend']}")
    logger.info(f"Failed - Too far from EMA: {stats['failed_proximity']}")
    logger.info(f"Failed - No recent EMA touch: {stats['failed_ema_touch']}")
    logger.info(f"Failed - Not consolidating: {stats['failed_consolidation']}")
    logger.info(f"✅ Passed all criteria: {stats['passed_all']}")
    logger.info("=" * 70)
    
    # Create debug CSV with all stocks
    debug_df = pd.DataFrame(debug_results)
    debug_output_file = 'debug_analysis.csv'
    debug_df.to_csv(debug_output_file, index=False)
    logger.info(f"Debug analysis saved to: {debug_output_file}")
    
    # Create results DataFrame
    if results:
        results_df = pd.DataFrame(results)
        
        # Sort by proximity to EMA (closest first)
        results_df = results_df.sort_values('Distance from EMA (%)')
        
        # Save to CSV
        output_file = 'ema_screener_results.csv'
        results_df.to_csv(output_file, index=False)
        
        logger.info("=" * 70)
        logger.info("SCREENING COMPLETE!")
        logger.info(f"Results saved to: {output_file}")
        logger.info("=" * 70)
        
        # Display results
        print("\n" + "=" * 70)
        print(f"Top {min(10, len(results))} Results:")
        print("=" * 70)
        print(results_df.head(10).to_string(index=False))
        print("=" * 70)
    else:
        logger.warning("=" * 70)
        logger.warning("No stocks matched the screening criteria")
        logger.warning("This can happen due to:")
        logger.warning("  - Current market conditions")
        logger.warning("  - Criteria being too strict")
        logger.warning("Consider adjusting thresholds using environment variables:")
        logger.warning(f"  - PROXIMITY_PERCENTAGE (current: {PROXIMITY_PERCENTAGE})")
        logger.warning(f"  - LOOKBACK_DAYS (current: {LOOKBACK_DAYS})")
        logger.warning(f"  - CONSOLIDATION_VOLATILITY_THRESHOLD (current: {CONSOLIDATION_VOLATILITY_THRESHOLD})")
        logger.warning(f"  - EMA_TOUCH_TOLERANCE (current: {EMA_TOUCH_TOLERANCE})")
        logger.warning("=" * 70)
        
        # Create empty results file
        pd.DataFrame(columns=[
            'Stock Symbol', 'Company Name', 'Current Price', '10 EMA',
            'Distance from EMA (%)', 'Last Touch Date', 'Volatility Ratio', 'Analysis Date'
        ]).to_csv('ema_screener_results.csv', index=False)


if __name__ == "__main__":
    main()
