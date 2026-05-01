import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

st.set_page_config(
    page_title="Priorización Diabetes Jalisco",
    page_icon="🏥",
    layout="wide"
)

# ── CARGAR DATOS ──
@st.cache_data
def cargar_datos():
    df = pd.read_excel(
        'priorizacion_municipios_jalisco V28042026 (1).xlsx',
        sheet_name=0)
    df['dm2_contribuyente'] = df['dm2_cualquier'] - df['dm2_basica']
    df['pct_hombre'] = 100 - df['pct_mujer']
    return df

df_original = cargar_datos()

@st.cache_data
def cargar_clues():
    return pd.read_csv('clues_jalisco_activo.csv')

df_clues = cargar_clues()

# ── NORMALIZACIÓN ──
def norm(serie, invertir=False):
    mn, mx = serie.min(), serie.max()
    if mx == mn:
        return pd.Series(0.5, index=serie.index)
    n = (serie - mn) / (mx - mn)
    return 1 - n if invertir else n

def recalcular_indice(df, pesos):
    d = df.copy()
    d['d1'] = (
        norm(d['tasa_anual_dm2']) * (pesos['tasa']/100) +
        norm(d['avpp_total'])     * (pesos['avpp_t']/100)
    ) * (pesos['d1']/100)
    d['d2'] = (
        norm(d['avpp_prom']) * (pesos['avpp_p']/100)
    ) * (pesos['d2']/100)
    d['d3'] = (
        norm(d['pct_sin_escol'])                * (pesos['escol']/100) +
        norm(d['pct_sin_derecho'])              * (pesos['derecho']/100) +
        norm(d['enigh_ingreso'], invertir=True) * (pesos['ingreso']/100) +
        norm(d['enigh_vulnerabilidad'])         * (pesos['vuln']/100) +
        norm(d['enigh_internet'], invertir=True)* (pesos['internet']/100)
    ) * (pesos['d3']/100)
    d['tiene_2do'] = (d['segundo_nivel'] > 0).astype(float)
    d['d4'] = (
        norm(d['distancia_gdl_km'])              * (pesos['dist']/100) +
        norm(d['tiene_2do'], invertir=True)      * (pesos['sin2do']/100) +
        norm(d['unidades_x100k'], invertir=True) * (pesos['densidad']/100)
    ) * (pesos['d4']/100)
    d['d5'] = (
        norm(d['razon_erc_dm2'])           * (pesos['erc']/100) +
        norm(d['pct_dm2_contribuyente'])   * (pesos['contrib']/100)
    ) * (pesos['d5']/100)
    d['indice_calc'] = (d['d1'] + d['d2'] + d['d3'] + d['d4'] + d['d5']).round(4)
    d = d.sort_values('indice_calc', ascending=False).reset_index(drop=True)
    d['ranking_calc'] = d.index + 1
    return d

# ── SIDEBAR: PESOS ──
st.sidebar.image("logofunsalud.jpg", use_container_width=True)
st.sidebar.markdown("## ⚙️ Pesos del índice")
st.sidebar.markdown("---")

st.sidebar.markdown("**D1 — Carga de enfermedad**")
d1 = st.sidebar.slider("Peso D1 (%)", 0, 100, 35, 5)
tasa_w = st.sidebar.slider("→ Tasa cruda DM2", 0, 100, 60, 10)
avpp_t_w = st.sidebar.slider("→ AVPP total", 0, 100, 40, 10)

st.sidebar.markdown("**D2 — Prematuridad**")
d2 = st.sidebar.slider("Peso D2 (%)", 0, 100, 20, 5)
avpp_p_w = st.sidebar.slider("→ AVPP promedio", 0, 100, 100, 10)

st.sidebar.markdown("**D3 — Vulnerabilidad social**")
d3 = st.sidebar.slider("Peso D3 (%)", 0, 100, 20, 5)
escol_w   = st.sidebar.slider("→ % sin escolaridad", 0, 100, 30, 10)
derecho_w = st.sidebar.slider("→ % sin derecho", 0, 100, 30, 10)
ingreso_w = st.sidebar.slider("→ Ingreso (inv.)", 0, 100, 20, 10)
vuln_w    = st.sidebar.slider("→ Vulnerabilidad", 0, 100, 10, 10)
internet_w= st.sidebar.slider("→ Internet (inv.)", 0, 100, 10, 10)

