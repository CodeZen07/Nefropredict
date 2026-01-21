import pandas as pd
import numpy as np
import joblib
import sqlite3
import bcrypt
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from fpdf import FPDF
from io import BytesIO

# =============================================
# 1. CONFIGURACIÓN Y ESTÉTICA
# =============================================
st.set_page_config(page_title="NefroPredict RD Pro", page_icon="🏥", layout="wide")

# Colores institucionales
C_PRIM = "#0066CC"  # Azul Médico
C_SEC = "#00A896"   # Verde Salud
C_CRIT = "#E63946"  # Rojo Crítico

st.markdown(f"""
<style>
    .stApp {{ background-color: #0b0e14; color: #e0e0e0; }}
    [data-testid="stSidebar"] {{ background-color: #151921; border-right: 1px solid #2d3748; }}
    .metric-card {{ background: #1a202c; padding: 20px; border-radius: 15px; border-left: 5px solid {C_PRIM}; }}
    .stButton>button {{ border-radius: 8px; font-weight: 600; transition: 0.3s; }}
    .stButton>button:hover {{ transform: scale(1.02); background-color: {C_SEC}; }}
</style>
""", unsafe_allow_html=True)

# =============================================
# 2. GESTIÓN DE DATOS (SQLite)
# =============================================
class SystemDB:
    def __init__(self):
        self.conn = sqlite3.connect("nefro_pro.db", check_same_thread=False)
        self.init_tables()

    def init_tables(self):
        c = self.conn.cursor()
        c.execute("""CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY, password TEXT, name TEXT, role TEXT, active INT)""")
        c.execute("""CREATE TABLE IF NOT EXISTS patients (
            id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, doctor TEXT, age INT, 
            sex TEXT, creat REAL, tfg REAL, risk REAL, stage TEXT, date TEXT)""")
        
        # Crear admin por defecto
        c.execute("SELECT * FROM users WHERE username='admin'")
        if not c.fetchone():
            hash_pw = bcrypt.hashpw("Admin2026!".encode(), bcrypt.gensalt()).decode()
            c.execute("INSERT INTO users VALUES (?,?,?,?,?)", ("admin", hash_pw, "Admin Central", "admin", 1))
        self.conn.commit()

    def add_user(self, user, pw, name, role):
        try:
            hash_pw = bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()
            self.conn.execute("INSERT INTO users VALUES (?,?,?,?,?)", (user, hash_pw, name, role, 1))
            self.conn.commit()
            return True
        except: return False

db = SystemDB()

# =============================================
# 3. LÓGICA CLÍNICA Y GRÁFICOS
# =============================================
def get_scientific_recom(stage, risk):
    if risk > 75:
        return "URGENTE: Referencia a Nefrología. Iniciar IECA/ARA-II si no hay contraindicación. Restricción de sodio <2g/día."
    if "G3" in stage:
        return "MONITOREO: Evaluar relación Albúmina/Creatinina. Ajustar dosis de metformina/fármacos renales."
    return "PREVENCIÓN: Control de Hemoglobina Glicosilada <7% y actividad física regular 150 min/semana."

def draw_radar(data):
    # Normalización simple para visualización
    categories = ['Creatinina', 'Glucosa', 'Presión Sist.', 'IMC', 'Edad']
    values = [data['creat']*10, data['gluc']/2, data['pres']/2, data['bmi'], data['age']]
    
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(r=values, theta=categories, fill='toself', line_color=C_SEC))
    fig.update_layout(polar=dict(radialaxis=dict(visible=False)), showlegend=False, 
                     paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', title="Puntos Críticos Metabólicos")
    return fig

# =============================================
# 4. GENERADOR DE PDF
# =============================================
def generate_pdf(p_data, doctor_name):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_fill_color(0, 102, 204)
    pdf.rect(0, 0, 210, 40, 'F')
    
    pdf.set_font("Arial", 'B', 22)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 20, "NefroPredict RD - Reporte Clínico", 0, 1, 'C')
    
    pdf.set_text_color(0, 0, 0)
    pdf.ln(25)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, f"Paciente: {p_data['name']} | Fecha: {datetime.now().strftime('%Y-%m-%d')}", 0, 1)
    pdf.line(10, 55, 200, 55)
    
    pdf.ln(10)
    pdf.set_font("Arial", '', 11)
    col_w = 90
    pdf.cell(col_w, 8, f"Tasa Filtrado (TFG): {p_data['tfg']} ml/min", 1)
    pdf.cell(col_w, 8, f"Estadio ERC: {p_data['stage']}", 1, 1)
    pdf.cell(col_w, 8, f"Riesgo Predictivo: {p_data['risk']}%", 1)
    pdf.cell(col_w, 8, f"Creatinina: {p_data['creat']} mg/dL", 1, 1)
    
    pdf.ln(10)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, "Observaciones y Recomendaciones Médicas (KDIGO):", 0, 1)
    pdf.set_font("Arial", '', 11)
    pdf.multi_cell(0, 8, p_data['recom'])
    
    pdf.ln(30)
    pdf.line(70, pdf.get_y(), 140, pdf.get_y())
    pdf.cell(0, 10, f"Dr(a). {doctor_name}", 0, 1, 'C')
    pdf.set_font("Arial", 'I', 8)
    pdf.cell(0, 5, "Firma y Sello Digital", 0, 1, 'C')
    
    return pdf.output(dest='S').encode('latin-1')

