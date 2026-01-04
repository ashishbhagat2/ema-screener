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
- ✅ Comprehensive error handling and logging
- ✅ Configurable proximity percentage

## Files

- **`screener.py`**: Main screening logic
- **`requirements.txt`**: Python dependencies
- **`Futures Stocks List.csv`**: Input file with 200 stock names
- **`ema_screener_results.csv`**: Output file with screening results (generated after first run)
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

The `ema_screener_results.csv` file contains the following columns:

| Column | Description |
|--------|-------------|
| **Stock Symbol** | Ticker symbol (e.g., RELIANCE.NS) |
| **Company Name** | Full company name |
| **Current Price** | Latest closing price |
| **10 EMA** | Current 10-period EMA value |
| **Distance from EMA (%)** | Percentage distance above EMA |
| **Last Touch Date** | Date when price last touched EMA |
| **Analysis Date** | Date of analysis |

Results are sorted by "Distance from EMA (%)" with stocks closest to EMA appearing first.

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

2. **Recent Touch Check**: In the last 5 days:
   - Daily low came within 2% of EMA, OR
   - Closing price was at or below EMA

3. **Consolidation Check**: Over the last 10 days:
   - Average True Range (ATR) / Price < 3% (low volatility)
   - Average distance from EMA < 15%

4. **Proximity Check**: `0% < (Price - EMA) / EMA × 100 < 10%`

### Error Handling

The screener includes robust error handling:
- Skips stocks with insufficient data
- Handles network timeouts gracefully
- Logs all errors for debugging
- Continues processing even if individual stocks fail

## Configuration

### Environment Variables

- `PROXIMITY_PERCENTAGE`: Maximum percentage above EMA (default: 10)

### Code Constants

Edit these in `screener.py`:
- `DATA_DAYS`: Days of historical data to fetch (default: 60)
- `LOOKBACK_DAYS`: Days to check for EMA touch (default: 5)
- `EMA_PERIOD`: EMA period (default: 10)

## Troubleshooting

### No stocks match criteria

This is normal on some days. Market conditions vary, and some days may have fewer stocks meeting all criteria.

### "Insufficient data" warnings

Some stocks may have:
- Recently listed (less than 60 days of trading)
- Trading halted
- Delisted

These are automatically skipped.

### Slow execution

Fetching data for 200 stocks can take 10-15 minutes depending on:
- Network speed
- yfinance API response time
- Server load

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