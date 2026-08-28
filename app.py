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
st.set_page_config(page_title="한국증시 개별종목 공매도 현황 대시보드", layout="wide")

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
@st.cache_data
def load_stock_tickers():
    """상장 종목 전체 리스트 가져오기 (비로그인 상태로도 작동 가능)"""
    try:
        st_ticker = StockTicker()
        df = st_ticker.listed
        return df
    except Exception as e:
        st.error(f"종목 리스트 로드 실패: {e}")
        return pd.DataFrame()

def fetch_and_process_data(start_date, end_date, ticker):
    """주가 데이터와 공매도 잔고 데이터를 병합하여 반환"""
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
        # '공매도금액' 컬럼이 순보유 잔고금액에 대응함 (원 -> 억원)
        if '공매도금액' in df_combined.columns:
            df_combined['공매도 순보유 잔고금액 (억원)'] = df_combined['공매도금액'] / 100_000_000.0
        else:
            df_combined['공매도 순보유 잔고금액 (억원)'] = np.nan
            
        # 컬럼명 매핑 및 정리
        rename_cols = {
            '공매도잔고': '공매도 순보유 잔고수량 (주)',
            '상장주식수': '상장주식수 (주)',
            '비중': '공매도 비중 (%)'
        }
        df_combined.rename(columns=rename_cols, inplace=True)
        
        # 수집 범위 정보 메시지 구성
        price_range = f"{df_price.index[0].strftime('%Y-%m-%d')} ~ {df_price.index[-1].strftime('%Y-%m-%d')}"
        valid_short = df_combined[df_combined['공매도 순보유 잔고금액 (억원)'].notna()]
        if not valid_short.empty:
            short_range = f"{valid_short.index[0].strftime('%Y-%m-%d')} ~ {valid_short.index[-1].strftime('%Y-%m-%d')}"
        else:
            short_range = "데이터 없음"
            
        info_msg = f'<div style="font-size: 0.8rem; color: #BDC1C6; line-height: 1.4; margin-bottom: 5px;">📈 <b>주가 데이터 범위</b>: {price_range}<br/>📉 <b>공매도 데이터 범위</b> (T+2 지연반영): {short_range}</div>'
        
        return df_combined, info_msg, None
    except Exception as e:
        return pd.DataFrame(), None, f"데이터 로드 중 예외가 발생했습니다: {e}"

# -----------------------------------------------------------------------------
# 4. 메인 화면 구성
# -----------------------------------------------------------------------------
st.markdown("<h1 style='color: #8AB4F8; margin-bottom: 10px;'>한국증시 개별종목 공매도 현황</h1>", unsafe_allow_html=True)
st.markdown("<p style='color: #BDC1C6; font-size: 1.0rem; margin-bottom: 20px;'>KRX 거래소 계정 정보를 이용하여 개별 종목의 공매도 순보유잔고와 주가 추이를 분석합니다.</p>", unsafe_allow_html=True)

# 사이드바 설정
st.sidebar.header("🔑 KRX 로그인 설정")

# env 로드 값
env_id = os.getenv("KRX_ID", "")
env_pw = os.getenv("KRX_PW", "")

# 사이드바 입력창
krx_id = st.sidebar.text_input("KRX ID", value=env_id, help="data.krx.co.kr 로그인 아이디")
krx_pw = st.sidebar.text_input("KRX Password", value=env_pw, type="password", help="data.krx.co.kr 로그인 비밀번호")

login_success = False
if krx_id and krx_pw:
    login_success = try_krx_login(krx_id, krx_pw)
    if login_success:
        st.sidebar.success("✔️ KRX 로그인 성공")
    else:
        st.sidebar.error("❌ KRX 로그인 실패 (계정을 확인해 주세요)")
else:
    st.sidebar.warning("⚠️ KRX 로그인 정보 입력이 필요합니다.")

st.sidebar.markdown("---")
st.sidebar.header("🔍 조회 조건")

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
            
    selected_display = st.sidebar.selectbox("종목 선택", display_names, index=default_idx)
    # 티커 코드 추출 (마지막 괄호 안의 6자리 문자)
    selected_ticker = selected_display.split("(")[-1].replace(")", "").strip()
    selected_name = tickers_df.loc[selected_ticker, '종목']
else:
    st.sidebar.error("종목 정보를 로드할 수 없습니다.")
    st.stop()

# 기간 선택
periods = ["1W", "2W", "1M", "3M", "6M", "1Y", "YTD"]
selected_period = st.sidebar.selectbox("조회 기간", periods, index=0)

