import pandas as pd
import sqlite3
import bcrypt
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from fpdf import FPDF
from io import BytesIO

# =============================================
# 1. CONFIGURACIÓN Y MARCO LEGAL
# =============================================
st.set_page_config(page_title="NefroCardio SaaS RD", page_icon="🏥", layout="wide")

LEGAL_NOTICE = """AVISO: Soporte clinico basado en guias KDIGO (2024) y AHA/ACC (2023). 
El juicio del profesional prevalece sobre los calculos de la app."""

# =============================================
# 2. MOTOR DE BASE DE DATOS (CON OBSERVACIONES)
# =============================================
class AppDatabase:
    def __init__(self):
        self.conn = sqlite3.connect("nefrocardio_v7.db", check_same_thread=False)
        self.init_db()
        self.repair_db()

    def init_db(self):
        cursor = self.conn.cursor()
        cursor.execute("""CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY, password TEXT, name TEXT, 
            role TEXT, specialty TEXT, active INT)""")
        cursor.execute("""CREATE TABLE IF NOT EXISTS records (
            id INTEGER PRIMARY KEY AUTOINCREMENT, px_id TEXT, px_name TEXT, 
            doctor TEXT, spec TEXT, weight REAL, height REAL, sys INT, 
            gluc REAL, creat REAL, tfg REAL, risk REAL, date TEXT,
            sleep_hours REAL, stress_level TEXT, exercise_min INT,
            observations TEXT)""") # Columna de observaciones añadida
        
        cursor.execute("SELECT * FROM users WHERE username='admin'")
        if not cursor.fetchone():
            hashed = bcrypt.hashpw("Admin2026!".encode(), bcrypt.gensalt()).decode()
            cursor.execute("INSERT INTO users VALUES (?,?,?,?,?,?)", 
                          ("admin", hashed, "Admin Maestro", "admin", "todas", 1))
        self.conn.commit()

    def repair_db(self):
        cursor = self.conn.cursor()
        cursor.execute("PRAGMA table_info(records)")
        cols = [c[1] for c in cursor.fetchall()]
        if 'observations' not in cols:
            cursor.execute("ALTER TABLE records ADD COLUMN observations TEXT")
        self.conn.commit()

db = AppDatabase()

# =============================================
# 3. LÓGICA CIENTÍFICA Y SUGERENCIAS SUSTENTADAS
# =============================================
def get_medical_insights(data):
    imc = round(data['w'] / ((data['h']/100)**2), 1)
    tfg = data['tfg']
    
    # Sugerencias basadas en evidencia
    sug = []
    if tfg < 60:
        sug.append("⚠️ Sugerencia KDIGO: Ajustar dosis de farmacos de excrecion renal y evitar AINEs.")
    if data['sys'] > 130:
        sug.append("❤️ Guia AHA: Meta tensional <130/80 mmHg. Considerar IECA/ARA-II si existe proteinuria.")
    if imc > 25:
        sug.append(f"🥗 Meta Nutricional: Reducir {round(data['w']*0.1,1)}kg para mejorar perfil metabolico.")
    
    plan = {
        "nutricion": "Dieta DASH/Mediterranea rica en potasio (si TFG >30) y baja en sodio.",
        "ejercicio": "150 min/semana de actividad aerobica moderada (Guia OMS).",
        "sueno": "Higiene del sueno estricta: Meta 7.5h para regulacion de cortisol.",
        "sugerencias": " ".join(sug)
    }
    return plan, imc

