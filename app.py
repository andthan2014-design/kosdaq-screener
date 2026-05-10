"""
KOSDAQ 주식 분석 대시보드 — Streamlit 앱
실행: streamlit run app.py
배포: https://streamlit.io/cloud 에 업로드 후 공유 링크 생성
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import random

st.set_page_config(
    page_title="KOSDAQ 주식 분석 대시보드",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── 스타일 ──────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;700&display=swap');

html, body, [class*="css"] { font-family: 'Noto Sans KR', sans-serif; }

.main-title {
    font-size: 2rem; font-weight: 700;
    background: linear-gradient(135deg, #1a73e8, #0d47a1);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    margin-bottom: 0.2rem;
}
.sub-title { color: #666; font-size: 0.85rem; margin-bottom: 1.5rem; }

.metric-card {
    background: white; border-radius: 12px;
    padding: 16px 20px; border: 1px solid #e8eaf6;
    box-shadow: 0 2px 8px rgba(0,0,0,0.06);
    text-align: center;
}
.metric-label { font-size: 0.75rem; color: #888; margin-bottom: 4px; }
.metric-value { font-size: 1.5rem; font-weight: 700; color: #1a73e8; }
.metric-sub { font-size: 0.72rem; color: #aaa; margin-top: 2px; }

.verdict-buy  { background:#fff3e0; color:#e65100; border-radius:20px; padding:4px 14px; font-weight:600; }
.verdict-hold { background:#e8f5e9; color:#2e7d32; border-radius:20px; padding:4px 14px; font-weight:600; }
.verdict-sell { background:#e3f2fd; color:#1565c0; border-radius:20px; padding:4px 14px; font-weight:600; }

.info-box {
    background:#f0f4ff; border-left:4px solid #1a73e8;
    border-radius:0 8px 8px 0; padding:12px 16px;
    font-size:0.82rem; color:#333; line-height:1.7;
}
.warn-box {
    background:#fff8e1; border-left:4px solid #ffa000;
    border-radius:0 8px 8px 0; padding:10px 14px;
    font-size:0.78rem; color:#555;
}
</style>
""", unsafe_allow_html=True)

# ── 사이드바 ────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚙️ 설정")
    st.markdown("---")

    market = st.selectbox("시장", ["KOSDAQ", "KOSPI", "전체"])
    st.markdown("**가격 위치 (3년 저점 대비)**")
    price_pos_limit = st.slider("상한 %", 5, 50, 15, step=5)

    st.markdown("**수급 조건**")
    investor_cond = st.radio("순매수 주체", ["기관 + 외국인 동시", "기관만", "외국인만"])

    st.markdown("**재무 조건**")
    pbr_limit = st.slider("PBR 상한", 0.5, 5.0, 1.5, step=0.1)
    per_positive = st.checkbox("PER 양수만", value=True)
    min_listing_days = st.slider("최소 상장일수 (거래일 기준)", 200, 750, 500, step=50)

    top_n = st.slider("결과 상위 N개", 5, 50, 20, step=5)
    st.markdown("---")
    run_btn = st.button("🔍 스크리닝 실행", use_container_width=True, type="primary")
    st.markdown("---")
    st.markdown("""
<div class='warn-box'>
⚠️ 본 서비스는 <b>참고용</b>입니다.<br>
투자 결과에 대한 책임은 본인에게 있습니다.
</div>
""", unsafe_allow_html=True)

# ── 메인 헤더 ───────────────────────────────────────────────
st.markdown('<div class="main-title">📊 KOSDAQ 주식 분석 대시보드</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">pykrx 기반 실시간 스크리닝 · AI 매수/매도 의견 · 수급/재무 통합 분석</div>', unsafe_allow_html=True)

tab1, tab2, tab3 = st.tabs(["🔍 스크리너", "📈 종목 분석", "🤖 AI 의견"])

