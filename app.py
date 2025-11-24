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

# Paleta de colores médica profesional
PRIMARY = "#0066CC"      # Azul médico profesional
SECONDARY = "#00A896"    # Verde azulado (salud)
DANGER = "#E63946"       # Rojo médico
WARNING = "#F77F00"      # Naranja cálido
SUCCESS = "#06D6A0"      # Verde éxito
BG_LIGHT = "#F8F9FA"
TEXT_DARK = "#212529"

# Función auxiliar para convertir HEX a RGBA
def hex_to_rgba(hex_color, alpha):
    """Convierte un color hexadecimal de 6 dígitos a una cadena RGBA."""
    hex_color = hex_color.lstrip('#')
    try:
        r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        return f'rgba({r}, {g}, {b}, {alpha})'
    except ValueError:
        return 'rgba(128, 128, 128, 0.2)'


st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    * {{
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }}
    
    /* Estilos generales */
    .main {{
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
    }}
    
    h1, h2, h3, h4, h5 {{
        color: #ffffff !important;
        font-weight: 600 !important;
    }}
    
    /* Botones mejorados */
    .stButton>button {{
        background: linear-gradient(135deg, {PRIMARY}, {SECONDARY});
        color: white;
        border: none;
        border-radius: 10px;
        padding: 0.6rem 1.8rem;
        font-weight: 600;
        font-size: 0.95rem;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(0,102,204,0.2);
    }}
    
    .stButton>button:hover {{
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(0,102,204,0.3);
    }}
    
    /* Cards de métricas */
    .metric-card {{
        background: #2d3748;
        padding: 25px;
        border-radius: 15px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.3);
        border-left: 5px solid {PRIMARY};
        transition: all 0.3s ease;
        color: white;
    }}
    
    .metric-card:hover {{
        transform: translateY(-5px);
        box-shadow: 0 8px 25px rgba(0,0,0,0.12);
    }}
    
    /* Tarjetas de riesgo */
    .risk-card {{
        padding: 30px;
        border-radius: 20px;
        text-align: center;
        box-shadow: 0 8px 30px rgba(0,0,0,0.12);
        animation: fadeIn 0.5s ease-in;
    }}
    
    @keyframes fadeIn {{
        from {{ opacity: 0; transform: scale(0.95); }}
        to {{ opacity: 1; transform: scale(1); }}
    }}
    
    .risk-high {{
        background: linear-gradient(135deg, {DANGER}22, {DANGER}11);
        border: 3px solid {DANGER};
    }}
    
    .risk-med {{
        background: linear-gradient(135deg, {WARNING}22, {WARNING}11);
        border: 3px solid {WARNING};
    }}
    
    .risk-low {{
        background: linear-gradient(135deg, {SUCCESS}22, {SUCCESS}11);
        border: 3px solid {SUCCESS};
    }}
    
    /* Tabs personalizados */
    .stTabs [data-baseweb="tab-list"] {{
        gap: 10px;
        background: #2d3748;
        padding: 10px;
        border-radius: 15px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.3);
    }}
    
    .stTabs [data-baseweb="tab"] {{
        border-radius: 10px;
        padding: 10px 20px;
        font-weight: 600;
        transition: all 0.3s ease;
        color: #cbd5e0;
    }}
    
    .stTabs [aria-selected="true"] {{
        background: linear-gradient(135deg, {PRIMARY}, {SECONDARY});
        color: white !important;
    }}
    
    /* Inputs mejorados */
    .stTextInput input, .stNumberInput input, .stSelectbox select {{
        border-radius: 10px;
        border: 2px solid #4a5568;
        background: #2d3748;
        color: white;
        transition: all 0.3s ease;
    }}
    
    .stTextInput input:focus, .stNumberInput input:focus {{
        border-color: {PRIMARY};
        box-shadow: 0 0 0 3px {PRIMARY}22;
        background: #374151;
    }}
    
    /* Labels de inputs */
    .stTextInput label, .stNumberInput label, .stSelectbox label {{
        color: #e2e8f0 !important;
    }}
    
    /* Notificaciones */
    .stSuccess, .stError, .stWarning, .stInfo {{
        border-radius: 10px;
        border-left: 5px solid;
        background: #2d3748;
        color: white;
    }}
    
    /* Footer */
    .footer {{
        text-align: center;
        padding: 20px;
        color: #cbd5e0;
        font-size: 0.9em;
        background: #2d3748;
        border-radius: 15px;
        margin-top: 30px;
    }}
    
    /* Login especial */
    .login-container {{
        background: #2d3748;
        padding: 40px;
        border-radius: 20px;
        box-shadow: 0 10px 40px rgba(0,0,0,0.5);
    }}
    
    /* Contenedores generales */
    .stMarkdown, .stDataFrame {{
        color: #e2e8f0;
    }}
    
    /* Sidebar oscuro */
    [data-testid="stSidebar"] {{
        background: #1a202c;
    }}
</style>
""", unsafe_allow_html=True)

# Header principal
st.markdown(f"""
<div style='text-align:center; padding: 30px 0; background: linear-gradient(135deg, #2d3748, #1a202c); border-radius: 20px; margin-bottom: 30px; box-shadow: 0 4px 15px rgba(0,0,0,0.3);'>
    <h1 style='color: {PRIMARY}; font-size: 3em; margin: 0;'>🏥 NefroPredict RD</h1>
    <p style='color: #cbd5e0; font-size: 1.2em; margin-top: 10px;'>Sistema Inteligente de Detección Temprana de ERC</p>
    <p style='color: #718096; font-size: 0.9em;'>República Dominicana • Versión 2.0</p>
</div>
""", unsafe_allow_html=True)

# =============================================
# SEGURIDAD Y DB
# =============================================

def hash_password(password):
    """Encripta contraseña con bcrypt"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password, hashed):
    """Verifica contraseña"""
    try:
        if not hashed.startswith('$2b$'):
            return password == hashed  # Compatibilidad con contraseñas antiguas
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    except:
        return False

def generate_session_token():
    """Genera token de sesión único"""
    return secrets.token_urlsafe(32)

