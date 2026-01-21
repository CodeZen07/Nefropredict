import pandas as pd
import numpy as np
import sqlite3
import bcrypt
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from fpdf import FPDF
from io import BytesIO

# =============================================
# 1. CONFIGURACIÓN DE INTERFAZ
# =============================================
st.set_page_config(
    page_title="NefroPredict RD Pro",
    page_icon="🏥",
    layout="wide"
)

# Colores y Estilos CSS
C_PRIM = "#0066CC"
C_SEC = "#00A896"
C_CRIT = "#E63946"

st.markdown(f"""
<style>
    .stApp {{ background-color: #0b0e14; color: #e0e0e0; }}
    .metric-card {{ 
        background: #1a202c; padding: 20px; border-radius: 15px; 
        border-left: 5px solid {C_PRIM}; box-shadow: 0 4px 12px rgba(0,0,0,0.3);
    }}
    .risk-card {{ 
        padding: 30px; border-radius: 20px; text-align: center; 
        margin: 10px 0; box-shadow: 0 10px 25px rgba(0,0,0,0.2);
    }}
    .stButton>button {{ 
        border-radius: 8px; font-weight: 600; background: linear-gradient(135deg, {C_PRIM}, {C_SEC});
        color: white; border: none; transition: 0.3s;
    }}
    .stButton>button:hover {{ transform: translateY(-2px); }}
</style>
""", unsafe_allow_html=True)

# =============================================
# 2. BASE DE DATOS
# =============================================
class SystemDB:
    def __init__(self):
        self.conn = sqlite3.connect("nefro_final.db", check_same_thread=False)
        self.init_tables()

    def init_tables(self):
        c = self.conn.cursor()
        c.execute("""CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY, password TEXT, name TEXT, role TEXT, active INT)""")
        c.execute("""CREATE TABLE IF NOT EXISTS patients (
            id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, doctor TEXT, age INT, 
            sex TEXT, creat REAL, tfg REAL, risk REAL, stage TEXT, date TEXT)""")
        
        c.execute("SELECT * FROM users WHERE username='admin'")
        if not c.fetchone():
            hash_pw = bcrypt.hashpw("Admin2026!".encode(), bcrypt.gensalt()).decode()
            c.execute("INSERT INTO users VALUES (?,?,?,?,?)", ("admin", hash_pw, "Administrador", "admin", 1))
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
# 3. FUNCIONES CLÍNICAS Y PDF
# =============================================
def get_scientific_recom(stage, risk):
    if risk > 75:
        return "URGENTE: Referencia inmediata a Nefrologia. Evaluar inicio de terapia de reemplazo renal. Restriccion estricta de sodio <2g/dia."
    if "G3" in stage:
        return "MONITOREO: Evaluar relacion Albumina/Creatinina. Ajustar dosis de farmacos renales. Control de Presion Arterial meta <130/80 mmHg."
    return "PREVENCION: Mantener Hemoglobina Glicosilada <7%. Actividad fisica regular (150 min/semana). Screening renal anual."

def generate_pdf(p_data, doctor_name):
    pdf = FPDF()
    pdf.add_page()
    
    # Encabezado
    pdf.set_fill_color(0, 102, 204)
    pdf.rect(0, 0, 210, 40, 'F')
    pdf.set_font("Arial", 'B', 22)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 20, "NefroPredict RD - Reporte Clinico", 0, 1, 'C')
    
    # Datos
    pdf.set_text_color(0, 0, 0)
    pdf.ln(25)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, f"Paciente: {p_data['name'].upper()} | Fecha: {datetime.now().strftime('%d/%m/%Y')}", 0, 1)
    pdf.line(10, 55, 200, 55)
    
    pdf.ln(10)
    pdf.set_font("Arial", '', 11)
    pdf.cell(90, 10, f"Tasa Filtrado (TFG): {p_data['tfg']} ml/min", 1)
    pdf.cell(90, 10, f"Estadio ERC: {p_data['stage']}", 1, 1)
    pdf.cell(90, 10, f"Riesgo Predictivo: {p_data['risk']}%", 1)
    pdf.cell(90, 10, f"Creatinina: {p_data['creat']} mg/dL", 1, 1)
    
    pdf.ln(10)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, "Recomendaciones Clinicas (KDIGO):", 0, 1)
    pdf.set_font("Arial", '', 11)
    # Limpieza de caracteres para evitar errores de encoding
    recom_txt = p_data['recom'].replace('á','a').replace('é','e').replace('í','i').replace('ó','o').replace('ú','u').replace('ñ','n')
    pdf.multi_cell(0, 8, recom_txt)
    
    pdf.ln(25)
    pdf.line(70, pdf.get_y(), 140, pdf.get_y())
    pdf.cell(0, 10, f"Dr(a). {doctor_name}", 0, 1, 'C')
    
    # --- SALIDA A BYTESIO (Solución al Error) ---
    pdf_out = pdf.output(dest='S')
    if isinstance(pdf_out, str):
        return BytesIO(pdf_out.encode('latin-1', errors='replace'))
    return BytesIO(pdf_out)

