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

        self.market_capitalization = self._Balance_sheet['Ordinary Shares Number'] * self._latest_price
        # calculating net book value 
        current_liabilities = self._Balance_sheet['Current Liabilities'] + self._Balance_sheet['Other Current Liabilities'] + self._Balance_sheet['Current Deferred Liabilities']
        non_current_liabilities = self._Balance_sheet['Non Current Deferred Liabilities'] + self._Balance_sheet['Other Non Current Liabilities'] + self._Balance_sheet['Non Current Deferred Liabilities']
        self._Balance_sheet['Total Liabilities'] = current_liabilities + non_current_liabilities
        self.Net_book_value = self._Balance_sheet['Total Assets'] - self._Balance_sheet['Total Liabilities'] - self._Balance_sheet['Total Equity Gross Minority Interest']


    
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
    



    

if __name__ == "__main__":
    enterM = EnterpriseMulti('MSFT')
    print(enterM._EV_Capital())

    Equit = EquityMulti('MSFT')
    print(Equit.P_E())