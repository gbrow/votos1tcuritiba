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

# 5. Aplicação dos Filtros nos Dados
df_filtrado = df[df['zona_eleitoral'].isin(zona_selecionada)]
df_filtrado = df_filtrado[df_filtrado['BAIRRO'].isin(bairro_selecionado)]

# 6. Aplicar lógica para proporção ou absoluto
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

# 7. Implementação da Escala Automática para Radius com Legenda Integrada
# Definir os intervalos (bins) para valor_exibido com verificação
num_bins = 5  # Número de categorias para a legenda

unique_vals = df_filtrado[valor_exibido].nunique()

if unique_vals > 1:
    bins = np.linspace(df_filtrado[valor_exibido].min(), df_filtrado[valor_exibido].max(), num_bins + 1)
    labels = [f"{round(bins[i],2)} - {round(bins[i+1],2)}" for i in range(num_bins)]
    try:
        df_filtrado['bin'] = pd.cut(df_filtrado[valor_exibido], bins=bins, labels=labels, include_lowest=True, duplicates='drop')
    except ValueError:
        # Caso ainda ocorram bins duplicados, definir manualmente
        df_filtrado['bin'] = 'Valor Único'
        labels = ['Valor Único']
else:
    # Todos os valores são iguais; criar um único bin
    bins = [df_filtrado[valor_exibido].min(), df_filtrado[valor_exibido].max()]
    labels = [f"{df_filtrado[valor_exibido].min()}"]
    df_filtrado['bin'] = pd.cut(df_filtrado[valor_exibido], bins=bins, labels=labels, include_lowest=True)

if unique_vals > 1:
    # Definir um mapeamento de bins para tamanhos de bolinhas
    radius_mapping = {
        label: size for label, size in zip(labels, np.linspace(150, 1100, len(labels)))
    }
    # Definir um mapeamento de bins para cores
    paleta_cores = [
        (0, 128, 255,220),      # Azul claro
        (0, 100, 200,220),
        (0, 80, 180,220),
        (0, 60, 160,220),
        (0, 40, 140,220)        # Azul escuro
    ]
    color_mapping = {
        label: cor for label, cor in zip(labels, paleta_cores)
    }
else:
    # Caso todos os valores sejam iguais, usar uma cor intermediária
    radius_mapping = {labels[0]: 650}  # Média entre 200 e 550
    paleta_cores = [
        (0, 128, 255,200)      # Azul claro
    ]
    color_mapping = {labels[0]: (0, 128, 255,220)}  # Azul intermediário

if isinstance(df_filtrado.index, pd.MultiIndex):
    df_filtrado = df_filtrado.reset_index()  # Remove MultiIndex do DataFrame.

df_filtrado['bin'] = df_filtrado['bin'].astype(str)

# Atribuir o tamanho da bolinha com base no bin
df_filtrado['radius'] = df_filtrado['bin'].map(radius_mapping)

# Atribuir a cor com base no bin
df_filtrado['color'] = df_filtrado['bin'].map(color_mapping)

# Verificar se há alguma cor não mapeada e atribuir cor padrão
if df_filtrado['color'].isnull().any():
    df_filtrado['color'] = df_filtrado['color'].apply(lambda x: (0, 128, 255) if pd.isnull(x) else x)

# 8. Funções para gerar legendas
def gerar_legenda_tamanho(radius_mapping_leg):
    legenda_html = "<div style='margin-top:10px;'>"
    legenda_html += "<h4>Legenda do Tamanho das Bolinhas</h4>"
    i = 0
    for label, size in radius_mapping_leg.items():
        legenda_html += f"""
        <div style="display: flex; align-items: center; margin-bottom:5px;">
            <div style="
                width: {size}px;
                height: {size}px;
                background-color: rgba({paleta_cores[i][0]}, {paleta_cores[i][1]}, {paleta_cores[i][2]}, 0.8);
                border: 1px solid #000;
                border-radius: 50%;
                margin-right: 10px;
            "></div>
            <div>{label}</div>
        </div>
        """
        i+=1
    legenda_html += "</div>"
    return legenda_html

