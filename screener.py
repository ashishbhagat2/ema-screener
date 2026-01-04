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

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
PROXIMITY_PERCENTAGE = float(os.getenv('PROXIMITY_PERCENTAGE', '10'))  # Default 10%
DATA_DAYS = 60  # Days of historical data to fetch
LOOKBACK_DAYS = 5  # Days to check for EMA touch
EMA_PERIOD = 10  # EMA period


def calculate_ema(prices, period):
    """
    Calculate Exponential Moving Average.
    
    EMA formula: EMA = (Close - Previous EMA) * (2 / (period + 1)) + Previous EMA
    
    Args:
        prices: pandas Series of closing prices
        period: EMA period
        
    Returns:
        pandas Series of EMA values
    """
    return prices.ewm(span=period, adjust=False).mean()


def check_ema_touch(prices, ema_values, lookback_days=5):
    """
    Check if price touched or came close to EMA in the last N days.
    
    A "touch" is defined as:
    - Price low was within 2% of EMA, OR
    - Price crossed the EMA (was below it at some point)
    
    Args:
        prices: DataFrame with High, Low, Close columns
        ema_values: Series of EMA values
        lookback_days: Number of recent days to check
        
    Returns:
        tuple: (touched: bool, last_touch_date: str or None)
    """
    if len(prices) < lookback_days:
        return False, None
    
    recent_data = prices.tail(lookback_days)
    recent_ema = ema_values.tail(lookback_days)
    
    for i, (idx, row) in enumerate(recent_data.iterrows()):
        ema_val = recent_ema.iloc[i]
        # Check if low came within 2% of EMA or if close was below EMA
        if row['Low'] <= ema_val * 1.02 or row['Close'] <= ema_val:
            return True, idx.strftime('%Y-%m-%d')
    
    return False, None


def check_consolidation(prices, ema_values, period=10):
    """
    Check if price shows consolidation behavior around EMA.
    
    Consolidation is identified by:
    - Low volatility (ATR relative to price)
    - Price staying relatively close to EMA
    
    Args:
        prices: DataFrame with High, Low, Close columns
        ema_values: Series of EMA values
        period: Period to check for consolidation
        
    Returns:
        bool: True if consolidating, False otherwise
    """
    if len(prices) < period:
        return False
    
    recent_data = prices.tail(period)
    recent_ema = ema_values.tail(period)
    
    # Calculate Average True Range (ATR) as a measure of volatility
    high_low = recent_data['High'] - recent_data['Low']
    atr = high_low.mean()
    
    # Calculate average price
    avg_price = recent_data['Close'].mean()
    
    # Volatility ratio (ATR / average price)
    volatility_ratio = atr / avg_price if avg_price > 0 else 1
    
    # Check if price stayed relatively close to EMA (within 15% on average)
    ema_distances = abs(recent_data['Close'] - recent_ema) / recent_ema
    avg_distance = ema_distances.mean()
    
    # Consolidation criteria: low volatility AND staying close to EMA
    is_consolidating = volatility_ratio < 0.03 and avg_distance < 0.15
    
    return is_consolidating


