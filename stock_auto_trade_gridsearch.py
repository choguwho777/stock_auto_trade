# !pip install pandas_ta alpaca-py tqdm matplotlib

import math
import pandas as pd
import pandas_ta as ta
import numpy as np
import itertools

import matplotlib.pyplot as plt
from tqdm.notebook import tqdm
import unicodedata

import json

import time
from zoneinfo import ZoneInfo
import datetime as dt
from datetime import datetime, timedelta

from sklearn.model_selection import train_test_split

from google.colab import userdata

from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame

from alpaca.trading.client import TradingClient
from alpaca.trading.requests import GetCalendarRequest

# 기본 설정 ====================================================================

Alpaca_API_key = userdata.get("Alpaca_API_key")
Alpaca_secret_key = userdata.get("Alpaca_secret_key")
Alpaca_paper = True
data_client = StockHistoricalDataClient(Alpaca_API_key, Alpaca_secret_key)
trading_client = TradingClient(Alpaca_API_key, Alpaca_secret_key, paper = Alpaca_paper)

parameter_grid = {
    'stoch_buy': [20, 30, 40],
    'stoch_sell': [60, 70, 80],
    'stop_loss_ratio': [0.01, 0.015, 0.02],
    #'trailing_stop_ratio': [0.005, 0.010, 0.015]
                  }
allowed_position_count = 10 # 최대 보유 종목 수
allowed_account_ratio = 0.10 # 종목 당 허용 자산 비율

initial_account = 100000.0

EST = ZoneInfo("America/New_York")

start_date = datetime(2024, 7, 1, tzinfo = EST)
end_date = datetime(2024, 9, 30, tzinfo = EST)

# S&P 500 종목 리스트 ==========================================================

