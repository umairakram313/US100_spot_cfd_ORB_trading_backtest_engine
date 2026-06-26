import MetaTrader5 as mt5
import pandas as pd
import numpy as np
import pytz
import datetime as dt
from enum import Enum
import matplotlib.pyplot as plt


class state(Enum):
    WITHIN_RANGE=0
    BULLISH_BREAKOUT=1
    BEARISH_BREAKOUT=2
    BULLISH_CONFIRMATION=3
    BEARISH_CONFIRMATION=4
    LONG_ENTRY=5
    SHORT_ENTRY=6
    LONG_PARTIAL_TP_HIT=7
    SHORT_PARTIAL_TP_HIT=8
    LONG_FULL_SL_HIT=9
    SHORT_FULL_SL_HIT=10
    LONG_TRAIL_SL_HIT=11
    SHORT_TRAIL_SL_HIT=12
    LONG_FULL_TP_HIT=13
    SHORT_FULL_TP_HIT=14
    INCOMP_LONG=15
    INCOMP_SHORT=16
    TP_SL_NOTSURE=17

class volatility(Enum):
    HIGH_VOL=0
    NORMAL_VOL=1
    LOW_VOL=2

class trend(Enum):
    CHOPPY_TREND=0
    NEUTRAL_TREND=1
    TRENDY_TREND=2


def fetch_daily_data():
    mt5.initialize()

    symbol = "US100.cash"

    timezone = pytz.timezone("Etc/UTC")

    start_date = dt.datetime(year=2020, month=1, day=1, tzinfo=timezone)
    end_date = dt.datetime(year=2026, month=6, day=2, tzinfo=timezone)

    data = mt5.copy_rates_range(
        symbol,
        mt5.TIMEFRAME_D1,
        start_date,
        end_date
    )

    data = pd.DataFrame(data)

    data['time'] = pd.to_datetime(data['time'], unit='s')

    data.to_csv("daily_ohlcv_nasdaq.csv", index=False)

def make_daily_atr_relvol():

    data = pd.read_csv("daily_ohlcv_nasdaq.csv")

    data['time'] = pd.to_datetime(data['time'])

    # True Range
    data['prev_close'] = data['close'].shift(1)

    data['tr1'] = data['high'] - data['low']
    data['tr2'] = abs(data['high'] - data['prev_close'])
    data['tr3'] = abs(data['low'] - data['prev_close'])

    data['TR'] = data[['tr1', 'tr2', 'tr3']].max(axis=1)

    # ATR(14)
    data['ATR_14'] = data['TR'].rolling(14).mean()

    # IMPORTANT:
    # shift by 1 day to avoid lookahead bias
    data['ATR_14_shifted'] = data['ATR_14'].shift(1)

    data = data[['time', 'ATR_14_shifted']]

    data.to_csv("daily_ohlcv_nasdaq.csv", index=False)

def fetch_5min_data():
    mt5.initialize()

    symbol="US100.cash"

    timezone = pytz.timezone("Etc/UTC")
    start_date=dt.datetime(year=2021, month=9, day=15, tzinfo=timezone)
    end_date=dt.datetime(year=2026, month=6, day=2, tzinfo=timezone)


    data=mt5.copy_rates_range(symbol, mt5.TIMEFRAME_M5, start_date, end_date)
    data=pd.DataFrame(data)
    data['time']=pd.to_datetime(data['time'], unit='s')

    data.to_csv("5_min_ohlcv_nasdaq.csv", index=False)

def fetch_1min_data():
    mt5.initialize()

    symbol="US100.cash"

    timezone = pytz.timezone("Etc/UTC")
    start_date=dt.datetime(year=2021, month=9, day=15, tzinfo=timezone)
    end_date=dt.datetime(year=2026, month=6, day=2, tzinfo=timezone)


    data=mt5.copy_rates_range(symbol, mt5.TIMEFRAME_M1, start_date, end_date)
    data=pd.DataFrame(data)
    data['time']=pd.to_datetime(data['time'], unit='s')

    data.to_csv("1_min_ohlcv_nasdaq.csv", index=False)


