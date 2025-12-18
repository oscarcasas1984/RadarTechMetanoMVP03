import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

st.set_page_config(page_title="Methane Tech Explorer", layout="wide")

# =============== Definiciones ===============
REQUIRED_CATALOG_COLS = [
    "proveedor","producto_modelo","familia","tipo","principio","escala",
    "continuo","trl","trlc","segmento_negocio","tipo_emision","eje_monitoreo",
    "taxonomia","limite_deteccion_valor","limite_deteccion_unidad",
    "rango_deteccion_ppb_ppm","exactitud_incertidumbre","cobertura_espacial_temporal",
    "costo_capex_opex","casos_uso","condiciones_climaticas","condiciones_operativas"
]
REQUIRED_ADOP_COLS = ["empresa","region","tecnologias_reportadas","segmento_negocio","tipo_emision","fecha"]
REQUIRED_CONT_COLS = ["proveedor","producto_modelo","familia","region_principal","contacto_tipo","contacto_email","sitio_web"]

st.title("Monitor de Tecnología para Emisiones de Metano - 2025")
# === Resumen / Introducción (placeholder editable) ===
st.markdown("""
Reporte interactivo de tecnologías para monitoreo de emisiones de metano en distintos segmentos de la Industria de
los Hidrocarburos, según resolución, escala física, estrategia de monitoreo y madurez tecnológica.
>
""")
st.caption("Explora por Segmento × Emisión × Eje × Taxonomía, con Radar de evaluación. Catalogo Base de IA con 120 Tecnologías")

# =============== Carga de datos ===============
with st.sidebar:
    st.header("Datos de Entrada")
    st.markdown("Carga de Base de Datos de Monitoreo Tecnológico en formato Excel (.xlsx) con las hojas `Catalogo`, `Adopcion` y `Contactos`.")

    # DataFrames vacíos por defecto
    df_cat = pd.DataFrame(); df_adop = pd.DataFrame(); df_contacts = pd.DataFrame()

    # Normalización de columnas (sin cambios en la lógica original)
    def normalize_cols(df: pd.DataFrame) -> pd.DataFrame:
        df.columns = [str(c).strip().replace("  "," ").replace(" ","_").lower() for c in df.columns]
        # Harmonización de nombres (alias) desde Excel v3/v4
        alias_map = {
            "limite_deteccion": "limite_deteccion_valor",
            "lod": "limite_deteccion_valor",
            "plataforma_escala": "escala",   # v3/v4 usa plataforma_escala
            "plataforma": "escala"           # por si viene como 'plataforma'
        }
        return df.rename(columns=alias_map)

    # Único cargador de Excel
    up_xlsx = st.file_uploader("Cargar Monitoreo Tecnológico (.xlsx)", type=["xlsx"])
    if up_xlsx is not None:
        try:
            xl = pd.ExcelFile(up_xlsx)
            if "Catalogo" in xl.sheet_names:
                df_cat = pd.read_excel(up_xlsx, sheet_name="Catalogo")
            if "Adopcion" in xl.sheet_names:
                df_adop = pd.read_excel(up_xlsx, sheet_name="Adopcion")
            if "Contactos" in xl.sheet_names:
                df_contacts = pd.read_excel(up_xlsx, sheet_name="Contactos")
        except Exception as e:
            st.error(f"Error leyendo Excel: {e}")

    # Normalización posterior a lectura
    if not df_cat.empty: df_cat = normalize_cols(df_cat)
    if not df_adop.empty: df_adop = normalize_cols(df_adop)
    if not df_contacts.empty: df_contacts = normalize_cols(df_contacts)

    # Compatibilidad: si no hay 'escala' pero sí 'plataforma_escala', crear alias
    if not df_cat.empty and "escala" not in df_cat.columns and "plataforma_escala" in df_cat.columns:
        df_cat["escala"] = df_cat["plataforma_escala"]

    st.divider()
    st.subheader("Diccionario mínimo — Catálogo")
    st.code(", ".join(REQUIRED_CATALOG_COLS), language="text")

# =============== Validaciones ===============
def req_check(df, cols, title):
    if df.empty:
        return False, f"⚠️ No se cargó **{title}**."
    miss = [c for c in cols if c not in df.columns]
    if miss:
        return False, f"⚠️ Faltan columnas en **{title}**: {', '.join(miss)}"
    else:
        return True, f"✅ {title}: columnas mínimas OK."

