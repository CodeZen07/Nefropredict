import pandas as pd
import sqlite3
import bcrypt
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from fpdf import FPDF
import io

# =============================================
# 1. CONFIGURACIÓN Y BASE DE DATOS
# =============================================
st.set_page_config(page_title="NefroCardio Pro SaaS", page_icon="⚖️", layout="wide")

class AppDatabase:
    def __init__(self):
        self.conn = sqlite3.connect("nefrocardio_v2026.db", check_same_thread=False)
        self.init_db()

    def init_db(self):
        c = self.conn.cursor()
        c.execute("""CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY, 
            password TEXT, 
            name TEXT, 
            role TEXT, 
            specialty TEXT,
            active INTEGER DEFAULT 1,
            created_date TEXT)""")
        
        c.execute("""CREATE TABLE IF NOT EXISTS clinical_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            px_name TEXT, 
            px_id TEXT, 
            date TEXT, 
            doctor TEXT,
            sys INT, 
            tfg REAL, 
            albuminuria REAL, 
            potasio REAL, 
            bun_cr REAL,
            fevi REAL, 
            troponina REAL, 
            bnp REAL, 
            ldl REAL, 
            sleep REAL, 
            stress TEXT, 
            exercise INT, 
            obs TEXT)""")
        
        c.execute("""CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            timestamp TEXT, 
            user TEXT, 
            action TEXT, 
            details TEXT)""")
        
        c.execute("SELECT * FROM users WHERE username='admin'")
        if not c.fetchone():
            pw = bcrypt.hashpw("Admin2026!".encode(), bcrypt.gensalt()).decode()
            c.execute("INSERT INTO users VALUES ('admin', ?, 'Admin Master', 'admin', 'Sistemas', 1, ?)", 
                     (pw, datetime.now().strftime("%Y-%m-%d")))
        self.conn.commit()

    def log_action(self, user, action, details):
        self.conn.execute("INSERT INTO audit_logs (timestamp, user, action, details) VALUES (?,?,?,?)",
                          (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), user, action, details))
        self.conn.commit()

db = AppDatabase()

# =============================================
# 2. MOTOR DE RECOMENDACIONES Y PDF
# =============================================
def generar_plan_cientifico(d):
    """
    Genera recomendaciones basadas en guías KDIGO 2024 y AHA/ACC 2023
    """
    recom = {"dieta": [], "estilo": [], "clinico": [], "seguimiento": []}
    alertas = []
    
    # Evaluación Renal (KDIGO 2024)
    tfg = d.get('tfg', 90)
    if tfg < 30:
        recom['clinico'].append("⚠️ ERC G4-G5: Derivar a nefrología. Considerar preparación para terapia de reemplazo renal.")
        alertas.append("CRÍTICO: TFG <30 ml/min")
    elif tfg < 60:
        recom['clinico'].append("ERC G3: Iniciar/optimizar IECA o ARA-II + SGLT2i (ej: empagliflozina 10mg/día) según KDIGO.")
        recom['seguimiento'].append("Control de TFG cada 3 meses")
    elif tfg < 90:
        recom['seguimiento'].append("Monitoreo anual de función renal")
    
    # Evaluación de Potasio
    potasio = d.get('potasio', 4.0)
    if potasio > 5.5:
        recom['dieta'].append("🔴 HIPERPOTASEMIA: Dieta estricta baja en K+ (<2g/día). Evitar: plátanos, naranjas, tomates, aguacate, frijoles.")
        recom['clinico'].append("Considerar quelante de potasio (patiromer o ciclosilicato de zirconio sódico)")
        alertas.append("URGENTE: K+ >5.5 mEq/L")
    elif potasio > 5.2:
        recom['dieta'].append("Restricción moderada de potasio. Limitar cítricos y vegetales crudos.")
    elif potasio < 3.5:
        recom['dieta'].append("Aumentar ingesta de potasio: plátanos, espinacas, batatas.")
        alertas.append("Hipopotasemia detectada")
    
    # Evaluación Cardíaca (AHA/ACC 2023)
    fevi = d.get('fevi', 55)
    if fevi < 40:
        recom['clinico'].append("🫀 IC-FEr: Terapia cuádruple GDMT: ARNI (sacubitrilo/valsartán) + betabloqueador + ARM + SGLT2i")
        recom['seguimiento'].append("Ecocardiograma cada 3-6 meses")
        alertas.append("Insuficiencia Cardíaca con FEr <40%")
    elif fevi < 50:
        recom['clinico'].append("FE limítrofe: Optimizar control de presión arterial y manejo de volumen")
        recom['seguimiento'].append("Ecocardiograma anual")
    
    # Presión Arterial
    sys = d.get('sys', 120)
    if sys >= 140:
        recom['clinico'].append("HTA: Meta <130/80 mmHg en ERC. IECA/ARA-II como primera línea.")
        recom['dieta'].append("Dieta DASH: <2g sodio/día, rica en frutas y vegetales (ajustar K+ si ERC avanzada)")
    elif sys < 100:
        alertas.append("Hipotensión: Revisar medicación antihipertensiva")
    
    # Estilo de Vida
    sleep = d.get('sleep', 7)
    if sleep < 6:
        recom['estilo'].append("⚠️ Sueño insuficiente (<6h): Aumenta riesgo CV 20-30%. Meta: 7-8 horas/noche.")
        recom['estilo'].append("Higiene del sueño: Horario regular, evitar pantallas 1h antes de dormir, ambiente oscuro.")
    elif sleep > 9:
        recom['estilo'].append("Sueño excesivo (>9h): Evaluar causas subyacentes (depresión, apnea del sueño)")
    
    # Manejo de Estrés
    stress = d.get('stress', 'Bajo')
    if stress == "Alto":
        recom['estilo'].append("Estrés elevado aumenta activación simpática y eje RAA. Técnicas recomendadas:")
        recom['estilo'].append("• Mindfulness/meditación 10-20 min/día (reduce PA sistólica 4-5 mmHg)")
        recom['estilo'].append("• Ejercicio aeróbico moderado 150 min/semana")
        recom['estilo'].append("• Considerar apoyo psicológico si persiste")
    
    # Ejercicio
    exercise = d.get('exercise', 0)
    if exercise < 150:
        recom['estilo'].append(f"Actividad física actual: {exercise} min/sem. Meta AHA: ≥150 min ejercicio moderado.")
        recom['estilo'].append("Iniciar gradualmente: Caminata 30 min 5 días/semana, aumentar progresivamente.")
    
    return recom, alertas

