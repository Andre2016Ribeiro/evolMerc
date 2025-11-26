"""
Dashboard de Trading em Tempo Real
Monitoriza commodities e pares forex com análise de tendência e inclinação
Requisitos: pip install dash plotly pandas numpy yfinance requests
"""

import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.graph_objs as go
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import yfinance as yf
import threading
import time

# Configuração dos ativos
ASSETS = {
    'GC=F': {'name': 'Ouro (Gold)', 'color': '#FFD700', 'unit': '$'},
    'SI=F': {'name': 'Prata (Silver)', 'color': '#C0C0C0', 'unit': '$'},
    'NG=F': {'name': 'Gás Natural', 'color': '#FF6B35', 'unit': '$'},
    'BZ=F': {'name': 'Brent', 'color': '#00B4D8', 'unit': '$'},
    '^GSPC': {'name': 'S&P 500', 'color': '#10B981', 'unit': ''},
    'EURUSD=X': {'name': 'EUR/USD', 'color': '#3B82F6', 'unit': ''},
    'USDJPY=X': {'name': 'USD/JPY', 'color': '#EC4899', 'unit': ''}
}

# Armazenamento global de dados
data_store = {}
last_update = None

def calculate_slope(prices):
    """Calcula a inclinação da tendência (regressão linear)"""
    if len(prices) < 2:
        return 0, 0
    
    x = np.arange(len(prices))
    y = np.array(prices)
    
    # Regressão linear
    coeffs = np.polyfit(x, y, 1)
    slope = coeffs[0]
    
    # Convertemos para ângulo (graus)
    angle = np.arctan(slope) * (180 / np.pi)
    
    return slope, angle

def get_trend_info(slope, angle):
    """Determina a tendência baseada no ângulo"""
    if angle > 15:
        return "📈 FORTE ALTA", "#10B981"
    elif angle > 5:
        return "↗️ ALTA MODERADA", "#34D399"
    elif angle > -5:
        return "➡️ LATERAL", "#FBBF24"
    elif angle > -15:
        return "↘️ BAIXA MODERADA", "#FB923C"
    else:
        return "📉 FORTE BAIXA", "#EF4444"

def fetch_asset_data(symbol, minutes=3):
    """Busca dados do ativo dos últimos X minutos"""
    try:
        # Busca dados intraday (1 minuto)
        ticker = yf.Ticker(symbol)
        end_time = datetime.now()
        start_time = end_time - timedelta(minutes=minutes)
        
        # YFinance usa intervalos de 1m, 2m, 5m, 15m, etc.
        df = ticker.history(start=start_time, end=end_time, interval='1m')
        
        if df.empty:
            return None
        
        prices = df['Close'].tolist()
        times = df.index.tolist()
        
        if len(prices) < 2:
            return None
        
        # Calcula métricas
        current_price = prices[-1]
        previous_price = prices[0]
        change = current_price - previous_price
        change_pct = (change / previous_price) * 100
        
        slope, angle = calculate_slope(prices)
        trend, trend_color = get_trend_info(slope, angle)
        
        return {
            'symbol': symbol,
            'prices': prices,
            'times': times,
            'current_price': current_price,
            'change': change,
            'change_pct': change_pct,
            'slope': slope,
            'angle': angle,
            'trend': trend,
            'trend_color': trend_color
        }
    except Exception as e:
        print(f"Erro ao buscar {symbol}: {e}")
        return None

def update_all_data():
    """Atualiza dados de todos os ativos"""
    global data_store, last_update
    
    while True:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Atualizando dados...")
        
        for symbol in ASSETS.keys():
            data = fetch_asset_data(symbol, minutes=3)
            if data:
                data_store[symbol] = data
        
        last_update = datetime.now()
        time.sleep(60)  # Atualiza a cada 60 segundos

# Inicializa Dash app
app = dash.Dash(__name__)
app.title = "Dashboard Trading Pro"

# Layout do Dashboard
app.layout = html.Div([
    # Header
    html.Div([
        html.H1("📊 Dashboard de Trading em Tempo Real", 
                style={'textAlign': 'center', 'color': '#FFD700', 'marginBottom': '10px'}),
        html.P("Monitorização de Commodities e Forex - Últimos 3 Minutos",
               style={'textAlign': 'center', 'color': '#9CA3AF', 'marginBottom': '5px'}),
        html.Div(id='last-update', 
                style={'textAlign': 'center', 'color': '#6B7280', 'fontSize': '14px'})
    ], style={'padding': '20px', 'backgroundColor': '#1F2937'}),
    
    # Cards de Ativos
    html.Div(id='asset-cards', style={'padding': '20px'}),
    
    # Gráficos
    html.Div([
        dcc.Graph(id='price-charts', style={'height': '600px'})
    ], style={'padding': '20px'}),
    
    # Intervalo de atualização
    dcc.Interval(
        id='interval-component',
        interval=10*1000,  # Atualiza a cada 10 segundos
        n_intervals=0
    ),
    
    # Aviso
    html.Div([
        html.Div([
            html.H3("⚠️ AVISO IMPORTANTE", style={'color': '#1F2937', 'marginBottom': '10px'}),
            html.P("Esta aplicação usa dados atrasados do Yahoo Finance. Para trading real, use APIs profissionais como Alpha Vantage, Twelve Data ou brokers diretos.",
                   style={'color': '#1F2937', 'fontSize': '14px'})
        ], style={'backgroundColor': '#FCD34D', 'padding': '15px', 'borderRadius': '8px'})
    ], style={'padding': '20px'})
    
], style={'backgroundColor': '#111827', 'minHeight': '100vh', 'fontFamily': 'Arial'})