def get_SnP_tickers():
    try:
        URL = "https://raw.githubusercontent.com/datasets/s-and-p-500-companies/main/data/constituents.csv"
        df = pd.read_csv(URL)
        tickers = df["Symbol"].tolist()
        tickers = [ticker.replace("-", ".") for ticker in tickers]
        return tickers
    except Exception as e:
        print(f"[ERROR] S&P 500 종목 리스트 수집 실패: {e}")
        return [
            "A", "AAL", "AAPL", "ABBV", "ABNB", "ABT", "ACGL", "ACN", "ADBE", "ADI",
            "ADM", "ADP", "ADSK", "AEE", "AEP", "AES", "AFL", "AIG", "AIZ", "AJG",
            "AKAM", "ALB", "ALGN", "ALL", "ALLE", "AMAT", "AMCR", "AMD", "AME", "AMGN",
            "AMP", "AMT", "AMZN", "ANET", "ANSS", "AON", "AOS", "APA", "APD", "APH",
            "APTV", "ARE", "ATO", "AVB", "AVGO", "AVY", "AWK", "AXON", "AXP", "AZO",
            "BA", "BAC", "BALL", "BAX", "BBWI", "BBY", "BDX", "BEN", "BF.B", "BG",
            "BIIB", "BK", "BKNG", "BKR", "BLDR", "BLK", "BMY", "BR", "BRK.B", "BRO",
            "BSX", "BWA", "BX", "BXP", "C", "CAG", "CAH", "CARR", "CAT", "CB",
            "CBOE", "CBRE", "CCI", "CCJ", "CCL", "CDNS", "CDW", "CE", "CEG", "CF",
            "CFG", "CHD", "CHRW", "CHTR", "CI", "CINF", "CL", "CLX", "CMA", "CMG",
            "CMI", "CMS", "CNC", "CNP", "COF", "COO", "COP", "COR", "COST", "CPAY",
            "CPB", "CPRT", "CPT", "CRL", "CRM", "CRWD", "CSGP", "CSX", "CTAS", "CTRA",
            "CTSH", "CTVA", "CVS", "CVX", "CZR", "D", "DAL", "DAY", "DD", "DE",
            "DECK", "DELL", "DFS", "DG", "DGX", "DHI", "DHR", "DIS", "DLR", "DLTR",
            "DOC", "DOV", "DOW", "DPZ", "DRI", "DTE", "DUK", "DVA", "DVN", "DXCM",
            "EA", "EBAY", "ECL", "ED", "EFX", "EG", "EIX", "EL", "ELV", "EMR",
            "ENPH", "EOG", "EPAM", "EQIX", "EQR", "EQT", "ERIE", "ES", "ESS", "ETN",
            "ETR", "EVRG", "EW", "EXC", "EXPD", "EXPE", "EXR", "F", "FANG", "FAST",
            "FI", "FICO", "FIS", "FITB", "FMC", "FOX", "FOXA", "FRT", "FSLR", "FTNT",
            "FTV", "GD", "GDDY", "GE", "GEHC", "GEN", "GEV", "GILD", "GIS", "GL",
            "GLW", "GM", "GNRC", "GOOG", "GOOGL", "GPC", "GPK", "GPN", "GRMN", "GS",
            "GWW", "HAL", "HAS", "HBAN", "HCA", "HD", "AES", "HIG", "HII", "HLT",
            "HOLX", "HON", "HRL", "HSIC", "HST", "HSY", "HUBB", "HUM", "HWM", "IBM",
            "ICE", "IDXX", "IEX", "IFF", "INCX", "INCY", "INTC", "INTU", "INVH", "IP",
            "IPG", "IQV", "IR", "IRM", "ISRG", "IT", "ITW", "IVZ", "J", "JBHT",
            "JBL", "JCI", "JKHY", "JNJ", "JNPR", "JPM", "K", "KDP", "KEY", "KEYS",
            "KHC", "KIM", "KLAC", "KMB", "KMI", "KMX", "KO", "KR", "KVUE", "L",
            "LDOS", "LEN", "LH", "LHX", "LRCX", "LMT", "LNT", "LOW", "LRCX", "LULU",
            "LUV", "LVS", "LW", "LYB", "LYV", "MA", "MAA", "MAR", "MAS", "MCD",
            "MCHP", "MCK", "MCO", "MDLZ", "MDT", "MET", "META", "MGM", "MHK", "MKC",
            "MKTX", "MLM", "MMC", "MMM", "MNST", "MO", "MOH", "MOS", "MPC", "MPWR",
            "MRNA", "MRK", "MS", "MSCI", "MSFT", "MSI", "MTB", "MTD", "MU", "NCLH",
            "NDAQ", "NDSN", "NEE", "NEM", "NFLX", "NI", "NKE", "NLR", "NOC", "NOW",
            "NRG", "NSC", "NTAP", "NTR", "NTRS", "NUE", "NVDA", "NVR", "NWS", "NWSA",
            "NXPI", "O", "ODFL", "OKE", "OMC", "ON", "ORLY", "ORCL", "OTIS", "OXY",
            "PANW", "PARA", "PAYX", "PAYC", "PCAR", "PCG", "PEG", "PEP", "PFE", "PFG",
            "PG", "PGR", "PH", "PHM", "PKG", "PLD", "PLTR", "PM", "PNC", "PNR",
            "PNW", "PODD", "POOL", "PPG", "PPL", "PRU", "PSA", "PSX", "PTC", "PWR",
            "PYPL", "QCOM", "QRVO", "RCL", "REG", "REGN", "RF", "RJF", "RL", "RMD",
            "ROK", "ROL", "ROP", "ROST", "RSG", "SBAC", "SBUX", "SCCO", "SCHW", "SHW",
            "SJM", "SLB", "SMCI", "SNA", "SNPS", "SO", "SOLV", "SPG", "SPGI", "SRE",
            "STE", "STLD", "STT", "STX", "STZ", "SWK", "SWKS", "SYK", "SYF", "SYY",
            "T", "TAP", "TDG", "TDY", "TECH", "TEL", "TER", "TFC", "TFX", "TGT",
            "TJX", "TMO", "TMUS", "TPR", "TRGP", "TRMB", "TROW", "TRV", "TSCO", "TSLA",
            "TSN", "TT", "TTWO", "TXN", "TXT", "TYL", "UAL", "UBER", "UDR", "UHS",
            "ULTA", "UNH", "UNP", "UPS", "URI", "USB", "V", "VICI", "VLO", "VLTO",
            "VMC", "VRSK", "VRSN", "VRTX", "VST", "VTR", "VTRS", "VZ", "WAB", "WAT",
            "WBA", "WBD", "WDAY", "WDC", "WEC", "WELL", "WFC", "WM", "WMB", "WMT",
            "WRB", "WST", "WTW", "WY", "WYNN", "XEL", "XOM", "XYL", "YUM", "ZBH",
            "ZBRA", "ZTS"
        ]