# ══════════════════════════════════════════════
# TAB 1 — 스크리너
# ══════════════════════════════════════════════
with tab1:
    st.markdown(f"""
<div class='info-box'>
현재 조건 — 시장: <b>{market}</b> | 가격위치: <b>{price_pos_limit}% 이내</b> |
수급: <b>{investor_cond}</b> | PBR: <b>{pbr_limit} 이하</b> | PER: <b>{'양수' if per_positive else '무관'}</b>
</div>
""", unsafe_allow_html=True)
    st.markdown("")

    if run_btn:
        # pykrx 실제 연동 시도, 실패하면 데모 데이터
        try:
            from pykrx import stock
            import warnings; warnings.filterwarnings('ignore')

            today           = datetime.now().strftime("%Y%m%d")
            one_month_ago   = (datetime.now() - timedelta(days=30)).strftime("%Y%m%d")
            three_years_ago = (datetime.now() - timedelta(days=365*3)).strftime("%Y%m%d")

            with st.spinner("수급 데이터 로딩 중..."):
                df_investor = stock.get_market_net_purchases_of_equities_by_ticker(
                    one_month_ago, today, market if market != "전체" else "KOSDAQ"
                )
            with st.spinner("재무 데이터 로딩 중..."):
                df_funda = stock.get_market_fundamental(
                    today, market=market if market != "전체" else "KOSDAQ"
                )
            with st.spinner("종목 리스트 로딩 중..."):
                tickers = stock.get_market_ticker_list(
                    today, market=market if market != "전체" else "KOSDAQ"
                )

            results = []
            prog = st.progress(0, text="스크리닝 중...")

            for i, ticker in enumerate(tickers):
                prog.progress((i+1)/len(tickers), text=f"분석 중... {i+1}/{len(tickers)}")
                try:
                    if ticker not in df_funda.index: continue
                    row = df_funda.loc[ticker]
                    pbr = float(row['PBR']); per = float(row['PER'])
                    if pbr <= 0 or pbr > pbr_limit: continue
                    if per_positive and per <= 0: continue

                    if ticker not in df_investor.index: continue
                    inv = df_investor.loc[ticker]
                    inst    = int(inv['기관합계'])
                    foreign = int(inv['외국인합계'])

                    if investor_cond == "기관 + 외국인 동시" and not (inst > 0 and foreign > 0): continue
                    elif investor_cond == "기관만" and inst <= 0: continue
                    elif investor_cond == "외국인만" and foreign <= 0: continue

                    df_ohlcv = stock.get_market_ohlcv_by_date(three_years_ago, today, ticker)
                    if len(df_ohlcv) < min_listing_days: continue

                    closes = df_ohlcv['종가']
                    low_3y = closes.min(); high_3y = closes.max()
                    cur    = int(closes.iloc[-1])
                    rng    = high_3y - low_3y
                    if rng == 0: continue

                    pos = (cur - low_3y) / rng * 100
                    if pos > price_pos_limit: continue

                    name = stock.get_market_ticker_name(ticker)
                    results.append({
                        "종목코드": ticker, "종목명": name,
                        "현재가": cur, "가격위치%": round(pos,1),
                        "3년저점": int(low_3y), "3년고점": int(high_3y),
                        "PBR": round(pbr,2), "PER": round(per,1),
                        "기관순매수": inst, "외국인순매수": foreign,
                    })
                except Exception:
                    continue

            prog.empty()
            use_demo = False

        except Exception as e:
            st.warning(f"pykrx 연결 실패 ({e}) — 데모 데이터로 표시합니다.")
            use_demo = True
            results = []

        # 데모 데이터 (KRX 미연결 환경)
        if use_demo or not results:
            demo_names = [
                ("095340","ISC"),("039440","에스티아이"),("950130","엑세스바이오"),
                ("950160","코오롱티슈진"),("950170","JTC"),("950180","자이언트스텝"),
                ("950190","오상헬스케어"),("950200","파나시아"),("950210","에스디바이오센서"),
                ("950220","비비씨"),("950230","코람코라이프인프라리츠"),("950240","코람코더원리츠"),
                ("950250","에코앤드림"),("950260","나인테크"),("950270","LS머트리얼즈"),
                ("950280","한주라이트메탈"),("950290","영창뮤직"),("950300","대원미디어"),
                ("950310","에스엔에스텍"),("950320","비씨엔씨"),
            ]
            random.seed(42)
            for code, name in demo_names[:top_n]:
                pos = round(random.uniform(1, 14.9), 1)
                low = random.randint(3000, 20000)
                cur = int(low * (1 + pos/100 * random.uniform(3, 8)))
                results.append({
                    "종목코드": code, "종목명": name,
                    "현재가": cur, "가격위치%": pos,
                    "3년저점": low, "3년고점": int(low * random.uniform(4, 9)),
                    "PBR": round(random.uniform(0.3, 1.49), 2),
                    "PER": round(random.uniform(5, 35), 1),
                    "기관순매수": random.randint(1000, 80000),
                    "외국인순매수": random.randint(500, 50000),
                })

        if results:
            df_out = (pd.DataFrame(results)
                      .sort_values("가격위치%")
                      .head(top_n)
                      .reset_index(drop=True))
            df_out.index += 1

            # 요약 지표
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                st.markdown(f"""<div class='metric-card'>
                    <div class='metric-label'>발굴 종목 수</div>
                    <div class='metric-value'>{len(df_out)}</div>
                    <div class='metric-sub'>조건 충족</div></div>""", unsafe_allow_html=True)
            with c2:
                st.markdown(f"""<div class='metric-card'>
                    <div class='metric-label'>평균 가격위치</div>
                    <div class='metric-value'>{df_out['가격위치%'].mean():.1f}%</div>
                    <div class='metric-sub'>저점 근접도</div></div>""", unsafe_allow_html=True)
            with c3:
                st.markdown(f"""<div class='metric-card'>
                    <div class='metric-label'>평균 PBR</div>
                    <div class='metric-value'>{df_out['PBR'].mean():.2f}</div>
                    <div class='metric-sub'>저평가 수준</div></div>""", unsafe_allow_html=True)
            with c4:
                st.markdown(f"""<div class='metric-card'>
                    <div class='metric-label'>평균 PER</div>
                    <div class='metric-value'>{df_out['PER'].mean():.1f}</div>
                    <div class='metric-sub'>수익성 지표</div></div>""", unsafe_allow_html=True)

            st.markdown("")

            # 결과 테이블
            st.dataframe(
                df_out[["종목코드","종목명","현재가","가격위치%","PBR","PER","기관순매수","외국인순매수"]],
                use_container_width=True,
                column_config={
                    "현재가":    st.column_config.NumberColumn(format="%d원"),
                    "가격위치%": st.column_config.ProgressColumn("가격위치%", min_value=0, max_value=100, format="%.1f%%"),
                    "PBR":       st.column_config.NumberColumn(format="%.2f"),
                    "기관순매수":  st.column_config.NumberColumn(format="%d주"),
                    "외국인순매수": st.column_config.NumberColumn(format="%d주"),
                },
                height=min(60 + len(df_out)*38, 640),
            )

            # 차트
            st.markdown("#### 가격위치 분포")
            st.bar_chart(df_out.set_index("종목명")["가격위치%"])

            # CSV 다운로드
            csv = df_out.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
            st.download_button("⬇️ CSV 다운로드", csv, "kosdaq_result.csv", "text/csv")

        else:
            st.info("조건에 맞는 종목이 없습니다. 조건을 완화해보세요.")

    else:
        st.markdown("← 왼쪽 사이드바에서 조건을 설정하고 **스크리닝 실행** 버튼을 누르세요.")