def initiate_backtest_file():
    open_cand_data = pd.read_csv("5_min_ohlcv_nasdaq.csv")
    open_cand_data['time'] = pd.to_datetime(open_cand_data['time'])

    atr_data = pd.read_csv("daily_ohlcv_nasdaq.csv")
    atr_data['time'] = pd.to_datetime(atr_data['time'])

    # Extract date
    open_cand_data['date'] = open_cand_data['time'].dt.date
    atr_data['date'] = atr_data['time'].dt.date

    # Merge ATR
    open_cand_data = open_cand_data.merge(
        atr_data[['date', 'ATR_14_shifted']],
        on='date',
        how='left'
    )

    # Select opening 5-minute candle
    open_cand_data = open_cand_data[
        open_cand_data['time'].dt.time == dt.time(16, 30)
    ].reset_index(drop=True)

    #relative volume
    open_cand_data['average_vol_14d']=open_cand_data['tick_volume'].rolling(window=14).mean().shift(1)
    open_cand_data['relative_vol']=open_cand_data['tick_volume']/open_cand_data['average_vol_14d']
    open_cand_data = open_cand_data.dropna(subset=['relative_vol'])

    #open range/ATR

    open_cand_data['OR-ATR']=(open_cand_data['high']-open_cand_data['low'])/open_cand_data['ATR_14_shifted']
    
    # Create backtest framework
    backtest_data = pd.DataFrame({
        'time': open_cand_data['time'],
        'state': state.WITHIN_RANGE.name,
        'ATR':open_cand_data['ATR_14_shifted'],
        '5_min_high': open_cand_data['high'],
        '5_min_low': open_cand_data['low'],
        '5_min_range':open_cand_data['high']-open_cand_data['low'],
        'relative_vol': open_cand_data['relative_vol'],
        'OR-ATR': open_cand_data['OR-ATR'],
        '5_min_polarity': np.where(open_cand_data['close'] >= open_cand_data['open'],'Bullish','Bearish')
    })

    # Initialize future columns
    cols_to_init = [
        'entry_price', 'TP', 'SL', 'PnL'
    ]

    backtest_data[cols_to_init] = 0.0


    backtest_data.to_csv("backtest_file.csv", index=False)

