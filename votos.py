import dash
from dash import dcc, html
from dash import dash_table
from dash.dependencies import Input, Output
import pandas as pd
import dash_bootstrap_components as dbc

# Carregar o CSV em um DataFrame
df = pd.read_csv('votacao_secao-zona_2024_pr_curitiba.csv',delimiter=';', encoding='latin1')
df = df.drop(['aa_eleicao', 'cd_tipo_eleicao', 'nm_tipo_eleicao', 'cd_eleicao',
       'ds_eleicao', 'dt_eleicao', 'sg_uf', 'cd_municipio', 'nm_municipio',
       'nm_local_votacao', 'ds_local_votacao_endereco', 'nr_secao',
       'sq_candidato', 'dt_carga', 'ds_cargo'   ], axis=1)
df = df.groupby(['nr_zona', 'nr_local_votacao', 'nm_votavel'])[['qt_aptos', 'qt_abstencoes','qt_votos_nominais', 'qt_votos']].sum().reset_index()
df_agrupado = df.groupby(['nr_zona', 'nr_local_votacao', 'nm_votavel']).agg({
    'qt_votos': 'sum'     
}).reset_index()
df_agrupado['zon_loc'] =  df_agrupado['nr_zona'].astype(str).str.cat(df_agrupado['nr_local_votacao'].astype(str), sep='_')

df_agrupado2 = df.groupby(['nr_zona', 'nr_local_votacao' ]).agg({
    'qt_aptos': 'max',
    'qt_abstencoes': 'max',
    'qt_votos_nominais': 'max'     
}).reset_index()
df_agrupado2['zon_loc'] =  df_agrupado2['nr_zona'].astype(str).str.cat(df_agrupado2['nr_local_votacao'].astype(str), sep='_')
df_agrupado2 = df_agrupado2.drop(['nr_zona', 'nr_local_votacao'], axis=1)

df_pivot = df_agrupado.pivot_table(index=['nr_local_votacao', 'nr_zona','zon_loc'], columns='nm_votavel', values='qt_votos', aggfunc='sum', fill_value=0).reset_index()
df_junto = pd.merge(df_agrupado2, df_pivot, on='zon_loc', how='inner')

# Iniciar o aplicativo Dash
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

# Layout do aplicativo
app.layout = dbc.Container([
    html.H1("Tabela Dinâmica com Filtros"),
    
    # Dropdowns para filtros dinâmicos
    html.Div([
        dcc.Dropdown(
            id='nr_local_votacao',
            options=[{'label': str(i), 'value': i} for i in df_junto['nr_local_votacao'].unique()],
            multi=True,
            placeholder="Local"
        ),
        dcc.Dropdown(
            id='nr_zona',
            options=[{'label': i, 'value': i} for i in df_junto['nr_zona'].unique()],
            multi=True,
            placeholder="Zona"
        ),
        # Adicione mais dropdowns conforme necessário para outras colunas
    ], style={'display': 'flex', 'gap': '10px', 'margin-bottom': '20px', 'width':'100px'}),
    
    # Tabela interativa
    dash_table.DataTable(
        id='table',
        columns=[{"name": col, "id": col} for col in df_junto.columns],
        data=df_junto.to_dict('records'),
        filter_action="native",   # Permite filtragem nativa
        sort_action="native",     # Permite ordenação nativa
        page_size=10              # Define o número de linhas por página
    )
])

# Callbacks para atualizar a tabela com base nos filtros
@app.callback(
    Output('table', 'data'),
    Input('nr_local_votacao', 'value'),
    Input('nr_zona', 'value')
)
def update_table(nr_local_votacao, nr_zona):
    filtered_df = df_junto.copy()

    if nr_local_votacao:
        filtered_df = filtered_df[filtered_df['nr_local_votacao'].isin(nr_local_votacao)]
    if nr_zona:
        filtered_df = filtered_df[filtered_df['nr_zona'].isin(nr_zona)]
        
    return filtered_df.to_dict('records')

# Rodar o aplicativo
if __name__ == '__main__':
    app.run_server(debug=True)