cat_ok, cat_msg = req_check(df_cat, [*REQUIRED_CATALOG_COLS], "Catálogo") if not df_cat.empty else (False, "⚠️ No se cargó **Catálogo**.")
adp_ok, adp_msg = req_check(df_adop, [*REQUIRED_ADOP_COLS], "Adopción") if not df_adop.empty else (False, "⚠️ No se cargó **Adopción**.")
con_ok, con_msg = req_check(df_contacts, [*REQUIRED_CONT_COLS], "Contactos") if not df_contacts.empty else (False, "⚠️ No se cargó **Contactos**.")

validation_msgs = [cat_msg, adp_msg, con_msg]

if not cat_ok:
    st.info("Sube el **Catálogo** para comenzar.")
    st.stop()

# =============== Limpieza y campos numéricos ===============
def as_num(x):
    try: return float(str(x).replace(",", ".").replace(" ", ""))
    except: return np.nan

df_cat["trl_num"] = pd.to_numeric(df_cat.get("trl", np.nan), errors="coerce")
df_cat["lod_num"] = pd.to_numeric(df_cat.get("limite_deteccion_valor", np.nan), errors="coerce")

# Heurísticas rápidas para puntajes del Radar si no vienen en el Excel
if "exactitud_score" not in df_cat.columns:
    def map_exactitud(s):
        s = str(s).lower()
        if any(k in s for k in ["ppb","±0.0","muy alta","laboratorio"]): return 90
        if any(k in s for k in ["±","alta"]): return 75
        if any(k in s for k in ["media","screening"]): return 60
        return np.nan
    df_cat["exactitud_score"] = df_cat.get("exactitud_incertidumbre","").map(map_exactitud)

if "cobertura_score" not in df_cat.columns:
    def map_cobertura(s):
        s = str(s).lower()
        if any(k in s for k in ["regional","satélite","constelación"]): return 90
        if any(k in s for k in ["área","aéreo","uav","bloque"]): return 75
        if any(k in s for k in ["on-site","punto","planta"]): return 60
        return np.nan
    df_cat["cobertura_score"] = df_cat.get("cobertura_espacial_temporal","").map(map_cobertura)

if "costo_score" not in df_cat.columns:
    def map_costo(s):
        s = str(s).lower()
        if any(k in s for k in ["bajo","low","económico"]): return 90
        if any(k in s for k in ["medio","moderado"]): return 70
        if any(k in s for k in ["alto","suscripción","por vuelo","capex"]): return 50
        return np.nan
    df_cat["costo_score"] = df_cat.get("costo_capex_opex","").map(map_costo)

if "robustez_score" not in df_cat.columns:
    def map_robustez(row):
        clima = str(row.get("condiciones_climaticas","")).lower()
        op = str(row.get("condiciones_operativas","")).lower()
        score = 60
        if any(k in clima for k in ["amplio","rango","outdoor","hostil"]): score += 15
        if any(k in op for k in ["línea de vista","permiso","espacio aéreo","clasificada"]): score -= 10
        return max(30, min(95, score))
    df_cat["robustez_score"] = df_cat.apply(map_robustez, axis=1)

# =============== Filtros ===============
st.subheader("🎛️ Filtros")
c = st.columns(6)
seg_sel = c[0].multiselect("Segmento de negocio / área", sorted(df_cat["segmento_negocio"].dropna().unique()))
tipo_sel = c[1].multiselect("Tipo de emisión", sorted(df_cat["tipo_emision"].dropna().unique()))
eje_sel  = c[2].multiselect("Eje de monitoreo", sorted(df_cat["eje_monitoreo"].dropna().unique()))
tax_sel  = c[3].multiselect("Taxonomía", sorted(df_cat["taxonomia"].dropna().unique()))
trl_min  = c[4].number_input("TRL mín", 0, 9, 0)
trl_max  = c[5].number_input("TRL máx", 0, 9, 9)
query    = st.text_input("Búsqueda libre", placeholder="Proveedor, modelo, principio…")