def export_pdf(p_data, doc_name):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_fill_color(0, 51, 102)
    pdf.rect(0, 0, 210, 40, 'F')
    pdf.set_font("Arial", 'B', 16)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 15, "INFORME MEDICO Y PLAN ESTRATEGICO", 0, 1, 'C')
    
    pdf.set_text_color(0, 0, 0)
    pdf.ln(25)
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(0, 8, f"Paciente: {p_data['name']} | ID: {p_data['id']}", 0, 1)
    pdf.cell(0, 8, f"Medico: {doc_name} | Fecha: {datetime.now().strftime('%d/%m/%Y')}", 0, 1)
    pdf.line(10, 62, 200, 62)
    
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(0, 8, "OBSERVACIONES CLINICAS:", 0, 1)
    pdf.set_font("Arial", '', 10)
    pdf.multi_cell(0, 6, p_data.get('obs', 'Sin observaciones').replace('ñ','n'))
    
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(0, 8, "RECOMENDACIONES BASADAS EN EVIDENCIA:", 0, 1)
    for k, v in p_data['plan'].items():
        pdf.set_font("Arial", 'B', 9)
        pdf.cell(0, 6, f"{k.upper()}:", 0, 1)
        pdf.set_font("Arial", '', 9)
        pdf.multi_cell(0, 5, str(v).replace('ñ','n').replace('á','a').replace('é','e').replace('í','i').replace('ó','o').replace('ú','u'))
        pdf.ln(1)
        
    res = pdf.output(dest='S')
    return BytesIO(res.encode('latin-1', errors='replace')) if isinstance(res, str) else BytesIO(res)

# =============================================
# 4. INTERFAZ (LOGIN Y NAVEGACIÓN)
# =============================================
if "auth" not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:
    c1, c2, c3 = st.columns([1, 1.2, 1])
    with c2:
        st.title("🏥 NefroCardio SaaS")
        u = st.text_input("Usuario")
        p = st.text_input("Clave", type="password")
        if st.button("Ingresar", use_container_width=True):
            cursor = db.conn.cursor()
            cursor.execute("SELECT password, name, role, specialty FROM users WHERE username=?", (u,))
            res = cursor.fetchone()
            if res and bcrypt.checkpw(p.encode(), res[0].encode()):
                st.session_state.update({"auth":True, "user":u, "name":res[1], "role":res[2], "spec":res[3] if res[3] else "todas"})
                st.rerun()
    st.stop()

# --- SIDEBAR ---
with st.sidebar:
    st.header(f"Dr. {st.session_state.get('name')}")
    st.info(f"Especialidad: {st.session_state.get('spec').upper()}")
    menu = st.radio("Menú", ["🩺 Nueva Consulta", "📅 Historial Clínico", "⚙️ Admin"])
    if st.button("Cerrar Sesión"):
        st.session_state.clear()
        st.rerun()

