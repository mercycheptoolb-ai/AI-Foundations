"""Fetch Tesla's latest price from Yahoo Finance using yfinance."""

import yfinance as yf


def main() -> None:
    ticker = yf.Ticker("TSLA")
    price = ticker.fast_info["last_price"]
    print(f"Yahoo Finance access: successful")
    print(f"Tesla (TSLA): {price:.2f} USD")


if __name__ == "__main__":
    main()