# S&P 500 티커 층화 추출 =======================================================

def get_staratified_SnP_tickers(sample_size=50, random_state=42):
    try:
        url = "https://raw.githubusercontent.com/datasets/s-and-p-500-companies/main/data/constituents.csv"
        df = pd.read_csv(url)

        if not isinstance(df, pd.DataFrame):
            df = pd.DataFrame(df)

        symbol_col = 'Symbol' if 'Symbol' in df.columns else df.columns[0]
        sector_col = 'GICS Sector' if 'GICS Sector' in df.columns else ('Sector' if 'Sector' in df.columns else df.columns[1])

        df[symbol_col] = df[symbol_col].astype(str).str.replace('-', '.', regex=False)

        test_ratio = sample_size / len(df)

        _, sampled_df = train_test_split(
            df,
            test_size=test_ratio,
            stratify=df[sector_col],
            random_state=random_state,
        )
        tickers = sampled_df[symbol_col].tolist()
        print(f"S&P 500 섹터별 층화 추출 완료 / 총 {len(tickers)}개 종목 선택됨")
        return tickers

    except Exception as e:
        print(f"[ERROR] 층화 추출 실패: {e}")
        return

# 휴장일 반영 ==================================================================

def get_market_open_days(start_date, end_date):
    try:
        request = GetCalendarRequest(start = start_date, end = end_date)
        calendar = trading_client.get_calendar(request)
        open_days = [d.date for d in calendar]
        return open_days
    except Exception as e:
        print(f"[ERROR] 휴장일 조회 실패: {e}")
        # API 실패 시 전체 일자 반환 fallback
        return [start_date + timedelta(days=i) for i in range((end_date - start_date).days + 1)]

# 주가 데이터 수집 =============================================================

def load_backtest_data(data_client, sample_tickers, start_date, end_date):

    # 일봉 데이터 수집
    daily_chunk_size = 100
    try:
        daily_start_date = start_date - timedelta(days = 40)
        tickers = list(set(sample_tickers + ["SPY"]))
        daily_frames = []
        for i in tqdm(range(0, len(tickers), daily_chunk_size), desc = "일봉 데이터 수집 중"):
            chunk_tickers = tickers[i : i + daily_chunk_size]
            daily_request = StockBarsRequest(
                symbol_or_symbols = chunk_tickers,
                timeframe = TimeFrame.Day,
                start = daily_start_date,
                end = end_date
            )
            bars = data_client.get_stock_bars(daily_request).df.reset_index()
            daily_frames.append(bars)
            time.sleep(0.1)
        daily_bars = pd.concat(daily_frames, ignore_index = True)
        daily_bars['timestamp'] = pd.to_datetime(daily_bars['timestamp']).dt.tz_convert(EST)
        daily_bars['date'] = daily_bars['timestamp'].dt.date
        daily_bars.to_parquet("df_daily.parquet")
    except Exception as e:
        print(f"[ERROR] 일봉 데이터 수집 실패: {e}")
        return None, None

    # 5분봉 데이터 수집(EST 09:30 ~ 16:00)
    M5_chunk_size = 10
    try:
        M5_start_date = start_date - timedelta(days = 5)
        M5_frames = []
        for i in tqdm(range(0, len(sample_tickers), M5_chunk_size), desc = "5분봉 데이터 수집 중"):
            chunk_tickers = sample_tickers[i : i + M5_chunk_size]
            M5_request = StockBarsRequest(
                symbol_or_symbols = chunk_tickers,
                timeframe = TimeFrame(5, TimeFrame.Minute.unit),
                adjustment = 'split',
                start = M5_start_date,
                end = end_date
            )
            bars = data_client.get_stock_bars(M5_request).df.reset_index()
            M5_frames.append(bars)
            time.sleep(0.2)
        M5_bars = pd.concat(M5_frames, ignore_index = True)
        M5_bars['timestamp'] = pd.to_datetime(M5_bars['timestamp']).dt.tz_convert(EST)
        time_filter = (M5_bars['timestamp'].dt.time >= dt.time(9, 30)) & \
                      (M5_bars['timestamp'].dt.time <= dt.time(16, 0))
        df_M5 = M5_bars[time_filter].copy()
        df_M5.to_parquet("df_M5.parquet")
    except Exception as e:
        print(f"[ERROR] 5분봉 데이터 수집 실패: {e}")
        return None, None

    print("데이터 수집 완료")