def crear_pdf(datos, recoms, alertas, medico):
    """
    Genera PDF profesional con datos clínicos y recomendaciones
    """
    pdf = FPDF()
    pdf.add_page()
    
    # Encabezado
    pdf.set_font("Arial", 'B', 18)
    pdf.set_text_color(0, 51, 102)
    pdf.cell(0, 12, "REPORTE MEDICO CARDIORRENAL", ln=True, align='C')
    pdf.set_text_color(0, 0, 0)
    pdf.ln(5)
    
    # Información del paciente
    pdf.set_font("Arial", 'B', 13)
    pdf.set_fill_color(230, 240, 250)
    pdf.cell(0, 10, "DATOS DEL PACIENTE", ln=True, fill=True)
    pdf.set_font("Arial", '', 11)
    pdf.cell(95, 8, f"Nombre: {datos['px_name']}", border=1)
    pdf.cell(95, 8, f"ID: {datos['px_id']}", border=1, ln=True)
    pdf.cell(95, 8, f"Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}", border=1)
    pdf.cell(95, 8, f"Medico: Dr. {medico}", border=1, ln=True)
    pdf.ln(8)
    
    # Resultados clínicos
    pdf.set_font("Arial", 'B', 13)
    pdf.set_fill_color(230, 240, 250)
    pdf.cell(0, 10, "RESULTADOS CLINICOS", ln=True, fill=True)
    pdf.set_font("Arial", '', 11)
    
    resultados = [
        ("Presion Sistolica", f"{datos.get('sys', 'N/A')} mmHg"),
        ("TFG (Funcion Renal)", f"{datos.get('tfg', 'N/A')} ml/min/1.73m2"),
        ("Potasio (K+)", f"{datos.get('potasio', 'N/A')} mEq/L"),
        ("FEVI (Fraccion Eyeccion)", f"{datos.get('fevi', 'N/A')}%"),
        ("Horas de Sueno", f"{datos.get('sleep', 'N/A')} horas/dia"),
        ("Nivel de Estres", datos.get('stress', 'N/A'))
    ]
    
    for label, valor in resultados:
        pdf.cell(95, 7, label, border=1)
        pdf.cell(95, 7, valor, border=1, ln=True)
    pdf.ln(5)
    
    # Alertas críticas
    if alertas:
        pdf.set_font("Arial", 'B', 12)
        pdf.set_text_color(220, 20, 60)
        pdf.cell(0, 8, "ALERTAS CLINICAS", ln=True)
        pdf.set_text_color(0, 0, 0)
        pdf.set_font("Arial", '', 10)
        for alerta in alertas:
            pdf.multi_cell(0, 6, f"* {alerta}")
        pdf.ln(3)
    
    # Recomendaciones
    pdf.set_font("Arial", 'B', 13)
    pdf.set_fill_color(230, 240, 250)
    pdf.cell(0, 10, "PLAN DE TRATAMIENTO Y RECOMENDACIONES", ln=True, fill=True)
    pdf.ln(2)
    
    categorias = {
        'clinico': ('MANEJO CLINICO', (0, 100, 0)),
        'dieta': ('INTERVENCION NUTRICIONAL', (139, 69, 19)),
        'estilo': ('MODIFICACION DE ESTILO DE VIDA', (0, 51, 102)),
        'seguimiento': ('PLAN DE SEGUIMIENTO', (75, 0, 130))
    }
    
    for cat, items in recoms.items():
        if items:
            titulo, color = categorias.get(cat, (cat.upper(), (0, 0, 0)))
            pdf.set_font("Arial", 'B', 11)
            pdf.set_text_color(*color)
            pdf.cell(0, 8, titulo, ln=True)
            pdf.set_text_color(0, 0, 0)
            pdf.set_font("Arial", '', 10)
            for item in items:
                pdf.multi_cell(0, 6, f"  * {item}")
            pdf.ln(3)
    
    # Disclaimer
    pdf.ln(5)
    pdf.set_font("Arial", 'I', 9)
    pdf.set_text_color(128, 128, 128)
    pdf.multi_cell(0, 5, "AVISO LEGAL: Este reporte es una herramienta de apoyo clinico basada en guias KDIGO 2024 y AHA/ACC 2023. No sustituye el juicio clinico profesional ni la evaluacion individualizada del paciente. Todas las decisiones terapeuticas deben ser validadas por el medico tratante considerando el contexto clinico completo del paciente.")
    
    # Firma
    pdf.ln(8)
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", '', 10)
    pdf.cell(0, 6, "_" * 40, ln=True, align='C')
    pdf.cell(0, 6, f"Dr. {medico}", ln=True, align='C')
    pdf.cell(0, 6, "Firma y Sello Profesional", ln=True, align='C')
    
    return pdf.output(dest='S').encode('latin-1')

