import pandas as pd
import numpy as np
import joblib
import json
import os
import bcrypt
import secrets
from datetime import datetime, timedelta
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from io import BytesIO
from fpdf import FPDF

# =============================================
# 1. CONFIGURACIÓN Y ESTILOS
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
    try:
        r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        return f'rgba({r}, {g}, {b}, {alpha})'
    except:
        return 'rgba(128, 128, 128, 0.2)'

# =============================================
# 2. SEGURIDAD Y BASE DE DATOS
# =============================================
DB_FILE = "nefro_db.json"

class DataStore:
    def __init__(self):
        if not os.path.exists(DB_FILE): self._create_initial_db()
        self.data = self._load()

    def _create_initial_db(self):
        pwd = bcrypt.hashpw("Admin2024!".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        initial = {
            "users": {"admin": {"pwd": pwd, "role": "admin", "name": "Administrador", "active": True}},
            "patients": [], "audit_log": []
        }
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(initial, f, indent=4, ensure_ascii=False)

    def _load(self):
        with open(DB_FILE, "r", encoding="utf-8") as f: return json.load(f)

    def save(self):
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=4, ensure_ascii=False)

    def log_audit(self, user, action, action_type="INFO"):
        log = {"timestamp": datetime.now().isoformat(), "user": user, "action": action, "type": action_type}
        self.data.setdefault("audit_log", []).insert(0, log)
        self.save()

    def verify_login(self, u, p):
        user = self.data["users"].get(u)
        if user and bcrypt.checkpw(p.encode('utf-8'), user["pwd"].encode('utf-8')):
            if user.get("active", True): return user
        return None

db = DataStore()

# =============================================
# 3. FUNCIONES CLÍNICAS Y GRÁFICOS
# =============================================
def calcular_tfg_ckdepi(creatinina, edad, sexo="hombre", raza="no_afro"):
    k, alpha = (0.7, -0.329) if sexo == "mujer" else (0.9, -0.411)
    rf = 1.159 if raza == "afro" else 1.0
    sf = 1.018 if sexo == "mujer" else 1.0
    tfg = 141 * (min(creatinina/k, 1)**alpha) * (max(creatinina/k, 1)**-1.209) * (0.993**edad) * sf * rf
    return round(tfg)

def clasificar_erc(tfg):
    if tfg >= 90: return "G1 (Normal o Alto)"
    elif tfg >= 60: return "G2 (Levemente Disminuido)"
    elif tfg >= 45: return "G3a (Disminución Leve a Moderada)"
    elif tfg >= 30: return "G3b (Disminución Moderada a Severa)"
    elif tfg >= 15: return "G4 (Disminución Severa)"
    return "G5 (Fallo Renal)"

def crear_gauge_riesgo(riesgo):
    color = DANGER if riesgo > 70 else (WARNING if riesgo > 40 else SUCCESS)
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=riesgo,
        number={'suffix': "%", 'font': {'color': color}},
        gauge={
            'axis': {'range': , 'tickwidth': 2, 'tickcolor': PRIMARY}, # CORRECCIÓN AQUÍ
            'bar': {'color': color},
            'steps': [
                {'range': [5], 'color': hex_to_rgba(SUCCESS, 0.2)},
                {'range': [5], 'color': hex_to_rgba(WARNING, 0.2)},
                {'range': , 'color': hex_to_rgba(DANGER, 0.2)}
            ]
        }
    ))
    fig.update_layout(height=300, margin=dict(l=20, r=20, t=50, b=20), paper_bgcolor='rgba(0,0,0,0)')
    return fig

# =============================================
# 4. INTERFAZ Y NAVEGACIÓN
# =============================================
if "logged_in" not in st.session_state: st.session_state.logged_in = False

if not st.session_state.logged_in:
    c1, c2, c3 = st.columns([6, 7]) # CORRECCIÓN COLUMNAS
    with c2:
        st.header("🔐 NefroPredict Login")
        with st.form("login"):
            u = st.text_input("Usuario").lower().strip()
            p = st.text_input("Contraseña", type="password")
            if st.form_submit_button("Entrar"):
                res = db.verify_login(u, p)
                if res:
                    st.session_state.update({"logged_in": True, "username": u, "role": res["role"], "doctor_name": res["name"]})
                    db.log_audit(u, "Inicio de sesión exitoso", "LOGIN")
                    st.rerun()
                else: st.error("Credenciales incorrectas")
    st.stop()

# Menú según Rol
tabs_list = ["📋 Evaluación", "📤 Carga Masiva", "📊 Historial"]
if st.session_state.role == "admin":
    tabs_list += ["📈 Estadísticas", "🔍 Auditoría"]

tabs = st.tabs(tabs_list)

# --- TAB EVALUACIÓN ---
with tabs:
    col_f, col_r = st.columns([1.2, 1])
    with col_f:
        with st.form("eval"):
            nom = st.text_input("Nombre Paciente")
            c1, c2 = st.columns(2)
            with c1:
                sex = st.selectbox("Sexo", ["Hombre", "Mujer"])
                ed = st.number_input("Edad", 18, 120, 55)
                creat = st.number_input("Creatinina", 0.1, 15.0, 1.2)
            with c2:
                raz = st.selectbox("Raza", ["No-Afroamericano", "Afroamericano"])
                gluc = st.number_input("Glucosa", 50, 500, 100)
                pres = st.number_input("Sistólica", 80, 250, 120)
            if st.form_submit_button("Analizar"):
                if nom:
                    tfg = calcular_tfg_ckdepi(creat, ed, sex.lower(), "afro" if "Afro" in raz else "no_afro")
                    base_risk = 10 + (creat-1)*30 + max(0, gluc-126)*0.3
                    riesgo = round(max(1, min(99, base_risk)), 1)
                    rec = {"nombre_paciente": nom, "riesgo": riesgo, "tfg": tfg, "estadio_erc": clasificar_erc(tfg), 
                           "doctor_user": st.session_state.username, "timestamp": datetime.now().isoformat(), "nivel": "Normal"}
                    db.data["patients"].insert(0, rec)
                    db.save()
                    st.session_state.ultimo = rec
                else: st.error("Nombre requerido")

    if "ultimo" in st.session_state:
        with col_r:
            p = st.session_state.ultimo
            st.plotly_chart(crear_gauge_riesgo(p["riesgo"]), use_container_width=True)
            st.metric("TFG", f"{p['tfg']} ml/min")
            st.info(f"Estadio: {p['estadio_erc']}")

# --- TAB HISTORIAL ---
with tabs[7]:
    st.header("Historial")
    pats = db.data["patients"]
    if pats:
        df = pd.DataFrame(pats)
        cols = ['timestamp', 'nombre_paciente', 'riesgo', 'tfg', 'estadio_erc']
        st.dataframe(df[[c for c in cols if c in df.columns]])

# --- TABS ADMIN (ESTADÍSTICAS Y AUDITORÍA) ---
if st.session_state.role == "admin":
    with tabs[8]: # Estadísticas
        st.header("Estadísticas Globales")
        if db.data["patients"]:
            df_s = pd.DataFrame(db.data["patients"])
            st.plotly_chart(px.pie(df_s, names='estadio_erc', title="Distribución por Estadio"))
    with tabs[9]: # Auditoría
        st.header("Auditoría de Seguridad")
        st.dataframe(pd.DataFrame(db.data["audit_log"]))

if st.sidebar.button("Cerrar Sesión"):
    st.session_state.clear()
    st.rerun()
