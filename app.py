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
# CONFIGURACIÓN Y ESTILOS MEJORADOS
# =============================================
st.set_page_config(
    page_title="NefroPredict RD",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Paleta de colores médica profesional [6]
PRIMARY = "#0066CC" 
SECONDARY = "#00A896"
DANGER = "#E63946"
WARNING = "#F77F00"
SUCCESS = "#06D6A0"
BG_LIGHT = "#F8F9FA"
TEXT_DARK = "#212529"

def hex_to_rgba(hex_color, alpha):
    """Convierte un color hexadecimal a cadena RGBA para Plotly [6, 7]."""
    hex_color = hex_color.lstrip('#')
    try:
        r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        return f'rgba({r}, {g}, {b}, {alpha})'
    except ValueError:
        return 'rgba(128, 128, 128, 0.2)'

# Header principal [7]
st.markdown(f"""
    <div style="text-align: center; padding: 20px; background-color: {PRIMARY}; color: white; border-radius: 10px; margin-bottom: 20px;">
        <h1>🏥 NefroPredict RD</h1>
        <p>Sistema Inteligente de Detección Temprana de ERC<br>República Dominicana • Versión 2.0</p>
    </div>
""", unsafe_allow_html=True)

# =============================================
# SEGURIDAD Y BASE DE DATOS [4, 7]
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
    if len(password) < 8:
        return False, "La contraseña debe tener al menos 8 caracteres"
    if not any(c.isdigit() for c in password):
        return False, "Debe contener al menos un número"
    if not any(c.isupper() for c in password):
        return False, "Debe contener al menos una mayúscula"
    return True, "Contraseña segura"

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
            "patients": [],
            "uploads": [],
            "audit_log": [],
            "sessions": {}
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
        if not user:
            self.log_audit(username, "Intento de login - usuario no existe", "LOGIN_FAILED")
            return None
        if user.get("login_attempts", 0) >= 5:
            last_attempt = user.get("last_attempt_time")
            if last_attempt:
                time_passed = (datetime.now() - datetime.fromisoformat(last_attempt)).seconds
                if time_passed < 300: return "BLOCKED"
                else: user["login_attempts"] = 0
        
        if verify_password(password, user.get("pwd", "")):
            if user.get("active", True):
                user["login_attempts"] = 0
                user["last_login"] = datetime.now().isoformat()
                self.save()
                self.log_audit(username, "Inicio de sesión exitoso", "LOGIN")
                return user
        else:
            user["login_attempts"] = user.get("login_attempts", 0) + 1
            user["last_attempt_time"] = datetime.now().isoformat()
            self.save()
            self.log_audit(username, f"Contraseña incorrecta", "LOGIN_FAILED")
        return None

    def log_audit(self, user, action, action_type="INFO"):
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "user": user, "action": action, "type": action_type
        }
        self.data["audit_log"].insert(0, log_entry)
        self.data["audit_log"] = self.data["audit_log"][:2000]
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
        if username in self.data["users"] and self.data["users"][username].get("role") == "doctor":
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
# MODELO CLÍNICO Y CÁLCULOS [8-10]
# =============================================
def calcular_tfg_ckdepi(creatinina, edad, sexo="hombre", raza="no_afro"):
    k = 0.7 if sexo == "mujer" else 0.9
    alpha = -0.329 if sexo == "mujer" else -0.411
    raza_factor = 1.159 if raza == "afro" else 1.0
    sexo_factor = 1.018 if sexo == "mujer" else 1.0
    min_k_cr = min(creatinina / k, 1)
    max_k_cr = max(creatinina / k, 1)
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
    # Simulación inteligente basada en factores clínicos [11]
    base = 10 + (row["creatinina"] - 1) * 32
    base += max(0, row["glucosa_ayunas"] - 126) * 0.3
    base += max(0, row["presion_sistolica"] - 140) * 0.2
    riesgo = round(max(1, min(99, base + np.random.uniform(-5, 8))), 1)
    return riesgo, tfg, estadio

