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
# 2. MOTOR DE RECOMENDACIONES Y PDF
# =============================================
def generar_plan_cientifico(d):
    recom = {"dieta": [], "estilo": [], "clinico": []}
    # Uso de .get() para evitar KeyError
    if d.get('tfg', 90) < 60: recom['clinico'].append("Priorizar IECA/ARA-II y SGLT2i según KDIGO.")
    if d.get('potasio', 4.0) > 5.2: recom['dieta'].append("URGENTE: Dieta baja en potasio (evitar cítricos/tomate/guineo).")
    if d.get('fevi', 55) < 40: recom['clinico'].append("IC: Optimizar terapia cuádruple (ARNI/BB/MRA/SGLT2i).")
    if d.get('sleep', 7) < 7: recom['estilo'].append("Higiene de sueño: Meta 7-8h para regular eje RAA.")
    if d.get('stress') == "Alto": recom['estilo'].append("Gestión de estrés: Mindfulness para reducir tono simpático.")
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
    pdf.cell(200, 10, "RESULTADOS: TFG: " + str(datos['tfg']) + " | K+: " + str(datos['potasio']) + " | FEVI: " + str(datos['fevi']) + "%", ln=True)
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(200, 10, "RECOMENDACIONES:", ln=True)
    pdf.set_font("Arial", '', 10)
    for cat, items in recoms.items():
        if items:
            pdf.cell(200, 7, f"{cat.upper()}:", ln=True)
            for i in items:
                pdf.multi_cell(0, 7, f"* {i}")
    return pdf.output()

# =============================================
# 3. INTERFAZ DE USUARIO
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
            else: st.error("Error de credenciales")
    st.stop()

st.sidebar.title(f"Dr. {st.session_state.name}")
menu = st.sidebar.radio("Menú", ["Nueva Consulta", "Historial", "Panel Admin"])

# --- SECCIÓN: NUEVA CONSULTA ---
if menu == "Nueva Consulta":
    st.header("🔬 Evaluación Cardiorrenal")
    with st.form("consulta_form"):
        c1, c2, c3 = st.columns(3)
        px_name = c1.text_input("Nombre Paciente")
        px_id = c2.text_input("ID")
        sys_p = c3.number_input("Presión Sistólica", 80, 220, 120)
        n1, n2, n3 = st.columns(3)
        tfg_v = n1.number_input("TFG (ml/min)", 0.0, 150.0, 90.0)
        pot_v = n2.number_input("Potasio (K+)", 2.0, 8.0, 4.0)
        fevi_v = n3.number_input("FEVI (%)", 5.0, 80.0, 55.0)
        sleep_v = st.slider("Horas Sueño", 3.0, 12.0, 7.5)
        stress_v = st.selectbox("Estrés", ["Bajo", "Moderado", "Alto"])
        obs_v = st.text_area("Observaciones")
        btn = st.form_submit_button("ANALIZAR Y GUARDAR")

    if btn:
        datos_enviados = {"px_name": px_name, "px_id": px_id, "tfg": tfg_v, "potasio": pot_v, "fevi": fevi_v, "sleep": sleep_v, "stress": stress_v, "sys": sys_p}
        st.session_state.recoms = generar_plan_cientifico(datos_enviados)
        st.session_state.datos_recientes = datos_enviados
        st.session_state.analisis_listo = True
        
        db.conn.execute("INSERT INTO clinical_records (px_name, px_id, date, doctor, sys, tfg, potasio, fevi, sleep, stress, obs) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                        (px_name, px_id, datetime.now().strftime("%Y-%m-%d"), st.session_state.name, sys_p, tfg_v, pot_v, fevi_v, sleep_v, stress_v, obs_v))
        db.log_action(st.session_state.username, "Consulta", f"Consulta creada para {px_name}")

    if st.session_state.analisis_listo:
        d = st.session_state.datos_recientes
        r = st.session_state.recoms
        
        st.divider()
        col_g1, col_g2 = st.columns(2)
        with col_g1:
            fig_tfg = go.Figure(go.Indicator(mode="gauge+number", value=d['tfg'], title={'text': "Función Renal (TFG)"},
                gauge={'axis': {'range': [0, 120]}, 'steps': [{'range': [0, 30], 'color': "red"}, {'range': [30, 60], 'color': "orange"}, {'range': [60, 120], 'color': "green"}]}))
            st.plotly_chart(fig_tfg, use_container_width=True)
        with col_g2:
            fechas = ["Hoy", "+2 meses", "+4 meses", "+6 meses"]
            progreso = [d['tfg'], d['tfg']*1.02, d['tfg']*1.05, d['tfg']*1.08]
            fig_trend = go.Figure()
            fig_trend.add_trace(go.Scatter(x=fechas, y=progreso, mode='lines+markers', name="TFG Proyectada"))
            simbolo = "↑" if progreso[-1] > progreso[0] else "↓"
            fig_trend.add_annotation(x=fechas[-1], y=progreso[-1], text=f"Tendencia {simbolo}", showarrow=True, arrowhead=2)
            st.plotly_chart(fig_trend, use_container_width=True)

        

[Image of chronic kidney disease stages chart]


        c_pdf, c_rec = st.columns([1, 2])
        with c_pdf:
            st.info("### Reporte")
            pdf_data = crear_pdf(d, r, st.session_state.name)
            st.download_button("Descargar PDF", data=pdf_data, file_name=f"Reporte_{d['px_id']}.pdf", mime="application/pdf")
        with c_rec:
            st.info("### Guía Científica")
            for cat, items in r.items():
                if items: st.write(f"**{cat.capitalize()}:** {', '.join(items)}")

# --- SECCIÓN: PANEL ADMIN ---
elif menu == "Panel Admin":
    if st.session_state.role != 'admin': st.error("No tienes permisos")
    else:
        st.header("🔑 Administración y Auditoría")
        t1, t2 = st.tabs(["Auditoría de Logs", "Gestión de Usuarios"])
        with t1:
            df_logs = pd.read_sql("SELECT * FROM audit_logs ORDER BY id DESC", db.conn)
            st.dataframe(df_logs, use_container_width=True)
        with t2:
            with st.form("add_user"):
                new_u = st.text_input("Usuario"); new_n = st.text_input("Nombre"); new_p = st.text_input("Clave", type="password")
                new_r = st.selectbox("Rol", ["medico", "admin"])
                if st.form_submit_button("Crear"):
                    hash_p = bcrypt.hashpw(new_p.encode(), bcrypt.gensalt()).decode()
                    db.conn.execute("INSERT INTO users (username, password, name, role) VALUES (?,?,?,?)", (new_u, hash_p, new_n, new_r))
                    db.conn.commit()
                    st.success("Usuario registrado")

# --- SECCIÓN: HISTORIAL ---
elif menu == "Historial":
    st.header("📂 Historial de Pacientes")
    h_px = st.text_input("Nombre del paciente")
    if h_px:
        df_h = pd.read_sql(f"SELECT * FROM clinical_records WHERE px_name LIKE '%{h_px}%'", db.conn)
        st.dataframe(df_h)
        if not df_h.empty:
            st.plotly_chart(px.line(df_h, x="date", y=["tfg", "fevi"], title="Evolución Histórica"))

st.markdown("---")
st.warning("⚠️ **AVISO:** Este sistema es apoyo clínico. No sustituye la opinión profesional. Basado en guías KDIGO/AHA.")
