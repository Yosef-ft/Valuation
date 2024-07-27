import numpy as np
import pandas as pd

import streamlit as st
import plotly.express as px

import yfinance as yf


class EnterpriseMulti:
    def __init__(self, symbol:str):
        self.symbol = symbol

        self.load_data()

    # @st.cache_data
    def load_data(self):
        self._ticker = yf.Ticker(self.symbol)
        
        self._Balance_sheet = self._ticker.balance_sheet.transpose()
        self._Income_statement = self._ticker.income_stmt.transpose()

        self._latest_price = float(self._ticker.history(period='1d')['Close'].values[-1])

        self.equity_value = self._Balance_sheet['Ordinary Shares Number'] * self._latest_price
        self.enterprise_value = self.equity_value + self._Balance_sheet['Net Debt']

        # For equity ratios
        self.market_capitalization = self._Balance_sheet['Ordinary Shares Number'] * self._latest_price

        # calculating net book value 
        current_liabilities = self._Balance_sheet['Current Liabilities'] + self._Balance_sheet['Other Current Liabilities'] + self._Balance_sheet['Current Deferred Liabilities']
        non_current_liabilities = self._Balance_sheet['Non Current Deferred Liabilities'] + self._Balance_sheet['Other Non Current Liabilities'] + self._Balance_sheet['Non Current Deferred Liabilities']
        self._Balance_sheet['Total Liabilities'] = current_liabilities + non_current_liabilities
        self.Net_book_value = self._Balance_sheet['Total Assets'] - self._Balance_sheet['Total Liabilities'] - self._Balance_sheet['Total Equity Gross Minority Interest']

        # For Dividend yield
        ticker =yf.Ticker(self.symbol)
        self.Dividends = ticker.dividends

    
    def _EV_Revenue(self) -> pd.DataFrame:
        ratios = self.enterprise_value / self._Income_statement['Total Revenue']
        ratios = pd.DataFrame(ratios, columns=['EV/Revenue'])

        ratios.index = ratios.index.year
        ratios.index.name = 'Year'

        return ratios
    
    def _EV_EBITDA(self) -> pd.DataFrame:
        ratios = self.enterprise_value / self._Income_statement['EBITDA']
        ratios = pd.DataFrame(ratios, columns=['EV/EBITDA'])

        ratios.index = ratios.index.year
        ratios.index.name = 'Year'

        return ratios
    
    def _EV_Capital(self) -> pd.DataFrame:
        ratios = self.enterprise_value / self._Balance_sheet['Invested Capital']
        ratios = pd.DataFrame(ratios, columns=['EV/Invested Capital'])

        ratios.index = ratios.index.year
        ratios.index.name = 'Year'        

        return ratios
    

class EquityMulti(EnterpriseMulti):
    def __init__(self, symbol: str):
        super().__init__(symbol)


    def P_E(self) -> pd.DataFrame:
        ratios = self._latest_price / self._Income_statement['Diluted EPS']
        ratios = pd.DataFrame(ratios)
        ratios.rename({'Diluted EPS': 'P/E ratio'}, axis =1, inplace=True )

        ratios.index = ratios.index.year
        ratios.index.name = 'Year'          

        return ratios
    
    def Price_Book(self) -> pd.DataFrame:
        ratio = self.market_capitalization / self.Net_book_value
        ratio = pd.DataFrame(ratio, columns=['Price/Book'])

        return ratio
    
    def Price_Sales(self) -> pd.DataFrame:
        ratio = self.market_capitalization / self._Income_statement['Total Revenue']
        ratio = pd.DataFrame(ratio, columns=['Price/Sales'])

        return ratio
    

    def dividend_yield(self) -> pd.DataFrame:
        self.Dividends = pd.DataFrame(pd.to_datetime(self.Dividends.index), self.Dividends.values ).reset_index()
        self.Dividends.set_index('Date', inplace=True)
        self.Dividends.rename({'index': 'Quarterly dividends'}, axis = 1, inplace=True)
        self.Dividends = self.Dividends.groupby(self.Dividends.index.year)['Quarterly dividends'].sum()
        self.Dividends = pd.DataFrame(self.Dividends)
        self.Dividends.rename({'Quarterly dividends' : 'Yearly dividends'}, axis=1, inplace=True)
        self.Dividends.sort_index(ascending=False, inplace=True)

        self.Dividends['Dividend yields(%)'] = (self.Dividends['Yearly dividends'] / self._latest_price) * 100
        self.Dividends.drop('Yearly dividends', axis =1, inplace=True)

        return self.Dividends.head()
    



    

if __name__ == "__main__":
    enterM = EnterpriseMulti('MSFT')
    print(enterM._EV_Capital())

    Equit = EquityMulti('MSFT')
    print(Equit.dividend_yield())