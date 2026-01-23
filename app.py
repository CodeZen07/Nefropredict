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
# 1. CONFIGURACIÓN Y BASE DE DATOS (INTEGRA)
# =============================================
st.set_page_config(page_title="NefroCardio Pro SaaS", page_icon="⚖️", layout="wide")

class AppDatabase:
    def __init__(self):
        self.conn = sqlite3.connect("nefrocardio_v2026.db", check_same_thread=False)
        self.init_db()

    def init_db(self):
        c = self.conn.cursor()
        c.execute("""CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY, password TEXT, name TEXT, role TEXT, 
            specialty TEXT, active INTEGER DEFAULT 1, created_date TEXT)""")
        
        # Migraciones de seguridad y metadatos
        try: c.execute("SELECT active FROM users LIMIT 1")
        except sqlite3.OperationalError: c.execute("ALTER TABLE users ADD COLUMN active INTEGER DEFAULT 1")
        
        try: c.execute("SELECT created_date FROM users LIMIT 1")
        except sqlite3.OperationalError:
            c.execute("ALTER TABLE users ADD COLUMN created_date TEXT")
            c.execute("UPDATE users SET created_date = ? WHERE created_date IS NULL", (datetime.now().strftime("%Y-%m-%d"),))
        
        c.execute("""CREATE TABLE IF NOT EXISTS clinical_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT, px_name TEXT, px_id TEXT, date TEXT, doctor TEXT,
            sys INT, tfg REAL, albuminuria REAL, potasio REAL, fevi REAL, sleep REAL, 
            stress TEXT, exercise INT, obs TEXT)""")
        
        c.execute("""CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT, user TEXT, action TEXT, details TEXT)""")
        
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
# 2. MOTOR CIENTÍFICO (KDIGO / AHA)
# =============================================
def generar_plan_cientifico(d):
    recom = {"dieta": [], "estilo": [], "clinico": [], "seguimiento": []}
    alertas = []
    
    # Lógica Renal
    if d['tfg'] < 30:
        recom['clinico'].append("⚠️ ERC G4-G5: Derivar a nefrología urgentemente.")
        alertas.append("CRÍTICO: TFG <30 ml/min")
    elif d['tfg'] < 60:
        recom['clinico'].append("ERC G3: Optimizar IECA/ARA-II + iSGLT2.")
    
    # Lógica Cardiaca
    if d['fevi'] < 40:
        recom['clinico'].append("🫀 IC-FEr: Iniciar terapia cuádruple (GDMT).")
        alertas.append("FEVI REDUCIDA <40%")
        
    # Estilo de Vida
    if d['exercise'] < 150:
        recom['estilo'].append(f"Actividad física insuficiente ({d['exercise']} min). Meta: 150 min/sem.")
    
    return recom, alertas

# =============================================
# 3. PDF ENGINE (LATIN-1 SAFE)
# =============================================
def crear_pdf(datos, recoms, alertas, medico):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, "INFORME CLINICO ESPECIALIZADO", ln=True, align='C')
    pdf.ln(5)
    
    pdf.set_font("Arial", '', 10)
    pdf.cell(0, 8, f"Paciente: {datos['px_name']} | ID: {datos['px_id']}", ln=True)
    pdf.cell(0, 8, f"Fecha: {datetime.now().strftime('%d/%m/%Y')} | Medico: {medico}", ln=True)
    pdf.ln(5)
    
    # Datos en tabla simple
    pdf.set_fill_color(230, 230, 230)
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(45, 8, "TFG", 1, 0, 'C', True)
    pdf.cell(45, 8, "FEVI", 1, 0, 'C', True)
    pdf.cell(45, 8, "Presion", 1, 0, 'C', True)
    pdf.cell(45, 8, "Potasio", 1, 1, 'C', True)
    
    pdf.set_font("Arial", '', 10)
    pdf.cell(45, 8, f"{datos['tfg']}", 1, 0, 'C')
    pdf.cell(45, 8, f"{datos['fevi']}%", 1, 0, 'C')
    pdf.cell(45, 8, f"{datos['sys']}", 1, 0, 'C')
    pdf.cell(45, 8, f"{datos['potasio']}", 1, 1, 'C')
    
    pdf.ln(10)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, "PLAN DE ACCION:", ln=True)
    pdf.set_font("Arial", '', 10)
    for cat in recoms:
        for item in recoms[cat]:
            pdf.multi_cell(0, 6, f"* {item}")

    # Manejo de caracteres para latin-1
    return pdf.output(dest='S').encode('latin-1', 'ignore')

# =============================================
# 4. INTERFAZ Y LOGICA DE SESIÓN
# =============================================
if "auth" not in st.session_state: st.session_state.auth = False

if not st.session_state.auth:
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.title("🏥 NefroCardio Pro")
        u = st.text_input("Usuario")
        p = st.text_input("Contraseña", type="password")
        if st.button("Ingresar", use_container_width=True, type="primary"):
            res = db.conn.execute("SELECT password, name, role FROM users WHERE username=?", (u,)).fetchone()
            if res and bcrypt.checkpw(p.encode(), res[0].encode()):
                st.session_state.update({"auth": True, "name": res[1], "username": u, "role": res[2]})
                db.log_action(u, "Login", "Acceso exitoso")
                st.rerun()
            else:
                st.error("Error de credenciales")
    st.stop()