st.sidebar.markdown("**D4 — Acceso a servicios**")
d4 = st.sidebar.slider("Peso D4 (%)", 0, 100, 20, 5)
dist_w    = st.sidebar.slider("→ Distancia GDL", 0, 100, 50, 10)
sin2do_w  = st.sidebar.slider("→ Sin 2do nivel", 0, 100, 30, 10)
densidad_w= st.sidebar.slider("→ Densidad (inv.)", 0, 100, 20, 10)

st.sidebar.markdown("**D5 — Complejidad trazador**")
d5 = st.sidebar.slider("Peso D5 (%)", 0, 100, 5, 5)
erc_w     = st.sidebar.slider("→ Razón ERC/DM2", 0, 100, 50, 10)
contrib_w = st.sidebar.slider("→ % Contribuyente", 0, 100, 50, 10)

# Validación dimensiones principales
total = d1 + d2 + d3 + d4 + d5
st.sidebar.markdown("---")
if total == 100:
    st.sidebar.success(f"✅ Total D1-D5: {total}%")
else:
    st.sidebar.error(f"❌ Total D1-D5: {total}% (debe ser 100%)")

# Validación pesos internos
tot_d1 = tasa_w + avpp_t_w
tot_d3 = escol_w + derecho_w + ingreso_w + vuln_w + internet_w
tot_d4 = dist_w + sin2do_w + densidad_w
tot_d5 = erc_w + contrib_w

errores = []
if tot_d1 != 100: errores.append(f"D1 suma {tot_d1}%")
if tot_d3 != 100: errores.append(f"D3 suma {tot_d3}%")
if tot_d4 != 100: errores.append(f"D4 suma {tot_d4}%")
if tot_d5 != 100: errores.append(f"D5 suma {tot_d5}%")

if errores:
    st.sidebar.error("❌ Pesos internos incorrectos:\n" + "\n".join(errores))
else:
    st.sidebar.success("✅ Pesos internos correctos")
pesos = dict(
    d1=d1, tasa=tasa_w, avpp_t=avpp_t_w,
    d2=d2, avpp_p=avpp_p_w,
    d3=d3, escol=escol_w, derecho=derecho_w,
    ingreso=ingreso_w, vuln=vuln_w, internet=internet_w,
    d4=d4, dist=dist_w, sin2do=sin2do_w, densidad=densidad_w,
    d5=d5, erc=erc_w, contrib=contrib_w
)

df = recalcular_indice(df_original, pesos)

# ── HEADER ──
st.markdown("""
<div style="background:linear-gradient(135deg,#1F4E79,#2E75B6);
            padding:20px;border-radius:10px;color:white;text-align:center;margin-bottom:20px">
    <h2 style="margin:0">🏥 Sistema de Priorización Municipal — Diabetes Jalisco</h2>
    <p style="margin:5px 0 0;opacity:0.9;font-size:13px">
        SSJ 2018-2025 (excl. 2020-2021) | INEGI | CONAPO | ENIGH 2016-2024 | CLUES 2026
    </p>
</div>
""", unsafe_allow_html=True)

# ── TABS ──
tab1, tab2 = st.tabs(["📊 Top 15 por Rango de Población", "🔍 Análisis por Municipio"])

