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
PRIMARY = "#0066CC"
SECONDARY = "#00A896"
DANGER = "#E63946"
WARNING = "#F77F00"
SUCCESS = "#06D6A0"
BG_LIGHT = "#F8F9FA"
TEXT_DARK = "#212529"

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
    
    .main {{
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
    }}
    
    h1, h2, h3, h4, h5 {{
        color: #ffffff !important;
        font-weight: 600 !important;
    }}
    
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
    
    .action-plan-card {{
        background: #2d3748;
        padding: 20px;
        border-radius: 15px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.3);
        margin: 10px 0;
        border-left: 5px solid {SECONDARY};
    }}
    
    .alert-critical {{
        background: linear-gradient(135deg, {DANGER}33, {DANGER}22);
        border: 3px solid {DANGER};
        padding: 25px;
        border-radius: 15px;
        animation: pulse 2s infinite;
        box-shadow: 0 0 30px {DANGER}44;
    }}
    
    @keyframes pulse {{
        0%, 100% {{ transform: scale(1); }}
        50% {{ transform: scale(1.02); }}
    }}
    
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
    
    .stTextInput label, .stNumberInput label, .stSelectbox label {{
        color: #e2e8f0 !important;
    }}
    
    .stSuccess, .stError, .stWarning, .stInfo {{
        border-radius: 10px;
        border-left: 5px solid;
        background: #2d3748;
        color: white;
    }}
    
    .footer {{
        text-align: center;
        padding: 20px;
        color: #cbd5e0;
        font-size: 0.9em;
        background: #2d3748;
        border-radius: 15px;
        margin-top: 30px;
    }}
    
    .login-container {{
        background: #2d3748;
        padding: 40px;
        border-radius: 20px;
        box-shadow: 0 10px 40px rgba(0,0,0,0.5);
    }}
    
    .stMarkdown, .stDataFrame {{
        color: #e2e8f0;
    }}
    
    [data-testid="stSidebar"] {{
        background: #1a202c;
    }}
    
    .nutrient-calculator {{
        background: #374151;
        padding: 20px;
        border-radius: 12px;
        margin: 10px 0;
    }}
</style>
""", unsafe_allow_html=True)

st.markdown(f"""
<div style='text-align:center; padding: 30px 0; background: linear-gradient(135deg, #2d3748, #1a202c); border-radius: 20px; margin-bottom: 30px; box-shadow: 0 4px 15px rgba(0,0,0,0.3);'>
    <h1 style='color: {PRIMARY}; font-size: 3em; margin: 0;'>🏥 NefroPredict RD</h1>
    <p style='color: #cbd5e0; font-size: 1.2em; margin-top: 10px;'>Sistema Inteligente de Detección Temprana de ERC</p>
    <p style='color: #718096; font-size: 0.9em;'>República Dominicana • Versión 2.0 PRO</p>
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
            return password == hashed
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
        
        if user.get("login_attempts", 0) >= 5:
            last_attempt = user.get("last_attempt_time")
            if last_attempt:
                time_passed = (datetime.now() - datetime.fromisoformat(last_attempt)).seconds
                if time_passed < 300:
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
            self.log_audit(updated_by, f"Cambió/Restableció contraseña de @{username}", "PASSWORD_RESET")

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
            "ip": "N/A"
        }
        self.data["audit_log"].insert(0, log_entry)
        self.data["audit_log"] = self.data["audit_log"][:2000]
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
# MÓDULO DE PLAN DE ACCIÓN INTEGRAL (NUEVO)
# =============================================