def apply_filters(df):
    m = pd.Series(True, index=df.index)
    if seg_sel: m &= df["segmento_negocio"].isin(seg_sel)
    if tipo_sel: m &= df["tipo_emision"].isin(tipo_sel)
    if eje_sel:  m &= df["eje_monitoreo"].isin(eje_sel)
    if tax_sel:  m &= df["taxonomia"].isin(tax_sel)
    if "trl_num" in df.columns: m &= df["trl_num"].fillna(0).between(trl_min, trl_max)
    if query: m &= df.apply(lambda r: query.lower() in " ".join(map(str, r.values)).lower(), axis=1)
    return df[m]

df_cat_f = apply_filters(df_cat)

# =============== KPIs ===============
st.markdown("### 📌 KPIs")
k1,k2,k3,k4 = st.columns(4)
k1.metric("Tecnologías", len(df_cat_f))
k2.metric("Proveedores", df_cat_f["proveedor"].nunique() if not df_cat_f.empty else 0)
k3.metric("Promedio TRL", f"{df_cat_f['trl_num'].mean():.1f}" if "trl_num" in df_cat_f.columns and not df_cat_f.empty else "—")
k4.metric("% Continuo", f"{(df_cat_f.get('continuo','').astype(str).str.lower().isin(['sí','si','true','1']).mean()*100):.0f}%" if not df_cat_f.empty else "—")

# =============== Pestañas ===============
tabs = st.tabs([
    "🌐 Overview", "🗺️ Mapa de calor (Segmento × Emisión)", "🫧 TRL vs LOD",
    "🕸️ Radar de evaluación", "📚 Catálogo", "👥 Contactos", "⬇️ Exportar"
])

def _sanitize_hierarchy(df, path):
    # Remove rows with missing values in any of the path columns
    df_clean = df.dropna(subset=path)
    # Replace empty strings with 'Unknown' to avoid Plotly errors
    for col in path:
        df_clean[col] = df_clean[col].replace("", "Unknown")
    return df_clean

with tabs[0]:
    st.subheader("Sunburst y Treemap")
    if df_cat_f.empty:
        st.info("Ajusta filtros o verifica datos.")
    else:
        colA, colB = st.columns([1,1])
        # Saneamos y garantizamos hojas para evitar errores de Plotly
        df_sb = _sanitize_hierarchy(df_cat_f, ["segmento_negocio","tipo_emision","taxonomia"])
        df_sb["__leaf__"] = 1  # fuerza conteo explícito de hojas
        sb = px.sunburst(
            df_sb,
            path=["segmento_negocio","tipo_emision","taxonomia"],
            values="__leaf__",
            title="Segmento → Emisión → Taxonomía"
        )
        sb.update_layout(height=520, margin=dict(t=40,b=0,l=0,r=0))
        colA.plotly_chart(sb, use_container_width=True)

        if "familia" in df_cat_f.columns:
            df_tm = _sanitize_hierarchy(df_cat_f, ["taxonomia","familia","proveedor"])
            df_tm["__leaf__"] = 1
            tm = px.treemap(
                df_tm,
                path=["taxonomia","familia","proveedor"],
                values="__leaf__",
                title="Taxonomía → Familia → Proveedor"
            )
            tm.update_layout(height=520, margin=dict(t=40,b=0,l=0,r=0))
            colB.plotly_chart(tm, use_container_width=True)
        else:
            colB.info("Añade columna 'familia' para ver Treemap (Taxonomía → Familia → Proveedor).")

with tabs[1]:
    st.subheader("Mapa de calor (Segmento × Tipo de emisión)")
    if df_cat_f.empty:
        st.info("Sin datos tras filtros.")
    else:
        mat = (df_cat_f.groupby(["segmento_negocio","tipo_emision"])
               .size().reset_index(name="conteo"))
        fig = px.density_heatmap(mat, x="tipo_emision", y="segmento_negocio", z="conteo",
                                 color_continuous_scale="Blues", title="Disponibilidad de tecnologías")
        fig.update_layout(height=520)
        st.plotly_chart(fig, use_container_width=True)