def check_password_strength(password):
    """Valida fortaleza de contraseña"""
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
        
        # Asegurar todas las keys necesarias
        defaults = {
            "users": {},
            "patients": [],
            "uploads": [],
            "audit_log": [],
            "sessions": {}
        }
        for key, default in defaults.items():
            if key not in data:
                data[key] = default
        
        # Asegurar estructura de usuario completa
        for username, user in data.get("users", {}).items():
            user['role'] = user.get('role', 'doctor')
            user['active'] = user.get('active', True)
            user['login_attempts'] = user.get('login_attempts', 0)
            if 'created_at' not in user:
                 user['created_at'] = datetime.now().isoformat()

        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        return data

    def _migrate_passwords(self):
        """Migra contraseñas antiguas"""
        migrated = False
        for username, user_data in self.data["users"].items():
            pwd = user_data.get("pwd", "")
            if pwd and not pwd.startswith('$2b$'):
                self.data["users"][username]["pwd"] = hash_password(pwd)
                migrated = True
        if migrated:
            self.save()
            self.log_audit("SYSTEM", "Migración de contraseñas completada", "SECURITY")

    def save(self):
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=4, ensure_ascii=False)

    def get_user(self, username):
        return self.data["users"].get(username)

    def verify_login(self, username, password):
        """Login con protección contra fuerza bruta"""
        user = self.get_user(username)
        if not user:
            self.log_audit(username, "Intento de login - usuario no existe", "LOGIN_FAILED")
            return None
        
        # Protección contra fuerza bruta
        if user.get("login_attempts", 0) >= 5:
            last_attempt = user.get("last_attempt_time")
            if last_attempt:
                time_passed = (datetime.now() - datetime.fromisoformat(last_attempt)).seconds
                if time_passed < 300:  # 5 minutos de bloqueo
                    self.log_audit(username, "Cuenta bloqueada temporalmente", "LOGIN_BLOCKED")
                    return "BLOCKED"
                else:
                    user["login_attempts"] = 0
        
        if verify_password(password, user.get("pwd", "")):
            if user.get("active", True):
                user["login_attempts"] = 0
                user["last_login"] = datetime.now().isoformat()
                self.save()
                self.log_audit(username, "Inicio de sesión exitoso", "LOGIN")
                return user
            else:
                self.log_audit(username, "Intento de login - cuenta inactiva", "LOGIN_FAILED")
                return None
        else:
            user["login_attempts"] = user.get("login_attempts", 0) + 1
            user["last_attempt_time"] = datetime.now().isoformat()
            self.save()
            self.log_audit(username, f"Contraseña incorrecta (intento {user['login_attempts']})", "LOGIN_FAILED")
            return None

    def create_doctor(self, username, password, full_name, created_by="admin"):
        self.data["users"][username] = {
            "pwd": hash_password(password),
            "role": "doctor",
            "name": full_name,
            "active": True,
            "created_at": datetime.now().isoformat(),
            "created_by": created_by,
            "last_login": None,
            "login_attempts": 0
        }
        self.save()
        self.log_audit(created_by, f"Creó doctor: {full_name} (@{username})", "USER_CREATED")

    def update_password(self, username, new_pwd, updated_by="admin"):
        if username in self.data["users"]:
            self.data["users"][username]["pwd"] = hash_password(new_pwd)
            self.data["users"][username]["login_attempts"] = 0
            self.save()
            self.log_audit(updated_by, f"Cambió contraseña de @{username}", "PASSWORD_CHANGED")

    def toggle_active(self, username, toggled_by="admin"):
        if username in self.data["users"]:
            self.data["users"][username]["active"] = not self.data["users"][username]["active"]
            estado = "activada" if self.data["users"][username]["active"] else "desactivada"
            self.save()
            self.log_audit(toggled_by, f"Cuenta @{username} {estado}", "USER_STATUS_CHANGED")

    def delete_doctor(self, username, deleted_by="admin"):
        if username in self.data["users"] and self.data["users"][username].get("role") == "doctor":
            nombre = self.data["users"][username].get("name", username)
            del self.data["users"][username]
            self.save()
            self.log_audit(deleted_by, f"Eliminó doctor: {nombre} (@{username})", "USER_DELETED")

    def add_patient(self, record):
        self.data["patients"].insert(0, record)
        self.save()

    def get_patients_by_doctor(self, user_id):
        return [p for p in self.data["patients"] if p.get("doctor_user") == user_id]

    def get_all_patients(self):
        return self.data["patients"]

    def add_upload_log(self, log):
        self.data["uploads"].insert(0, log)
        self.save()

    def log_audit(self, user, action, action_type="INFO"):
        """Registro de auditoría"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "user": user,
            "action": action,
            "type": action_type,
            "ip": "N/A"  # Streamlit no expone IP fácilmente
        }
        self.data["audit_log"].insert(0, log_entry)
        self.data["audit_log"] = self.data["audit_log"][:2000] # Aumentar límite
        self.save()

    def get_audit_log(self, limit=100, user_filter=None, type_filter=None):
        logs = self.data.get("audit_log", [])
        if user_filter and user_filter != "Todos":
            logs = [l for l in logs if l.get("user") == user_filter]
        if type_filter and type_filter != "Todos":
            logs = [l for l in logs if l.get("type") == type_filter]
        return logs[:limit]

db = DataStore()

# =============================================
# MODELO DE PREDICCIÓN Y CLASIFICACIÓN
# =============================================
@st.cache_resource
def load_model():
    # Simular carga del modelo
    try:
        # En un entorno real, descomentar: return joblib.load("modelo_erc.joblib")
        return None 
    except:
        return None

model = load_model()

def predecir(row):
    # Estandarización de entradas para TFG
    sexo_tfg = "mujer" if row.get("sexo", "Hombre") == "Mujer" else "hombre"
    raza_tfg = "afro" if row.get("raza", "No-Afroamericano") == "Afroamericano" else "no_afro"
    
    # 1. CALCULAR TFG Y ESTADIO
    tfg = calcular_tfg_ckdepi(row["creatinina"], row["edad"], sexo_tfg, raza_tfg)
    estadio = clasificar_erc(tfg)

    # 2. PREDICCIÓN DEL RIESGO
    # El modelo real usaría: model.predict_proba(...)
    
    # Simulación inteligente basada en factores clínicos
    base = 10
    base += (row["creatinina"] - 1) * 32
    base += max(0, row["glucosa_ayunas"] - 126) * 0.3
    base += max(0, row["presion_sistolica"] - 140) * 0.2
    base += max(0, row["imc"] - 30) * 0.5
    base += max(0, row["edad"] - 60) * 0.3
    riesgo = round(max(1, min(99, base + np.random.uniform(-5, 8))), 1)

    return riesgo, tfg, estadio

def riesgo_level(risk):
    if risk > 70:
        return "MUY ALTO", DANGER, "Intervención URGENTE - Referir a nefrología inmediatamente", "Grave"
    elif risk > 40:
        return "ALTO", WARNING, "Intervención Media - Control estricto y seguimiento mensual", "Intermedio"
    else:
        return "MODERADO", SUCCESS, "Seguimiento Rutinario - Control cada 6 meses", "Normal"

def get_doctor_recommendation(risk):
    """Genera una recomendación médica detallada (solo para el doctor)."""
    if risk > 70:
        return "REFERENCIA URGENTE a NEFRÓLOGO. Iniciar estudios complementarios de inmediato (Proteinuria 24h/ACR, Fondo de Ojo). Considerar modificación de dieta y tratamiento antihipertensivo con bloqueo del SRAA."
    elif risk > 40:
        return "MONITOREO INTENSIVO. Evaluar inicio/ajuste de tratamiento con IECA/ARA-II. Repetir Creatinina/TFG en 1-3 meses. Control estricto de TA (<130/80 mmHg) y Glucemia (HbA1c <7.0%). Educación al paciente sobre dieta."
    else:
        return "SEGUIMIENTO DE RUTINA (cada 6-12 meses). Mantener control de factores de riesgo metabólicos y cardiovasculares. Enfatizar cambios en el estilo de vida (ejercicio, dieta)."

# =============================================
# FUNCIONES CLÍNICAS AVANZADAS
# =============================================

def calcular_tfg_ckdepi(creatinina, edad, sexo="hombre", raza="no_afro"):
    """
    Calcula la Tasa de Filtración Glomerular (TFG) usando la fórmula CKD-EPI (2009).
    """
    k = 0.7 if sexo == "mujer" else 0.9
    alpha = -0.329 if sexo == "mujer" else -0.411
    raza_factor = 1.159 if raza == "afro" else 1.0
    sexo_factor = 1.018 if sexo == "mujer" else 1.0
    
    min_k_cr = min(creatinina / k, 1)
    max_k_cr = max(creatinina / k, 1)
    
    TFG = 141 * (min_k_cr ** alpha) * (max_k_cr ** -1.209) * (0.993 ** edad) * sexo_factor * raza_factor
    
    return round(TFG)

def clasificar_erc(tfg):
    """Clasifica el estadio de la Enfermedad Renal Crónica (ERC) basado en la TFG."""
    if tfg >= 90:
        return "G1 (Normal o Alto)"
    elif tfg >= 60:
        return "G2 (Levemente Disminuido)"
    elif tfg >= 45:
        return "G3a (Disminución Leve a Moderada)"
    elif tfg >= 30:
        return "G3b (Disminución Moderada a Severa)"
    elif tfg >= 15:
        return "G4 (Disminución Severa)"
    else:
        return "G5 (Fallo Renal)"

# Clase para la Generación de PDF
class PDFReport(FPDF):
    def header(self):
        global PRIMARY
        self.set_fill_color(0, 102, 204) # PRIMARY
        self.rect(0, 0, 210, 20, 'F')
        self.set_text_color(255, 255, 255)
        self.set_font('Arial', 'B', 15)
        self.cell(0, 10, 'NefroPredict RD - Reporte de Evaluación', 0, 1, 'C')
        self.set_line_width(1.0)
        self.line(10, 18, 200, 18)
        self.ln(10)

    def chapter_title(self, title, color_hex):
        r, g, b = tuple(int(color_hex.strip('#')[i:i+2], 16) for i in (0, 2, 4))
        self.set_text_color(r, g, b)
        self.set_font('Arial', 'B', 14)
        self.cell(0, 10, title, 0, 1, 'L')
        self.ln(2)

    def chapter_body(self, body):
        self.set_text_color(33, 37, 41) # TEXT_DARK
        self.set_font('Arial', '', 12)
        self.multi_cell(0, 7, body)
        self.ln()
        
    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, f'Página {self.page_no()}/{{nb}} | Evaluación generada por NefroPredict RD', 0, 0, 'C')


def crear_gauge_riesgo(riesgo):
    """Gráfico de velocímetro mejorado con corrección RGBA."""
    if riesgo > 70:
        color = DANGER
    elif riesgo > 40:
        color = WARNING
    else:
        color = SUCCESS
    
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=riesgo,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': "Riesgo de ERC (%)", 'font': {'size': 20, 'color': PRIMARY}},
        number={'suffix': "%", 'font': {'size': 50, 'color': color}},
        gauge={
            'axis': {'range': [0, 100], 'tickwidth': 2, 'tickcolor': PRIMARY},
            'bar': {'color': color, 'thickness': 0.75},
            'bgcolor': "white",
            'borderwidth': 3,
            'bordercolor': PRIMARY,
            'steps': [
                # CORRECCIÓN: Usar la función hex_to_rgba para la transparencia
                {'range': [0, 40], 'color': hex_to_rgba(SUCCESS, 0.2)},
                {'range': [40, 70], 'color': hex_to_rgba(WARNING, 0.2)},
                {'range': [70, 100], 'color': hex_to_rgba(DANGER, 0.2)}
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.85,
                'value': riesgo
            }
        }
    ))
    fig.update_layout(
        height=350,
        margin=dict(l=20, r=20, t=60, b=20),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )
    return fig

# =============================================
# LOGIN MEJORADO
# =============================================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("""
        <div class='login-container'>
            <div style='text-align:center; margin-bottom:30px;'>
                <h2 style='color: #0066CC;'>🔐 Acceso Seguro</h2>
                <p style='color:#cbd5e0;'>Ingrese sus credenciales</p>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        with st.form("login_form"):
            username = st.text_input("👤 Usuario", placeholder="Ingrese su usuario").lower().strip()
            password = st.text_input("🔑 Contraseña", type="password", placeholder="Ingrese su contraseña")
            
            col_btn1, col_btn2 = st.columns(2)
            with col_btn1:
                submitted = st.form_submit_button("Iniciar Sesión", use_container_width=True)
            with col_btn2:
                forgot = st.form_submit_button("¿Olvidó su contraseña?", use_container_width=True)
            
            if submitted:
                if not username or not password:
                    st.error("❌ Por favor complete todos los campos")
                else:
                    result = db.verify_login(username, password)
                    
                    if result == "BLOCKED":
                        st.error("🚫 Cuenta bloqueada temporalmente por múltiples intentos fallidos. Intente en 5 minutos.")
                    elif result:
                        st.session_state.logged_in = True
                        st.session_state.username = username
                        st.session_state.role = result.get("role", "doctor")
                        st.session_state.doctor_name = result.get("name", username)
                        st.session_state.session_token = generate_session_token()
                        st.success("✅ Acceso exitoso")
                        st.rerun()
                    else:
                        user = db.get_user(username)
                        if user:
                            intentos_restantes = max(0, 5 - user.get("login_attempts", 0))
                            st.error(f"❌ Credenciales incorrectas. Intentos restantes: {intentos_restantes}")
                        else:
                            st.error("❌ Usuario o contraseña incorrectos")
            
            if forgot:
                st.info("📧 Contacte al administrador para restablecer su contraseña")
        
        st.markdown("""
        <div style='text-align:center; margin-top:30px; color:#718096; font-size:0.85em;'>
            <p>🔒 Conexión segura con encriptación bcrypt</p>
            <p>Primera vez: use <code style='background:#374151; padding:3px 8px; border-radius:5px;'>admin</code> / <code style='background:#374151; padding:3px 8px; border-radius:5px;'>Admin2024!</code></p>
        </div>
        """, unsafe_allow_html=True)
    st.stop()