def backtesting():

    backtest_data=pd.read_csv("backtest_file.csv")
    backtest_data['time']=pd.to_datetime(backtest_data['time'])

    
    iterate_data=pd.read_csv("1_min_ohlcv_nasdaq.csv")
    iterate_data['time']=pd.to_datetime(iterate_data['time'])

    grouped_data = {
    date: group.reset_index(drop=True)
    for date, group in iterate_data.groupby(iterate_data['time'].dt.date)
    }

    for idx in range(len(backtest_data)):
        row=backtest_data.iloc[idx]

        no_of_trades=0
        
        risk=0
        pos_size = 0
        tp_points=0
        sl_points=0

        related_data = grouped_data.get(row['time'].date())
        if related_data is None:
            continue
        related_data = related_data[(related_data['time'].dt.time >= dt.time(16, 35))&(related_data['time'].dt.time <= dt.time(23, 40))]
        related_data=related_data.reset_index(drop=True)

        for ipx in range(len(related_data)):
            cand=related_data.iloc[ipx]
            
            #upside breakout
            if backtest_data.loc[idx, 'state']==state.WITHIN_RANGE.name and cand['close']>backtest_data.loc[idx, '5_min_high']:
                backtest_data.loc[idx, 'state']=state.BULLISH_CONFIRMATION.name
            
            #downside breakout
            elif backtest_data.loc[idx, 'state']==state.WITHIN_RANGE.name and cand['close']<backtest_data.loc[idx, '5_min_low']:
                backtest_data.loc[idx, 'state']=state.BEARISH_CONFIRMATION.name

            #upside-entry
            elif backtest_data.loc[idx, 'state']==state.BULLISH_CONFIRMATION.name:
                backtest_data.loc[idx, 'state']=state.LONG_ENTRY.name
                no_of_trades=no_of_trades+1
                risk = 100 
                backtest_data.loc[idx, 'entry_price']=cand['open']
                sl_points= (0.05*backtest_data.loc[idx, 'ATR'])
                tp_points=2*sl_points
                pos_size=risk/sl_points
                backtest_data.loc[idx, 'SL']=backtest_data.loc[idx, 'entry_price']-sl_points
                backtest_data.loc[idx, 'TP']=backtest_data.loc[idx, 'entry_price']+tp_points
            #downside-entry
            elif backtest_data.loc[idx, 'state']==state.BEARISH_CONFIRMATION.name:
                backtest_data.loc[idx, 'state']=state.SHORT_ENTRY.name
                no_of_trades=no_of_trades+1
                risk = 100 
                backtest_data.loc[idx, 'entry_price']=cand['open']
                sl_points= (0.05*backtest_data.loc[idx, 'ATR'])
                tp_points=2*sl_points
                pos_size=risk/sl_points
                backtest_data.loc[idx, 'SL']=backtest_data.loc[idx, 'entry_price']+sl_points
                backtest_data.loc[idx, 'TP']=backtest_data.loc[idx, 'entry_price']-tp_points

            #upside-full-sl
            if backtest_data.loc[idx, 'state']==state.LONG_ENTRY.name and cand['low']<=backtest_data.loc[idx, 'SL']:
                backtest_data.loc[idx, 'PnL']=backtest_data.loc[idx, 'PnL']-((backtest_data.loc[idx, 'entry_price']-backtest_data.loc[idx, 'SL'])*pos_size)
                backtest_data.loc[idx, 'state']=state.LONG_FULL_SL_HIT.name
                break
                
            #long partial tp hit
            if backtest_data.loc[idx, 'state']==state.LONG_ENTRY.name and cand['high']>=backtest_data.loc[idx, 'TP']:
                backtest_data.loc[idx, 'state']=state.LONG_PARTIAL_TP_HIT.name
                backtest_data.loc[idx, 'PnL']=backtest_data.loc[idx, 'PnL']+((backtest_data.loc[idx, 'TP']-backtest_data.loc[idx, 'entry_price'])*pos_size/2)
                backtest_data.loc[idx, 'SL']=backtest_data.loc[idx, 'entry_price']
                backtest_data.loc[idx, 'TP']=backtest_data.loc[idx, 'TP']+tp_points


            #long trail sl hit
            if backtest_data.loc[idx, 'state']==state.LONG_PARTIAL_TP_HIT.name and cand['low']<=backtest_data.loc[idx, 'SL']:
                backtest_data.loc[idx, 'state']=state.LONG_TRAIL_SL_HIT.name
                break
            #long full tp hit
            if backtest_data.loc[idx, 'state']==state.LONG_PARTIAL_TP_HIT.name and cand['high']>=backtest_data.loc[idx, 'TP']:
                backtest_data.loc[idx, 'state']=state.LONG_FULL_TP_HIT.name
                backtest_data.loc[idx, 'PnL']=backtest_data.loc[idx, 'PnL']+((backtest_data.loc[idx, 'TP']-backtest_data.loc[idx, 'entry_price'])*pos_size/2)
                break

            #downside-full-sl
            if backtest_data.loc[idx, 'state']==state.SHORT_ENTRY.name and cand['high']>=backtest_data.loc[idx, 'SL']:
                backtest_data.loc[idx, 'PnL']=backtest_data.loc[idx, 'PnL']-((backtest_data.loc[idx, 'SL']-backtest_data.loc[idx, 'entry_price'])*pos_size)
                backtest_data.loc[idx, 'state']=state.SHORT_FULL_SL_HIT.name
                break

            #short partial tp hit
            if backtest_data.loc[idx, 'state']==state.SHORT_ENTRY.name and cand['low']<=backtest_data.loc[idx, 'TP']:
                backtest_data.loc[idx, 'state']=state.SHORT_PARTIAL_TP_HIT.name
                backtest_data.loc[idx, 'PnL']=backtest_data.loc[idx, 'PnL']+((backtest_data.loc[idx, 'entry_price']-backtest_data.loc[idx, 'TP'])*pos_size/2)
                backtest_data.loc[idx, 'SL']=backtest_data.loc[idx, 'entry_price']
                backtest_data.loc[idx, 'TP']=backtest_data.loc[idx, 'TP']-tp_points


            #short trail sl hit
            if backtest_data.loc[idx, 'state']==state.SHORT_PARTIAL_TP_HIT.name and cand['high']>=backtest_data.loc[idx, 'SL']:
                backtest_data.loc[idx, 'state']=state.SHORT_TRAIL_SL_HIT.name
                break
            #short full tp hit
            if backtest_data.loc[idx, 'state']==state.SHORT_PARTIAL_TP_HIT.name and cand['low']<=backtest_data.loc[idx, 'TP']:
                backtest_data.loc[idx, 'state']=state.SHORT_FULL_TP_HIT.name
                backtest_data.loc[idx, 'PnL']=backtest_data.loc[idx, 'PnL']+((backtest_data.loc[idx, 'entry_price']-backtest_data.loc[idx, 'TP'])*pos_size/2)
                break
            


    backtest_data.to_csv("backtest_file.csv", index=False)