# 지표 계산 ====================================================================

# 일봉 데이터
def calculate_daily_indicators():
    df_daily = pd.read_parquet("df_daily.parquet")
    processed = []
    for symbol, group in df_daily.groupby('symbol'):
        df = group.sort_values('date').copy()
        df['EMA_9'] = ta.ema(df['close'], length = 9)
        df['EMA_21'] = ta.ema(df['close'], length = 21)
        processed.append(df)
    df_daily_processed = pd.concat(processed, ignore_index = True)
    df_daily_processed.to_parquet("df_daily_processed.parquet")

# 5분봉 데이터
def calculate_M5_indicators():
    df_M5 = pd.read_parquet("df_M5.parquet")
    processed = []
    for symbol, group in df_M5.groupby('symbol'):
        df = group.sort_values('timestamp').copy()
        stoch_rsi = ta.stochrsi(df['close'], length = 14, rsi_length = 14, k = 3, d = 3)
        if stoch_rsi is not None and not stoch_rsi.empty:
            k_col = [col for col in stoch_rsi.columns if col.startswith("STOCHRSIk")][0]
            d_col = [col for col in stoch_rsi.columns if col.startswith("STOCHRSId")][0]
            df['stoch_k'] = stoch_rsi[k_col]
            df['stoch_d'] = stoch_rsi[d_col]
        else:
            print(f"[ERROR] {symbol} / stoch RSI 계산 실패")
            df['stoch_k'] = None
            df['stoch_d'] = None
        processed.append(df)
    df_M5_processed = pd.concat(processed, ignore_index = True)
    df_M5_processed.to_parquet("df_M5_processed.parquet")

# 매매 루프 ====================================================================

