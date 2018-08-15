import requests
import pandas as pd
import json
import time
import sys
import argparse

class BinancePy:
    """
    Constructs valid HTTP requests and queries data from binance api:
    https://github.com/binance-exchange/binance-official-api-docs/blob/master/rest-api.md
    """
    def __init__(self, api_version='v1'):
        self._base = 'https://api.binance.com/api/' + api_version

    def create_url(self, action, params):
        paramstr = ''.join('&{}={}'.format(k, v) for k, v in params.items())
        return '{}/{}?{}'.format(self._base, action, paramstr)

    def call_api(self, url):
        return json.loads(requests.get(url).text)

    def candlesticks(self, symbol, interval):
        """
        Return current market data based on interval window
        """
        url = self.create_url('klines', {'symbol'   : symbol,
                                         'interval' : interval,
                                         'limit'    : 1})
        return self.call_api(url)


class Cruncher:
    """
    Builds dataframes based on a specified window-length
    Runs calculations over the dataframes

    When querying market data with a specific window-length, the returned timestamp will remain constant for all queries within that window of time. This is how Crucher knows to either append the latest market data to an existing dataframe, or to begin a new dataframe.
    """
    def __init__(self):
        self._df = None
        self._current = None

    def transform_candle_data(self, data):
        """
        Convert list of lists into dataframe.
        Columns infered from api docs.
        """
        cols = ['open_time', 'open', 'high',
                'low', 'close', 'volume',
                'close_time', 'asset_volume',
                'num_trades', 'taker_buy_vol_base',
                'taker_buy_vol_asset', 'ignore']

        df = pd.DataFrame(data, columns=cols)
        return df

    def build_interval_df(self, data):
        """
        Construct dataframe by adding data from the last
        instance of the current candlestick interval
        """
        df = self.transform_candle_data(data)
        last_timestamp = df.open_time.values[0]

        if self._current == last_timestamp:
            self._df = pd.concat([self._df, df])
            self._new_interval = False
        else:
            self._current = last_timestamp
            self._df = df
            self._new_interval = True

    def stat_average(self, df, precision, stat='close'):
        return round(df[stat].astype(float).mean(), precision)


class Automator(BinancePy, Cruncher):
    """
    Queries binance every second for updated market data
    Displays the average price in the current interval window
    Resets average price when a new interval begins
    Runs until user exits manually
    """
    def __init__(self, trading_pair, precision, interval):
        self._symbol = trading_pair
        self._precision = int(precision)
        self._interval = interval

        Cruncher.__init__(self)
        BinancePy.__init__(self)

    def run(self):
        while True:

            # Query Binance
            try:
                data = self.candlesticks(symbol=self._symbol,
                                         interval=self._interval)
            except:
                print('Error: Is this a valid trading pair?')
                break

            # Find average price
            self.build_interval_df(data)
            avg = self.stat_average(self._df, self._precision)

            if self._new_interval:
                print('\n\n---New {} interval started---'\
                                                    .format(self._interval))

            sys.stdout.write('\rTrading Pair: {}, {} average: {}'\
                                                .format(self._symbol,
                                                        self._interval,
                                                        avg))
            sys.stdout.flush()

            time.sleep(1)   # Run every second


if __name__=='__main__':
    """
    Common trading pairs: BTCUSDT, ETHUSDT, ETHBTC
    BTC/USD with two points of precision will run by default

    Set --decimals to 7 or 8 for non-USDT or low volume pairs

    --interval determines time-period for context windows.
    Default set to 1 minute
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--pair', default='BTCUSDT')
    parser.add_argument('-d', '--decimals', default=2)
    parser.add_argument('-i',  '--interval', default='1m')
    args = parser.parse_args()

    auto = Automator(trading_pair=args.pair,
                     precision=args.decimals,
                     interval=args.interval)
    auto.run()

