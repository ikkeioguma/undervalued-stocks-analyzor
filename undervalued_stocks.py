import yfinance as yf
import pandas as pd
from flask import Flask, jsonify
import webbrowser
from colorama import Fore, Style


# Function to fetch data for the Russell 2000 index
def get_russell_2000_data():
    # Fetch historical data for the Russell 2000 index from a financial data provider
    russell_2000_data = yf.download('^RUT', start='2024-01-01', end='2024-06-01')
    return russell_2000_data

# Function to calculate ratios for the Russell 2000 index
def calculate_russell_2000_ratios(russell_2000_data):
    # Calculate ratios for the Russell 2000 index
    # For simplicity, let's just calculate average ratios for the period
    average_dividend_yield = russell_2000_data['Dividends'].mean() / russell_2000_data['Close'].mean()
    average_free_cash_flow_yield = (russell_2000_data['Free Cash Flow'] / russell_2000_data['Close']).mean()
    average_ev_to_ebitda = (russell_2000_data['Enterprise Value'] / russell_2000_data['EBITDA']).mean()
    
    russell_2000_ratios = {
        'dividend_yield': average_dividend_yield,
        'free_cash_flow_yield': average_free_cash_flow_yield,
        'ev_to_ebitda': average_ev_to_ebitda
    }
    return russell_2000_ratios

# Function to compare stock ratios with Russell 2000 index ratios
def compare_with_russell_2000(stock_ratios, russell_2000_ratios):
    # Compare the ratios of individual stocks with the Russell 2000 index ratios
    is_undervalued = (
        stock_ratios['dividend_yield'] > russell_2000_ratios['dividend_yield'] and
        stock_ratios['free_cash_flow_yield'] > russell_2000_ratios['free_cash_flow_yield'] and
        stock_ratios['ev_to_ebitda'] < russell_2000_ratios['ev_to_ebitda']
    )
    return is_undervalued

def get_small_cap_companies():
    # Fetch a list of small-cap companies from a stock screener API or financial data provider
    # Replace this with your implementation to fetch a larger list of tickers
    return ['PLUG', 'FUV', 'MVIS', 'AMD', 'NVDA', 'TSLA', 'AAPL', 'MSFT', 'AMZN', 'GOOGL','DJT']

def get_stock_data(ticker):
    try:
        stock = yf.Ticker(ticker)
        balance_sheet = stock.balance_sheet
        info = stock.info
        return balance_sheet, info
    except Exception as e:
        print(f"{Fore.RED}Error retrieving data for {ticker}: {e}{Style.RESET_ALL}")
        return None, None

def calculate_ratios(ticker, info, balance_sheet):
    if balance_sheet is None or info is None or balance_sheet.empty:
        print(f"{Fore.RED}Balance sheet or info not available for {ticker}{Style.RESET_ALL}")
        return None

    try:
        cash_cash_equivalents_and_short_term_investments = balance_sheet.loc['Cash Cash Equivalents And Short Term Investments'].iloc[0]
    except KeyError:
        cash_cash_equivalents_and_short_term_investments = 0

    try:
        other_short_term_investments = balance_sheet.loc['Other Short Term Investments'].iloc[0]
    except KeyError:
        other_short_term_investments = 0

    try:
        total_liabilities = balance_sheet.loc['Total Liab'].iloc[0]
    except KeyError:
        total_liabilities = 0

    market_cap = info.get('marketCap', None)
    if market_cap is None:
        print(f"{Fore.RED}Market cap data not available for {ticker}{Style.RESET_ALL}")
        return None

    net_cash = cash_cash_equivalents_and_short_term_investments + 0.7 * other_short_term_investments - total_liabilities
    net_cash_ratio = round(net_cash / market_cap, 3)

    per = round(info.get('trailingPE', 0.0), 3)
    ev_to_ebitda = round(info.get('enterpriseToEbitda', 0.0), 3)
    dividend_yield = round(info.get('dividendYield', 0.0), 3)
    free_cash_flow_yield = round(info.get('freeCashFlowYield', 0.0), 3)

    return {
        'ticker': ticker,
        'net_cash_ratio': net_cash_ratio,
        'per': per,
        'ev_to_ebitda': ev_to_ebitda,
        'dividend_yield': dividend_yield,
        'free_cash_flow_yield': free_cash_flow_yield
    }

