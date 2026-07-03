import streamlit as st
import pandas as pd
import plotly.express as px
from supabase import create_client, Client
import os

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
    /* Estilizar la barra lateral (filtros) */
    [data-testid="stSidebar"] {
        background-color: #161824;
    }
    </style>
""", unsafe_allow_html=True)

# ----------------------------------------
# 2. CONEXIÓN A SUPABASE
# ----------------------------------------
@st.cache_resource
def init_connection():
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
    except:
        url = os.environ.get("SUPABASE_URL", "")
        key = os.environ.get("SUPABASE_KEY", "")
        
    if not url or not key:
        st.error("Faltan las credenciales de Supabase en Variables de Entorno.")
        st.stop()
    return create_client(url, key)

supabase = init_connection()

# ----------------------------------------
# 3. EXTRACCIÓN DE DATOS
# ----------------------------------------
@st.cache_data(ttl=600)
def load_data():
    # Productos
    res_prod = supabase.table("productos").select("*").execute()
    df_prod = pd.DataFrame(res_prod.data)
    
    # Mermas
    res_mermas = supabase.table("registros_mermas").select("*").execute()
    df_mermas = pd.DataFrame(res_mermas.data)
    
    # Niveles Inventario
    res_inv = supabase.table("niveles_inventario").select("*").execute()
    df_inv = pd.DataFrame(res_inv.data)
    
    # Cruces con Productos
    df_m = pd.DataFrame()
    df_i = pd.DataFrame()
    
    if not df_mermas.empty and not df_prod.empty:
        df_m = df_mermas.merge(df_prod[['id', 'nombre', 'categoria']], left_on='id_producto', right_on='id', how='left')
        
    if not df_inv.empty and not df_prod.empty:
        df_i = df_inv.merge(df_prod[['id', 'nombre', 'categoria']], left_on='id_producto', right_on='id', how='left')
        
    return df_m, df_i

with st.spinner("Cargando datos desde Supabase..."):
    df_mermas, df_inv = load_data()

# ----------------------------------------
# 4. FILTROS (BARRA LATERAL)
# ----------------------------------------
st.sidebar.image("https://upload.wikimedia.org/wikipedia/commons/thumb/c/ca/Metro_Per%C3%BA_logo.svg/512px-Metro_Per%C3%BA_logo.svg.png", width=150)
st.sidebar.title("🔍 Filtros")

# Filtro de Categoría
categorias = ["Todas"] + list(df_mermas['categoria'].dropna().unique())
cat_filtro = st.sidebar.selectbox("Filtro por Categoría", categorias)

# Aplicar filtros a los DataFrames
if cat_filtro != "Todas":
    mermas_filtrado = df_mermas[df_mermas['categoria'] == cat_filtro]
    inv_filtrado = df_inv[df_inv['categoria'] == cat_filtro]
else:
    mermas_filtrado = df_mermas.copy()
    inv_filtrado = df_inv.copy()

# Filtro extra para motivos de merma
motivos = ["Todos"] + list(mermas_filtrado['motivo'].dropna().unique())
motivo_filtro = st.sidebar.selectbox("Motivo de Merma", motivos)

if motivo_filtro != "Todos":
    mermas_filtrado = mermas_filtrado[mermas_filtrado['motivo'] == motivo_filtro]


# ----------------------------------------
# 5. DASHBOARD PRINCIPAL Y PESTAÑAS
# ----------------------------------------
st.title("🛒 Dashboard de Mermas e Inventario")
st.markdown("Sistema de Analítica de Big Data para la Mitigación de Mermas - **Supermercados Metro**")

if df_mermas.empty:
    st.warning("No hay datos disponibles.")
    st.stop()

# Crear Pestañas (Tabs) para separar Mermas de Stocks
tab1, tab2 = st.tabs(["📉 Análisis de Mermas", "📦 Verificación de Stock"])

# ===== PESTAÑA 1: MERMAS =====
with tab1:
    st.subheader(f"Indicadores de Mermas - {cat_filtro}")
    col1, col2, col3 = st.columns(3)
    
    costo_total = mermas_filtrado['costo_perdida'].sum()
    unidades_perdidas = mermas_filtrado['cantidad'].sum()
    if not mermas_filtrado.empty:
        top_prod = mermas_filtrado.groupby('nombre')['costo_perdida'].sum().idxmax()
    else:
        top_prod = "Ninguno"
    
    col1.metric("Costo de Mermas", f"${costo_total:,.2f}", delta="-Impacto Financiero", delta_color="inverse")
    col2.metric("Unidades Perdidas", f"{unidades_perdidas:,}")
    col3.metric("Producto más afectado", f"{top_prod}", delta="Pérdida Crítica", delta_color="inverse")
    
    st.divider()

    # Gráficos
    col_c1, col_c2 = st.columns(2)
    with col_c1:
        st.markdown("### 💸 Costo por Producto (Top 10)")
        if not mermas_filtrado.empty:
            costo_prod = mermas_filtrado.groupby('nombre')['costo_perdida'].sum().reset_index().sort_values(by='costo_perdida', ascending=False).head(10)
            fig1 = px.bar(costo_prod, x='nombre', y='costo_perdida', color='nombre', color_discrete_sequence=px.colors.sequential.Magma)
            fig1.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font_color="white", showlegend=False)
            st.plotly_chart(fig1, use_container_width=True)

    with col_c2:
        st.markdown("### ⚠️ Motivos")
        if not mermas_filtrado.empty:
            motivos_df = mermas_filtrado.groupby('motivo')['cantidad'].sum().reset_index()
            fig2 = px.pie(motivos_df, values='cantidad', names='motivo', hole=0.4, color_discrete_sequence=px.colors.sequential.RdBu)
            fig2.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font_color="white")
            st.plotly_chart(fig2, use_container_width=True)
            
    st.subheader("🔍 Tabla de Registros de Mermas")
    st.dataframe(mermas_filtrado[['fecha', 'nombre', 'categoria', 'motivo', 'cantidad', 'costo_perdida']].sort_values(by='fecha', ascending=False), use_container_width=True)


# ===== PESTAÑA 2: STOCKS =====
with tab2:
    st.subheader(f"Verificación de Stocks y Alertas - {cat_filtro}")
    st.markdown("Monitoreo del Nivel de Inventario contra el **Umbral Mínimo de Seguridad**.")
    
    if not inv_filtrado.empty:
        # Calcular Alerta
        inv_show = inv_filtrado[['nombre', 'categoria', 'stock_actual', 'umbral_minimo', 'fecha_actualizacion']].copy()
        inv_show['Estado'] = inv_show.apply(lambda row: '⚠️ PELIGRO (Bajo Umbral)' if row['stock_actual'] < row['umbral_minimo'] else '✅ OK', axis=1)
        
        # Resumen de alertas
        alertas_count = len(inv_show[inv_show['Estado'].str.contains('PELIGRO')])
        st.error(f"Se detectaron **{alertas_count}** productos por debajo de su umbral mínimo de seguridad en la categoría seleccionada.")
        
        # Gráfico comparativo
        st.markdown("### Comparativa: Stock Actual vs Umbral de Seguridad")
        fig3 = px.bar(inv_show.head(30), x='nombre', y=['stock_actual', 'umbral_minimo'], barmode='group',
                      color_discrete_map={'stock_actual': '#00d2ff', 'umbral_minimo': '#ff4b4b'})
        fig3.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font_color="white")
        st.plotly_chart(fig3, use_container_width=True)
        
        st.subheader("🔍 Tabla de Inventarios")
        st.dataframe(inv_show.sort_values(by='stock_actual'), use_container_width=True)
    else:
        st.info("No hay datos de inventario para esta selección.")