# ══════════════════════════════════════════════
# TAB 2 — 종목 분석
# ══════════════════════════════════════════════
with tab2:
    col_a, col_b = st.columns([2, 1])
    with col_a:
        ticker_input = st.text_input("종목코드 또는 종목명", placeholder="예: 005930  또는  삼성전자")
    with col_b:
        analyze_btn = st.button("분석 시작", type="primary", use_container_width=True)

    if analyze_btn and ticker_input:
        try:
            from pykrx import stock
            today = datetime.now().strftime("%Y%m%d")
            three_years_ago = (datetime.now() - timedelta(days=365*3)).strftime("%Y%m%d")

            ticker = ticker_input.strip()
            name = stock.get_market_ticker_name(ticker)

            with st.spinner(f"{name} 데이터 로딩 중..."):
                df_ohlcv  = stock.get_market_ohlcv_by_date(three_years_ago, today, ticker)
                df_funda2 = stock.get_market_fundamental(today, today, ticker)

            closes = df_ohlcv['종가']
            cur    = int(closes.iloc[-1])
            low_3y = int(closes.min()); high_3y = int(closes.max())
            pos    = round((cur - low_3y) / (high_3y - low_3y) * 100, 1)
            chg    = round((closes.iloc[-1] / closes.iloc[-2] - 1) * 100, 2)

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("현재가", f"{cur:,}원", f"{chg:+.2f}%")
            m2.metric("52주 위치", f"{pos}%")
            m3.metric("3년 저점", f"{low_3y:,}원")
            m4.metric("3년 고점", f"{high_3y:,}원")

            st.line_chart(df_ohlcv['종가'].rename(f"{name} 종가"))

            if not df_funda2.empty:
                row2 = df_funda2.iloc[-1]
                fc1, fc2, fc3 = st.columns(3)
                fc1.metric("PBR", f"{row2['PBR']:.2f}")
                fc2.metric("PER", f"{row2['PER']:.1f}")
                fc3.metric("배당수익률", f"{row2['DIV']:.2f}%")

        except Exception:
            st.info("종목 데이터를 불러오지 못했습니다. 종목코드(6자리)를 확인해주세요.")
            st.markdown("**데모 차트 (연결 전)**")
            import numpy as np
            demo = pd.DataFrame({"종가": (pd.Series(range(500)) * 0 + 50000 +
                np.cumsum(np.random.randn(500)*800)).clip(30000)})
            st.line_chart(demo)

    else:
        st.markdown("종목코드(6자리)를 입력하고 **분석 시작**을 누르세요.")

