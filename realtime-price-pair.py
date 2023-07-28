import ccxt.pro
from asyncio import gather, run
import matplotlib.pyplot as plt
import datetime
import threading
from matplotlib.animation import FuncAnimation

class ExchangeData:
    def __init__(self, label, ccxt_id, symbols):
        self.label = label
        self.ccxt_id = ccxt_id
        self.symbols = symbols
        self.time = []
        self.price = []
        self.opposite = None

    async def fetch_symbol(self, symbol):
        print(f'Starting {self.label} symbol loop with {symbol}')
        exchange = getattr(ccxt.pro, self.ccxt_id)({
            'newUpdates': True,  # https://github.com/ccxt/ccxt/wiki/ccxt.pro.manual#incremental-data-structures
        })

        while True:
            try:
                ticker = await exchange.watch_ticker(symbol)
                now = exchange.milliseconds()
                time = datetime.datetime.fromtimestamp(now / 1000)
                print(f'{exchange.iso8601(now)} {exchange.id} {symbol} bid: {ticker["bid"]} ask: {ticker["ask"]} last: {ticker["last"]} on {ticker["datetime"]}')
                self.time.append(time)
                self.price.append(ticker['last'])
            except Exception as e:
                print(str(e))
                break

    async def start_fetching(self):
        await gather(*(self.fetch_symbol(symbol) for symbol in self.symbols))

    def set_opposite(self, opposite):
        self.opposite = opposite

EXCHANGE_A_LABEL = 'binance-u'
EXCHANGE_A_CCXT_ID = 'binance'
EXCHANGE_A_SYMBOLS = ['WLD/USDT:USDT']

EXCHANGE_B_LABEL = 'okex'
EXCHANGE_B_CCXT_ID = 'okex'
EXCHANGE_B_SYMBOLS = ['WLD/USDT:USDT']

# Prepare a dictionary to store the data
data = {
    EXCHANGE_A_LABEL: ExchangeData(EXCHANGE_A_LABEL, EXCHANGE_A_CCXT_ID, EXCHANGE_A_SYMBOLS),
    EXCHANGE_B_LABEL: ExchangeData(EXCHANGE_B_LABEL, EXCHANGE_B_CCXT_ID, EXCHANGE_B_SYMBOLS),
}

for label, exchange_data in data.items():
    exchange_data.set_opposite(data[EXCHANGE_B_LABEL if label == EXCHANGE_A_LABEL else EXCHANGE_A_LABEL])

# Set up the plot
fig, axs = plt.subplots(2)

# Function to update the plot
def update(i):
    axs[0].clear()
    axs[1].clear()

    for label, exchange_data in data.items():
        axs[0].plot(exchange_data.time, exchange_data.price, label=label)

    if data[EXCHANGE_A_LABEL].time and data[EXCHANGE_B_LABEL].time:
        common_times = list(set(data[EXCHANGE_A_LABEL].time) & set(data[EXCHANGE_B_LABEL].time))
        common_times.sort()
        price_diffs = [data[EXCHANGE_A_LABEL].price[data[EXCHANGE_A_LABEL].time.index(time)] - data[EXCHANGE_B_LABEL].price[data[EXCHANGE_B_LABEL].time.index(time)] for time in common_times]
        axs[1].plot(common_times, price_diffs, label='Difference')

    axs[0].legend()
    axs[1].legend()

async def main():
    await gather(*(exchange_data.start_fetching() for exchange_data in data.values()))

# Start the asyncio event loop in a separate thread
threading.Thread(target=run, args=(main(),)).start()

# Start the animation
ani = FuncAnimation(fig, update, interval=20)  # update every 20ms

# Show the plot
plt.show()
