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
# 1. CONFIGURACIÓN Y ESTILOS [2-4]
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
BG_LIGHT = "#F8F9FA"
TEXT_DARK = "#212529"

def hex_to_rgba(hex_color, alpha):
    hex_color = hex_color.lstrip('#')
    try:
        r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        return f'rgba({r}, {g}, {b}, {alpha})'
    except ValueError:
        return 'rgba(128, 128, 128, 0.2)'

st.markdown(f"""
    <div style="text-align: center; padding: 20px; background-color: {PRIMARY}; color: white; border-radius: 10px; margin-bottom: 20px;">
        <h1>🏥 NefroPredict RD</h1>
        <p>Sistema Inteligente de Detección Temprana de ERC<br>República Dominicana • Versión 2.0</p>
    </div>
""", unsafe_allow_html=True)

# =============================================
# 2. SEGURIDAD Y BASE DE DATOS [5-9]
# =============================================
DB_FILE = "nefro_db.json"

def hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password, hashed):
    try:
        if not hashed.startswith('$2b$'): return password == hashed
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    except: return False

class DataStore:
    def __init__(self):
        if not os.path.exists(DB_FILE): self._create_initial_db()
        self.data = self._load()
        self._migrate_passwords()

    def _create_initial_db(self):
        initial = {
            "users": {"admin": {"pwd": hash_password("Admin2024!"), "role": "admin", "name": "Administrador", "active": True, "created_at": datetime.now().isoformat(), "last_login": None, "login_attempts": 0}},
            "patients": [], "uploads": [], "audit_log": [], "sessions": {}
        }
        with open(DB_FILE, "w", encoding="utf-8") as f: json.dump(initial, f, indent=4, ensure_ascii=False)

    def _load(self):
        with open(DB_FILE, "r", encoding="utf-8") as f: data = json.load(f)
        for key in ["users", "patients", "uploads", "audit_log", "sessions"]:
            if key not in data: data[key] = [] if key != "users" and key != "sessions" else {}
        return data

    def _migrate_passwords(self):
        migrated = False
        for username, user_data in self.data["users"].items():
            pwd = user_data.get("pwd", "")
            if pwd and not pwd.startswith('$2b$'):
                self.data["users"][username]["pwd"] = hash_password(pwd)
                migrated = True
        if migrated: self.save()

    def save(self):
        with open(DB_FILE, "w", encoding="utf-8") as f: json.dump(self.data, f, indent=4, ensure_ascii=False)

    def verify_login(self, username, password):
        user = self.data["users"].get(username)
        if not user: return None
        if verify_password(password, user.get("pwd", "")):
            if user.get("active", True):
                user["last_login"] = datetime.now().isoformat()
                self.save()
                self.log_audit(username, "Inicio de sesión exitoso", "LOGIN")
                return user
        return None

    def log_audit(self, user, action, action_type="INFO"):
        log_entry = {"timestamp": datetime.now().isoformat(), "user": user, "action": action, "type": action_type}
        self.data["audit_log"].insert(0, log_entry)
        self.data["audit_log"] = self.data["audit_log"][:2000]
        self.save()

    def add_patient(self, record):
        self.data["patients"].insert(0, record)
        self.save()

    def get_all_patients(self): return self.data["patients"]
    def get_patients_by_doctor(self, user_id): return [p for p in self.data["patients"] if p.get("doctor_user") == user_id]
    def get_audit_log(self, limit=100, user_filter="Todos", type_filter="Todos"):
        logs = self.data.get("audit_log", [])
        if user_filter != "Todos": logs = [l for l in logs if l.get("user") == user_filter]
        if type_filter != "Todos": logs = [l for l in logs if l.get("type") == type_filter]
        return logs[:limit]

db = DataStore()

# =============================================
# 3. FUNCIONES CLÍNICAS Y PREDICCIÓN [10-14]
# =============================================
def calcular_tfg_ckdepi(creatinina, edad, sexo="hombre", raza="no_afro"):
    k = 0.7 if sexo == "mujer" else 0.9
    alpha = -0.329 if sexo == "mujer" else -0.411
    raza_factor = 1.159 if raza == "afro" else 1.0
    sexo_factor = 1.018 if sexo == "mujer" else 1.0
    min_k_cr, max_k_cr = min(creatinina / k, 1), max(creatinina / k, 1)
    return round(141 * (min_k_cr ** alpha) * (max_k_cr ** -1.209) * (0.993 ** edad) * sexo_factor * raza_factor)

def clasificar_erc(tfg):
    if tfg >= 90: return "G1 (Normal o Alto)"
    elif tfg >= 60: return "G2 (Levemente Disminuido)"
    elif tfg >= 45: return "G3a (Disminución Leve a Moderada)"
    elif tfg >= 30: return "G3b (Disminución Moderada a Severa)"
    elif tfg >= 15: return "G4 (Disminución Severa)"
    return "G5 (Fallo Renal)"

def predecir(row):
    sexo_tfg = "mujer" if row.get("sexo") == "Mujer" else "hombre"
    raza_tfg = "afro" if "Afro" in row.get("raza", "") else "no_afro"
    tfg = calcular_tfg_ckdepi(row["creatinina"], row["edad"], sexo_tfg, raza_tfg)
    estadio = clasificar_erc(tfg)
    base = 10 + (row["creatinina"] - 1) * 32 + max(0, row["glucosa_ayunas"] - 126) * 0.3
    riesgo = round(max(1, min(99, base + np.random.uniform(-5, 8))), 1)
    return riesgo, tfg, estadio