# =============================================
# 4. APLICACIÓN PRINCIPAL
# =============================================
if "auth" not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:
    col1, col2, col3 = st.columns([1,1.5,1])
    with col2:
        st.markdown("<h2 style='text-align: center;'>🔐 Acceso Médico</h2>", unsafe_allow_html=True)
        u = st.text_input("Usuario")
        p = st.text_input("Contraseña", type="password")
        if st.button("INGRESAR AL SISTEMA", use_container_width=True):
            cursor = db.conn.cursor()
            cursor.execute("SELECT password, name, role FROM users WHERE username=?", (u,))
            res = cursor.fetchone()
            if res and bcrypt.checkpw(p.encode(), res[0].encode()):
                st.session_state.auth = True
                st.session_state.user, st.session_state.name, st.session_state.role = u, res[1], res[2]
                st.rerun()
            else: st.error("Error de credenciales")
    st.stop()

# Navegación Sidebar
with st.sidebar:
    st.title("NefroPredict RD")
    st.write(f"Sesión: Dr. {st.session_state.name}")
    menu = st.radio("Menu", ["🩺 Evaluación", "📅 Historial", "👥 Usuarios"])
    if st.button("Cerrar Sesión"):
        st.session_state.auth = False
        st.rerun()

if menu == "🩺 Evaluación":
    st.header("Nueva Evaluación Clínica")
    c1, c2 = st.columns([1, 1.2])
    
    with c1:
        with st.form("form_eval"):
            px = st.text_input("Nombre del Paciente")
            edad = st.number_input("Edad", 18, 100, 55)
            sexo = st.selectbox("Sexo", ["Hombre", "Mujer"])
            creat = st.number_input("Creatinina (mg/dL)", 0.3, 12.0, 1.2)
            gluc = st.number_input("Glucosa (mg/dL)", 60, 400, 110)
            pres = st.number_input("Presión Sistólica", 80, 200, 135)
            imc = st.number_input("IMC", 15.0, 45.0, 27.0)
            submit = st.form_submit_button("ANALIZAR RIESGO")

    if submit:
        # Cálculo TFG (CKD-EPI simplificado)
        k = 0.7 if sexo == "Mujer" else 0.9
        a = -0.329 if sexo == "Mujer" else -0.411
        tfg = round(141 * min(creat/k, 1)**a * max(creat/k, 1)**-1.209 * 0.993**edad * (1.018 if sexo == "Mujer" else 1), 1)
        risk = round(min(98, (creat*20) + (edad*0.1) + (gluc*0.05)), 1)
        stage = "G1" if tfg >= 90 else "G2" if tfg >= 60 else "G3" if tfg >= 30 else "G4" if tfg >= 15 else "G5"
        recom = get_scientific_recom(stage, risk)
        
        db.conn.execute("INSERT INTO patients (name, doctor, age, sex, creat, tfg, risk, stage, date) VALUES (?,?,?,?,?,?,?,?,?)",
                       (px, st.session_state.name, edad, sexo, creat, tfg, risk, stage, datetime.now().strftime('%Y-%m-%d')))
        db.conn.commit()

        with c2:
            # Gráfico de Radar
            fig = go.Figure(go.Scatterpolar(r=[creat*10, gluc/2, pres/2, imc, edad], theta=['Creat','Gluc','Pres','IMC','Edad'], fill='toself'))
            fig.update_layout(polar=dict(radialaxis=dict(visible=False)), showlegend=False, title="Factores Críticos")
            st.plotly_chart(fig, use_container_width=True)
            
            st.markdown(f"<div class='risk-card' style='background:{C_CRIT if risk > 60 else C_SEC}22;'><h2>Riesgo: {risk}%</h2><p>Estadio {stage}</p></div>", unsafe_allow_html=True)
            
            # Botón de Descarga Seguro
            p_data = {'name': px, 'tfg': tfg, 'stage': stage, 'risk': risk, 'creat': creat, 'recom': recom}
            pdf_buf = generate_pdf(p_data, st.session_state.name)
            st.download_button("📥 Descargar Reporte PDF", data=pdf_buf.getvalue(), file_name=f"Reporte_{px}.pdf", mime="application/pdf")

elif menu == "📅 Historial":
    st.header("Registro de Pacientes")
    df = pd.read_sql("SELECT * FROM patients ORDER BY id DESC", db.conn)
    st.dataframe(df, use_container_width=True)

elif menu == "👥 Usuarios":
    if st.session_state.role != "admin":
        st.warning("Solo administradores")
    else:
        st.subheader("Registrar Nuevo Doctor")
        with st.form("add_doc"):
            nu, np, nn = st.text_input("ID Usuario"), st.text_input("Password", type="password"), st.text_input("Nombre")
            if st.form_submit_button("Crear"):
                if db.add_user(nu, np, nn, "doctor"): st.success("Doctor creado")
                else: st.error("Error al crear")