def gerar_legenda_cores(color_mapping):
    legenda_html = "<div style='margin-top:10px;'>"
    legenda_html += "<h4>Legenda de Cores</h4>"
    for label, cor in color_mapping.items():
        legenda_html += f"""
        <div style="display: flex; align-items: center; margin-bottom:5px;">
            <div style="
                width: 20px;
                height: 20px;
                background-color: rgba({cor[0]}, {cor[1]}, {cor[2]}, 0.7);
                border: 1px solid #000;
                margin-right: 10px;
            "></div>
            <div>{label}</div>
        </div>
        """
    legenda_html += "</div>"
    return legenda_html

# Gerar a legenda de tamanho das bolinhas
if unique_vals > 1:
    radius_mapping_leg = {
        label: size for label, size in zip(labels, np.linspace(5, 30, len(labels)))
    }
else:
    radius_mapping_leg = {labels[0]: 15}  # Tamanho intermediário

legenda_tamanho = gerar_legenda_tamanho(radius_mapping_leg)

# Gerar a legenda de cores
legenda_cores = gerar_legenda_cores(color_mapping)

# 9. Criação dos Gráficos
def criar_graficos(df, valor_exibido, titulo_valor, modo_visualizacao):
    if modo_visualizacao == "Proporção (%)":
        # Agregar somatório por bairro e calcular a proporção
        df_agrupado = df.groupby('BAIRRO').agg({
            voto_selecionado: 'sum',
            'VOTOS APTOS': 'sum'
        }).reset_index()
        df_agrupado['Proporção (%)'] = (df_agrupado[voto_selecionado] / df_agrupado['VOTOS APTOS']) * 100
        grafico_barras = alt.Chart(df_agrupado).mark_bar().encode(
            x=alt.X('BAIRRO:N', title="Bairro"),
            y=alt.Y('Proporção (%)', title="Proporção (%)"),
            color=alt.Color('BAIRRO:N', legend=None),
            tooltip=['BAIRRO', 'Proporção (%)']
        ).properties(
            width=600,
            height=400,
            title='Proporção de Votos por Bairro'
        ).configure_axis(
            labelFontSize=12,
            titleFontSize=14
        ).configure_title(
            fontSize=16
        )
        
        grafico_pizza = px.pie(
            df_agrupado, 
            values='Proporção (%)', 
            names='BAIRRO', 
            title=f"Distribuição de Proporção (%) por Bairro",
            color_discrete_sequence=px.colors.qualitative.Pastel
        )
    else:
        # Agregar somatório por bairro
        df_agrupado = df.groupby('BAIRRO').agg({
            voto_selecionado: 'sum'
        }).reset_index()
        grafico_barras = alt.Chart(df_agrupado).mark_bar().encode(
            x=alt.X('BAIRRO:N', title="Bairro"),
            y=alt.Y(voto_selecionado, title=titulo_valor),
            color=alt.Color('BAIRRO:N', legend=None),
            tooltip=['BAIRRO', voto_selecionado]
        ).properties(
            width=600,
            height=400,
            title='Quantidade de Votos por Bairro'
        ).configure_axis(
            labelFontSize=12,
            titleFontSize=14
        ).configure_title(
            fontSize=16
        )
        
        grafico_pizza = px.pie(
            df_agrupado, 
            values=voto_selecionado, 
            names='BAIRRO', 
            title=f"Distribuição de {titulo_valor} por Bairro",
            color_discrete_sequence=px.colors.qualitative.Pastel
        )
    
    return grafico_barras, grafico_pizza

# Criar os gráficos de barra e pizza
grafico_barras, grafico_pizza = criar_graficos(df_filtrado, valor_exibido, titulo_valor, modo_visualizacao)