# --- MÓDULO CONSULTA ---
if menu == "🩺 Nueva Consulta":
    st.header("Evaluación Médica Integral")
    
    cursor = db.conn.cursor()
    cursor.execute("SELECT DISTINCT px_name FROM records")
    lista_px = [row[0] for row in cursor.fetchall()]
    
    sel_px = st.selectbox("🔍 Buscar Paciente:", ["-- Registrar Nuevo --"] + lista_px)
    
    px_id, px_name, w_ini, h_ini, obs_ini = "", "", 70.0, 165.0, ""
    
    if sel_px != "-- Registrar Nuevo --":
        cursor.execute("SELECT px_id, weight, height, observations FROM records WHERE px_name=? ORDER BY id DESC LIMIT 1", (sel_px,))
        prev = cursor.fetchone()
        if prev: px_id, px_name, w_ini, h_ini, obs_ini = prev[0], sel_px, prev[1], prev[2], prev[3]

    # FORMULARIO
    with st.form("consulta_form"):
        c1, c2 = st.columns(2)
        f_name = c1.text_input("Nombre Paciente", value=px_name)
        f_id = c2.text_input("ID/Cédula", value=px_id)
        
        st.markdown("### 🧬 Parámetros Clínicos")
        col1, col2, col3, col4 = st.columns(4)
        weight = col1.number_input("Peso (kg)", 30.0, 200.0, w_ini)
        height = col2.number_input("Talla (cm)", 100, 220, int(h_ini))
        sys_p = col3.number_input("Presión Sistólica", 80, 200, 120)
        gluc = col4.number_input("Glucosa", 60, 400, 100)
        
        st.markdown("### 🥗 Estilo de Vida")
        b1, b2, b3 = st.columns(3)
        sleep = b1.slider("Sueño (Hrs)", 3.0, 12.0, 7.0)
        exer = b2.number_input("Minutos Ejercicio/Sem", 0, 600, 150)
        stress = b3.selectbox("Estrés", ["Bajo", "Moderado", "Alto"])
        
        st.markdown("### 📝 Notas Médicas")
        observations = st.text_area("Observaciones y comentarios personalizados:", value=obs_ini)

        # Cálculo TFG
        tfg = 0
        if st.session_state.get('spec') in ["nefrologia", "todas"]:
            cr = st.number_input("Creatinina", 0.4, 15.0, 1.0)
            tfg = round(141 * min(cr/0.9, 1)**-0.411 * 0.993**45, 1)

        btn_save = st.form_submit_button("ANALIZAR Y GUARDAR")

    # PROCESAMIENTO FUERA DEL FORMULARIO (Evita el error de Streamlit)
    if btn_save:
        if f_name and f_id:
            plan, imc = get_medical_insights({'w':weight, 'h':height, 'tfg':tfg, 'sys':sys_p})
            
            db.conn.execute("""INSERT INTO records 
                (px_id, px_name, doctor, spec, weight, height, sys, gluc, creat, tfg, date, sleep_hours, stress_level, exercise_min, observations) 
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (f_id, f_name, st.session_state.get('name'), st.session_state.get('spec'), weight, height, sys_p, gluc, 1.0, tfg, 
                 datetime.now().strftime('%Y-%m-%d'), sleep, stress, exer, observations))
            db.conn.commit()
            
            st.success("✅ Registro almacenado con éxito.")
            
            # --- SECCIÓN DE GRÁFICOS AMIGABLES ---
            st.markdown("---")
            st.subheader("📊 Análisis Visual de Riesgos")
            g1, g2 = st.columns(2)
            
            with g1:
                # Gráfico de Radar de Riesgo
                fig_radar = go.Figure()
                fig_radar.add_trace(go.Scatterpolar(
                    r=[imc, sys_p/5, (150-tfg)/2 if tfg>0 else 0, exer/10],
                    theta=['IMC', 'Presión', 'Disfunción Renal', 'Actividad'],
                    fill='toself', name='Perfil Actual'
                ))
                fig_radar.update_layout(polar=dict(radialaxis=dict(visible=False)), showlegend=False, title="Radar de Riesgo Metabólico")
                st.plotly_chart(fig_radar, use_container_width=True)
            
            with g2:
                # Gráfico de Barras de Estilo de Vida
                fig_life = px.bar(
                    x=["Sueño (Meta 8h)", "Ejercicio (Meta 150m)"], 
                    y=[sleep, exer/18.75], # Normalizado a escala 8
                    title="Balance de Estilo de Vida",
                    color_discrete_sequence=[st.session_state.get('spec') == 'nefrologia' and '#0066cc' or '#e63946']
                )
                st.plotly_chart(fig_life, use_container_width=True)

            # Botón de descarga corregido (FUERA DEL FORM)
            p_data = {"id": f_id, "name": f_name, "plan": plan, "obs": observations}
            pdf_buf = export_pdf(p_data, st.session_state.get('name'))
            st.download_button("📥 DESCARGAR REPORTE PARA PACIENTE", pdf_buf.getvalue(), f"Reporte_{f_name}.pdf", "application/pdf", use_container_width=True)
        else:
            st.error("Nombre e ID son obligatorios.")

elif menu == "📅 Historial Clínico":
    st.header("Seguimiento Longitudinal")
    h_name = st.text_input("Buscar por Nombre")
    if h_name:
        df = pd.read_sql(f"SELECT * FROM records WHERE px_name LIKE '%{h_name}%' ORDER BY date ASC", db.conn)
        if not df.empty:
            st.write(f"### Evolución de {h_name}")
            fig_evol = px.line(df, x="date", y=["weight", "tfg"], markers=True, title="Tendencia de Peso y Función Renal")
            st.plotly_chart(fig_evol, use_container_width=True)
            st.dataframe(df)
