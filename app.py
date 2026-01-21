import pandas as pd
import sqlite3
import bcrypt
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
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
        
        # Admin por defecto
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
# 2. FUNCIONES DE APOYO (PDF Y PREDICCIÓN)
# =============================================
def generar_pdf_reporte(datos, recoms, medico):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, "REPORTE MÉDICO CARDIORRENAL", ln=True, align='C')
    
    pdf.set_font("Arial", size=10)
    pdf.cell(200, 10, f"Fecha: {datetime.now().strftime('%d/%m/%Y')} | Médico: {medico}", ln=True)
    pdf.line(10, 30, 200, 30)
    
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(200, 10, f"Paciente: {datos['px_name']} (ID: {datos['px_id']})", ln=True)
    
    pdf.set_font("Arial", size=11)
    pdf.multi_cell(0, 10, f"Veredicto Clínico:\n- TFG: {datos['tfg']} ml/min\n- Potasio: {datos['potasio']} mEq/L\n- FEVI: {datos['fevi']}%")
    
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(200, 10, "RECOMENDACIONES CIENTÍFICAS:", ln=True)
    pdf.set_font("Arial", size=10)
    for cat, items in recoms.items():
        pdf.set_font("Arial", 'B', 10)
        pdf.cell(200, 7, f"{cat.upper()}:", ln=True)
        pdf.set_font("Arial", size=10)
        for item in items:
            pdf.multi_cell(0, 7, f"* {item}")
            
    pdf.ln(10)
    pdf.set_font("Arial", 'I', 8)
    pdf.multi_cell(0, 5, "AVISO LEGAL: Este documento es un apoyo clínico y no sustituye el juicio final del profesional de salud.")
    
    return pdf.output(dest='S').encode('latin-1')

def generar_plan_cientifico(d):
    recom = {"dieta": [], "estilo": [], "clinico": []}
    if d.get('tfg', 90) < 60: recom['clinico'].append("Priorizar IECA/ARA-II y SGLT2i.")
    if d.get('potasio', 4.0) > 5.2: recom['dieta'].append("URGENTE: Restringir potasio (frutos secos, cítricos).")
    if d.get('fevi', 55) < 40: recom['clinico'].append("Insuficiencia Cardiaca: Optimizar terapia cuádruple.")
    if d.get('sleep', 7) < 7: recom['estilo'].append("Higiene de sueño: Meta 7-8h para equilibrio metabólico.")
    if d.get('stress') == "Alto": recom['estilo'].append("Manejo de cortisol: Mindfulness y actividad física ligera.")
    return recom

# =============================================
# 3. INTERFAZ Y LÓGICA
# =============================================
if "auth" not in st.session_state: st.session_state.auth = False

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
                db.log_action(u, "Login", "Acceso exitoso al sistema")
                st.rerun()
    st.stop()

st.sidebar.title(f"Bienvenido: {st.session_state.name}")
menu = st.sidebar.radio("Menú", ["Nueva Consulta", "Historial", "Panel Admin" if st.session_state.role == 'admin' else None])

# --- NUEVA CONSULTA ---
if menu == "Nueva Consulta":
    st.header("🔬 Evaluación Cardiorrenal Integral")
    with st.form("consulta_form"):
        c1, c2, c3 = st.columns(3)
        px_name = c1.text_input("Nombre Paciente")
        px_id = c2.text_input("ID/Cédula")
        sys_p = c3.number_input("Presión Sistólica", 80, 200, 120)
        
        n1, n2, n3 = st.columns(3)
        tfg = n1.number_input("TFG (ml/min)", 0, 150, 90)
        pot = n2.number_input("Potasio", 2.0, 8.0, 4.0)
        fevi = n3.number_input("FEVI (%)", 5, 80, 55)
        
        e1, e2 = st.columns(2)
        sleep = e1.slider("Horas Sueño", 3.0, 12.0, 7.0)
        stress = e2.selectbox("Nivel Estrés", ["Bajo", "Moderado", "Alto"])
        obs = st.text_area("Notas Clínicas")
        
        submit = st.form_submit_button("ANALIZAR Y GENERAR REPORTE")

    if submit:
        datos = {"tfg": tfg, "potasio": pot, "fevi": fevi, "sleep": sleep, "stress": stress, "px_name": px_name, "px_id": px_id}
        recoms = generar_plan_cientifico(datos)
        
        # Guardar Registro
        db.conn.execute("INSERT INTO clinical_records (px_name, px_id, date, doctor, sys, tfg, potasio, fevi, sleep, stress, obs) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                        (px_name, px_id, datetime.now().strftime("%Y-%m-%d"), st.session_state.name, sys_p, tfg, pot, fevi, sleep, stress, obs))
        db.log_action(st.session_state.username, "Consulta", f"Nueva consulta para {px_name}")
        
        # Dashboard de resultados
        st.subheader("📊 Predicción de Evolución (Próximos 6 meses)")
        # Lógica de predicción simple basada en tendencia (Mejorable con ML)
        meses = ["Hoy", "+2 meses", "+4 meses", "+6 meses (Control)"]
        valores_tfg = [tfg, tfg*1.02 if tfg < 90 else tfg, tfg*1.04 if tfg < 90 else tfg, tfg*1.05 if tfg < 90 else tfg]
        
        fig = px.area(x=meses, y=valores_tfg, title="Trayectoria Esperada de TFG con Tratamiento")
        st.plotly_chart(fig)
        
        st.info("### 🧬 Recomendaciones Personalizadas")
        for cat, val in recoms.items(): st.write(f"**{cat.capitalize()}:** {', '.join(val)}")
        
        # PDF
        pdf_bytes = generar_pdf_reporte(datos, recoms, st.session_state.name)
        st.download_button("📥 Descargar Reporte PDF", data=pdf_bytes, file_name=f"Reporte_{px_id}.pdf", mime="application/pdf")

# --- PANEL ADMIN ---
elif menu == "Panel Admin":
    st.header("🔑 Panel de Administración y Auditoría")
    tab1, tab2 = st.tabs(["Auditoría de Sistema", "Gestión de Usuarios"])
    
    with tab1:
        st.subheader("Logs de Actividad")
        logs = pd.read_sql("SELECT * FROM audit_logs ORDER BY id DESC", db.conn)
        st.dataframe(logs, use_container_width=True)
    
    with tab2:
        st.subheader("Registrar Nuevo Médico")
        with st.form("new_user"):
            new_u = st.text_input("Usuario")
            new_n = st.text_input("Nombre Completo")
            new_p = st.text_input("Clave", type="password")
            new_r = st.selectbox("Rol", ["medico", "admin"])
            if st.form_submit_button("Crear Usuario"):
                hash_p = bcrypt.hashpw(new_p.encode(), bcrypt.gensalt()).decode()
                try:
                    db.conn.execute("INSERT INTO users (username, password, name, role) VALUES (?,?,?,?)", (new_u, hash_p, new_n, new_r))
                    db.conn.commit()
                    st.success("Usuario creado")
                except: st.error("El usuario ya existe")

# --- FOOTER LEGAL ---
st.markdown("---")
st.caption("⚠️ **AVISO DE APOYO MÉDICO:** Esta aplicación es una herramienta de soporte basada en guías clínicas (KDIGO/AHA). Los resultados y predicciones son sugerencias y **no sustituyen la opinión, diagnóstico o veredicto de un profesional de la salud calificado.**")
