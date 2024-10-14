import streamlit as st
import pandas as pd
import geopandas as gpd
import pydeck as pdk
import altair as alt
import plotly.express as px
import numpy as np

# 1. Configuração da página
st.set_page_config(page_title="Painel de Votação - Curitiba", layout="wide")

# 2. Título do painel
st.title("Análise de Votação para Prefeitura de Curitiba - Primeiro Turno")

# 3. Carregamento dos dados
@st.cache_data
def load_data(votes_path, geojson_path):
    # Carregar dados de votação
    df_votes = pd.read_csv(votes_path, dtype={'zon_loc': str})
    
    # Separar 'zon_loc' em 'zona_eleitoral' e 'local_votacao'
    df_votes[['zona_eleitoral', 'local_votacao']] = df_votes['zon_loc'].str.split('_', expand=True)
    
    # Carregar dados geográficos
    gdf = gpd.read_file(geojson_path)
    gdf['zon_loc'] = gdf['zon_loc'].astype(str)
    
    # Unir dados de votação com geográficos
    df_merged = df_votes.merge(gdf, on='zon_loc')
    
    # Garantir que estamos lidando com um GeoDataFrame
    if not isinstance(df_merged, gpd.GeoDataFrame):
        df_merged = gpd.GeoDataFrame(df_merged, geometry='geometry')
    
    # Definir CRS para WGS 84 (EPSG:4326)
    df_merged = df_merged.set_crs("EPSG:4326", allow_override=True)
    
    return df_merged

# Caminhos dos arquivos
votes_csv = 'votos_cwb_pref1T_locvot.csv'
geojson_file = 'locais_votacao.geojson'

# Carregar os dados
df = load_data(votes_csv, geojson_file)

# 4. Filtros na Barra Lateral
st.sidebar.header("Filtros")

# Filtro por Zona Eleitoral
zonas = sorted(df['zona_eleitoral'].unique())
zona_selecionada = st.sidebar.multiselect(
    "Selecione a(s) Zona(s) Eleitoral(is):", options=zonas, default=zonas
)

# Filtro de Tipo de Voto (Quantidades e Candidatos)
opcoes_votos = [
    'VOTOS APTOS', 'ABSTENÇÕES', 'VOTOS NOMINAIS', 'VOTO BRANCO', 'VOTO NULO',
    'CRISTINA REIS GRAEML', 'EDUARDO PIMENTEL SLAVIERO', 'FELIPE GUSTAVO BOMBARDELLI',
    'LUCIANO DUCCI', 'LUIZ GOULARTE ALVES', 'MARIA VICTORIA BORGHETTI BARROS',
    'NEY LEPREVOST NETO', 'ROBERTO REQUIÃO DE MELLO E SILVA', 'SAMUEL DE MATTOS FIGUEIREDO'
]
voto_selecionado = st.sidebar.selectbox("Selecione o Tipo de Voto:", options=opcoes_votos)

# Novo seletor: Absoluto ou Proporção
modo_visualizacao = st.sidebar.radio(
    "Visualizar como:",
    options=["Números Absolutos", "Proporção (%)"]
)

# Dicionário de cores por tipo de voto/candidato
cores_votos = {
    'VOTOS APTOS': [34, 139, 34],  # Verde
    'ABSTENÇÕES': [255, 0, 0],  # Vermelho
    'VOTOS NOMINAIS': [0, 0, 255],  # Azul
    'VOTO BRANCO': [255, 255, 255],  # Branco
    'VOTO NULO': [100, 100, 100],  # Preto
    'CRISTINA REIS GRAEML': [128, 0, 128],  # Roxo
    'EDUARDO PIMENTEL SLAVIERO': [255, 165, 0],  # Laranja
    'FELIPE GUSTAVO BOMBARDELLI': [155, 50, 100],
    'LUCIANO DUCCI': [55, 65, 10], 
    'LUIZ GOULARTE ALVES': [255, 65, 200], 
    'MARIA VICTORIA BORGHETTI BARROS': [55, 5, 200],
    'NEY LEPREVOST NETO': [155, 15, 90], 
    'ROBERTO REQUIÃO DE MELLO E SILVA': [55, 120, 220], 
    'SAMUEL DE MATTOS FIGUEIREDO': [5, 165, 60]
    # Adicione cores para os demais candidatos...
}

# Obter a cor correspondente ao tipo de voto selecionado
cor_selecionada = cores_votos.get(voto_selecionado, [0, 128, 255])  # Default Azul

# 5. Aplicação dos Filtros nos Dados
df_filtrado = df[df['zona_eleitoral'].isin(zona_selecionada)]

# Aplicar lógica para proporção ou absoluto
if modo_visualizacao == "Proporção (%)":
    # Evitar divisão por zero
    df_filtrado['valor_exibido'] = np.where(
        df_filtrado['VOTOS APTOS'] > 0,
        (df_filtrado[voto_selecionado] / df_filtrado['VOTOS APTOS']) * 100,
        0
    )
    titulo_valor = "Proporção (%)"
