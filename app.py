import pandas as pd
import numpy as np
import joblib
import json
import os
import bcrypt
import secrets
from datetime import datetime
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from fpdf import FPDF 

# =============================================
# CONFIGURACIÓN Y ESTILOS
# =============================================
st.set_page_config(
    page_title="NefroPredict RD",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="collapsed"
)

PRIMARY = "#0066CC"    
SECONDARY = "#00A896"  
DANGER = "#E63946"     
WARNING = "#F77F00"    
SUCCESS = "#06D6A0"    

def hex_to_rgba(hex_color, alpha):
    hex_color = hex_color.lstrip('#')
    r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    return f'rgba({r}, {g}, {b}, {alpha})'

st.markdown(f"""
<style>
    .main {{ background: #0e1117; }}
    .stButton>button {{
        background: linear-gradient(135deg, {PRIMARY}, {SECONDARY});
        color: white; border-radius: 10px; border: none; padding: 0.5rem 1rem;
    }}
    .metric-card {{
        background: #1e293b; padding: 20px; border-radius: 15px;
        border-left: 5px solid {PRIMARY}; color: white; margin-bottom: 10px;
    }}
    .risk-card {{ padding: 30px; border-radius: 20px; text-align: center; margin-bottom: 20px; }}
    .risk-high {{ background: {hex_to_rgba(DANGER, 0.1)}; border: 2px solid {DANGER}; }}
    .risk-med {{ background: {hex_to_rgba(WARNING, 0.1)}; border: 2px solid {WARNING}; }}
    .risk-low {{ background: {hex_to_rgba(SUCCESS, 0.1)}; border: 2px solid {SUCCESS}; }}
</style>
""", unsafe_allow_html=True)

# =============================================
# SISTEMA DE DATOS Y SEGURIDAD
# =============================================
DB_FILE = "nefro_db.json"

def hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password, hashed):
    try:
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    except:
        return password == hashed

class DataStore:
    def __init__(self):
        if not os.path.exists(DB_FILE): self._create_db()
        self.data = self._load()

    def _create_db(self):
        initial = {
            "users": {"admin": {"pwd": hash_password("Admin2024!"), "role": "admin", "name": "Administrador", "active": True}},
            "patients": [], "audit_log": []
        }
        with open(DB_FILE, "w") as f: json.dump(initial, f, indent=4)

    def _load(self):
        with open(DB_FILE, "r") as f: return json.load(f)

    def save(self):
        with open(DB_FILE, "w") as f: json.dump(self.data, f, indent=4)

    def verify_login(self, user, pwd):
        u = self.data["users"].get(user)
        if u and verify_password(pwd, u["pwd"]) and u.get("active", True): return u
        return None

    def add_patient(self, record):
        self.data["patients"].insert(0, record)
        self.save()

    def log_audit(self, user, action, type="INFO"):
        self.data["audit_log"].insert(0, {"ts": datetime.now().isoformat(), "user": user, "action": action, "type": type})
        self.save()

db = DataStore()

# =============================================
# LÓGICA CLÍNICA
# =============================================
def calcular_tfg(creatinina, edad, sexo, raza):
    k = 0.7 if sexo == "Mujer" else 0.9
    alpha = -0.329 if sexo == "Mujer" else -0.411
    f_raza = 1.159 if "Afro" in raza else 1.0
    f_sexo = 1.018 if sexo == "Mujer" else 1.0
    tfg = 141 * (min(creatinina/k, 1)**alpha) * (max(creatinina/k, 1)**-1.209) * (0.993**edad) * f_sexo * f_raza
    return round(tfg)

def clasificar_erc(tfg):
    if tfg >= 90: return "G1 (Normal)"
    if tfg >= 60: return "G2 (Leve)"
    if tfg >= 45: return "G3a (Leve-Mod)"
    if tfg >= 30: return "G3b (Mod-Sev)"
    if tfg >= 15: return "G4 (Severo)"
    return "G5 (Fallo)"

def predecir_riesgo(d):
    # Simulación de modelo basada en scores clínicos
    score = (d['creatinina']*25) + (d['glucosa_ayunas']*0.1) + (d['presion_sistolica']*0.15)
    riesgo = min(99.9, max(5.0, score - 30))
    return round(riesgo, 1)

# =============================================
# GENERACIÓN DE REPORTES (PDF)
# =============================================
class PDFReport(FPDF):
    def header(self):
        self.set_fill_color(0, 102, 204)
        self.rect(0, 0, 210, 20, 'F')
        self.set_text_color(255, 255, 255)
        self.set_font('Arial', 'B', 12)
        self.cell(0, 10, 'NEFROPREDICT RD - INFORME CLINICO', 0, 1, 'C')
        self.ln(10)

def generar_pdf_bytes(p, reco):
    pdf = PDFReport()
    pdf.add_page()
    pdf.set_font('Arial', 'B', 14)
    pdf.cell(0, 10, f"Paciente: {p['nombre_paciente']}", 0, 1)
    pdf.set_font('Arial', '', 11)
    pdf.cell(0, 7, f"Fecha: {p['timestamp'][:10]} | Medico: {p['doctor_name']}", 0, 1)
    pdf.ln(5)
    
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(0, 10, "RESULTADOS DE EVALUACION", 1, 1, 'C', True)
    pdf.cell(95, 10, f"Riesgo ERC: {p['riesgo']}%", 1, 0)
    pdf.cell(95, 10, f"TFG: {p['tfg']} ml/min", 1, 1)
    pdf.cell(95, 10, f"Estadio: {p['estadio_erc']}", 1, 0)
    pdf.cell(95, 10, f"Creatinina: {p['creatinina']} mg/dL", 1, 1)
    pdf.ln(5)
    pdf.multi_cell(0, 7, f"RECOMENDACION: {reco}")
    return pdf.output(dest='S').encode('latin-1')