# Barra superior mejorada
st.markdown(f"""
<div style='background: linear-gradient(135deg, #2d3748, #1a202c); padding:15px 25px; border-radius:15px; margin-bottom:25px; box-shadow: 0 2px 10px rgba(0,0,0,0.3); display:flex; justify-content:space-between; align-items:center;'>
    <div>
        <span style='font-size:1.1em; color:white;'>👨‍⚕️ <strong>{st.session_state.doctor_name}</strong></span>
        <span style='color:#cbd5e0; margin-left:15px;'>@{st.session_state.username}</span>
        <span style='background:{PRIMARY}; color:white; padding:3px 10px; border-radius:20px; margin-left:15px; font-size:0.85em;'>{st.session_state.role.upper()}</span>
    </div>
</div>
""", unsafe_allow_html=True)

col_logout1, col_logout2 = st.columns([6, 1])
with col_logout2:
    if st.button("🚪 Cerrar Sesión"):
        db.log_audit(st.session_state.username, "Cerró sesión", "LOGOUT")
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

st.markdown("---")

# =============================================
# MENÚ PRINCIPAL
# =============================================
if st.session_state.role == "admin":
    tabs = st.tabs([
        "📋 Evaluación Individual",
        "📤 Carga Masiva",
        "📊 Historial",
        "👥 Gestión Usuarios",
        "📈 Estadísticas",
        "🔍 Auditoría"
    ])
    tab1, tab2, tab3, tab4, tab5, tab6 = tabs
