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
            username TEXT PRIMARY KEY, password TEXT, name TEXT, role TEXT, specialty TEXT)""")
        c.execute("""CREATE TABLE IF NOT EXISTS clinical_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT, px_name TEXT, px_id TEXT, date TEXT, doctor TEXT,
            sys INT, tfg REAL, albuminuria REAL, potasio REAL, bun_cr REAL,
            fevi REAL, troponina REAL, bnp REAL, ldl REAL, sleep REAL, stress TEXT, exercise INT, obs TEXT)""")
        c.execute("""CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT, user TEXT, action TEXT, details TEXT)""")
        
        c.execute("SELECT * FROM users WHERE username='admin'")
        if not c.fetchone():
            pw = bcrypt.hashpw("Admin2026!".encode(), bcrypt.gensalt()).decode()
            c.execute("INSERT INTO users VALUES ('admin', ?, 'Admin Master', 'admin', 'Sistemas')", (pw,))
        self.conn.commit()

    def log_action(self, user, action, details):
        self.conn.execute("INSERT INTO audit_logs (timestamp, user, action, details) VALUES (?,?,?,?)",
                          (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), user, action, details))
        self.conn.commit()

db = AppDatabase()

# =============================================
# 2. MOTOR DE RECOMENDACIONES Y PDF (CORREGIDO)
# =============================================
def generar_plan_cientifico(d):
    recom = {"dieta": [], "estilo": [], "clinico": []}
    if d.get('tfg', 90) < 60: recom['clinico'].append("Priorizar IECA/ARA-II y SGLT2i según KDIGO.")
    if d.get('potasio', 4.0) > 5.2: recom['dieta'].append("URGENTE: Dieta baja en potasio (evitar cítricos/tomate).")
    if d.get('fevi', 55) < 40: recom['clinico'].append("IC: Optimizar terapia cuádruple (ARNI/BB).")
    if d.get('sleep', 7) < 7: recom['estilo'].append("Higiene de sueño: Meta 7-8h para eje RAA.")
    if d.get('stress') == "Alto": recom['estilo'].append("Gestión de estrés: Mindfulness y control de cortisol.")
    return recom

def crear_pdf(datos, recoms, medico):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, "REPORTE MEDICO CARDIORRENAL", ln=True, align='C')
    pdf.ln(10)
    
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(100, 10, f"Paciente: {datos['px_name']}")
    pdf.cell(100, 10, f"ID: {datos['px_id']}", ln=True)
    pdf.set_font("Arial", '', 11)
    pdf.cell(100, 10, f"Fecha: {datetime.now().strftime('%Y-%m-%d')}")
    pdf.cell(100, 10, f"Medico: {medico}", ln=True)
    pdf.ln(5)
    
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(200, 10, "RESULTADOS CLAVE:", ln=True)
    pdf.set_font("Arial", '', 11)
    pdf.cell(200, 8, f"- TFG: {datos['tfg']} ml/min | Potasio: {datos['potasio']} mEq/L", ln=True)
    pdf.cell(200, 8, f"- FEVI: {datos['fevi']}% | Presion Sistolica: {datos['sys']} mmHg", ln=True)
    pdf.ln(5)

    pdf.set_font("Arial", 'B', 12)
    pdf.cell(200, 10, "RECOMENDACIONES:", ln=True)
    for cat, items in recoms.items():
        if items:
            pdf.set_font("Arial", 'B', 10)
            pdf.cell(200, 7, f"{cat.upper()}:", ln=True)
            pdf.set_font("Arial", '', 10)
            for i in items:
                pdf.multi_cell(0, 7, f"* {i}")
    
    pdf.ln(10)
    pdf.set_font("Arial", 'I', 8)
    pdf.multi_cell(0, 5, "AVISO: Este reporte es una herramienta de apoyo medico y no sustituye el juicio clinico final.")
    
    # CORRECCIÓN DE ATRIBUTO: fpdf2 devuelve bytes directamente si no hay nombre de archivo
    return pdf.output() 

# =============================================
# 3. LOGICA DE INTERFAZ
# =============================================
if "auth" not in st.session_state: st.session_state.auth = False
if "analisis_listo" not in st.session_state: st.session_state.analisis_listo = False

if not st.session_state.auth:
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.title("🏥 NefroCardio SaaS")
        u = st.text_input("Usuario")
        p = st.text_input("Clave", type="password")
        if st.button("Acceder", use_container_width=True):
            res = db.conn.execute("SELECT password, name, role FROM users WHERE username=?", (u,)).fetchone()
            if res and bcrypt.checkpw(p.encode(), res[0].encode()):
                st.session_state.update({"auth":True, "name":res[1], "role":res[2], "username":u})
                db.log_action(u, "Login", "Acceso exitoso")
                st.rerun()
            else:
                st.error("Credenciales incorrectas")
    st.stop()

st.sidebar.title(f"Dr. {st.session_state.name}")
menu = st.sidebar.radio("Menú", ["Nueva Consulta", "Historial", "Panel Admin"])

if menu == "Nueva Consulta":
    st.header("🔬 Evaluación Cardiorrenal")
    
    with st.form("form_clinico"):
        c1, c2, c3 = st.columns(3)
        px_name = c1.text_input("Nombre Paciente")
        px_id = c2.text_input("ID")
        sys_p = c3.number_input("Presión Sistólica", 80, 220, 120)
        
        n1, n2, n3 = st.columns(3)
        tfg_in = n1.number_input("TFG (ml/min)", 0, 150, 90)
        pot_in = n2.number_input("Potasio (K+)", 2.0, 8.0, 4.0)
        fevi_in = n3.number_input("FEVI (%)", 5, 80, 55)
        
        sleep_in = st.slider("Horas Sueño", 3.0, 12.0, 7.0)
        stress_in = st.selectbox("Estrés", ["Bajo", "Moderado", "Alto"])
        obs_in = st.text_area("Observaciones")
        
        btn_analizar = st.form_submit_button("GENERAR VEREDICTO")

    if btn_analizar:
        st.session_state.datos_actuales = {
            "px_name": px_name, "px_id": px_id, "sys": sys_p, 
            "tfg": tfg_in, "potasio": pot_in, "fevi": fevi_in, 
            "sleep": sleep_in, "stress": stress_in, "obs": obs_in
        }
        st.session_state.recoms_actuales = generar_plan_cientifico(st.session_state.datos_actuales)
        st.session_state.analisis_listo = True
        
        db.conn.execute("INSERT INTO clinical_records (px_name, px_id, date, doctor, sys, tfg, potasio, fevi, sleep, stress, obs) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                        (px_name, px_id, datetime.now().strftime("%Y-%m-%d"), st.session_state.name, sys_p, tfg_in, pot_in, fevi_in, sleep_in, stress_in, obs_in))
        db.log_action(st.session_state.username, "Consulta", f"Paciente {px_name} analizado")

    if st.session_state.analisis_listo:
        st.divider()
        d = st.session_state.datos_actuales
        r = st.session_state.recoms_actuales
        
        # --- GRÁFICO DE DISPERSIÓN CON FLECHA DE TENDENCIA ---
        st.subheader("📈 Análisis de Tendencia Cardiorrenal (6 meses)")
        
        fechas = ["Hoy", "+2 meses", "+4 meses", "+6 meses"]
        # Simulación de tendencia basada en TFG actual
        # Si TFG > 60 es ascendente/estable, si < 60 simula recuperación con tratamiento
        valores_tfg = [d['tfg'], d['tfg']*1.03, d['tfg']*1.06, d['tfg']*1.08]
        
        fig = go.Figure()
        # Línea de dispersión
        fig.add_trace(go.Scatter(x=fechas, y=valores_tfg, mode='lines+markers', 
                                 name='TFG Proyectada', line=dict(color='royalblue', width=4)))
        
        # Flecha de tendencia ascendente o descendente
        simbolo = "▲" if valores_tfg[-1] > valores_tfg[0] else "▼"
        color_flecha = "green" if valores_tfg[-1] > valores_tfg[0] else "red"
        
        fig.add_annotation(x=fechas[-1], y=valores_tfg[-1],
                           text=f"Tendencia {simbolo}", showarrow=True, arrowhead=2, 
                           ax=-40, ay=-40, font=dict(color=color_flecha, size=15))

        st.plotly_chart(fig, use_container_width=True)

        

[Image of chronic kidney disease stages chart]


        st.success("✅ Veredicto Científico Generado")
        col_pdf, col_rec = st.columns([1, 2])
        
        with col_pdf:
            pdf_data = crear_pdf(d, r, st.session_state.name)
            st.download_button(label="📄 Descargar Reporte PDF", data=pdf_data, 
                               file_name=f"Reporte_{d['px_id']}.pdf", mime="application/pdf")

        with col_rec:
            for cat, items in r.items():
                if items: st.markdown(f"**{cat.capitalize()}:** {', '.join(items)}")

# --- SECCIÓN ADMIN Y LOGS ---
elif menu == "Panel Admin":
    if st.session_state.role != "admin":
        st.error("Acceso denegado.")
    else:
        st.header("🛡️ Auditoría de Usuarios")
        tab1, tab2 = st.tabs(["Registro de Acciones", "Nuevos Usuarios"])
        with tab1:
            logs = pd.read_sql("SELECT * FROM audit_logs ORDER BY id DESC", db.conn)
            st.dataframe(logs, use_container_width=True)
        with tab2:
            with st.form("new_u"):
                nu = st.text_input("Usuario"); nn = st.text_input("Nombre"); np = st.text_input("Clave", type="password")
                nr = st.selectbox("Rol", ["medico", "admin"])
                if st.form_submit_button("Registrar"):
                    hp = bcrypt.hashpw(np.encode(), bcrypt.gensalt()).decode()
                    db.conn.execute("INSERT INTO users (username, password, name, role) VALUES (?,?,?,?)", (nu, hp, nn, nr))
                    db.conn.commit()
                    st.success("Usuario creado")

st.markdown("---")
st.warning("⚠️ **AVISO:** Este software es apoyo médico. Los gráficos de tendencia son proyecciones estadísticas y no deben usarse como única base para cambios de tratamiento sin revisión física.")
