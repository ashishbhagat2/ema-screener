# EMA Stock Screener

An automated stock screener that identifies stocks with favorable trading setups based on the 10-period Exponential Moving Average (EMA).

## Overview

This screener analyzes stocks to find those that are:
- **In an uptrend**: Current price is above the 10 EMA
- **Recently pulled back**: Price has touched or tested the 10 EMA within the last 5 trading days
- **Consolidating**: Shows consolidation behavior around the 10 EMA with lower volatility
- **In proximity range**: Current price is within 0-10% above the 10 EMA

These conditions often indicate a potential continuation of the uptrend after a healthy pullback and consolidation.

## Features

- ✅ Analyzes 200 stocks from NSE (National Stock Exchange of India)
- ✅ Fetches 60 days of historical data for accurate EMA calculation
- ✅ Calculates 10-period EMA using proper exponential weighting
- ✅ Identifies consolidation patterns based on volatility analysis
- ✅ Generates sorted results (stocks closest to EMA appear first)
- ✅ Automated daily execution via GitHub Actions
- ✅ Comprehensive error handling and retry logic
- ✅ Configurable thresholds via environment variables
- ✅ Debug mode with detailed logging
- ✅ Statistics summary showing pass/fail counts
- ✅ Debug CSV with all stocks analyzed
- ✅ Rate limiting to avoid API blocks
- ✅ EMA validation (checks for NaN, zero, insufficient data)

## Files

- **`screener.py`**: Main screening logic with comprehensive filtering and logging
- **`requirements.txt`**: Python dependencies
- **`Futures Stocks List.csv`**: Input file with 200 stock names
- **`ema_screener_results.csv`**: Output file with stocks that passed all criteria (generated after run)
- **`debug_analysis.csv`**: Debug output with all stocks analyzed (generated after run)
- **`.github/workflows/daily-screener.yml`**: GitHub Actions automation workflow

## Installation

### Prerequisites

- Python 3.11 or higher
- pip (Python package manager)

### Setup

