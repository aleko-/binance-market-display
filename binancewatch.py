import requests
import pandas as pd
import json
import time
import sys
import argparse

class BinancePy:
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
    def __init__(self, trading_pair='BTCUSDT', precision=2, interval='1m'):
        self._symbol = trading_pair
        self._precision = int(precision)
        self._interval = interval

        Cruncher.__init__(self)
        BinancePy.__init__(self)

    def run(self):
        """
        Query the current market data of the given interval window
        Display the average close price of the current interval window
        Reset average when new interval window begins
        """
        while True:
            try:
                data = self.candlesticks(symbol=self._symbol,
                                         interval=self._interval)
            except:
                print('Error: Is this a valid trading pair?')
                break

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
    Default set to 1 minute for this exercise.
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

