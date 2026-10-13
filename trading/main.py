import os
from dotenv import load_dotenv

import requests
import math
import pandas as pd
import pandas_ta as ta

from zoneinfo import ZoneInfo
import time
import datetime
from datetime import time as dtime

from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame

from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest, LimitOrderRequest, ClosePositionRequest, GetOrdersRequest
from alpaca.trading.enums import OrderSide, TimeInForce, QueryOrderStatus

# 기본 설정 ====================================================================

env_path = "/home/ubuntu/stock_auto_trade/.env"
load_dotenv(dotenv_path = env_path)
Alpaca_API_key = os.environ.get("Alpaca_API_key")
Alpaca_secret_key = os.environ.get("Alpaca_secret_key")
paper = True # 모의투자: True
data_client = StockHistoricalDataClient(Alpaca_API_key, Alpaca_secret_key) # 데이터 클라이언트
trading_client = TradingClient(Alpaca_API_key, Alpaca_secret_key, paper = paper) # 트레이딩 클라이언트
# Toss API
Toss_client_ID = os.environ.get("Toss_client_ID")
Toss_client_secret = os.environ.get("Toss_client_secret")

# Telegram API
Telegram_token = os.environ.get("Telegram_token")
Telegram_chat_ID = os.environ.get("Telegram_chat_ID")

# 파라미터 설정
RSI_threshold = 50 # RSI(매수 조건)

trailing_stop_ratio = 0.005 # 트레일링 스탑 비율(매도 조건)
stop_loss_BB_ratio = 1.0 # 볼린저밴드 비율(손절가 기준)

allowed_position_count = 10 # 최대 보유 종목 수
allowed_account_ratio = 0.10 # 종목 당 허용 자산 비율

# 미국 동부 시간 설정
EST = ZoneInfo("America/New_York")
EST_today = datetime.datetime.now(EST).date()

# 함수 정의 ====================================================================

# state
class tradingstate:
    def __init__(self):
        self.is_trading_enabled = True
        self.trade_list = []
state = tradingstate()

# global
highest_prices = {}

# S&P 500 종목 리스트(wikipedia)
def get_SnP_tickers():
    try:
        url = "https://raw.githubusercontent.com/datasets/s-and-p-500-companies/main/data/constituents.csv"
        df = pd.read_csv(url)
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
SnP_tickers = get_SnP_tickers()

# 매도 신호 검사 및 주문(Alpaca)
def sell_order(data_client, trading_client, start_date_market):
    global highest_prices
    # 매도 신호 검사
    # 보유 종목 조회
    try:
        positions = trading_client.get_all_positions()
        if not positions:
            print("매도 신호 검사 종료: 보유 중인 종목 없음")
            return
    except Exception as e:
        print(f"[ERROR] 매도 신호 검사 종료: 보유 종목 조회 실패: {e}")
        return
    # 5분봉 데이터 수집(최근 5일)
    tickers = [position.symbol for position in positions]
    request = StockBarsRequest(
        symbol_or_symbols = tickers,
        timeframe = TimeFrame.Minute,
        timeframe_value = 5,
        start = start_date_market,
    )
    try:
        bars = data_client.get_stock_bars(request)
        combined_df = bars.df
    except Exception as e:
        print(f"[ERROR] 매도 신호 검사 종료: 5분봉 데이터 수집 실패: {e}")
        return
    # 매도 신호 검사
    for position in positions:
        symbol = position.symbol
        QTY = float(position.qty)
        current_price = float(position.current_price)
        # 트레일링 스탑 기준 최신화
        if (symbol not in highest_prices or current_price > highest_prices[symbol]):
            highest_prices[symbol] = current_price
        trailing_stop_price = highest_prices[symbol] * (1 - trailing_stop_ratio)
        # 손절가 계산
        try:
            df = combined_df.xs(symbol).copy()
            BB = ta.bbands(df["close"], length = 20, std = 2)
            BBM_columns = [column for column in BB.columns if column.startswith("BBM")]
            BBL_columns = [column for column in BB.columns if column.startswith("BBL")]
            df = pd.concat([df, BB], axis = 1)

            last_bar = df.iloc[-2]
            BBM = last_bar[BBM_columns[0]]
            BBL = last_bar[BBL_columns[0]]
            BB_width = BBM - BBL
            stop_loss_price = BBM - (BB_width * stop_loss_BB_ratio)
        except Exception as e:
            print(f"{symbol} / 트레일링 스탑 검사 진행: 손절가 계산 실패: {e}")
            stop_loss_price = 0
        # 매도 신호 검사
        is_trailing_stop = current_price <= trailing_stop_price
        is_stop_loss = current_price <= stop_loss_price
        if is_trailing_stop or is_stop_loss:
            if is_trailing_stop:
                reason = (f"트레일링 스탑 / 최고가: ${highest_prices[symbol]:.2f} / 매도가: ${trailing_stop_price:.2f}")
            else:
                reason = (f"볼린저밴드 손절 / 매도가: ${stop_loss_price:.2f}")
            print(f"{symbol} / 매도 신호 발생 / 사유: {reason} / 현재가: ${current_price:.2f}")
            # 매도 주문
            try:
                order_data = MarketOrderRequest(
                    symbol = symbol,
                    qty = QTY,
                    side = OrderSide.SELL,
                    time_in_force=TimeInForce.DAY
                )
                trading_client.submit_order(order_data)
                print(f"{symbol} / 매도 주문 성공 / 수량: {QTY}주")
            except Exception as e:
                print(f"{symbol} / 매도 주문 실패: {e}")