else:
    tabs = st.tabs([
        "📋 Evaluación Individual",
        "📤 Carga Masiva",
        "📊 Historial"
    ])
    tab1, tab2, tab3 = tabs

# =============================================
# TAB 1: EVALUACIÓN INDIVIDUAL
# =============================================
with tab1:
    st.markdown("## 📋 Evaluación Individual de Paciente")
    
    col_form, col_result = st.columns([1.2, 1])
    
    with col_form:
        st.markdown("<div style='background:#2d3748; padding:25px; border-radius:15px;'>", unsafe_allow_html=True)
        st.markdown("### 📝 Datos del Paciente")
        with st.form("form_eval"):
            nombre = st.text_input("👤 Nombre completo", placeholder="Juan Pérez García")
            
            st.markdown("#### Datos Demográficos y Clínicos")
            c0_1, c0_2 = st.columns(2)
            with c0_1:
                sexo_input = st.selectbox("🚻 Sexo biológico", ["Hombre", "Mujer"]) 
            with c0_2:
                raza_input = st.selectbox("🌍 Raza (para CKD-EPI)", ["No-Afroamericano", "Afroamericano"]) 
            
            c1, c2 = st.columns(2)
            with c1:
                edad = st.number_input("📅 Edad (años)", 18, 120, 55)
                imc = st.number_input("⚖️ IMC (kg/m²)", 10.0, 60.0, 27.0, 0.1)
                glucosa = st.number_input("🩸 Glucosa en ayunas (mg/dL)", 50, 500, 110)
            with c2:
                presion = st.number_input("💓 Presión sistólica (mmHg)", 80, 250, 130)
                creat = st.number_input("🧪 Creatinina sérica (mg/dL)", 0.1, 15.0, 1.2, 0.01)
            
            submitted = st.form_submit_button("🔬 Analizar Riesgo", use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)
    
    with col_result:
        if submitted:
            if not nombre.strip():
                st.error("⚠️ El nombre del paciente es obligatorio")
            else:
                # Estandarización de entradas para TFG y Predicción
                datos = {
                    "edad": edad, "imc": imc, "presion_sistolica": presion,
                    "glucosa_ayunas": glucosa, "creatinina": creat,
                    "sexo": sexo_input, "raza": raza_input
                }
                
                riesgo, tfg, estadio = predecir(datos)
                nivel, color, reco_publica, _ = riesgo_level(riesgo)
                reco_privada = get_doctor_recommendation(riesgo)
                
                # Guardar
                record = {
                    "nombre_paciente": nombre,
                    "doctor_user": st.session_state.username,
                    "doctor_name": st.session_state.doctor_name,
                    "timestamp": datetime.now().isoformat(),
                    **datos, 
                    "riesgo": riesgo, "nivel": nivel, 
                    "tfg": tfg, "estadio_erc": estadio,
                    "reco_privada": reco_privada # Guardar recomendación privada
                }
                db.add_patient(record)
                db.log_audit(st.session_state.username, f"Evaluó: {nombre} - {riesgo}%", "EVALUATION")
                
                st.session_state.ultimo = record
        
        if "ultimo" in st.session_state:
            p = st.session_state.ultimo
            nivel, color, reco_publica, _ = riesgo_level(p["riesgo"])
            reco_privada = p.get("reco_privada", get_doctor_recommendation(p["riesgo"])) # Asegurar reco privada si es registro antiguo
            
            st.markdown("### 📊 Resultado")
            
            # Gauge (CORREGIDO)
            st.plotly_chart(crear_gauge_riesgo(p["riesgo"]), use_container_width=True)
            
            # Tarjeta resultado
            st.markdown(f"""
            <div class='risk-card risk-{"high" if p["riesgo"]>70 else "med" if p["riesgo"]>40 else "low"}'>
                <h2 style='color:{color}; margin:0; text-shadow: 0 2px 10px rgba(0,0,0,0.3);'>{nivel}</h2>
                <h1 style='font-size:3.5em; color:{color}; margin:10px 0; text-shadow: 0 2px 10px rgba(0,0,0,0.3);'>{p["riesgo"]:.1f}%</h1>
                <p style='color:#e2e8f0; font-size:1.1em; text-shadow: 0 1px 3px rgba(0,0,0,0.2);'>{reco_publica}</p>
            </div>
            """, unsafe_allow_html=True)
            
            # Recomendación Privada para el Doctor
            st.markdown("---")
            st.markdown("### 👨‍⚕️ Recomendación para la Toma de Decisión (Solo Doctor)")
            st.warning(f"**Cita Médica Sugerida:** {reco_privada}")
            st.markdown("_Recuerde que esta es una herramienta de ayuda; no sustituye el criterio médico._")
            
            # Resultados Clínicos y Botón PDF
            st.markdown("---")
            st.markdown("### 🔬 Parámetros Renales Clave")
            
            col_tfg1, col_tfg2 = st.columns(2)
            with col_tfg1:
                st.markdown(f"""
                <div class='metric-card' style='border-left: 5px solid {SECONDARY};'>
                    <p style='margin:0; font-size:0.9em; color:#a0aec0;'>Tasa de Filtración Glomerular (TFG)</p>
                    <h3 style='margin:5px 0 0 0; color:{SECONDARY};'>{p['tfg']} ml/min/1.73m²</h3>
                </div>
                """, unsafe_allow_html=True)
            
            with col_tfg2:
                st.markdown(f"""
                <div class='metric-card' style='border-left: 5px solid {SECONDARY};'>
                    <p style='margin:0; font-size:0.9em; color:#a0aec0;'>Estadio de ERC</p>
                    <h3 style='margin:5px 0 0 0; color:{SECONDARY};'>{p['estadio_erc']}</h3>
                </div>
                """, unsafe_allow_html=True)
            
            # Generación del PDF (Botón de Descarga)
            if st.button("⬇️ Descargar Reporte PDF", use_container_width=True):
                
                pdf = PDFReport()
                pdf.set_auto_page_break(auto=True, margin=15)
                pdf.add_page()
                pdf.set_font('Arial', '', 12)
                
                pdf.chapter_title("1. Datos de la Evaluación", PRIMARY)
                pdf.chapter_body(
                    f"Paciente: {p['nombre_paciente']}\n"
                    f"Fecha: {datetime.fromisoformat(p['timestamp']).strftime('%d/%m/%Y %H:%M')}\n"
                    f"Evaluado por: {p['doctor_name']} (@{p['doctor_user']})"
                )
                
                pdf.chapter_title("2. Parámetros de Entrada", PRIMARY)
                pdf.chapter_body(
                    f"Edad: {p['edad']} años\n"
                    f"Sexo: {p['sexo']}\n"
                    f"Raza: {p['raza']}\n"
                    f"IMC: {p['imc']} kg/m²\n"
                    f"Presión Sistólica: {p['presion_sistolica']} mmHg\n"
                    f"Glucosa en Ayunas: {p['glucosa_ayunas']} mg/dL\n"
                    f"Creatinina Sérica: {p['creatinina']} mg/dL"
                )
                
                pdf.chapter_title("3. Resultados de la Predicción", color)
                pdf.chapter_body(
                    f"RIESGO DE ERC (Predicción): {p['riesgo']:.1f}% ({nivel})\n"
                    f"TFG Estimada (CKD-EPI): {p['tfg']} ml/min/1.73m²\n"
                    f"ESTADIO ERC: {p['estadio_erc']}\n\n"
                    f"RECOMENDACIÓN PÚBLICA: {reco_publica}"
                )

                # Sección de firma
                pdf.set_y(pdf.get_y() + 20)
                pdf.set_font('Arial', 'I', 10)
                pdf.set_text_color(100, 100, 100)
                pdf.cell(0, 5, "___________________________________", 0, 1, 'L')
                pdf.cell(0, 5, f"Firma del Médico: {st.session_state.doctor_name} (@{st.session_state.username})", 0, 1, 'L')
                
                pdf_output = pdf.output(dest='S').encode('latin1')
                st.download_button(
                    label="¡Reporte generado! Haz clic para descargar.",
                    data=pdf_output,
                    file_name=f"Reporte_ERC_{p['nombre_paciente'].replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.pdf",
                    mime="application/pdf"
                )

