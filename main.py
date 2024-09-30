#region imports
from AlgorithmImports import *
from datetime import timedelta
#endregion

class SeasonalWADStopLossAlgorithm(QCAlgorithm):
    def Initialize(self):
        self.SetStartDate(1985, 1, 1)  # Set the start date for backtesting
        self.SetEndDate(2023, 12, 31)  # Set the end date for backtesting
        self.SetCash(100000)  # Set the initial capital

        # List of stocks to trade
        self.stocks = ["AMAT", "BKNG", "AVGO", "BR", "MCHP", "MKTX", "NOC", "PENN", "PG", "SPGI", "SBUX", "TER", "VFC"]

        # Dictionary to store trade dates and other trade-specific data
        self.trade_dates = {
            "AMAT": {"buy": (3, 15), "sell": (4, 15), "profit": 5.01, "stop_loss": 0}, 
            "BKNG": {"buy": (2, 20), "sell": (3, 25), "profit": 4.50, "stop_loss": 0}, 
            "AVGO": {"buy": (1, 10), "sell": (2, 20), "profit": 6.00, "stop_loss" : 0}, 
            "BR": {"buy": (4, 1), "sell": (5, 10), "profit": 5.25, "stop_loss": 0}, 
            "MCHP": {"buy": (5, 5), "sell": (6, 15), "profit": 4.75, "stop_loss":0}, 
            "MKTX": {"buy": (6, 1), "sell": (7, 10), "profit": 5.50, "stop_loss": 0},
            "NOC": {"buy": (7, 15), "sell": (8, 25), "profit": 6.10, "stop_loss": 0},
            "PENN": {"buy": (8, 20), "sell": (9, 30), "profit": 4.80, "stop_loss": 0},
            "PG": {"buy": (9, 10), "sell": (10, 20), "profit": 5.00, "stop_loss": 0},
            "SPGI": {"buy": (10, 1), "sell": (11, 10), "profit": 5.15, "stop_loss":0},
            "SBUX": {"buy": (11, 15), "sell": (12, 25), "profit": 5.40, "stop_loss": 0},
            "TER": {"buy": (12, 5), "sell": (1, 15), "profit": 5.30, "stop_loss":0},
            "VFC": {"buy": (1, 1), "sell": (2, 10), "profit": 4.90, "stop_loss": 0}
        }

        # Add equities to the algorithm
        for ticker in self.stocks:
            self.AddEquity(ticker, Resolution.Daily)

    def OnData(self, data):
        today = self.Time.date()  # Convert datetime to date for comparison

        for ticker in self.stocks:

            symbol = self.Symbol(ticker)
            if not data.ContainsKey(symbol) or data[symbol] is None or not data[symbol].Close:
                continue  # Skip if no data or invalid data for the ticker

            bar = data[symbol]
            buy_date = datetime(today.year, *self.trade_dates[ticker]['buy']).date()  # Ensure date type
            sell_date = datetime(today.year, *self.trade_dates[ticker]['sell']).date()  # Ensure date type

            # 3 Days before/after buy date            
            if  (buy_date - timedelta(days=3) <= today <= buy_date) or (buy_date <= today <= buy_date + timedelta(days=3)):
                # Calculate WAD here or retrieve from indicators
                wad = self.CalculateWAD(bar)

                # Check if WAD is bullish and buy condition is met
                if wad > 0 and not self.Portfolio[ticker].Invested:
                    self.SetHoldings(symbol, 1 / len(self.stocks))
                    self.Log(f"Bought {ticker} at {bar.Close} wad was {wad}")
                    # set initial stop
                    self.trade_dates[ticker]['stop_loss'] = self.Portfolio[ticker].Price * 0.95
                    self.Log(f"Set stop loss to {bar.Close * 0.95}")

            if self.Portfolio[ticker].Invested:

                # Raise stop loss when hit avg profit
                if bar.Close >= (self.trade_dates[ticker]['profit']+ self.Portfolio[ticker].AveragePrice):
                    self.trade_dates[ticker]["stop_loss"] = self.Portfolio[ticker].AveragePrice
                    self.Log(f"Stop loss set to breakeven - {self.Portfolio[ticker].AveragePrice}")
                    self.Log(f'Average profit was {self.trade_dates[ticker]["profit"] + self.Portfolio[ticker].AveragePrice}')

                # Check if it's time to sell
                if today >= sell_date:
                    self.Liquidate(symbol)
                    self.Log(f"Sold {ticker} at {bar.Close}")

                # Stop loss
                if self.Portfolio[ticker].Price <= self.trade_dates[ticker]["stop_loss"]:
                    self.Liquidate(symbol)
                    self.Log(f'Stopped out of trade price is {self.Portfolio[ticker].Price} and stop was {self.trade_dates[ticker]["stop_loss"]}')

    def CalculateWAD(self, bar):
        symbol = bar.Symbol
        
        # Initialize previous close if this is the first time calculating WAD
        if not hasattr(self, 'previous_closes'):
            self.previous_closes = {}

        # If this is the first bar for the symbol, we can't calculate WAD
        if symbol not in self.previous_closes:
            self.previous_closes[symbol] = bar.Close
            return 0  # No WAD for the first bar

        # Get the previous close price
        previous_close = self.previous_closes[symbol]

        # Calculate True Range High (TRH) and True Range Low (TRL)
        TRH = max(bar.High, previous_close)
        TRL = min(bar.Low, previous_close)

        # Accumulation/Distribution Calculation
        if bar.Close > previous_close:
            AD = bar.Close - TRL
        elif bar.Close < previous_close:
            AD = bar.Close - TRH
        else:
            AD = 0  # If close is equal to previous close, AD is 0

        # Initialize cumulative WAD dictionary if needed
        if not hasattr(self, 'cumulative_wad'):
            self.cumulative_wad = {}
        
        # Initialize cumulative WAD for the symbol if not present
        if symbol not in self.cumulative_wad:
            self.cumulative_wad[symbol] = 0
        
        # Update the cumulative WAD value
        self.cumulative_wad[symbol] += AD

        # Update previous close for the next calculation
        self.previous_closes[symbol] = bar.Close

        # Return the updated WAD value
        return self.cumulative_wad[symbol]

    def OnEndOfDay(self):
        # Log end-of-day values for stocks
        for ticker in self.stocks:
            symbol = self.Symbol(ticker)
            if self.Portfolio[symbol].Invested:
                self.Log(f"End of Day {ticker} Price: {self.Securities[symbol].Price}")