def run_backtest(df_daily, dict_M5_symbol, tickers, open_days, parameter):
    stoch_buy = parameter['stoch_buy']
    stoch_sell = parameter['stoch_sell']
    stop_loss_ratio = parameter['stop_loss_ratio']
    #trailing_stop_ratio = parameter['trailing_stop_ratio']
    cash = initial_account
    positions = {}
    trade_logs = []
    daily_equity_log = []
    for current_date in tqdm(open_days, desc = "백테스트 진행 중", leave = False):
        past_daily = df_daily[df_daily['date'] < current_date]
        # 1차 필터
        spy_past = past_daily[past_daily['symbol'] == 'SPY'].sort_values('date')
        if len(spy_past) < 30:
            daily_equity_log.append({'date': current_date, 'equity': cash})
            continue
        if not ((spy_past.iloc[-1]['close'] > spy_past.iloc[-1]['EMA_9']) and (spy_past.iloc[-1]['EMA_9'] > spy_past.iloc[-1]['EMA_21'])):
            daily_equity_log.append({'date': current_date, 'equity': cash})
            continue
        # 2차 필터
        passed_stocks = []
        for ticker in sample_tickers:
            t_daily = past_daily[past_daily['symbol'] == ticker].sort_values('date')
            if len(t_daily) < 30:
                continue
            last = t_daily.iloc[-1]
            if (last['close'] > last['EMA_9']) and (last['EMA_9'] > last['EMA_21']):
                passed_stocks.append(ticker)
        if not passed_stocks:
            daily_equity_log.append({'date': current_date, 'equity': cash})
            continue
        # 매매 루프
        time_steps = pd.date_range(
            start = f"{current_date} 09:30:00",
            end = f"{current_date} 16:00:00",
            freq = "5min",
            tz = EST
        )
        for current_time in time_steps:
            curr_time_obj = pd.to_datetime(current_time).time()
            # 매도 조건 검사
            for symbol in list(positions.keys()):
                sym_df = dict_M5_symbol.get(symbol)
                if sym_df is None:
                    continue
                try:
                    idx = sym_df.index.get_loc(current_time)
                except KeyError:
                    continue
                if idx < 2:
                    continue
                last1 = sym_df.iloc[idx - 1]
                last2 = sym_df.iloc[idx - 2]
                curr_price = float(last1['close'])
                pos = positions[symbol]
                entry_price = pos['entry_price']
                # 트레일링 스탑 가격 갱신
                #if curr_price > pos['highest_price']:
                    #pos['highest_price'] = curr_price
                #trailing_stop_price = pos['highest_price'] * (1 - trailing_stop_ratio)
                # 손절/익절 조건
                #trailing_stop = curr_price <= trailing_stop_price
                stop_loss = (curr_price - entry_price) / entry_price <= -stop_loss_ratio
                stoch_dead_cross = (last2['stoch_k'] >= last2['stoch_d']) and (last1['stoch_k'] < last1['stoch_d'])
                if stop_loss or ((last1['stoch_k'] >= stoch_sell) and stoch_dead_cross):
                    reason = "고정 손절" if stop_loss else "stoch RSI 매도"
                    cash += pos['qty'] * curr_price
                    pnl = (curr_price - pos['entry_price']) * pos['qty']
                    trade_logs.append({
                        'timestamp': current_time, 'symbol': symbol, 'side': 'SELL',
                        'price': curr_price, 'qty': pos['qty'], 'pnl': pnl, 'reason': reason
                    })
                    del positions[symbol]
            # 매수 조건 검사 (EST 10:30 ~ 13:30)
            if dt.time(10, 30) <= curr_time_obj < dt.time(13, 30):
                available_slots = allowed_position_count - len(positions)
                if available_slots > 0:
                    buy_targets = []
                    for ticker in passed_stocks:
                        if ticker in positions:
                            continue
                        sym_df = dict_M5_symbol.get(ticker)
                        if sym_df is None:
                            continue
                        try:
                            idx = sym_df.index.get_loc(current_time)
                        except KeyError:
                            continue
                        if idx < 2:
                            continue
                        last1 = sym_df.iloc[idx - 1]
                        last2 = sym_df.iloc[idx - 2]
                        stoch_golden_cross = (last2['stoch_k'] <= last2['stoch_d']) and (last1['stoch_k'] > last1['stoch_d'])
                        if (last1['stoch_k'] <= stoch_buy) and stoch_golden_cross:
                            buy_targets.append({'symbol': ticker, 'stoch_k': last1['stoch_k'], 'price': last1['close']})
                    # stoch RSI 오름차순 정렬(우선 순위 설정) 후 매수
                    buy_targets.sort(key = lambda x: x['stoch_k'])
                    for target in buy_targets[:available_slots]:
                        sym = target['symbol']
                        curr_price = float(target['price'])
                        total_equity = cash + sum(p['qty'] * curr_price for p in positions.values())
                        target_cost = total_equity * allowed_account_ratio
                        qty = math.floor(target_cost / curr_price)
                        max_qty = math.floor(cash / curr_price)
                        qty = min(qty, max_qty)
                        if qty > 0:
                            cash -= qty * curr_price
                            positions[sym] = {'qty': qty, 'entry_price': curr_price, 'highest_price': curr_price}
                            trade_logs.append({
                                'timestamp': current_time, 'symbol': sym, 'side': 'BUY',
                                'price': curr_price, 'qty': qty, 'pnl': 0.0, 'reason': '매수 조건 충족'
                            })
            # 장 마감 일괄 매도 (EST 15:50 ~ 16:00)
            if dt.time(15, 50) <= curr_time_obj <= dt.time(16, 0):
                for symbol in list(positions.keys()):
                    sym_df = dict_M5_symbol.get(symbol)
                    if sym_df is None:
                        continue
                    try:
                        idx = sym_df.index.get_loc(current_time)
                    except KeyError:
                        continue
                    if idx < 1:
                        continue
                    last1 = sym_df.iloc[idx -1]
                    curr_price = float(last1['close'])
                    pos = positions[symbol]
                    cash += pos['qty'] * curr_price
                    pnl = (curr_price - pos['entry_price']) * pos['qty']
                    trade_logs.append({
                        'timestamp': current_time, 'symbol': symbol, 'side': 'SELL',
                        'price': curr_price, 'qty': pos['qty'], 'pnl': pnl, 'reason': '장 마감 일괄 매도'
                    })
                    del positions[symbol]
        daily_equity = cash + sum(p['qty'] * p['highest_price'] for p in positions.values())
        daily_equity_log.append({'date': current_date, 'equity': daily_equity})
    return pd.DataFrame(trade_logs), pd.DataFrame(daily_equity_log)

# 수익률 그래프 ================================================================