def is_undervalued(stock_ratios):
    if stock_ratios is None:
        return False
    return (stock_ratios['net_cash_ratio'] > 0.9 and
            stock_ratios['per'] is not None and stock_ratios['per'] <= 15 and
            stock_ratios['dividend_yield'] is not None and
            stock_ratios['free_cash_flow_yield'] is not None and
            stock_ratios['ev_to_ebitda'] is not None)

def sort_stocks(stocks, sort_keys):
    return sorted(stocks, key=lambda x: [x[key] for key in sort_keys], reverse=True)

def find_undervalued_stocks():
    tickers = get_small_cap_companies()
    undervalued_stocks = []
    non_undervalued_stocks = []

    for ticker in tickers:
        try:
            balance_sheet, info = get_stock_data(ticker)
            stock_ratios = calculate_ratios(ticker, info, balance_sheet)
            if stock_ratios:
                if is_undervalued(stock_ratios):
                    undervalued_stocks.append(stock_ratios)
                else:
                    non_undervalued_stocks.append(stock_ratios)
        except Exception as e:
            print(f"{Fore.RED}Error processing {ticker}: {e}{Style.RESET_ALL}")

    sort_keys = ['net_cash_ratio', 'per', 'dividend_yield', 'free_cash_flow_yield', 'ev_to_ebitda']
    sorted_undervalued_stocks = sort_stocks(undervalued_stocks, sort_keys)
    sorted_non_undervalued_stocks = sort_stocks(non_undervalued_stocks, sort_keys)

    return sorted_undervalued_stocks, sorted_non_undervalued_stocks

app = Flask(__name__)

@app.route('/undervalued', methods=['GET'])
def undervalued():
    undervalued_stocks, non_undervalued_stocks = find_undervalued_stocks()

    print(f"{Fore.GREEN}Definition of Undervalued Stocks:{Style.RESET_ALL}")
    print("- Net Cash Ratio > 0.9")
    print("- Price-to-Earnings (P/E) Ratio <= 15")
    print("- Dividend Yield is not None")
    print("- Free Cash Flow Yield is not None")
    print("- Enterprise Value-to-EBITDA (EV/EBITDA) Ratio is not None")
    print("-" * 100)

    print(f"{Fore.GREEN}Undervalued Stocks (sorted by ratios):{Style.RESET_ALL}")
    print("-" * 100)
    print(f"{'Ticker':10} {'Net Cash Ratio':20} {'P/E':20} {'Div Yield':20} {'FCF Yield':20} {'EV/EBITDA':20}")
    print("-" * 100)

    for stock in undervalued_stocks:
        print(f"{stock['ticker']:10} {stock['net_cash_ratio']:20.3f} {stock['per']:20.3f} {stock['dividend_yield']:20.3f} {stock['free_cash_flow_yield']:20.3f} {stock['ev_to_ebitda']:20.3f}")

    print(f"{Fore.RED}\nNon-Undervalued Stocks (sorted by ratios):{Style.RESET_ALL}")
    print("-" * 100)
    print(f"{'Ticker':10} {'Net Cash Ratio':20} {'P/E':20} {'Div Yield':20} {'FCF Yield':20} {'EV/EBITDA':20}")
    print("-" * 100)

    for stock in non_undervalued_stocks:
        print(f"{stock['ticker']:10} {stock['net_cash_ratio']:20.3f} {stock['per']:20.3f} {stock['dividend_yield']:20.3f} {stock['free_cash_flow_yield']:20.3f} {stock['ev_to_ebitda']:20.3f}")

    return jsonify({})

if __name__ == "__main__":
    port = 5000
    url = f"http://127.0.0.1:{port}/undervalued"
    webbrowser.open(url)
    app.run(port=port)
if __name__ == "__main__":
    port = 5000
    url = f"http://127.0.0.1:{port}/undervalued"
    print(f"Opening {url} in your default web browser...")
    webbrowser.open(url)
    print("Starting Flask server. Press CTRL+C to quit.")
    app.run(port=port)
