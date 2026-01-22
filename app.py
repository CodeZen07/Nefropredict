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

# Aplicar tema oscuro personalizado
st.markdown("""
<style>
    /* Fondo principal */
    .stApp {
        background-color: #0f172a;
    }
    
    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: #1e293b;
    }
    
    /* Texto principal */
    .stApp, p, span, label {
        color: #f8fafc !important;
    }
    
    /* Headers */
    h1, h2, h3 {
        color: #3b82f6 !important;
    }
    
    /* Inputs y selectbox */
    .stTextInput > div > div, .stSelectbox > div > div, .stNumberInput > div > div {
        background-color: #1e293b !important;
        border-color: #334155 !important;
        color: #f8fafc !important;
    }
    
    /* Botones primarios */
    .stButton > button[kind="primary"] {
        background-color: #2563eb !important;
        color: #f8fafc !important;
        border: none !important;
    }
    
    .stButton > button[kind="primary"]:hover {
        background-color: #3b82f6 !important;
    }
    
    /* Botones secundarios */
    .stButton > button {
        background-color: #334155 !important;
        color: #f8fafc !important;
        border: 1px solid #475569 !important;
    }
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        background-color: #1e293b;
        border-bottom: 2px solid #334155;
    }
    
    .stTabs [data-baseweb="tab"] {
        color: #94a3b8 !important;
        background-color: transparent;
    }
    
    .stTabs [aria-selected="true"] {
        color: #3b82f6 !important;
        border-bottom-color: #3b82f6 !important;
    }
    
    /* Métricas */
    [data-testid="stMetricValue"] {
        color: #3b82f6 !important;
    }
    
    /* Dataframes */
    .stDataFrame {
        background-color: #1e293b !important;
    }
    
    /* Divisores */
    hr {
        border-color: #334155 !important;
    }
    
    /* Info boxes */
    .stInfo {
        background-color: #1e293b !important;
        border-left-color: #2563eb !important;
        color: #f8fafc !important;
    }
    
    /* Success boxes */
    .stSuccess {
        background-color: #1e293b !important;
        border-left-color: #10b981 !important;
        color: #f8fafc !important;
    }
    
    /* Warning boxes */
    .stWarning {
        background-color: #1e293b !important;
        border-left-color: #f59e0b !important;
        color: #f8fafc !important;
    }
    
    /* Error boxes */
    .stError {
        background-color: #1e293b !important;
        border-left-color: #ef4444 !important;
        color: #f8fafc !important;
    }
    
    /* Forms */
    .stForm {
        background-color: #1e293b;
        border: 1px solid #334155;
        border-radius: 8px;
        padding: 20px;
    }
    
    /* Slider */
    .stSlider > div > div > div {
        background-color: #334155 !important;
    }
    
    /* Radio buttons */
    .stRadio > label {
        color: #f8fafc !important;
    }
    
    /* Text area */
    .stTextArea > div > div {
        background-color: #1e293b !important;
        border-color: #334155 !important;
        color: #f8fafc !important;
    }
    
    /* Date input */
    .stDateInput > div > div {
        background-color: #1e293b !important;
        border-color: #334155 !important;
        color: #f8fafc !important;
    }
    
    /* Expander */
    .streamlit-expanderHeader {
        background-color: #1e293b !important;
        border-color: #334155 !important;
        color: #f8fafc !important;
    }
</style>
""", unsafe_allow_html=True)

