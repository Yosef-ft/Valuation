import datetime
import time

import numpy as np
import pandas as pd

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

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
        ratios.dropna(inplace=True)

        ratios.index.name = 'Year'
        ratios.index = pd.to_datetime(ratios.index, format='%Y').year   

        return ratios.sort_index(ascending=False)
    
    def _EV_EBITDA(self) -> pd.DataFrame:
        ratios = self.enterprise_value / self._Income_statement['EBITDA']
        ratios = pd.DataFrame(ratios, columns=['EV/EBITDA'])
        ratios.dropna(inplace=True)

        ratios.index.name = 'Year'
        ratios.index = pd.to_datetime(ratios.index, format='%Y').year   

        return ratios.sort_index(ascending=False)
    
    def _EV_Capital(self) -> pd.DataFrame:
        ratios = self.enterprise_value / self._Balance_sheet['Invested Capital']
        ratios = pd.DataFrame(ratios, columns=['EV/Invested Capital'])
        ratios.dropna(inplace=True)

        ratios.index.name = 'Year'
        ratios.index = pd.to_datetime(ratios.index, format='%Y').year       

        return ratios.sort_index(ascending=False)
    

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
    

class DDM:
    def __init__(self, symbol: str, req_return: float):
        self.symbol= symbol
        self.req_return = req_return / 100

        ticker =yf.Ticker(self.symbol)
        self.Dividends = ticker.dividends

        self._latest_price = float(ticker.history(period='1d')['Close'].values[-1])


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



st.set_page_config(layout="wide")

st.title('Stock Valuator')         
with st.expander('About this App'):
    st.write('This app calculates all enterprice ratios, equity ratios and also performs Discount Dividend Model(DDM) to identify if a stock is overpriced, underpriced')
    # st.image('https://th.bing.com/th/id/R.43137e38ed9b7298607ae8137c89b524?rik=Df4TCFL25fXEHQ&pid=ImgRaw&r=0', width=250)

st.sidebar.header('Chose your model')
model = st.sidebar.selectbox('Choose your value model', ['Enterprice Ratios', 'Equity Ratios', 'Discount Dividend Model(DDM)', 'Discount Cash Flow'])