# 매수 주문(Alpaca)
def buy_order(data_client, trading_client, symbol, current_price):
    try:
        # 계좌 조회
        account = trading_client.get_account()
        equity = float(account.equity)
        buying_power = float(account.buying_power)
        # 보유 종목 여부
        positions = trading_client.get_all_positions()
        held_positions = [position.symbol for position in positions]
        if symbol in held_positions:
            print(f"{symbol} / 매수 주문 취소: 보유 중인 종목")
            return
        # 종목 당 허용 자산 비율
        QTY = math.floor((equity * allowed_account_ratio) / current_price)
        # 예수금 초과 제한
        order_cost = QTY * current_price
        if order_cost > buying_power:
            QTY = math.floor(buying_power / current_price)
        if QTY <= 0:
            print(f"{symbol} / 매수 주문 취소: 예수금 부족")
            return
        # 매수 주문
        order_data = MarketOrderRequest(
            symbol = symbol,
            qty = QTY,
            side = OrderSide.BUY,
            time_in_force = TimeInForce.DAY
        )
        order = trading_client.submit_order(order_data)
        print(f"{symbol} / 매수 주문 성공 / 수량: {QTY}주 / 진입가: ${current_price:.2f}")
    except Exception as e:
        print(f"[ERROR] {symbol} / 매수 주문 실패: {e}")

