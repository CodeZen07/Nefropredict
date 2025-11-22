import streamlit as st
import pandas as pd
import numpy as np
import time
import joblib 
import json
import os
import io
from datetime import datetime

# --- CONFIGURACIÓN DE LA PÁGINA Y ESTILOS MEJORADOS (MAYOR CONTRASTE Y SOMBRAS) ---
st.set_page_config(page_title="NefroPredict RD", page_icon="🫘", layout="wide")

st.markdown("""
<style>
    /* Tipografía y claridad general */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');
    html, body, [class*="st-"] {
        font-family: 'Inter', sans-serif;
        color: #333333; /* Texto oscuro para máxima legibilidad */
    }

    /* Títulos y Branding - Más prominentes */
    h1, h2, h3, .st-emotion-cache-10trblm h1, .st-emotion-cache-10trblm h3 {
        color: #002868; /* Azul oscuro profesional (dominicano) */
        font-weight: 800;
        text-shadow: 1px 1px 2px rgba(0,0,0,0.05); /* Sombra sutil para levantar el texto */
    }
    .st-emotion-cache-10trblm h2 {
        border-bottom: 2px solid #EEEEEE;
        padding-bottom: 5px;
        margin-top: 20px;
        color: #1A1A1A; /* Color de subtítulos más neutro */
    }
    
    /* Contenedor principal con fondo ligeramente gris para mejor contraste de tarjetas */
    .block-container {
        padding-top: 1.5rem; /* Más espacio */
        padding-bottom: 1rem;
        padding-left: 2rem;
        padding-right: 2rem;
        background-color: #F8F8F8; /* Fondo sutilmente gris */
    }

    /* Estilo de Tarjetas/Contenedores para levantarlos del fondo (MEJORA DE LEGIBILIDAD VISUAL) */
    .st-emotion-cache-1cpx9h1, .risk-gauge-container {
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1); /* Sombra para crear profundidad */
        border: 1px solid #E0E0E0 !important;
        border-radius: 12px;
        background: white; /* Aseguramos fondo blanco en las "tarjetas" */
    }

    /* Estilo de Botones y Elementos Interactivos */
    .stButton>button {
        background-color: #002868;
        color: white;
        border-radius: 8px;
        font-weight: 600;
        padding: 10px 20px;
        transition: background-color 0.3s;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
    }
    .stButton>button:hover {
        background-color: #0040A0;
    }

    /* Estilos de Métricas (KPIs) - Más grandes y claros */
    [data-testid="stMetricValue"] {
        font-size: 1.5rem;
        font-weight: 700;
        color: #002868; /* Usamos el azul principal para los valores de KPI */
    }
    
    /* Encabezado de DataFrames (MEJORA DE LEGIBILIDAD) */
    .st-emotion-cache-k3g09m th {
        background-color: #002868 !important; 
        color: white !important;
        font-weight: 700;
    }
    
    /* Medidor de Riesgo (Visualización Impactante) */
    .risk-gauge-container {
        border: 2px solid #ccc;
        border-radius: 12px;
        padding: 15px;
        text-align: center;
        margin-bottom: 20px;
        background: white; /* Aseguramos fondo blanco */
        box-shadow: 0 6px 15px rgba(206, 17, 38, 0.15); /* Sombra de impacto */
    }
    .risk-gauge-bar {
        height: 30px;
        border-radius: 15px;
        background: linear-gradient(to right, 
            #4CAF50 0%, /* Verde (Moderado) */
            #FFC400 40%, /* Amarillo (Alto) */
            #FFC400 70%, /* Naranja/Amarillo (Alto) */
            #CE1126 100% /* Rojo (Muy Alto) */
        );
        position: relative;
        margin-top: 10px;
    }
    .risk-gauge-marker {
        position: absolute;
        top: -15px; /* Subido un poco para mayor impacto */
        transform: translateX(-50%);
        width: 8px; /* Más ancho */
        height: 60px; /* Más alto */
        background-color: black;
        border-radius: 4px;
        z-index: 10;
        box-shadow: 0 0 8px rgba(0,0,0,0.8);
    }
    .risk-label {
        position: absolute;
        top: 45px;
        font-size: 0.8em;
        font-weight: 600;
        color: #555;
    }
    .risk-label.moderate { left: 20%; transform: translateX(-50%); color: #4CAF50; }
    .risk-label.high { left: 55%; transform: translateX(-50%); }
    .risk-label.critical { right: 90%; transform: translateX(50%); color: #CE1126; } /* Ajuste de posición */

    /* Estilos para el visor del reporte HTML */
    .report-viewer iframe {
        border: 2px solid #002868;
        border-radius: 12px;
        width: 100%;
        min-height: 500px;
    }
</style>
""", unsafe_allow_html=True)


# --- 0. CLASE DE PERSISTENCIA SIMULADA (REEMPLAZO DE FIRESTORE) ---
# NOTA: En un entorno de producción con Streamlit Cloud, este archivo JSON NO persistiría 
# entre sesiones. Se usa para simular un ambiente con autenticación y DB.
DB_FILE_PATH = "nefro_db.json"