def generar_plan_accion(estadio_erc, riesgo, imc, edad):
    """
    Genera un plan de acción integral basado en el estadio ERC y factores clínicos.
    
    Returns:
        dict: Plan completo con nutrición, ejercicio e hidratación
    """
    plan = {
        "nutricion": {},
        "ejercicio": {},
        "hidratacion": {},
        "alertas": []
    }
    
    # PLAN NUTRICIONAL ESPECÍFICO POR ESTADIO
    if "G1" in estadio_erc or "G2" in estadio_erc:
        plan["nutricion"] = {
            "proteinas": "0.8-1.0 g/kg/día (Normal)",
            "proteinas_detalle": "Puede consumir proteínas sin restricción severa. Prefiera carnes magras, pescado y legumbres.",
            "sodio": "< 2300 mg/día (2-3g de sal)",
            "sodio_detalle": "Evite alimentos procesados, embutidos y comidas rápidas.",
            "potasio": "Sin restricción estricta",
            "potasio_detalle": "Puede consumir frutas y verduras libremente. Monitoree si usa medicamentos (IECA/ARA-II).",
            "fosforo": "Sin restricción (800-1000 mg/día)",
            "liquidos": "Sin restricción, 2-3 litros/día según tolerancia"
        }
    elif "G3a" in estadio_erc:
        plan["nutricion"] = {
            "proteinas": "0.6-0.8 g/kg/día (Moderada restricción)",
            "proteinas_detalle": "Reduzca el consumo de carnes rojas. Prefiera pescado blanco, pollo sin piel y claras de huevo.",
            "sodio": "< 2000 mg/día (Máximo 2g de sal)",
            "sodio_detalle": "Cocine sin sal. Use especias naturales para dar sabor.",
            "potasio": "2000-3000 mg/día (Moderación)",
            "potasio_detalle": "Limite: plátanos, naranjas, tomates, papas. Remoje verduras antes de cocinar.",
            "fosforo": "800-1000 mg/día (Evite excesos)",
            "fosforo_detalle": "Reduzca lácteos, frutos secos y bebidas cola.",
            "liquidos": "1.5-2 litros/día (Consulte si hay edema)"
        }
        plan["alertas"].append("⚠️ Considere consulta con nutricionista renal")
    elif "G3b" in estadio_erc or "G4" in estadio_erc:
        plan["nutricion"] = {
            "proteinas": "0.6 g/kg/día (Restricción moderada-severa)",
            "proteinas_detalle": "CRÍTICO: Limite proteínas. Consulte nutricionista para dieta especializada. Prefiera proteínas de alto valor biológico en pequeñas cantidades.",
            "sodio": "< 1500 mg/día (Menos de 1.5g sal)",
            "sodio_detalle": "Evite todo alimento procesado. No agregue sal a las comidas.",
            "potasio": "1500-2000 mg/día (Restricción)",
            "potasio_detalle": "EVITE: plátanos, melón, naranjas, tomate, papa, espinacas crudas. Hierva verduras 2 veces.",
            "fosforo": "600-800 mg/día (Restricción estricta)",
            "fosforo_detalle": "Evite lácteos, frutos secos, legumbres, refrescos oscuros. Considere quelantes de fósforo si el médico lo indica.",
            "liquidos": "1-1.5 litros/día (Control estricto según diuresis)"
        }
        plan["alertas"].append("🚨 REFERENCIA NUTRICIONAL URGENTE - Dieta renal especializada obligatoria")
    else:  # G5
        plan["nutricion"] = {
            "proteinas": "0.6-0.8 g/kg/día (Ajustar según diálisis)",
            "proteinas_detalle": "Si está en diálisis, las necesidades aumentan a 1.2 g/kg/día. Siga indicaciones de su nefrólogo.",
            "sodio": "< 1000 mg/día (Menos de 1g sal) - SIN SAL",
            "sodio_detalle": "Restricción MÁXIMA. Cero sal agregada.",
            "potasio": "< 1500 mg/día (Restricción severa)",
            "potasio_detalle": "Lista de alimentos permitidos/prohibidos con nutricionista. Riesgo de arritmias.",
            "fosforo": "< 800 mg/día + Quelantes obligatorios",
            "fosforo_detalle": "Control estricto. Use quelantes de fósforo con cada comida según indicación médica.",
            "liquidos": "500-1000 ml/día (Restringir severamente - según diuresis residual)"
        }
        plan["alertas"].append("🚨🚨 ESTADIO TERMINAL - Manejo con equipo multidisciplinario especializado")
    
    # PLAN DE EJERCICIO
    if imc > 30:
        intensidad_base = "Baja a Moderada"
    elif imc > 25:
        intensidad_base = "Moderada"
    else:
        intensidad_base = "Moderada a Vigorosa"
    
    if edad > 70:
        intensidad_base = "Baja (adaptada a adulto mayor)"
    
    if "G1" in estadio_erc or "G2" in estadio_erc:
        plan["ejercicio"] = {
            "tipo": "Aeróbico + Fuerza",
            "intensidad": intensidad_base,
            "frecuencia": "5 días/semana mínimo",
            "duracion": "150 minutos semanales (30 min/día)",
            "recomendaciones": "Caminata rápida, natación, ciclismo, ejercicios de resistencia con bandas. Mantener actividad física regular.",
            "precauciones": "Monitoree presión arterial antes y después del ejercicio si es hipertenso."
        }
    elif "G3a" in estadio_erc or "G3b" in estadio_erc:
        plan["ejercicio"] = {
            "tipo": "Aeróbico ligero + Flexibilidad",
            "intensidad": "Moderada (adaptada)",
            "frecuencia": "3-5 días/semana",
            "duracion": "20-30 minutos por sesión",
            "recomendaciones": "Caminata a paso moderado, bicicleta estática, yoga suave, estiramientos. Evite ejercicios de alto impacto.",
            "precauciones": "Evite deshidratación. Suspenda si hay mareos, dolor torácico o fatiga extrema. Consulte antes de iniciar programa nuevo."
        }
        plan["alertas"].append("⚠️ Consulte con su médico antes de iniciar ejercicio intenso")
    else:  # G4-G5
        plan["ejercicio"] = {
            "tipo": "Actividad ligera supervisada",
            "intensidad": "Baja",
            "frecuencia": "Según tolerancia (idealmente diario)",
            "duracion": "10-15 minutos, varias veces al día",
            "recomendaciones": "Caminatas cortas en casa, estiramientos suaves, ejercicios de respiración. Si está en diálisis, siga programa de ejercicio intradialítico si está disponible.",
            "precauciones": "NO realizar ejercicio intenso. Evite levantamiento de peso. Monitoreo médico continuo necesario."
        }
        plan["alertas"].append("🚨 Ejercicio solo bajo supervisión médica")
    
    # CRONOGRAMA DE HIDRATACIÓN
    if "G1" in estadio_erc or "G2" in estadio_erc:
        plan["hidratacion"] = {
            "cantidad_diaria": "2000-3000 ml (8-12 vasos)",
            "distribucion": "Distribuir durante el día, 250 ml cada 2 horas aprox.",
            "tipos_liquidos": "Agua pura principalmente. Puede incluir infusiones sin azúcar, agua de coco (moderación).",
            "evitar": "Bebidas azucaradas, refrescos, alcohol en exceso.",
            "señales_alerta": "Orina oscura = aumentar ingesta. Hinchazón = reducir y consultar."
        }
    elif "G3a" in estadio_erc or "G3b" in estadio_erc:
        plan["hidratacion"] = {
            "cantidad_diaria": "1500-2000 ml (6-8 vasos) - Ajustar según diuresis",
            "distribucion": "Pequeños sorbos frecuentes. 200 ml cada 2-3 horas.",
            "tipos_liquidos": "Agua pura preferentemente. Limite jugos (alto potasio).",
            "evitar": "Refrescos, bebidas energéticas, alcohol. Caldos muy salados.",
            "señales_alerta": "Hinchazón de pies/manos = REDUCIR líquidos y avisar al médico inmediatamente."
        }
        plan["alertas"].append("📊 Lleve registro diario de líquidos ingeridos y orina eliminada")
    else:  # G4-G5
        plan["hidratacion"] = {
            "cantidad_diaria": "500-1000 ml (2-4 vasos) - CONTROL ESTRICTO",
            "distribucion": "Solo para medicamentos y sed intensa. Medir con precisión.",
            "tipos_liquidos": "Agua pura únicamente. Todo líquido cuenta (sopas, frutas, helados).",
            "evitar": "TODOS los líquidos no esenciales. Alcohol PROHIBIDO.",
            "señales_alerta": "Peso diario en ayunas. Aumento de >1 kg en 24h = retención de líquidos, contacte a su nefrólogo."
        }
        plan["alertas"].append("🚨🚨 Use vaso medidor. Pese todo líquido. Control vital para evitar edema pulmonar.")
    
    return plan