# =============================================
# 3. INTERFAZ DE USUARIO
# =============================================
if "auth" not in st.session_state: 
    st.session_state.auth = False
if "analisis_listo" not in st.session_state: 
    st.session_state.analisis_listo = False

# LOGIN
if not st.session_state.auth:
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.markdown("# 🏥 NefroCardio Pro SaaS")
        st.markdown("### Sistema Integrado de Evaluación Cardiorrenal")
        st.divider()
        u = st.text_input("👤 Usuario", placeholder="admin")
        p = st.text_input("🔒 Contraseña", type="password", placeholder="Admin2026!")
        
        if st.button("🚀 Acceder", use_container_width=True, type="primary"):
            res = db.conn.execute("SELECT password, name, role FROM users WHERE username=? AND active=1", (u,)).fetchone()
            if res and bcrypt.checkpw(p.encode(), res[0].encode()):
                st.session_state.update({"auth":True, "name":res[1], "role":res[2], "username":u})
                db.log_action(u, "Login", "Acceso exitoso al sistema")
                st.success("✅ Autenticación exitosa")
                st.rerun()
            else: 
                st.error("❌ Credenciales inválidas o usuario inactivo")
                db.log_action(u or "Desconocido", "Login Fallido", "Intento de acceso denegado")
        
        st.info("💡 **Usuario demo:** admin | **Contraseña:** Admin2026!")
    st.stop()

# SIDEBAR
st.sidebar.markdown(f"### 👨‍⚕️ Dr. {st.session_state.name}")
st.sidebar.markdown(f"**Rol:** {st.session_state.role.capitalize()}")
st.sidebar.divider()
menu = st.sidebar.radio("📋 Menú Principal", ["🔬 Nueva Consulta", "📂 Historial", "⚙️ Panel Admin"], label_visibility="collapsed")

if st.sidebar.button("🚪 Cerrar Sesión", use_container_width=True):
    db.log_action(st.session_state.username, "Logout", "Sesión cerrada")
    st.session_state.clear()
    st.rerun()

