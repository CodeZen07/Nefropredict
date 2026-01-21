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
    recom = {"dieta": [], "estilo": [], "clinico": [], "seguimiento": []}
    alertas = []
    
    tfg = d.get('tfg', 90)
    if tfg < 30:
        recom['clinico'].append("⚠️ ERC G4-G5: Derivar a nefrología.")
        alertas.append("CRÍTICO: TFG <30 ml/min")
    elif tfg < 60:
        recom['clinico'].append("ERC G3: Iniciar/optimizar IECA/ARA-II + SGLT2i.")
    
    potasio = d.get('potasio', 4.0)
    if potasio > 5.5:
        recom['dieta'].append("🔴 HIPERPOTASEMIA: Dieta estricta baja en K+.")
        alertas.append("URGENTE: K+ >5.5 mEq/L")
    
    fevi = d.get('fevi', 55)
    if fevi < 40:
        recom['clinico'].append("🫀 IC-FEr: Terapia cuádruple GDMT.")
        alertas.append("Insuficiencia Cardíaca FEr <40%")
        
    return recom, alertas

def crear_pdf(datos, recoms, alertas, medico):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, "REPORTE MÉDICO CARDIORRENAL", ln=True, align='C')
    pdf.ln(5)
    pdf.set_font("Arial", '', 11)
    pdf.cell(0, 10, f"Paciente: {datos['px_name']} | ID: {datos['px_id']}", ln=True)
    pdf.cell(0, 10, f"Médico: Dr. {medico} | Fecha: {datetime.now().strftime('%d/%m/%Y')}", ln=True)
    pdf.ln(5)
    return pdf.output(dest='S').encode('latin-1')

# =============================================
# 3. INTERFAZ DE USUARIO
# =============================================
if "auth" not in st.session_state: st.session_state.auth = False
if "analisis_listo" not in st.session_state: st.session_state.analisis_listo = False

if not st.session_state.auth:
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.title("🏥 NefroCardio SaaS")
        u = st.text_input("👤 Usuario")
        p = st.text_input("🔒 Contraseña", type="password")
        if st.button("🚀 Acceder", use_container_width=True):
            res = db.conn.execute("SELECT password, name, role FROM users WHERE username=? AND active=1", (u,)).fetchone()
            if res and bcrypt.checkpw(p.encode(), res[0].encode()):
                st.session_state.update({"auth":True, "name":res[1], "role":res[2], "username":u})
                db.log_action(u, "Login", "Acceso exitoso")
                st.rerun()
            else: st.error("❌ Credenciales inválidas")
    st.stop()

# SIDEBAR
st.sidebar.markdown(f"### 👨‍⚕️ Dr. {st.session_state.name}")
menu = st.sidebar.radio("📋 Menú Principal", ["🔬 Nueva Consulta", "📂 Historial", "⚙️ Panel Admin"])

if st.sidebar.button("🚪 Cerrar Sesión"):
    st.session_state.clear()
    st.rerun()