# ════════════════════════════
# TAB 1 — TOP 10
# ════════════════════════════
with tab1:
    def rango_pob(p):
        if p <= 10000:   return '0 — 10,000'
        elif p <= 20000: return '10,001 — 20,000'
        elif p <= 30000: return '20,001 — 30,000'
        elif p <= 40000: return '30,001 — 40,000'
        else:            return 'Más de 40,000'
    df['rango'] = df['pob_2024'].apply(rango_pob)

    filtro_dist = st.radio(
        "Filtrar por distancia a Guadalajara:",
        ['Sin filtro', 'Menos de 150 km', 'Más de 150 km'],
        horizontal=True
    )
    col_filtro, col_orden = st.columns([3,2])
    with col_filtro:
        rango = st.radio(
            "Filtrar por rango de población:",
            ['Todos','0 — 10,000','10,001 — 20,000','20,001 — 30,000','30,001 — 40,000','Más de 40,000'],
            horizontal=True
        )
    with col_orden:
        ordenar_por = st.selectbox(
            "Ordenar Top 10 por:",
            options=['indice_calc','tasa_aj_general_2025','avpp_prom','pob_2024'],
            format_func=lambda x: {
                'indice_calc':         '📊 Índice de priorización',
                'tasa_aj_general_2025':'📈 Tasa ajustada SSJ',
                'avpp_prom':           '⏱️ AVPP promedio',
                'pob_2024':            '👥 Población'
            }[x]
        )

    if filtro_dist == 'Menos de 150 km':
        df_dist = df[df['distancia_gdl_km'] < 150]
    elif filtro_dist == 'Más de 150 km':
        df_dist = df[df['distancia_gdl_km'] >= 150]
    else:
        df_dist = df

    if rango == 'Todos':
        sub = df_dist.dropna(subset=['indice_calc'])
    else:
        sub = df_dist[df_dist['rango']==rango].dropna(subset=['indice_calc'])
    top = sub.nlargest(15, ordenar_por).reset_index(drop=True)

    # Tabla
    fig_t = go.Figure(data=[go.Table(
        columnwidth=[25,150,80,90,100,80,80],
        header=dict(
            values=['#','Municipio','Pob 2024','Muertes totales',
                    'Tasa ajustada SSJ*',
                    'AVPP prom','Índice'],
            fill_color='#1F4E79',
            font=dict(color='white',size=11,family='Calibri'),
            align='center', height=32),
        cells=dict(
            values=[
                list(range(1,len(top)+1)),
                top['municipio'],
                top['pob_2024'].apply(lambda x: f"{int(x):,}"),
                top['dm2_total_con_pandemia'].apply(lambda x: f"{int(x):,}"),
                top['tasa_aj_general_2025'].apply(lambda x: f"{x:.1f}"),
                top['avpp_prom'].apply(lambda x: f"{x:.1f}"),
                top['indice_calc'].apply(lambda x: f"{x:.4f}"),
            ],
            fill_color=[['#F0F7FF' if i%2==0 else 'white'
                         for i in range(len(top))]]*7,
            font=dict(size=11,family='Calibri'),
            align=['center','left']+['center']*5,
            height=26)
    )])
    fig_t.update_layout(margin=dict(l=0,r=0,t=10,b=0),height=330)
    st.plotly_chart(fig_t, use_container_width=True)
    st.caption("* Tasa ajustada por edad SSJ 2025, incluye todos los años 2018-2025")
    
    col1, col2 = st.columns(2)
    with col1:
        fig_m = go.Figure()
        fig_m.add_trace(go.Bar(name='1ª causa',x=top['municipio'],
            y=top['dm2_basica_pandemia'],marker_color='#1F4E79',
            text=top['dm2_basica_pandemia'].astype(int),textposition='inside',
            textfont=dict(color='white',size=9)))
        fig_m.add_trace(go.Bar(name='Contribuyente',x=top['municipio'],
            y=top['dm2_contrib_pandemia'],marker_color='#70AD47',
            text=top['dm2_contrib_pandemia'].astype(int),textposition='inside',
            textfont=dict(color='white',size=9)))
        fig_m.update_layout(barmode='stack',title='Muertes DM2: 1ª causa vs contribuyente (2018-2025)',
            xaxis_tickangle=-40,legend=dict(orientation='h',y=1.1),
            height=380,margin=dict(l=10,r=10,t=55,b=100),font=dict(family='Calibri'))
        st.plotly_chart(fig_m, use_container_width=True)

    with col2:
        fig_s = go.Figure()
        fig_s.add_trace(go.Bar(name='Hombres',x=top['municipio'],
            y=top['pct_hombre'],marker_color='#2E75B6',
            text=top['pct_hombre'].apply(lambda x:f"{x:.0f}%"),
            textposition='inside',textfont=dict(color='white',size=9)))
        fig_s.add_trace(go.Bar(name='Mujeres',x=top['municipio'],
            y=top['pct_mujer'],marker_color='#ED7D31',
            text=top['pct_mujer'].apply(lambda x:f"{x:.0f}%"),
            textposition='inside',textfont=dict(color='white',size=9)))
        fig_s.update_layout(barmode='stack',title='Distribución por sexo (%)',
            xaxis_tickangle=-40,legend=dict(orientation='h',y=1.1),
            height=380,margin=dict(l=10,r=10,t=55,b=100),font=dict(family='Calibri'))
        st.plotly_chart(fig_s, use_container_width=True)

    col3, col4 = st.columns(2)
    with col3:
        pj = df['avpp_prom'].mean()
        fig_a = go.Figure()
        fig_a.add_trace(go.Bar(x=top['municipio'],y=top['avpp_prom'],
            marker=dict(color=top['avpp_prom'],colorscale='Blues',showscale=False),
            text=top['avpp_prom'].apply(lambda x:f"{x:.1f}"),textposition='outside'))
        fig_a.add_hline(y=pj,line_dash='dash',line_color='red',
            annotation_text=f"Prom. Jalisco: {pj:.1f}",
            annotation_position='top right')
        fig_a.update_layout(title='AVPP promedio por persona',
            xaxis_tickangle=-40,showlegend=False,
            height=380,margin=dict(l=10,r=10,t=55,b=100),
            font=dict(family='Calibri'))
        st.plotly_chart(fig_a, use_container_width=True)

    with col4:
        cols_barra = ['#C00000' if i==0 else '#FF4040' if i<3
                      else '#ED7D31' if i<6 else '#FFC000'
                      for i in range(len(top))]
        fig_idx = go.Figure()
        fig_idx.add_trace(go.Bar(x=top['municipio'],y=top['indice_calc'],
            marker_color=cols_barra,
            text=top['indice_calc'].apply(lambda x:f"{x:.4f}"),
            textposition='outside'))
        fig_idx.update_layout(title='Índice de priorización (0-1)',
            xaxis_tickangle=-40,showlegend=False,
            yaxis=dict(range=[0,top['indice_calc'].max()*1.15]),
            height=380,margin=dict(l=10,r=10,t=55,b=100),
            font=dict(family='Calibri'))
        st.plotly_chart(fig_idx, use_container_width=True)