1. Clone the repository:
```bash
git clone https://github.com/ashishbhagat2/ema-screener.git
cd ema-screener
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Running Manually

Execute the screener script:
```bash
python screener.py
```

The script will:
1. Read the stock list from `Futures Stocks List.csv`
2. Fetch historical data for each stock (may take several minutes)
3. Apply screening criteria
4. Generate `ema_screener_results.csv` with results
5. Display top 10 results in the console

### Running with Custom Configuration

You can configure the proximity percentage via environment variable:
```bash
PROXIMITY_PERCENTAGE=15 python screener.py
```

### Automated Execution

The screener runs automatically daily at **5:00 PM IST (11:30 AM UTC)** via GitHub Actions.

To manually trigger the workflow:
1. Go to the "Actions" tab in the GitHub repository
2. Select "Daily Stock Screener" workflow
3. Click "Run workflow"

## Output Format

The screener generates two CSV files:

### 1. ema_screener_results.csv

Contains only stocks that passed all criteria:

| Column | Description |
|--------|-------------|
| **Stock Symbol** | Ticker symbol (e.g., RELIANCE.NS) |
| **Company Name** | Full company name |
| **Current Price** | Latest closing price |
| **10 EMA** | Current 10-period EMA value |
| **Distance from EMA (%)** | Percentage distance above EMA |
| **Last Touch Date** | Date when price last touched EMA |
| **Volatility Ratio** | ATR/Price ratio (lower = more consolidation) |
| **Analysis Date** | Date of analysis |

Results are sorted by "Distance from EMA (%)" with stocks closest to EMA appearing first.

### 2. debug_analysis.csv

Contains ALL stocks analyzed with detailed information:

| Column | Description |
|--------|-------------|
| **Stock Symbol** | Ticker symbol |
| **Company Name** | Full company name |
| **Current Price** | Latest closing price |
| **10 EMA** | Current 10-period EMA value |
| **In Uptrend** | Boolean - price above EMA |
| **Distance %** | Percentage distance from EMA |
| **EMA Touched** | Boolean - touched in lookback period |
| **Touch Date** | Date of last touch |
| **Touch Distance %** | How close the touch was |
| **Is Consolidating** | Boolean - meets consolidation criteria |
| **Volatility Ratio** | ATR/Price ratio |
| **Avg Distance from EMA** | Average distance over consolidation period |
| **EMA Rising** | Boolean - EMA trending up |
| **Final Result** | PASS or FAIL |
| **Failure Reason** | Why the stock failed (if applicable) |

This debug file helps you understand why stocks didn't pass the screening criteria.

## Interpreting Results

### What to Look For

Stocks in the results are candidates for potential entry points, but **always perform additional analysis**:

1. **Proximity to EMA**: Stocks with 0-3% distance are very close to EMA support
2. **Recent Touch Date**: More recent touches indicate active consolidation
3. **Volume Analysis**: Check if consolidation occurred on lower volume (not in this screener)
4. **Market Context**: Consider overall market conditions and sector trends

### Example Trading Strategy

While this screener identifies potential setups, here's how traders might use this information:

1. Review screened stocks for additional confirmation:
   - Check volume patterns
   - Look at support/resistance levels
   - Review company fundamentals
   - Check news and events

2. Entry considerations:
   - Enter when price bounces off 10 EMA with volume
   - Wait for bullish candlestick confirmation
   - Set stop-loss below recent swing low

3. Risk management:
   - Never risk more than 1-2% of capital per trade
   - Use proper position sizing
   - Have a clear exit plan

⚠️ **Disclaimer**: This screener is for educational purposes only. Always do your own research and consider consulting with a financial advisor before making investment decisions.

## Technical Details

### EMA Calculation

The 10-period Exponential Moving Average (EMA) is calculated using:

```
EMA = (Close - Previous EMA) × (2 / (period + 1)) + Previous EMA
```

This gives more weight to recent prices compared to a Simple Moving Average (SMA).

### Screening Criteria Details

1. **Uptrend Check**: `Current Price > 10 EMA`

2. **Recent Touch Check**: In the last 7 days (configurable via LOOKBACK_DAYS):
   - Daily low came within 5% of EMA (configurable via EMA_TOUCH_TOLERANCE), OR
   - Closing price was at or below EMA

3. **Consolidation Check**: Over the last 10 days:
   - Average True Range (ATR) / Price < 5% (configurable via CONSOLIDATION_VOLATILITY_THRESHOLD) - indicates low volatility
   - Average distance from EMA < 20% - price staying close to EMA
   - EMA is rising - confirms uptrend

4. **Proximity Check**: `0% < (Price - EMA) / EMA × 100 < 10%` (configurable via PROXIMITY_PERCENTAGE)

### Error Handling

The screener includes robust error handling:
- Skips stocks with insufficient data
- Handles network timeouts gracefully
- Logs all errors for debugging
- Continues processing even if individual stocks fail

## Configuration

### Environment Variables

You can configure the screener behavior using the following environment variables:

- **`PROXIMITY_PERCENTAGE`**: Maximum percentage above EMA (default: 10)
  - Example: `PROXIMITY_PERCENTAGE=15 python screener.py`
  
- **`LOOKBACK_DAYS`**: Days to check for EMA touch (default: 7)
  - Example: `LOOKBACK_DAYS=10 python screener.py`
  
- **`CONSOLIDATION_VOLATILITY_THRESHOLD`**: Maximum volatility ratio for consolidation (default: 0.05 = 5%)
  - Example: `CONSOLIDATION_VOLATILITY_THRESHOLD=0.07 python screener.py`
  
- **`EMA_TOUCH_TOLERANCE`**: Tolerance for EMA touch detection (default: 0.05 = 5%)
  - Example: `EMA_TOUCH_TOLERANCE=0.03 python screener.py`
  
- **`DEBUG`**: Enable detailed debug logging (default: false)
  - Example: `DEBUG=true python screener.py`

### Running with Custom Configuration

You can combine multiple environment variables:

```bash
DEBUG=true PROXIMITY_PERCENTAGE=15 LOOKBACK_DAYS=10 python screener.py
```

### Code Constants

Edit these in `screener.py`:
- `DATA_DAYS`: Days of historical data to fetch (default: 60)
- `EMA_PERIOD`: EMA period (default: 10)
- `API_DELAY`: Delay between API calls in seconds (default: 0.5)

## Troubleshooting

### Understanding the Screening Criteria

The screener applies four key criteria in sequence. A stock must pass ALL of them:

1. **Uptrend Check**: Current price must be above the 10 EMA
   - Why: We only want stocks in an uptrend
   - Fails if: Price is below or equal to EMA

2. **Proximity Check**: Price must be within 0-10% above the 10 EMA (configurable)
   - Why: We want stocks close to support, not extended
   - Fails if: Price is more than PROXIMITY_PERCENTAGE above EMA

3. **EMA Touch Check**: Price must have touched/tested the EMA within the last 7 days (configurable)
   - Why: Confirms recent pullback to support
   - How it works: Checks if the low of any candle came within 5% of EMA, or price crossed below EMA
   - Fails if: No touch detected in LOOKBACK_DAYS

4. **Consolidation Check**: Stock must show consolidation behavior
   - Why: We want stocks that are building energy, not trending
   - Criteria:
     - Low volatility: ATR/Price < 5% (CONSOLIDATION_VOLATILITY_THRESHOLD)
     - Staying close to EMA: Average distance < 20%
     - EMA is rising: Confirms uptrend
   - Fails if: Any of the above criteria not met

### No stocks match criteria

This is normal and can happen due to:

1. **Current market conditions**: Some days have fewer setups
2. **Criteria too strict**: Consider adjusting thresholds

**How to adjust:**

If you're getting too few results, try:
```bash
# Increase proximity range to 15%
PROXIMITY_PERCENTAGE=15 python screener.py