if model == 'Enterprice Ratios':
    st.header('Enterprice Ratios')

    symbol = st.text_input('Please enter the company\'s ticker to evaluate the ratios (**Example** Microsoft would be MSFT)').upper()
    if symbol != '':
        try:
            enterM = EnterpriseMulti(symbol)

            company_name = yf.Ticker(symbol).info['longBusinessSummary'].split()[0]
            
            col1, col2, col3= st.columns(3)
            col4, col5, col6= st.columns(3)
            col7, col8, col9= st.columns(3)



            with col1:
                st.subheader('')

                EV_capital = enterM._EV_Capital()
                # st.write(EV_capital)
                if EV_capital.shape[0] != 0:
                    st.write('Enterprise value / Invested Capital ratio')

                    fig = px.line(EV_capital, y='EV/Invested Capital')
                    st.plotly_chart(fig)
                else:
                    st.write(f"sorry can't retrive data for {company_name} Plase try with another company.")



            with col2:
                st.subheader(company_name)

                EV_Revenue = enterM._EV_Revenue()
                # st.write(EV_Revenue)
                if EV_Revenue.shape[0] == 0:
                    st.write(f"sorry can't retrive data for {company_name} Plase try with another company.")
                else:
                    st.write('Enterprise value / Revenue ratio')
                    fig = px.line(EV_Revenue, y='EV/Revenue')
                    st.plotly_chart(fig)

            with col3:
                st.subheader('')

                EV_EBITDA = enterM._EV_EBITDA()
                # st.write(EV_EBITDA)
                if EV_EBITDA.shape[0] == 0:
                    st.write(f"sorry can't retrive data for {company_name} Plase try with another company.")
                else:
                    st.write('Enterprise value / EBITDA ratio')
                    fig = px.line(EV_EBITDA, y='EV/EBITDA')
                    st.plotly_chart(fig)

            symbol2 = ''

            if symbol2 == '':
                st.write(f'Compare {company_name} with another company?\n If yes Enter the company\'s symbol ')
            
                symbol2 = st.text_input('Please enter the second company\'s ticker to evaluate the ratios (**Example** Microsoft would be MSFT)').upper()
            if symbol2 != '':
                try: 
                    enterM2 = EnterpriseMulti(symbol2)
                    company_name2 = yf.Ticker(symbol2).info['longBusinessSummary'].split()[0]
                    
                    with col4:
                        st.subheader('')

                        EV_capital2 = enterM2._EV_Capital()
                        # st.write(EV_capital)
                        if EV_capital2.shape[0] == 0:
                            st.write(f"sorry can't retrive data for {company_name2} Plase try with another company.")
                        else:
                            st.write('Enterprise value / Invested Capital ratio')
                            fig = px.line(EV_capital2, y='EV/Invested Capital')
                            st.plotly_chart(fig)


                    with col5:
                        st.subheader(company_name2)

                        EV_Revenue2 = enterM2._EV_Revenue()
                        # st.write(EV_Revenue)
                        if EV_Revenue2.shape[0] == 0:
                            st.write(f"sorry can't retrive data for {company_name2} Plase try with another company.")
                        else:
                            st.write('Enterprise value / Revenue ratio')
                            fig = px.line(EV_Revenue2, y='EV/Revenue')
                            st.plotly_chart(fig)

                    with col6:
                        st.subheader('')

                        EV_EBITDA2 = enterM2._EV_EBITDA()
                        # st.write(EV_EBITDA)
                        if EV_EBITDA2.shape[0] == 0:
                            st.write(f"sorry can't retrive data for {company_name2} Plase try with another company.")
                        else:
                            st.write('Enterprise value / EBITDA ratio')
                            fig = px.line(EV_EBITDA2, y='EV/EBITDA')
                            st.plotly_chart(fig)

                    with col7:
                        st.subheader('')

                        st.write('Enterprise value / Invested Capital ratio')

                        fig2 = go.Figure()
                        fig2.add_trace(go.Line(x=EV_capital.index, y=EV_capital['EV/Invested Capital'], name=company_name,
                                                mode='lines', line=dict(color='Blue')))
                        fig2.add_trace(go.Line(x=EV_capital2.index, y=EV_capital2['EV/Invested Capital'], name=company_name2,
                                                mode='lines', line=dict(color='Red')))

                        st.plotly_chart(fig2)

                    with col8:
                        st.subheader(f'{company_name} vs {company_name2}')

                        st.write('Enterprise value / Revenue ratio')

                        fig2 = go.Figure()
                        fig2.add_trace(go.Line(x=EV_Revenue.index, y=EV_Revenue['EV/Revenue'], name=company_name,
                                                mode='lines', line=dict(color='Blue')))
                        fig2.add_trace(go.Line(x=EV_Revenue2.index, y=EV_Revenue2['EV/Revenue'], name=company_name2,
                                                mode='lines', line=dict(color='Red')))

                        st.plotly_chart(fig2)   

                    with col9:             
                        st.subheader('')

                        st.write('Enterprise value / EBITDA ratio')

                        fig2 = go.Figure()
                        fig2.add_trace(go.Line(x=EV_EBITDA.index, y=EV_EBITDA['EV/EBITDA'], name=company_name,
                                                mode='lines', line=dict(color='Blue')))
                        fig2.add_trace(go.Line(x=EV_EBITDA2.index, y=EV_EBITDA2['EV/EBITDA'], name=company_name2,
                                                mode='lines', line=dict(color='Red')))

                        st.plotly_chart(fig2)    
                except Exception as e:
                    st.write(f'Sorry we were not able to retrive {symbol2}. Please try with another symbol or check if the symbol exists.')                            
        except Exception as e:
            st.write(f'Sorry we were not able to retrive {symbol}. Please try with another symbol or check if the symbol exists.')

    else:
        st.write('Enter a symbol or ticker for the company of your choice')

    