# =============================================
# SECCIÓN: NUEVA CONSULTA
# =============================================
if menu == "🔬 Nueva Consulta":
    st.title("🔬 Evaluación Cardiorrenal Integral")
    st.info("⚕️ **Sistema de apoyo clínico basado en guías KDIGO 2024 y AHA/ACC 2023**")
    
    with st.form("consulta_form"):
        st.subheader("📋 Datos del Paciente")
        c1, c2, c3 = st.columns(3)
        px_name = c1.text_input("Nombre Completo *", placeholder="Juan Pérez")
        px_id = c2.text_input("Cédula/ID *", placeholder="001-0000000-0")
        fecha_actual = c3.date_input("Fecha Consulta", datetime.now())
        
        st.divider()
        st.subheader("🩺 Parámetros Clínicos")
        
        col1, col2, col3, col4 = st.columns(4)
        sys_p = col1.number_input("Presión Sistólica (mmHg)", 80, 220, 120, help="Presión arterial sistólica")
        tfg_v = col2.number_input("TFG (ml/min/1.73m²)", 0.0, 150.0, 90.0, help="Tasa de Filtración Glomerular")
        pot_v = col3.number_input("Potasio K+ (mEq/L)", 2.0, 8.0, 4.0, step=0.1, help="Nivel sérico de potasio")
        fevi_v = col4.number_input("FEVI (%)", 5.0, 80.0, 55.0, help="Fracción de Eyección Ventricular Izquierda")
        
        st.divider()
        st.subheader("🏃 Estilo de Vida")
        
        col_a, col_b, col_c = st.columns(3)
        sleep_v = col_a.slider("Horas de Sueño/día", 3.0, 12.0, 7.0, 0.5)
        stress_v = col_b.selectbox("Nivel de Estrés", ["Bajo", "Moderado", "Alto"])
        exercise_v = col_c.number_input("Ejercicio (min/semana)", 0, 500, 150, step=10)
        
        st.divider()
        obs_v = st.text_area("📝 Observaciones Clínicas", placeholder="Notas adicionales sobre el paciente...")
        
        submitted = st.form_submit_button("🔍 ANALIZAR Y GUARDAR", use_container_width=True, type="primary")

    if submitted and px_name and px_id:
        datos_enviados = {
            "px_name": px_name, 
            "px_id": px_id, 
            "tfg": tfg_v, 
            "potasio": pot_v, 
            "fevi": fevi_v, 
            "sleep": sleep_v, 
            "stress": stress_v, 
            "sys": sys_p,
            "exercise": exercise_v
        }
        
        recoms, alertas = generar_plan_cientifico(datos_enviados)
        st.session_state.recoms = recoms
        st.session_state.alertas = alertas
        st.session_state.datos_recientes = datos_enviados
        st.session_state.analisis_listo = True
        
        # Guardar en base de datos
        db.conn.execute("""INSERT INTO clinical_records 
            (px_name, px_id, date, doctor, sys, tfg, potasio, fevi, sleep, stress, exercise, obs) 
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (px_name, px_id, fecha_actual.strftime("%Y-%m-%d"), st.session_state.name, 
             sys_p, tfg_v, pot_v, fevi_v, sleep_v, stress_v, exercise_v, obs_v))
        db.conn.commit()
        db.log_action(st.session_state.username, "Consulta Creada", f"Paciente: {px_name} ({px_id})")
        st.success("✅ Análisis completado y guardado exitosamente")
        st.rerun()

    # MOSTRAR RESULTADOS
    if st.session_state.analisis_listo:
        d = st.session_state.datos_recientes
        r = st.session_state.recoms
        alertas = st.session_state.get('alertas', [])
        
        st.divider()
        st.header("📊 Resultados del Análisis")
        
        # Alertas críticas
        if alertas:
            st.error("### ⚠️ ALERTAS CLÍNICAS DETECTADAS")
            for alerta in alertas:
                st.warning(f"🔴 {alerta}")
            st.divider()
        
        # Gráficos principales
        col_g1, col_g2 = st.columns(2)
        
        with col_g1:
            # Gauge de TFG
            fig_tfg = go.Figure(go.Indicator(
                mode="gauge+number+delta",
                value=d['tfg'],
                title={'text': "Función Renal (TFG)<br><span style='font-size:0.8em'>ml/min/1.73m²</span>", 'font': {'size': 20}},
                delta={'reference': 90, 'increasing': {'color': "green"}},
                gauge={
                    'axis': {'range': [None, 120], 'tickwidth': 1},
                    'bar': {'color': "darkblue"},
                    'bgcolor': "white",
                    'steps': [
                        {'range': [0, 15], 'color': "#8B0000", 'name': 'G5'},
                        {'range': [15, 30], 'color': "#FF4500", 'name': 'G4'},
                        {'range': [30, 45], 'color': "#FFA500", 'name': 'G3b'},
                        {'range': [45, 60], 'color': "#FFD700", 'name': 'G3a'},
                        {'range': [60, 90], 'color': "#90EE90", 'name': 'G2'},
                        {'range': [90, 120], 'color': "#32CD32", 'name': 'G1'}
                    ],
                    'threshold': {
                        'line': {'color': "red", 'width': 4},
                        'thickness': 0.75,
                        'value': 60
                    }
                }
            ))
            fig_tfg.update_layout(height=350, margin=dict(l=20, r=20, t=80, b=20))
            st.plotly_chart(fig_tfg, use_container_width=True)
            
            # Clasificación ERC
            if d['tfg'] >= 90:
                categoria = "G1 - Normal"
                color = "green"
            elif d['tfg'] >= 60:
                categoria = "G2 - Leve ↓"
                color = "lightgreen"
            elif d['tfg'] >= 45:
                categoria = "G3a - Moderada ↓"
                color = "yellow"
            elif d['tfg'] >= 30:
                categoria = "G3b - Moderada-Severa ↓"
                color = "orange"
            elif d['tfg'] >= 15:
                categoria = "G4 - Severa ↓"
                color = "darkorange"
            else:
                categoria = "G5 - Falla Renal"
                color = "red"
            
            st.markdown(f"**Clasificación KDIGO:** :{color}[{categoria}]")
        
        with col_g2:
            # Gauge de FEVI
            fig_fevi = go.Figure(go.Indicator(
                mode="gauge+number",
                value=d['fevi'],
                title={'text': "Función Cardíaca (FEVI)<br><span style='font-size:0.8em'>Fracción de Eyección %</span>", 'font': {'size': 20}},
                gauge={
                    'axis': {'range': [0, 80]},
                    'bar': {'color': "crimson"},
                    'steps': [
                        {'range': [0, 40], 'color': "rgba(255, 0, 0, 0.3)"},
                        {'range': [40, 50], 'color': "rgba(255, 165, 0, 0.3)"},
                        {'range': [50, 80], 'color': "rgba(0, 128, 0, 0.3)"}
                    ],
                    'threshold': {
                        'line': {'color': "orange", 'width': 4},
                        'thickness': 0.75,
                        'value': 50
                    }
                }
            ))
            fig_fevi.update_layout(height=350, margin=dict(l=20, r=20, t=80, b=20))
            st.plotly_chart(fig_fevi, use_container_width=True)
            
            # Clasificación IC
            if d['fevi'] >= 50:
                cat_fevi = "Normal"
                color_fevi = "green"
            elif d['fevi'] >= 40:
                cat_fevi = "FE Limítrofe"
                color_fevi = "orange"
            else:
                cat_fevi = "IC con FE Reducida"
                color_fevi = "red"
            
            st.markdown(f"**Estado Cardíaco:** :{color_fevi}[{cat_fevi}]")
        
        # Gráfico de tendencia proyectada
        st.subheader("📈 Proyección de Evolución (Con Adherencia al Tratamiento)")
        fechas = ["Hoy", "+2 meses", "+4 meses", "+6 meses", "+12 meses"]
        
        # Proyección optimista con tratamiento
        if d['tfg'] < 60:
            progreso_tfg = [d['tfg'], d['tfg']*1.02, d['tfg']*1.04, d['tfg']*1.06, d['tfg']*1.08]
        else:
            progreso_tfg = [d['tfg'], d['tfg']*1.01, d['tfg']*1.015, d['tfg']*1.02, d['tfg']*1.02]
        
        if d['fevi'] < 50:
            progreso_fevi = [d['fevi'], d['fevi']*1.03, d['fevi']*1.06, d['fevi']*1.08, d['fevi']*1.10]
        else:
            progreso_fevi = [d['fevi'], d['fevi']*1.01, d['fevi']*1.01, d['fevi']*1.015, d['fevi']*1.015]
        
        fig_trend = go.Figure()
        fig_trend.add_trace(go.Scatter(
            x=fechas, y=progreso_tfg, 
            mode='lines+markers', 
            name="TFG Proyectada",
            line=dict(color='royalblue', width=3),
            marker=dict(size=10)
        ))
        fig_trend.add_trace(go.Scatter(
            x=fechas, y=progreso_fevi, 
            mode='lines+markers', 
            name="FEVI Proyectada",
            line=dict(color='crimson', width=3, dash='dash'),
            marker=dict(size=10, symbol='diamond')
        ))
        
        fig_trend.update_layout(
            title="Evolución Esperada con Manejo Óptimo",
            xaxis_title="Tiempo",
            yaxis_title="Valor",
            hovermode='x unified',
            height=400,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig_trend, use_container_width=True)
        
        # Gráfico de parámetros múltiples
        st.subheader("🎯 Panel de Parámetros Clínicos")
        col_p1, col_p2 = st.columns(2)
        
        with col_p1:
            # Gráfico de barras comparativo
            parametros = ['Presión\nSistólica', 'Potasio\n(K+)', 'Horas\nSueño']
            valores = [d['sys'], d['potasio']*25, d['sleep']*15]
            valores_objetivo = [120, 4.5*25, 7.5*15]
            
            fig_params = go.Figure(data=[
                go.Bar(name='Valor Actual', x=parametros, y=valores, marker_color='lightsalmon'),
                go.Bar(name='Valor Objetivo', x=parametros, y=valores_objetivo, marker_color='lightgreen')
            ])
            fig_params.update_layout(
                title="Comparación con Valores Objetivo",
                barmode='group',
                height=350,
                yaxis_title="Valor (escala normalizada)"
            )
            st.plotly_chart(fig_params, use_container_width=True)
        
        with col_p2:
            # Gráfico de radar para estilo de vida
            categories = ['Sueño\n(h/día)', 'Ejercicio\n(min/sem)', 'Control\nEstrés']
            
            valores_actuales = [
                (d['sleep'] / 8) * 100,
                (d.get('exercise', 0) / 150) * 100,
                {'Alto': 30, 'Moderado': 60, 'Bajo': 90}.get(d['stress'], 60)
            ]
            
            fig_radar = go.Figure()
            fig_radar.add_trace(go.Scatterpolar(
                r=valores_actuales,
                theta=categories,
                fill='toself',
                name='Actual',
                line_color='coral'
            ))
            fig_radar.add_trace(go.Scatterpolar(
                r=[100, 100, 100],
                theta=categories,
                fill='toself',
                name='Objetivo',
                line_color='lightgreen',
                opacity=0.5
            ))
            fig_radar.update_layout(
                polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
                title="Evaluación de Estilo de Vida",
                height=350
            )
            st.plotly_chart(fig_radar, use_container_width=True)
        
        # Recomendaciones científicas
        st.divider()
        st.header("💊 Plan de Tratamiento y Recomendaciones")
        
        tab1, tab2, tab3, tab4 = st.tabs(["🏥 Manejo Clínico", "🥗 Nutrición", "🏃 Estilo de Vida", "📅 Seguimiento"])
        
        with tab1:
            if r['clinico']:
                for rec in r['clinico']:
                    st.success(rec)
            else:
                st.info("No se detectaron necesidades clínicas urgentes")
        
        with tab2:
            if r['dieta']:
                for rec in r['dieta']:
                    st.warning(rec) if 'URGENTE' in rec or '🔴' in rec else st.info(rec)
            else:
                st.info("Mantener dieta balanceada según recomendaciones generales")
        
        with tab3:
            if r['estilo']:
                for rec in r['estilo']:
                    st.info(rec)
            else:
                st.success("Estilo de vida dentro de parámetros saludables")
        
        with tab4:
            if r['seguimiento']:
                for rec in r['seguimiento']:
                    st.info(rec)
            else:
                st.info("Control anual de rutina recomendado")
        
        # Generar PDF
        st.divider()
        col_pdf, col_info = st.columns([1, 2])
        
        with col_pdf:
            st.subheader("📄 Generar Reporte")
            pdf_data = crear_pdf(d, r, alertas, st.session_state.name)
            st.download_button(
                label="⬇️ Descargar PDF Completo",
                data=pdf_data,
                file_name=f"Reporte_Cardiorrenal_{d['px_id']}_{datetime.now().strftime('%Y%m%d')}.pdf",
                mime="application/pdf",
                use_container_width=True,
                type="primary"
            )
            st.caption(f"Generado por: Dr. {st.session_state.name}")
        
        with col_info:
            st.warning("""
            ### ⚕️ IMPORTANTE - Uso Responsable del Sistema
            
            Este sistema es una **herramienta de apoyo clínico** basada en:
            - Guías KDIGO 2024 (Enfermedad Renal Crónica)
            - Guías AHA/ACC 2023 (Insuficiencia Cardíaca)
            
            **NO sustituye:**
            - La evaluación médica presencial
            - El juicio clínico individualizado
            - La valoración integral del contexto del paciente
            
            Todas las decisiones terapéuticas deben ser validadas por el médico tratante.
            """)

# =============================================
# SECCIÓN: HISTORIAL DE PACIENTES
# =============================================
elif menu == "📂 Historial":
    st.title("📂 Historial Clínico de Pacientes")
    
    col_search, col_filter = st.columns([2, 1])
    with col_search:
        h_px = st.text_input("🔍 Buscar por nombre de paciente", placeholder="Ej: Juan Pérez")
    with col_filter:
        fecha_desde = st.date_input("Desde", datetime.now().replace(day=1))
    
    if h_px or st.button("Ver todos los registros"):
        query = "SELECT * FROM clinical_records WHERE 1=1"
        params = []
        
        if h_px:
            query += " AND px_name LIKE ?"
            params.append(f"%{h_px}%")
        
        query += " ORDER BY date DESC"
        
        df_h = pd.read_sql(query, db.conn, params=params if params else None)
        
        if not df_h.empty:
            st.success(f"✅ Se encontraron {len(df_h)} registros")
            
            # Mostrar tabla
            st.dataframe(
                df_h[['id', 'px_name', 'px_id', 'date', 'doctor', 'tfg', 'fevi', 'potasio', 'sys']],
                use_container_width=True,
                column_config={
                    "id": "ID",
                    "px_name": "Paciente",
                    "px_id": "Cédula",
                    "date": "Fecha",
                    "doctor": "Médico",
                    "tfg": st.column_config.NumberColumn("TFG", format="%.1f"),
                    "fevi": st.column_config.NumberColumn("FEVI %", format="%.0f"),
                    "potasio": st.column_config.NumberColumn("K+", format="%.2f"),
                    "sys": st.column_config.NumberColumn("PA Sistólica", format="%.0f")
                }
            )
            
            # Gráfico de evolución histórica
            if len(df_h) > 1:
                st.subheader("📈 Evolución Temporal")
                
                fig_hist = go.Figure()
                fig_hist.add_trace(go.Scatter(
                    x=df_h['date'], y=df_h['tfg'],
                    mode='lines+markers',
                    name='TFG',
                    line=dict(color='blue', width=2),
                    marker=dict(size=8)
                ))
                fig_hist.add_trace(go.Scatter(
                    x=df_h['date'], y=df_h['fevi'],
                    mode='lines+markers',
                    name='FEVI',
                    line=dict(color='red', width=2),
                    marker=dict(size=8),
                    yaxis='y2'
                ))
                
                fig_hist.update_layout(
                    title=f"Evolución Clínica - {df_h.iloc[0]['px_name']}",
                    xaxis_title="Fecha",
                    yaxis=dict(title="TFG (ml/min)", side='left'),
                    yaxis2=dict(title="FEVI (%)", overlaying='y', side='right'),
                    hovermode='x unified',
                    height=400
                )
                st.plotly_chart(fig_hist, use_container_width=True)
                
                # Análisis de tendencia
                tendencia_tfg = df_h['tfg'].iloc[0] - df_h['tfg'].iloc[-1]
                tendencia_fevi = df_h['fevi'].iloc[0] - df_h['fevi'].iloc[-1]
                
                col_t1, col_t2 = st.columns(2)
                with col_t1:
                    if tendencia_tfg > 0:
                        st.success(f"📈 TFG: Mejora de {tendencia_tfg:.1f} ml/min")
                    elif tendencia_tfg < 0:
                        st.error(f"📉 TFG: Descenso de {abs(tendencia_tfg):.1f} ml/min")
                    else:
                        st.info("➡️ TFG: Estable")
                
                with col_t2:
                    if tendencia_fevi > 0:
                        st.success(f"📈 FEVI: Mejora de {tendencia_fevi:.1f}%")
                    elif tendencia_fevi < 0:
                        st.error(f"📉 FEVI: Descenso de {abs(tendencia_fevi):.1f}%")
                    else:
                        st.info("➡️ FEVI: Estable")
        else:
            st.warning("No se encontraron registros con los criterios de búsqueda")

# =============================================
# SECCIÓN: PANEL DE ADMINISTRACIÓN
# =============================================
elif menu == "⚙️ Panel Admin":
    if st.session_state.role != 'admin':
        st.error("⛔ Acceso denegado. Se requieren privilegios de administrador.")
        st.stop()
    
    st.title("⚙️ Panel de Administración")
    
    tab1, tab2 = st.tabs(["👥 Gestión de Usuarios", "📊 Auditoría del Sistema"])
    
    # TAB 1: Gestión de Usuarios
    with tab1:
        st.header("👥 Administración de Usuarios")
        
        # Listar usuarios existentes
        df_users = pd.read_sql("SELECT username, name, role, specialty, active, created_date FROM users", db.conn)
        
        col_u1, col_u2 = st.columns([2, 1])
        with col_u1:
            st.subheader("Usuarios Registrados")
            st.dataframe(
                df_users,
                use_container_width=True,
                column_config={
                    "username": "Usuario",
                    "name": "Nombre",
                    "role": "Rol",
                    "specialty": "Especialidad",
                    "active": st.column_config.CheckboxColumn("Activo"),
                    "created_date": "Fecha Creación"
                }
            )
        
        with col_u2:
            st.metric("Total Usuarios", len(df_users))
            st.metric("Usuarios Activos", df_users['active'].sum())
            st.metric("Administradores", len(df_users[df_users['role'] == 'admin']))
        
        st.divider()
        
        # Crear nuevo usuario
        col_crear, col_gestionar = st.columns(2)
        
        with col_crear:
            st.subheader("➕ Crear Nuevo Usuario")
            with st.form("add_user_form"):
                new_u = st.text_input("Usuario *", placeholder="jperez")
                new_n = st.text_input("Nombre Completo *", placeholder="Dr. Juan Pérez")
                new_p = st.text_input("Contraseña *", type="password", placeholder="Mínimo 8 caracteres")
                new_spec = st.text_input("Especialidad", placeholder="Cardiología")
                new_r = st.selectbox("Rol *", ["medico", "admin"])
                
                if st.form_submit_button("✅ Crear Usuario", use_container_width=True, type="primary"):
                    if new_u and new_n and new_p:
                        try:
                            hash_p = bcrypt.hashpw(new_p.encode(), bcrypt.gensalt()).decode()
                            db.conn.execute(
                                "INSERT INTO users (username, password, name, role, specialty, active, created_date) VALUES (?,?,?,?,?,1,?)",
                                (new_u, hash_p, new_n, new_r, new_spec, datetime.now().strftime("%Y-%m-%d"))
                            )
                            db.conn.commit()
                            db.log_action(st.session_state.username, "Usuario Creado", f"Nuevo usuario: {new_u} ({new_r})")
                            st.success(f"✅ Usuario '{new_u}' creado exitosamente")
                            st.rerun()
                        except sqlite3.IntegrityError:
                            st.error("❌ El usuario ya existe")
                    else:
                        st.error("⚠️ Complete todos los campos obligatorios")
        
        with col_gestionar:
            st.subheader("🔧 Gestionar Usuario Existente")
            user_select = st.selectbox("Seleccionar usuario", df_users['username'].tolist())
            
            if user_select:
                user_data = df_users[df_users['username'] == user_select].iloc[0]
                
                col_act1, col_act2 = st.columns(2)
                
                with col_act1:
                    if user_data['active'] == 1:
                        if st.button("🔴 Desactivar Usuario", use_container_width=True):
                            db.conn.execute("UPDATE users SET active=0 WHERE username=?", (user_select,))
                            db.conn.commit()
                            db.log_action(st.session_state.username, "Usuario Desactivado", f"Usuario: {user_select}")
                            st.success(f"Usuario '{user_select}' desactivado")
                            st.rerun()
                    else:
                        if st.button("🟢 Activar Usuario", use_container_width=True):
                            db.conn.execute("UPDATE users SET active=1 WHERE username=?", (user_select,))
                            db.conn.commit()
                            db.log_action(st.session_state.username, "Usuario Activado", f"Usuario: {user_select}")
                            st.success(f"Usuario '{user_select}' activado")
                            st.rerun()
                
                with col_act2:
                    if st.button("🗑️ Eliminar Permanentemente", use_container_width=True, type="secondary"):
                        if user_select != 'admin':
                            db.conn.execute("DELETE FROM users WHERE username=?", (user_select,))
                            db.conn.commit()
                            db.log_action(st.session_state.username, "Usuario Eliminado", f"Usuario: {user_select}")
                            st.warning(f"Usuario '{user_select}' eliminado")
                            st.rerun()
                        else:
                            st.error("⛔ No se puede eliminar el usuario admin")
                
                st.info(f"""
                **Información del Usuario:**
                - **Nombre:** {user_data['name']}
                - **Rol:** {user_data['role']}
                - **Especialidad:** {user_data['specialty'] or 'N/A'}
                - **Estado:** {'Activo' if user_data['active'] == 1 else 'Inactivo'}
                - **Creado:** {user_data['created_date']}
                """)
    
    # TAB 2: Auditoría
    with tab2:
        st.header("📊 Registro de Auditoría del Sistema")
        
        col_f1, col_f2, col_f3 = st.columns(3)
        with col_f1:
            filtro_user = st.selectbox("Filtrar por usuario", ["Todos"] + df_users['username'].tolist())
        with col_f2:
            filtro_accion = st.selectbox("Filtrar por acción", 
                ["Todas", "Login", "Logout", "Consulta Creada", "Usuario Creado", "Usuario Desactivado", "Usuario Eliminado"])
        with col_f3:
            limite_registros = st.number_input("Mostrar últimos N registros", 10, 1000, 100, step=10)
        
        # Construir query de auditoría
        query_audit = "SELECT * FROM audit_logs WHERE 1=1"
        params_audit = []
        
        if filtro_user != "Todos":
            query_audit += " AND user = ?"
            params_audit.append(filtro_user)
        
        if filtro_accion != "Todas":
            query_audit += " AND action = ?"
            params_audit.append(filtro_accion)
        
        query_audit += f" ORDER BY id DESC LIMIT {limite_registros}"
        
        df_logs = pd.read_sql(query_audit, db.conn, params=params_audit if params_audit else None)
        
        if not df_logs.empty:
            st.dataframe(
                df_logs,
                use_container_width=True,
                column_config={
                    "id": "ID",
                    "timestamp": "Fecha/Hora",
                    "user": "Usuario",
                    "action": "Acción",
                    "details": "Detalles"
                }
            )
            
            # Estadísticas de auditoría
            st.divider()
            st.subheader("📈 Estadísticas de Actividad")
            
            col_s1, col_s2, col_s3, col_s4 = st.columns(4)
            col_s1.metric("Total Eventos", len(df_logs))
            col_s2.metric("Logins", len(df_logs[df_logs['action'] == 'Login']))
            col_s3.metric("Consultas", len(df_logs[df_logs['action'] == 'Consulta Creada']))
            col_s4.metric("Usuarios Únicos", df_logs['user'].nunique())
            
            # Gráfico de actividad por acción
            fig_audit = px.pie(
                df_logs, 
                names='action', 
                title='Distribución de Acciones en el Sistema',
                hole=0.4
            )
            st.plotly_chart(fig_audit, use_container_width=True)
            
            # Exportar auditoría
            csv = df_logs.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Exportar Auditoría (CSV)",
                data=csv,
                file_name=f"auditoria_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
        else:
            st.info("No hay registros de auditoría con los filtros seleccionados")

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666; font-size: 0.9em;'>
    <p><strong>NefroCardio Pro SaaS v2.0</strong> | Sistema de Evaluación Cardiorrenal</p>
    <p>⚕️ Basado en guías KDIGO 2024 y AHA/ACC 2023</p>
    <p>⚠️ <em>Herramienta de apoyo clínico - No sustituye la evaluación médica profesional</em></p>
</div>
""", unsafe_allow_html=True)