# 텔레그램 전송
def send_telegram(message):
    url = f"https://api.telegram.org/bot{Telegram_token}/sendMessage"
    payload = {
        "chat_id": Telegram_chat_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        response = requests.post(url, json = payload, timeout = 10)
        return response.ok
    except Exception as e:
        print(f"[ERROR] 텔레그램 전송 실패: {e}")
        return False

# 프리마켓(EST 09:30 ~ 10:30) 함수 정의 ========================================

def run_premarket(data_client, trading_client, state, EST_today):
    state.is_trading_enabled = True # 매매 활성화 스위치
    start_date_pre = EST_today - datetime.timedelta(days = 40)

    # 1차 필터(SPY)
    spy_request = StockBarsRequest(
        symbol_or_symbols = "SPY",
        timeframe = TimeFrame.Day,
        start = start_date_pre
    )
    spy_bars = data_client.get_stock_bars(spy_request).df
    spy_bars['SMA5'] = ta.sma(spy_bars['close'], length = 5)
    spy_last = spy_bars.iloc[-2]
    # 1차 필터 조건 적용
    if spy_last['close'] <= spy_last['SMA5']:
        state.is_trading_enabled = False
        print("1차 필터링 / 금일 매매 비활성화")
        return

    # 2차 필터(S&P 500)
    chunk_size = 100
    combined_df = []
    for i in range(0, len(SnP_tickers), chunk_size):
        chunk_tickers = SnP_tickers[i : i + chunk_size]
        SnP_request = StockBarsRequest(
            symbol_or_symbols = chunk_tickers,
            timeframe = TimeFrame.Day,
            start = start_date_pre
        )
        try:
            SnP_bars = data_client.get_stock_bars(SnP_request)
            combined_df.append(SnP_bars.df)
        except Exception as e:
            print(f"[ERROR] S&P 500 {i} ~ {i + chunk_size} 구간 데이터 수집 실패: {e}")
            continue
    if not combined_df:
        state.is_trading_enabled = False
        print("[ERROR] 금일 매매 비활성화: S&P500 데이터 수집 실패")
        return

    SnP_combined_df = pd.concat(combined_df)
    passed_stocks = []
    available_tickers = SnP_combined_df.index.get_level_values('symbol').unique()
    for ticker in available_tickers:
        try:
            df = SnP_combined_df.xs(ticker).copy()
            df['SMA5'] = ta.sma(df['close'], length = 5)
            df['SMA20'] = ta.sma(df['close'], length = 20)
            last_bar = df.iloc[-2]
            # 2차 필터 조건 적용
            ### RSI 조건(ex. < 70)을 걸어서 과열된 종목까지 필터링하는 것도 괜찮을 것 같음
            if (last_bar['close'] > last_bar['SMA5']) and (last_bar['SMA5'] > last_bar['SMA20']):
                passed_stocks.append(ticker)
        except Exception:
            continue

    if not passed_stocks:
        state.is_trading_enabled = False
        print("2차 필터링 / 금일 매매 비활성화")
        return

    state.trade_list = passed_stocks
    print(f"1, 2차 필터링 완료 / 총 {len(state.trade_list)}개 종목 통과")
    print(f"금일 매매 대상: {state.trade_list}")
    print("=" * 60)

# 정규장(EST 10:30 ~ 13:30) 함수 정의 ==========================================

def run_market(data_client, trading_client, state, EST_today):
    start_date_market = EST_today - datetime.timedelta(days = 5)

    # 매도 신호 검사 및 주문 실행
    sell_order(data_client, trading_client, start_date_market)

    # 보유 종목 수 초과 대응
    try:
        positions = trading_client.get_all_positions()
        available_slot = allowed_position_count - len(positions)
        if available_slot <= 0:
            print("매수 신호 검사 종료: 보유 종목 수 초과")
            return
    except Exception as e:
        print(f"[ERROR] 매수 신호 검사 종료: 보유 종목 조회 실패: {e}")
        return

    # 매수 신호 검사
    # 5분봉 데이터 수집(최근 5일)
    request = StockBarsRequest(
        symbol_or_symbols = state.trade_list,
        timeframe = TimeFrame.Minute,
        timeframe_value = 5,
        start = start_date_market,
    )
    try:
        bars = data_client.get_stock_bars(request)
        combined_df = bars.df
    except Exception as e:
        print(f"[ERROR] 매수 신호 검사 종료: 5분봉 데이터 수집 실패: {e}")
        return
    # 매수 조건 지표 및 손절가 계산
    available_tickers = combined_df.index.get_level_values('symbol').unique()
    buy_target = []
    for ticker in available_tickers:
        try:
            df = combined_df.xs(ticker).copy()
            # 이동평균선(5분봉), RSI
            df["SMA5"] = ta.sma(df["close"], length = 5)
            df["SMA20"] = ta.sma(df["close"], length = 20)
            df["RSI"] = ta.rsi(df["close"], length = 14)

            present_bar = df.iloc[-1]
            last1_bar = df.iloc[-2]
            last2_bar = df.iloc[-3]
            last3_bar = df.iloc[-4]

            SMA5_last1_value = last1_bar["SMA5"]
            SMA5_last2_value = last2_bar["SMA5"]
            SMA5_last3_value = last3_bar["SMA5"]

            SMA20_last3_value = last3_bar["SMA20"]

            RSI_last1_value = last1_bar["RSI"]
            RSI_last2_value = last2_bar["RSI"]
            RSI_last3_value = last3_bar["RSI"]
            # 매수 조건
            is_SMA5_below_SMA20 = SMA5_last3_value < SMA20_last3_value
            is_RSI_below_threshold = RSI_last3_value < RSI_threshold
            is_SMA5_uptrend = (SMA5_last1_value > SMA5_last2_value) and (SMA5_last2_value > SMA5_last3_value)
            is_RSI_uptrend = (RSI_last1_value > RSI_last2_value) and (RSI_last2_value > RSI_last3_value)
            if is_SMA5_below_SMA20 and is_RSI_below_threshold and is_SMA5_uptrend and is_RSI_uptrend:
                buy_target.append({"symbol": ticker,
                                   "RSI": RSI_last1_value,
                                   "close": present_bar["close"]})
        except Exception as e:
            print(f"[ERROR] {ticker} / 매수 신호 검사 실패: {e}")
            continue
    if not buy_target:
        print("매수 신호 검사 종료: 매수 신호 발생 종목 없음")
        return
    # 우선 순위 정렬(RSI 내림차순)
    buy_target.sort(key = lambda x: x["RSI"], reverse = True)
    target_list = [item["symbol"] for item in buy_target]
    print(f"총 {len(buy_target)}개 종목 매수 신호 발생")
    print(f"해당 종목: {', '.join(target_list)}")

    # 매수 주문 실행
    for target in buy_target[:available_slot]:
        buy_order(data_client, trading_client,
                  symbol = target["symbol"],
                  current_price = target["close"])

# 애프터마켓(EST 13:30 ~ 16:00) 함수 정의 ======================================

# 애프터마켓 자동매매 루프(신규 매수 제한)
def run_aftermarket(data_client, trading_client, EST_today):
    start_date_market = EST_today - datetime.timedelta(days = 5)
    sell_order(data_client, trading_client, start_date_market)

# 장마감 루틴(1차)
def close_check(trading_client):
    try:
        cancel_responses = trading_client.cancel_orders()
        print(f"미체결 주문 {len(cancel_responses)}건 취소 요청 완료")
        close_responses = trading_client.close_all_positions(cancel_orders = True)
        print(f"보유 중인 {len(close_responses)}개 종목 시장가 매도 주문 완료")
        for position_response in close_responses:
            print(f"{position_response.symbol} / 매도 주문 성공 / 주문 ID: {position_response.id}")
    except Exception as e:
        print(f"[ERROR] 장마감 루틴(1차) 실행 실패: {e}")

# 장마감 루틴(2차)
def close_check_check(trading_client):
    try:
        open_orders = trading_client.get_orders()
        if open_orders:
            trading_client.cancel_orders()
            print(f"미체결 주문 재확인 및 취소 요청 완료")

        positions = trading_client.get_all_positions()
        if not positions:
            print("잔여 종목 매도 성공 / 보유 중인 종목: 0개")
            return True
        print(f"보유 중인 {len(positions)}개 종목 발견 / 개별 매도 주문 실행")
        for position in positions:
            symbol = position.symbol
            QTY = position.qty
            try:
                trading_client.close_position(
                    symbol_or_asset_id = symbol,
                    close_option = ClosePositionRequest(qty = QTY),
                    time_in_force = TimeInForce.DAY
                )
                print(f"{symbol} / 매도 주문 성공")
            except Exception as position_e:
                print(f"[ERROR] {symbol} / 매도 주문 실패: {position_e}")

        time.sleep(5)
        final_positions = trading_client.get_all_positions()
        if not final_positions:
            print("잔여 종목 매도 성공 / 보유 중인 종목: 0개")
            return True
        else:
            print(f"[ERROR] 매도 주문 실패 종목: {[position.symbol for position in final_positions]}")
            return False
    except Exception as e:
        print(f"[ERROR] 장마감 루틴(2차) 실행 실패: {e}")
        return False

# 텔레그램 보고서 전송
def send_report_telegram(trading_client, EST_today):
    try:
        # 계좌 조회
        account = trading_client.get_account()
        equity = float(account.equity)
        cash = float(account.cash)
        last_equity = float(account.last_equity)
        # 손익 및 수익률 계산
        daily_PnL = equity - last_equity
        daily_PnL_ratio = ((daily_PnL / last_equity) * 100) if last_equity > 0 else 0.0
        # 주문 내역 조회
        start_of_day = datetime.datetime.combine(EST_today, datetime.time.min)
        orders_request = GetOrdersRequest(
            status = QueryOrderStatus.CLOSED,
            after = start_of_day,
            nested = True
        )
        closed_orders = trading_client.get_orders(filter = orders_request)
        # 주문 내역 정리
        filled_summary = []
        for order in closed_orders:
            if order.status.value == "filled":
                side_str = "매수" if order.side.value == "buy" else "매도"
                filled_QTY = order.filled_qty
                avg_price = float(order.filled_avg_price) if order.filled_avg_price else 0.0
                filled_summary.append(f"- *{order.symbol}* / {side_str} / {filled_QTY}주 / ${avg_price:.2f}")
        # 주문 내역 메시지 생성
        if filled_summary:
            orders_text = "\n".join(filled_summary[:10])
            if len(filled_summary) > 10:
                orders_text += f"\n...외 {len(filled_summary) - 10}건 생략"
        else:
            orders_text = "- 금일 체결 주문 0건"
        # 텔레그램 보고서 생성
        report_msg = (
            f"*[stock_auto_trade] 마감 보고서*\n"
            f"- 일자: {EST_today}\n\n"
            f"*계좌 현황*\n"
            f"- 총 자산: ${equity:,.2f}\n"
            f"- 예수금: ${cash:,.2f}\n"
            f"*손익 현황*\n"
            f"- 일일 손익: ${daily_PnL:+,.2f} / {daily_PnL_ratio:+.2f}%\n\n"
            f"*주문 내역*\n"
            f"{orders_text}"
        )
        # 텔레그램 전송
        success = send_telegram(report_msg)
        if success:
            print("텔레그램 보고서 전송 성공")
        else:
            print("[ERROR] 텔레그램 보고서 전송 실패")
    except Exception as e:
        print(f"[ERROR] 텔레그램 보고서 생성 및 전송 실패: {e}")


# 스케줄링 루프 ================================================================

if __name__ == "__main__":
    print("[stock_auto_trade] 시스템 시작")
    current_date = datetime.datetime.now(EST).date()
    premarket_executed = False
    highest_prices = {}
    last_scanned_minute = -1
    close_check_executed = False
    while True:
        try:
            current_time = datetime.datetime.now(EST).time()
            EST_today = datetime.datetime.now(EST).date()
            # 자정 변수 초기화
            if EST_today != current_date:
                current_date = EST_today
                premarket_executed = False # 프리마켓 루프 실행 여부 초기화
                highest_prices = {} # 보유 종목별 최고가 딕셔너리 초기화
                last_scanned_minute = -1 # 정규장, 애프터마켓 루프 실행 기록 초기화
                close_check_executed = False # 장마감 매도 실행 기록 초기화
                time.sleep(600)

            # 프리마켓(EST 09:30 ~ 10:30 / 정규장 시간 재시작 방지 ~ 13:30 적용)
            if (not premarket_executed) and (dtime(9, 30) <= current_time < dtime(13, 30)):
                print("[프리마켓] 1, 2차 필터링 실행")
                run_premarket(data_client, trading_client, state, EST_today)
                premarket_executed = True

            # 정규장(EST 10:30 ~ 13:30)
            elif (premarket_executed) and (state.is_trading_enabled) and (dtime(10, 30) <= current_time < dtime(13, 30)):
                if (current_time.minute % 5 == 0) and (current_time.second) == 2 and (current_time.minute != last_scanned_minute):
                    print(f"[정규장] 자동 매매 루프 실행 / ({current_time.strftime('%H:%M:%S')})")
                    run_market(data_client, trading_client, state, EST_today)
                    last_scanned_minute = current_time.minute

            # 애프터마켓(EST 13:30 ~ 15:50 / 15:50 ~ 16:00)
            elif (premarket_executed) and (dtime(13,30) <= current_time < dtime(15,50)):
                if (current_time.minute % 5 == 0) and (current_time.minute != last_scanned_minute):
                    print(f"[애프터마켓] 자동 매매 루프 실행 / 신규 매수 제한 / ({current_time.strftime('%H:%M:%S')})")
                    run_aftermarket(data_client, trading_client, EST_today)
                    last_scanned_minute = current_time.minute

            elif (premarket_executed) and (not close_check_executed) and (dtime(15,50) <= current_time <= dtime(16,0)):
                print("[장마감] 자동 매매 루프 종료 / 장마감 루틴 실행")
                # 미체결 주문 취소 및 보유 종목 시장가 매도
                close_check(trading_client)
                time.sleep(5)
                # 미체결 주문 및 보유 종목 2차 확인
                close_check_check(trading_client)
                # 텔레그램 보고서 전송
                send_report_telegram(trading_client, EST_today)
                close_check_executed = True
                print("[휴식] 시스템 휴식 루프 진입")

            # 휴식(EST 16:00 ~ 익일 09:30)
            else:
                time.sleep(60)
                continue

            time.sleep(1)

        except Exception as e:
            error_msg = f"[ERROR] 자동 매매 루프 에러: {e}"
            print(error_msg)
            send_telegram(error_msg)
            time.sleep(10)