elif model == 'Equity Ratios':
    st.header('Equity Ratios')

    symbol = st.text_input('Please enter the company\'s ticker to evaluate the ratios (**Example** Microsoft would be MSFT)').upper()
    if symbol != '':
        try:
            equityM = EquityMulti(symbol)
            company_name = yf.Ticker(symbol).info['longBusinessSummary'].split()[0]
            
            col1, col2, col3, col3a= st.columns(4)
            col4, col5, col6, col6a= st.columns(4)
            col7, col8, col9, col9a= st.columns(4)



            with col1:
                st.subheader('')

                P_E = equityM.P_E()
                if P_E.shape[0] == 0:
                    st.write(f"sorry can't retrive data for {company_name} Plase try with another company.")
                else:
                    st.write('P/E ratio')
                    fig = px.line(P_E, y='P/E ratio')
                    st.plotly_chart(fig)


            with col2:
                st.subheader('')

                Price_Book = equityM.Price_Book()
                if Price_Book.shape[0] == 0:
                    st.write(f"sorry can't retrive data for {company_name} Plase try with another company.")
                else:
                    st.write('Price/Book ratio')
                    fig = px.line(Price_Book, y='Price/Book')
                    st.plotly_chart(fig)

            with col3:
                st.subheader(company_name)

                Price_Sales = equityM.Price_Sales()
                if Price_Sales.shape[0] == 0:
                    st.write(f"sorry can't retrive data for {company_name} Plase try with another company.")
                else:
                    st.write('Price/Sales ratio')
                    fig = px.line(Price_Sales, y='Price/Sales')
                    st.plotly_chart(fig)

            with col3a:
                st.subheader('')

                div_yield = equityM.dividend_yield()
                if div_yield.shape[0] == 0:
                    st.write(f"sorry can't retrive data for {company_name} Plase try with another company.")
                else:
                    st.write('Dividend yields(%)')
                    fig = px.line(div_yield, y='Dividend yields(%)')
                    st.plotly_chart(fig)

            symbol2 = ''

            if symbol2 == '':
                st.write(f'Compare {company_name} with another company?\n If yes Enter the company\'s symbol ')
            
                symbol2 = st.text_input('Please enter the second company\'s ticker to evaluate the ratios (**Example** Microsoft would be MSFT)').upper()
            if symbol2 != '':
                try:
                    equityM2 = EquityMulti(symbol2)
                    company_name2 = yf.Ticker(symbol2).info['longBusinessSummary'].split()[0]
                    
                    with col4:
                        st.subheader('')

                        P_E2 = equityM2.P_E()
                        if P_E2.shape[0] == 0:
                            st.write(f"sorry can't retrive data for {company_name2} Plase try with another company.")
                        else:
                            st.write('P/E ratio')
                            fig = px.line(P_E2, y='P/E ratio')
                            st.plotly_chart(fig)


                    with col5:
                        st.subheader('')

                        Price_Book2 = equityM2.Price_Book()
                        if Price_Book2.shape[0] == 0:
                            st.write(f"sorry can't retrive data for {company_name2} Plase try with another company.")
                        else:
                            st.write('Price/Book ratio')
                            fig = px.line(Price_Book2, y='Price/Book')
                            st.plotly_chart(fig)

                    with col6:
                        st.subheader(company_name2)

                        Price_Sales2 = equityM2.Price_Sales()
                        if Price_Sales2.shape[0] == 0:
                            st.write(f"sorry can't retrive data for {company_name2} Plase try with another company.")
                        else:
                            st.write('Price/Sales ratio')
                            fig = px.line(Price_Sales2, y='Price/Sales')
                            st.plotly_chart(fig)

                    with col6a:
                        st.subheader('')

                        div_yield2 = equityM2.dividend_yield()
                        if div_yield2.shape[0] == 0:
                            st.write(f"sorry can't retrive data for {company_name2} Plase try with another company.")
                        else:
                            st.write('Dividend yields(%)')
                            fig = px.line(div_yield2, y='Dividend yields(%)')
                            st.plotly_chart(fig)

                    with col7:
                        st.subheader('')

                        st.write('P/E ratio ratio')

                        fig2 = go.Figure()
                        fig2.add_trace(go.Line(x=P_E.index, y=P_E['P/E ratio'], name=company_name,
                                                mode='lines', line=dict(color='Blue')))
                        fig2.add_trace(go.Line(x=P_E2.index, y=P_E2['P/E ratio'], name=company_name2,
                                                mode='lines', line=dict(color='Red')))

                        st.plotly_chart(fig2)

                    with col8:
                        st.subheader(f'{company_name} -versus- ')

                        st.write('Price/Book ratio')

                        fig2 = go.Figure()
                        fig2.add_trace(go.Line(x=Price_Book.index, y=Price_Book['Price/Book'], name=company_name,
                                                mode='lines', line=dict(color='Blue')))
                        fig2.add_trace(go.Line(x=Price_Book2.index, y=Price_Book2['Price/Book'], name=company_name2,
                                                mode='lines', line=dict(color='Red')))

                        st.plotly_chart(fig2)   

                    with col9:             
                        st.subheader(f'{company_name2}')

                        st.write('Price/Sales ratio')

                        fig2 = go.Figure()
                        fig2.add_trace(go.Line(x=Price_Sales.index, y=Price_Sales['Price/Sales'], name=company_name,
                                                mode='lines', line=dict(color='Blue')))
                        fig2.add_trace(go.Line(x=Price_Sales2.index, y=Price_Sales2['Price/Sales'], name=company_name2,
                                                mode='lines', line=dict(color='Red')))

                        st.plotly_chart(fig2)     

                    with col9a:
                        st.subheader('')

                        st.write('Dividend yields(%)')      

                        fig2 = go.Figure()
                        fig2.add_trace(go.Line(x=div_yield.index, y=div_yield['Dividend yields(%)'], name=company_name,
                                                mode='lines', line=dict(color='Blue')))
                        fig2.add_trace(go.Line(x=div_yield2.index, y=div_yield2['Dividend yields(%)'], name=company_name2,
                                                mode='lines', line=dict(color='Red')))

                        st.plotly_chart(fig2) 
                except Exception as e:
                    st.write(f'Sorry we were not able to retrive {symbol2}. Please try with another symbol or check if the symbol exists.')
        except Exception as e:
            st.write(f'Sorry we were not able to retrive {symbol}. Please try with another symbol or check if the symbol exists.')

    else:
        st.write('Enter a symbol or ticker for the company of your choice')    