with tabs[2]:
    st.subheader("TRL vs Límite de detección (LOD)")
    df_sc = df_cat_f.dropna(subset=["trl_num"])
    if df_sc.empty:
        st.info("No hay TRL numérico.")
    else:
        if "lod_num" not in df_sc.columns:
            df_sc["lod_num"] = pd.to_numeric(df_sc.get("limite_deteccion_valor", np.nan), errors="coerce")
        scatter = df_sc.dropna(subset=["lod_num"])
        if scatter.empty:
            st.info("No hay LOD numérico suficiente.")
        else:
            fig = px.scatter(scatter, x="trl_num", y="lod_num", color="tipo_emision",
                             hover_data=["proveedor","producto_modelo","taxonomia","eje_monitoreo"],
                             labels={"trl_num":"TRL","lod_num":"LOD (num)"})
            fig.update_layout(height=520)
            st.plotly_chart(fig, use_container_width=True)

with tabs[3]:
    st.subheader("Radar de evaluación (elige 2–5 tecnologías)")
    if df_cat_f.empty:
        st.info("Sin datos tras filtros.")
    else:
        df_cat_f["key"] = df_cat_f["proveedor"].fillna("") + " — " + df_cat_f["producto_modelo"].fillna("")
        choices = st.multiselect("Selecciona tecnologías", sorted(df_cat_f["key"].unique()))
        metrics = ["exactitud_score","cobertura_score","costo_score","robustez_score","trl_num"]
        labels_map = {"exactitud_score":"Exactitud","cobertura_score":"Cobertura","costo_score":"Costo (invertido)","robustez_score":"Robustez","trl_num":"TRL"}

        if 2 <= len(choices) <= 5:
            plot_df = []
            for k in choices:
                row = df_cat_f[df_cat_f["key"]==k].iloc[0].copy()
                vals = {
                    "exactitud_score": row.get("exactitud_score", np.nan),
                    "cobertura_score": row.get("cobertura_score", np.nan),
                    "costo_score": row.get("costo_score", np.nan),
                    "robustez_score": row.get("robustez_score", np.nan),
                    "trl_num": (row.get("trl_num", np.nan) or np.nan) * (100/9.0)
                }
                for m in metrics:
                    plot_df.append({"tec": k, "métrica": labels_map[m], "valor": vals[m]})

            pdf = pd.DataFrame(plot_df).dropna(subset=["valor"])
            if pdf.empty:
                st.info("No hay puntajes suficientes para el radar (agrega *_score en tu Excel si quieres control total).")
            else:
                fig = px.line_polar(pdf, r="valor", theta="métrica", color="tec", line_close=True, range_r=[0,100])
                fig.update_traces(fill='toself', opacity=0.5)
                fig.update_layout(height=620, legend_title_text="Tecnología")
                st.plotly_chart(fig, use_container_width=True)

                with st.expander("Ver tabla de puntajes"):
                    st.dataframe(pdf.pivot_table(index="tec", columns="métrica", values="valor"), use_container_width=True)
        else:
            st.info("Selecciona entre 2 y 5 tecnologías para comparar en el radar.")

with tabs[4]:
    st.subheader("Catálogo (filtrable)")
    st.dataframe(df_cat_f, use_container_width=True)

with tabs[5]:
    st.subheader("Contactos")
    if df_contacts.empty:
        st.info("No se cargaron contactos.")
    else:
        st.dataframe(df_contacts, use_container_width=True)

with tabs[6]:
    st.subheader("Exportar")
    st.download_button("Descargar catálogo filtrado (CSV)", data=df_cat_f.to_csv(index=False), file_name="catalogo_filtrado.csv")
    if not df_adop.empty:
        st.download_button("Descargar adopción (CSV)", data=df_adop.to_csv(index=False), file_name="adopcion.csv")
    if not df_contacts.empty:
        st.download_button("Descargar contactos (CSV)", data=df_contacts.to_csv(index=False), file_name="contactos.csv")

st.divider()
st.subheader("Validaciones de entrada")
for msg in validation_msgs:
    if msg:
        st.write(msg)

st.success("MVP02. Radar interactivo de IA para Metano en fase de prueba")
# === Pie de página ===
st.markdown("---", unsafe_allow_html=True)
st.markdown(
    "<div style='text-align: center; color: gray;'>© 2025 · Producto en prueba · Equipo Cambio Climático - Metano, 2025</div>",
    unsafe_allow_html=True
)