import ccxt
import pandas as pd
import numpy as np

# Define the timeframe and the number of periods for historical data
timeframe = '1d'  # 1 day
periods = 1  # last 7 days

# Initialize the exchange
exchange = ccxt.binanceusdm({
    'enableRateLimit': True,  
})

# Fetch all symbols
symbols = exchange.load_markets().keys()

# Calculate price change and volatility for each symbol
data = {}
for symbol in symbols:
    try:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=periods)
        close_prices = [x[4] for x in ohlcv]  # extract close prices
        price_change = (close_prices[-1] - close_prices[0]) / close_prices[0]
        volatility = np.std(close_prices)
        data[symbol] = {
            'price_change': price_change, 
            'volatility': volatility,
        }
    except Exception as e:
        print(f'Could not fetch data for {symbol}: {e}')

# Convert to DataFrame
df = pd.DataFrame(data).T

# Sort by price change and volatility
df['score'] = df['price_change'].abs() + df['volatility']
df = df.sort_values('score', ascending=False)

# Get top 30 symbols
top_symbols = df.head(50).index.tolist()

print(top_symbols)
