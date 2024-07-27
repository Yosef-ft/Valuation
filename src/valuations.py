import datetime

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
        self.dividends = pd.DataFrame(pd.to_datetime(self.Dividends.index), self.Dividends.values ).reset_index()
        self.dividends.set_index('Date', inplace=True)
        self.dividends.rename({'index': 'Quarterly dividends'}, axis = 1, inplace=True)
        self.dividends = self.dividends.groupby(self.dividends.index.year)['Quarterly dividends'].sum()
        self.dividends = pd.DataFrame(self.dividends)
        self.dividends.rename({'Quarterly dividends' : 'Yearly dividends'}, axis=1, inplace=True)
        self.dividends.sort_index(ascending=False, inplace=True)

        self.dividends['Dividend yields(%)'] = (self.dividends['Yearly dividends'] / self._latest_price) * 100
        self.dividends.drop('Yearly dividends', axis =1, inplace=True)

        return self.dividends.head()
    

class DDM(EnterpriseMulti):
    def __init__(self, symbol: str, req_return: float):
        super().__init__(symbol)
        self.req_return = req_return / 100

    def ddm_calc(self) -> float:
        self.dividends = pd.DataFrame(self.Dividends)
        self.dividends = self.dividends.groupby(self.dividends.index.year)['Dividends'].sum()
        self.dividends = pd.DataFrame(self.dividends).sort_index(ascending=False)

        growth_rate = self.dividends['Dividends'].pct_change().mean()

        self.dividends.drop(self.dividends.index[self.dividends.index == datetime.datetime.now().year], inplace = True)
        self.dividends = self.dividends.sort_index()
        self.dividends.index = pd.to_datetime(self.dividends.index, format='%Y')

        # Forecast for the next 5 years
        for i in range(5):
            next_year = self.dividends.iloc[-1].values + (growth_rate * self.dividends.iloc[-1].values)
            self.dividends.loc[pd.to_datetime(self.dividends.index.max().year + 1, format='%Y')] = next_year

        self.dividends.index = self.dividends.index.year
        self.dividends.sort_index(ascending=False, inplace=True)

        dividends_5y = self.dividends.head()

        # Calculate the DDM price for the forecaseted 5 years
        counter = 1
        DDM_price = 0
        for i in range(len(dividends_5y) - 1):
            DDM_price += (dividends_5y.iloc[-1-i].values) / ((1 + self.req_return) ** counter)
            counter += 1


        DDM_price += (self.req_return + dividends_5y.iloc[0].values) / ((1 + self.req_return) ** counter)     

        return DDM_price   
    
    def price(self) -> str:
        DDM_price = self.ddm_calc()

        if self._latest_price > DDM_price:
            return 'Overpriced! This is a sell signal.'
        else:
            return 'Underpriced! This is a buy signal'

            

    

if __name__ == "__main__":
    enterM = EnterpriseMulti('MSFT')
    print(enterM._EV_Capital())

    Equit = EquityMulti('MSFT')
    print(Equit.dividend_yield())

    ddm = DDM('MSFT', 10)
    print(ddm.price())