def riesgo_level(risk):
    if risk > 70: return "MUY ALTO", DANGER, "Intervención URGENTE - Referir a nefrología inmediatamente"
    elif risk > 40: return "ALTO", WARNING, "Intervención Media - Control estricto y seguimiento mensual"
    else: return "MODERADO", SUCCESS, "Seguimiento Rutinario - Control cada 6 meses"

def get_doctor_recommendation(risk):
    if risk > 70: return "REFERENCIA URGENTE a NEFRÓLOGO. Iniciar estudios complementarios de inmediato (Proteinuria/ACR)."
    elif risk > 40: return "MONITOREO INTENSIVO. Evaluar ajuste de tratamiento con IECA/ARA-II. Repetir Creatinina en 1-3 meses."
    return "SEGUIMIENTO DE RUTINA (cada 6-12 meses). Mantener control metabólico."

# =============================================
# REPORTE PDF Y VISUALIZACIÓN [3, 12, 13]
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
        self.set_font('Arial', 'B', 12); self.cell(0, 10, title, 0, 1, 'L')
    def chapter_body(self, body):
        self.set_text_color(33, 37, 41); self.set_font('Arial', '', 11); self.multi_cell(0, 6, body); self.ln(2)

def crear_gauge_riesgo(riesgo):
    color = DANGER if riesgo > 70 else (WARNING if riesgo > 40 else SUCCESS)
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=riesgo,
        number={'suffix': "%", 'font': {'color': color}},
        gauge={
            'axis': {'range': }, 'bar': {'color': color},
            'steps': [
                {'range': [14], 'color': hex_to_rgba(SUCCESS, 0.2)},
                {'range': [14], 'color': hex_to_rgba(WARNING, 0.2)},
                {'range': , 'color': hex_to_rgba(DANGER, 0.2)}
            ]
        }
    ))
    fig.update_layout(height=250, margin=dict(l=20, r=20, t=30, b=20), paper_bgcolor='rgba(0,0,0,0)')
    return fig

# =============================================
# LÓGICA DE INTERFAZ (LOGIN Y TABS) [15, 16]
# =============================================
if "logged_in" not in st.session_state: st.session_state.logged_in = False

if not st.session_state.logged_in:
    col1, col2, col3 = st.columns([1, 6])
    with col2:
        st.markdown("### 🔐 Acceso Seguro")
        with st.form("login"):
            user_in = st.text_input("Usuario").lower().strip()
            pass_in = st.text_input("Contraseña", type="password")
            if st.form_submit_button("Iniciar Sesión", use_container_width=True):
                res = db.verify_login(user_in, pass_in)
                if res == "BLOCKED": st.error("Cuenta bloqueada por 5 min.")
                elif res:
                    st.session_state.logged_in = True
                    st.session_state.username = user_in
                    st.session_state.role = res['role']
                    st.session_state.doctor_name = res['name']
                    st.rerun()
                else: st.error("Credenciales incorrectas")
    st.stop()

# Barra Superior
st.sidebar.markdown(f"**Doctor/a:** {st.session_state.doctor_name}\n**Rol:** {st.session_state.role.upper()}")
if st.sidebar.button("🚪 Cerrar Sesión"):
    for k in list(st.session_state.keys()): del st.session_state[k]
    st.rerun()

# Menú de Tabs
tabs_labels = ["📋 Evaluación", "📤 Carga Masiva", "📊 Historial"]
if st.session_state.role == "admin": tabs_labels += ["👥 Usuarios", "📈 Estadísticas", "🔍 Auditoría"]
tabs = st.tabs(tabs_labels)

