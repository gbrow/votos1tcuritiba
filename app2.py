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
st.title("Dados de Votação para Prefeitura de Curitiba - Primeiro Turno")

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

# Filtro de Tipo de Voto (Quantidades e Candidatos)
opcoes_votos = [
    'VOTOS APTOS','ABSTENÇÕES','VOTOS NOMINAIS', 'VOTO BRANCO', 'VOTO NULO',
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

# Filtro por Zona Eleitoral
zonas = sorted(df['zona_eleitoral'].unique())
zona_selecionada = st.sidebar.multiselect(
    "Selecione a(s) Zona(s) Eleitoral(is):", options=zonas, default=zonas
)

# Filtro por Bairro
bairros = sorted(df['BAIRRO'].unique())
bairro_selecionado = st.sidebar.multiselect(
    "Selecione o(s) Bairro(s):", options=bairros, default=bairros
)

# Dicionário de cores por tipo de voto/candidato
cores_votos = {
    'VOTOS APTOS': [34, 139, 34],  # Verde
    'ABSTENÇÕES': [255, 0, 0],  # Vermelho
    'VOTOS NOMINAIS': [0, 0, 255],  # Azul
    'VOTO BRANCO': [220, 220, 220],  # Cinza claro
    'VOTO NULO': [128, 128, 128],  # Cinza
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
df_filtrado = df_filtrado[df_filtrado['BAIRRO'].isin(bairro_selecionado)]

# Aplicar lógica para proporção ou absoluto
if modo_visualizacao == "Proporção (%)":
    # Evitar divisão por zero
    valor_exibido = voto_selecionado + " (%)" 
    df_filtrado[valor_exibido] = np.where(
        df_filtrado['VOTOS APTOS'] > 0,
        round((df_filtrado[voto_selecionado] / df_filtrado['VOTOS APTOS']) * 100, 1),
        0
    )
    titulo_valor = "Proporção em Relação aos Votos Aptos"
    # Remover possíveis valores negativos ou NaN
    df_filtrado[valor_exibido] = df_filtrado[valor_exibido].fillna(0)
else:
    valor_exibido = voto_selecionado
    df_filtrado[valor_exibido] = df_filtrado[voto_selecionado].fillna(0)
    titulo_valor = "Quantidade de " + voto_selecionado

# 6. Implementação da Escala Automática para Radius com Legenda Integrada
def calcular_radius(series, min_radius=200, max_radius=550):
    min_val = series.min()
    max_val = series.max()
    if max_val == min_val:
        return [min_radius for _ in series]
    else:
        # Aplicar uma transformação logarítmica para melhor distribuição
        transformed = np.log1p(series)
        min_val = transformed.min()
        max_val = transformed.max()
        return 200 + (transformed - min_val) / (max_val - min_val) * (550 - 200)

# Definir os intervalos (bins) para valor_exibido
if (valor_exibido == 'VOTOS APTOS (%)'):
    num_bins = 1  # Número de categorias para a legenda
else:
    num_bins = 5  # Número de categorias para a legenda
bins = np.linspace(0.01, df_filtrado[valor_exibido].max(), num_bins + 1)
labels = [f"{round(bins[i],2)} - {round(bins[i+1],2)}" for i in range(num_bins)]
df_filtrado['bin'] = pd.cut(df_filtrado[valor_exibido], bins=bins, labels=labels, include_lowest=True)

# Definir um mapeamento de bins para tamanhos de bolinhas
radius_mapping = {
    label: size for label, size in zip(labels, np.linspace(150, 1100, num_bins))
}
radius_mapping_leg = {
    label: size for label, size in zip(labels, np.linspace(5, 30, num_bins))
}
# Atribuir o tamanho da bolinha com base no bin
df_filtrado['radius'] = df_filtrado['bin'].map(radius_mapping)

# Função para gerar a legenda de tamanho das bolinhas
def gerar_legenda_tamanho(radius_mapping):
    legenda_html = "<div style='margin-top:10px;'>"
    legenda_html += "<h4>Legenda do Tamanho das Bolinhas</h4>"
    for label, size in radius_mapping.items():
        legenda_html += f"""
        <div style="display: flex; align-items: center; margin-bottom:5px;">
            <div style="
                width: {size}px;
                height: {size}px;
                background-color: rgba(0, 128, 255, 0.7);
                border: 1px solid #000;
                border-radius: 50%;
                margin-right: 10px;
            "></div>
            <div>{label}</div>
        </div>
        """
    legenda_html += "</div>"
    return legenda_html

# Gerar a legenda de tamanho das bolinhas
legenda_tamanho = gerar_legenda_tamanho(radius_mapping_leg)

# 7. Criação dos Gráficos
def criar_graficos(df, valor_exibido, titulo_valor):
    # Gráfico de Barras
    grafico_barras = alt.Chart(df).mark_bar().encode(
        x=alt.X('BAIRRO:N', title="Bairro"),
        y=alt.Y(valor_exibido, title=titulo_valor),
        color=alt.Color('BAIRRO:N', legend=None),
        tooltip=['zona_eleitoral', 'local_votacao', 'BAIRRO', valor_exibido]
    ).properties(
        width=600,
        height=400
    ).configure_axis(
        labelFontSize=12,
        titleFontSize=14
    ).configure_title(
        fontSize=16
    )
    
    # Gráfico de Pizza
    grafico_pizza = px.pie(
        df, 
        values=valor_exibido, 
        names='BAIRRO', 
        title=f"Distribuição de {titulo_valor} por Bairro",
        color_discrete_sequence=px.colors.qualitative.Pastel
    )
    
    return grafico_barras, grafico_pizza

# Criar os gráficos
grafico_barras, grafico_pizza = criar_graficos(df_filtrado, valor_exibido, titulo_valor)

# 8. Verificar se há pontos disponíveis
if df_filtrado.empty:
    st.warning("Nenhum dado encontrado para os filtros selecionados.")
else:
    # 9. Organizar o Layout em Containers e Colunas
    st.header("Visualizações Interativas")
    
    # Container para Indicadores Principais
    with st.container():
        st.markdown("### Indicadores Principais")
        total_votos = df_filtrado[voto_selecionado].sum()
        total_aptos = df_filtrado['VOTOS APTOS'].sum()
        percentual_total = (total_votos / total_aptos * 100) if total_aptos > 0 else 0
        
        col1, col2, col3 = st.columns(3)
        
        col1.metric("Total de Votos", f"{total_votos}")
        if modo_visualizacao == "Proporção (%)":
            col2.metric("Proporção Total (%)", f"{percentual_total:.2f}%")
        col3.metric("Votos Aptos", f"{total_aptos}")
    
    # Container para Mapas e Tabelas
    with st.container():
        col1, col2 = st.columns([2, 1])  # Mapa ocupa mais espaço que a tabela
        with col1:
            # 10. Criação do Mapa Interativo
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
                    get_line_color=[0, 0, 0],  # Bordas pretas
                    line_width_min_pixels=1,
                    get_radius="radius",
                    pickable=True,
                    auto_highlight=True
                )
            
                # Configuração do estado inicial do mapa com zoom fixo
                if not df_filtrado.empty:
                    midpoint = (df_filtrado['lon'].mean(), df_filtrado['lat'].mean())
                else:
                    midpoint = (-49.2733, -25.4284)  # Coordenadas de Curitiba
            
                view_state = pdk.ViewState(
                    longitude=midpoint[0],
                    latitude=midpoint[1],
                    zoom=10,  # Zoom fixo para manter a proporcionalidade
                    pitch=0
                )
            
                # Renderização do mapa
                r = pdk.Deck(
                    layers=[layer],
                    initial_view_state=view_state,
                    tooltip={
                        "html": f"Zona: {{zona_eleitoral}}<br/>Local: {{local_votacao}}<br/>{titulo_valor}: {{{valor_exibido}}}",
                        "style": {"backgroundColor": "steelblue", "color": "white"}
                    }
                )
            
                st.pydeck_chart(r)
        
        with col2:
            st.markdown("### Legenda")
            # Legenda para o tipo de voto/candidato
            legenda_cor = f"""
            <div style="display: flex; align-items: center; margin-bottom:10px;">
                <div style="
                    width: 20px;
                    height: 20px;
                    background-color: rgba({cor_selecionada[0]}, {cor_selecionada[1]}, {cor_selecionada[2]}, 0.7);
                    border: 1px solid #000;
                    border-radius: 50%;
                    margin-right: 10px;
                "></div>
                <div>{voto_selecionado}</div>
            </div>
            """
            # Legenda para o tamanho das bolinhas
            st.markdown(legenda_cor + legenda_tamanho, unsafe_allow_html=True)
            
            # Nota sobre o zoom fixo
            st.markdown("""
                <div style="margin-top:10px; font-size:12px;">
                    <i>Nota: A legenda de tamanho das bolinhas é baseada no nível de zoom 11 do mapa.</i>
                </div>
            """, unsafe_allow_html=True)
            
    
    # Container para Gráficos
    with st.container():
    #    col1 = st.columns(1)
        
    #    with col1:
        st.subheader("Distribuição dos Votos por Bairro")
        st.altair_chart(grafico_barras, use_container_width=True)
        
        #with col2:
        #    st.subheader("Proporção dos Votos por Bairro")
        #    st.plotly_chart(grafico_pizza, use_container_width=True)
    
    # Container para Legenda
    with st.container():
    # 11. Tabela Dinâmica
        st.subheader(f"Dados das Localidades de Votação - {titulo_valor}")
        colunas_exibir = ['zona_eleitoral', 'local_votacao', valor_exibido, 'BAIRRO']
        st.dataframe(df_filtrado[colunas_exibir].reset_index(drop=True))
        