class AppDatabase:
    def __init__(self):
        self.conn = sqlite3.connect("nefrocardio_v2026.db", check_same_thread=False)
        self.init_db()

    def init_db(self):
        c = self.conn.cursor()
        
        # Crear tabla de usuarios
        c.execute("""CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY, 
            password TEXT, 
            name TEXT, 
            role TEXT, 
            specialty TEXT,
            active INTEGER DEFAULT 1,
            created_date TEXT)""")
        
        # Migración: Agregar columnas si no existen
        try:
            c.execute("SELECT active FROM users LIMIT 1")
        except sqlite3.OperationalError:
            c.execute("ALTER TABLE users ADD COLUMN active INTEGER DEFAULT 1")
            print("Columna 'active' agregada a la tabla users")
        
        try:
            c.execute("SELECT created_date FROM users LIMIT 1")
        except sqlite3.OperationalError:
            c.execute("ALTER TABLE users ADD COLUMN created_date TEXT")
            c.execute("UPDATE users SET created_date = ? WHERE created_date IS NULL", 
                     (datetime.now().strftime("%Y-%m-%d"),))
            print("Columna 'created_date' agregada a la tabla users")
        
        # Crear tabla de registros clínicos
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
        
        # Migración: Agregar columna exercise si no existe
        try:
            c.execute("SELECT exercise FROM clinical_records LIMIT 1")
        except sqlite3.OperationalError:
            c.execute("ALTER TABLE clinical_records ADD COLUMN exercise INTEGER DEFAULT 0")
            print("Columna 'exercise' agregada a clinical_records")
        
        # Crear tabla de auditoría
        c.execute("""CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            timestamp TEXT, 
            user TEXT, 
            action TEXT, 
            details TEXT)""")
        
        # Crear usuario admin si no existe
        c.execute("SELECT * FROM users WHERE username='admin'")
        if not c.fetchone():
            pw = bcrypt.hashpw("Admin2026!".encode(), bcrypt.gensalt()).decode()
            c.execute("INSERT INTO users VALUES ('admin', ?, 'Admin Master', 'admin', 'Sistemas', 1, ?)", 
                     (pw, datetime.now().strftime("%Y-%m-%d")))
            print("Usuario admin creado")
        
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
    pdf.set_text_color(37, 99, 235)  # #2563eb
    pdf.cell(0, 12, "REPORTE MEDICO CARDIORRENAL", ln=True, align='C')
    pdf.set_text_color(0, 0, 0)
    pdf.ln(5)
    
    # Información del paciente
    pdf.set_font("Arial", 'B', 13)
    pdf.set_fill_color(30, 41, 59)  # #1e293b
    pdf.cell(0, 10, "DATOS DEL PACIENTE", ln=True, fill=True)
    pdf.set_font("Arial", '', 11)
    pdf.cell(95, 8, f"Nombre: {datos['px_name']}", border=1)
    pdf.cell(95, 8, f"ID: {datos['px_id']}", border=1, ln=True)
    pdf.cell(95, 8, f"Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}", border=1)
    pdf.cell(95, 8, f"Medico: Dr. {medico}", border=1, ln=True)
    pdf.ln(8)
    
    # Resultados clínicos
    pdf.set_font("Arial", 'B', 13)
    pdf.set_fill_color(30, 41, 59)  # #1e293b
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
        pdf.set_text_color(239, 68, 68)  # #ef4444
        pdf.cell(0, 8, "ALERTAS CLINICAS", ln=True)
        pdf.set_text_color(0, 0, 0)
        pdf.set_font("Arial", '', 10)
        for alerta in alertas:
            pdf.multi_cell(0, 6, f"* {alerta}")
        pdf.ln(3)
    
    # Recomendaciones
    pdf.set_font("Arial", 'B', 13)
    pdf.set_fill_color(30, 41, 59)  # #1e293b
    pdf.cell(0, 10, "PLAN DE TRATAMIENTO Y RECOMENDACIONES", ln=True, fill=True)
    pdf.ln(2)
    
    categorias = {
        'clinico': ('MANEJO CLINICO', (16, 185, 129)),  # #10b981
        'dieta': ('INTERVENCION NUTRICIONAL', (139, 69, 19)),
        'estilo': ('MODIFICACION DE ESTILO DE VIDA', (59, 130, 246)),  # #3b82f6
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
    pdf.set_text_color(148, 163, 184)  # #94a3b8
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
        
        # Gráficos principales con tema oscuro
        col_g1, col_g2 = st.columns(2)
        
        with col_g1:
            # Gauge de TFG con colores oscuros
            fig_tfg = go.Figure(go.Indicator(
                mode="gauge+number+delta",
                value=d['tfg'],
                title={'text': "Función Renal (TFG)<br><span style='font-size:0.8em'>ml/min/1.73m²</span>", 'font': {'size': 20, 'color': '#f8fafc'}},
                delta={'reference': 90, 'increasing': {'color': "#10b981"}},
                gauge={
                    'axis': {'range': [None, 120], 'tickwidth': 1, 'tickcolor': '#94a3b8'},
                    'bar': {'color': "#3b82f6"},
                    'bgcolor': "#1e293b",
                    'steps': [
                        {'range': [0, 15], 'color': "#7f1d1d"},
                        {'range': [15, 30], 'color': "#991b1b"},
                        {'range': [30, 45], 'color': "#b45309"},
                        {'range': [45, 60], 'color': "#ca8a04"},
                        {'range': [60, 90], 'color': "#15803d"},
                        {'range': [90, 120], 'color': "#047857"}
                    ],
                    'threshold': {
                        'line': {'color': "#ef4444", 'width': 4},
                        'thickness': 0.75,
                        'value': 60
                    }
                }
            ))
            fig_tfg.update_layout(
                height=350, 
                margin=dict(l=20, r=20, t=80, b=20),
                paper_bgcolor='#0f172a',
                plot_bgcolor='#1e293b',
                font={'color': '#f8fafc'}
            )
            st.plotly_chart(fig_tfg, use_container_width=True)
            
            # Clasificación ERC
            if d['tfg'] >= 90:
                st.success("**Clasificación KDIGO:** G1 - Normal")
            elif d['tfg'] >= 60:
                st.info("**Clasificación KDIGO:** G2 - Leve ↓")
            elif d['tfg'] >= 45:
                st.warning("**Clasificación KDIGO:** G3a - Moderada ↓")
            elif d['tfg'] >= 30:
                st.warning("**Clasificación KDIGO:** G3b - Moderada-Severa ↓")
            elif d['tfg'] >= 15:
                st.error("**Clasificación KDIGO:** G4 - Severa ↓")
            else:
                st.error("**Clasificación KDIGO:** G5 - Falla Renal")
        
        with col_g2:
            #
