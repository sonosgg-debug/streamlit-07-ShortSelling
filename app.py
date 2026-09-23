import socket
socket.setdefaulttimeout(5.0)

import streamlit as st
import datetime
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from dateutil.relativedelta import relativedelta
from dotenv import load_dotenv
import os

# pykrx 모듈 가져오기
from pykrx import stock
from pykrx.website.krx.market.ticker import StockTicker
from pykrx.website.comm.auth import build_krx_session, set_auth_session

# .env 파일 로드
load_dotenv()

# 웹 페이지 레이아웃 설정
st.set_page_config(page_title="한국증시 개별종목 공매도 현황", layout="wide", initial_sidebar_state="expanded")

# 사이드바 접기/펼치기 버튼 상시 표시 및 모바일 대비 강화 CSS
st.markdown("""
<style>
    /* 메인 콘텐츠 상단 여백 규격화 */
    .main .block-container,
    [data-testid="stMainBlockContainer"],
    .block-container {
        padding-top: 2.0rem !important;
    }

    /* Headers & Main Title (00 Bookmarks 테마 일치) */
    h1, .main h1, [data-testid="stHeadingWithActionElements"] h1, .main-title {
        color: #8AB4F8 !important;
        -webkit-text-fill-color: #8AB4F8 !important;
        font-size: 2.0rem !important;
        font-weight: 800 !important;
        text-align: center !important;
    }

    /* Button Styling (39 DividendStock 표준 스타일 일치) */
    .stButton button[kind="primary"],
    .stButton > button[kind="primary"],
    section[data-testid="stSidebar"] button[kind="primary"] {
        background-color: #2563eb !important;
        color: #ffffff !important;
        border: none !important;
        font-weight: 600 !important;
        border-radius: 6px !important;
        transition: all 0.2s ease !important;
    }
    .stButton button[kind="primary"]:hover,
    .stButton > button[kind="primary"]:hover,
    section[data-testid="stSidebar"] button[kind="primary"]:hover {
        background-color: #1d4ed8 !important;
        box-shadow: 0 0 10px rgba(37, 99, 235, 0.4) !important;
    }

    /* 다운로드 버튼 공통 통일 스타일 */
    div[data-testid="stDownloadButton"] > button,
    .stDownloadButton > button {
        background-color: #334155 !important;
        color: #f8fafc !important;
        border: 1px solid #475569 !important;
        border-radius: 6px !important;
        font-size: 0.875rem !important;
        font-weight: 500 !important;
        height: 38px !important;
        min-height: 38px !important;
        max-height: 38px !important;
        line-height: 36px !important;
        padding: 0 16px !important;
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
        text-align: center !important;
        transition: all 0.2s ease-in-out !important;
        box-sizing: border-box !important;
    }
    div[data-testid="stDownloadButton"] > button:hover,
    .stDownloadButton > button:hover {
        background-color: #475569 !important;
        border-color: #38bdf8 !important;
        color: #ffffff !important;
        box-shadow: 0 0 10px rgba(56, 189, 248, 0.25) !important;
    }
    div[data-testid="stDownloadButton"] > button:active,
    .stDownloadButton > button:active {
        background-color: #1e293b !important;
        border-color: #0284c7 !important;
    }
    div[data-testid="stDownloadButton"] > button p,
    div[data-testid="stDownloadButton"] > button span,
    .stDownloadButton > button p,
    .stDownloadButton > button span {
        font-size: 0.875rem !important;
        font-weight: 500 !important;
        color: inherit !important;
        line-height: inherit !important;
        margin: 0 !important;
        padding: 0 !important;
    }

    /* =========================================================
       사이드바 접기(<<) 및 펼치기(>>) 버튼 항상 표시 및 시인성/대비 강화
       ========================================================= */
    /* 1. 사이드바가 열려 있을 때 접기 버튼 (<<) 상시 표시 */
    [data-testid="stSidebarCollapseButton"] {
        visibility: visible !important;
        opacity: 1 !important;
        display: inline-flex !important;
    }
    
    [data-testid="stSidebarCollapseButton"] button {
        visibility: visible !important;
        opacity: 1 !important;
        background-color: #1e293b !important;       /* 진한 네이비 배경 */
        border: 1.5px solid #38bdf8 !important;     /* 선명한 스카이블루 테두리로 상자 명확화 */
        border-radius: 8px !important;
        width: 38px !important;
        height: 38px !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.4), 0 0 6px rgba(56, 189, 248, 0.2) !important;
        transition: all 0.2s ease !important;
    }
    
    /* 상자 내부의 << 아이콘(Material Icon span/svg/문자)을 순백색으로 강제하여 상자와 극명한 대비 구현 */
    [data-testid="stSidebarCollapseButton"] button *,
    [data-testid="stSidebarCollapseButton"] span,
    [data-testid="stSidebarCollapseButton"] [data-testid="stIconMaterial"],
    [data-testid="stSidebarCollapseButton"] svg {
        color: #ffffff !important;
        fill: #ffffff !important;
        opacity: 1 !important;
        visibility: visible !important;
        font-size: 1.35rem !important;
        font-weight: 700 !important;
    }
    
    /* 호버(PC) 및 터치 시 반전 효과 */
    [data-testid="stSidebarCollapseButton"] button:hover {
        background-color: #38bdf8 !important;
        border-color: #38bdf8 !important;
    }
    [data-testid="stSidebarCollapseButton"] button:hover * {
        color: #0f172a !important;
        fill: #0f172a !important;
    }

    /* 2. 사이드바 헤더 영역 패딩 및 정렬 보정 */
    [data-testid="stSidebarHeader"] {
        padding-top: 0.5rem !important;
        padding-bottom: 0.5rem !important;
    }

    /* 3. 사이드바가 닫혔을 때 다시 여는 버튼 (>>) 시인성 강화 */
    [data-testid="stSidebarCollapsedControl"] {
        visibility: visible !important;
        opacity: 1 !important;
    }
    
    [data-testid="stSidebarCollapsedControl"] button {
        background-color: #1e293b !important;
        border: 1.5px solid #38bdf8 !important;
        border-radius: 8px !important;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.4), 0 0 6px rgba(56, 189, 248, 0.2) !important;
    }
    
    [data-testid="stSidebarCollapsedControl"] button *,
    [data-testid="stSidebarCollapsedControl"] span,
    [data-testid="stSidebarCollapsedControl"] [data-testid="stIconMaterial"],
    [data-testid="stSidebarCollapsedControl"] svg {
        color: #38bdf8 !important;
        fill: #38bdf8 !important;
        opacity: 1 !important;
        visibility: visible !important;
        font-size: 1.35rem !important;
    }

    /* 알림 및 뱃지 스타일 */
    .status-card {
        background-color: #1e293b;
        border: 1px solid #334155;
        border-left: 4px solid #38bdf8;
        border-radius: 8px;
        padding: 14px 18px;
        margin-bottom: 16px;
        font-size: 0.9rem;
        line-height: 1.5;
        color: #cbd5e1;
    }
    .status-card b {
        color: #f8fafc;
    }
    .status-badge-ok {
        background-color: rgba(34, 197, 94, 0.15);
        color: #4ade80;
        border: 1px solid rgba(34, 197, 94, 0.3);
        padding: 2px 8px;
        border-radius: 4px;
        font-weight: 600;
    }
    .status-badge-wait {
        background-color: rgba(234, 179, 8, 0.15);
        color: #facc15;
        border: 1px solid rgba(234, 179, 8, 0.3);
        padding: 2px 8px;
        border-radius: 4px;
        font-weight: 600;
    }

</style>
""", unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# 1. 날짜 연산 함수
# -----------------------------------------------------------------------------
def calculate_dates(period):
    today = datetime.date.today()
    
    if period == "1W":
        start_date = today - datetime.timedelta(weeks=1)
    elif period == "2W":
        start_date = today - datetime.timedelta(weeks=2)
    elif period == "1M":
        start_date = today - relativedelta(months=1)
    elif period == "3M":
        start_date = today - relativedelta(months=3)
    elif period == "6M":
        start_date = today - relativedelta(months=6)
    elif period == "1Y":
        start_date = today - relativedelta(years=1)
    elif period == "YTD":
        start_date = datetime.date(today.year, 1, 1)
    else:
        start_date = today - datetime.timedelta(weeks=1)
        
    return start_date.strftime("%Y%m%d"), today.strftime("%Y%m%d")

# -----------------------------------------------------------------------------
# 2. KRX 로그인 세션 초기화 및 상태 관리
# -----------------------------------------------------------------------------
def try_krx_login(login_id, login_pw):
    """세션 갱신을 수행하고 session state에 보관"""
    if not login_id or not login_pw:
        return False
        
    try:
        # 이전에 성공한 세션이 있고 유효하다면 로그인 건너뜀
        if "krx_session" in st.session_state and st.session_state.krx_session.is_valid():
            set_auth_session(st.session_state.krx_session)
            return True
            
        # 신규 로그인 시도
        session = build_krx_session(login_id, login_pw)
        if session and session.is_authenticated:
            st.session_state.krx_session = session
            set_auth_session(session)
            return True
    except Exception as e:
        st.error(f"로그인 중 에러 발생: {e}")
        
    return False

# -----------------------------------------------------------------------------
# 3. 데이터 로드 및 정제 모듈 (캐싱 지원)
# -----------------------------------------------------------------------------
@st.cache_data(ttl=86400)
def load_stock_tickers():
    """상장 종목 전체 리스트 가져오기 (로컬 CSV -> pykrx StockTicker -> FDR -> 내장 대표주)"""
    csv_path = os.path.join(os.path.dirname(__file__), "krx_tickers.csv")

    # 1. 로컬 krx_tickers.csv 최우선 로드 (해외 IP 차단/네트워크 지연 원천 차단)
    if os.path.exists(csv_path):
        try:
            df = pd.read_csv(csv_path, dtype={'티커': str}, index_col='티커')
            if not df.empty and '종목' in df.columns:
                return df
        except Exception:
            pass

    # 2. pykrx StockTicker 시도
    try:
        st_ticker = StockTicker()
        df = st_ticker.listed
        if not df.empty and '종목' in df.columns:
            try:
                df.to_csv(csv_path, encoding='utf-8-sig')
            except Exception:
                pass
            return df
    except Exception:
        pass

    # 3. Fallback to FinanceDataReader
    try:
        import FinanceDataReader as fdr
        df = fdr.StockListing('KRX')
        df = df.set_index('Code')
        df['종목'] = df['Name']
        return df
    except Exception:
        pass

    # 4. 내장 대표 32개 우량주 fallback (최악의 오프라인/네트워크 차단 환경 대비)
    fallback_data = {
        '005930': '삼성전자', '000660': 'SK하이닉스', '373220': 'LG에너지솔루션',
        '207940': '삼성바이오로직스', '005380': '현대차', '000270': '기아',
        '068270': '셀트리온', '105560': 'KB금융', '055550': '신한지주',
        '035420': 'NAVER', '005490': 'POSCO홀딩스', '012330': '현대모비스',
        '035720': '카카오', '028260': '삼성물산', '051910': 'LG화학',
        '086520': '에코프로', '247540': '에코프로비엠', '196170': '알테오젠',
        '036930': '주성엔지니어링', '006400': '삼성SDI', '032830': '삼성생명',
        '015760': '한국전력', '329180': 'HD현대중공업', '010130': '고려아연',
        '033780': 'KT&G', '003550': 'LG', '018260': '삼성에스디에스',
        '017670': 'SK텔레콤', '030200': 'KT', '034730': 'SK',
        '323410': '카카오뱅크', '259960': '크래프톤'
    }
    return pd.DataFrame(list(fallback_data.items()), columns=['티커', '종목']).set_index('티커')

def fetch_and_process_balance_data(start_date, end_date, ticker):
    """[33001] 개별종목 공매도 순보유잔고 및 주가 병합"""
    try:
        # 1. 주가 데이터 (OHLCV) 가져오기
        df_price = stock.get_market_ohlcv_by_date(start_date, end_date, ticker)
        if df_price.empty:
            return pd.DataFrame(), None, "주가 데이터가 존재하지 않습니다."
            
        # 2. 개별종목 공매도 순보유잔고(33001) 가져오기
        df_short = stock.get_shorting_balance_by_date(start_date, end_date, ticker)
        if df_short.empty:
            return pd.DataFrame(), None, "공매도 잔고 데이터가 존재하지 않습니다. 로그인이 정상적으로 되었는지 확인하세요."
            
        # 데이터 인덱스 포맷 맞추기 (datetime)
        df_price.index = pd.to_datetime(df_price.index)
        df_short.index = pd.to_datetime(df_short.index)
        
        # 3. 두 데이터프레임 병합 (left join을 사용하여 주가 데이터 기준 유지)
        df_combined = df_price[['종가']].rename(columns={'종가': '주가'}).join(df_short, how='left')
        
        # 4. 공매도 순보유 잔고금액 (억원) 계산 및 컬럼 정리
        short_amt_cols = [c for c in df_short.columns if '금액' in c or '공매도금액' in c]
        if short_amt_cols:
            df_combined['공매도 순보유 잔고금액 (억원)'] = df_combined[short_amt_cols[0]] / 100_000_000.0
        elif len(df_short.columns) >= 3:
            df_combined['공매도 순보유 잔고금액 (억원)'] = df_combined.iloc[:, 3] / 100_000_000.0
        else:
            df_combined['공매도 순보유 잔고금액 (억원)'] = np.nan
            
        # 컬럼명 매핑 및 정리
        rename_cols = {
            '공매도잔고': '공매도 순보유 잔고수량 (주)',
            '상장주식수': '상장주식수 (주)',
            '비중': '공매도 비중 (%)'
        }
        df_combined.rename(columns=rename_cols, inplace=True)
        
        # 메타 정보 추출
        valid_short = df_combined[df_combined['공매도 순보유 잔고금액 (억원)'].notna()]
        latest_short_date = valid_short.index[-1] if not valid_short.empty else None
        latest_price_date = df_price.index[-1]
        
        missing_dates = [d for d in df_price.index if d > latest_short_date] if latest_short_date is not None else []
        
        meta = {
            'price_start': df_price.index[0],
            'price_end': latest_price_date,
            'short_start': valid_short.index[0] if not valid_short.empty else None,
            'short_end': latest_short_date,
            'missing_dates': missing_dates,
            'has_gap': len(missing_dates) > 0
        }
        
        return df_combined, meta, None
    except Exception as e:
        return pd.DataFrame(), None, f"데이터 로드 중 예외가 발생했습니다: {e}"

def fetch_and_process_trading_data(start_date, end_date, ticker):
    """[12002] 일별 공매도 거래실적(거래대금/거래량) 및 주가 병합"""
    try:
        # 1. 주가 데이터 (OHLCV)
        df_price = stock.get_market_ohlcv_by_date(start_date, end_date, ticker)
        if df_price.empty:
            return pd.DataFrame(), None, "주가 데이터가 존재하지 않습니다."
            
        # 2. 거래실적 가져오기
        df_val = stock.get_shorting_value_by_date(start_date, end_date, ticker)
        df_vol = stock.get_shorting_volume_by_date(start_date, end_date, ticker)
        
        df_price.index = pd.to_datetime(df_price.index)
        df_val.index = pd.to_datetime(df_val.index)
        df_vol.index = pd.to_datetime(df_vol.index)
        
        df_trading = df_price[['종가']].rename(columns={'종가': '주가'})
        
        # 컬럼 인덱스를 활용하여 인코딩 이슈 방지 (0: 매도/공매도, 1: 매수/총합, 2: 비중)
        if not df_val.empty and len(df_val.columns) >= 3:
            df_trading['공매도 거래대금 (억원)'] = df_val.iloc[:, 0] / 100_000_000.0
            df_trading['총 거래대금 (억원)'] = df_val.iloc[:, 1] / 100_000_000.0
            df_trading['공매도 거래대금 비중 (%)'] = df_val.iloc[:, 2]
        else:
            df_trading['공매도 거래대금 (억원)'] = np.nan
            df_trading['총 거래대금 (억원)'] = np.nan
            df_trading['공매도 거래대금 비중 (%)'] = np.nan
            
        if not df_vol.empty and len(df_vol.columns) >= 3:
            df_trading['공매도 거래량 (주)'] = df_vol.iloc[:, 0]
            df_trading['총 거래량 (주)'] = df_vol.iloc[:, 1]
            df_trading['공매도 거래량 비중 (%)'] = df_vol.iloc[:, 2]
        else:
            df_trading['공매도 거래량 (주)'] = np.nan
            df_trading['총 거래량 (주)'] = np.nan
            df_trading['공매도 거래량 비중 (%)'] = np.nan
            
        meta = {
            'trading_start': df_trading.index[0],
            'trading_end': df_trading.index[-1]
        }
        return df_trading, meta, None
    except Exception as e:
        return pd.DataFrame(), None, f"거래실적 데이터 로드 중 예외가 발생했습니다: {e}"

def fetch_and_process_data(start_date, end_date, ticker):
    """하위 호환용 래퍼 함수"""
    return fetch_and_process_balance_data(start_date, end_date, ticker)

# -----------------------------------------------------------------------------
# 4. 메인 화면 구성
# -----------------------------------------------------------------------------
st.markdown("<h1 class='main-title' style='text-align: center; font-size: 2.0rem !important; font-weight: 800 !important; color: #8AB4F8 !important; -webkit-text-fill-color: #8AB4F8 !important; margin-bottom: 10px;'><span style='color: #8AB4F8 !important; -webkit-text-fill-color: #8AB4F8 !important;'>한국증시 개별종목 공매도 현황</span></h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #BDC1C6; font-size: 1.0rem; margin-bottom: 20px;'>KRX 거래소 계정 정보를 이용하여 개별 종목의 공매도 순보유잔고와 주가 추이를 분석합니다.</p>", unsafe_allow_html=True)
st.markdown("<hr style='border: 0; height: 1px; background-color: #334155; margin-bottom: 22px;'>", unsafe_allow_html=True)


# 사이드바 설정
with st.sidebar:
    st.header("🔑 KRX 로그인 설정")

    # env 로드 값
    env_id = os.getenv("KRX_ID", "")
    env_pw = os.getenv("KRX_PW", "")

    # 사이드바 입력창
    krx_id = st.text_input("KRX ID", value=env_id, help="data.krx.co.kr 로그인 아이디")
    krx_pw = st.text_input("KRX Password", value=env_pw, type="password", help="data.krx.co.kr 로그인 비밀번호")

    login_success = False
    if krx_id and krx_pw:
        login_success = try_krx_login(krx_id, krx_pw)
        if login_success:
            st.success("✔️ KRX 로그인 성공")
        else:
            st.error("❌ KRX 로그인 실패 (계정을 확인해 주세요)")
    else:
        st.warning("⚠️ KRX 로그인 정보 입력이 필요합니다.")

    st.markdown("---")
    st.subheader("🎯 조회 조건")

    # 종목 로드
    tickers_df = load_stock_tickers()
    if not tickers_df.empty:
        # selectbox 표시용 포맷팅: 종목명 (티커)
        tickers_df['display_name'] = tickers_df['종목'] + " (" + tickers_df.index + ")"
        display_names = sorted(tickers_df['display_name'].tolist())
        
        # 디폴트 종목: 삼성전자
        default_idx = 0
        for idx, name in enumerate(display_names):
            if "삼성전자" in name:
                default_idx = idx
                break
                
        selected_display = st.selectbox("종목 선택", display_names, index=default_idx)
        # 티커 코드 추출 (마지막 괄호 안의 6자리 문자)
        selected_ticker = selected_display.split("(")[-1].replace(")", "").strip()
        selected_name = tickers_df.loc[selected_ticker, '종목']
    else:
        st.error("종목 정보를 로드할 수 없습니다.")
        st.stop()

    # 기간 선택
    periods = ["1W", "2W", "1M", "3M", "6M", "1Y", "YTD"]
    default_period_idx = periods.index("3M") if "3M" in periods else 0
    selected_period = st.selectbox("조회 기간", periods, index=default_period_idx)

    # 액션 버튼 (Update & 조회)
    st.markdown("")
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        btn_update = st.button("🔄 Update", use_container_width=True, help="캐시를 초기화하고 최신 공매도 데이터를 다시 수집합니다.")
    with col_btn2:
        submit_button = st.button("🔍 조회", type="primary", use_container_width=True, help="선택한 조건으로 대시보드를 새로고침합니다.")

    if btn_update:
        st.cache_data.clear()
        st.rerun()

# -----------------------------------------------------------------------------
# 5. 데이터 조회 및 시각화 영역
# -----------------------------------------------------------------------------
if login_success:
    # 조회 날짜 계산
    start_date, end_date = calculate_dates(selected_period)
    
    st.markdown(f"<h3 style='color: #BDC1C6; font-size: 1.25rem; font-weight: 600; margin-top: 10px; margin-bottom: 10px;'>{selected_name} ({selected_ticker}) - {selected_period} 공매도 분석</h3>", unsafe_allow_html=True)
    
    tab_balance, tab_trading = st.tabs([
        "📊 공매도 순보유잔고 (T+2 지연공시)", 
        "📈 일별 공매도 거래현황 (최신 거래대금/거래량)"
    ])
    
    # =========================================================================
    # TAB 1: 공매도 순보유잔고
    # =========================================================================
    with tab_balance:
        with st.spinner("공매도 잔고 데이터를 로드하고 있습니다..."):
            df_bal, meta_bal, err_bal = fetch_and_process_balance_data(start_date, end_date, selected_ticker)
            
        if err_bal:
            st.error(err_bal)
            st.info("💡 팁: KRX 로그인 정보가 일치하지 않거나 세션이 만료된 경우 발생할 수 있습니다.")
        elif not df_bal.empty:
            # T+2 공시 일정 안내 카드 렌더링
            latest_short_str = meta_bal['short_end'].strftime('%Y-%m-%d') if meta_bal['short_end'] is not None else "데이터 없음"
            latest_price_str = meta_bal['price_end'].strftime('%Y-%m-%d')
            
            if meta_bal['has_gap']:
                missing_str = ", ".join([d.strftime('%m/%d') for d in meta_bal['missing_dates']])
                next_target = meta_bal['missing_dates'][0].strftime('%Y-%m-%d')
                
                st.markdown(f"""
                <div class="status-card">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                        <span>📡 <b>KRX 공매도 잔고 수집 상태</b>: 최신 반영일 <span class="status-badge-ok">{latest_short_str}</span> (정상 수집 중)</span>
                        <span class="status-badge-wait">T+2 법정 공시 대기: {missing_str}</span>
                    </div>
                    <div style="color: #94a3b8; font-size: 0.85rem; line-height: 1.5;">
                        • <b>T+2 결제 및 공시 주기 안내</b>: 자본시장법 시행령 제208조의2에 따라 공매도 순보유잔고는 체결일(T)로부터 <b>2영업일 뒤(T+2) 18:00</b>에 거래소에서 공시됩니다.<br/>
                        • 따라서 최근 2~3영업일 잔고가 비어 있는 것은 <b>수집 오류가 아닌 정상적인 공시 대기 상태</b>이며, <b>{next_target}</b> 잔고는 T+2일 18:00 이후 KRX 공시를 통해 자동 반영됩니다.<br/>
                        • 최신(어제/오늘) 공매도 체결 내역을 확인하시려면 상단의 <b>[일별 공매도 거래현황]</b> 탭을 확인해 주세요.
                    </div>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div class="status-card">
                    📡 <b>KRX 공매도 잔고 수집 상태</b>: 최신 공시일 <span class="status-badge-ok">{latest_short_str}</span>까지 모두 수집 완료되었습니다.
                </div>
                """, unsafe_allow_html=True)
                
            # 차트 표시 범위 정렬 옵션
            col_opt, _ = st.columns([3, 1])
            with col_opt:
                align_chart = st.checkbox(
                    f"공매도 잔고 공시 완료일({latest_short_str})까지만 차트 표시 (권장: 선 끊김 방지)",
                    value=True,
                    help="체크 시 주가와 공매도 잔고의 종료 날짜를 공시 완료일로 일치시켜 선 단절 없이 깔끔하게 비교합니다."
                )
                
            df_plot = df_bal.copy()
            if align_chart and meta_bal['short_end'] is not None:
                df_plot = df_plot[df_plot.index <= meta_bal['short_end']]
                
            # Plotly 이중 Y축 차트 그리기
            fig_bal = make_subplots(specs=[[{"secondary_y": True}]])
            
            # 1. 주가 (좌측 Y축, 꺾은선)
            fig_bal.add_trace(
                go.Scatter(
                    x=df_plot.index.strftime('%Y-%m-%d'),
                    y=df_plot['주가'],
                    name="주가 (종가)",
                    mode='lines+markers',
                    line=dict(color='#1f77b4', width=2),
                    marker=dict(size=6),
                    hovertemplate='%{x} 주가: %{y:,.0f} 원<extra></extra>'
                ),
                secondary_y=False
            )
            
            # 2. 공매도 순보유 잔고금액 (우측 Y축, 꺾은선)
            fig_bal.add_trace(
                go.Scatter(
                    x=df_plot.index.strftime('%Y-%m-%d'),
                    y=df_plot['공매도 순보유 잔고금액 (억원)'],
                    name="공매도 순보유 잔고금액 (억원)",
                    mode='lines+markers',
                    line=dict(color='#ff7f0e', width=2),
                    marker=dict(size=6),
                    hovertemplate='%{x} 공매도 잔고금액: %{y:.2f} 억원<extra></extra>'
                ),
                secondary_y=True
            )
            
            fig_bal.update_layout(
                template="plotly_dark",
                paper_bgcolor="#1E293B",
                plot_bgcolor="#0F172A",
                title=dict(
                    text=f"<b>{selected_name} 주가 및 공매도 순보유 잔고금액 추이</b>",
                    font=dict(color="#F8FAFC", size=15),
                    x=0.5,
                    xanchor="center"
                ),
                hovermode="x unified",
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="center",
                    x=0.5,
                    bgcolor="rgba(30, 41, 59, 0.85)",
                    bordercolor="#334155",
                    borderwidth=1,
                    font=dict(color="#F8FAFC", size=11)
                ),
                margin=dict(l=20, r=20, t=80, b=20),
                height=480
            )
            fig_bal.update_xaxes(title_text="날짜", type='category', tickangle=-45, gridcolor="#334155", linecolor="#475569", tickfont=dict(color="#cbd5e1"))
            fig_bal.update_yaxes(title_text="주가 (원)", tickformat=",.0f", secondary_y=False, gridcolor="#334155", linecolor="#475569", tickfont=dict(color="#cbd5e1"))
            fig_bal.update_yaxes(title_text="공매도 순보유 잔고금액 (억원)", tickformat=",.2f", secondary_y=True, showgrid=False, linecolor="#475569", tickfont=dict(color="#cbd5e1"))
            
            st.plotly_chart(fig_bal, use_container_width=True)
            
            # 일별 데이터 상세 테이블
            st.markdown("<h4 style='color: #BDC1C6; font-size: 1.05rem; font-weight: 600; margin-top: 20px; margin-bottom: 5px;'>📝 공매도 순보유잔고 일별 상세</h4>", unsafe_allow_html=True)
            st.markdown("<div style='font-size: 0.8rem; color: #94a3b8; margin-bottom: 12px;'>※ 최근 일자의 결측치('-')는 거래소 T+2 공시 대기 중인 정상 상태입니다.</div>", unsafe_allow_html=True)
            
            display_cols_bal = [
                '주가', 
                '공매도 순보유 잔고금액 (억원)', 
                '공매도 순보유 잔고수량 (주)', 
                '공매도 비중 (%)', 
                '상장주식수 (주)'
            ]
            valid_cols_bal = [c for c in display_cols_bal if c in df_bal.columns]
            df_bal_display = df_bal[valid_cols_bal].copy()
            df_bal_display.index = df_bal_display.index.strftime('%Y-%m-%d')
            
            styled_bal = df_bal_display.sort_index(ascending=False).style.format({
                '주가': '{:,.0f}',
                '공매도 순보유 잔고금액 (억원)': '{:.2f}',
                '공매도 순보유 잔고수량 (주)': '{:,.0f}',
                '공매도 비중 (%)': '{:.2f}',
                '상장주식수 (주)': '{:,.0f}'
            }, na_rep='-')
            
            st.dataframe(styled_bal, use_container_width=True)
        else:
            st.warning("공매도 잔고 데이터가 비어 있습니다.")

    # =========================================================================
    # TAB 2: 일별 공매도 거래현황 (최신 거래대금/거래량)
    # =========================================================================
    with tab_trading:
        with st.spinner("일별 공매도 거래실적 데이터를 로드하고 있습니다..."):
            df_tr, meta_tr, err_tr = fetch_and_process_trading_data(start_date, end_date, selected_ticker)
            
        if err_tr:
            st.error(err_tr)
        elif not df_tr.empty:
            latest_trading_str = meta_tr['trading_end'].strftime('%Y-%m-%d')
            
            st.markdown(f"""
            <div class="status-card">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                    <span>⚡ <b>일별 공매도 거래실적</b>: 최신 반영일 <span class="status-badge-ok">{latest_trading_str}</span> (당일 장 마감 후 즉시 공시)</span>
                </div>
                <div style="color: #94a3b8; font-size: 0.85rem; line-height: 1.5;">
                    • <b>실시간 반영 안내</b>: 일별 공매도 거래대금과 거래량은 T+2 잔고 공시와 달리 <b>매일 장 마감 후 거래소에서 즉시 집계</b>되어 공시됩니다.<br/>
                    • 따라서 최근 거래일의 공매도 유입 강도 및 거래대금 비중을 지연 없이 가장 빠르게 파악하실 수 있습니다.
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Plotly 차트: 주가(선) + 공매도 거래대금(막대)
            fig_tr = make_subplots(specs=[[{"secondary_y": True}]])
            
            # 1. 주가 (좌측 Y축, 선)
            fig_tr.add_trace(
                go.Scatter(
                    x=df_tr.index.strftime('%Y-%m-%d'),
                    y=df_tr['주가'],
                    name="주가 (종가)",
                    mode='lines+markers',
                    line=dict(color='#1f77b4', width=2),
                    marker=dict(size=6),
                    hovertemplate='%{x} 주가: %{y:,.0f} 원<extra></extra>'
                ),
                secondary_y=False
            )
            
            # 2. 공매도 거래대금 (우측 Y축, 바)
            fig_tr.add_trace(
                go.Bar(
                    x=df_tr.index.strftime('%Y-%m-%d'),
                    y=df_tr['공매도 거래대금 (억원)'],
                    name="공매도 거래대금 (억원)",
                    marker=dict(color='rgba(255, 127, 14, 0.75)', line=dict(color='#ff7f0e', width=1)),
                    hovertemplate='%{x} 공매도 거래대금: %{y:.2f} 억원<extra></extra>'
                ),
                secondary_y=True
            )
            
            fig_tr.update_layout(
                template="plotly_dark",
                paper_bgcolor="#1E293B",
                plot_bgcolor="#0F172A",
                title=dict(
                    text=f"<b>{selected_name} 주가 및 일별 공매도 거래대금 추이</b>",
                    font=dict(color="#F8FAFC", size=15),
                    x=0.5,
                    xanchor="center"
                ),
                hovermode="x unified",
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="center",
                    x=0.5,
                    bgcolor="rgba(30, 41, 59, 0.85)",
                    bordercolor="#334155",
                    borderwidth=1,
                    font=dict(color="#F8FAFC", size=11)
                ),
                margin=dict(l=20, r=20, t=80, b=20),
                height=480
            )
            fig_tr.update_xaxes(title_text="날짜", type='category', tickangle=-45, gridcolor="#334155", linecolor="#475569", tickfont=dict(color="#cbd5e1"))
            fig_tr.update_yaxes(title_text="주가 (원)", tickformat=",.0f", secondary_y=False, gridcolor="#334155", linecolor="#475569", tickfont=dict(color="#cbd5e1"))
            fig_tr.update_yaxes(title_text="공매도 거래대금 (억원)", tickformat=",.2f", secondary_y=True, showgrid=False, linecolor="#475569", tickfont=dict(color="#cbd5e1"))
            
            st.plotly_chart(fig_tr, use_container_width=True)
            
            # 일별 공매도 거래 상세 테이블
            st.markdown("<h4 style='color: #BDC1C6; font-size: 1.05rem; font-weight: 600; margin-top: 20px; margin-bottom: 5px;'>📝 일별 공매도 거래실적 상세</h4>", unsafe_allow_html=True)
            
            display_cols_tr = [
                '주가', 
                '공매도 거래대금 (억원)', 
                '공매도 거래대금 비중 (%)',
                '총 거래대금 (억원)', 
                '공매도 거래량 (주)', 
                '총 거래량 (주)', 
                '공매도 거래량 비중 (%)'
            ]
            valid_cols_tr = [c for c in display_cols_tr if c in df_tr.columns]
            df_tr_display = df_tr[valid_cols_tr].copy()
            df_tr_display.index = df_tr_display.index.strftime('%Y-%m-%d')
            
            styled_tr = df_tr_display.sort_index(ascending=False).style.format({
                '주가': '{:,.0f}',
                '공매도 거래대금 (억원)': '{:.2f}',
                '공매도 거래대금 비중 (%)': '{:.2f}',
                '총 거래대금 (억원)': '{:.2f}',
                '공매도 거래량 (주)': '{:,.0f}',
                '총 거래량 (주)': '{:,.0f}',
                '공매도 거래량 비중 (%)': '{:.2f}'
            }, na_rep='-')
            
            st.dataframe(styled_tr, use_container_width=True)
        else:
            st.warning("일별 공매도 거래실적 데이터가 비어 있습니다.")
else:
    st.info("👈 대시보드 조회를 위해 사이드바에 KRX 로그인 정보를 입력해 주세요.")
    st.markdown("""
    ### 📌 시작 가이드
    1. 왼쪽 사이드바에 **KRX 정보데이터시스템(data.krx.co.kr)** 로그인 ID와 PW를 입력하세요.
    2. 로그인이 완료되면 자동으로 실시간 종목 리스트와 상세 공매도 현황을 가져올 수 있는 상태가 됩니다.
    3. 혹은 프로젝트 루트 디렉토리에 `.env` 파일을 생성하여 다음과 같이 계정을 미리 입력해 둘 수 있습니다.
    
    ```bash
    # .env 파일 예시
    KRX_ID=your_id
    KRX_PW=your_password
    ```
    """)

st.markdown("---")
st.markdown("<div style='text-align: center; color: #64748b; font-size: 0.8rem; margin-top: 8px; margin-bottom: 24px; line-height: 1.6;'>⚠️ 본 서비스에서 제공하는 모든 정보는 투자 참고용이며, 투자의 최종 결정과 책임은 투자자 본인에게 있습니다.</div>", unsafe_allow_html=True)
