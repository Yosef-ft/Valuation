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
    


        

