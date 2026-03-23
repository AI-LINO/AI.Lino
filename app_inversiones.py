import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# ─────────────────────────────────────────────
# 1. CONFIGURACIÓN Y ESTILO PRO
# ─────────────────────────────────────────────
st.set_page_config(page_title="AI.Lino - Inteligencia Financiera", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    .stMetric { background-color: #161b22; border-radius: 10px; padding: 15px; border: 1px solid #30363d; }
    .footer { position: fixed; bottom: 10px; right: 10px; color: #58a6ff; font-weight: bold; font-size: 20px; }
    </style>
    """, unsafe_allow_html=True)

st.title("🚀 Motor de Inversión de Precisión v3.0")
st.subheader("Análisis Global de Activos - By AI.Lino")
st.markdown("---")

# ─────────────────────────────────────────────
# 2. HELPERS — Extracción segura de datos
# ─────────────────────────────────────────────
def safe_float(val):
    """Convierte a float; devuelve None si es NaN, None o no numérico."""
    try:
        f = float(val)
        return None if np.isnan(f) else f
    except (TypeError, ValueError):
        return None

def calcular_rsi(close: pd.Series, period: int = 14):
    """Calcula RSI y devuelve el último valor. Retorna None si no hay datos suficientes."""
    delta = close.diff()
    gain  = delta.where(delta > 0, 0.0).rolling(period).mean()
    loss  = (-delta.where(delta < 0, 0.0)).rolling(period).mean()
    rs    = gain / loss.replace(0, np.nan)
    rsi_s = 100 - (100 / (1 + rs))
    last  = rsi_s.dropna()
    return float(last.iloc[-1]) if not last.empty else None

# ─────────────────────────────────────────────
# 3. SCORE PONDERADO — FIX: manejo correcto de None
# ─────────────────────────────────────────────
def calcular_score(peg, pe, deuda, rsi, vol, v_rel):
    score = 0

    # Lynch (25 pts) — valor fundamental
    if peg is not None and 0 < peg < 1.2:
        score += 25
    elif pe is not None and 0 < pe < 20:
        score += 20
    elif pe is not None and 0 < pe < 30:
        score += 12
    else:
        score += 8   # sin datos o valor alto → puntaje conservador

    # Dalio (20 pts) — salud financiera
    if deuda is None:
        score += 10  # neutro por falta de datos
    elif deuda < 50:
        score += 20
    elif deuda < 70:
        score += 15
    elif deuda < 100:
        score += 8
    else:
        score += 3

    # Soros (20 pts) — psicología / RSI
    if rsi is None:
        score += 10
    elif rsi < 30:
        score += 20  # sobreventa fuerte
    elif rsi < 45:
        score += 16
    elif rsi < 65:
        score += 10
    else:
        score += 3   # sobrecompra

    # Simons (20 pts) — volatilidad
    if vol is None:
        score += 10
    elif vol < 25:
        score += 20
    elif vol < 40:
        score += 14
    elif vol < 60:
        score += 7
    else:
        score += 3

    # Turbo (15 pts) — presión de volumen
    if v_rel is None:
        score += 7
    elif 1.3 <= v_rel <= 3.0:
        score += 15
    elif v_rel >= 1.0:
        score += 10
    else:
        score += 5

    return score

# ─────────────────────────────────────────────
# 4. ENTRADA DE DATOS
# ─────────────────────────────────────────────
ticker_input = st.text_input(
    "INGRESA EL SÍMBOLO (Ej: BIMBOA.MX, TSLA, NVDA):", "NVDA"
).upper().strip()

if st.button("⚙️ EJECUTAR ANÁLISIS MAESTRO"):
    with st.spinner("Sincronizando con mercados globales..."):
        accion = yf.Ticker(ticker_input)
        hist   = accion.history(period="1y")
        # Info fundamental
        try:
            import time
            time.sleep(1)  # pausa de 1 segundo para evitar rate limit
            info = accion.info
            nombre_empresa = info.get('longName', ticker_limpio)
            sector = info.get('sector', 'N/A')
            pais = info.get('country', 'N/A')
        except Exception:
            info = {}
            nombre_empresa = ticker_limpio
            sector = 'N/A'
            pais = 'N/A'

    # FIX Bug #2: eliminamos el len(hist) < 200 para no bloquear BMV
    if hist.empty:
        st.error("⚠️ Error: Ticker no encontrado. Verifica el símbolo. "
                 "Para México usa .MX (ej: BIMBOA.MX). Para EE.UU. usa el ticker directo.")
        st.stop()

    # ── Extracción segura (FIX Bug #1 y #3) ─────
    peg   = safe_float(info.get("pegRatio"))
    pe    = safe_float(info.get("trailingPE"))
    deuda = safe_float(info.get("debtToEquity"))

    ema50  = hist["Close"].ewm(span=50,  adjust=False).mean()
    ema200 = hist["Close"].ewm(span=200, adjust=False).mean()

    rsi   = calcular_rsi(hist["Close"])           # FIX Bug #3 — nunca lanza NaN al UI
    vol   = safe_float(hist["Close"].pct_change().std() * np.sqrt(252) * 100)
    v_rel = safe_float(hist["Volume"].iloc[-1] / hist["Volume"].mean()) \
            if hist["Volume"].mean() > 0 else None

    score = calcular_score(peg, pe, deuda, rsi, vol, v_rel)

    # ── Tablero de métricas ──────────────────────
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("LYNCH (Valor)",    f"PE: {pe:.1f}"    if pe    is not None else "N/D", "Puntaje Valor")
    c2.metric("DALIO (Deuda)",    f"{deuda:.1f}%"    if deuda is not None else "N/D", "Puntaje Deuda")
    c3.metric("SOROS (RSI)",      f"{rsi:.1f}"       if rsi   is not None else "N/D", "Puntaje Psicología")
    c4.metric("SIMONS (Riesgo)",  f"{vol:.1f}%"      if vol   is not None else "N/D", "Puntaje Estocástico")
    c5.metric("TURBO (Volumen)",  f"{v_rel:.2f}x"    if v_rel is not None else "N/D", "Puntaje Presión")

    st.markdown("---")

    # ── Veredicto y estrategia ───────────────────
    st.subheader(f"🎯 Score AI.Lino: {score}/100")

    if score >= 78:
        st.success("🟢 COMPRA FUERTE: Fundamentos y técnica alineados.")
        st.info("💡 REGLA DE ORO: Score alto. Si el precio está tocando la EMA 200 (línea roja), "
                "es tu entrada de menor riesgo.")
    elif score >= 55:
        st.warning("🟡 COMPRA MODERADA / MANTENER: Espera confirmación de tendencia.")
    else:
        st.error("🔴 EVITAR: El motor detecta debilidad estructural o precio excesivo.")

    # Aviso de datos faltantes
    faltantes = [n for n, v in [("PEG", peg), ("P/E", pe), ("Deuda", deuda), ("RSI", rsi)] if v is None]
    if faltantes:
        st.info(f"ℹ️ Sin datos en Yahoo Finance para: **{', '.join(faltantes)}**. "
                "Se usó puntaje neutro en esas dimensiones.")

    # ── Gráfica técnica profesional ─────────────
    fig = go.Figure()
    fig.add_trace(go.Candlestick(
        x=hist.index,
        open=hist["Open"], high=hist["High"],
        low=hist["Low"],   close=hist["Close"],
        name="Precio",
        increasing_line_color="#26a69a",
        decreasing_line_color="#ef5350"
    ))
    fig.add_trace(go.Scatter(
        x=hist.index, y=ema50,
        line=dict(color="#FFD700", width=2),
        name="EMA 50 (Mediano Plazo)"
    ))
    fig.add_trace(go.Scatter(
        x=hist.index, y=ema200,
        line=dict(color="#FF4B4B", width=2.5, dash="dash"),
        name="EMA 200 (Largo Plazo)"
    ))

    fig.update_layout(
        template="plotly_dark", height=600,
        xaxis_rangeslider_visible=False,
        legend=dict(orientation="h", y=1.02),
        margin=dict(l=10, r=10, t=40, b=10)
    )
    st.plotly_chart(fig, use_container_width=True)

    # Señal de cruce EMA
    if len(ema50.dropna()) >= 2 and len(ema200.dropna()) >= 2:
        if ema50.iloc[-1] > ema200.iloc[-1] and ema50.iloc[-2] <= ema200.iloc[-2]:
            st.success("⚡ GOLDEN CROSS detectado: EMA50 cruzó hacia arriba la EMA200 — señal alcista.")
        elif ema50.iloc[-1] < ema200.iloc[-1] and ema50.iloc[-2] >= ema200.iloc[-2]:
            st.error("⚡ DEATH CROSS detectado: EMA50 cruzó hacia abajo la EMA200 — señal bajista.")

        tend = "📈 Tendencia ALCISTA" if ema50.iloc[-1] > ema200.iloc[-1] else "📉 Tendencia BAJISTA"
        st.caption(f"{tend} (EMA50 {'>' if ema50.iloc[-1] > ema200.iloc[-1] else '<'} EMA200)")

# ─────────────────────────────────────────────
# MARCA PERSONAL
# ─────────────────────────────────────────────
st.markdown('<div class="footer">AI.Lino ®</div>', unsafe_allow_html=True)

# ─────────────────────────────────────────────
# MANUAL DE OPERACIONES
# ─────────────────────────────────────────────
st.markdown("---")
with st.expander("📖 MANUAL DE OPERACIÓN MAESTRA - AI.LINO"):
    st.write("""
    ### 1. Los 5 Cilindros del Motor
    * **Lynch (Valor):** Mide si la empresa está barata respecto a lo que gana. Si el precio es puro "aire", este cilindro te detiene.
    * **Dalio (Deuda):** Analiza la salud del chasis. Una empresa con mucha deuda es una trampa si la economía cae.
    * **Soros (Psicología):** Usa el RSI para detectar si la gente está loca comprando (Burbuja) o tiene miedo (Oportunidad).
    * **Simons (Matemática):** Mide qué tan fuerte se sacude la acción. Menos de 30% es estabilidad; más de 50% es un viaje salvaje.
    * **Turbo (Volumen):** Es la gasolina real. Si el **Turbo > 1.30x**, las instituciones están operando.

    ### 2. El Score y el Punto de Entrada
    | Rango | Señal |
    |---|---|
    | 78–100 | 🟢 Compra Fuerte |
    | 55–77  | 🟡 Compra Moderada / Mantener |
    | 0–54   | 🔴 Evitar |

    **Estrategia de Entrada:** No compres solo por el Score arriva de 78. El punto de menor riesgo es cuando el precio está cerca de la EMA 200 (línea roja). Analiza ambas partes. Score alto + precio tocando EMA 200 = operación perfecta.

    ### 3. Las EMAs
    * **EMA 50 (Dorada):** Si el precio está arriba de ella, la tendencia es alcista hoy.
    * **EMA 200 (Roja punteada):** Es el piso psicológico del mercado.
    * **Golden Cross:** Cuando la dorada cruza hacia arriba a la roja → señal de crecimiento.
    * **Death Cross:** Cuando la dorada cruza hacia abajo → señal de precaución.
    """)