else:
    df_filtrado['valor_exibido'] = df_filtrado[voto_selecionado]
    titulo_valor = "Quantidade de Votos"

# Remover possíveis valores negativos ou NaN
df_filtrado['valor_exibido'] = df_filtrado['valor_exibido'].fillna(0)

# 6. Implementação da Escala Automática para Radius
def calcular_radius(series, min_radius=5, max_radius=50):
    min_val = series.min()
    max_val = series.max()
    if max_val == min_val:
        return [min_radius for _ in series]
    else:
        # Escala linear
        return min_radius + (series - min_val) / (max_val - min_val) * (max_radius - min_radius)

# Calcular o radius automaticamente
df_filtrado['radius'] = calcular_radius(df_filtrado['valor_exibido'])

# 7. Criação dos Gráficos
# Gráfico de Barras
grafico_barras = alt.Chart(df_filtrado).mark_bar().encode(
    x=alt.X('zona_eleitoral:N', title="Zona Eleitoral"),
    y=alt.Y('valor_exibido', title=titulo_valor),
    color='zona_eleitoral:N',
    tooltip=['zona_eleitoral', 'local_votacao', 'valor_exibido']
).properties(
    width=600,
    height=400
)

# Gráfico de Pizza
grafico_pizza = px.pie(
    df_filtrado, 
    values='valor_exibido', 
    names='zona_eleitoral', 
    title=f"Distribuição de {voto_selecionado} por Zona Eleitoral",
    color_discrete_sequence=px.colors.qualitative.Pastel
)

# 8. Verificar se há pontos disponíveis
if df_filtrado.empty:
    st.warning("Nenhum dado encontrado para os filtros selecionados.")
else:
    # 9. Organizar o Layout em Colunas
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Distribuição dos Votos por Zona Eleitoral")
        st.altair_chart(grafico_barras, use_container_width=True)
    
    with col2:
        st.subheader("Gráfico de Pizza")
        st.plotly_chart(grafico_pizza, use_container_width=True)
    
    # 10. Adicionar a Legenda
    st.markdown("### Legenda")
    legend_html = f"""
    <div style="display: flex; align-items: center;">
        <div style="width: 20px; height: 20px; background-color: rgba({cor_selecionada[0]}, {cor_selecionada[1]}, {cor_selecionada[2]}, 0.7); border: 1px solid #000; margin-right: 10px;"></div>
        <div>{voto_selecionado}</div>
    </div>
    """
    st.markdown(legend_html, unsafe_allow_html=True)
    
    # 11. Criação do Mapa Interativo
    st.subheader("Mapa das Localidades de Votação")
    
    # Extrair coordenadas X e Y da geometria
    df_filtrado = df_filtrado.copy()  # Evita SettingWithCopyWarning
    df_filtrado['lon'] = df_filtrado.geometry.x
    df_filtrado['lat'] = df_filtrado.geometry.y
    
    # Garantir que a coluna selecionada existe e é numérica
    if voto_selecionado not in df_filtrado.columns:
        st.error(f"A coluna '{voto_selecionado}' não existe nos dados.")
    elif not pd.api.types.is_numeric_dtype(df_filtrado[voto_selecionado]):
        st.error(f"A coluna '{voto_selecionado}' não é numérica.")
    else:
        # Definir a camada do mapa
        layer = pdk.Layer(
            "ScatterplotLayer",
            data=df_filtrado,
            get_position='[lon, lat]',
            get_fill_color=cor_selecionada + [180],  # Adicionar transparência
            get_radius="radius",
            pickable=True,
            auto_highlight=True
        )
    
        # Configuração do estado inicial do mapa
        if not df_filtrado.empty:
            midpoint = (df_filtrado['lon'].mean(), df_filtrado['lat'].mean())
        else:
            midpoint = (-49.2733, -25.4284)  # Coordenadas de Curitiba
    
        view_state = pdk.ViewState(
            longitude=midpoint[0],
            latitude=midpoint[1],
            zoom=11,
            pitch=0
        )
    
        # Renderização do mapa
        r = pdk.Deck(
            layers=[layer],
            initial_view_state=view_state,
            tooltip={
                "html": f"Zona: {{zona_eleitoral}}<br/>Local: {{local_votacao}}<br/>{titulo_valor}: {{valor_exibido}}",
                "style": {"backgroundColor": "steelblue", "color": "white"}
            }
        )
    
        st.pydeck_chart(r)
    
    # 12. Tabela Dinâmica
    st.subheader(f"Dados das Localidades de Votação - {titulo_valor}")
    colunas_exibir = ['zon_loc', 'zona_eleitoral', 'local_votacao', 'valor_exibido']
    st.dataframe(df_filtrado[colunas_exibir].reset_index(drop=True))