elif model == 'Discount Dividend Model(DDM)':
    st.header('Discount Dividend Model')

    symbol = st.text_input('Please enter the company\'s ticker to evaluate the DDM to determine if the price is overprice/underpriced (**Example** Microsoft would be MSFT)').upper()
    req_return = st.number_input('Enter the required rate of return as a percentage for the year: ')

    if symbol != '':
        try:
            ddm = DDM(symbol, req_return)
            company_name = yf.Ticker(symbol).info['longBusinessSummary'].split()[0]
            st.header('')
            st.subheader(f'The company {company_name} is {ddm.price()}')
        except Exception as e:
            st.write(f'Sorry we were not able to retrive {symbol}. Please try with another symbol or check if the symbol exists.')
    else:
        st.write('Enter a symbol or ticker for the company of your choice')



elif model == 'Discount Cash Flow':
    st.header('Discount Cash Flow')
    my_bar = st.progress(0)
    
    for percent_complete in range(33):
        time.sleep(0.09)
        my_bar.progress(percent_complete + 1)

    
    st.subheader('Comming soon')
    st.write('Site under construction')

# if __name__ == "__main__":
#     enterM = EnterpriseMulti('MSFT')
#     print(enterM._EV_Capital())

#     Equit = EquityMulti('MSFT')
#     print(Equit.dividend_yield())

#     ddm = DDM('MSFT', 10)
#     print(ddm.price())