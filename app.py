"""
KOSDAQ 주식 분석 대시보드 — Streamlit 앱 (Gemini AI 연동)
실행: streamlit run app.py
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import random
import requests

st.set_page_config(
    page_title="KOSDAQ 주식 분석 대시보드",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;700&display=swap');
html, body, [class*="css"] { font-family: 'Noto Sans KR', sans-serif; }
.info-box {
    background:#f0f4ff; border-left:4px solid #1a73e8;
    border-radius:0 8px 8px 0; padding:12px 16px;
    font-size:0.82rem; color:#333; line-height:1.7;
}
.warn-box {
    background:#fff8e1; border-left:4px solid #ffa000;
    border-radius:0 8px 8px 0; padding:10px 14px;
    font-size:0.78rem; color:#555; margin-top:8px;
}
.ai-result {
    background: #f8f9ff; border-radius: 12px;
    padding: 20px; border: 1px solid #e0e4ff;
    line-height: 1.8; font-size: 0.9rem;
}
</style>
""", unsafe_allow_html=True)

# ── Gemini API 호출 ─────────────────────────────────────────
def ask_gemini(api_key: str, prompt: str) -> str:
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"gemini-2.0-flash:generateContent?key={api_key}"
    )
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    try:
        res = requests.post(url, json=payload, timeout=30)
        res.raise_for_status()
        return res.json()["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        return f"❌ API 오류: {e}"

# ── 사이드바 ────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚙️ 설정")
    st.markdown("---")
    st.markdown("**🤖 Gemini AI 설정**")
    gemini_key = st.text_input(
        "Gemini API 키",
        type="password",
        placeholder="AIza...",
        help="aistudio.google.com 에서 무료 발급"
    )
    if not gemini_key:
        st.markdown("""
<div class='warn-box'>
AI 의견 탭 사용하려면 API 키 필요해요.<br>
<a href='https://aistudio.google.com/app/apikey' target='_blank'>
👉 무료 발급 받기</a>
</div>
""", unsafe_allow_html=True)
    else:
        st.success("✅ API 키 입력됨")

    st.markdown("---")
    market = st.selectbox("시장", ["KOSDAQ", "KOSPI", "전체"])
    price_pos_limit = st.slider("가격위치 상한 %", 5, 50, 15, step=5)
    investor_cond = st.radio("수급 조건", ["기관 + 외국인 동시", "기관만", "외국인만"])
    pbr_limit = st.slider("PBR 상한", 0.5, 5.0, 1.5, step=0.1)
    per_positive = st.checkbox("PER 양수만", value=True)
    top_n = st.slider("결과 상위 N개", 5, 50, 20, step=5)
    st.markdown("---")
    run_btn = st.button("🔍 스크리닝 실행", use_container_width=True, type="primary")
    st.markdown("""
<div class='warn-box'>
⚠️ 본 서비스는 <b>참고용</b>입니다.<br>
투자 결과 책임은 본인에게 있습니다.
</div>
""", unsafe_allow_html=True)

# ── 메인 ────────────────────────────────────────────────────
st.markdown("# 📊 KOSDAQ 주식 분석 대시보드")
st.markdown("##### pykrx 기반 실시간 스크리닝 · Gemini AI 매수/매도 의견 · 수급/재무 통합 분석")

tab1, tab2, tab3 = st.tabs(["🔍 스크리너", "📈 종목 분석", "🤖 AI 의견 (Gemini)"])

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
        results = []
        try:
            from pykrx import stock
            import warnings; warnings.filterwarnings('ignore')

            today           = datetime.now().strftime("%Y%m%d")
            one_month_ago   = (datetime.now() - timedelta(days=30)).strftime("%Y%m%d")
            three_years_ago = (datetime.now() - timedelta(days=365*3)).strftime("%Y%m%d")

            with st.spinner("수급 데이터 로딩 중..."): df_investor = stock.get_market_net_purchases_of_equities_by_ticker(one_month_ago, today, market if market != "전체" else "KOSDAQ")
            with st.spinner("재무 데이터 로딩 중..."): df_funda = stock.get_market_fundamental(today, market=market if market != "전체" else "KOSDAQ")
            with st.spinner("종목 리스트 로딩 중..."): tickers = stock.get_market_ticker_list(today, market=market if market != "전체" else "KOSDAQ")

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
                    inst = int(inv['기관합계']); foreign = int(inv['외국인합계'])
                    if investor_cond == "기관 + 외국인 동시" and not (inst > 0 and foreign > 0): continue
                    elif investor_cond == "기관만" and inst <= 0: continue
                    elif investor_cond == "외국인만" and foreign <= 0: continue
                    df_ohlcv = stock.get_market_ohlcv_by_date(three_years_ago, today, ticker)
                    if len(df_ohlcv) < 500: continue
                    closes = df_ohlcv['종가']
                    low_3y = closes.min(); high_3y = closes.max(); cur = int(closes.iloc[-1])
                    rng = high_3y - low_3y
                    if rng == 0: continue
                    pos = (cur - low_3y) / rng * 100
                    if pos > price_pos_limit: continue
                    name = stock.get_market_ticker_name(ticker)
                    results.append({"종목코드": ticker, "종목명": name, "현재가": cur, "가격위치%": round(pos,1), "3년저점": int(low_3y), "3년고점": int(high_3y), "PBR": round(pbr,2), "PER": round(per,1), "기관순매수": inst, "외국인순매수": foreign})
                except Exception:
                    continue
            prog.empty()

        except Exception:
            st.warning("pykrx 연결 실패 — 데모 데이터로 표시합니다.")

        # 데모 데이터
        if not results:
            demo = [("095340","ISC"),("039440","에스티아이"),("950130","엑세스바이오"),("950160","코오롱티슈진"),("950180","자이언트스텝"),("950190","오상헬스케어"),("950200","파나시아"),("950210","에스디바이오센서"),("950250","에코앤드림"),("950260","나인테크"),("950270","LS머트리얼즈"),("950280","한주라이트메탈"),("950300","대원미디어"),("950310","에스엔에스텍"),("950320","비씨엔씨")]
            random.seed(42)
            for code, name in demo[:top_n]:
                pos = round(random.uniform(1, 14.9), 1); low = random.randint(3000, 20000); cur = int(low*(1+pos/100*random.uniform(3,8)))
                results.append({"종목코드": code, "종목명": name, "현재가": cur, "가격위치%": pos, "3년저점": low, "3년고점": int(low*random.uniform(4,9)), "PBR": round(random.uniform(0.3,1.49),2), "PER": round(random.uniform(5,35),1), "기관순매수": random.randint(1000,80000), "외국인순매수": random.randint(500,50000)})

        df_out = pd.DataFrame(results).sort_values("가격위치%").head(top_n).reset_index(drop=True)
        df_out.index += 1

        c1,c2,c3,c4 = st.columns(4)
        c1.metric("발굴 종목 수", f"{len(df_out)}개")
        c2.metric("평균 가격위치", f"{df_out['가격위치%'].mean():.1f}%")
        c3.metric("평균 PBR", f"{df_out['PBR'].mean():.2f}")
        c4.metric("평균 PER", f"{df_out['PER'].mean():.1f}")
        st.markdown("")

        st.dataframe(df_out[["종목코드","종목명","현재가","가격위치%","PBR","PER","기관순매수","외국인순매수"]], use_container_width=True,
            column_config={"현재가": st.column_config.NumberColumn(format="%d원"), "가격위치%": st.column_config.ProgressColumn("가격위치%", min_value=0, max_value=100, format="%.1f%%"), "기관순매수": st.column_config.NumberColumn(format="%d주"), "외국인순매수": st.column_config.NumberColumn(format="%d주")},
            height=min(60+len(df_out)*38, 640))
        st.bar_chart(df_out.set_index("종목명")["가격위치%"])

        if gemini_key and st.button("🤖 Gemini로 전체 결과 분석"):
            with st.spinner("Gemini 분석 중..."):
                top5 = df_out.head(5)[["종목명","가격위치%","PBR","PER","기관순매수","외국인순매수"]].to_string(index=False)
                prompt = f"""당신은 한국 주식 전문 애널리스트입니다.
KOSDAQ 저점 스크리닝 결과 상위 5개 종목입니다 (조건: 3년 저점 대비 {price_pos_limit}% 이내, PBR {pbr_limit} 이하, {investor_cond} 순매수):

{top5}

각 종목 투자 매력도(매수/관망/매도)와 핵심 근거 2줄, 마지막에 전체 요약 한 줄. 한국어로 간결하게."""
                st.markdown('<div class="ai-result">', unsafe_allow_html=True)
                st.markdown(ask_gemini(gemini_key, prompt))
                st.markdown('</div>', unsafe_allow_html=True)

        csv = df_out.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
        st.download_button("⬇️ CSV 다운로드", csv, "kosdaq_result.csv", "text/csv")

    else:
        st.markdown("← 왼쪽 사이드바에서 조건 설정 후 **스크리닝 실행** 버튼을 누르세요.")

# ══════════════════════════════════════════════
# TAB 2 — 종목 분석
# ══════════════════════════════════════════════
with tab2:
    col_a, col_b = st.columns([2,1])
    with col_a:
        ticker_input = st.text_input("종목코드 (6자리)", placeholder="예: 005930")
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
            cur = int(closes.iloc[-1]); low_3y = int(closes.min()); high_3y = int(closes.max())
            pos = round((cur-low_3y)/(high_3y-low_3y)*100, 1)
            chg = round((closes.iloc[-1]/closes.iloc[-2]-1)*100, 2)
            st.subheader(f"📌 {name} ({ticker})")
            m1,m2,m3,m4 = st.columns(4)
            m1.metric("현재가", f"{cur:,}원", f"{chg:+.2f}%")
            m2.metric("3년 가격위치", f"{pos}%")
            m3.metric("3년 저점", f"{low_3y:,}원")
            m4.metric("3년 고점", f"{high_3y:,}원")
            st.line_chart(df_ohlcv['종가'].rename(f"{name} 종가"))
            if not df_funda2.empty:
                row2 = df_funda2.iloc[-1]
                fc1,fc2,fc3 = st.columns(3)
                fc1.metric("PBR", f"{row2['PBR']:.2f}")
                fc2.metric("PER", f"{row2['PER']:.1f}")
                fc3.metric("배당수익률", f"{row2['DIV']:.2f}%")
                if gemini_key and st.button(f"🤖 {name} Gemini 분석"):
                    with st.spinner("Gemini 분석 중..."):
                        prompt = f"""한국 주식 전문 애널리스트로서 아래 종목을 분석해주세요.
종목: {name}({ticker}) / 현재가: {cur:,}원({chg:+.2f}%) / 3년위치: {pos}% / 저점: {low_3y:,} / 고점: {high_3y:,} / PBR: {row2['PBR']:.2f} / PER: {row2['PER']:.1f} / 배당: {row2['DIV']:.2f}%
형식: ## 종합의견(매수/관망/매도) ## 근거3가지 ## 목표가및손절 ## 한줄요약. 한국어로."""
                        st.markdown('<div class="ai-result">', unsafe_allow_html=True)
                        st.markdown(ask_gemini(gemini_key, prompt))
                        st.markdown('</div>', unsafe_allow_html=True)
        except Exception:
            st.info("종목코드(6자리)를 확인해주세요. 예: 삼성전자 → 005930")

# ══════════════════════════════════════════════
# TAB 3 — AI 의견 (Gemini)
# ══════════════════════════════════════════════
with tab3:
    st.markdown("#### 🤖 Gemini AI 매수/매도 의견")
    if not gemini_key:
        st.markdown("""
<div class='warn-box'>
왼쪽 사이드바에 Gemini API 키를 입력하세요.<br>
<a href='https://aistudio.google.com/app/apikey' target='_blank'>
👉 무료 발급 받기 (Google 계정만 있으면 됩니다)</a>
</div>
""", unsafe_allow_html=True)
    else:
        ai_ticker = st.text_input("종목명", placeholder="예: 셀트리온")
        c1,c2,c3 = st.columns(3)
        with c1:
            ai_price = st.number_input("현재가 (원)", value=50000, step=100)
            ai_pos   = st.number_input("3년 가격위치 (%)", 0.0, 100.0, 8.5, step=0.1)
        with c2:
            ai_pbr   = st.number_input("PBR", 0.0, 10.0, 0.85, step=0.01)
            ai_per   = st.number_input("PER", 0.0, 200.0, 12.3, step=0.1)
        with c3:
            ai_inst  = st.number_input("기관 순매수 (주)", value=25000, step=1000)
            ai_for   = st.number_input("외국인 순매수 (주)", value=12000, step=1000)
        free_text = st.text_area("추가 정보 (선택)", placeholder="예: 최근 실적 발표, 신제품 출시, 업황 변화 등")

        if st.button("🤖 Gemini 분석 요청", type="primary"):
            with st.spinner("Gemini가 분석 중입니다..."):
                prompt = f"""한국 주식 전문 애널리스트로서 투자 의견을 제시해주세요.
종목: {ai_ticker or '미입력'} / 현재가: {ai_price:,}원 / 3년위치: {ai_pos}% / PBR: {ai_pbr} / PER: {ai_per} / 기관순매수: {ai_inst:,}주 / 외국인순매수: {ai_for:,}주
{f'추가정보: {free_text}' if free_text else ''}
형식: ## 종합의견(매수/관망/매도) ## 핵심근거3가지 ## 목표가및손절기준 ## 한줄요약. 한국어로 전문적이고 간결하게."""
                st.markdown('<div class="ai-result">', unsafe_allow_html=True)
                st.markdown(ask_gemini(gemini_key, prompt))
                st.markdown('</div>', unsafe_allow_html=True)

        st.markdown("""
<div class='warn-box'>
⚠️ AI 의견은 참고용이며 투자 권유가 아닙니다. 최종 투자 판단은 본인 책임입니다.
</div>
""", unsafe_allow_html=True)