# =============================================
# INTERFAZ DE USUARIO (UI)
# =============================================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.markdown("<h2 style='text-align:center;'>🏥 Acceso NefroPredict</h2>", unsafe_allow_html=True)
        with st.form("login"):
            u = st.text_input("Usuario").lower()
            p = st.text_input("Contraseña", type="password")
            if st.form_submit_button("Entrar", use_container_width=True):
                user_data = db.verify_login(u, p)
                if user_data:
                    st.session_state.logged_in = True
                    st.session_state.username = u
                    st.session_state.role = user_data["role"]
                    st.session_state.doctor_name = user_data["name"]
                    db.log_audit(u, "Inicio de sesión", "LOGIN")
                    st.rerun()
                else: st.error("Credenciales inválidas")
    st.stop()

# Dashboard Principal
st.markdown(f"### Bienvendid@, Dr. {st.session_state.doctor_name} | `{st.session_state.role.upper()}`")

tabs = st.tabs(["📋 Evaluación", "📊 Historial", "👥 Usuarios", "🔍 Auditoría"])

# --- TAB 1: EVALUACIÓN ---
with tabs[0]:
    c1, c2 = st.columns([1, 1])
    with c1:
        with st.form("eval"):
            nombre = st.text_input("Nombre del Paciente")
            col_a, col_b = st.columns(2)
            sexo = col_a.selectbox("Sexo", ["Hombre", "Mujer"])
            raza = col_b.selectbox("Raza", ["No-Afroamericano", "Afroamericano"])
            edad = st.number_input("Edad", 18, 100, 50)
            creat = st.number_input("Creatinina (mg/dL)", 0.1, 10.0, 1.1)
            glu = st.number_input("Glucosa (mg/dL)", 50, 400, 100)
            tas = st.number_input("Presión Sistólica", 80, 200, 120)
            imc = st.number_input("IMC", 15.0, 50.0, 25.0)
            
            if st.form_submit_button("Analizar"):
                tfg = calcular_tfg(creat, edad, sexo, raza)
                estadio = clasificar_erc(tfg)
                riesgo = predecir_riesgo({'creatinina': creat, 'glucosa_ayunas': glu, 'presion_sistolica': tas})
                
                record = {
                    "nombre_paciente": nombre, "doctor_name": st.session_state.doctor_name,
                    "timestamp": datetime.now().isoformat(), "sexo": sexo, "raza": raza,
                    "edad": edad, "creatinina": creat, "tfg": tfg, "estadio_erc": estadio,
                    "riesgo": riesgo, "glucosa": glu, "tas": tas, "imc": imc
                }
                db.add_patient(record)
                st.session_state.last_p = record

    with c2:
        if "last_p" in st.session_state:
            p = st.session_state.last_p
            color = DANGER if p['riesgo'] > 70 else WARNING if p['riesgo'] > 40 else SUCCESS
            st.markdown(f"""
            <div class='risk-card risk-{'high' if p['riesgo']>70 else 'med' if p['riesgo']>40 else 'low'}'>
                <h3 style='color:{color}'>RIESGO ESTIMADO</h3>
                <h1 style='font-size:4em; color:{color}'>{p['riesgo']}%</h1>
                <p>Estadio: <b>{p['estadio_erc']}</b> | TFG: <b>{p['tfg']}</b></p>
            </div>
            """, unsafe_allow_html=True)
            
            reco = "Referencia Urgente a Nefrología" if p['riesgo'] > 70 else "Control Mensual" if p['riesgo'] > 40 else "Seguimiento Anual"
            st.info(f"**Nota Médica:** {reco}")
            
            pdf_data = generar_pdf_bytes(p, reco)
            st.download_button("📥 Descargar Reporte PDF", pdf_data, f"Reporte_{p['nombre_paciente']}.pdf", "application/pdf")

# --- TAB 2: HISTORIAL ---
with tabs[1]:
    df = pd.DataFrame(db.data["patients"])
    if not df.empty:
        st.dataframe(df[['timestamp', 'nombre_paciente', 'tfg', 'estadio_erc', 'riesgo', 'doctor_name']], use_container_width=True)
    else: st.write("No hay registros.")

# --- TAB 3: GESTIÓN USUARIOS (ADMIN) ---
with tabs[2]:
    if st.session_state.role == "admin":
        with st.expander("Crear Nuevo Médico"):
            with st.form("new_user"):
                new_u = st.text_input("Usuario ID")
                new_n = st.text_input("Nombre Completo")
                new_p = st.text_input("Clave Temporal")
                if st.form_submit_button("Registrar"):
                    db.data["users"][new_u] = {"pwd": hash_password(new_p), "role": "doctor", "name": new_n, "active": True}
                    db.save()
                    st.success("Usuario creado")
    else: st.warning("Acceso restringido a administradores.")

# --- TAB 4: AUDITORÍA ---
with tabs[3]:
    if st.session_state.role == "admin":
        st.table(db.data["audit_log"][:20])
    else: st.write("No tienes permisos para ver logs.")

# Botón de cierre
if st.sidebar.button("Cerrar Sesión"):
    st.session_state.logged_in = False
    st.rerun()