def analyze_stock(symbol, company_name):
    """
    Analyze a single stock based on EMA criteria.
    
    Args:
        symbol: Stock ticker symbol
        company_name: Company name
        
    Returns:
        dict: Analysis results or None if failed
    """
    try:
        logger.info(f"Analyzing {symbol} - {company_name}")
        
        # Fetch historical data
        stock = yf.Ticker(symbol)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=DATA_DAYS + 30)  # Extra buffer
        
        # Get historical data
        hist = stock.history(start=start_date, end=end_date)
        
        if hist.empty or len(hist) < EMA_PERIOD + 5:
            logger.warning(f"Insufficient data for {symbol}")
            return None
        
        # Calculate 10 EMA
        hist['EMA_10'] = calculate_ema(hist['Close'], EMA_PERIOD)
        
        # Get most recent data
        current_price = hist['Close'].iloc[-1]
        current_ema = hist['EMA_10'].iloc[-1]
        
        # Check if current price is above EMA (uptrend)
        if current_price <= current_ema:
            logger.debug(f"{symbol}: Not in uptrend (price below EMA)")
            return None
        
        # Calculate distance from EMA
        distance_pct = ((current_price - current_ema) / current_ema) * 100
        
        # Check if within proximity range (0-10% above EMA)
        if distance_pct > PROXIMITY_PERCENTAGE:
            logger.debug(f"{symbol}: Too far from EMA ({distance_pct:.2f}%)")
            return None
        
        # Check for recent EMA touch
        touched, last_touch_date = check_ema_touch(
            hist[['High', 'Low', 'Close']],
            hist['EMA_10'],
            LOOKBACK_DAYS
        )
        
        if not touched:
            logger.debug(f"{symbol}: No recent EMA touch")
            return None
        
        # Check for consolidation
        is_consolidating = check_consolidation(
            hist[['High', 'Low', 'Close']],
            hist['EMA_10']
        )
        
        if not is_consolidating:
            logger.debug(f"{symbol}: Not consolidating")
            return None
        
        # Stock passed all criteria
        logger.info(f"✓ {symbol} passed all criteria!")
        
        return {
            'Stock Symbol': symbol,
            'Company Name': company_name,
            'Current Price': round(current_price, 2),
            '10 EMA': round(current_ema, 2),
            'Distance from EMA (%)': round(distance_pct, 2),
            'Last Touch Date': last_touch_date,
            'Analysis Date': datetime.now().strftime('%Y-%m-%d')
        }
        
    except Exception as e:
        logger.error(f"Error analyzing {symbol}: {str(e)}")
        return None


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
        
        # Extract company names from first column
        # Try to extract ticker symbols from company names
        stocks = []
        for idx, row in df.iterrows():
            company_name = row['Name']
            # For Indian stocks, we need to add .NS suffix for NSE
            # Extract a reasonable ticker from the company name
            # This is a simplified approach - might need refinement
            symbol = company_name.split()[0].upper()
            
            # Add .NS suffix for NSE (National Stock Exchange of India)
            if not symbol.endswith('.NS'):
                symbol = f"{symbol}.NS"
            
            stocks.append((symbol, company_name))
        
        logger.info(f"Loaded {len(stocks)} stocks from {filename}")
        return stocks
        
    except Exception as e:
        logger.error(f"Error reading stock list: {str(e)}")
        sys.exit(1)


def main():
    """Main execution function."""
    logger.info("=" * 70)
    logger.info("Starting Stock Screener - 10 EMA Analysis")
    logger.info(f"Configuration: Proximity={PROXIMITY_PERCENTAGE}%, Days={DATA_DAYS}")
    logger.info("=" * 70)
    
    # Read stock list
    stock_list = read_stock_list('Futures Stocks List.csv')
    
    # Analyze stocks
    results = []
    total_stocks = len(stock_list)
    
    for i, (symbol, company_name) in enumerate(stock_list, 1):
        logger.info(f"Progress: {i}/{total_stocks}")
        result = analyze_stock(symbol, company_name)
        if result:
            results.append(result)
    
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
        logger.info(f"Total stocks analyzed: {total_stocks}")
        logger.info(f"Stocks passing criteria: {len(results)}")
        logger.info(f"Results saved to: {output_file}")
        logger.info("=" * 70)
        
        # Display results
        print("\nTop 10 Results:")
        print(results_df.head(10).to_string(index=False))
    else:
        logger.warning("No stocks matched the screening criteria")
        # Create empty results file
        pd.DataFrame(columns=[
            'Stock Symbol', 'Company Name', 'Current Price', '10 EMA',
            'Distance from EMA (%)', 'Last Touch Date', 'Analysis Date'
        ]).to_csv('ema_screener_results.csv', index=False)


if __name__ == "__main__":
    main()