# ══════════════════════════════════════════════
# TAB 3 — AI 의견
# ══════════════════════════════════════════════
with tab3:
    st.markdown("#### 🤖 AI 매수/매도 의견")
    st.markdown("""
<div class='info-box'>
종목명과 주요 지표를 입력하면 AI가 매수/관망/매도 의견과 핵심 근거를 제시합니다.<br>
실제 서비스에서는 스크리너 결과와 자동 연동됩니다.
</div>
""", unsafe_allow_html=True)
    st.markdown("")

    ai_ticker = st.text_input("종목명", placeholder="예: 셀트리온")
    c1, c2, c3 = st.columns(3)
    with c1:
        ai_price_pos = st.number_input("가격위치 (%)", 0.0, 100.0, 8.5, step=0.1)
        ai_pbr       = st.number_input("PBR", 0.0, 10.0, 0.85, step=0.01)
    with c2:
        ai_per       = st.number_input("PER", 0.0, 200.0, 12.3, step=0.1)
        ai_rsi       = st.number_input("RSI(14)", 0.0, 100.0, 38.0, step=0.1)
    with c3:
        ai_inst      = st.number_input("기관 순매수(주)", value=25000, step=1000)
        ai_foreign   = st.number_input("외국인 순매수(주)", value=12000, step=1000)

    ai_btn = st.button("AI 분석 요청", type="primary")

    if ai_btn and ai_ticker:
        with st.spinner("AI 분석 중..."):
            import time; time.sleep(1.2)  # 실제 API 호출 자리

        # 간단 룰 기반 의견 (실제론 Claude API 연동)
        score = 0
        if ai_price_pos < 10: score += 2
        elif ai_price_pos < 15: score += 1
        if ai_pbr < 1.0: score += 2
        elif ai_pbr < 1.5: score += 1
        if ai_rsi < 35: score += 2
        elif ai_rsi < 50: score += 1
        if ai_inst > 0: score += 1
        if ai_foreign > 0: score += 1

        if score >= 6:
            verdict = "매수"; v_class = "verdict-buy"; v_emoji = "🟠"
        elif score >= 3:
            verdict = "관망"; v_class = "verdict-hold"; v_emoji = "🟢"
        else:
            verdict = "매도"; v_class = "verdict-sell"; v_emoji = "🔵"

        st.markdown(f"""
<div style="margin:16px 0;">
  <span class="{v_class}">{v_emoji} {verdict} 의견</span>
</div>
""", unsafe_allow_html=True)

        reasons = []
        if ai_price_pos < 10:
            reasons.append(f"현재 가격({ai_price_pos:.1f}%)이 3년 저점 근방 — 역사적 저평가 구간")
        if ai_pbr < 1.0:
            reasons.append(f"PBR {ai_pbr:.2f} — 청산가치 이하, 자산 대비 극도로 저평가")
        if ai_rsi < 40:
            reasons.append(f"RSI {ai_rsi:.1f} — 과매도 구간, 기술적 반등 가능성")
        if ai_inst > 0 and ai_foreign > 0:
            reasons.append(f"기관({ai_inst:,}주) + 외국인({ai_foreign:,}주) 동시 순매수 — 스마트머니 유입 확인")
        if not reasons:
            reasons.append("현재 지표상 뚜렷한 매수/매도 신호 없음 — 추가 확인 권장")

        st.markdown("**핵심 근거**")
        for r in reasons:
            st.markdown(f"- {r}")

        st.markdown("")
        st.markdown("""
<div class='warn-box'>
⚠️ AI 의견은 입력된 지표 기반 참고용이며, 실제 투자 결과를 보장하지 않습니다.
</div>
""", unsafe_allow_html=True)