@app.callback(
    [Output('asset-cards', 'children'),
     Output('price-charts', 'figure'),
     Output('last-update', 'children')],
    [Input('interval-component', 'n_intervals')]
)
def update_dashboard(n):
    """Atualiza todo o dashboard"""
    
    # Cards
    cards = []
    for symbol, asset_info in ASSETS.items():
        data = data_store.get(symbol)
        
        if data:
            card_color = '#10B981' if data['change'] >= 0 else '#EF4444'
            
            card = html.Div([
                html.Div([
                    html.H3(asset_info['name'], 
                           style={'color': 'white', 'marginBottom': '10px', 'fontSize': '18px'}),
                    html.Div([
                        html.Span(f"{asset_info['unit']}{data['current_price']:.2f}" if asset_info['unit'] == '$' else f"{data['current_price']:.5f}",
                                 style={'fontSize': '28px', 'fontWeight': 'bold', 'color': 'white'}),
                        html.Div([
                            html.Span(f"{'↑' if data['change'] >= 0 else '↓'} {abs(data['change']):.4f}",
                                     style={'color': card_color, 'fontSize': '16px', 'marginRight': '10px'}),
                            html.Span(f"({data['change_pct']:+.2f}%)",
                                     style={'color': card_color, 'fontSize': '16px'})
                        ], style={'marginTop': '5px'})
                    ]),
                    html.Hr(style={'borderColor': '#374151', 'margin': '15px 0'}),
                    html.Div([
                        html.Div([
                            html.Span("Tendência:", style={'color': '#9CA3AF', 'fontSize': '14px'}),
                            html.Span(data['trend'], 
                                     style={'color': data['trend_color'], 'fontSize': '14px', 'fontWeight': 'bold', 'marginLeft': '10px'})
                        ]),
                        html.Div([
                            html.Span("Inclinação:", style={'color': '#9CA3AF', 'fontSize': '14px'}),
                            html.Span(f"{data['angle']:.2f}°", 
                                     style={'color': 'white', 'fontSize': '14px', 'fontWeight': 'bold', 'marginLeft': '10px'})
                        ], style={'marginTop': '5px'})
                    ])
                ], style={
                    'backgroundColor': '#1F2937',
                    'padding': '20px',
                    'borderRadius': '10px',
                    'border': f'2px solid {asset_info["color"]}',
                    'boxShadow': '0 4px 6px rgba(0,0,0,0.3)'
                })
            ], style={'flex': '1', 'minWidth': '280px', 'margin': '10px'})
            
            cards.append(card)
    
    cards_container = html.Div(cards, style={
        'display': 'flex',
        'flexWrap': 'wrap',
        'justifyContent': 'space-around'
    })
    
    # Gráficos
    fig = go.Figure()
    
    for symbol, asset_info in ASSETS.items():
        data = data_store.get(symbol)
        if data:
            # Normaliza os preços para comparação visual
            prices = data['prices']
            normalized = [(p - min(prices)) / (max(prices) - min(prices)) * 100 if max(prices) != min(prices) else 50 for p in prices]
            
            times = [t.strftime('%H:%M:%S') for t in data['times']]
            
            fig.add_trace(go.Scatter(
                x=times,
                y=normalized,
                mode='lines+markers',
                name=asset_info['name'],
                line=dict(color=asset_info['color'], width=2),
                marker=dict(size=4)
            ))
    
    fig.update_layout(
        title="Evolução dos Preços (Normalizado 0-100)",
        xaxis_title="Tempo",
        yaxis_title="Preço Normalizado",
        hovermode='x unified',
        plot_bgcolor='#1F2937',
        paper_bgcolor='#1F2937',
        font=dict(color='white'),
        xaxis=dict(gridcolor='#374151'),
        yaxis=dict(gridcolor='#374151'),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    # Última atualização
    update_text = f"Última atualização: {last_update.strftime('%H:%M:%S')}" if last_update else "Aguardando dados..."
    
    return cards_container, fig, update_text

if __name__ == '__main__':
    print("=" * 60)
    print("🚀 Iniciando Dashboard de Trading em Tempo Real")
    print("=" * 60)
    print("\n📊 Ativos monitorados:")
    for symbol, info in ASSETS.items():
        print(f"  • {info['name']} ({symbol})")
    
    print("\n⏳ Carregando dados iniciais...")
    
    # Carrega dados iniciais
    for symbol in ASSETS.keys():
        data = fetch_asset_data(symbol, minutes=3)
        if data:
            data_store[symbol] = data
    last_update = datetime.now()
    
    print("✅ Dados carregados!")
    
    # Inicia thread de atualização em background
    update_thread = threading.Thread(target=update_all_data, daemon=True)
    update_thread.start()
    
    print("\n🌐 Abrindo dashboard em http://127.0.0.1:8050")
    print("💡 Pressione Ctrl+C para sair\n")
    print("=" * 60)
    
    # Inicia servidor
    app.run(debug=False, host='127.0.0.1', port=8050)