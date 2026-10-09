"""A simple stock price tracker using Alpha Vantage and Plotly.

Install dependencies:
    pip install requests plotly

Get an API key from Alpha Vantage, then run:
    python stock_tracker_fixed.py
"""

from datetime import datetime

import plotly.express as px
import requests


API_URL = "https://www.alphavantage.co/query"
REQUEST_TIMEOUT = 15


def _fetch_series(symbol, api_key, function, series_key, date_format, interval=None):
    """Fetch a time series and return dates and closing prices in chronological order."""
    params = {
        "function": function,
        "symbol": symbol,
        "apikey": api_key,
    }

    if interval:
        params["interval"] = interval

    try:
        response = requests.get(API_URL, params=params, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.Timeout:
        print("The request timed out. Check your connection and try again.")
        return [], []
    except requests.exceptions.HTTPError as error:
        print(f"The stock-data service returned an HTTP error: {error}")
        return [], []
    except requests.exceptions.RequestException as error:
        print(f"Could not connect to the stock-data service: {error}")
        return [], []
    except ValueError:
        print("The stock-data service returned a response that was not valid JSON.")
        return [], []

    # Alpha Vantage may return an error message instead of stock data.
    if "Error Message" in data:
        print("The request was rejected. Check the stock symbol and API request.")
        return [], []

    if "Note" in data or "Information" in data:
        print(
            "Alpha Vantage returned a notice or rate-limit message. "
            "Check your API usage or try again later."
        )
        return [], []

    if series_key not in data:
        print(
            f"No {series_key} data was returned for {symbol}. "
            "Check the symbol, API key, and API response."
        )
        return [], []

    series = data[series_key]
    dates = []
    prices = []

    try:
        # ISO-formatted date strings sort from oldest to newest.
        for timestamp, values in sorted(series.items()):
            dates.append(datetime.strptime(timestamp, date_format))
            prices.append(float(values["4. close"]))
    except (KeyError, TypeError, ValueError):
        print("The stock-data response was missing or contained invalid price data.")
        return [], []

    return dates, prices


def daily_data(symbol, api_key):
    """Get daily closing prices."""
    return _fetch_series(
        symbol,
        api_key,
        function="TIME_SERIES_DAILY",
        series_key="Time Series (Daily)",
        date_format="%Y-%m-%d",
    )


def intraday_data(symbol, api_key):
    """Get five-minute intraday closing prices."""
    return _fetch_series(
        symbol,
        api_key,
        function="TIME_SERIES_INTRADAY",
        series_key="Time Series (5min)",
        date_format="%Y-%m-%d %H:%M:%S",
        interval="5min",
    )


def weekly_data(symbol, api_key):
    """Get weekly closing prices."""
    return _fetch_series(
        symbol,
        api_key,
        function="TIME_SERIES_WEEKLY",
        series_key="Weekly Time Series",
        date_format="%Y-%m-%d",
    )


def monthly_data(symbol, api_key):
    """Get monthly closing prices."""
    return _fetch_series(
        symbol,
        api_key,
        function="TIME_SERIES_MONTHLY",
        series_key="Monthly Time Series",
        date_format="%Y-%m-%d",
    )


def performance(dates, prices):
    """Return the highest closing price and its date, or (None, None) if invalid."""
    if not dates or not prices:
        return None, None

    if len(dates) != len(prices):
        print("Cannot calculate performance: dates and prices do not match.")
        return None, None

    max_index = 0
    max_price = prices[0]

    for index in range(1, len(prices)):
        if prices[index] > max_price:
            max_price = prices[index]
            max_index = index

    return max_price, dates[max_index]


def graph(time_stamps, closing_prices, title, time_format):
    """Display a line chart if matching data is available."""
    if not time_stamps or not closing_prices:
        print("There is no data to graph.")
        return

    if len(time_stamps) != len(closing_prices):
        print("Cannot graph the data: dates and prices do not match.")
        return

    chart_data = {"Time": time_stamps, "Price": closing_prices}
    figure = px.line(chart_data, x="Time", y="Price", title=title)
    figure.update_xaxes(tickformat=time_format, tickangle=45)
    figure.update_layout(
        title_font_size=28,
        xaxis_title_font_size=20,
        yaxis_title_font_size=20,
    )
    figure.show()


def main():
    """Run the interactive stock tracker."""
    api_key = input("Enter your Alpha Vantage API key: ").strip()
    if not api_key:
        print("An API key is required to retrieve stock data.")
        return

    stock_symbol = input("Enter the stock symbol (e.g., IBM): ").strip().upper()
    if not stock_symbol:
        print("A stock symbol is required.")
        return

    time_period = input(
        "Choose a graph: intraday, weekly, or monthly: "
    ).strip().lower()

    if time_period not in {"intraday", "weekly", "monthly"}:
        print("Please choose intraday, weekly, or monthly.")
        return

    if time_period == "intraday":
        dates, prices = intraday_data(stock_symbol, api_key)
        chart_dates = dates
        chart_prices = prices
        chart_title = f"{stock_symbol} Intraday (5-minute intervals)"
        date_format = "%H:%M"
    elif time_period == "weekly":
        dates, prices = weekly_data(stock_symbol, api_key)
        # Display the most recent 12 weekly data points, not just two.
        chart_dates = dates[-12:]
        chart_prices = prices[-12:]
        chart_title = f"{stock_symbol} - Latest 12 Weeks"
        date_format = "%b %d"
    else:
        dates, prices = monthly_data(stock_symbol, api_key)
        # Display the most recent 12 monthly data points.
        chart_dates = dates[-12:]
        chart_prices = prices[-12:]
        chart_title = f"{stock_symbol} - Latest 12 Months"
        date_format = "%b %Y"

    # Stop before indexing into a list if the API returned no usable data.
    if not dates or not prices:
        print("No usable stock data was found. Nothing else to display.")
        return

    graph(chart_dates, chart_prices, chart_title, date_format)

    best_price, best_date = performance(dates, prices)
    latest_price = prices[-1]

    if best_price is not None:
        print(f"Highest closing price in the returned data: ${best_price:.2f}")
        print(f"Date of highest close: {best_date:%Y-%m-%d}")
        print(f"Latest available closing price: ${latest_price:.2f}")


if __name__ == "__main__":
    main()