# --- DASHBOARD PRINCIPAL ---
st.sidebar.title(f"Dr. {st.session_state.name}")
opcion = st.sidebar.radio("Navegación", ["Nueva Consulta", "Historial Clínico"])

if opcion == "Nueva Consulta":
    with st.container(border=True):
        st.subheader("Datos de Evaluación")
        c1, c2, c3 = st.columns(3)
        px_n = c1.text_input("Nombre")
        px_i = c2.text_input("ID")
        sys_p = c3.number_input("Sistólica", 80, 200, 120)
        
        c4, c5, c6 = st.columns(3)
        tfg_p = c4.number_input("TFG", 0, 150, 70)
        fevi_p = c5.number_input("FEVI %", 10, 80, 55)
        pot_p = c6.number_input("K+", 2.0, 7.0, 4.0)
        
        st.divider()
        st.caption("Estilo de Vida")
        e1, e2, e3 = st.columns(3)
        sleep_p = e1.slider("Sueño", 4, 12, 7)
        stress_p = e2.selectbox("Estrés", ["Bajo", "Moderado", "Alto"])
        exe_p = e3.number_input("Ejercicio (min/sem)", 0, 600, 150)
        
        if st.button("EJECUTAR ANÁLISIS BIO-ESTADÍSTICO", use_container_width=True, type="primary"):
            datos = {"px_name": px_n, "px_id": px_i, "tfg": tfg_p, "fevi": fevi_p, 
                     "potasio": pot_p, "sys": sys_p, "sleep": sleep_p, "stress": stress_p, "exercise": exe_p}
            
            recoms, alertas = generar_plan_cientifico(datos)
            
            # Persistencia en BD
            db.conn.execute("INSERT INTO clinical_records (px_name, px_id, date, doctor, sys, tfg, potasio, fevi, sleep, stress, exercise) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                           (px_n, px_i, datetime.now().strftime("%Y-%m-%d"), st.session_state.name, sys_p, tfg_p, pot_p, fevi_p, sleep_p, stress_p, exe_p))
            db.conn.commit()
            db.log_action(st.session_state.username, "Consulta", f"Evaluado: {px_n}")
            
            # --- VISUALIZACIÓN ---
            st.divider()
            col_left, col_right = st.columns(2)
            
            with col_left:
                # Gauge TFG con semáforo técnico
                fig_tfg = go.Figure(go.Indicator(
                    mode="gauge+number", value=tfg_p, title={'text': "Estatus Renal (TFG)"},
                    gauge={'axis': {'range': [0, 120]}, 'steps': [
                        {'range': [0, 30], 'color': "#ff4d4d"}, # Rojo
                        {'range': [30, 60], 'color': "#ffa64d"}, # Naranja
                        {'range': [60, 90], 'color': "#ffff4d"}, # Amarillo
                        {'range': [90, 120], 'color': "#4dff4d"}]})) # Verde
                st.plotly_chart(fig_tfg, use_container_width=True)

            with col_right:
                # Radar de Vida
                cat_radar = ['Sueño', 'Ejercicio', 'Control Estrés']
                val_radar = [(sleep_p/8)*100, (exe_p/150)*100, {'Bajo':100,'Moderado':60,'Alto':30}[stress_p]]
                fig_radar = go.Figure()
                fig_radar.add_trace(go.Scatterpolar(r=val_radar, theta=cat_radar, fill='toself', name='Actual', line_color='teal'))
                fig_radar.add_trace(go.Scatterpolar(r=[100,100,100], theta=cat_radar, mode='lines', name='Meta', line_color='gray'))
                fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])), title="Radar Bio-Psicosocial")
                st.plotly_chart(fig_radar, use_container_width=True)

            # Cuadrante de Riesgo Cardiorrenal
            st.subheader("📍 Posicionamiento Clínico")
            
            fig_q = px.scatter(x=[tfg_p], y=[fevi_p], labels={'x':'Tasa Filtración (TFG)', 'y':'Función Cardiaca (FEVI)'})
            fig_q.add_vline(x=60, line_dash="dot", line_color="red")
            fig_q.add_hline(y=40, line_dash="dot", line_color="red")
            fig_q.update_traces(marker=dict(size=20, color='red', symbol='cross'))
            st.plotly_chart(fig_q, use_container_width=True)

            # Botón de PDF
            pdf_out = crear_pdf(datos, recoms, alertas, st.session_state.name)
            st.download_button("📩 DESCARGAR INFORME PARA PACIENTE", pdf_out, f"NefroCardio_{px_i}.pdf", "application/pdf")

elif opcion == "Historial Clínico":
    st.title("Expedientes Digitales")
    df = pd.read_sql("SELECT * FROM clinical_records ORDER BY id DESC", db.conn)
    st.dataframe(df, use_container_width=True)
""", unsafe_allow_html=True)