def mostrar_plan_accion(plan, estadio, riesgo):
    """Muestra el plan de acción en la interfaz con diseño profesional"""
    
    st.markdown("---")
    st.markdown("## 📋 Plan de Acción Integral Personalizado")
    
    # Alertas críticas al inicio
    if plan["alertas"]:
        for alerta in plan["alertas"]:
            if "🚨🚨" in alerta:
                st.markdown(f"<div class='alert-critical'><h3>🚨 ALERTA CRÍTICA</h3><p>{alerta}</p></div>", unsafe_allow_html=True)
            elif "🚨" in alerta or "⚠️" in alerta:
                st.error(alerta)
            else:
                st.warning(alerta)
    
    # Tabs para cada componente del plan
    tab_nut, tab_ej, tab_hid = st.tabs(["🥗 Nutrición", "🏃 Ejercicio", "💧 Hidratación"])
    
    with tab_nut:
        st.markdown("### 🥗 Plan Nutricional Renal")
        
        col_n1, col_n2 = st.columns(2)
        
        with col_n1:
            st.markdown(f"""
            <div class='action-plan-card'>
                <h4>🥩 Proteínas</h4>
                <p style='color:{WARNING}; font-size:1.2em; font-weight:bold;'>{plan['nutricion']['proteinas']}</p>
                <p style='font-size:0.9em; color:#cbd5e0;'>{plan['nutricion']['proteinas_detalle']}</p>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown(f"""
            <div class='action-plan-card'>
                <h4>🧂 Sodio</h4>
                <p style='color:{DANGER}; font-size:1.2em; font-weight:bold;'>{plan['nutricion']['sodio']}</p>
                <p style='font-size:0.9em; color:#cbd5e0;'>{plan['nutricion']['sodio_detalle']}</p>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown(f"""
            <div class='action-plan-card'>
                <h4>🍌 Potasio</h4>
                <p style='color:{WARNING}; font-size:1.2em; font-weight:bold;'>{plan['nutricion']['potasio']}</p>
                <p style='font-size:0.9em; color:#cbd5e0;'>{plan['nutricion']['potasio_detalle']}</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col_n2:
            st.markdown(f"""
            <div class='action-plan-card'>
                <h4>🦴 Fósforo</h4>
                <p style='color:{WARNING}; font-size:1.2em; font-weight:bold;'>{plan['nutricion']['fosforo']}</p>
                <p style='font-size:0.9em; color:#cbd5e0;'>{plan['nutricion'].get('fosforo_detalle', 'Control de fósforo importante')}</p>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown(f"""
            <div class='action-plan-card'>
                <h4>💧 Líquidos</h4>
                <p style='color:{SECONDARY}; font-size:1.2em; font-weight:bold;'>{plan['nutricion']['liquidos']}</p>
            </div>
            """, unsafe_allow_html=True)
    
    with tab_ej:
        st.markdown("### 🏃 Rutina de Ejercicio Recomendada")
        
        col_e1, col_e2 = st.columns(2)
        
        with col_e1:
            st.markdown(f"""
            <div class='action-plan-card'>
                <h4>🎯 Tipo de Ejercicio</h4>
                <p style='color:{SUCCESS}; font-weight:bold;'>{plan['ejercicio']['tipo']}</p>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown(f"""
            <div class='action-plan-card'>
                <h4>⚡ Intensidad</h4>
                <p style='color:{WARNING}; font-weight:bold;'>{plan['ejercicio']['intensidad']}</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col_e2:
            st.markdown(f"""
            <div class='action-plan-card'>
                <h4>📅 Frecuencia</h4>
                <p style='color:{PRIMARY}; font-weight:bold;'>{plan['ejercicio']['frecuencia']}</p>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown(f"""
            <div class='action-plan-card'>
                <h4>⏱️ Duración</h4>
                <p style='color:{SECONDARY}; font-weight:bold;'>{plan['ejercicio']['duracion']}</p>
            </div>
            """, unsafe_allow_html=True)
        
        st.info(f"**Recomendaciones:** {plan['ejercicio']['recomendaciones']}")
        st.warning(f"**⚠️ Precauciones:** {plan['ejercicio']['precauciones']}")
    
    with tab_hid:
        st.markdown("### 💧 Cronograma de Hidratación")
        
        st.markdown(f"""
        <div class='action-plan-card' style='border-left: 5px solid {SECONDARY};'>
            <h4>💦 Cantidad Diaria Recomendada</h4>
            <h2 style='color:{SECONDARY}; margin:10px 0;'>{plan['hidratacion']['cantidad_diaria']}</h2>
        </div>
        """, unsafe_allow_html=True)
        
        col_h1, col_h2 = st.columns(2)
        
        with col_h1:
            st.markdown(f"""
            <div class='action-plan-card'>
                <h4>📊 Distribución</h4>
                <p>{plan['hidratacion']['distribucion']}</p>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown(f"""
            <div class='action-plan-card'>
                <h4>✅ Líquidos Permitidos</h4>
                <p>{plan['hidratacion']['tipos_liquidos']}</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col_h2:
            st.markdown(f"""
            <div class='action-plan-card'>
                <h4>❌ Evitar</h4>
                <p style='color:{DANGER};'>{plan['hidratacion']['evitar']}</p>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown(f"""
            <div class='action-plan-card'>
                <h4>🚨 Señales de Alerta</h4>
                <p style='color:{WARNING};'>{plan['hidratacion']['señales_alerta']}</p>
            </div>
            """, unsafe_allow_html=True)

# =============================================
# CALCULADORA DE NUTRIENTES (NUEVO)
# =============================================

ALIMENTOS_DB = {
    "Frutas": {
        "Manzana (1 mediana)": {"potasio": 195, "fosforo": 20, "sodio": 2, "proteinas": 0.5},
        "Plátano (1 mediano)": {"potasio": 422, "fosforo": 26, "sodio": 1, "proteinas": 1.3},
        "Naranja (1 mediana)": {"potasio": 237, "fosforo": 18, "sodio": 0, "proteinas": 1.2},
        "Uvas (1 taza)": {"potasio": 288, "fosforo": 30, "sodio": 3, "proteinas": 1.1},
        "Sandía (1 taza)": {"potasio": 170, "fosforo": 15, "sodio": 2, "proteinas": 0.9},
        "Melón (1 taza)": {"potasio": 427, "fosforo": 27, "sodio": 25, "proteinas": 1.3},
        "Piña (1 taza)": {"potasio": 180, "fosforo": 13, "sodio": 2, "proteinas": 0.9},
    },
    "Vegetales": {
        "Papa cocida (1 mediana)": {"potasio": 610, "fosforo": 78, "sodio": 10, "proteinas": 3.0},
        "Tomate (1 mediano)": {"potasio": 292, "fosforo": 30, "sodio": 6, "proteinas": 1.1},
        "Espinaca cocida (1 taza)": {"potasio": 839, "fosforo": 101, "sodio": 126, "proteinas": 5.3},
        "Zanahoria (1 taza)": {"potasio": 410, "fosforo": 44, "sodio": 88, "proteinas": 1.2},
        "Lechuga (1 taza)": {"potasio": 102, "fosforo": 20, "sodio": 10, "proteinas": 0.7},
        "Pepino (1 taza)": {"potasio": 152, "fosforo": 25, "sodio": 2, "proteinas": 0.7},
    },
    "Proteínas": {
        "Pollo (100g)": {"potasio": 220, "fosforo": 200, "sodio": 70, "proteinas": 27.0},
        "Pescado (100g)": {"potasio": 400, "fosforo": 250, "sodio": 50, "proteinas": 22.0},
        "Huevo (1 unidad)": {"potasio": 69, "fosforo": 99, "sodio": 71, "proteinas": 6.3},
        "Carne res (100g)": {"potasio": 370, "fosforo": 210, "sodio": 60, "proteinas": 26.0},
    },
    "Lácteos": {
        "Leche (1 taza)": {"potasio": 366, "fosforo": 247, "sodio": 107, "proteinas": 8.0},
        "Yogurt (1 taza)": {"potasio": 380, "fosforo": 250, "sodio": 120, "proteinas": 9.0},
        "Queso (30g)": {"potasio": 28, "fosforo": 145, "sodio": 180, "proteinas": 7.0},
    }
}

def calculadora_nutrientes(estadio_erc):
    """Calculadora rápida de nutrientes para alimentos comunes"""
    st.markdown("### 🔢 Calculadora Rápida de Nutrientes")
    st.info("Verifique si un alimento es seguro según el estadio del paciente")
    
    # Establecer límites según estadio
    if "G1" in estadio_erc or "G2" in estadio_erc:
        limites = {"potasio": 4000, "fosforo": 1000, "sodio": 2300}
        nivel_restriccion = "Sin restricciones severas"
    elif "G3a" in estadio_erc:
        limites = {"potasio": 3000, "fosforo": 1000, "sodio": 2000}
        nivel_restriccion = "Restricción Moderada"
    elif "G3b" in estadio_erc or "G4" in estadio_erc:
        limites = {"potasio": 2000, "fosforo": 800, "sodio": 1500}
        nivel_restriccion = "Restricción Estricta"
    else:  # G5
        limites = {"potasio": 1500, "fosforo": 800, "sodio": 1000}
        nivel_restriccion = "Restricción Máxima"
    
    st.markdown(f"**Nivel de Restricción:** `{nivel_restriccion}`")
    st.markdown(f"**Límites diarios:** Potasio ≤ {limites['potasio']}mg | Fósforo ≤ {limites['fosforo']}mg | Sodio ≤ {limites['sodio']}mg")
    
    categoria = st.selectbox("Seleccione categoría de alimento", list(ALIMENTOS_DB.keys()))
    alimento = st.selectbox("Seleccione el alimento", list(ALIMENTOS_DB[categoria].keys()))
    
    valores = ALIMENTOS_DB[categoria][alimento]
    
    col_calc1, col_calc2, col_calc3, col_calc4 = st.columns(4)
    
    # Determinar si es seguro
    potasio_ok = valores["potasio"] < limites["potasio"] * 0.15  # 15% del límite diario
    fosforo_ok = valores["fosforo"] < limites["fosforo"] * 0.15
    sodio_ok = valores["sodio"] < limites["sodio"] * 0.10
    
    with col_calc1:
        color_k = SUCCESS if potasio_ok else DANGER
        st.markdown(f"""
        <div class='nutrient-calculator' style='border-left: 4px solid {color_k};'>
            <p style='margin:0; font-size:0.8em;'>Potasio</p>
            <h3 style='color:{color_k}; margin:5px 0;'>{valores['potasio']} mg</h3>
            <p style='font-size:0.7em;'>{"✅ Seguro" if potasio_ok else "⚠️ Alto"}</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col_calc2:
        color_p = SUCCESS if fosforo_ok else DANGER
        st.markdown(f"""
        <div class='nutrient-calculator' style='border-left: 4px solid {color_p};'>
            <p style='margin:0; font-size:0.8em;'>Fósforo</p>
            <h3 style='color:{color_p}; margin:5px 0;'>{valores['fosforo']} mg</h3>
            <p style='font-size:0.7em;'>{"✅ Seguro" if fosforo_ok else "⚠️ Alto"}</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col_calc3:
        color_na = SUCCESS if sodio_ok else DANGER
        st.markdown(f"""
        <div class='nutrient-calculator' style='border-left: 4px solid {color_na};'>
            <p style='margin:0; font-size:0.8em;'>Sodio</p>
            <h3 style='color:{color_na}; margin:5px 0;'>{valores['sodio']} mg</h3>
            <p style='font-size:0.7em;'>{"✅ Seguro" if sodio_ok else "⚠️ Alto"}</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col_calc4:
        st.markdown(f"""
        <div class='nutrient-calculator' style='border-left: 4px solid {PRIMARY};'>
            <p style='margin:0; font-size:0.8em;'>Proteínas</p>
            <h3 style='color:{PRIMARY}; margin:5px 0;'>{valores['proteinas']} g</h3>
        </div>
        """, unsafe_allow_html=True)
    
    # Recomendación final
    if potasio_ok and fosforo_ok and sodio_ok:
        st.success(f"✅ **{alimento}** es SEGURO para consumo moderado en estadio {estadio_erc}")
    elif not potasio_ok or not fosforo_ok:
        st.error(f"🚫 **{alimento}** tiene niveles ALTOS de {'potasio' if not potasio_ok else 'fósforo'}. EVITAR o consumir en cantidades mínimas.")
    else:
        st.warning(f"⚠️ **{alimento}** puede consumirse con PRECAUCIÓN. Consulte con nutricionista.")

# =============================================
# MODELO DE PREDICCIÓN Y CLASIFICACIÓN
# =============================================
@st.cache_resource
def load_model():
    try:
        if os.path.exists("modelo_erc.joblib"):
            return joblib.load("modelo_erc.joblib")
        st.warning("⚠️ No se encontró el archivo 'modelo_erc.joblib'. Se utilizará la simulación predictiva.")
        return None
    except Exception as e:
        st.error(f"Error al cargar el modelo: {e}. Se utilizará la simulación.")
        return None

model = load_model()

# Validaciones de entrada
def validar_parametros(edad, creat, glucosa, presion, imc):
    """Valida que los parámetros clínicos estén en rangos biológicamente posibles"""
    errores = []
    
    if not (18 <= edad <= 120):
        errores.append("⚠️ Edad debe estar entre 18 y 120 años")
    if not (0.3 <= creat <= 15.0):
        errores.append("⚠️ Creatinina debe estar entre 0.3 y 15.0 mg/dL")
    if not (50 <= glucosa <= 500):
        errores.append("⚠️ Glucosa debe estar entre 50 y 500 mg/dL")
    if not (80 <= presion <= 250):
        errores.append("⚠️ Presión sistólica debe estar entre 80 y 250 mmHg")
    if not (10.0 <= imc <= 60.0):
        errores.append("⚠️ IMC debe estar entre 10.0 y 60.0 kg/m²")
    
    return errores

def predecir(row):
    sexo_tfg = "mujer" if row.get("sexo", "Hombre") == "Mujer" else "hombre"
    raza_tfg = row.get("raza", "No-Afroamericano").lower()
    raza_tfg_input = "afro" if "afro" in raza_tfg else "no_afro"
    
    tfg = calcular_tfg_ckdepi(row["creatinina"], row["edad"], sexo_tfg, raza_tfg_input)
    estadio = clasificar_erc(tfg)

    if model is not None:
        pass
        
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
    k = 0.7 if sexo == "mujer" else 0.9
    alpha = -0.329 if sexo == "mujer" else -0.411
    raza_factor = 1.159 if raza == "afro" else 1.0
    sexo_factor = 1.018 if sexo == "mujer" else 1.0
    
    min_k_cr = min(creatinina / k, 1)
    max_k_cr = max(creatinina / k, 1)
    
    TFG = 141 * (min_k_cr ** alpha) * (max_k_cr ** -1.209) * (0.993 ** edad) * sexo_factor * raza_factor
    
    return round(TFG)

def clasificar_erc(tfg):
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

# Clase mejorada para la Generación de PDF
class PDFReport(FPDF):
    def __init__(self):
        super().__init__()
        self.set_auto_page_break(auto=True, margin=15)
    
    def header(self):
        self.set_fill_color(0, 102, 204)
        self.rect(0, 0, 210, 25, 'F')
        self.set_text_color(255, 255, 255)
        self.set_font('Arial', 'B', 16)
        self.cell(0, 15, 'NefroPredict RD - Reporte de Evaluacion', 0, 1, 'C')
        self.set_draw_color(0, 102, 204)
        self.set_line_width(1.5)
        self.line(10, 24, 200, 24)
        self.ln(5)

    def chapter_title(self, title, r=0, g=102, b=204):
        self.set_text_color(r, g, b)
        self.set_font('Arial', 'B', 13)
        self.cell(0, 8, title, 0, 1, 'L')
        self.set_draw_color(r, g, b)
        self.set_line_width(0.5)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(3)

    def chapter_body(self, body):
        self.set_text_color(33, 37, 41)
        self.set_font('Arial', '', 11)
        # Manejar caracteres especiales
        body_encoded = body.encode('latin-1', 'replace').decode('latin-1')
        self.multi_cell(0, 6, body_encoded)
        self.ln(2)
        
    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f'Pagina {self.page_no()}/{{nb}} | Generado: {datetime.now().strftime("%d/%m/%Y %H:%M")}', 0, 0, 'C')

def crear_gauge_riesgo(riesgo):
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
# TAB 1: EVALUACIÓN INDIVIDUAL (MEJORADA)
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
                # Validar parámetros
                errores = validar_parametros(edad, creat, glucosa, presion, imc)
                if errores:
                    for error in errores:
                        st.error(error)
                else:
                    datos = {
                        "edad": edad, "imc": imc, "presion_sistolica": presion,
                        "glucosa_ayunas": glucosa, "creatinina": creat,
                        "sexo": sexo_input, "raza": raza_input
                    }
                    
                    riesgo, tfg, estadio = predecir(datos)
                    nivel, color, reco_publica, _ = riesgo_level(riesgo)
                    reco_privada = get_doctor_recommendation(riesgo)
                    
                    # Generar plan de acción
                    plan_accion = generar_plan_accion(estadio, riesgo, imc, edad)
                    
                    record = {
                        "nombre_paciente": nombre,
                        "doctor_user": st.session_state.username,
                        "doctor_name": st.session_state.doctor_name,
                        "timestamp": datetime.now().isoformat(),
                        **datos, 
                        "riesgo": riesgo, "nivel": nivel, 
                        "tfg": tfg, "estadio_erc": estadio,
                        "reco_privada": reco_privada,
                        "plan_accion": plan_accion
                    }
                    db.add_patient(record)
                    db.log_audit(st.session_state.username, f"Evaluó: {nombre} - {riesgo}%", "EVALUATION")
                    
                    st.session_state.ultimo = record
        
        if "ultimo" in st.session_state:
            p = st.session_state.ultimo
            nivel, color, reco_publica, _ = riesgo_level(p["riesgo"])
            reco_privada = p.get("reco_privada", get_doctor_recommendation(p["riesgo"]))
            plan_accion = p.get("plan_accion", generar_plan_accion(p["estadio_erc"], p["riesgo"], p["imc"], p["edad"]))
            
            st.markdown("### 📊 Resultado")
            
            # Alerta crítica mejorada para riesgo muy alto
            if p["riesgo"] > 70:
                st.markdown(f"""
                <div class='alert-critical'>
                    <h2 style='color:{DANGER}; margin:0;'>🚨 ALERTA CRÍTICA 🚨</h2>
                    <h3 style='color:white; margin:10px 0;'>RIESGO MUY ALTO DE ERC</h3>
                    <p style='color:white; font-size:1.1em;'>ACCIÓN INMEDIATA REQUERIDA</p>
                    <p style='color:#ffcccc;'>Referir a nefrología con URGENCIA</p>
                </div>
                """, unsafe_allow_html=True)
            
            st.plotly_chart(crear_gauge_riesgo(p["riesgo"]), use_container_width=True)
            
            st.markdown(f"""
            <div class='risk-card risk-{"high" if p["riesgo"]>70 else "med" if p["riesgo"]>40 else "low"}'>
                <h2 style='color:{color}; margin:0; text-shadow: 0 2px 10px rgba(0,0,0,0.3);'>{nivel}</h2>
                <h1 style='font-size:3.5em; color:{color}; margin:10px 0; text-shadow: 0 2px 10px rgba(0,0,0,0.3);'>{p["riesgo"]:.1f}%</h1>
                <p style='color:#e2e8f0; font-size:1.1em; text-shadow: 0 1px 3px rgba(0,0,0,0.2);'>{reco_publica}</p>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown("---")
            st.markdown("### 👨‍⚕️ Recomendación para la Toma de Decisión (Solo Doctor)")
            st.warning(f"**Cita Médica Sugerida:** {reco_privada}")
            st.markdown("_Recuerde que esta es una herramienta de ayuda; no sustituye el criterio médico._")
            
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
            
            # Mostrar Plan de Acción
            mostrar_plan_accion(plan_accion, p['estadio_erc'], p['riesgo'])
            
            # Calculadora de Nutrientes
            st.markdown("---")
            calculadora_nutrientes(p['estadio_erc'])
            
            # Generación del PDF COMPLETO con Plan de Acción
            st.markdown("---")
            pdf = PDFReport()
            pdf.alias_nb_pages()
            pdf.add_page()
            
            pdf.chapter_title("1. Datos de la Evaluacion", 0, 102, 204)
            pdf.chapter_body(
                f"Paciente: {p['nombre_paciente']}\n"
                f"Fecha: {datetime.fromisoformat(p['timestamp']).strftime('%d/%m/%Y %H:%M')}\n"
                f"Evaluado por: {p['doctor_name']} (@{p['doctor_user']})"
            )
            
            pdf.chapter_title("2. Parametros de Entrada", 0, 102, 204)
            pdf.chapter_body(
                f"Edad: {p['edad']} años\n"
                f"Sexo: {p['sexo']}\n"
                f"Raza: {p['raza']}\n"
                f"IMC: {p['imc']} kg/m2\n"
                f"Creatinina Serica: {p['creatinina']} mg/dL\n"
                f"Glucosa en Ayunas: {p['glucosa_ayunas']} mg/dL\n"
                f"Presion Sistolica: {p['presion_sistolica']} mmHg"
            )
            
            pdf.chapter_title("3. Resultados del Analisis", 0, 168, 150)
            pdf.set_font('Arial', 'B', 12)
            pdf.set_text_color(0, 0, 0)
            pdf.cell(0, 7, f"Riesgo de ERC: {p['riesgo']:.1f}% ({nivel})", 0, 1, 'L')
            pdf.cell(0, 7, f"TFG (CKD-EPI): {p['tfg']} ml/min/1.73m2", 0, 1, 'L')
            pdf.cell(0, 7, f"Estadio de ERC (KDIGO): {p['estadio_erc']}", 0, 1, 'L')
            pdf.ln(5)
            
            pdf.chapter_title("4. Recomendacion Medica (Confidencial)", 230, 57, 70)
            pdf.chapter_body(reco_privada)
            
            # NUEVO: Agregar Plan de Acción al PDF
            pdf.add_page()
            pdf.chapter_title("5. PLAN DE ACCION INTEGRAL", 0, 102, 204)
            
            pdf.chapter_title("5.1 Plan Nutricional", 0, 168, 150)
            pdf.chapter_body(
                f"Proteinas: {plan_accion['nutricion']['proteinas']}\n"
                f"{plan_accion['nutricion']['proteinas_detalle']}\n\n"
                f"Sodio: {plan_accion['nutricion']['sodio']}\n"
                f"{plan_accion['nutricion']['sodio_detalle']}\n\n"
                f"Potasio: {plan_accion['nutricion']['potasio']}\n"
                f"{plan_accion['nutricion']['potasio_detalle']}\n\n"
                f"Fosforo: {plan_accion['nutricion']['fosforo']}\n"
                f"{plan_accion['nutricion'].get('fosforo_detalle', '')}\n\n"
                f"Liquidos: {plan_accion['nutricion']['liquidos']}"
            )
            
            pdf.chapter_title("5.2 Plan de Ejercicio", 0, 168, 150)
            pdf.chapter_body(
                f"Tipo: {plan_accion['ejercicio']['tipo']}\n"
                f"Intensidad: {plan_accion['ejercicio']['intensidad']}\n"
                f"Frecuencia: {plan_accion['ejercicio']['frecuencia']}\n"
                f"Duracion: {plan_accion['ejercicio']['duracion']}\n\n"
                f"Recomendaciones: {plan_accion['ejercicio']['recomendaciones']}\n\n"
                f"Precauciones: {plan_accion['ejercicio']['precauciones']}"
            )
            
            pdf.chapter_title("5.3 Cronograma de Hidratacion", 0, 168, 150)
            pdf.chapter_body(
                f"Cantidad Diaria: {plan_accion['hidratacion']['cantidad_diaria']}\n"
                f"Distribucion: {plan_accion['hidratacion']['distribucion']}\n"
                f"Liquidos Permitidos: {plan_accion['hidratacion']['tipos_liquidos']}\n"
                f"Evitar: {plan_accion['hidratacion']['evitar']}\n"
                f"Senales de Alerta: {plan_accion['hidratacion']['señales_alerta']}"
            )
            
            if plan_accion["alertas"]:
                pdf.chapter_title("6. ALERTAS IMPORTANTES", 230, 57, 70)
                alertas_text = "\n\n".join(plan_accion["alertas"])
                pdf.chapter_body(alertas_text)
            
            pdf.chapter_title("7. Nota Legal", 247, 127, 0)
            pdf.chapter_body(
                "Este reporte es generado por NefroPredict RD y esta basado en un modelo predictivo. "
                "La interpretacion y decision clinica final debe ser siempre realizada por un medico especialista. "
                "Este documento contiene informacion medica confidencial del paciente."
            )
            
            pdf_output = pdf.output(dest='S').encode('latin-1')
            
            st.download_button(
                label="⬇️ Descargar Reporte Completo PDF",
                data=pdf_output,
                file_name=f"Reporte_NefroPredict_{p['nombre_paciente'].replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.pdf",
                mime="application/pdf",
                use_container_width=True
            )

# =============================================
# TAB 2: CARGA MASIVA
# =============================================
with tab2:
    st.markdown("## 📤 Carga Masiva de Pacientes (CSV)")
    st.info("Permite evaluar múltiples pacientes simultáneamente mediante la carga de un archivo CSV.")
    
    template_data = {
        "nombre_paciente": ["Ejemplo Juan", "Ejemplo María"],
        "edad": [65, 48],
        "sexo": ["Hombre", "Mujer"],
        "raza": ["No-Afroamericano", "Afroamericano"],
        "imc": [32.5, 24.1],
        "presion_sistolica": [150, 125],
        "creatinina": [1.4, 0.9],
        "glucosa_ayunas": [180, 105],
    }
    template_df = pd.DataFrame(template_data)
    csv_template = template_df.to_csv(index=False, encoding='utf-8')
    
    st.download_button(
        label="📥 Descargar Plantilla CSV",
        data=csv_template,
        file_name="plantilla_nefropredict.csv",
        mime="text/csv",
        help="Use esta plantilla para asegurar el formato correcto de las columnas.",
        type="secondary"
    )
    
    uploaded_file = st.file_uploader("📂 Seleccione el archivo CSV para cargar", type="csv")
    
    if uploaded_file is not None:
        try:
            df = pd.read_csv(uploaded_file)
            st.success(f"CSV cargado. Filas a procesar: {len(df)}")
            
            if st.button("▶️ Iniciar Procesamiento Masivo", key="process_mass"):
                with st.spinner("Procesando predicciones..."):
                    results = []
                    required_cols = list(template_data.keys())
                    
                    if not all(col in df.columns for col in required_cols):
                        st.error(f"❌ Error: El archivo CSV debe contener las columnas: {', '.join(required_cols)}")
                    else:
                        for index, row in df.iterrows():
                            sexo_input = row['sexo'].strip().title() if pd.notna(row['sexo']) else "Hombre"
                            raza_input = row['raza'].strip().title() if pd.notna(row['raza']) else "No-Afroamericano"
                            
                            datos = {
                                "edad": row['edad'], "imc": row['imc'], "presion_sistolica": row['presion_sistolica'],
                                "glucosa_ayunas": row['glucosa_ayunas'], "creatinina": row['creatinina'],
                                "sexo": "Mujer" if "Mujer" in sexo_input else "Hombre", 
                                "raza": "Afroamericano" if "Afro" in raza_input else "No-Afroamericano"
                            }
                            
                            riesgo, tfg, estadio = predecir(datos)
                            nivel, _, _, _ = riesgo_level(riesgo)
                            reco_privada = get_doctor_recommendation(riesgo)
                            plan_accion = generar_plan_accion(estadio, riesgo, datos["imc"], datos["edad"])
                            
                            record = {
                                "nombre_paciente": row['nombre_paciente'],
                                "doctor_user": st.session_state.username,
                                "doctor_name": st.session_state.doctor_name,
                                "timestamp": datetime.now().isoformat(),
                                **datos, 
                                "riesgo": riesgo, "nivel": nivel, 
                                "tfg": tfg, "estadio_erc": estadio,
                                "reco_privada": reco_privada,
                                "plan_accion": plan_accion
                            }
                            db.add_patient(record)
                            results.append(record)
                        
                        df_results = pd.DataFrame(results)
                        st.success(f"✅ Procesamiento masivo completado. {len(results)} registros guardados.")
                        db.log_audit(st.session_state.username, f"Carga masiva: {len(results)} pacientes procesados", "MASS_UPLOAD")

                        st.markdown("### Resultados del Lote")
                        st.dataframe(df_results[['nombre_paciente', 'riesgo', 'tfg', 'estadio_erc', 'nivel']], use_container_width=True)
                        
        except Exception as e:
            st.error(f"❌ Ocurrió un error al leer/procesar el archivo: {e}")

# =============================================
# TAB 3: HISTORIAL DE EVALUACIONES
# =============================================
with tab3:
    st.markdown("## 📊 Historial de Evaluaciones")
    
    if st.session_state.role == "admin":
        st.markdown("### 🌎 Historial Completo (Administrador)")
        patients = db.get_all_patients()
    else:
        st.markdown(f"### 🧑‍⚕️ Mis Evaluaciones Recientes")
        patients = db.get_patients_by_doctor(st.session_state.username)
        
    if not patients:
        st.info("Aún no se ha realizado ninguna evaluación.")
    else:
        df_historial = pd.DataFrame(patients)
        df_historial['Fecha'] = pd.to_datetime(df_historial['timestamp']).dt.strftime('%Y-%m-%d %H:%M')
        
        cols_to_display = ['Fecha', 'nombre_paciente', 'edad', 'creatinina', 'glucosa_ayunas', 'riesgo', 'nivel', 'estadio_erc']
        if st.session_state.role == "admin":
            cols_to_display.insert(2, 'doctor_name')
            
        st.dataframe(df_historial[cols_to_display].sort_values(by='Fecha', ascending=False), use_container_width=True)

# =============================================
# TAB 4: GESTIÓN DE USUARIOS (ADMIN SOLAMENTE)
# =============================================
if st.session_state.role == "admin":
    with tab4:
        st.markdown("## 👥 Gestión de Doctores")
        st.markdown("### ➕ Crear Nuevo Doctor")
        
        with st.form("form_create_user", clear_on_submit=True):
            col_a, col_b = st.columns(2)
            with col_a:
                new_username = st.text_input("Usuario (ID)", help="Ej: jramirez").lower().strip()
                new_name = st.text_input("Nombre Completo")
            with col_b:
                new_password = st.text_input("Contraseña Temporal", type="password")
            
            submitted = st.form_submit_button("Crear Usuario")
            
            if submitted:
                if not new_username or not new_password or not new_name:
                    st.error("❌ Todos los campos son obligatorios.")
                elif db.get_user(new_username):
                    st.error(f"❌ El usuario @{new_username} ya existe.")
                else:
                    is_strong, msg = check_password_strength(new_password)
                    if not is_strong:
                        st.warning(f"⚠️ Contraseña débil. Se recomienda: {msg}")
                    db.create_doctor(new_username, new_password, new_name, st.session_state.username)
                    st.success(f"✅ Doctor/a {new_name} (@{new_username}) creado exitosamente.")
        
        st.markdown("---")
        st.markdown("### 📋 Listado y Gestión")
        
        user_list = db.data['users']
        doctor_users = {u: data for u, data in user_list.items() if data.get('role') == 'doctor'}
        
        df_users = pd.DataFrame(doctor_users).T
        df_users = df_users[['name', 'role', 'active', 'created_at', 'last_login']]
        
        if not df_users.empty:
            for index, row in df_users.iterrows():
                col_name, col_status, col_actions = st.columns([2, 1, 3])
                
                status_color = SUCCESS if row['active'] else DANGER
                
                with col_name:
                    st.markdown(f"**{row['name']}** (@{index})")
                    st.caption(f"Creado: {pd.to_datetime(row['created_at']).strftime('%Y-%m-%d')}")
                
                with col_status:
                    st.markdown(f"<span style='background:{status_color}; color:white; padding:4px 10px; border-radius:10px; font-size:0.8em; font-weight:600;'>{'ACTIVO' if row['active'] else 'INACTIVO'}</span>", unsafe_allow_html=True)
                
                with col_actions:
                    col_t, col_r, col_d = st.columns(3)
                    with col_t:
                        if st.button(f"{'🚫 Desactivar' if row['active'] else '🟢 Activar'}", key=f"toggle_{index}", use_container_width=True):
                            db.toggle_active(index, st.session_state.username)
                            st.rerun()
                    with col_r:
                        if st.button("🔑 Resetear Contraseña", key=f"reset_{index}", use_container_width=True):
                            new_temp_pwd = secrets.token_urlsafe(8)
                            db.update_password(index, new_temp_pwd, st.session_state.username)
                            st.success(f"Contraseña de @{index} reseteada. Nueva temporal: **{new_temp_pwd}** (¡Informar al usuario!)")
                    with col_d:
                        if st.button("🗑️ Eliminar", key=f"delete_{index}", use_container_width=True):
                            db.delete_doctor(index, st.session_state.username)
                            st.rerun()
                            
                st.markdown("---")
        else:
            st.info("No hay otros usuarios doctores registrados.")

    # =============================================
    # TAB 5: ESTADÍSTICAS (ADMIN SOLAMENTE)
    # =============================================
    with tab5:
        st.markdown("## 📈 Estadísticas Globales del Sistema")
        all_patients = db.get_all_patients()
        
        if not all_patients:
            st.info("No hay datos de pacientes para generar estadísticas.")
        else:
            df_stats = pd.DataFrame(all_patients)
            total_patients = len(df_stats)
            
            c_metrics = st.columns(4)
            with c_metrics[0]:
                st.markdown(f"<div class='metric-card'>Total Pacientes: <h2 style='color:{PRIMARY};'>{total_patients}</h2></div>", unsafe_allow_html=True)
            with c_metrics[1]:
                avg_risk = df_stats['riesgo'].mean()
                st.markdown(f"<div class='metric-card'>Riesgo Promedio: <h2 style='color:{SECONDARY};'>{avg_risk:.1f}%</h2></div>", unsafe_allow_html=True)
            with c_metrics[2]:
                high_risk = len(df_stats[df_stats['riesgo'] > 70])
                st.markdown(f"<div class='metric-card'>Riesgo Muy Alto: <h2 style='color:{DANGER};'>{high_risk}</h2></div>", unsafe_allow_html=True)
            with c_metrics[3]:
                avg_tfg = df_stats['tfg'].mean()
                st.markdown(f"<div class='metric-card'>TFG Promedio: <h2 style='color:{WARNING};'>{avg_tfg:.1f}</h2></div>", unsafe_allow_html=True)

            st.markdown("---")
            
            col_g1, col_g2 = st.columns(2)
            
            with col_g1:
                st.markdown("### Distribución por Nivel de Riesgo")
                risk_counts = df_stats['nivel'].value_counts().reset_index()
                risk_counts.columns = ['Nivel', 'Conteo']
                fig_risk = px.pie(risk_counts, values='Conteo', names='Nivel', title='Distribución de Riesgo de ERC')
                fig_risk.update_layout(showlegend=True, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color='white')
                st.plotly_chart(fig_risk, use_container_width=True)

            with col_g2:
                st.markdown("### Conteo por Estadio de ERC")
                estadio_counts = df_stats['estadio_erc'].value_counts().reset_index()
                estadio_counts.columns = ['Estadio', 'Conteo']
                fig_estadio = px.bar(estadio_counts, x='Estadio', y='Conteo', title='Pacientes por Estadio KDIGO', color='Estadio',
                                     color_discrete_map={'G1 (Normal o Alto)': SUCCESS, 'G2 (Levemente Disminuido)': SUCCESS, 
                                                         'G3a (Disminución Leve a Moderada)': WARNING, 'G3b (Disminución Moderada a Severa)': WARNING,
                                                         'G4 (Disminución Severa)': DANGER, 'G5 (Fallo Renal)': DANGER})
                fig_estadio.update_layout(xaxis_title="Estadio KDIGO", yaxis_title="Número de Pacientes", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color='white')
                st.plotly_chart(fig_estadio, use_container_width=True)

    # =============================================
    # TAB 6: AUDITORÍA (ADMIN SOLAMENTE)
    # =============================================
    with tab6:
        st.markdown("## 🔍 Registro de Auditoría y Seguridad")
        st.info("Muestra las acciones clave del sistema: logins, creación de usuarios, evaluaciones, etc.")
        
        col_filters = st.columns(3)
        user_options = ["Todos"] + list(db.data['users'].keys()) + ["SYSTEM"]
        type_options = ["Todos", "LOGIN", "LOGIN_FAILED", "LOGOUT", "USER_CREATED", "PASSWORD_RESET", "EVALUATION", "MASS_UPLOAD", "SECURITY"]
        
        with col_filters[0]:
            user_filter = st.selectbox("Filtrar por Usuario", user_options)
        with col_