# Increase lookback period to 10 days
LOOKBACK_DAYS=10 python screener.py

# Relax consolidation threshold to 7%
CONSOLIDATION_VOLATILITY_THRESHOLD=0.07 python screener.py

# Increase EMA touch tolerance to 7%
EMA_TOUCH_TOLERANCE=0.07 python screener.py
```

If you're getting too many results, try:
```bash
# Decrease proximity range to 5%
PROXIMITY_PERCENTAGE=5 python screener.py

# Stricter consolidation threshold
CONSOLIDATION_VOLATILITY_THRESHOLD=0.03 python screener.py
```

### Using Debug Mode

Enable debug mode to see detailed analysis for each stock:

```bash
DEBUG=true python screener.py
```

This will show:
- Each stock being analyzed
- Pass/fail status for each criterion
- Specific values (price, EMA, distances, volatility)
- Why each stock failed

### Interpreting the Statistics Summary

At the end of each run, the screener prints statistics:

```
SCREENING STATISTICS
Total stocks analyzed: 200
Failed - Data errors: 5
Failed - Not in uptrend: 80
Failed - Too far from EMA: 40
Failed - No recent EMA touch: 50
Failed - Not consolidating: 20
✅ Passed all criteria: 5
```

This helps you understand:
- Where most stocks are failing
- Whether to adjust specific criteria
- If market conditions are favorable

### Interpreting the Debug CSV

The `debug_analysis.csv` file contains ALL stocks with their scores:

| Column | Meaning |
|--------|---------|
| **Final Result** | PASS or FAIL |
| **Failure Reason** | Why the stock failed (if it did) |
| **In Uptrend** | True/False |
| **Distance %** | How far above EMA |
| **EMA Touched** | True/False |
| **Touch Date** | When it last touched |
| **Is Consolidating** | True/False |
| **Volatility Ratio** | Lower is better |

Use this to:
- Understand why specific stocks didn't make the cut
- Identify stocks that almost passed
- Fine-tune your thresholds

### "Insufficient data" warnings

Some stocks may have:
- Recently listed (less than 60 days of trading)
- Trading halted
- Delisted
- API issues

These are automatically skipped and don't affect results.

### Slow execution

Fetching data for 200 stocks can take 10-20 minutes due to:
- Network speed
- yfinance API response time
- Rate limiting (intentional delay to avoid blocks)

The screener includes:
- Retry logic for failed API calls
- Rate limiting (0.5 second delay between stocks)
- Progress indicators

Consider running during off-peak hours or reducing the stock list for testing.

## Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

This project is open source and available under the MIT License.

## Acknowledgments

- Data provided by Yahoo Finance via yfinance library
- Stock list based on NSE Futures stocks

## Support

For issues or questions:
- Open an issue on GitHub
- Check existing issues for solutions

---

**Remember**: This tool is for screening purposes only. Always perform thorough analysis before making investment decisions.