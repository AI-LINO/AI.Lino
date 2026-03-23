import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import time

# 1. CONFIGURACIÓN Y ESTILO PRO
st.set_page_config(page_title="AI.Lino - Inteligencia Financiera", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    .stMetric { background-color: #161b22; border-radius: 10px; padding: 15px; border: 1px solid #30363d; }
    .footer { position: fixed; bottom: 10px; right: 10px; color: #58a6ff; font-weight: bold; font-size: 20px; }
    </style>
    """, unsafe_allow_html=True)

st.title("🚀 Motor de Inversión de Precisión v3.1")
st.subheader("Análisis Global de Activos - By AI.Lino")
st.markdown("---")

# 2. LÓGICA DE CÁLCULO
def calcular_score(peg, pe, deuda, rsi, vol, v_rel):
    score = 0
    # Lynch (25)
    score += 25 if (peg and 0 < peg < 1.2) else (20 if (pe and 0 < pe < 20) else 10)
    # Dalio (20)
    score += 20 if (deuda and deuda < 70) else 10
    # Soros (20)
    score += 20 if (rsi and rsi < 40) else (10 if (rsi and rsi < 65) else 5)
    # Simons (20)
    score += 20 if (vol and vol < 30) else 10
    # Turbo (15)
    score += 15 if (v_rel and v_rel > 1.3) else 7
    return score

# 3. ENTRADA DE DATOS
ticker_input = st.text_input("INGRESA EL SÍMBOLO (Ej: BIMBOA.MX, TSLA, NVDA):", "NVDA").upper().strip()

if st.button("⚙️ EJECUTAR ANÁLISIS MAESTRO"):
    with st.spinner("Sincronizando con mercados globales..."):
        try:
            accion = yf.Ticker(ticker_input)
            hist = accion.history(period="1y")
            
            # Protección contra bloqueos de Yahoo
            info = accion.info
            if not info:
                st.error("⚠️ Yahoo Finance no respondió. Intenta de nuevo en 1 minuto.")
                st.stop()

            # EMAs
            ema50 = hist['Close'].ewm(span=50, adjust=False).mean()
            ema200 = hist['Close'].ewm(span=200, adjust=False).mean()
            
            # Datos base
            peg = info.get('pegRatio')
            pe = info.get('trailingPE')
            deuda = info.get('debtToEquity')
            
            # RSI & Volatilidad
            delta = hist['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            rsi = 100 - (100 / (1 + (gain / loss.replace(0, np.nan)))).iloc[-1]
            vol = float(hist['Close'].pct_change().std() * np.sqrt(252) * 100)
            v_rel = float(hist['Volume'].iloc[-1] / hist['Volume'].mean())

            # TABLERO DE MÉTRICAS
            score = calcular_score(peg, pe, deuda, rsi, vol, v_rel)
            
            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric("LYNCH (Valor)", f"PE: {pe:.1f}" if pe else "N/D")
            c2.metric("DALIO (Deuda)", f"{deuda:.1f}%" if deuda else "N/D")
            c3.metric("SOROS (RSI)", f"{rsi:.1f}")
            c4.metric("SIMONS (Riesgo)", f"{vol:.1f}%")
            c5.metric("TURBO (Volumen)", f"{v_rel:.2f}x")

            st.markdown("---")

            # VERDICTO
            st.subheader(f"🎯 Score AI.Lino: {score}/100")
            if score >= 78:
                st.success("🟢 COMPRA FUERTE: Fundamentos y técnica alineados.")
                st.info("💡 REGLA: Score alto. Si el precio toca la EMA 200 (Roja), es el punto de menor riesgo.")
            elif score >= 55:
                st.warning("🟡 MANTENER: Espera confirmación de tendencia.")
            else:
                st.error("🔴 EVITAR: Riesgo alto detectado por el motor.")

            # GRÁFICA TÉCNICA
            fig = go.Figure()
            fig.add_trace(go.Candlestick(x=hist.index, open=hist['Open'], high=hist['High'], low=hist['Low'], close=hist['Close'], name="Precio"))
            fig.add_trace(go.Scatter(x=hist.index, y=ema50, line=dict(color='#FFD700', width=2), name="EMA 50 (DORADA)"))
            fig.add_trace(go.Scatter(x=hist.index, y=ema200, line=dict(color='#FF4B4B', width=2.5, dash='dash'), name="EMA 200 (ROJA)"))
            
            fig.update_layout(template="plotly_dark", height=600, xaxis_rangeslider_visible=False)
            st.plotly_chart(fig, use_container_width=True)

        except Exception as e:
            st.error(f"Falla en la conexión: {e}. Por favor, espera 30 segundos y reintenta.")

# MARCA PERSONAL
st.markdown('<div class="footer">AI.Lino ®</div>', unsafe_allow_html=True)

# 4. MANUAL
with st.expander("📖 MANUAL DE OPERACIÓN - AI.LINO"):
    st.write("""
    - **Score > 78:** Compra Fuerte.
    - **EMA 200 (Roja):** Es el piso. Si el precio está cerca de ella y el score es verde, es la entrada perfecta.
    - **Turbo:** Debe ser mayor a 1.30x para confirmar que hay interés real.
    """)
