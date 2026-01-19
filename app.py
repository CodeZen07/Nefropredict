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
# CONFIGURACIÓN Y ESTILOS [2-4]
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
# SEGURIDAD Y BASE DE DATOS [5-9]
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

    def _create_initial_db(self):
        initial = {
            "users": {"admin": {"pwd": hash_password("Admin2024!"), "role": "admin", "name": "Administrador", "active": True}},
            "patients": [], "audit_log": []
        }
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(initial, f, indent=4, ensure_ascii=False)

    def _load(self):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)

    def save(self):
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=4, ensure_ascii=False)

    def verify_login(self, username, password):
        user = self.data["users"].get(username)
        if user and verify_password(password, user["pwd"]) and user.get("active", True):
            self.log_audit(username, "Inicio de sesión", "LOGIN")
            return user
        return None

    def log_audit(self, user, action, action_type="INFO"):
        log_entry = {"timestamp": datetime.now().isoformat(), "user": user, "action": action, "type": action_type}
        self.data.setdefault("audit_log", []).insert(0, log_entry)
        self.save()

    def add_patient(self, record):
        self.data.setdefault("patients", []).insert(0, record)
        self.save()

    def get_all_patients(self): return self.data.get("patients", [])
    def get_audit_log(self): return self.data.get("audit_log", [])

db = DataStore()

# =============================================
# MODELO CLÍNICO Y CÁLCULOS [10-14]
# =============================================
def calcular_tfg_ckdepi(creatinina, edad, sexo="hombre", raza="no_afro"):
    k, alpha = (0.7, -0.329) if sexo == "mujer" else (0.9, -0.411)
    r_f = 1.159 if raza == "afro" else 1.0
    s_f = 1.018 if sexo == "mujer" else 1.0
    tfg = 141 * (min(creatinina/k, 1)**alpha) * (max(creatinina/k, 1)**-1.209) * (0.993**edad) * s_f * r_f
    return round(tfg)

def clasificar_erc(tfg):
    if tfg >= 90: return "G1 (Normal o Alto)"
    elif tfg >= 60: return "G2 (Levemente Disminuido)"
    elif tfg >= 45: return "G3a (Disminución Leve a Moderada)"
    elif tfg >= 30: return "G3b (Disminución Moderada a Severa)"
    elif tfg >= 15: return "G4 (Disminución Severa)"
    else: return "G5 (Fallo Renal)"

def predecir(row):
    tfg = calcular_tfg_ckdepi(row["creatinina"], row["edad"], row["sexo"].lower(), "afro" if "Afro" in row["raza"] else "no_afro")
    base = 10 + (row["creatinina"] - 1) * 32 + max(0, row["glucosa_ayunas"] - 126) * 0.3
    riesgo = round(max(1, min(99, base + np.random.uniform(-5, 5))), 1)
    return riesgo, tfg, clasificar_erc(tfg)

def riesgo_level(risk):
    if risk > 70: return "MUY ALTO", DANGER, "Referencia URGENTE", "Grave"
    elif risk > 40: return "ALTO", WARNING, "Monitoreo intensivo", "Intermedio"
    return "MODERADO", SUCCESS, "Seguimiento rutinario", "Normal"

# =============================================
# INTERFAZ DE USUARIO [15-20]
# =============================================
if not st.session_state.get("logged_in"):
    st.title("🏥 NefroPredict RD")
    with st.form("login"):
        u = st.text_input("Usuario").lower().strip()
        p = st.text_input("Contraseña", type="password")
        if st.form_submit_button("Entrar"):
            res = db.verify_login(u, p)
            if res:
                st.session_state.update({"logged_in": True, "username": u, "role": res["role"], "doctor_name": res["name"]})
                st.rerun()
    st.stop()

# --- TABS DINÁMICAS [20] ---
tabs_list = ["📋 Evaluación", "📤 Carga Masiva", "📊 Historial"]
if st.session_state.role == "admin": tabs_list += ["📈 Estadísticas", "🔍 Auditoría"]
tabs = st.tabs(tabs_list)

# --- TAB 1: EVALUACIÓN [21-26] ---
with tabs:
    with st.form("eval"):
        nom = st.text_input("Nombre del Paciente")
        c1, c2 = st.columns(2)
        with c1:
            sex = st.selectbox("Sexo", ["Hombre", "Mujer"])
            ed = st.number_input("Edad", 18, 120, 55)
            cre = st.number_input("Creatinina", 0.1, 15.0, 1.2)
        with c2:
            raz = st.selectbox("Raza", ["No-Afroamericano", "Afroamericano"])
            glu = st.number_input("Glucosa", 50, 500, 100)
            pre = st.number_input("Presión Sistólica", 80, 250, 120)
        if st.form_submit_button("Analizar"):
            datos = {"nombre_paciente": nom, "edad": ed, "creatinina": cre, "sexo": sex, "raza": raz, "glucosa_ayunas": glu, "presion_sistolica": pre, "imc": 25.0}
            ri, tf, es = predecir(datos)
            nivel, _, rec, _ = riesgo_level(ri)
            record = {**datos, "riesgo": ri, "tfg": tf, "estadio_erc": es, "nivel": nivel, "doctor_name": st.session_state.doctor_name, "timestamp": datetime.now().isoformat()}
            db.add_patient(record)
            st.success(f"Riesgo: {ri}% - {nivel}")

# --- TAB 3: HISTORIAL (CORRECCIÓN KEYERROR) [1] ---
with tabs[3]:
    st.header("Historial de Evaluaciones")
    pats = db.get_all_patients()
    if pats:
        df = pd.DataFrame(pats)
        # CORRECCIÓN DINÁMICA: Solo selecciona columnas que existen
        cols_posibles = ['timestamp', 'nombre_paciente', 'riesgo', 'nivel', 'tfg', 'estadio_erc', 'doctor_name']
        cols_visibles = [c for c in cols_posibles if c in df.columns]
        st.dataframe(df[cols_visibles].sort_values(by='timestamp', ascending=False))
    else: st.info("Sin registros.")

# --- TABS ADMIN: ESTADÍSTICAS Y AUDITORÍA [27-32] ---
if st.session_state.role == "admin":
    with tabs[4]:
        st.header("Estadísticas Globales")
        all_p = db.get_all_patients()
        if all_p:
            df_s = pd.DataFrame(all_p)
            st.metric("Total Pacientes", len(df_s))
            if 'riesgo' in df_s: st.plotly_chart(px.pie(df_s, names='nivel', title="Distribución de Riesgo"))
    
    with tabs[5]:
        st.header("Auditoría del Sistema")
        logs = db.get_audit_log()
        if logs: st.dataframe(pd.DataFrame(logs))

if st.sidebar.button("Cerrar Sesión"):
    st.session_state.clear()
    st.rerun()