# =============================================
# TAB 2: CARGA MASIVA (IMPLEMENTADO)
# =============================================
with tab2:
    st.markdown("## 📤 Carga Masiva de Datos")
    st.info("Suba un archivo Excel (.xlsx) o CSV con múltiples pacientes para una evaluación rápida.")

    uploaded_file = st.file_uploader("Subir Archivo de Datos", type=['csv', 'xlsx'])

    if uploaded_file is not None:
        try:
            if uploaded_file.name.endswith('.csv'):
                df = pd.read_csv(uploaded_file)
            else:
                df = pd.read_excel(uploaded_file)
            
            st.markdown("### Vista Previa de Datos Cargados")
            st.dataframe(df.head(), use_container_width=True)

            # Estandarización de columnas esperadas (ej. con sinónimos)
            col_map = {
                'nombre': 'nombre_paciente', 'name': 'nombre_paciente', 
                'edad': 'edad', 'age': 'edad',
                'sexo': 'sexo', 'gender': 'sexo',
                'raza': 'raza', 'race': 'raza',
                'imc': 'imc', 'bmi': 'imc', 
                'presion_sistolica': 'presion_sistolica', 'ps': 'presion_sistolica', 'sysbp': 'presion_sistolica',
                'glucosa_ayunas': 'glucosa_ayunas', 'glucosa': 'glucosa_ayunas', 'fasting_glucose': 'glucosa_ayunas',
                'creatinina': 'creatinina', 'cr': 'creatinina', 'creatinine': 'creatinina'
            }
            
            df_processed = df.rename(columns=col_map, errors='ignore')
            
            required_cols = ['nombre_paciente', 'edad', 'imc', 'presion_sistolica', 'glucosa_ayunas', 'creatinina']
            missing_cols = [col for col in required_cols if col not in df_processed.columns]
            
            if missing_cols:
                st.error(f"❌ Columnas obligatorias faltantes: {', '.join(missing_cols)}. Por favor, revise su archivo.")
            else:
                # 1. Limpieza y conversión de tipos
                for col in required_cols[1:]: # Ignorar nombre_paciente
                    df_processed[col] = pd.to_numeric(df_processed[col], errors='coerce')
                
                df_processed = df_processed.dropna(subset=required_cols[1:]).reset_index(drop=True)
                
                st.success(f"✅ {len(df_processed)} filas válidas encontradas y listas para procesar.")
                
                if st.button("🚀 Procesar Carga Masiva", use_container_width=True):
                    results = []
                    
                    with st.spinner("Realizando predicciones..."):
                        for index, row in df_processed.iterrows():
                            try:
                                datos_input = {
                                    "edad": row["edad"], "imc": row["imc"], "presion_sistolica": row["presion_sistolica"],
                                    "glucosa_ayunas": row["glucosa_ayunas"], "creatinina": row["creatinina"],
                                    "sexo": row.get("sexo", "Hombre"),
                                    "raza": row.get("raza", "No-Afroamericano")
                                }
                                
                                riesgo, tfg, estadio = predecir(datos_input)
                                nivel, _, _, clasificacion = riesgo_level(riesgo)
                                
                                record = {
                                    "nombre_paciente": row["nombre_paciente"],
                                    "doctor_user": st.session_state.username,
                                    "doctor_name": st.session_state.doctor_name,
                                    "timestamp": datetime.now().isoformat(),
                                    **datos_input, 
                                    "riesgo": riesgo, "nivel": nivel, 
                                    "tfg": tfg, "estadio_erc": estadio,
                                    "clasificacion": clasificacion # Para la tabla de resultados
                                }
                                
                                db.add_patient(record)
                                results.append(record)
                                
                            except Exception as e:
                                results.append({"nombre_paciente": row.get("nombre_paciente", "N/A"), "error": f"Error al predecir: {e}"})

                    st.success(f"🎉 Procesamiento completado. {len(results)} registros guardados.")
                    db.log_audit(st.session_state.username, f"Carga masiva de {len(results)} registros.", "MASS_UPLOAD")
                    
                    results_df = pd.DataFrame(results)
                    
                    # Mostrar resultados clasificados
                    st.markdown("### Clasificación de Riesgo de la Carga")
                    if 'clasificacion' in results_df.columns:
                        
                        df_clasificado = results_df[['nombre_paciente', 'edad', 'creatinina', 'tfg', 'estadio_erc', 'riesgo', 'clasificacion']]
                        
                        # Colores para la tabla
                        def color_clasificacion(val):
                            if val == 'Grave': return f'background-color: {DANGER}44'
                            if val == 'Intermedio': return f'background-color: {WARNING}44'
                            return f'background-color: {SUCCESS}44'

                        st.dataframe(
                            df_clasificado.style.applymap(color_clasificacion, subset=['clasificacion']),
                            use_container_width=True,
                            hide_index=True
                        )
                        
                        @st.cache_data
                        def convert_df(df):
                            return df.to_csv(index=False).encode('utf-8')
                        
                        csv = convert_df(df_clasificado)
                        st.download_button(
                            label="Descargar Reporte Masivo en CSV",
                            data=csv,
                            file_name=f'reporte_masivo_{datetime.now().strftime("%Y%m%d_%H%M")}.csv',
                            mime='text/csv',
                            use_container_width=True
                        )
                    else:
                        st.error("Ocurrió un error al generar la tabla de resultados.")

        except Exception as e:
            st.error(f"⚠️ Error al leer el archivo: {e}")

