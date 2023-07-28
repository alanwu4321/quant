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

class VirtualExchange:
    def __init__(self, initial_balance):
        self.balance = initial_balance
        self.holdings = 0
        self.position = 0  # 0: 空倉，1: 多倉
        self.profits = [initial_balance]  # 紀錄獲利的列表，起始值為初始資金

    def place_order(self, symbol, price, quantity, side):
        if side == 'buy':
            self.holdings += quantity
            self.balance -= price * quantity
            self.position = 1
        elif side == 'sell':
            self.holdings -= quantity
            self.balance += price * quantity
            self.position = 0

        # 更新套利策略的績效曲線
        self.profits.append(self.balance + self.holdings * price)

    def get_balance(self):
        return self.balance + self.holdings * data['okex'].price[-1]

    def get_mdd(self):
        peak = self.balance
        mdd = 0
        for price in data['okex'].price:
            balance = self.balance + self.holdings * price
            peak = max(peak, balance)
            drawdown = (balance - peak) / peak
            mdd = min(mdd, drawdown)
        return mdd



EXCHANGE_A_LABEL = 'binance-u'
EXCHANGE_A_CCXT_ID = 'binance'
EXCHANGE_A_SYMBOLS = ['ETH/USDT:USDT']

EXCHANGE_B_LABEL = 'okex'
EXCHANGE_B_CCXT_ID = 'okex'
EXCHANGE_B_SYMBOLS = ['ETH/USDT:USDT']

# Prepare a dictionary to store the data
data = {
    EXCHANGE_A_LABEL: ExchangeData(EXCHANGE_A_LABEL, EXCHANGE_A_CCXT_ID, EXCHANGE_A_SYMBOLS),
    EXCHANGE_B_LABEL: ExchangeData(EXCHANGE_B_LABEL, EXCHANGE_B_CCXT_ID, EXCHANGE_B_SYMBOLS),
}

for label, exchange_data in data.items():
    exchange_data.set_opposite(data[EXCHANGE_B_LABEL if label == EXCHANGE_A_LABEL else EXCHANGE_A_LABEL])

# Set up the plot
fig, axs = plt.subplots(2)



virtual_binance = VirtualExchange(1000)
virtual_okex = VirtualExchange(1000)
def trade_logic():
    price_diff_threshold = 0.6
    exit_threshold = 0.2

    for i in range(1, len(data['binance-u'].price)):
        binance_price = data['binance-u'].price[i]
        okex_price = data['okex'].price[i]
        price_diff = binance_price - okex_price

        if price_diff > price_diff_threshold and not virtual_binance.position:
            quantity = virtual_okex.balance / okex_price
            virtual_binance.place_order('ETH/USDT', binance_price, quantity, 'sell')
            virtual_okex.place_order('ETH/USDT', okex_price, quantity, 'buy')

        if price_diff < exit_threshold and virtual_binance.position:
            quantity = virtual_binance.holdings
            virtual_binance.place_order('ETH/USDT', binance_price, quantity, 'buy')
            virtual_okex.place_order('ETH/USDT', okex_price, quantity, 'sell')


# Function to update the plot
def update(i):
    axs[0].clear()
    axs[1].clear()
    
    trade_logic()  # Execute trading logic

    axs[0].plot(data['binance-u'].time, data['binance-u'].price, label='binance-u')
    axs[0].plot(data['okex'].time, data['okex'].price, label='okex')
    axs[0].legend()

    # 將套利策略的資產曲線顯示在資金曲線圖中
    axs[1].plot(data['okex'].time, virtual_binance.profits, label='Arbitrage Strategy')
    axs[1].legend()

    # Update title to show MDD
    mdd = virtual_binance.get_mdd()
    axs[1].set_title(f'MDD: {mdd:.2f}')

    for label, exchange_data in data.items():
        axs[0].plot(exchange_data.time, exchange_data.price, label=label)

    if data[EXCHANGE_A_LABEL].time and data[EXCHANGE_B_LABEL].time:
        common_times = list(set(data[EXCHANGE_A_LABEL].time) & set(data[EXCHANGE_B_LABEL].time))
        common_times.sort()
        price_diffs = [data[EXCHANGE_A_LABEL].price[data[EXCHANGE_A_LABEL].time.index(time)] - data[EXCHANGE_B_LABEL].price[data[EXCHANGE_B_LABEL].time.index(time)] for time in common_times]
        axs[1].plot(common_times, price_diffs, label='Difference')

    #axs[0].legend()
    #axs[1].legend()
    

async def main():
    await gather(*(exchange_data.start_fetching() for exchange_data in data.values()))
# Start the asyncio event loop in a separate thread
threading.Thread(target=run, args=(main(),)).start()

# Start the animation
ani = FuncAnimation(fig, update, interval=2)  # update every 20ms

# Show the plot
plt.show()