def plot_results(equity_df, mdd):
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize = (12, 7), sharex = True, gridspec_kw = {'height_ratios': [2, 1]})

    ax1.plot(equity_df.index, equity_df['equity'], label = 'Portfolio Equity ($)', color = 'blue')
    ax1.axhline(y=initial_account, color = 'red', linestyle = '--', label = 'Initial account')
    ax1.set_title('Equity Curve', fontsize = 14)
    ax1.set_ylabel('Account Value ($)')
    ax1.legend(loc = 'upper left')
    ax1.grid(True, alpha = 0.3)

    ax2.fill_between(equity_df.index, equity_df['drawdown'], 0, color = 'red', alpha = 0.3, label = 'Drawdown (%)')
    ax2.set_title(f'Drawdown (MDD: {mdd:.2f}%)', fontsize = 12)
    ax2.set_xlabel('Date')
    ax2.set_ylabel('Drawdown (%)')
    ax2.legend(loc = 'lower left')
    ax2.grid(True, alpha = 0.3)

    plt.tight_layout()
    plt.show()

# 결과 테이블 정렬 =============================================================

def get_display_width(text):
    width = 0
    for char in str(text):
        if unicodedata.east_asian_width(char) in ["W", "F"]:
            width += 2
        else:
            width += 1
    return width

def pad_right(text, target_width):
    text_str = str(text)
    current_width = get_display_width(text_str)
    padding = max(0, target_width - current_width)
    return " " * padding + text_str

def print_clean_table(df, title=""):
    if title:
        print(f"[{title}]")
    str_df = df.astype(str)
    col_widths = {}
    for col in str_df.columns:
        max_w = max([get_display_width(col)] + [get_display_width(val) for val in str_df[col]])
        col_widths[col] = max_w + 3
    header_str = "".join([pad_right(col, col_widths[col]) for col in str_df.columns])
    print(header_str)
    total_table_width = sum(col_widths.values())
    print("-" * total_table_width)
    for _, row in str_df.iterrows():
        row_str = "".join([pad_right(row[col], col_widths[col]) for col in str_df.columns])
        print(row_str)

# 실행 =========================================================================

# 종목 리스트 설정(get_SnP_tickers or get_staratified_SnP_tickers)
sample_tickers = get_SnP_tickers()
# 층화 추출 티커로 같은 기간 반복 테스트 시 실행하지 않고 저장된 리스트 활용(json)
#sample_tickers = get_staratified_SnP_tickers(sample_size=50, random_state=42)
#with open("sample_tickers.json", "w") as f:
#    json.dump(sample_tickers, f)
#with open("sample_tickers.json", "r") as f:
#    sample_tickers = json.load(f)

# 주가 데이터 수집 및 지표 계산
# 같은 기간 반복 테스트 시 실행하지 않고 저장된 데이터 활용(parquet)
load_backtest_data(data_client, sample_tickers, start_date, end_date)
calculate_daily_indicators()
calculate_M5_indicators()

# 그리드서치
keys, values = zip(*parameter_grid.items())
parameter_combinations = [dict(zip(keys, v)) for v in itertools.product(*values)]
print(f"그리드서치 시작 / 총 {len(parameter_combinations)}개 조합")
open_days = get_market_open_days(start_date, end_date)
try:
    df_daily = pd.read_parquet("df_daily_processed.parquet")
    df_M5 = pd.read_parquet("df_M5_processed.parquet")
except Exception as e:
    print(f"[ERROR] 데이터 parquet 로드 실패: {e}")
# 데이터 딕셔너리 렌더링
dict_M5_time = {}
for ts, group in df_M5.groupby('timestamp'):
    dict_M5_time[ts] = group.set_index('symbol').to_dict('index')
dict_M5_symbol = {}
for sym, group in df_M5.groupby('symbol'):
    dict_M5_symbol[sym] = group.sort_values('timestamp').set_index('timestamp')