# --- TAB 1: EVALUACIÓN INDIVIDUAL ---
with tabs:
    col_f, col_r = st.columns([1])
    with col_f:
        with st.form("eval"):
            nombre = st.text_input("Nombre del Paciente")
            c1, c2 = st.columns(2)
            with c1:
                sexo = st.selectbox("Sexo", ["Hombre", "Mujer"])
                edad = st.number_input("Edad", 18, 120, 55)
                creat = st.number_input("Creatinina (mg/dL)", 0.1, 15.0, 1.1)
            with c2:
                raza = st.selectbox("Raza", ["No-Afroamericano", "Afroamericano"])
                glucosa = st.number_input("Glucosa (mg/dL)", 50, 500, 100)
                presion = st.number_input("Sistólica (mmHg)", 80, 250, 120)
            if st.form_submit_button("Analizar Riesgo"):
                if nombre:
                    datos = {"edad": edad, "creatinina": creat, "sexo": sexo, "raza": raza, "glucosa_ayunas": glucosa, "presion_sistolica": presion, "imc": 25.0}
                    riesgo, tfg, estadio = predecir(datos)
                    rec_p = get_doctor_recommendation(riesgo)
                    record = {**datos, "nombre_paciente": nombre, "riesgo": riesgo, "tfg": tfg, "estadio_erc": estadio, 
                              "doctor_user": st.session_state.username, "doctor_name": st.session_state.doctor_name,
                              "timestamp": datetime.now().isoformat(), "reco_privada": rec_p}
                    db.add_patient(record)
                    st.session_state.ultimo = record
                else: st.error("Nombre requerido")
    
    if "ultimo" in st.session_state:
        p = st.session_state.ultimo
        with col_r:
            st.plotly_chart(crear_gauge_riesgo(p["riesgo"]), use_container_width=True)
            nivel, color, rec_pub = riesgo_level(p["riesgo"])
            st.markdown(f"**Resultado:** {nivel} ({p['riesgo']}%)\n\n**TFG:** {p['tfg']} | **Estadio:** {p['estadio_erc']}")
            st.info(f"**Sugerencia Clínica:** {p['reco_privada']}")
            
            # PDF [17]
            pdf = PDFReport()
            pdf.add_page()
            pdf.chapter_title("Resultados", PRIMARY)
            pdf.chapter_body(f"Paciente: {p['nombre_paciente']}\nRiesgo: {p['riesgo']}%\nTFG: {p['tfg']} ({p['estadio_erc']})")
            pdf.chapter_title("Recomendación", DANGER)
            pdf.chapter_body(p['reco_privada'])
            st.download_button("⬇️ Descargar PDF", pdf.output(dest='S').encode('latin-1'), file_name="reporte.pdf", mime="application/pdf")

# --- TAB 2: CARGA MASIVA [18] ---
with tabs[1]:
    st.markdown("### Carga de CSV")
    file = st.file_uploader("Subir archivo", type="csv")
    if file and st.button("Procesar"):
        df = pd.read_csv(file)
        for _, r in df.iterrows():
            d = {"edad": r['edad'], "creatinina": r['creatinina'], "sexo": r['sexo'], "raza": r['raza'], "glucosa_ayunas": r['glucosa_ayunas'], "presion_sistolica": r['presion_sistolica'], "imc": 25.0}
            ri, tf, es = predecir(d)
            db.add_patient({**d, "nombre_paciente": r['nombre_paciente'], "riesgo": ri, "tfg": tf, "estadio_erc": es, "doctor_user": st.session_state.username, "timestamp": datetime.now().isoformat()})
        st.success("Procesado correctamente")

# --- TAB 3: HISTORIAL [19] ---
with tabs[6]:
    data = db.get_all_patients() if st.session_state.role == "admin" else db.get_patients_by_doctor(st.session_state.username)
    if data: st.dataframe(pd.DataFrame(data)[['timestamp', 'nombre_paciente', 'riesgo', 'tfg', 'estadio_erc']])

# --- TABS ADMIN [20-30] ---
if st.session_state.role == "admin":
    with tabs[7]: # Usuarios
        with st.form("new_user"):
            u, n, p = st.text_input("ID"), st.text_input("Nombre"), st.text_input("Pass", type="password")
            if st.form_submit_button("Crear"):
                db.create_doctor(u, p, n)
                st.rerun()
    with tabs[31]: # Estadísticas
        ps = db.get_all_patients()
        if ps:
            dfp = pd.DataFrame(ps)
            st.plotly_chart(px.pie(dfp, names='estadio_erc', title="Distribución por Estadio"))
    with tabs[4]: # Auditoría
        st.dataframe(db.get_audit_log())