# --- SECCIÓN: NUEVA CONSULTA ---
if menu == "🔬 Nueva Consulta":
    st.title("🔬 Nueva Evaluación")
    with st.form("consulta_form"):
        c1, c2 = st.columns(2); px_name = c1.text_input("Nombre Paciente"); px_id = c2.text_input("ID")
        col1, col2, col3, col4 = st.columns(4)
        sys_p = col1.number_input("Sistólica", 80, 220, 120)
        tfg_v = col2.number_input("TFG", 0.0, 150.0, 90.0)
        pot_v = col3.number_input("K+", 2.0, 8.0, 4.0)
        fevi_v = col4.number_input("FEVI", 5.0, 80.0, 55.0)
        sleep_v = st.slider("Sueño", 3.0, 12.0, 7.0)
        stress_v = st.selectbox("Estrés", ["Bajo", "Moderado", "Alto"])
        exercise_v = st.number_input("Ejercicio (min/sem)", 0, 500, 150)
        obs_v = st.text_area("Notas")
        submitted = st.form_submit_button("🔍 ANALIZAR")

    if submitted:
        datos = {"px_name": px_name, "px_id": px_id, "tfg": tfg_v, "potasio": pot_v, "fevi": fevi_v, "sleep": sleep_v, "stress": stress_v, "sys": sys_p, "exercise": exercise_v}
        recoms, alertas = generar_plan_cientifico(datos)
        st.session_state.update({"recoms": recoms, "alertas": alertas, "datos_recientes": datos, "analisis_listo": True})
        db.conn.execute("INSERT INTO clinical_records (px_name, px_id, date, doctor, sys, tfg, potasio, fevi, sleep, stress, exercise, obs) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                        (px_name, px_id, datetime.now().strftime("%Y-%m-%d"), st.session_state.name, sys_p, tfg_v, pot_v, fevi_v, sleep_v, stress_v, exercise_v, obs_v))
        db.conn.commit()
        st.rerun()

    if st.session_state.analisis_listo:
        d = st.session_state.datos_recientes
        st.divider()
        col_g1, col_g2 = st.columns(2)
        with col_g1:
            fig_tfg = go.Figure(go.Indicator(mode="gauge+number", value=d['tfg'], title={'text': "TFG"},
                gauge={'axis': {'range': [0, 120]}, 'steps': [
                    {'range': [0, 15], 'color': "#8B0000"}, {'range': [15, 30], 'color': "#FF4500"},
                    {'range': [30, 45], 'color': "#FFA500"}, {'range': [45, 60], 'color': "#FFD700"}, # <-- CORREGIDO AQUÍ
                    {'range': [60, 90], 'color': "#90EE90"}, {'range': [90, 120], 'color': "#32CD32"}
                ]}))
            st.plotly_chart(fig_tfg, use_container_width=True)
        
        

[Image of chronic kidney disease stages chart]

        
        with col_g2:
            st.write("### Recomendaciones")
            for k, v in st.session_state.recoms.items():
                if v: st.write(f"**{k.upper()}:** {', '.join(v)}")
        
        pdf_bytes = crear_pdf(d, st.session_state.recoms, st.session_state.alertas, st.session_state.name)
        st.download_button("⬇️ Descargar PDF", data=pdf_bytes, file_name="Reporte.pdf", mime="application/pdf")

# --- SECCIÓN: PANEL ADMIN ---
elif menu == "⚙️ Panel Admin":
    if st.session_state.role != 'admin': st.error("Acceso Denegado")
    else:
        st.title("⚙️ Administración")
        t1, t2 = st.tabs(["👥 Usuarios", "📊 Logs"])
        with t1:
            df_u = pd.read_sql("SELECT username, name, role, active FROM users", db.conn)
            st.dataframe(df_u, use_container_width=True)
            with st.form("new_user"):
                st.subheader("Nuevo Usuario")
                nu = st.text_input("Usuario"); nn = st.text_input("Nombre"); np = st.text_input("Clave", type="password")
                nr = st.selectbox("Rol", ["medico", "admin"])
                if st.form_submit_button("Crear"):
                    hp = bcrypt.hashpw(np.encode(), bcrypt.gensalt()).decode()
                    db.conn.execute("INSERT INTO users (username, password, name, role, created_date) VALUES (?,?,?,?,?)",
                                   (nu, hp, nn, nr, datetime.now().strftime("%Y-%m-%d")))
                    db.conn.commit()
                    st.success("Usuario creado")
        with t2:
            df_l = pd.read_sql("SELECT * FROM audit_logs ORDER BY id DESC", db.conn)
            st.dataframe(df_l, use_container_width=True)

# --- SECCIÓN: HISTORIAL ---
elif menu == "📂 Historial":
    st.title("📂 Historial")
    df_h = pd.read_sql("SELECT * FROM clinical_records", db.conn)
    st.dataframe(df_h, use_container_width=True)