class DataStore:
    def __init__(self, file_path):
        self.file_path = file_path
        self._initialize_db()

    def _initialize_db(self):
        """Crea el archivo DB con datos iniciales si no existe, o asegura la estructura."""
        initial_data = {
            "users": {
                "admin": {"pwd": "admin", "role": "admin", "id": "admin_nefro", "active": True},
                "dr.perez": {"pwd": "pass1", "role": "doctor", "id": "dr_perez_uid_001", "active": True},
                "dr.gomez": {"pwd": "pass2", "role": "doctor", "id": "dr_gomez_uid_002", "active": True},
                "dr.sanchez": {"pwd": "pass3", "role": "doctor", "id": "dr_sanchez_uid_003", "active": False},
            },
            "file_history": [
                {"usuario": "dr.perez", "user_id": "dr_perez_uid_001", "timestamp": "2025-05-02 14:30", "filename": "Mis_Pacientes_Q1_2025.xlsx", "patients": 55, "high_risk_count": 12},
                {"usuario": "dr.gomez", "user_id": "dr_gomez_uid_002", "timestamp": "2025-05-01 11:00", "filename": "Pacientes_HTA.xlsx", "patients": 80, "high_risk_count": 25},
            ],
            # COLECCIÓN PARA REGISTROS INDIVIDUALES DE PACIENTES
            "patient_records": [
                # Ejemplo 1: Paciente de Alto Riesgo Inicial que ha sido evaluado dos veces
                {"nombre_paciente": "Maria Almonte", "user_id": "dr_perez_uid_001", "usuario": "dr.perez", "timestamp": "2024-10-01 10:00:00", "edad": 60, "imc": 30.1, "presion_sistolica": 160, "creatinina": 1.9, "glucosa_ayunas": 190, "risk": 78.0, "nivel": "MUY ALTO", "color": "#CE1126", "html_report": "<!-- Reporte inicial de Maria Almonte (simulado) -->"},
                {"nombre_paciente": "Maria Almonte", "user_id": "dr_perez_uid_001", "usuario": "dr.perez", "timestamp": "2025-01-15 11:30:00", "edad": 60, "imc": 28.5, "presion_sistolica": 140, "creatinina": 1.5, "glucosa_ayunas": 140, "risk": 55.0, "nivel": "ALTO", "color": "#FFC400", "html_report": "<!-- Reporte intermedio de Maria Almonte (simulado) -->"},
                # Ejemplo 2: Paciente de Bajo Riesgo
                {"nombre_paciente": "Juan Perez", "user_id": "dr_gomez_uid_002", "usuario": "dr.gomez", "timestamp": "2025-05-02 12:00:00", "edad": 45, "imc": 24.0, "presion_sistolica": 120, "creatinina": 1.0, "glucosa_ayunas": 95, "risk": 20.0, "nivel": "MODERADO", "color": "#4CAF50", "html_report": "<!-- Reporte único de Juan Perez (simulado) -->"},
            ]
        }
        
        if not os.path.exists(self.file_path):
            self._write_db(initial_data)
        else:
            db = self._read_db()
            if 'patient_records' not in db:
                db['patient_records'] = []
            if 'file_history' not in db: # Asegurar que file_history exista
                db['file_history'] = []
            self._write_db(db)
            
    def _read_db(self):
        """Lee todos los datos del archivo DB."""
        if not os.path.exists(self.file_path):
            self._initialize_db()
        try:
            with open(self.file_path, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            st.error("Error al leer la base de datos simulada. Reiniciando DB.")
            self._initialize_db()
            with open(self.file_path, 'r') as f:
                return json.load(f)

    def _write_db(self, data):
        """Escribe todos los datos al archivo DB."""
        with open(self.file_path, 'w') as f:
            json.dump(data, f, indent=4)

    def get_user(self, username):
        """Obtiene un usuario por nombre de usuario."""
        db = self._read_db()
        return db['users'].get(username)

    def get_all_users(self):
        """Obtiene todos los usuarios."""
        db = self._read_db()
        return db['users']

    def create_user(self, username, user_data):
        """Crea un nuevo usuario."""
        db = self._read_db()
        db['users'][username] = user_data
        self._write_db(db)

    # NUEVA FUNCIÓN PARA ACTUALIZAR USUARIO (USADA EN ADMIN)
    def update_user(self, username, updates):
        db = self._read_db()
        if username in db['users']:
            db['users'][username].update(updates)
            self._write_db(db)
            return True
        return False


    def get_file_history(self):
        """Obtiene todo el historial de archivos subidos."""
        db = self._read_db()
        # Ordena por timestamp descendente para mostrar lo más reciente primero
        return sorted(db.get('file_history', []), key=lambda x: x['timestamp'], reverse=True)

    def add_file_record(self, record):
        """Añade un nuevo registro de archivo al historial."""
        db = self._read_db()
        db['file_history'].insert(0, record) 
        self._write_db(db)
        
    def add_patient_record(self, record):
        """Añade un nuevo registro individual de paciente."""
        db = self._read_db()
        db['patient_records'].insert(0, record) 
        self._write_db(db)

    def get_patient_records(self, patient_name):
        """Obtiene el historial de predicciones de un paciente por NOMBRE."""
        db = self._read_db()
        # Búsqueda insensible a mayúsculas/minúsculas y ordenada por fecha
        return sorted([
            record for record in db.get('patient_records', []) 
            if record.get('nombre_paciente', '').lower() == patient_name.lower()
        ], key=lambda x: x['timestamp'], reverse=False) # Ascendente para la gráfica de evolución

    def get_all_patient_names(self):
        """Obtiene todos los nombres de pacientes únicos registrados."""
        db = self._read_db()
        return sorted(list(set(
            record.get('nombre_paciente') for record in db.get('patient_records', []) 
            if record.get('nombre_paciente')
        )))

# Inicializamos el DataStore (simulando la conexión a Firestore)
db_store = DataStore(DB_FILE_PATH)

# --- 1. Título y Branding ---
st.markdown("<h1 style='text-align: center;'>🫘 NefroPredict RD 2025</h1>", unsafe_allow_html=True)
st.markdown("<h3 style='text-align: center; color: #555555;'>Detección temprana de enfermedad renal crónica</h3>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color:#CE1126; font-size:1.1em; font-weight: 600;'>República Dominicana 🇩🇴</p>", unsafe_allow_html=True)

# --- FUNCIÓN DE CARGA DE MODELO ---
@st.cache_resource
def load_model(path):
    try:
        model = joblib.load(path)
        st.sidebar.success("Modelo ML cargado correctamente.")
        return model
    except (FileNotFoundError, Exception) as e:
        st.sidebar.error(f"⚠️ Error al cargar el modelo. Usando modo simulación. (Detalle: {e})")
        return None

# El modelo joblib debe estar en el mismo directorio. Si no lo está, usará simulación.
nefro_model = load_model('modelo_erc.joblib')
model_loaded = nefro_model is not None


# --- 2. SISTEMA DE AUTENTICACIÓN Y ROLES ---

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_id = None
    st.session_state.user_role = None
    st.session_state.username = None
    st.session_state.last_mass_df = None
    st.session_state.last_individual_report = None


def check_login():
    """Maneja el flujo de login usando DataStore."""
    if not st.session_state.logged_in:
        st.markdown("### 🔐 Acceso de Usuario")
        
        with st.form("login_form"):
            user = st.text_input("Nombre de Usuario (ej: admin, dr.perez)", key="user_input").lower()
            pwd = st.text_input("Contraseña", type="password", key="password_input")
            
            submitted = st.form_submit_button("Ingresar")

            if submitted:
                user_data = db_store.get_user(user)

                if user_data and user_data['pwd'] == pwd:
                    if not user_data.get('active', True):
                        st.error("Tu cuenta ha sido desactivada. Por favor, contacta al administrador.")
                        return False

                    st.session_state.logged_in = True
                    st.session_state.user_id = user_data['id']
                    st.session_state.user_role = user_data['role']
                    st.session_state.username = user
                    st.success(f"¡Acceso concedido! Rol: {st.session_state.user_role.capitalize()}")
                    time.sleep(0.1)
                    st.rerun()
                else:
                    st.error("Usuario o contraseña incorrectos.")
        
        st.sidebar.caption("Usuarios de prueba: `admin`/`admin` | `dr.perez`/`pass1` (Historial: Maria Almonte) | `dr.gomez`/`pass2` (Historial: Juan Perez) | `dr.sanchez`/`pass3` (Inactivo)")
        st.stop()
    return True

if not check_login():
    st.stop()
    
# Mostrar información de sesión y botón de Logout
col_user, col_logout = st.columns([4, 1])
current_user_data = db_store.get_user(st.session_state.username)
current_status = "Activo" if current_user_data.get('active', True) else "INACTIVO"

with col_user:
    st.success(f"✅ Sesión activa | Usuario: **{st.session_state.username}** | Rol: **{st.session_state.user_role.capitalize()}** | Estado: **{current_status}**")
with col_logout:
    if st.button("Cerrar Sesión", key="logout_btn"):
        st.session_state.logged_in = False
        st.session_state.user_id = None
        st.session_state.user_role = None
        st.session_state.username = None
        st.session_state.last_mass_df = None
        st.session_state.last_individual_report = None
        st.rerun()

st.markdown("---")

# --- 3. FUNCIONES DE GESTIÓN (Para Admin Panel) ---
def create_new_user_db(username, password, role="doctor"):
    """Crea un nuevo usuario en la DB (DataStore)."""
    if db_store.get_user(username):
        return False, "Ese nombre de usuario ya existe."
    
    user_id = f"{role}_{username}_uid_{int(time.time())}"
    user_data = {"pwd": password, "role": role, "id": user_id, "active": True}
    db_store.create_user(username, user_data)
    return True, f"Usuario '{username}' ({role.capitalize()}) creado con éxito (ID: {user_id})."

def get_doctors_db():
    """Obtiene la lista de todos los médicos (no admin) de la DB."""
    all_users = db_store.get_all_users()
    return {k: v for k, v in all_users.items() if v['role'] == 'doctor'}

def get_global_history_db():
    """Obtiene todo el historial de archivos de la DB."""
    return db_store.get_file_history()


# --- 4. FUNCIONES DE PREDICCIÓN Y EXPLICACIÓN ---

def get_risk_level(risk):
    """Clasifica el riesgo y asigna colores y recomendaciones."""
    if risk > 70:
        return "MUY ALTO", "#CE1126", "Referir URGENTE a nefrólogo. Se requiere intervención intensiva y seguimiento inmediato."
    elif risk > 40:
        return "ALTO", "#FFC400", "Control estricto cada 3 meses. Monitorear biomarcadores y ajustar terapia farmacológica."
    else:
        return "MODERADO", "#4CAF50", "Control anual o bianual. Reafirmar hábitos de vida saludables y control de presión arterial."

def predict_risk(data_series):
    """Realiza la predicción de riesgo (real o simulada) a partir de una Serie de Pandas."""
    # Aseguramos que solo las columnas necesarias estén presentes y en orden
    data = data_series[['edad', 'imc', 'presion_sistolica', 'glucosa_ayunas', 'creatinina']].to_frame().T
    
    if model_loaded:
        # Nota: Aquí se asume que el modelo fue entrenado con las columnas en el orden correcto
        prediction_proba = nefro_model.predict_proba(data)[:, 1][0]
        return (prediction_proba * 100).round(1)
    else:
        # Simulación de riesgo (la simulación original del usuario)
        base_risk = 15.0 
        adjustment = (data['creatinina'].iloc[0] * 15) + \
                     (data['glucosa_ayunas'].iloc[0] * 0.15) + \
                     (data['edad'].iloc[0] * 0.4)
        
        simulated_risk = base_risk + adjustment + (np.random.rand() * 10 - 5)
        return max(1.0, min(99.9, simulated_risk)).round(1)

def generate_explanation_data(row):
    """Simula la contribución de cada característica al riesgo (como los valores SHAP)."""
    contributions = {}
    
    # Valores de referencia de riesgo (umbrales simplificados)
    creatinina = row.get('creatinina', 1.0) 
    glucosa = row.get('glucosa_ayunas', 90)
    presion = row.get('presion_sistolica', 120) 
    edad = row.get('edad', 50) 
    imc = row.get('imc', 25.0) 

    # Lógica de Contribución (Aumento/Disminución del riesgo base):
    # Creatinina
    if creatinina > 2.0: contributions['Creatinina (Alto)'] = 0.40
    elif creatinina > 1.3: contributions['Creatinina (Elevado)'] = 0.25
    else: contributions['Creatinina (Normal)'] = -0.10
    
    # Glucosa Ayunas
    if glucosa > 125: contributions['Glucosa Ayunas (Diabetes)'] = 0.20
    elif glucosa > 100: contributions['Glucosa Ayunas (Pre-Diab)'] = 0.05
    else: contributions['Glucosa Ayunas (Normal)'] = -0.05

    # Presión Sistólica
    if presion > 140: contributions['Presión Sistólica (HTA)'] = 0.15
    elif presion > 130: contributions['Presión Sistólica (Pre-HTA)'] = 0.05
    else: contributions['Presión Sistólica (Normal)'] = -0.05
        
    # Edad
    if edad > 65: contributions['Edad (Mayor de 65)'] = 0.10
    else: contributions['Edad (Menor de 65)'] = -0.03

    # IMC
    if imc > 30.0: contributions['IMC (Obesidad)'] = 0.08
    elif imc < 18.5: contributions['IMC (Bajo Peso)'] = 0.03 # También es un factor de riesgo leve
    else: contributions['IMC (Normal)'] = -0.02

    # Normalizar las contribuciones para que el gráfico sea más informativo (total de impactos absolutos = 1)
    total_abs = sum(abs(v) for v in contributions.values())
    if total_abs > 0:
        contributions = {k: v / total_abs for k, v in contributions.items()}

    return contributions

def display_explanation_charts(data):
    """Muestra los datos de contribución como un gráfico de barras horizontal (interactivo)."""
    
    df_chart = pd.DataFrame(data.items(), columns=['Factor', 'Contribucion_Normalizada'])
    df_chart['Riesgo_Impacto'] = np.where(df_chart['Contribucion_Normalizada'] > 0, 'Aumenta Riesgo', 'Disminuye Riesgo')
    df_chart['Color'] = np.where(df_chart['Contribucion_Normalizada'] > 0, '#CE1126', '#4CAF50') # Rojo o Verde

    st.markdown("#### 📈 Contribución Individual de Factores")
    # Streamlit's st.bar_chart es simple, pero suficiente para la visualización.
    st.bar_chart(df_chart, x='Factor', y='Contribucion_Normalizada', color='Color', use_container_width=True)
    st.markdown("<p style='font-size: 0.8em; text-align: center; color: #888;'>Las barras rojas representan un factor que aumenta el riesgo. Las barras verdes lo disminuyen.</p>", unsafe_allow_html=True)


# --- 5. FUNCIÓN DE REPORTE INDIVIDUAL PERSONALIZADO (PDF SIMULADO) ---

def generate_individual_report_html(patient_data, risk_percentage, doctor_name, explanation_data):
    """Genera el contenido HTML para el reporte individual, listo para imprimir (Guardar como PDF)."""
    
    nivel, color, recomendacion = get_risk_level(risk_percentage)
    now = time.strftime("%Y-%m-%d %H:%M:%S")

    explanation_rows = ""
    for factor, contrib in explanation_data.items():
        contrib_text = f"{abs(contrib*100):.1f}%"
        arrow = "🔺" if contrib > 0 else "🔻"
        color_contrib = "color:#CE1126;" if contrib > 0 else "color:#4CAF50;"
        explanation_rows += f"""
        <tr>
            <td>{factor}</td>
            <td style="{color_contrib} font-weight: bold;">{arrow} {contrib_text}</td>
        </tr>
        """

    # Estilos CSS más limpios para el reporte
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Reporte NefroPredict - {patient_data['nombre_paciente']}</title>
        <style>
            @media print, screen {{
                body {{ font-family: 'Inter', sans-serif; color: #333; margin: 0; padding: 0; }}
                h1, h2, h3 {{ margin-top: 0; }}
                .report-container {{ width: 210mm; margin: 0 auto; padding: 20mm; box-shadow: 0 0 10px rgba(0,0,0,0.1); }}
                .header {{ text-align: center; border-bottom: 3px solid #002868; padding-bottom: 10px; margin-bottom: 20px; }}
                .doctor-info {{ text-align: right; font-size: 0.9em; }}
                .risk-box {{ 
                    padding: 15px; 
                    margin-top: 20px; 
                    border: 3px solid {color}; 
                    background-color: {color}15; /* Sombra ligera del color de riesgo */
                    text-align: center;
                    border-radius: 8px;
                }}
                .risk-level {{ font-size: 3em; font-weight: bold; color: {color}; }}
                .data-table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
                .data-table th, .data-table td {{ border: 1px solid #ddd; padding: 10px; text-align: left; }}
                .data-table th {{ background-color: #f0f0f0; }}
                .recommendation {{ margin-top: 30px; padding: 15px; border-left: 5px solid {color}; background-color: #f5f5f5; border-radius: 4px; }}
                .explanation-table {{ width: 100%; border-collapse: collapse; margin-top: 10px;}}
                .explanation-table th, .explanation-table td {{ padding: 8px; text-align: left; border: none; border-bottom: 1px dotted #ccc;}}
                @media print {{ .printable-report {{ box-shadow: none; border: none; }} }}
            }}
            /* Estilos para visualización en Streamlit */
            .printable-report {{ border: 1px solid #ccc; padding: 20px; border-radius: 8px; background-color: white; }}
        </style>
    </head>
    <body>
        <div class="report-container printable-report">
            <div class="header">
                <h1 style="color:#002868; font-size: 1.8em;">NefroPredict RD</h1>
                <h3 style="color:#555;">Reporte de Riesgo de Enfermedad Renal Crónica</h3>
            </div>
            
            <div class="doctor-info">
                <p><strong>Médico Responsable:</strong> Dr./Dra. {doctor_name.upper()}</p>
                <p><strong>Fecha del Reporte:</strong> {now}</p>
                <p><strong>Paciente:</strong> {patient_data['nombre_paciente']}</p>
            </div>
            
            <div class="risk-box">
                Riesgo de ERC a 5 años
                <div class="risk-level">{risk_percentage:.1f}%</div>
                <p style="font-size: 1.2em;">**NIVEL DE RIESGO: {nivel}**</p>
            </div>

            <h2>Datos Biomarcadores</h2>
            <table class="data-table">
                <tr><th>Variable</th><th>Valor</th><th>Unidad</th></tr>
                <tr><td>Edad</td><td>{patient_data['edad']}</td><td>años</td></tr>
                <tr><td>IMC</td><td>{patient_data['imc']:.1f}</td><td>kg/m²</td></tr>
                <tr><td>Presión Sistólica</td><td>{patient_data['presion_sistolica']}</td><td>mmHg</td></tr>
                <tr><td>Glucosa Ayunas</td><td>{patient_data['glucosa_ayunas']}</td><td>mg/dL</td></tr>
                <tr><td>Creatinina</td><td>{patient_data['creatinina']:.2f}</td><td>mg/dL</td></tr>
            </table>

            <h2>Análisis de Contribución al Riesgo</h2>
            <p>Factores que influyen en el resultado predictivo:</p>
            <table class="explanation-table">
                <tr><th>Factor</th><th>Impacto Normalizado</th></tr>
                {explanation_rows}
            </table>
            <div style="clear: both;"></div>
            
            <div class="recommendation">
                <h3 style="color:{color};">RECOMENDACIÓN CLÍNICA</h3>
                <p style="font-size: 1.1em;">{recomendacion}</p>
            </div>
        </div>
        </body>
    </html>
    """
    return html_content


# --- 6. FUNCIÓN DE LA PLANTILLA EXCEL ---

def get_excel_template():
    """Genera la plantilla Excel recomendada para la carga masiva."""
    data = {
        'id_paciente': ['P-1001', 'P-1002', 'P-1003'], 
        'edad': [65, 48, 72],
        'imc': [32.5, 24.1, 28.9],
        'presion_sistolica': [150, 125, 140],
        'glucosa_ayunas': [180, 95, 115],
        'creatinina': [1.8, 0.9, 1.5],
    }
    df_template = pd.DataFrame(data)
    
    # Usando 'openpyxl' como motor para asegurar compatibilidad
    output = io.BytesIO()
    writer = pd.ExcelWriter(output, engine='openpyxl') 
    df_template.to_excel(writer, index=False, sheet_name='Plantilla_ERC')
    writer.close()
    processed_data = output.getvalue()
    return processed_data


# --- 7. Funciones de Cálculo Adicionales (eGFR) ---

def calculate_egfr(creatinine, age, sex):
    """Calcula eGFR usando la fórmula CKD-EPI 2009 (sin raza, para simplificar)."""
    # Asegura que la edad no sea 0 para evitar error de 0.993**0 = 1
    age = max(1, age) 
    
    k = 0.7 if sex == 'F' else 0.9
    a = -0.329 if sex == 'F' else -0.411
    
    # CKD-EPI 2009 (Formula simplificada)
    egfr_val = 141 * (min(creatinine / k, 1)**a) * (max(creatinine / k, 1)**-1.209) * (0.993**age) * (1.018 if sex == 'F' else 1)
    
    return egfr_val.round(1)


# --- 8. Interfaz del Médico (Estructura de pestañas) ---
if st.session_state.user_role == 'doctor' or st.session_state.user_role == 'admin':
    
    st.subheader("Selección de Modo de Evaluación")
    
    # Nuevas pestañas añadidas: Historial Clínico, Otros Cálculos y Mi Historial
    tabs_list = [
        "🩺 Predicción Individual", 
        "📁 Carga Masiva (Excel)", 
        "📂 Historial Clínico", 
        "⭐ Otros Cálculos Clínicos", 
        "⏱️ Mi Historial de Archivos"
    ]
    
    if st.session_state.user_role == 'admin':
        tabs_list.append("⚙️ Panel de Administrador")
    
    tab_individual, tab_masiva, tab_patient_history, tab_otros, tab_historial, *tab_admin_list = st.tabs(tabs_list)
    tab_admin = tab_admin_list[0] if tab_admin_list else None


    # =================================================================
    # 8.1 PESTAÑA DE PREDICCIÓN INDIVIDUAL (Implementación del usuario con corrección)
    # =================================================================
    with tab_individual:
        st.markdown("#### Ingreso de Datos de un Único Paciente")
        st.info("Ingresa los 5 biomarcadores clave para obtener un riesgo instantáneo y un reporte descargable, que será guardado en el Historial Clínico.")
        
        with st.form("individual_patient_form"):
            col_id, col_edad = st.columns(2)
            with col_id:
                nombre_paciente = st.text_input("Nombre Completo del Paciente (Ej: María Almonte)", value="Nuevo Paciente", key="input_name")
            with col_edad:
                edad = st.number_input("Edad (años)", min_value=1, max_value=120, value=55, key="input_edad")

            col_1, col_2 = st.columns(2)
            with col_1:
                imc = st.number_input("IMC (kg/m²)", min_value=10.0, max_value=60.0, value=25.0, step=0.1, key="input_imc", help="Índice de Masa Corporal")
                glucosa_ayunas = st.number_input("Glucosa en Ayunas (mg/dL)", min_value=50, max_value=500, value=90, key="input_glucosa")
            with col_2:
                presion_sistolica = st.number_input("Presión Sistólica (mmHg)", min_value=80, max_value=250, value=120, key="input_presion")
                creatinina = st.number_input("Creatinina (mg/dL)", min_value=0.1, max_value=10.0, value=1.0, step=0.01, format="%.2f", key="input_creatinina")
            
            submitted = st.form_submit_button("Calcular Riesgo y Guardar en Historial Clínico")
            
            if submitted:
                patient_data = pd.Series({
                    'nombre_paciente': nombre_paciente, 
                    'edad': edad,
                    'imc': imc,
                    'presion_sistolica': presion_sistolica,
                    'glucosa_ayunas': glucosa_ayunas,
                    'creatinina': creatinina
                })
                
                risk_percentage = predict_risk(patient_data)
                explanation_data = generate_explanation_data(patient_data)
                
                # Generar el reporte HTML para guardarlo
                html_report = generate_individual_report_html(
                    patient_data.to_dict(), 
                    risk_percentage, 
                    st.session_state.username, 
                    explanation_data
                )
                
                # Guardar el registro individual
                nivel, color, _ = get_risk_level(risk_percentage)
                record = {
                    "nombre_paciente": nombre_paciente,
                    "user_id": st.session_state.user_id,
                    "usuario": st.session_state.username,
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "edad": patient_data['edad'],
                    "imc": patient_data['imc'],
                    "presion_sistolica": patient_data['presion_sistolica'],
                    "creatinina": patient_data['creatinina'],
                    "glucosa_ayunas": patient_data['glucosa_ayunas'],
                    "risk": risk_percentage,
                    "nivel": nivel,
                    "color": color,
                    "html_report": html_report # Guardamos el reporte completo
                }
                db_store.add_patient_record(record)
                st.success(f"Registro de '{nombre_paciente}' guardado correctamente y listo para análisis. Dirígete a 'Historial Clínico' para ver la evolución.")


                st.session_state.last_individual_report = {
                    'data': patient_data.to_dict(),
                    'risk': risk_percentage,
                    'explanation': explanation_data,
                    'html_report': html_report
                }
                time.sleep(0.1)
                st.rerun() 

        if 'last_individual_report' in st.session_state:
            report_data = st.session_state.last_individual_report
            risk_percentage = report_data['risk']
            nivel, color, recomendacion = get_risk_level(risk_percentage)
            
            st.markdown("---")
            st.markdown("### 3. Resultados y Reporte Instantáneo")
            
            # --- MEJORA VISUAL: MEDIDOR DE RIESGO ESTILIZADO ---
            marker_position = risk_percentage 
            
            st.markdown(f"""
                <div class="risk-gauge-container">
                    <h2 style="color: {color}; margin-bottom: 5px;">{nivel}</h2>
                    <h1 style="font-size: 3.5em; color: #333; margin-top: 0; margin-bottom: 20px;">{risk_percentage:.1f}%</h1>
                    
                    <div class="risk-gauge-bar">
                        <div class="risk-gauge-marker" style="left: {marker_position}%;"></div>
                    </div>
                    <span class="risk-label moderate">Moderado (0-40%)</span>
                    <span class="risk-label high" style="left: 50%;">Alto (40-70%)</span>
                    <span class="risk-label critical" style="left: 80%;">Muy Alto (70-100%)</span>
                </div>
            """, unsafe_allow_html=True)
            
            # Recomendación clínica destacada
            st.markdown(f"""
                <div style='border: 1px solid #ddd; padding: 15px; border-left: 5px solid {color}; background-color: #f0f0f0; border-radius: 4px;'>
                    <h4 style='color:{color};'>Recomendación Clínica</h4>
                    <p style='font-size: 1.1em;'>{recomendacion}</p>
                </div>
            """, unsafe_allow_html=True)
            
            # --- FIN MEJORA VISUAL ---

            st.markdown("---")
            
            display_explanation_charts(report_data['explanation'])
            
            st.markdown("---")
            
            st.markdown("### 4. Generar Documento Imprimible (PDF)")
            
            # Muestra el reporte HTML en un Iframe para previsualización
            st.markdown('<div class="report-viewer">', unsafe_allow_html=True)
            st.components.v1.html(report_data['html_report'], height=500, scrolling=True)
            st.markdown('</div>', unsafe_allow_html=True)

            # Botón de impresión (Utiliza el JS print() estándar)
            st.components.v1.html(
                f"""
                <button onclick="window.print()" 
                    style="background-color: #CE1126; color: white; padding: 10px 20px; border: none; border-radius: 8px; cursor: pointer; font-size: 1.1em; box-shadow: 0 4px 6px rgba(0,0,0,0.2); width: 100%;">
                    🖨️ Generar PDF (Imprimir)
                </button>
                """,
                height=60,
            )


    # =================================================================
    # 8.2 PESTAÑA DE CARGA MASIVA (Excel)
    # =================================================================
    with tab_masiva:
        st.markdown("#### 🚀 Predicción de Riesgo por Lotes (Carga Masiva)")
        st.info("Sube un archivo Excel (.xlsx) o CSV con las columnas: `id_paciente`, `edad`, `imc`, `presion_sistolica`, `glucosa_ayunas`, `creatinina`.")

        # 1. Descarga de Plantilla
        excel_template = get_excel_template()
        st.download_button(
            label="📥 Descargar Plantilla de Ejemplo (.xlsx)",
            data=excel_template,
            file_name="plantilla_nefropredict_rd.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key='download_template'
        )
        st.markdown("---")

        # 2. Carga de Archivo
        uploaded_file = st.file_uploader("Sube tu archivo de datos (Excel o CSV)", type=["xlsx", "csv"])

        if uploaded_file is not None:
            try:
                if uploaded_file.name.endswith('.csv'):
                    df = pd.read_csv(uploaded_file)
                else:
                    df = pd.read_excel(uploaded_file)
                
                # Asegurar columnas requeridas
                required_cols = ['edad', 'imc', 'presion_sistolica', 'glucosa_ayunas', 'creatinina']
                if not all(col in df.columns for col in required_cols):
                    st.error(f"El archivo debe contener las siguientes columnas: {', '.join(required_cols)}")
                else:
                    st.success(f"Archivo '{uploaded_file.name}' cargado con {len(df)} registros.")
                    
                    # 3. Realizar predicciones
                    st.warning("Calculando riesgo...")
                    
                    # Aplicar la predicción fila por fila
                    df['risk_percentage'] = df.apply(predict_risk, axis=1)
                    df[['risk_level', 'risk_color', 'recomendacion']] = df['risk_percentage'].apply(
                        lambda x: pd.Series(get_risk_level(x))
                    )
                    
                    # 4. Mostrar Resultados y Resumen
                    st.markdown("---")
                    st.markdown("### Resultados de la Evaluación Masiva")
                    
                    high_risk_count = len(df[df['risk_level'].isin(['ALTO', 'MUY ALTO'])])
                    
                    col_kpi_1, col_kpi_2 = st.columns(2)
                    with col_kpi_1:
                        st.metric("Pacientes Evaluados", len(df))
                    with col_kpi_2:
                        st.metric("Casos de Alto/Muy Alto Riesgo", high_risk_count, f"{high_risk_count/len(df)*100:.1f}% del total")
                    
                    # Guardar historial de archivo
                    file_record = {
                        "usuario": st.session_state.username,
                        "user_id": st.session_state.user_id,
                        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                        "filename": uploaded_file.name,
                        "patients": len(df),
                        "high_risk_count": high_risk_count
                    }
                    db_store.add_file_record(file_record)
                    st.session_state.last_mass_df = df
                    
                    # 5. Mostrar tabla (solo columnas relevantes)
                    display_cols = ['id_paciente', 'edad', 'creatinina', 'risk_percentage', 'risk_level', 'recomendacion']
                    st.dataframe(df[display_cols].rename(columns={
                        'id_paciente': 'ID Paciente', 
                        'risk_percentage': 'Riesgo (%)', 
                        'risk_level': 'Nivel de Riesgo',
                        'creatinina': 'Creatinina (mg/dL)'
                    }).sort_values(by='Riesgo (%)', ascending=False), 
                        hide_index=True, use_container_width=True
                    )
                    
                    # 6. Botón de descarga de resultados
                    csv_results = df.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="💾 Descargar Resultados con Predicción (.csv)",
                        data=csv_results,
                        file_name=f"nefropredict_resultados_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv",
                        key='download_results'
                    )

            except Exception as e:
                st.error(f"Ocurrió un error al procesar el archivo. Asegúrate que el formato de datos es correcto. Error: {e}")

    
    # =================================================================
    # 8.3 PESTAÑA DE HISTORIAL CLÍNICO (Seguimiento de Pacientes)
    # =================================================================
    with tab_patient_history:
        st.markdown("#### 📂 Seguimiento de la Evolución Clínica")
        st.info("Selecciona un paciente para visualizar todas las evaluaciones de riesgo almacenadas en el sistema. Los datos se obtienen del modo de 'Predicción Individual'.")

        all_patient_names = db_store.get_all_patient_names()

        if not all_patient_names:
            st.warning("Aún no se ha guardado ninguna evaluación individual. Utiliza la pestaña 'Predicción Individual' para guardar registros.")
            
        else:
            selected_patient = st.selectbox("Selecciona un Paciente", options=all_patient_names, key='patient_selector')
            
            if selected_patient:
                history_records = db_store.get_patient_records(selected_patient)
                
                if history_records:
                    df_history = pd.DataFrame(history_records)
                    
                    st.markdown(f"### Historial de Riesgo de {selected_patient}")
                    
                    # Gráfico de evolución del riesgo
                    df_history['timestamp_dt'] = pd.to_datetime(df_history['timestamp'])
                    
                    st.line_chart(df_history.set_index('timestamp_dt')['risk'], 
                                  x_label="Fecha de Evaluación", 
                                  y_label="Riesgo de ERC (%)", 
                                  color='#002868'
                    )
                    st.caption("Gráfico de la evolución del riesgo a lo largo del tiempo. Idealmente, la línea debería ser descendente.")
                    st.markdown("---")
                    
                    # Tabla de historial detallada
                    st.markdown("#### Detalle de Evaluaciones")
                    display_cols = ['timestamp', 'edad', 'imc', 'presion_sistolica', 'glucosa_ayunas', 'creatinina', 'risk', 'nivel', 'usuario']
                    df_display = df_history[display_cols].rename(columns={
                        'timestamp': 'Fecha', 
                        'risk': 'Riesgo (%)', 
                        'nivel': 'Nivel',
                        'usuario': 'Evaluado por'
                    })
                    st.dataframe(df_display.sort_values(by='Fecha', ascending=False), hide_index=True, use_container_width=True)
                
    # =================================================================
    # 8.4 PESTAÑA DE OTROS CÁLCULOS CLÍNICOS (eGFR)
    # =================================================================
    with tab_otros:
        st.markdown("#### ⭐ Calculadora de Tasa de Filtración Glomerular Estimada (eGFR)")
        st.info("Usa la fórmula CKD-EPI 2009 para estimar la función renal. TFG es clave para estadificar la ERC. [Image of the kidney structure and nephrons]")
        
        with st.form("egfr_form"):
            col_egfr_1, col_egfr_2 = st.columns(2)
            with col_egfr_1:
                egfr_creatinina = st.number_input("Creatinina (mg/dL)", min_value=0.1, max_value=10.0, value=1.0, step=0.01, format="%.2f", key="egfr_creatinina")
                egfr_age = st.number_input("Edad (años)", min_value=1, max_value=120, value=55, key="egfr_age")
            with col_egfr_2:
                egfr_sex = st.radio("Sexo Biológico", options=['M', 'F'], key="egfr_sex", horizontal=True)
                st.markdown("<br>", unsafe_allow_html=True)

            egfr_submitted = st.form_submit_button("Calcular eGFR")

        if egfr_submitted:
            egfr_result = calculate_egfr(egfr_creatinina, egfr_age, egfr_sex)
            
            # Clasificación KDIGO (Simplified)
            if egfr_result >= 90:
                kdigo_stage = "G1 (Normal o Alto)"
                kdigo_color = "#4CAF50"
            elif egfr_result >= 60:
                kdigo_stage = "G2 (Levemente Disminuida)"
                kdigo_color = "#FFC400"
            elif egfr_result >= 30:
                kdigo_stage = "G3a/G3b (Moderada/Severamente Disminuida)"
                kdigo_color = "#FF9900"
            elif egfr_result >= 15:
                kdigo_stage = "G4 (Severa)"
                kdigo_color = "#CE1126"
            else:
                kdigo_stage = "G5 (Fallo Renal)"
                kdigo_color = "#990000"

            st.markdown("---")
            
            col_res_1, col_res_2 = st.columns(2)
            with col_res_1:
                st.markdown(f"""
                <div style="padding: 20px; border: 2px solid {kdigo_color}; border-radius: 8px; text-align: center; background-color: white;">
                    <p style="font-size: 1.1em; color: #555; margin-bottom: 5px;">TFG Estimada (CKD-EPI 2009)</p>
                    <h2 style="font-size: 2.5em; color: {kdigo_color}; margin-top: 0;">{egfr_result} ml/min/1.73m²</h2>
                </div>
                """, unsafe_allow_html=True)

            with col_res_2:
                st.markdown(f"""
                <div style="padding: 20px; border: 2px solid {kdigo_color}; border-radius: 8px; text-align: center; background-color: white;">
                    <p style="font-size: 1.1em; color: #555; margin-bottom: 5px;">Etapa KDIGO</p>
                    <h2 style="font-size: 2.5em; color: {kdigo_color}; margin-top: 0;">{kdigo_stage}</h2>
                </div>
                """, unsafe_allow_html=True)
            
    # =================================================================
    # 8.5 PESTAÑA DE MI HISTORIAL DE ARCHIVOS
    # =================================================================
    with tab_historial:
        st.markdown("#### ⏱️ Historial de Archivos Cargados por el Usuario")
        st.info("Revisa los archivos de carga masiva que has procesado y los resultados clave.")
        
        all_history = db_store.get_file_history()
        
        user_history = [
            record for record in all_history if record['user_id'] == st.session_state.user_id
        ]
        
        if not user_history:
            st.warning("No tienes historial de archivos de carga masiva.")
        else:
            df_user_history = pd.DataFrame(user_history)
            st.dataframe(df_user_history[['timestamp', 'filename', 'patients', 'high_risk_count']].rename(columns={
                'timestamp': 'Fecha de Carga',
                'filename': 'Nombre de Archivo',
                'patients': 'Total Pacientes',
                'high_risk_count': 'Riesgo Alto/Muy Alto'
            }), hide_index=True, use_container_width=True)

    
    # =================================================================
    # 8.6 PESTAÑA DEL PANEL DE ADMINISTRADOR
    # =================================================================
    if st.session_state.user_role == 'admin' and tab_admin:
        with tab_admin:
            st.markdown("#### ⚙️ Panel de Control de Administrador")
            st.warning("Acceso restringido: Gestiona usuarios y revisa la actividad global del sistema.")
            
            col_user_mgt, col_user_stats = st.columns(2)

            # --- Gestión de Usuarios ---
            with col_user_mgt:
                st.markdown("##### Crear Nuevo Usuario")
                with st.form("new_user_form"):
                    new_user = st.text_input("Nombre de Usuario (único)").lower()
                    new_pwd = st.text_input("Contraseña", type="password")
                    new_role = st.selectbox("Rol", options=['doctor', 'admin'])
                    
                    if st.form_submit_button("Crear Usuario"):
                        success, message = create_new_user_db(new_user, new_pwd, new_role)
                        if success:
                            st.success(message)
                        else:
                            st.error(message)

                st.markdown("---")
                st.markdown("##### Activar/Desactivar Cuentas")
                
                all_doctors = get_doctors_db()
                doctor_usernames = list(all_doctors.keys())
                
                if doctor_usernames:
                    for username, data in all_doctors.items():
                        is_active = data.get('active', True)
                        if st.checkbox(f"Activo: **{username}** (ID: {data['id']})", value=is_active, key=f"active_{username}"):
                            if not is_active:
                                db_store.update_user(username, {'active': True})
                                st.success(f"Cuenta de {username} activada.")
                        else:
                            if is_active:
                                db_store.update_user(username, {'active': False})
                                st.error(f"Cuenta de {username} desactivada.")
                else:
                    st.info("No hay médicos registrados para gestionar.")


            # --- Estadísticas Globales ---
            with col_user_stats:
                st.markdown("##### Resumen de Actividad Global")
                
                global_history = get_global_history_db()
                
                total_files = len(global_history)
                total_patients = sum(r['patients'] for r in global_history)
                
                st.metric("Archivos de Carga Masiva Procesados", total_files)
                st.metric("Pacientes Evaluados (Total Masivo)", total_patients)
                
                if global_history:
                    df_global = pd.DataFrame(global_history)
                    
                    # Gráfico de actividad por usuario
                    st.markdown("##### Distribución de Carga por Médico")
                    activity_df = df_global.groupby('usuario')['patients'].sum().reset_index()
                    st.bar_chart(activity_df, x='usuario', y='patients', color='#002868')
                
                st.markdown("---")
                st.markdown("##### Últimas Cargas Masivas")
                if global_history:
                    st.dataframe(pd.DataFrame(global_history[:5]), hide_index=True)
                else:
                    st.info("No hay registros de carga masiva en el sistema.")