# =============================================
# TAB 3: HISTORIAL (IMPLEMENTADO)
# =============================================
with tab3:
    st.markdown("## 📊 Historial de Evaluaciones")
    st.info("Aquí puede revisar todas las evaluaciones registradas en el sistema. Seleccione un paciente para ver sus detalles.")
    
    # Lógica para mostrar los datos
    if st.session_state.role == "admin":
        data = db.get_all_patients()
        st.markdown("### Historial Completo del Sistema")
    else:
        data = db.get_patients_by_doctor(st.session_state.username)
        st.markdown(f"### Historial de Evaluaciones Realizadas por @{st.session_state.username}")

    if data:
        df = pd.DataFrame(data)
        
        # Formatear la columna de tiempo
        df['Fecha'] = pd.to_datetime(df['timestamp']).dt.strftime('%d/%m/%Y %H:%M')
        
        # Seleccionar y renombrar las columnas relevantes
        df_display = df[[
            'nombre_paciente', 'Fecha', 'edad', 'sexo', 'creatinina', 'tfg', 
            'estadio_erc', 'riesgo', 'nivel', 'doctor_name', 'timestamp'
        ]].rename(columns={
            'nombre_paciente': 'Paciente',
            'edad': 'Edad',
            'sexo': 'Sexo',
            'creatinina': 'Creatinina (mg/dL)',
            'tfg': 'TFG (CKD-EPI)',
            'estadio_erc': 'Estadio ERC',
            'riesgo': 'Riesgo (%)',
            'nivel': 'Nivel Riesgo',
            'doctor_name': 'Doctor'
        })
        
        # Mostrar la tabla de datos y permitir selección
        st.dataframe(df_display.drop(columns=['timestamp']), use_container_width=True, selection_mode='single')
        
        # Manejar la selección
        selected_rows = st.session_state.get('dataframe_historial_evaluaciones_selected_rows') # Se usa el nombre de Streamlit para el widget dataframe
        
        if selected_rows and selected_rows['selected_rows']:
            selected_index = selected_rows['selected_rows'][0]
            selected_record_timestamp = df_display.loc[selected_index, 'timestamp']
            
            # Buscar el registro completo en la lista original usando el timestamp único
            selected_record = next(
                (p for p in data if p['timestamp'] == selected_record_timestamp), 
                None
            )
            
            if selected_record:
                st.markdown("---")
                st.markdown(f"### Detalle de Evaluación: {selected_record['nombre_paciente']}")
                
                # Almacenar en session_state para poder generar PDF individual
                st.session_state.ultimo = selected_record
                st.rerun() # Disparar reruns para mostrar el detalle en tab 1 si se desea, o solo mostrar aquí
                
                # Mostrar detalle del resultado
                s_riesgo = selected_record['riesgo']
                s_nivel, s_color, s_reco_publica, _ = riesgo_level(s_riesgo)
                s_reco_privada = selected_record.get('reco_privada', get_doctor_recommendation(s_riesgo))
                
                col_det1, col_det2 = st.columns(2)
                with col_det1:
                    st.plotly_chart(crear_gauge_riesgo(s_riesgo), use_container_width=True)
                
                with col_det2:
                    st.markdown(f"""
                    <div class='risk-card risk-{"high" if s_riesgo>70 else "med" if s_riesgo>40 else "low"}'>
                        <h2 style='color:{s_color}; margin:0; text-shadow: 0 2px 10px rgba(0,0,0,0.3);'>{s_nivel}</h2>
                        <h1 style='font-size:3.5em; color:{s_color}; margin:10px 0; text-shadow: 0 2px 10px rgba(0,0,0,0.3);'>{s_riesgo:.1f}%</h1>
                        <p style='color:#e2e8f0; font-size:1.1em; text-shadow: 0 1px 3px rgba(0,0,0,0.2);'>{s_reco_publica}</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    st.markdown("---")
                    st.markdown("### Parámetros")
                    st.text(f"TFG: {selected_record['tfg']} | Estadio: {selected_record['estadio_erc']}")
                    st.text(f"Creatinina: {selected_record['creatinina']} | Edad: {selected_record['edad']}")
                    
                    st.markdown("---")
                    st.markdown("### Recomendación Privada")
                    st.warning(s_reco_privada)

        
        # Opción de descarga del historial completo
        @st.cache_data
        def convert_df(df):
            return df.to_csv(index=False).encode('utf-8')

        csv = convert_df(df_display.drop(columns=['timestamp']))

        st.download_button(
            label="Descargar Historial en CSV",
            data=csv,
            file_name=f'historial_nefropredict_{st.session_state.username}_{datetime.now().strftime("%Y%m%d")}.csv',
            mime='text/csv',
        )

    else:
        st.warning("No se encontraron evaluaciones registradas.")


# =============================================
# TAB 4: GESTIÓN DE USUARIOS (SOLO ADMIN - CORREGIDO)
# =============================================
if st.session_state.role == "admin":
    with tab4:
        st.markdown("## 👥 Gestión de Usuarios Médicos")
        
        tab_add, tab_list = st.tabs(["➕ Crear Nuevo Doctor", "📋 Lista y Acciones"])
        
        # --- TAB: CREAR NUEVO DOCTOR ---
        with tab_add:
            st.markdown("### 👨‍⚕️ Registro de Nuevo Usuario Doctor")
            with st.form("form_new_doctor"):
                new_name = st.text_input("Nombre Completo del Doctor", placeholder="Dr. Luis Rodríguez")
                new_username = st.text_input("Nombre de Usuario (ID)", placeholder="luis.rodriguez").lower().strip()
                
                c_pwd1, c_pwd2 = st.columns(2)
                with c_pwd1:
                    new_password = st.text_input("Contraseña", type="password")
                with c_pwd2:
                    confirm_password = st.text_input("Confirmar Contraseña", type="password")
                
                submitted_new = st.form_submit_button("Crear Doctor", use_container_width=True)
                
                if submitted_new:
                    if not new_name or not new_username or not new_password:
                        st.error("⚠️ Todos los campos son obligatorios.")
                    elif db.get_user(new_username):
                        st.error(f"❌ El usuario @{new_username} ya existe.")
                    elif new_password != confirm_password:
                        st.error("❌ Las contraseñas no coinciden.")
                    else:
                        is_strong, msg = check_password_strength(new_password)
                        if not is_strong:
                            st.warning(f"Contraseña débil: {msg}")
                        
                        db.create_doctor(new_username, new_password, new_name, st.session_state.username)
                        st.success(f"✅ Doctor **{new_name} (@{new_username})** creado exitosamente.")
                        st.experimental_rerun()

        # --- TAB: LISTA Y ACCIONES ---
        with tab_list:
            st.markdown("### 📋 Doctores Registrados")
            users = db.data["users"]
            
            doctor_data_list = []
            for username, data in users.items():
                if data["role"] == "doctor":
                    doctor_data_list.append({
                        'Usuario': username,
                        'Nombre': data.get('name', 'N/A'),
                        'Fecha Creación': data.get('created_at'),
                        'Último Ingreso': data.get('last_login', 'Nunca'),
                        'Creado por': data.get('created_by', 'Sistema'),
                        'Estado': 'Activo' if data.get('active', False) else 'Inactivo'
                    })

            if not doctor_data_list:
                st.info("No hay doctores registrados en el sistema.")
            else:
                df_users = pd.DataFrame(doctor_data_list)
                df_users['Fecha Creación'] = pd.to_datetime(df_users['Fecha Creación']).dt.strftime('%d/%m/%Y %H:%M')
                
                st.dataframe(df_users, use_container_width=True)
                
                st.markdown("---")
                st.markdown("### Acciones de Usuario")
                
                # Usar solo doctores para acciones, excluyendo al admin
                user_options = [k for k, v in users.items() if v.get("role") == "doctor"]
                
                col_u1, col_u2, col_u3 = st.columns(3)
                user_to_act = col_u1.selectbox("Seleccionar Usuario:", user_options, key="select_user_action")
                
                if user_to_act:
                    current_user = db.get_user(user_to_act)
                    current_status = current_user.get("active", True)
                    
                    # Toggle Activo/Inactivo
                    action_label = "Desactivar Cuenta" if current_status else "Activar Cuenta"
                    if col_u2.button(f"🔒 {action_label}", key=f"toggle_{user_to_act}", use_container_width=True):
                        db.toggle_active(user_to_act, st.session_state.username)
                        st.success(f"Estado de @{user_to_act} cambiado a {'Inactivo' if current_status else 'Activo'}.")
                        st.experimental_rerun()
                        
                    # Eliminar
                    if col_u3.button("🗑️ Eliminar Usuario", key=f"delete_{user_to_act}", use_container_width=True):
                        db.delete_doctor(user_to_act, st.session_state.username)
                        st.success(f"Usuario @{user_to_act} eliminado permanentemente.")
                        st.experimental_rerun()

# =============================================
# TAB 5: ESTADÍSTICAS (SOLO ADMIN - IMPLEMENTADO)
# =============================================
if st.session_state.role == "admin":
    with tab5:
        st.markdown("## 📈 Estadísticas Globales del Sistema")
        
        all_data = db.get_all_patients()
        
        if not all_data:
            st.info("No hay suficientes datos para generar estadísticas.")
        else:
            df_stats = pd.DataFrame(all_data)
            
            col_s1, col_s2 = st.columns(2)
            
            # --- GRÁFICO 1: Distribución por Estadio ERC ---
            with col_s1:
                st.markdown("### Distribución de Estadios ERC")
                df_erc = df_stats['estadio_erc'].value_counts().reset_index()
                df_erc.columns = ['Estadio', 'Total']
                
                fig_erc = px.pie(df_erc, values='Total', names='Estadio', title='Distribución por Estadios ERC (CKD-EPI)',
                                 color_discrete_sequence=[SUCCESS, PRIMARY, WARNING, DANGER, "#8A2BE2"])
                fig_erc.update_traces(textposition='inside', textinfo='percent+label')
                fig_erc.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color='white')
                st.plotly_chart(fig_erc, use_container_width=True)

            # --- GRÁFICO 2: Distribución de Nivel de Riesgo ---
            with col_s2:
                st.markdown("### Distribución de Nivel de Riesgo")
                df_riesgo = df_stats['nivel'].value_counts().reset_index()
                df_riesgo.columns = ['Nivel', 'Total']
                
                nivel_order = ["MODERADO", "ALTO", "MUY ALTO"]
                color_map = {"MODERADO": SUCCESS, "ALTO": WARNING, "MUY ALTO": DANGER}
                
                fig_riesgo = px.bar(df_riesgo.set_index('Nivel').loc[nivel_order].reset_index(), x='Nivel', y='Total', 
                                    color='Nivel', title='Casos por Nivel de Riesgo',
                                    color_discrete_map=color_map)
                fig_riesgo.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color='white', xaxis_title="", yaxis_title="Número de Evaluaciones")
                st.plotly_chart(fig_riesgo, use_container_width=True)

            # --- GRÁFICO 3: Tendencia de Evaluaciones ---
            st.markdown("### Tendencia de Evaluaciones por Mes")
            df_stats['mes_eval'] = pd.to_datetime(df_stats['timestamp']).dt.to_period('M')
            df_trend = df_stats.groupby('mes_eval').size().reset_index(name='Evaluaciones')
            df_trend['mes_eval'] = df_trend['mes_eval'].astype(str)
            
            fig_trend = px.line(df_trend, x='mes_eval', y='Evaluaciones', title='Crecimiento de Evaluaciones Registradas',
                                markers=True, line_shape='spline', color_discrete_sequence=[PRIMARY])
            fig_trend.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color='white', xaxis_title="Mes", yaxis_title="Evaluaciones")
            st.plotly_chart(fig_trend, use_container_width=True)

# =============================================
# TAB 6: AUDITORÍA (SOLO ADMIN - IMPLEMENTADO)
# =============================================
if st.session_state.role == "admin":
    with tab6:
        st.markdown("## 🔍 Registro de Auditoría del Sistema")
        
        all_logs = db.get_audit_log(limit=2000)
        
        if not all_logs:
            st.info("No hay registros de auditoría.")
        else:
            df_logs = pd.DataFrame(all_logs)
            
            col_f1, col_f2, col_f3 = st.columns(3)
            
            users_list = ["Todos"] + sorted(df_logs['user'].unique().tolist())
            types_list = ["Todos"] + sorted(df_logs['type'].unique().tolist())
            
            user_filter = col_f1.selectbox("Filtrar por Usuario:", users_list)
            type_filter = col_f2.selectbox("Filtrar por Tipo de Acción:", types_list)
            limit_display = col_f3.number_input("Máximo de Registros a Mostrar:", 10, 500, 100)
            
            
            logs_filtered = db.get_audit_log(limit=limit_display, user_filter=user_filter, type_filter=type_filter)

            if logs_filtered:
                df_filtered = pd.DataFrame(logs_filtered)
                df_filtered['timestamp'] = pd.to_datetime(df_filtered['timestamp']).dt.strftime('%d/%m/%Y %H:%M:%S')
                df_filtered = df_filtered.rename(columns={'timestamp': 'Fecha', 'user': 'Usuario', 'action': 'Acción', 'type': 'Tipo'})
                st.dataframe(df_filtered.drop(columns=['ip']), use_container_width=True)
            else:
                st.warning("No se encontraron registros con los filtros seleccionados.")

# =============================================
# CARACTERÍSTICAS SUGERIDAS (FIN DEL CÓDIGO)
# =============================================
st.markdown("---")
st.info("""
### 🚀 Próximas Características Sugeridas:

**🔒 Seguridad Avanzada:**
- ✅ Encriptación de contraseñas (bcrypt)
- ✅ Protección contra fuerza bruta (5 intentos)
- ✅ Registro de auditoría completo
- 🔜 Autenticación de 2 factores (2FA)
- 🔜 Sesiones con expiración automática
- 🔜 Recuperación de contraseña por email

**💰 Monetización:**
- Planes por suscripción (Básico/Pro/Enterprise)
- Límite de evaluaciones por mes
- Multi-clínica con facturación centralizada
- API para integración con otros sistemas

**📊 Funciones Médicas Avanzadas:**
- ✅ **Cálculo automático de TFG (Tasa de Filtración Glomerular)**
- ✅ **Clasificación por estadios ERC (G1-G5)**
- ✅ **Reportes PDF profesionales**
- ✅ **Recomendación Médica de Citas (Solo Doctor)**
- Alertas automáticas para pacientes críticos
- Comparación temporal del mismo paciente
- Recomendaciones de tratamiento

**🏥 Para Clínicas:**
- Sistema multi-clínica
- Dashboard ejecutivo
- Exportación masiva de reportes
- Integración con sistemas hospitalarios (HL7/FHIR)

""")
