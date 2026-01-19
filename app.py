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
# SEGURIDAD Y BASE DE DATOS
# =============================================
def hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password, hashed):
    try:
        if not hashed.startswith('$2b$'):
            return password == hashed 
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    except:
        return False

def generate_session_token():
    return secrets.token_urlsafe(32)

def check_password_strength(password):
    if len(password) < 8: return False, "Mínimo 8 caracteres"
    if not any(c.isdigit() for c in password): return False, "Falta número"
    if not any(c.isupper() for c in password): return False, "Falta mayúscula"
    return True, "Segura"

DB_FILE = "nefro_db.json"

class DataStore:
    def __init__(self):
        if not os.path.exists(DB_FILE):
            self._create_initial_db()
        self.data = self._load()
        self._migrate_passwords()

    def _create_initial_db(self):
        initial = {
            "users": {
                "admin": {
                    "pwd": hash_password("Admin2024!"),
                    "role": "admin",
                    "name": "Administrador",
                    "active": True,
                    "created_at": datetime.now().isoformat(),
                    "last_login": None,
                    "login_attempts": 0
                }
            },
            "patients": [], "uploads": [], "audit_log": [], "sessions": {}
        }
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(initial, f, indent=4, ensure_ascii=False)

    def _load(self):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        defaults = {"users": {}, "patients": [], "uploads": [], "audit_log": [], "sessions": {}}
        for key, default in defaults.items():
            if key not in data: data[key] = default
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
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=4, ensure_ascii=False)

    def get_user(self, username):
        return self.data["users"].get(username)

    def verify_login(self, username, password):
        user = self.get_user(username)
        if not user: return None
        if user.get("login_attempts", 0) >= 5:
            last_attempt = user.get("last_attempt_time")
            if last_attempt:
                time_passed = (datetime.now() - datetime.fromisoformat(last_attempt)).seconds
                if time_passed < 300: return "BLOCKED"
        
        if verify_password(password, user.get("pwd", "")):
            if user.get("active", True):
                user["login_attempts"] = 0
                user["last_login"] = datetime.now().isoformat()
                self.save()
                self.log_audit(username, "Inicio de sesión", "LOGIN")
                return user
        else:
            user["login_attempts"] = user.get("login_attempts", 0) + 1
            user["last_attempt_time"] = datetime.now().isoformat()
            self.save()
        return None

    def log_audit(self, user, action, action_type="INFO"):
        log_entry = {"timestamp": datetime.now().isoformat(), "user": user, "action": action, "type": action_type}
        self.data.setdefault("audit_log", []).insert(0, log_entry)
        self.save()

    def add_patient(self, record):
        self.data["patients"].insert(0, record)
        self.save()

    def get_all_patients(self): return self.data["patients"]
    def get_patients_by_doctor(self, user_id):
        return [p for p in self.data["patients"] if p.get("doctor_user") == user_id]

    def create_doctor(self, username, password, full_name, created_by="admin"):
        self.data["users"][username] = {
            "pwd": hash_password(password), "role": "doctor", "name": full_name,
            "active": True, "created_at": datetime.now().isoformat(),
            "created_by": created_by, "last_login": None, "login_attempts": 0
        }
        self.save()

    def toggle_active(self, username, toggled_by="admin"):
        if username in self.data["users"]:
            self.data["users"][username]["active"] = not self.data["users"][username]["active"]
            self.save()

    def delete_doctor(self, username, deleted_by="admin"):
        if username in self.data["users"]:
            del self.data["users"][username]
            self.save()

    def update_password(self, username, new_pwd, updated_by="admin"):
        if username in self.data["users"]:
            self.data["users"][username]["pwd"] = hash_password(new_pwd)
            self.save()

    def get_audit_log(self, limit=100, user_filter="Todos", type_filter="Todos"):
        logs = self.data.get("audit_log", [])
        if user_filter != "Todos": logs = [l for l in logs if l.get("user") == user_filter]
        if type_filter != "Todos": logs = [l for l in logs if l.get("type") == type_filter]
        return logs[:limit]

db = DataStore()

# =============================================
# MODELO CLÍNICO Y CÁLCULOS
# =============================================
def calcular_tfg_ckdepi(creatinina, edad, sexo="hombre", raza="no_afro"):
    k = 0.7 if sexo == "mujer" else 0.9
    alpha = -0.329 if sexo == "mujer" else -0.411
    raza_factor = 1.159 if raza == "afro" else 1.0
    sexo_factor = 1.018 if sexo == "mujer" else 1.0
    min_k_cr, max_k_cr = min(creatinina / k, 1), max(creatinina / k, 1)
    TFG = 141 * (min_k_cr ** alpha) * (max_k_cr ** -1.209) * (0.993 ** edad) * sexo_factor * raza_factor
    return round(TFG)

