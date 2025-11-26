import streamlit as st
import pandas as pd
import yfinance as yf
import numpy as np
import pytz
from datetime import datetime, timedelta
from plotly.subplots import make_subplots
import plotly.graph_objects as go

st.set_page_config(layout="wide", page_title="Dashboard Trading Pro")

st.markdown("""
    <h1 style='text-align: center; color: #FFD700; margin-bottom: 5px;'>Dashboard de Trading em Tempo Real</h1>
    <p style='text-align: center; color: #9CA3AF; margin-bottom: 20px;'>
      Monitorização de Commodities e Índices • Últimos 5 Dias (Horário PT)
    </p>""", unsafe_allow_html=True)

ASSETS = {
    'GC=F':   {'name': 'Ouro (Gold)',      'color': '#FFD700', 'unit': '$', 'interval': '30m'},
    'SI=F':   {'name': 'Prata (Silver)',   'color': '#C0C0C0', 'unit': '$', 'interval': '30m'},
    'CL=F':   {'name': 'Petróleo (Crude)', 'color': '#00B4D8', 'unit': '$', 'interval': '30m'},
    '^GSPC':  {'name': 'S&P 500',          'color': '#10B981', 'unit': '',  'interval': '5m'},
    '^NDX':   {'name': 'NASDAQ 100',       'color': '#3B82F6', 'unit': '',  'interval': '5m'},
    '^DJI':   {'name': 'Dow Jones',        'color': '#EC4899', 'unit': '',  'interval': '5m'},
    '^GDAXI': {'name': 'DAX',              'color': '#F59E0B', 'unit': '',  'interval': '15m'}
}
timezone_pt = pytz.timezone("Europe/Lisbon")

def calculate_slope(prices):
    if len(prices) < 2: return 0.0, 0.0
    x = np.arange(len(prices))
    y = np.array(prices, dtype=float)
    coeffs = np.polyfit(x, y, 1)
    slope = coeffs[0]
    angle = np.arctan(slope) * (180 / np.pi)
    return slope, angle

def get_trend_info(angle):
    if angle > 15: return "FORTE ALTA", "#10B981"
    elif angle > 5: return "ALTA MODERADA", "#34D399"
    elif angle > -5: return "LATERAL", "#FBBF24"
    elif angle > -15: return "BAIXA MODERADA", "#FB923C"
    else: return "FORTE BAIXA", "#EF4444"

@st.cache_data(ttl=60, show_spinner="A carregar dados...")
def fetch_asset_data(symbol, info):
    end_time = datetime.now(timezone_pt)
    start_time = end_time - timedelta(days=5)
    df = yf.Ticker(symbol).history(start=start_time, end=end_time, interval=info['interval'])
    if df is None or df.empty: return None
    if df.index.tz is None: df.index = df.index.tz_localize('UTC')
    df.index = df.index.tz_convert(timezone_pt)
    closes = df['Close'].dropna()
    if closes.empty: return None
    prices = closes.tolist()
    times = closes.index.tolist()
    current_price = prices[-1]
    previous_price = prices[0]
    change = current_price - previous_price
    change_pct = (change / previous_price) * 100 if previous_price else 0.0
    slope, angle = calculate_slope(prices)
    trend, trend_color = get_trend_info(angle)
    return {'current_price': current_price, 'last_time': times[-1], 'change': change, 'change_pct': change_pct, 'trend': trend, 'trend_color': trend_color, 'angle': angle, 'prices': prices, 'times': times}

# Carrega os dados dos ativos
data_store = {}
for symbol, info in ASSETS.items():
    try:
        data = fetch_asset_data(symbol, info)
    except Exception as e:
        st.warning(f"Erro ao carregar {symbol}: {e}")
        data = None
    if data: data_store[symbol] = data

# Header (botão update)
col1, col2 = st.columns([1, 6])
with col1:
    if st.button("🔄 Atualizar Agora"):
        st.cache_data.clear()
        st.rerun()
with col2:
    now_pt = datetime.now(timezone_pt)
    st.markdown(f"<p style='text-align: right; color: #6B7280; font-size: 14px;'>Última atualização: {now_pt.strftime('%d/%m/%Y %H:%M:%S')} (PT)</p>", unsafe_allow_html=True)