# ════════════════════════════
# TAB 2 — MUNICIPIO
# ════════════════════════════
with tab2:
    municipio = st.selectbox(
        "Seleccionar municipio:",
        sorted(df['municipio'].tolist())
    )

    row = df[df['municipio']==municipio].iloc[0]
    prom = df.mean(numeric_only=True)
    ranking = int(row['ranking_calc'])

    col_a, col_b, col_c, col_d, col_e, col_f = st.columns(6)
    col_a.metric("Clave", row['cve_mun'])
    col_b.metric("Población 2024", f"{int(row['pob_2024']):,}")
    col_c.metric("Ranking", f"#{ranking}")
    col_d.metric("Índice", f"{row['indice_calc']:.4f}")
    col_e.metric("Dist. GDL", f"{row['distancia_gdl_km']:.0f} km")
    col_f.metric("Muertes DM2", f"{int(row['dm2_cualquier']):,}")

    # Mapa
    lats = df['latitud'].tolist()
    lons = df['longitud'].tolist()
    sizes = [16 if m == municipio else 8 for m in df['municipio']]
    df_otros = df[df['municipio'] != municipio]
    df_sel   = df[df['municipio'] == municipio]

    fig_mapa = go.Figure()
    fig_mapa.add_trace(go.Scattermapbox(
        lat=df_otros['latitud'].tolist(),
        lon=df_otros['longitud'].tolist(),
        mode='markers',
        marker=dict(size=8,
            color=df_otros['indice_calc'],
            colorscale='RdYlGn_r',
            showscale=True,
            colorbar=dict(title='Índice')),
        text=df_otros['municipio'],
        customdata=df_otros[['indice_calc','tasa_anual_dm2','avpp_prom']].values,
        hovertemplate='<b>%{text}</b><br>Índice: %{customdata[0]:.4f}<br>Tasa: %{customdata[1]:.1f}<br>AVPP: %{customdata[2]:.1f}<extra></extra>',
        name='Municipios'
    ))
    fig_mapa.add_trace(go.Scattermapbox(
        lat=[df_sel.iloc[0]['latitud']],
        lon=[df_sel.iloc[0]['longitud']],
        mode='markers+text',
        marker=dict(size=22, color='#FF0000',),
        text=[municipio],
        textposition='top right',
        textfont=dict(size=13, color='#FF0000', family='Calibri'),
        hovertemplate=f'<b>{municipio}</b><br>Índice: {df_sel.iloc[0]["indice_calc"]:.4f}<extra></extra>',
        name=municipio
    ))
    fig_mapa.update_layout(
        mapbox=dict(style='carto-positron',
            center=dict(lat=20.6,lon=-103.5),zoom=6.5),
        height=420,margin=dict(l=0,r=0,t=0,b=0))
    st.plotly_chart(fig_mapa, use_container_width=True)

    # Radar
    dims = ['d1','d2','d3','d4','d5']
    nombres = ['Carga enfermedad','Prematuridad',
               'Vulnerabilidad','Acceso servicios','Trazador']
    vm = [row[d] for d in dims]
    vj = [prom[d] for d in dims]

    expandir = st.toggle("📂 Expandir todos los indicadores", value=False)
    col_r, col_cards = st.columns([1,1])
    with col_r:
        fig_r = go.Figure()
        fig_r.add_trace(go.Scatterpolar(
            r=vm+[vm[0]], theta=nombres+[nombres[0]],
            fill='toself', name=municipio,
            fillcolor='rgba(31,78,121,0.2)',
            line=dict(color='#1F4E79',width=2)))
        fig_r.add_trace(go.Scatterpolar(
            r=vj+[vj[0]], theta=nombres+[nombres[0]],
            fill='toself', name='Prom. Jalisco',
            fillcolor='rgba(112,173,71,0.15)',
            line=dict(color='#70AD47',width=2,dash='dash')))
        fig_r.update_layout(
            polar=dict(radialaxis=dict(visible=True)),
            height=380,legend=dict(orientation='h',y=-0.15),
            margin=dict(l=30,r=30,t=30,b=50),
            font=dict(family='Calibri'))
        st.plotly_chart(fig_r, use_container_width=True)

    
    with col_cards:
        EXPL = {
            'd1':('D1 — Carga de enfermedad','#1F4E79',
                  'Tasa de mortalidad y años de vida perdidos.',
                  [('Tasa cruda DM2','tasa_anual_dm2','{:.1f} x100k hab'),
                   ('AVPP total','avpp_total','{:.0f} años')]),
            'd2':('D2 — Prematuridad','#2E75B6',
                  'Qué tan joven muere la población por diabetes.',
                  [('AVPP promedio','avpp_prom','{:.1f} años/persona')]),
            'd3':('D3 — Vulnerabilidad social','#70AD47',
                  'Educación, seguridad social, ingreso y conectividad.',
                  [('% sin escolaridad','pct_sin_escol','{:.1f}%'),
                   ('% sin derechohabiencia','pct_sin_derecho','{:.1f}%'),
                   ('Ingreso hogar','enigh_ingreso','${:,.0f}'),
                   ('Vulnerabilidad ENIGH','enigh_vulnerabilidad','{:.2f}/5'),
                   ('% con internet','enigh_internet','{:.1f}%')]),
            'd4':('D4 — Acceso a servicios','#ED7D31',
                  'Distancia y disponibilidad de unidades de salud.',
                  [('Distancia a GDL','distancia_gdl_km','{:.0f} km'),
                   ('Unidades 2do nivel','segundo_nivel','{:.0f}'),
                   ('Densidad unidades','unidades_x100k','{:.1f} x100k')]),
            'd5':('D5 — Complejidad trazador','#7030A0',
                  'Progresión hacia complicaciones graves.',
                  [('Razón ERC/DM2','razon_erc_dm2','{:.2f}'),
                   ('% causa contribuyente','pct_dm2_contribuyente','{:.1f}%')])
        }

        for dk,(nombre,color,desc,variables) in EXPL.items():
            dv = row[dk]; dp = prom[dk]
            diff = dv - dp
            arrow = '▲' if diff > 0 else '▼'
            cdiff = 'red' if diff > 0 else 'green'
            with st.expander(f"{nombre} — Score: {dv:.4f}  {arrow} {abs(diff):.4f} vs Jalisco", expanded=expandir):
                st.caption(desc)
                for vn,vc,vf in variables:
                    if vc in row.index and pd.notna(row[vc]):
                        col_v1, col_v2, col_v3 = st.columns([2,1,1])
                        col_v1.write(vn)
                        col_v2.write(f"**{vf.format(row[vc])}**")
                        col_v3.caption(f"prom: {vf.format(prom[vc])}")