def clasificar_erc(tfg):
    if tfg >= 90: return "G1 (Normal o Alto)"
    elif tfg >= 60: return "G2 (Levemente Disminuido)"
    elif tfg >= 45: return "G3a (Disminución Leve a Moderada)"
    elif tfg >= 30: return "G3b (Disminución Moderada a Severa)"
    elif tfg >= 15: return "G4 (Disminución Severa)"
    else: return "G5 (Fallo Renal)"

def predecir(row):
    sexo_tfg = "mujer" if row.get("sexo") == "Mujer" else "hombre"
    raza_tfg = "afro" if "Afro" in row.get("raza", "") else "no_afro"
    tfg = calcular_tfg_ckdepi(row["creatinina"], row["edad"], sexo_tfg, raza_tfg)
    estadio = clasificar_erc(tfg)
    base = 10 + (row["creatinina"] - 1) * 32 + max(0, row["glucosa_ayunas"] - 126) * 0.3
    base += max(0, row["presion_sistolica"] - 140) * 0.2
    riesgo = round(max(1, min(99, base + np.random.uniform(-5, 8))), 1)
    return riesgo, tfg, estadio

def riesgo_level(risk):
    if risk > 70: return "MUY ALTO", DANGER, "Intervención URGENTE - Referir a nefrología inmediatamente", "Grave"
    elif risk > 40: return "ALTO", WARNING, "Intervención Media - Control estricto y seguimiento mensual", "Intermedio"
    else: return "MODERADO", SUCCESS, "Seguimiento Rutinario - Control cada 6 meses", "Normal"

def get_doctor_recommendation(risk):
    if risk > 70: return "REFERENCIA URGENTE a NEFRÓLOGO. Iniciar estudios complementarios de inmediato."
    elif risk > 40: return "MONITOREO INTENSIVO. Evaluar ajuste de tratamiento con IECA/ARA-II."
    return "SEGUIMIENTO DE RUTINA (cada 6-12 meses)."

# =============================================
# REPORTE PDF Y GAUGE
# =============================================
class PDFReport(FPDF):
    def header(self):
        self.set_fill_color(0, 102, 204)
        self.rect(0, 0, 210, 20, 'F')
        self.set_text_color(255, 255, 255)
        self.set_font('Arial', 'B', 15)
        self.cell(0, 10, 'NefroPredict RD - Reporte de Evaluación', 0, 1, 'C')
    def chapter_title(self, title, color_hex):
        r, g, b = tuple(int(color_hex.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
        self.set_text_color(r, g, b)
        self.set_font('Arial', 'B', 14); self.cell(0, 10, title, 0, 1, 'L')
    def chapter_body(self, body):
        self.set_text_color(33, 37, 41); self.set_font('Arial', '', 12); self.multi_cell(0, 7, body)

def crear_gauge_riesgo(riesgo):
    color = DANGER if riesgo > 70 else (WARNING if riesgo > 40 else SUCCESS)
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=riesgo,
        number={'suffix': "%", 'font': {'color': color}},
        gauge={'axis': {'range': }, 'bar': {'color': color},
               'steps': [{'range': [3], 'color': hex_to_rgba(SUCCESS, 0.2)},
                         {'range': [3], 'color': hex_to_rgba(WARNING, 0.2)},
                         {'range': , 'color': hex_to_rgba(DANGER, 0.2)}]}
    ))
    fig.update_layout(height=350, margin=dict(l=20, r=20, t=60, b=20), paper_bgcolor='rgba(0,0,0,0)')
    return fig

# =============================================
# LÓGICA DE INTERFAZ
# =============================================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    # CORRECCIÓN DE ERROR: 3 variables para 3 columnas [1, 4]
    col1, col2, col3 = st.columns([1, 4])
    with col2:
        st.markdown("### 🔐 Acceso Seguro")
        with st.form("login"):
            u = st.text_input("Usuario").lower().strip()
            p = st.text_input("Contraseña", type="password")
            if st.form_submit_button("Entrar", use_container_width=True):
                res = db.verify_login(u, p)
                if res == "BLOCKED": st.error("Cuenta bloqueada por 5 min.")
                elif res:
                    st.session_state.update({"logged_in": True, "username": u, "role": res["role"], "doctor_name": res["name"]})
                    st.rerun()
                else: st.error("❌ Credenciales incorrectas")
    st.stop()

# Logout y Encabezado
col_logout1, col_logout2 = st.columns([4, 5])
with col_logout2:
    if st.button("🚪 Salir"):
        st.session_state.clear()
        st.rerun()

# Tabs según Rol
tabs_labels = ["📋 Evaluación", "📤 Carga Masiva", "📊 Historial"]
if st.session_state.role == "admin":
    tabs_labels += ["👥 Usuarios", "📈 Estadísticas", "🔍 Auditoría"]

