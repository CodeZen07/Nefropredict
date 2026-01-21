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
    
    .food-card {{
        background: #2d3748;
        padding: 15px;
        border-radius: 10px;
        margin: 10px 0;
        border-left: 4px solid {SECONDARY};
    }}
    
    .nutrition-alert {{
        background: #1a202c;
        padding: 20px;
        border-radius: 15px;
        margin: 15px 0;
        border: 2px solid {WARNING};
    }}
</style>
""", unsafe_allow_html=True)

st.markdown(f"""
<div style='text-align:center; padding: 30px 0; background: linear-gradient(135deg, #2d3748, #1a202c); border-radius: 20px; margin-bottom: 30px; box-shadow: 0 4px 15px rgba(0,0,0,0.3);'>
    <h1 style='color: {PRIMARY}; font-size: 3em; margin: 0;'>🏥 NefroPredict RD</h1>
    <p style='color: #cbd5e0; font-size: 1.2em; margin-top: 10px;'>Sistema Inteligente de Detección Temprana de ERC</p>
    <p style='color: #718096; font-size: 0.9em;'>República Dominicana • Versión 3.0 - Con Nutrición y Bienestar</p>
</div>
""", unsafe_allow_html=True)

# =============================================
# BASE DE DATOS DE ALIMENTOS (Evidencia Científica)
# =============================================
ALIMENTOS_DB = {
    # Proteínas
    "Pollo (pechuga sin piel)": {"categoria": "Proteína", "proteina": 31, "sodio": 74, "potasio": 256, "fosforo": 220, "calorias": 165, "riesgo_erc": "BAJO"},
    "Pescado blanco (tilapia)": {"categoria": "Proteína", "proteina": 26, "sodio": 52, "potasio": 302, "fosforo": 204, "calorias": 128, "riesgo_erc": "BAJO"},
    "Huevo (1 unidad)": {"categoria": "Proteína", "proteina": 6, "sodio": 62, "potasio": 63, "fosforo": 86, "calorias": 72, "riesgo_erc": "BAJO"},
    "Carne roja (res)": {"categoria": "Proteína", "proteina": 26, "sodio": 72, "potasio": 370, "fosforo": 210, "calorias": 250, "riesgo_erc": "MEDIO"},
    "Embutidos (salchichas)": {"categoria": "Proteína", "proteina": 12, "sodio": 620, "potasio": 180, "fosforo": 110, "calorias": 290, "riesgo_erc": "ALTO"},
    
    # Lácteos
    "Leche descremada (1 taza)": {"categoria": "Lácteo", "proteina": 8, "sodio": 130, "potasio": 419, "fosforo": 247, "calorias": 83, "riesgo_erc": "MEDIO"},
    "Yogur natural": {"categoria": "Lácteo", "proteina": 5, "sodio": 70, "potasio": 234, "fosforo": 152, "calorias": 59, "riesgo_erc": "MEDIO"},
    "Queso cheddar": {"categoria": "Lácteo", "proteina": 25, "sodio": 621, "potasio": 98, "fosforo": 512, "calorias": 403, "riesgo_erc": "ALTO"},
    
    # Vegetales
    "Brócoli": {"categoria": "Vegetal", "proteina": 2.8, "sodio": 33, "potasio": 316, "fosforo": 66, "calorias": 34, "riesgo_erc": "BAJO"},
    "Zanahoria": {"categoria": "Vegetal", "proteina": 0.9, "sodio": 69, "potasio": 320, "fosforo": 35, "calorias": 41, "riesgo_erc": "BAJO"},
    "Espinaca": {"categoria": "Vegetal", "proteina": 2.9, "sodio": 79, "potasio": 558, "fosforo": 49, "calorias": 23, "riesgo_erc": "MEDIO"},
    "Papa": {"categoria": "Vegetal", "proteina": 2, "sodio": 6, "potasio": 425, "fosforo": 57, "calorias": 77, "riesgo_erc": "MEDIO"},
    "Tomate": {"categoria": "Vegetal", "proteina": 0.9, "sodio": 5, "potasio": 237, "fosforo": 24, "calorias": 18, "riesgo_erc": "BAJO"},
    
    # Frutas
    "Manzana": {"categoria": "Fruta", "proteina": 0.3, "sodio": 1, "potasio": 107, "fosforo": 11, "calorias": 52, "riesgo_erc": "BAJO"},
    "Plátano": {"categoria": "Fruta", "proteina": 1.1, "sodio": 1, "potasio": 358, "fosforo": 22, "calorias": 89, "riesgo_erc": "MEDIO"},
    "Naranja": {"categoria": "Fruta", "proteina": 0.9, "sodio": 0, "potasio": 181, "fosforo": 14, "calorias": 47, "riesgo_erc": "BAJO"},
    "Uvas": {"categoria": "Fruta", "proteina": 0.7, "sodio": 2, "potasio": 191, "fosforo": 20, "calorias": 69, "riesgo_erc": "BAJO"},
    
    # Granos y Cereales
    "Arroz blanco (cocido)": {"categoria": "Grano", "proteina": 2.7, "sodio": 1, "potasio": 35, "fosforo": 43, "calorias": 130, "riesgo_erc": "BAJO"},
    "Pan integral": {"categoria": "Grano", "proteina": 4, "sodio": 230, "potasio": 120, "fosforo": 90, "calorias": 80, "riesgo_erc": "MEDIO"},
    "Avena": {"categoria": "Grano", "proteina": 5, "sodio": 2, "potasio": 140, "fosforo": 180, "calorias": 150, "riesgo_erc": "MEDIO"},
    
    # Procesados (Alto Riesgo)
    "Pizza congelada": {"categoria": "Procesado", "proteina": 12, "sodio": 710, "potasio": 180, "fosforo": 220, "calorias": 266, "riesgo_erc": "ALTO"},
    "Sopa enlatada": {"categoria": "Procesado", "proteina": 3, "sodio": 890, "potasio": 120, "fosforo": 60, "calorias": 74, "riesgo_erc": "ALTO"},
    "Refresco/Soda cola": {"categoria": "Bebida", "proteina": 0, "sodio": 15, "potasio": 2, "fosforo": 41, "calorias": 140, "riesgo_erc": "ALTO"},
}

# =============================================
# FUNCIONES DE NUTRICIÓN BASADAS EN EVIDENCIA
# =============================================

def generar_plan_nutricional(tfg, estadio, imc, glucosa, presion):
    """
    Genera recomendaciones nutricionales basadas en guías KDOQI/KDIGO.
    Referencia: National Kidney Foundation Clinical Practice Guidelines
    """
    recomendaciones = {
        "proteinas_g_kg": 0.8,
        "sodio_mg": 2300,
        "potasio_mg": 4700,
        "fosforo_mg": 1400,
        "calorias_dia": 2000,
        "liquidos_ml": 2000,
        "restricciones": [],
        "alimentos_permitidos": [],
        "alimentos_evitar": []
    }
    
    # Ajustes según estadio ERC
    if "G1" in estadio or "G2" in estadio:
        recomendaciones["proteinas_g_kg"] = 0.8
        recomendaciones["sodio_mg"] = 2300
        recomendaciones["restricciones"].append("Sin restricciones severas. Enfoque en prevención.")
        recomendaciones["alimentos_permitidos"] = ["Frutas frescas", "Vegetales variados", "Proteínas magras", "Granos integrales"]
        
    elif "G3a" in estadio:
        recomendaciones["proteinas_g_kg"] = 0.8
        recomendaciones["sodio_mg"] = 2000
        recomendaciones["potasio_mg"] = 3000
        recomendaciones["restricciones"].append("Moderar sodio y fósforo. Control de potasio.")
        recomendaciones["alimentos_permitidos"] = ["Manzanas", "Arroz blanco", "Pollo", "Pescado blanco", "Zanahorias"]
        recomendaciones["alimentos_evitar"] = ["Plátanos", "Papas", "Tomates", "Lácteos en exceso"]
        
    elif "G3b" in estadio or "G4" in estadio:
        recomendaciones["proteinas_g_kg"] = 0.6
        recomendaciones["sodio_mg"] = 1500
        recomendaciones["potasio_mg"] = 2000
        recomendaciones["fosforo_mg"] = 900
        recomendaciones["restricciones"].append("RESTRICCIÓN MODERADA de proteínas, sodio, potasio y fósforo.")
        recomendaciones["alimentos_permitidos"] = ["Arroz blanco", "Manzanas", "Uvas", "Pollo (porciones pequeñas)", "Pepino"]
        recomendaciones["alimentos_evitar"] = ["Lácteos", "Carnes rojas", "Procesados", "Plátanos", "Espinacas", "Refrescos"]
        
    elif "G5" in estadio:
        recomendaciones["proteinas_g_kg"] = 0.6
        recomendaciones["sodio_mg"] = 1000
        recomendaciones["potasio_mg"] = 1500
        recomendaciones["fosforo_mg"] = 800
        recomendaciones["liquidos_ml"] = 1000
        recomendaciones["restricciones"].append("RESTRICCIÓN SEVERA. Consulta con nutricionista renal OBLIGATORIA.")
        recomendaciones["alimentos_permitidos"] = ["Arroz blanco", "Manzanas sin cáscara", "Claras de huevo"]
        recomendaciones["alimentos_evitar"] = ["Todos los lácteos", "Carnes rojas", "Procesados", "Frutas altas en potasio", "Frijoles", "Nueces"]
    
    # Ajustes por IMC
    peso_estimado = 70  # Asumir peso promedio
    if imc < 18.5:
        recomendaciones["calorias_dia"] = 2500
        recomendaciones["restricciones"].append("⚠️ Bajo peso: Aumentar calorías sin exceder proteínas.")
    elif imc >= 25 and imc < 30:
        recomendaciones["calorias_dia"] = 1800
        recomendaciones["restricciones"].append("Sobrepeso: Reducir calorías para pérdida gradual de peso.")
    elif imc >= 30:
        recomendaciones["calorias_dia"] = 1500
        recomendaciones["restricciones"].append("Obesidad: Reducción calórica supervisada + ejercicio.")
    
    # Ajustes por glucosa (Diabetes)
    if glucosa >= 126:
        recomendaciones["restricciones"].append("🩸 DIABETES: Control estricto de carbohidratos. Evitar azúcares simples.")
        recomendaciones["alimentos_evitar"].extend(["Refrescos", "Jugos azucarados", "Postres", "Pan blanco"])
    
    # Ajustes por presión (Hipertensión)
    if presion >= 140:
        recomendaciones["sodio_mg"] = min(recomendaciones["sodio_mg"], 1500)
        recomendaciones["restricciones"].append("💓 HIPERTENSIÓN: Dieta DASH. Sodio <1500mg/día.")
        recomendaciones["alimentos_evitar"].extend(["Embutidos", "Enlatados", "Comidas rápidas", "Quesos curados"])
    
    return recomendaciones

def calcular_calorias_diarias(edad, sexo, imc, nivel_actividad="sedentario"):
    """
    Calcula requerimiento calórico usando ecuación de Harris-Benedict revisada.
    """
    peso_estimado = 70 if sexo == "Hombre" else 60
    altura_estimada = 170 if sexo == "Hombre" else 160
    
    # TMB (Tasa Metabólica Basal)
    if sexo == "Hombre":
        tmb = 88.362 + (13.397 * peso_estimado) + (4.799 * altura_estimada) - (5.677 * edad)
    else:
        tmb = 447.593 + (9.247 * peso_estimado) + (3.098 * altura_estimada) - (4.330 * edad)
    
    # Factor de actividad
    factores = {
        "sedentario": 1.2,
        "ligero": 1.375,
        "moderado": 1.55,
        "activo": 1.725
    }
    
    calorias = tmb * factores.get(nivel_actividad, 1.2)
    
    # Ajuste por IMC
    if imc >= 30:
        calorias *= 0.85  # Déficit para pérdida de peso
    elif imc < 18.5:
        calorias *= 1.15  # Exceso para ganancia de peso
    
    return round(calorias)

def generar_plan_sueno(edad, nivel_estres="medio"):
    """
    Recomendaciones de sueño basadas en National Sleep Foundation.
    """
    if edad < 25:
        horas_sueño = "7-9 horas"
    elif edad < 65:
        horas_sueño = "7-9 horas"
    else:
        horas_sueño = "7-8 horas"
    
    recomendaciones = {
        "horas_optimas": horas_sueño,
        "consejos": [
            "🌙 Mantener horario regular (dormir y despertar a la misma hora)",
            "📵 Evitar pantallas 1 hora antes de dormir",
            "☕ No consumir cafeína después de las 2 PM",
            "🏃 Ejercicio regular (pero no 3 horas antes de dormir)",
            "🧘 Técnicas de relajación: respiración profunda, meditación",
            "🌡️ Temperatura fresca en habitación (18-20°C)",
            "🔇 Ambiente oscuro y silencioso"
        ],
        "impacto_erc": "El sueño inadecuado se asocia con progresión de ERC y mal control de presión arterial. Priorizar higiene del sueño."
    }
    
    if nivel_estres == "alto":
        recomendaciones["consejos"].insert(0, "⚠️ ESTRÉS ALTO: Considerar consulta con psicólogo/psiquiatra.")
    
    return recomendaciones

def generar_plan_estres(riesgo_erc):
    """
    Manejo de estrés basado en evidencia para pacientes renales.
    """
    estrategias = {
        "tecnicas_inmediatas": [
            "🧘‍♀️ Respiración 4-7-8: Inhalar 4 seg, retener 7 seg, exhalar 8 seg",
            "🚶 Caminata corta de 10 minutos al aire libre",
            "🎵 Música relajante o sonidos de naturaleza",
            "📝 Journaling: escribir pensamientos y emociones"
        ],
        "habitos_largo_plazo": [
            "🧘 Meditación mindfulness 10-15 min diarios",
            "🏃 Ejercicio aeróbico moderado 30 min, 5 días/semana",
            "👥 Conexión social: grupos de apoyo, familia, amigos",
            "🎨 Hobbies creativos: pintura, música, jardinería",
            "💆 Técnicas de relajación muscular progresiva",
            "📚 Terapia cognitivo-conductual si es necesario"
        ],
        "evitar": [
            "🚬 Tabaco",
            "🍺 Alcohol en exceso",
            "☕ Cafeína excesiva",
            "📱 Redes sociales tóxicas"
        ]
    }
    
    if riesgo_erc > 70:
        estrategias["recomendacion_especial"] = "⚠️ Riesgo alto de ERC: El estrés crónico puede acelerar deterioro renal. Considerar apoyo psicológico profesional."
    
    return estrategias

def analizar_alimento(alimento):
    """Analiza un alimento y proporciona recomendaciones para ERC."""
    if alimento not in ALIMENTOS_DB:
        return None
    
    data = ALIMENTOS_DB[alimento]
    analisis = {
        "nombre": alimento,
        "valores": data,
        "semaforo": {},
        "recomendacion": ""
    }
    
    # Sistema de semáforo
    if data["sodio"] < 140:
        analisis["semaforo"]["sodio"] = ("🟢", "BAJO")
    elif data["sodio"] < 400:
        analisis["semaforo"]["sodio"] = ("🟡", "MODERADO")
    else:
        analisis["semaforo"]["sodio"] = ("🔴", "ALTO")
    
    if data["potasio"] < 200:
        analisis["semaforo"]["potasio"] = ("🟢", "BAJO")
    elif data["potasio"] < 400:
        analisis["semaforo"]["potasio"] = ("🟡", "MODERADO")
    else:
        analisis["semaforo"]["potasio"] = ("🔴", "ALTO")
    
    if data["fosforo"] < 100:
        analisis["semaforo"]["fosforo"] = ("🟢", "BAJO")
    elif data["fosforo"] < 250:
        analisis["semaforo"]["fosforo"] = ("🟡", "MODERADO")
    else:
        analisis["semaforo"]["fosforo"] = ("🔴", "ALTO")
    
    # Recomendación general
    if data["riesgo_erc"] == "BAJO":
        analisis["recomendacion"] = "✅ SEGURO para la mayoría de pacientes con ERC. Consumo regular permitido."
    elif data["riesgo_erc"] == "MEDIO":
        analisis["recomendacion"] = "⚠️ MODERADO. Consumir con precaución en estadios G3b-G5. Controlar porciones."
    else:
        analisis["recomendacion"] = "🚫 ALTO RIESGO. Evitar en ERC avanzada (G3b+). Alto en sodio/fósforo/potasio."
    
    return analisis

# =============================================
# SEGURIDAD Y DB (Código original mantenido)
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
            json.dump(initial, f, indent=4, ensure_ascii*