# Unidades de salud
    st.markdown("### 🏥 Unidades de Salud en el Municipio")
    clues_mun = df_clues[df_clues['municipio'].str.upper() == municipio.upper()][[
        'nombre_unidad','tipologia','clave_ins','nivel_atencion','tipo_establecimiento'
    ]].reset_index(drop=True)
    clues_mun.index += 1
    clues_mun.columns = ['Nombre unidad','Tipología','Institución','Nivel atención','Tipo']
    if len(clues_mun) > 0:
        st.dataframe(clues_mun, use_container_width=True, height=250)
        st.caption(f"Total: {len(clues_mun)} unidades en operación — Fuente: CLUES marzo 2026")
    else:
        st.info("No se encontraron unidades registradas para este municipio.")
        
    enigh = (f"{int(row['enigh_hogares'])} hogares en muestra"
             if pd.notna(row.get('enigh_hogares')) else "Sin cobertura municipal")
    st.caption(f"📋 ENIGH: {row.get('enigh_cobertura','n/d')} — {enigh}")

st.markdown("---")
st.caption("Fuentes: Base Mortalidad Jalisco SSJ 2018-2025 (excl. 2020-2021) | INEGI-DEFUN | CONAPO | ENIGH 2016-2024 | CLUES marzo 2026")