# 10. Adicionar Gráfico de Distribuição de Locais por Faixa de Valores
def criar_grafico_distribuicao(df, valor_exibido):
    # Definir as faixas (bins) e labels para distribuição
    distrib_bins = bins # [0, 10, 25, 50, 75, 100]  # Ajuste conforme necessário
    distrib_labels = labels #['0-10%', '10-25%', '25-50%', '50-75%', '75-100%']
    
    # Categorizar os dados
    df['faixa_distribuicao'] = pd.cut(
        df[valor_exibido], 
        bins=distrib_bins, 
        labels=distrib_labels, 
        include_lowest=True
    )
    
    # Contar o número de locais por faixa
    df_distribuicao = df['faixa_distribuicao'].value_counts().reset_index()
    df_distribuicao.columns = ['Faixa de Valores', 'Número de Locais']
    #df_distribuicao = df_distribuicao.sort_values(by='Faixa de Valores')
    
    # Criar o gráfico de barras
    grafico_distribuicao = alt.Chart(df_distribuicao).mark_bar().encode(
        x=alt.X('Faixa de Valores:O', title='Faixa de Valores'),
        y=alt.Y('Número de Locais:Q', title='Número de Locais'),
        color=alt.Color('Faixa de Valores:O', legend=None),
        tooltip=['Faixa de Valores', 'Número de Locais']
    ).properties(
        width=600,
        height=400,
        title='Distribuição de Locais de Votação por Faixa de Valores'
    ).configure_axis(
        labelFontSize=12,
        titleFontSize=14
    ).configure_title(
        fontSize=16
    )
    
    return grafico_distribuicao

# Criar o gráfico de distribuição
grafico_distribuicao = criar_grafico_distribuicao(df_filtrado, valor_exibido)

# 11. Verificar se há pontos disponíveis
if df_filtrado.empty:
    st.warning("Nenhum dado encontrado para os filtros selecionados.")
else:
    # 12. Organizar o Layout em Containers e Colunas
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
    
    # Container para Mapas e Legendas
    with st.container():
        col1, col2 = st.columns([3, 1])  # Mapa ocupa mais espaço que a legenda
        with col1:
            # 13. Criação do Mapa Interativo
            st.subheader("Mapa das Localidades de Votação")
            
            # Extrair coordenadas X e Y da geometria
            df_filtrado = df_filtrado.copy()  # Evita SettingWithCopyWarning
            df_filtrado['lon'] = df_filtrado.geometry.x
            df_filtrado['lat'] = df_filtrado.geometry.y
            
            # Definir a camada do mapa com cores dinâmicas
            layer = pdk.Layer(
                "ScatterplotLayer",
                data=df_filtrado,
                get_position='[lon, lat]',
                get_fill_color='color',
                get_line_color=[0, 0, 0],  # Bordas pretas
                get_line_width= 10,
                get_radius="radius",
                pickable=True,
                auto_highlight=True
            )
        
            # Definir o estilo do mapa base
            map_style = "light"  # Altere conforme desejado
            # Outros exemplos: "mapbox://styles/mapbox/dark-v10", "mapbox://styles/mapbox/streets-v11", "mapbox://styles/mapbox/satellite-streets-v11"
        
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
                map_style=map_style,  # Aplicar o estilo do mapa
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
                    background-color: rgba(0, 80, 180, 0.7);
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
        # Gráfico de Barras por Bairro
        st.subheader("Distribuição dos Votos por Bairro")
        st.altair_chart(grafico_barras, use_container_width=True)
        
        # Gráfico de Distribuição de Locais por Faixa de Valores
        st.subheader("Distribuição de Número de Locais de Votação por Faixa de Valores")
        st.altair_chart(grafico_distribuicao, use_container_width=True)
    
    # Container para Tabela Dinâmica
    with st.container():
        st.subheader(f"Dados das Localidades de Votação - {titulo_valor}")
        colunas_exibir = ['zona_eleitoral', 'local_votacao', valor_exibido, 'BAIRRO']
        st.dataframe(df_filtrado[colunas_exibir].reset_index(drop=True))