# 결과 저장 변수 초기화
last_stop_loss_BB_ratio = None
df_M5_prepared = None
grid_results = []
best_return = -float('inf')
best_mdd = 0.0
best_equity_df = pd.DataFrame()
best_trades_df = pd.DataFrame()
best_param = None
for parameter in tqdm(parameter_combinations, desc = "그리드서치 진행 중", leave = False):
    # 백테스트
    trades_df, equity_df = run_backtest(df_daily, dict_M5_symbol, sample_tickers, open_days, parameter)
    # 결과 종합
    if not equity_df.empty:
        equity_df["date"] = pd.to_datetime(equity_df["date"])
        equity_df.set_index("date", inplace=True)
        equity_df["peak"] = equity_df["equity"].cummax()
        equity_df["drawdown"] = ((equity_df["equity"] - equity_df["peak"]) / equity_df["peak"] * 100)
        mdd = equity_df["drawdown"].min()
        final_equity = equity_df.iloc[-1]["equity"]

        total_return = ((final_equity - initial_account) / initial_account) * 100
        if not trades_df.empty:
            sells = trades_df[trades_df["side"] == "SELL"]
            total_trades = len(sells)
            win_trades = len(sells[sells["pnl"] > 0])
            win_rate = ((win_trades / total_trades * 100) if total_trades > 0 else 0)
            total_pnl = sells["pnl"].sum()
        else:
            total_trades, win_rate, total_pnl = 0, 0.0, 0.0

        res = parameter.copy()
        res.update({
            "final_equity": final_equity,
            "total_return": total_return,
            "mdd": mdd,
            "total_trades": total_trades,
            "win_rate": win_rate,
            "total_pnl": total_pnl,
            })
        grid_results.append(res)

        if total_return > best_return:
            best_return = total_return
            best_mdd = mdd
            best_equity_df = equity_df
            best_trades_df = trades_df
            best_param = parameter
# 결과 출력
results_df = pd.DataFrame(grid_results)
if not results_df.empty:
    results_df = results_df.sort_values(by="total_return", ascending = False).reset_index(drop = True)
    display_results = results_df.copy()
    display_results["final_equity"] = display_results["final_equity"].map("{:,.2f}($)".format)
    display_results["total_return"] = display_results["total_return"].map("{:,.2f}%".format)
    display_results["mdd"] = display_results["mdd"].map("{:,.2f}%".format)
    display_results["total_trades"] = display_results["total_trades"].map("{:,}회".format)
    display_results["win_rate"] = display_results["win_rate"].map("{:,.2f}%".format)
    display_results["total_pnl"] = display_results["total_pnl"].map("${:,.2f}".format)
    display_results.columns = ["stoch_BUY", "stoch_SELL", "SL", "최종 자산", "수익률", "MDD", "매도 건수", "승률", "총 손익"]
    print(f"\n")
    print_clean_table(display_results, title = "그리드서치 결과 요약 (수익률 순)")
    print(f"\n")

if best_param is not None:
    print("[최고 수익률 파라미터 조합 상세 결과]")
    print(
        f"- 파라미터 : stoch_BUY: {best_param['stoch_buy']} / "
                     f"stoch_SELL: {best_param['stoch_sell']} / "
                     f"stop_loss_ratio: {best_param['stop_loss_ratio']}"
    )
    print(f"- 최종 자산: ${best_equity_df.iloc[-1]['equity']:,.2f}")
    print(f"- 수익률   : {best_return:+.2f}%")
    print(f"- MDD      : {best_mdd:.2f}%")

    if not best_trades_df.empty:
        sells = best_trades_df[best_trades_df["side"] == "SELL"]
        total_trades = len(sells)
        win_trades = len(sells[sells["pnl"] > 0])
        win_rate = (win_trades / total_trades * 100) if total_trades > 0 else 0
        print(f"- 매도 건수: {total_trades}회")
        print(f"- 승률     : {win_rate:.2f}%")
        print(f"- 총 손익  : ${sells['pnl'].sum():+,.2f}")
        print(f"\n")

        reason_summary = (
            sells.groupby("reason").agg(
            count=("pnl", "count"),
            total_pnl=("pnl", "sum"),
            avg_pnl=("pnl", "mean"),
        ).reset_index()
        )
        reason_summary["count"] = reason_summary["count"].map("{:,}회".format)
        reason_summary["total_pnl"] = reason_summary["total_pnl"].map("{:,.2f}($)".format)
        reason_summary["avg_pnl"] = reason_summary["avg_pnl"].map("{:,.2f}($)".format)
        reason_summary.columns = ["매도 사유", "매도 건수", "총 손익", "평균 손익"]
        print_clean_table(reason_summary, title = "매도 사유 집계")
    # 수익률 그래프
    plot_results(best_equity_df, best_mdd)