# 조회 버튼
st.sidebar.markdown("")
submit_button = st.sidebar.button("📊 조회하기", use_container_width=True)

# -----------------------------------------------------------------------------
# 5. 데이터 조회 및 시각화 영역
# -----------------------------------------------------------------------------
if login_success:
    # 조회 날짜 계산
    start_date, end_date = calculate_dates(selected_period)
    
    st.markdown(f"<h3 style='color: #BDC1C6; font-size: 1.25rem; font-weight: 600; margin-top: 10px; margin-bottom: 10px;'>{selected_name} ({selected_ticker}) - {selected_period} 공매도 분석</h3>", unsafe_allow_html=True)
    
    with st.spinner("KRX 데이터를 로드하고 있습니다..."):
        df, info_msg, err_msg = fetch_and_process_data(start_date, end_date, selected_ticker)
        
    if err_msg:
        st.error(err_msg)
        st.info("💡 팁: KRX 로그인 정보가 일치하지 않거나 세션이 만료된 경우 발생할 수 있습니다.")
    elif not df.empty:
        # 데이터 수집 범위 렌더링
        if info_msg:
            st.markdown(info_msg, unsafe_allow_html=True)
            st.markdown("")
            
        # Plotly 이중 Y축 차트 그리기 (둘 다 꺾은선 그래프)
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        
        # 1. 주가 (좌측 Y축, 꺾은선)
        fig.add_trace(
            go.Scatter(
                x=df.index.strftime('%Y-%m-%d'),
                y=df['주가'],
                name="주가 (종가)",
                mode='lines+markers',
                line=dict(color='#1f77b4', width=2), # 파란색 계열
                marker=dict(size=6),
                hovertemplate='%{x} 주가: %{y:,.0f} 원<extra></extra>'
            ),
            secondary_y=False
        )
        
        # 2. 공매도 순보유 잔고금액 (우측 Y축, 꺾은선)
        fig.add_trace(
            go.Scatter(
                x=df.index.strftime('%Y-%m-%d'),
                y=df['공매도 순보유 잔고금액 (억원)'],
                name="공매도 순보유 잔고금액 (억원)",
                mode='lines+markers',
                line=dict(color='#ff7f0e', width=2), # 주황색 계열
                marker=dict(size=6),
                hovertemplate='%{x} 공매도 순보유 잔고금액: %{y:.2f} 억원<extra></extra>'
            ),
            secondary_y=True
        )
        
        # 레이아웃 설정
        fig.update_layout(
            title_text=f"{selected_name} 주가 및 공매도 순보유 잔고금액 추이",
            title_x=0.5,
            title_xanchor="center",
            hovermode="x unified",
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="center",
                x=0.5
            ),
            margin=dict(l=20, r=20, t=80, b=20),
            height=480
        )
        
        fig.update_xaxes(title_text="날짜", type='category', tickangle=-45)
        fig.update_yaxes(title_text="주가 (원)", tickformat=",.0f", secondary_y=False)
        fig.update_yaxes(title_text="공매도 순보유 잔고금액 (억원)", tickformat=",.2f", secondary_y=True)
        
        st.plotly_chart(fig, use_container_width=True)
        
        # 일별 데이터 상세 테이블
        st.markdown("<h4 style='color: #BDC1C6; font-size: 1.05rem; font-weight: 600; margin-top: 20px; margin-bottom: 10px;'>📝 일별 데이터 상세</h4>", unsafe_allow_html=True)
        
        # 표시할 컬럼 선정
        display_cols = [
            '주가', 
            '공매도 순보유 잔고금액 (억원)', 
            '공매도 순보유 잔고수량 (주)', 
            '공매도 비중 (%)', 
            '상장주식수 (주)'
        ]
        
        # 존재하는 컬럼만 노출
        valid_display_cols = [c for c in display_cols if c in df.columns]
        df_display = df[valid_display_cols].copy()
        df_display.index = df_display.index.strftime('%Y-%m-%d')
        
        # 포맷 설정 (NaN 값은 '-'로 표시)
        styled_display = df_display.sort_index(ascending=False).style.format({
            '주가': '{:,.0f}',
            '공매도 순보유 잔고금액 (억원)': '{:.2f}',
            '공매도 순보유 잔고수량 (주)': '{:,.0f}',
            '공매도 비중 (%)': '{:.2f}',
            '상장주식수 (주)': '{:,.0f}'
        }, na_rep='-')
        
        st.dataframe(styled_display, use_container_width=True)
        
    else:
        st.warning("데이터가 비어 있습니다. 기간 설정 또는 종목을 변경해 다시 시도하세요.")
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