# Cartões dos ativos
cards_html = "<div style='display: flex; flex-wrap: wrap; justify-content: space-around; gap: 15px; padding: 20px;'>"
for symbol, info in ASSETS.items():
    data = data_store.get(symbol)
    border_color = info['color']
    card_bg = '#1F2937'
    if not data:
        cards_html += f"""
        <div style='background: {card_bg}; padding: 20px; border-radius: 10px; border: 2px solid {border_color}; flex: 1; min-width: 260px; max-width: 300px; box-shadow: 0 4px 6px rgba(0,0,0,0.3);'>
            <h3 style='color: white; margin: 0 0 10px 0; font-size: 18px;'>{info['name']}</h3>
            <p style='color: #9CA3AF; font-size: 14px;'>Sem dados</p>
        </div>"""
        continue
    price_str = f"{info['unit']}{data['current_price']:.2f}" if info['unit'] else f"{data['current_price']:.2f}"
    hora_pt = data['last_time'].strftime("%d/%m %H:%M")
    change_sign = "↑" if data['change'] >= 0 else "↓"
    change_color = "#10B981" if data['change'] >= 0 else "#EF4444"
    cards_html += f"""
    <div style='background: {card_bg}; padding: 20px; border-radius: 10px; border: 2px solid {border_color}; box-shadow: 0 4px 6px rgba(0,0,0,0.3); flex: 1; min-width: 260px; max-width: 300px;'>
        <h3 style='color: white; margin: 0 0 8px 0; font-size: 18px;'>{info['name']}</h3>
        <div style='font-size: 28px; font-weight: bold; color: white; margin-bottom: 5px;'>{price_str}</div>
        <div style='font-size: 12px; color: #9CA3AF; margin-bottom: 10px;'>{hora_pt} (PT)</div>
        <div style='display: flex; justify-content: space-between; margin-bottom: 10px;'>
            <span style='color: {change_color}; font-size: 16px;'>{change_sign} {abs(data['change']):.4f}</span>
            <span style='color: {change_color}; font-size: 16px;'>({data['change_pct']:+.2f}%)</span>
        </div>
        <hr style='border-color: #374151; margin: 12px 0;'>
        <div style='font-size: 14px; color: #9CA3AF;'>Tendência: <span style='color: {data['trend_color']}; font-weight: bold;'>{data['trend']}</span></div>
        <div style='font-size: 14px; color: #9CA3AF; margin-top: 5px;'>Inclinação: <span style='color: white; font-weight: bold;'>{data['angle']:.1f}°</span></div>
    </div>"""
cards_html += "</div>"
st.markdown(cards_html, unsafe_allow_html=True)

# SUBPLOTS para cada ativo
from plotly.subplots import make_subplots
import plotly.graph_objects as go

# Seleciona apenas ativos com dados suficientes (>1 ponto e preço variável)
scripts = [s for s in ASSETS.keys() if s in data_store and len(data_store[s]['prices']) > 1 and min(data_store[s]['prices']) != max(data_store[s]['prices'])]

fig = make_subplots(
    rows=len(scripts), cols=1,
    shared_xaxes=False,  # cada subplot tem seu próprio eixo X
    vertical_spacing=0.06,
    subplot_titles=[ASSETS[s]['name'] for s in scripts]
)

for i, symbol in enumerate(scripts, 1):
    data = data_store[symbol]
    # Sempre formata datas para string legível
    times = [t.strftime('%d/%m %H:%M') for t in data['times']]
    prices = pd.Series(data['prices'], index=times)
    prices = prices.ffill().bfill()  # preenche buracos casuais
    normalized = (prices - prices.min()) / (prices.max() - prices.min()) * 100
    fig.add_trace(
        go.Scatter(
            x=prices.index,
            y=normalized,
            mode='lines+markers',
            name=ASSETS[symbol]['name'],
            line=dict(color=ASSETS[symbol]['color'], width=2),
            marker=dict(size=4),
            showlegend=False
        ),
        row=i, col=1
    )
    # Eixo Y: sempre percentagem de preço normalizado
    fig.update_yaxes(title_text="Preço Normalizado (%)", row=i, col=1, color=ASSETS[symbol]['color'], tickformat='.0f')
    # Eixo X: sempre datas legíveis e ângulo de 45º para melhor visualização
    fig.update_xaxes(title_text="Data/Hora (PT)", row=i, col=1, tickangle=45, tickfont=dict(color='white'))
fig.update_layout(
    title="Evolução dos Preços (Subplots por Ativo • Normalizado 0–100)",
    height=220 * max(len(scripts),1),
    plot_bgcolor='#1F2937', paper_bgcolor='#111827',
    font=dict(color='white', size=12),
    showlegend=False,
    margin=dict(l=50, r=50, t=70, b=40)
)
if scripts:
    st.plotly_chart(fig, width="stretch")
else:
    st.info("Gráfico: aguardando dados válidos...")



st.markdown("---")
st.markdown("""
    <div style='background-color: #FCD34D; padding: 15px; border-radius: 8px; text-align: center;'>
        <h3 style='color: #1F2937; margin: 0 0 10px 0;'>AVISO</h3>
        <p style='color: #1F2937; font-size: 14px; margin: 0;'>Dados do Yahoo Finance. Para trading real, use APIs profissionais.</p>
    </div>""", unsafe_allow_html=True)
st.caption("Atualização automática a cada 60s (via cache) • Hora PT em todos os cards")