tabs = st.tabs(tabs_labels)

# --- TAB EVALUACIÓN ---
with tabs:
    c_form, c_res = st.columns([1.2, 1])
    with c_form:
        with st.form("f_eval"):
            nom = st.text_input("Nombre del Paciente")
            ca, cb = st.columns(2)
            with ca:
                sex = st.selectbox("Sexo", ["Hombre", "Mujer"])
                ed = st.number_input("Edad", 18, 120, 55)
                creat = st.number_input("Creatinina", 0.1, 15.0, 1.1)
            with cb:
                raz = st.selectbox("Raza", ["No-Afroamericano", "Afroamericano"])
                gluc = st.number_input("Glucosa", 50, 500, 100)
                pres = st.number_input("Sistólica", 80, 250, 120)
            if st.form_submit_button("Analizar"):
                if nom:
                    r, tf, es = predecir({"edad": ed, "creatinina": creat, "sexo": sex, "raza": raz, "glucosa_ayunas": gluc, "presion_sistolica": pres})
                    rec_p = get_doctor_recommendation(r)
                    rec = {"nombre_paciente": nom, "riesgo": r, "tfg": tf, "estadio_erc": es, "doctor_user": st.session_state.username, 
                           "timestamp": datetime.now().isoformat(), "reco_privada": rec_p, "doctor_name": st.session_state.doctor_name,
                           "edad": ed, "creatinina": creat, "glucosa_ayunas": gluc, "presion_sistolica": pres, "imc": 25.0}
                    db.add_patient(rec)
                    st.session_state.ultimo = rec
                else: st.error("Falta nombre")
    
    if "ultimo" in st.session_state:
        with c_res:
            p = st.session_state.ultimo
            st.plotly_chart(crear_gauge_riesgo(p["riesgo"]), use_container_width=True)
            nivel, _, _, _ = riesgo_level(p["riesgo"])
            st.markdown(f"**Resultado:** {nivel} ({p['riesgo']}%)\n\n**TFG:** {p['tfg']} | **Estadio:** {p['estadio_erc']}")
            st.warning(f"**Sugerencia:** {p['reco_privada']}")

# --- TAB CARGA MASIVA ---
with tabs[4]:
    file = st.file_uploader("Subir CSV", type="csv")
    if file and st.button("Procesar"):
        df = pd.read_csv(file)
        for _, row in df.iterrows():
            d = {"edad": row['edad'], "creatinina": row['creatinina'], "sexo": row['sexo'], "raza": row['raza'], "glucosa_ayunas": row['glucosa_ayunas'], "presion_sistolica": row['presion_sistolica']}
            r, tf, es = predecir(d)
            db.add_patient({**d, "nombre_paciente": row['nombre_paciente'], "riesgo": r, "tfg": tf, "estadio_erc": es, "doctor_user": st.session_state.username, "timestamp": datetime.now().isoformat()})
        st.success("Completado")

# --- TAB HISTORIAL ---
with tabs[1]:
    pats = db.get_all_patients() if st.session_state.role == "admin" else db.get_patients_by_doctor(st.session_state.username)
    if pats:
        df_h = pd.DataFrame(pats)
        # CORRECCIÓN DE KEYERROR: Solo mostramos columnas si existen
        cols = ['timestamp', 'nombre_paciente', 'riesgo', 'tfg', 'estadio_erc']
        if st.session_state.role == "admin": cols.insert(2, 'doctor_name')
        st.dataframe(df_h[[c for c in cols if c in df_h.columns]].sort_values(by='timestamp', ascending=False))

# --- TABS EXCLUSIVAS ADMIN ---
if st.session_state.role == "admin":
    with tabs[2]: # Usuarios
        with st.form("new_u"):
            u_id, u_nom, u_pwd = st.text_input("ID"), st.text_input("Nombre"), st.text_input("Pass", type="password")
            if st.form_submit_button("Crear"):
                db.create_doctor(u_id, u_pwd, u_nom)
                st.rerun()
    with tabs[6]: # Estadísticas (HABILITADO)
        data_all = db.get_all_patients()
        if data_all:
            df_s = pd.DataFrame(data_all)
            c1, c2 = st.columns(2)
            with c1: st.plotly_chart(px.pie(df_s, names='estadio_erc', title="Distribución por Estadio"))
            with c2: 
                if 'riesgo' in df_s: st.metric("Riesgo Promedio", f"{df_s['riesgo'].mean():.1f}%")
    with tabs[7]: # Auditoría (HABILITADO)
        st.dataframe(pd.DataFrame(db.get_audit_log()))

st.markdown("<hr><center>© 2024 NefroPredict RD</center>", unsafe_allow_html=True)
