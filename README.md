# Opening Range Breakout (ORB) Trading Bot

A Python-based automated trading bot that implements an **Opening Range Breakout (ORB)** strategy for **US100 (Nasdaq)** using the MetaTrader 5 API.

The bot monitors the market during the trading session, identifies breakouts above or below the opening range, and executes trades automatically. Position sizing is calculated based on a fixed dollar risk per trade using the previous day's ATR (Average True Range), ensuring consistent risk management.

## Features

* Automated trade execution through MetaTrader 5
* Opening Range Breakout (ORB) strategy
* ATR-based stop-loss calculation
* Fixed-risk position sizing
* Maximum trades per session
* Automatic end-of-session position closing
* One-position-at-a-time trade management

## Technologies

* Python
* MetaTrader 5 Python API
* Pandas
* NumPy

## Disclaimer

This project is intended for educational and research purposes only. Trading financial markets involves substantial risk, and past performance does not guarantee future results.
