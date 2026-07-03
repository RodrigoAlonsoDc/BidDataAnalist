import streamlit as st
import pandas as pd
import plotly.express as px
from supabase import create_client, Client
import os
from streamlit_agraph import agraph, Node, Edge, Config
# ----------------------------------------
# 1. CONFIGURACIÓN DE LA PÁGINA
# ----------------------------------------
st.set_page_config(
    page_title="Dashboard Analítica - Supermercados Metro",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilo personalizado (Aesthetic CSS)
st.markdown("""
    <style>
    .main {
        background-color: #0f111a;
        color: #ffffff;
    }
    h1, h2, h3 {
        color: #00d2ff;
        font-family: 'Inter', sans-serif;
    }
    .stMetric {
        background-color: #1a1d2d;
        padding: 20px;
        border-radius: 10px;
        border: 1px solid #2d3142;
    }
    </style>
""", unsafe_allow_html=True)

# ----------------------------------------
# 2. CONEXIÓN A SUPABASE
# ----------------------------------------
# Render usará las variables de entorno que configures allí
@st.cache_resource
def init_connection():
    # Intenta buscar en st.secrets primero (si se usa Streamlit Cloud), sino usa variables de entorno
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
    except:
        url = os.environ.get("SUPABASE_URL", "")
        key = os.environ.get("SUPABASE_KEY", "")
        
    if not url or not key:
        st.error("Faltan las credenciales de Supabase. Configura SUPABASE_URL y SUPABASE_KEY en Render (Environment Variables).")
        st.stop()
    return create_client(url, key)

supabase = init_connection()

# ----------------------------------------
# 3. EXTRACCIÓN DE DATOS (ETL Básico)
# ----------------------------------------
@st.cache_data(ttl=600) # Se actualiza cada 10 minutos
def load_data():
    # Extraer Productos
    res_prod = supabase.table("productos").select("*").execute()
    df_prod = pd.DataFrame(res_prod.data)
    
    # Extraer Mermas
    res_mermas = supabase.table("registros_mermas").select("*").execute()
    df_mermas = pd.DataFrame(res_mermas.data)
    
    # Unir datos
    if not df_mermas.empty and not df_prod.empty:
        df_completo = df_mermas.merge(df_prod[['id', 'nombre', 'categoria', 'es_perecedero']], 
                                      left_on='id_producto', right_on='id', how='left')
        return df_completo
    return pd.DataFrame()

with st.spinner("Conectando a Data Warehouse (Supabase)..."):
    df = load_data()

# ----------------------------------------
# 4. INTERFAZ Y DASHBOARD
# ----------------------------------------
st.title("🛒 Dashboard de Mermas e Inventario")
st.markdown("Sistema de Analítica de Big Data para la Mitigación de Mermas - **Supermercados Metro**")

if df.empty:
    st.warning("No hay datos disponibles en la base de datos.")
else:
    # --- KPIs ---
    st.subheader("Indicadores Clave de Rendimiento (KPIs)")
    col1, col2, col3 = st.columns(3)
    
    costo_total = df['costo_perdida'].sum()
    unidades_perdidas = df['cantidad'].sum()
    top_categoria = df.groupby('categoria')['costo_perdida'].sum().idxmax()
    
    col1.metric("Costo Total de Mermas", f"${costo_total:,.2f}", delta="-Impacto Financiero", delta_color="inverse")
    col2.metric("Unidades Mermadas", f"{unidades_perdidas:,}", delta="Unidades perdidas en el año", delta_color="off")
    col3.metric("Categoría más crítica", f"{top_categoria}", delta="Mayor generador de pérdidas", delta_color="inverse")
    
    st.divider()

    # --- Gráficos Interactivos ---
    col_chart1, col_chart2 = st.columns(2)
    
    with col_chart1:
        st.markdown("### 💸 Costo de Mermas por Categoría")
        costo_cat = df.groupby('categoria')['costo_perdida'].sum().reset_index()
        fig1 = px.bar(costo_cat, x='categoria', y='costo_perdida', 
                      color='categoria', text_auto='.2s',
                      color_discrete_sequence=px.colors.sequential.Magma)
        fig1.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font_color="white")
        st.plotly_chart(fig1, use_container_width=True)

    with col_chart2:
        st.markdown("### ⚠️ Motivos Principales de Merma")
        motivos = df.groupby('motivo')['cantidad'].sum().reset_index()
        fig2 = px.pie(motivos, values='cantidad', names='motivo', 
                      hole=0.4, color_discrete_sequence=px.colors.sequential.RdBu)
        fig2.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font_color="white")
        st.plotly_chart(fig2, use_container_width=True)
        
    st.divider()
    
    # --- Tabla de Datos Crudos ---
    st.subheader("🔍 Explorador de Registros Crudos")
    st.dataframe(df[['fecha', 'nombre', 'categoria', 'motivo', 'cantidad', 'costo_perdida']].sort_values(by='fecha', ascending=False), use_container_width=True)

    st.divider()
    
    # --- Diagrama de Base de Datos Interactivo ---
    st.subheader("🗄️ Diagrama de Base de Datos Interactivo")
    st.markdown("Puedes arrastrar y mover las tablas (nodos) para ver cómo están conectadas mediante llaves foráneas.")
    
    nodes = [
        Node(id="TIENDAS", label="TIENDAS", size=30, shape="dot", color="#ff4b4b"),
        Node(id="PRODUCTOS", label="PRODUCTOS", size=30, shape="dot", color="#00d2ff"),
        Node(id="VENTAS_POS", label="VENTAS_POS", size=25, shape="dot", color="#808495"),
        Node(id="MOVIMIENTOS", label="MOVIMIENTOS_INVENTARIO", size=25, shape="dot", color="#808495"),
        Node(id="NIVELES", label="NIVELES_INVENTARIO", size=25, shape="dot", color="#808495"),
        Node(id="MERMAS", label="REGISTROS_MERMAS", size=25, shape="dot", color="#808495")
    ]
    
    edges = [
        Edge(source="TIENDAS", target="VENTAS_POS", label="1:N", color="#ffffff"),
        Edge(source="PRODUCTOS", target="VENTAS_POS", label="1:N", color="#ffffff"),
        Edge(source="TIENDAS", target="MOVIMIENTOS", label="1:N", color="#ffffff"),
        Edge(source="PRODUCTOS", target="MOVIMIENTOS", label="1:N", color="#ffffff"),
        Edge(source="TIENDAS", target="NIVELES", label="1:N", color="#ffffff"),
        Edge(source="PRODUCTOS", target="NIVELES", label="1:N", color="#ffffff"),
        Edge(source="TIENDAS", target="MERMAS", label="1:N", color="#ffffff"),
        Edge(source="PRODUCTOS", target="MERMAS", label="1:N", color="#ffffff")
    ]
    
    config = Config(width=1000, height=500, directed=True, physics=True, hierarchical=False)
    agraph(nodes=nodes, edges=edges, config=config)