# =============================================
# 5. INTERFAZ PRINCIPAL
# =============================================
if "auth" not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.markdown("<h2 style='text-align: center;'>🔐 Acceso Clínico</h2>", unsafe_allow_html=True)
        u = st.text_input("Usuario")
        p = st.text_input("Contraseña", type="password")
        if st.button("Iniciar Sesión", use_container_width=True):
            cursor = db.conn.cursor()
            cursor.execute("SELECT password, name, role FROM users WHERE username=?", (u,))
            res = cursor.fetchone()
            if res and bcrypt.checkpw(p.encode(), res[0].encode()):
                st.session_state.auth = True
                st.session_state.user = u
                st.session_state.name = res[1]
                st.session_state.role = res[2]
                st.rerun()
            else: st.error("Acceso denegado")
    st.stop()

# Menú Lateral
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2773/2773193.png", width=80)
    st.title("NefroPredict RD")
    opt = st.radio("Menú", ["🩺 Nueva Evaluación", "📅 Historial", "👥 Gestión Usuarios"])
    if st.button("Cerrar Sesión"):
        st.session_state.auth = False
        st.rerun()

# --- LÓGICA DE MÓDULOS ---
if opt == "🩺 Nueva Evaluación":
    st.header("Evaluación de Riesgo Renal")
    c1, c2 = st.columns([1, 1.2])
    
    with c1:
        with st.form("eval"):
            px_name = st.text_input("Nombre Completo del Paciente")
            age = st.number_input("Edad", 18, 100, 45)
            sex = st.selectbox("Sexo", ["Hombre", "Mujer"])
            creat = st.number_input("Creatinina Sérica (mg/dL)", 0.2, 12.0, 1.1)
            gluc = st.number_input("Glucosa Ayunas (mg/dL)", 60, 400, 105)
            pres = st.number_input("Presión Sistólica (mmHg)", 80, 200, 130)
            bmi = st.number_input("IMC (kg/m²)", 15.0, 45.0, 26.0)
            btn = st.form_submit_button("ANALIZAR AHORA")

    if btn:
        # Cálculos (Fórmulas simplificadas para el ejemplo)
        tfg = 141 * min(creat/0.9, 1)**-0.411 * max(creat/0.9, 1)**-1.209 * 0.993**age
        tfg = round(tfg, 1)
        risk = round(min(98, (creat*15) + (age*0.2) + (gluc*0.1)), 1)
        stage = "G1" if tfg > 90 else "G2" if tfg > 60 else "G3" if tfg > 30 else "G4"
        recom = get_scientific_recom(stage, risk)
        
        db.conn.execute("INSERT INTO patients (name, doctor, age, sex, creat, tfg, risk, stage, date) VALUES (?,?,?,?,?,?,?,?,?)",
                       (px_name, st.session_state.name, age, sex, creat, tfg, risk, stage, datetime.now().date()))
        db.conn.commit()

        with c2:
            st.plotly_chart(draw_radar(locals()), use_container_width=True)
            st.success(f"**Resultado:** Estadio {stage} - Riesgo {risk}%")
            
            p_data = {'name': px_name, 'tfg': tfg, 'stage': stage, 'risk': risk, 'creat': creat, 'recom': recom}
            pdf_bytes = generate_pdf(p_data, st.session_state.name)
            st.download_button("📥 Descargar Reporte PDF", data=pdf_bytes, file_name=f"Reporte_{px_name}.pdf", mime="application/pdf")

elif opt == "👥 Gestión Usuarios":
    if st.session_state.role != "admin":
        st.warning("Acceso restringido a administradores.")
    else:
        st.subheader("Crear Nuevo Personal Médico")
        with st.form("new_user"):
            new_u = st.text_input("ID Usuario")
            new_p = st.text_input("Contraseña Temporal")
            new_n = st.text_input("Nombre del Doctor")
            new_r = st.selectbox("Rol", ["doctor", "admin"])
            if st.form_submit_button("Registrar"):
                if db.add_user(new_u, new_p, new_n, new_r): st.success("Registrado")
                else: st.error("Error o usuario existente")
        
        st.subheader("Personal Registrado")
        users_df = pd.read_sql("SELECT username, name, role, active FROM users", db.conn)
        st.table(users_df)

elif opt == "📅 Historial":
    st.subheader("Registro Histórico de Evaluaciones")
    df = pd.read_sql("SELECT * FROM patients ORDER BY id DESC", db.conn)
    st.dataframe(df, use_container_width=True)