def make_rel_cols_2():
    data=pd.read_csv("backtest_file.csv")

    # --- Cumulative PnL (simple) ---
    data['cum_PnL'] = data['PnL'].cumsum()
    data['cum_PnL']=round(data['cum_PnL'], 3)
    data.to_csv("backtest_file.csv", index=False)

start_per=dt.datetime(year=2021, month=1, day=1)
end_per=dt.datetime(year=2025, month=1, day=1)

def compute_stats():
    global start_per, end_per
    data=pd.read_csv("backtest_file.csv")
    data['time']=pd.to_datetime(data['time'])
    data=data[(data['time']>=start_per)&(data['time']<=end_per)]
    # data=data[data['relative_vol']>1]
    win_accumu=0
    loss_accumu=0
    no_of_wins=0
    no_of_loss=0
    effective_win_no=0
    effective_loss_no=0

    for idx, row in data.iterrows():
        if row['PnL']>0:
            win_accumu=win_accumu+row['PnL']
            no_of_wins=no_of_wins+1
        elif row['PnL']<0:
            loss_accumu=loss_accumu-row['PnL']
            no_of_loss=no_of_loss+1

    equity = data['PnL'].cumsum()

    running_peak = equity.cummax()
    drawdown = equity - running_peak

    max_drawdown = drawdown.min()

    

    definite_trades=no_of_wins+no_of_loss
    avg_win=win_accumu/no_of_wins
    avg_loss=loss_accumu/no_of_loss

    expectancy=data['PnL'].sum()/(no_of_wins+no_of_loss)

    # ----- Sharpe Ratio -----

    pnl_series = data['PnL']

    mean_pnl = pnl_series.mean()
    std_pnl = pnl_series.std()

    # annualization assuming ~252 trading days
    sharpe_ratio = (mean_pnl / std_pnl) * np.sqrt(252)

    print("win rate: ", (no_of_wins/(no_of_wins+no_of_loss))*100)
    #print("effective_win_rate: ", (effective_win_no/(effective_win_no+effective_loss_no))*100)
    print("avg win: ", avg_win, ", avg loss: ", avg_loss)
    print("max drawdown: ",max_drawdown)
    print("Expectancy: ", expectancy)
    print("sharpe ratio: ", sharpe_ratio)
    print("missed trades: ",  len(data)-definite_trades, " percentage missed: ", (len(data) - definite_trades)/len(data), " %\n")




def plot_equity():
    global start_per, end_per
    data=pd.read_csv("backtest_file.csv")
    data['time']=pd.to_datetime(data['time'])
    data=data[(data['time']>=start_per)&(data['time']<=end_per)]
    data = data.sort_index()
    data['cum_PnL'] = data['PnL'].cumsum()
    data['cum_PnL']=round(data['cum_PnL'], 3)
    print(f"Rows after filter: {len(data)}")
    plt.figure(figsize=(16, 8))
    plt.plot(data.index, data['cum_PnL'])
    plt.xlabel("Number of Trades")
    plt.ylabel("Cumulative PnL")
    plt.title("Cumulative PnL Curve")
    plt.grid()
    plt.show()


def test_func():
    data=pd.read_csv("backtest_file.csv")
    data=data[data['PnL']>0].copy()
    print(data['no_of_SL'].quantile(0.95))
    # for i in range(10):
    #     j=i-0.5
    #     print(data['no_of_SL'].quantile((j+1)/10))
    

def pre_backtest():
    fetch_daily_data()
    make_daily_atr_relvol()
    fetch_5min_data()
    fetch_1min_data()


def backtest_process():
    initiate_backtest_file()
    backtesting()
    make_rel_cols_2()
    
def post_backtest():
    compute_stats()
    plot_equity()

pre_backtest()
backtest_process()
post_backtest()
# test_func()