def riesgo_level(risk):
    if risk > 70: return "MUY ALTO", DANGER, "Intervención URGENTE - Referir a nefrología inmediatamente", "Grave"
    elif risk > 40: return "ALTO", WARNING, "Intervención Media - Control estricto y seguimiento mensual", "Intermedio"
    return "MODERADO", SUCCESS, "Seguimiento Rutinario - Control cada 6 meses", "Normal"

# =============================================
# 4. INTERFAZ DE LOGIN [15-17]
# =============================================
if "logged_in" not in st.session_state: st.session_state.logged_in = False

if not st.session_state.logged_in:
    col1, col2, col3 = st.columns([2, 3])
    with col2:
        st.markdown("### 🔐 Acceso Seguro")
        with st.form("login"):
            username = st.text_input("Usuario").lower().strip()
            password = st.text_input("Contraseña", type="password")
            if st.form_submit_button("Iniciar Sesión", use_container_width=True):
                user = db.verify_login(username, password)
                if user:
                    st.session_state.update({"logged_in": True, "username": username, "role": user["role"], "doctor_name": user["name"]})
                    st.rerun()
                else: st.error("❌ Credenciales incorrectas")
    st.stop()

# =============================================
# 5. MENÚ Y TABS (HABILITADO) [18-21]
# =============================================
menu = ["📋 Evaluación Individual", "📤 Carga Masiva", "📊 Historial"]
if st.session_state.role == "admin": menu += ["📈 Estadísticas", "🔍 Auditoría"]
tabs = st.tabs(menu)

# --- TAB 1: EVALUACIÓN INDIVIDUAL ---
with tabs:
    col_f, col_r = st.columns([1.2, 1])
    with col_f:
        with st.form("eval"):
            nombre = st.text_input("Nombre del Paciente")
            c1, c2 = st.columns(2)
            with c1:
                sexo = st.selectbox("Sexo", ["Hombre", "Mujer"])
                edad = st.number_input("Edad", 18, 120, 55)
                creat = st.number_input("Creatinina (mg/dL)", 0.1, 15.0, 1.2)
            with c2:
                raza = st.selectbox("Raza", ["No-Afroamericano", "Afroamericano"])
                glucosa = st.number_input("Glucosa (mg/dL)", 50, 500, 110)
                presion = st.number_input("Sistólica (mmHg)", 80, 250, 130)
            if st.form_submit_button("Analizar Riesgo"):
                if nombre:
                    riesgo, tfg, estadio = predecir({"edad": edad, "creatinina": creat, "sexo": sexo, "raza": raza, "glucosa_ayunas": glucosa, "presion_sistolica": presion})
                    nivel, _, reco, _ = riesgo_level(riesgo)
                    record = {"nombre_paciente": nombre, "edad": edad, "sexo": sexo, "creatinina": creat, "glucosa_ayunas": glucosa, "riesgo": riesgo, "nivel": nivel, "tfg": tfg, "estadio_erc": estadio, "doctor_name": st.session_state.doctor_name, "doctor_user": st.session_state.username, "timestamp": datetime.now().isoformat()}
                    db.add_patient(record)
                    st.session_state.ultimo = record
                else: st.error("Nombre requerido")

# --- TAB 3: HISTORIAL (CORRECCIÓN KEYERROR) [1] ---
with tabs[3]:
    st.markdown("## 📊 Historial de Evaluaciones")
    patients = db.get_all_patients() if st.session_state.role == "admin" else db.get_patients_by_doctor(st.session_state.username)
    if patients:
        df_h = pd.DataFrame(patients)
        # SOLUCIÓN DINÁMICA: Filtrar solo las columnas que existen en el DataFrame real
        cols_deseadas = ['timestamp', 'nombre_paciente', 'edad', 'creatinina', 'riesgo', 'nivel', 'tfg', 'estadio_erc', 'doctor_name']
        cols_presentes = [c for c in cols_deseadas if c in df_h.columns]
        st.dataframe(df_h[cols_presentes].sort_values(by='timestamp', ascending=False), use_container_width=True)
    else: st.info("No hay registros.")

# --- TAB 5: ESTADÍSTICAS (HABILITADO) [22-24] ---
if st.session_state.role == "admin":
    with tabs[4]:
        st.markdown("## 📈 Estadísticas Globales")
        data_s = db.get_all_patients()
        if data_s:
            df_s = pd.DataFrame(data_s)
            c_m = st.columns(3)
            c_m.metric("Total Pacientes", len(df_s))
            if 'riesgo' in df_s: c_m[2].metric("Riesgo Promedio", f"{df_s['riesgo'].mean():.1f}%")
            if 'tfg' in df_s: c_m[3].metric("TFG Promedio", f"{df_s['tfg'].mean():.1f}")
            st.plotly_chart(px.pie(df_s, names='nivel', title="Distribución de Riesgo"), use_container_width=True)
        else: st.info("Sin datos para estadísticas.")

# --- TAB 6: AUDITORÍA (HABILITADO) [21, 25] ---
    with tabs[5]:
        st.markdown("## 🔍 Registro de Seguridad")
        logs = db.get_audit_log(limit=200)
        if logs: st.dataframe(pd.DataFrame(logs), use_container_width=True)
        else: st.info("Sin logs de auditoría.")

# Logout [26]
if st.sidebar.button("🚪 Cerrar Sesión"):
    st.session_state.clear()
    st.rerun()
