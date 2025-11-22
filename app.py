import pandas as pd
import numpy as np
import time
import joblib
import json
import os
import io
import streamlit as st 
import altair as alt # Se añade Altair para gráficos más avanzados

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
    .risk-label.critical { right: -5%; transform: translateX(50%); color: #CE1126; }

</style>
""", unsafe_allow_html=True)


# --- 0. CLASE DE PERSISTENCIA SIMULADA (REEMPLAZO DE FIRESTORE) ---
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
        return db.get('file_history', [])

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
        # Búsqueda insensible a mayúsculas/minúsculas
        return sorted([
            record for record in db.get('patient_records', [])
            if record.get('nombre_paciente', '').lower() == patient_name.lower()
        ], key=lambda x: x['timestamp'], reverse=True)
        
    def get_all_patient_names(self):
        """Obtiene una lista única de todos los nombres de pacientes en el historial."""
        db = self._read_db()
        return sorted(list(set(record.get('nombre_paciente') for record in db.get('patient_records', []))))


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
        st.sidebar.error(f"⚠️ Error al cargar el modelo. Usando modo simulación. ({e})")
        return None

# El modelo joblib debe estar en el mismo directorio. Si no lo está, usará simulación.
nefro_model = load_model('modelo_erc.joblib')
model_loaded = nefro_model is not None


# --- 2. SISTEMA DE AUTENTICACIÓN Y ROLES ---

# Inicialización segura de session_state (Añadido 'last_individual_report' = None)
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_id = None
    st.session_state.user_role = None
    st.session_state.username = None
    st.session_state.last_mass_df = None
    st.session_state.last_individual_report = None # Inicialización explícita

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
        
        st.sidebar.caption("Usuarios de prueba: `admin`/`admin` | `dr.perez`/`pass1` (Historial: Maria Almonte) | `dr.gomez`/`pass2` (Historial: Juan Perez)")
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
        # Simulación de riesgo
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
        <script>
            // Función para iniciar la impresión/PDF
            function printReport() {{
                window.print();
            }}
        </script>
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
    # Asegura que el escritor se cierre correctamente antes de obtener el valor
    writer.close()
    processed_data = output.getvalue()
    return processed_data


# --- 7. Funciones de Cálculo Adicionales (eGFR) ---

def calculate_egfr(creatinine, age, sex):
    """Calcula eGFR usando la fórmula CKD-EPI 2009 (sin raza, para simplificar)."""
    # CKD-EPI 2009 (Formula simplificada y ampliamente usada)
    
    # Conversión de Creatinina (si es necesario) y constantes
    k = 0.7 if sex == 'F' else 0.9
    a = -0.329 if sex == 'F' else -0.411
    
    egfr_val = 141 * (min(creatinine / k, 1)**a) * (max(creatinine / k, 1)**-1.209) * (0.993**age) * (1.018 if sex == 'F' else 1)
    
    return egfr_val.round(1)

# =================================================================
# ESTRUCTURA PRINCIPAL DE LA APLICACIÓN
# =================================================================

# --- 8. Interfaz del Médico (Estructura de pestañas) ---
if st.session_state.user_role == 'doctor' or st.session_state.user_role == 'admin':
    
    st.subheader("Selección de Modo de Evaluación")
    
    # Nuevas pestañas añadidas: Historial Clínico, Otros Cálculos y Mi Historial
    tab_individual, tab_masiva, tab_patient_history, tab_otros, tab_historial = st.tabs([
        "🩺 Predicción Individual",
        "📁 Carga Masiva (Excel)",
        "📂 Historial Clínico",
        "⭐ Otros Cálculos Clínicos",
        "⏱️ Mi Historial de Archivos"
    ])

    # =================================================================
    # 8.1 PESTAÑA DE PREDICCIÓN INDIVIDUAL (Original + Resultado)
    # =================================================================
    with tab_individual:
        st.markdown("#### Ingreso de Datos de un Único Paciente")
        st.info("Ingresa los 5 biomarcadores clave para obtener un riesgo instantáneo y un reporte descargable, que será guardado en el Historial Clínico.")
        
        with st.form("individual_patient_form"):
            col_id, col_edad = st.columns(2)
            with col_id:
                # CAMBIADO: Campo ahora pide el nombre completo
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
                st.success(f"Registro de '{nombre_paciente}' guardado correctamente y listo para análisis.")


                st.session_state.last_individual_report = {
                    'data': patient_data.to_dict(),
                    'risk': risk_percentage,
                    'explanation': explanation_data,
                    'html_report': html_report
                }
                time.sleep(0.1)
                st.rerun()

            # --- SECCIÓN DE RESULTADOS ---
            report_data = st.session_state.get('last_individual_report')
            
            if report_data: # Esta condición asegura que report_data no es None o está vacío
                # Usamos .get() con un valor por defecto seguro (0.0) en caso de estructura incompleta
                risk_percentage = report_data.get('risk', 0.0)
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
                            <span class="risk-label moderate" style="left: 20%;">Moderado (0-40%)</span>
                            <span class="risk-label high">Alto (40-70%)</span>
                            <span class="risk-label critical" style="right: -5%;">Muy Alto (70-100%)</span>
                        </div>
                    </div>
                """, unsafe_allow_html=True)
                
                # Recomendación clínica destacada
                st.markdown(f"""
                    <div style='border: 1px solid #ddd; padding: 15px; border-left: 5px solid {color}; background-color: #f0f0f0; border-radius: 4px;'>
                        <h4 style='color:{color};'>RECOMENDACIÓN:</h4>
                        <p>{recomendacion}</p>
                    </div>
                """, unsafe_allow_html=True)

                st.markdown("---")

                # Gráfico de explicación de factores
                display_explanation_charts(report_data.get('explanation', {}))
                
                # Botón de Descarga
                st.download_button(
                    label="⬇️ Descargar Reporte Clínico (HTML / PDF)",
                    data=report_data.get('html_report', "Reporte no disponible."),
                    file_name=f"Reporte_{report_data.get('data', {}).get('nombre_paciente', 'Paciente')}_{time.strftime('%Y%m%d')}.html",
                    mime="text/html",
                    help="Guarda el reporte en formato HTML. Puedes abrirlo en tu navegador e imprimirlo/guardarlo como PDF."
                )

    # =================================================================
    # 8.2 PESTAÑA DE CARGA MASIVA (Excel)
    # =================================================================
    with tab_masiva:
        st.markdown("#### Procesamiento de Múltiples Pacientes (Carga Masiva)")
        st.info("Sube un archivo Excel (.xlsx o .xls) con la información de tus pacientes para calcular el riesgo en lote.")

        col_upload, col_template = st.columns([3, 1])
        
        with col_template:
            template_excel = get_excel_template()
            st.download_button(
                label="📥 Descargar Plantilla Excel",
                data=template_excel,
                file_name='Plantilla_NefroPredict_RD.xlsx',
                mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
        
        uploaded_file = col_upload.file_uploader("Subir Archivo de Pacientes (Excel)", type=['xlsx', 'xls'])

        if uploaded_file is not None:
            try:
                df_input = pd.read_excel(uploaded_file)
                st.success(f"Archivo '{uploaded_file.name}' cargado. {len(df_input)} registros encontrados.")

                # 1. Validación y Limpieza
                required_cols = ['edad', 'imc', 'presion_sistolica', 'glucosa_ayunas', 'creatinina']
                
                # Asegurar que todas las columnas requeridas existen
                if not all(col in df_input.columns for col in required_cols):
                    st.error(f"El archivo debe contener las siguientes columnas: {', '.join(required_cols)}.")
                    st.dataframe(df_input.head())
                    st.stop()
                
                # Crear columna de nombre si no existe, usando un ID por defecto
                if 'nombre_paciente' not in df_input.columns:
                    if 'id_paciente' in df_input.columns:
                        df_input['nombre_paciente'] = 'ID: ' + df_input['id_paciente'].astype(str)
                    else:
                        df_input['nombre_paciente'] = [f"Paciente {i+1}" for i in df_input.index]

                # Convertir a tipos numéricos, forzando errores a NaN
                for col in required_cols:
                    df_input[col] = pd.to_numeric(df_input[col], errors='coerce')

                # Eliminar filas con valores NaN en las columnas clave
                df_cleaned = df_input.dropna(subset=required_cols)
                
                if len(df_input) != len(df_cleaned):
                    st.warning(f"Se eliminaron {len(df_input) - len(df_cleaned)} filas con datos faltantes o inválidos.")
                
                if df_cleaned.empty:
                    st.error("No quedan registros válidos para procesar después de la limpieza.")
                    st.stop()
                    
                # 2. Aplicar Predicción
                st.markdown("#### Ejecutando Predicciones...")
                with st.spinner("Calculando riesgo de ERC para todos los pacientes..."):
                    
                    # Aplica la función de predicción a cada fila
                    df_cleaned['Riesgo_ERC_pct'] = df_cleaned.apply(lambda row: predict_risk(row), axis=1)
                    
                    # Aplica la función de nivel de riesgo y recomendación
                    df_cleaned[['Nivel_Riesgo', 'Color_Riesgo', 'Recomendacion_Clinica']] = \
                        df_cleaned.apply(lambda row: get_risk_level(row['Riesgo_ERC_pct']), axis=1, result_type='expand')
                    
                    # 3. Guardar Historial de Archivo (Metadata)
                    high_risk_count = (df_cleaned['Nivel_Riesgo'] == 'MUY ALTO').sum()
                    file_record = {
                        "usuario": st.session_state.username,
                        "user_id": st.session_state.user_id,
                        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                        "filename": uploaded_file.name,
                        "patients": len(df_cleaned),
                        "high_risk_count": high_risk_count,
                        # Nota: No guardamos el DF completo en la DB simulada, solo la metadata.
                    }
                    db_store.add_file_record(file_record)
                    st.session_state.last_mass_df = df_cleaned.to_dict() # Guardar en session_state para la visualización

                st.success("Cálculos completados y metadata guardada en tu historial.")
                
            except Exception as e:
                st.error(f"Error al procesar el archivo: {e}")

        # 4. Mostrar Resultados Masivos (si existen en la sesión)
        if st.session_state.last_mass_df is not None:
            df_results = pd.DataFrame(st.session_state.last_mass_df)
            
            st.markdown("#### Resultados del Último Procesamiento Masivo")
            
            # KPIs
            col_kpi1, col_kpi2, col_kpi3 = st.columns(3)
            col_kpi1.metric("Total de Pacientes", len(df_results))
            col_kpi2.metric("Alto/Muy Alto Riesgo", (df_results['Nivel_Riesgo'].isin(['ALTO', 'MUY ALTO'])).sum())
            col_kpi3.metric("Riesgo Crítico (Muy Alto)", (df_results['Nivel_Riesgo'] == 'MUY ALTO').sum())

            # Preparar tabla final para display y descarga
            display_cols = ['nombre_paciente', 'edad', 'imc', 'presion_sistolica', 'glucosa_ayunas', 'creatinina', 'Riesgo_ERC_pct', 'Nivel_Riesgo']
            df_display = df_results[display_cols].rename(columns={
                'Riesgo_ERC_pct': 'Riesgo (%)',
                'Nivel_Riesgo': 'Nivel de Riesgo',
            })
            
            st.dataframe(df_display, use_container_width=True)
            
            # Botón de Descarga
            csv = df_results.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="⬇️ Descargar Resultados (CSV)",
                data=csv,
                file_name=f'Resultados_NefroPredict_{time.strftime("%Y%m%d")}.csv',
                mime='text/csv',
                help="Descarga el archivo con las columnas de riesgo y recomendación añadidas."
            )
            
            # Gráfico de Distribución de Riesgo
            st.markdown("#### Distribución del Nivel de Riesgo")
            
            chart = alt.Chart(df_results).mark_bar().encode(
                x=alt.X('Nivel_Riesgo:N', sort=['MODERADO', 'ALTO', 'MUY ALTO'], title="Nivel de Riesgo"),
                y=alt.Y('count():Q', title="Número de Pacientes"),
                color=alt.Color('Nivel_Riesgo:N', scale=alt.Scale(domain=['MODERADO', 'ALTO', 'MUY ALTO'], range=['#4CAF50', '#FFC400', '#CE1126']), legend=None),
                tooltip=['Nivel_Riesgo', 'count()']
            ).properties(
                title='Conteo de Pacientes por Nivel de Riesgo'
            ).interactive()
            
            st.altair_chart(chart, use_container_width=True)


    # =================================================================
    # 8.3 PESTAÑA DE HISTORIAL CLÍNICO (Análisis longitudinal)
    # =================================================================
    with tab_patient_history:
        st.markdown("#### 📂 Historial de Predicciones por Paciente")
        st.info("Selecciona un paciente de tu historial para visualizar su evolución de riesgo a lo largo del tiempo y acceder a los reportes guardados.")
        
        all_patient_names = db_store.get_all_patient_names()
        
        if not all_patient_names:
            st.warning("Aún no tienes registros de pacientes individuales guardados. Usa la pestaña 'Predicción Individual' para empezar.")
        else:
            selected_patient = st.selectbox("Selecciona Paciente:", all_patient_names)
            
            if selected_patient:
                history_records = db_store.get_patient_records(selected_patient)
                
                st.markdown(f"### Historial de Riesgo para {selected_patient}")
                st.caption(f"Total de evaluaciones encontradas: **{len(history_records)}**")
                
                # Crear DataFrame para el gráfico de evolución
                df_history = pd.DataFrame(history_records)
                df_history['timestamp'] = pd.to_datetime(df_history['timestamp'])
                df_history = df_history.sort_values('timestamp')
                
                # Gráfico de Evolución de Riesgo
                chart_risk = alt.Chart(df_history).mark_line(point=True).encode(
                    x=alt.X('timestamp', title='Fecha de Evaluación'),
                    y=alt.Y('risk', title='Riesgo de ERC (%)', scale=alt.Scale(domain=[0, 100])),
                    color=alt.value('#002868'), # Color de línea fijo
                    tooltip=['timestamp', 'risk', 'nivel']
                ).properties(
                    title="Evolución del Riesgo de ERC"
                ).interactive()
                
                st.altair_chart(chart_risk, use_container_width=True)
                
                st.markdown("#### 📜 Detalles de Evaluaciones")
                
                # Mostrar los datos en formato tabla/lista
                for i, record in enumerate(history_records):
                    expander_title = f"**{record['timestamp']}** | Riesgo: **{record['risk']:.1f}%** ({record['nivel']})"
                    with st.expander(expander_title, expanded=(i == 0)): # Expande el más reciente
                        st.markdown(f"**Evaluación realizada por:** Dr./Dra. {record['usuario']} (ID: {record['user_id']})")
                        
                        # Datos
                        col_d1, col_d2 = st.columns(2)
                        col_d1.metric("Edad", f"{record['edad']} años")
                        col_d2.metric("IMC", f"{record['imc']:.1f} kg/m²")
                        col_d1.metric("Presión Sistólica", f"{record['presion_sistolica']} mmHg")
                        col_d2.metric("Glucosa Ayunas", f"{record['glucosa_ayunas']} mg/dL")
                        col_d1.metric("Creatinina", f"{record['creatinina']:.2f} mg/dL")
                        
                        st.markdown("---")
                        st.markdown(f"**Nivel de Riesgo:** <span style='color: {record['color']}; font-weight: bold;'>{record['nivel']} ({record['risk']:.1f}%)</span>", unsafe_allow_html=True)
                        
                        # Botón para mostrar el reporte HTML (guardado)
                        if record.get('html_report'):
                            st.download_button(
                                label="⬇️ Descargar Reporte (HTML)",
                                data=record['html_report'],
                                file_name=f"Reporte_{selected_patient}_{record['timestamp'].replace(':', '-')}.html",
                                mime="text/html",
                                key=f"download_hist_{i}"
                            )
                        else:
                            st.error("Reporte HTML no disponible para este registro.")

    # =================================================================
    # 8.4 PESTAÑA DE OTROS CÁLCULOS CLÍNICOS (Calculadora eGFR)
    # =================================================================
    with tab_otros:
        st.markdown("#### ⭐ Calculadora de Tasa de Filtración Glomerular Estimada (eGFR)")
        st.info("Utiliza la fórmula CKD-EPI 2009 (simplificada) basada en Creatinina, Edad y Sexo.")
        
        with st.form("egfr_form"):
            creatinina_egfr = st.number_input("Creatinina (mg/dL)", min_value=0.1, max_value=10.0, value=1.0, step=0.01, format="%.2f", key="input_creatinina_egfr")
            edad_egfr = st.number_input("Edad (años)", min_value=1, max_value=120, value=50, key="input_edad_egfr")
            sexo_egfr = st.radio("Sexo Biológico", options=['M', 'F'], index=0, horizontal=True)
            
            submitted_egfr = st.form_submit_button("Calcular eGFR")
            
            if submitted_egfr:
                egfr_result = calculate_egfr(creatinina_egfr, edad_egfr, sexo_egfr)
                
                # Clasificación KDIGO
                if egfr_result >= 90:
                    clasificacion = "G1 (Normal o Alto)"
                    color_egfr = "#4CAF50"
                elif egfr_result >= 60:
                    clasificacion = "G2 (Ligeramente Disminuida)"
                    color_egfr = "#A2D99C"
                elif egfr_result >= 45:
                    clasificacion = "G3a (Moderada Disminución)"
                    color_egfr = "#FFC400"
                elif egfr_result >= 30:
                    clasificacion = "G3b (Severa Disminución)"
                    color_egfr = "#F08A00"
                elif egfr_result >= 15:
                    clasificacion = "G4 (Fallo Renal Grave)"
                    color_egfr = "#CE1126"
                else:
                    clasificacion = "G5 (Fallo Renal Terminal)"
                    color_egfr = "#CE1126"
                
                st.markdown("---")
                col_e1, col_e2 = st.columns(2)
                
                col_e1.markdown(f"""
                    <div style='background-color: #ffffff; padding: 15px; border-radius: 8px; border: 2px solid {color_egfr}; text-align: center;'>
                        <p style='font-size: 1.1em; color: #555;'>Tasa de Filtración Glomerular Estimada (eGFR)</p>
                        <h1 style='font-size: 3em; color: {color_egfr}; margin: 0;'>{egfr_result}</h1>
                        <p style='font-size: 1.1em; color: #555;'>mL/min/1.73m²</p>
                    </div>
                """, unsafe_allow_html=True)
                
                col_e2.markdown(f"""
                    <div style='background-color: #f0f0f0; padding: 15px; border-radius: 8px; border: 1px solid #ccc;'>
                        <p style='font-weight: bold; margin-bottom: 5px;'>Clasificación KDIGO:</p>
                        <p style='font-size: 1.2em; font-weight: bold; color: {color_egfr};'>{clasificacion}</p>
                        <p style='font-size: 0.8em; margin-top: 10px;'>Esta clasificación ayuda a estadificar la Enfermedad Renal Crónica.</p>
                    </div>
                """, unsafe_allow_html=True)
                
                st.markdown("<br>", unsafe_allow_html=True)
                
                # Insertar diagrama de clasificación de la ERC
                st.markdown("#### Diagrama de Estadificación KDIGO")
                st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/1/14/CKD_classification_by_G_and_A_stages_%28KDIGO_2012%29.svg/1024px-CKD_classification_by_G_and_A_stages_%28KDIGO_2012%29.svg.png", 
                         caption="Clasificación de la Enfermedad Renal Crónica (ERC) según KDIGO 2012 (G-stages por eGFR y A-stages por Albuminuria).", 
                         use_column_width=True)

    # =================================================================
    # 8.5 PESTAÑA DE MI HISTORIAL DE ARCHIVOS
    # =================================================================
    with tab_historial:
        st.markdown("#### ⏱️ Historial de Archivos Subidos por el Usuario")
        st.info("Revisa la metadata de todos los archivos de procesamiento masivo que has subido.")
        
        all_file_history = db_store.get_file_history()
        
        # Filtramos solo por el usuario actual (o todos si es admin para un dashboard)
        if st.session_state.user_role == 'admin':
            st.warning("Estás viendo el historial global (todos los usuarios) por tu rol de Administrador.")
            df_history = pd.DataFrame(all_file_history)
        else:
            user_history = [record for record in all_file_history if record['user_id'] == st.session_state.user_id]
            df_history = pd.DataFrame(user_history)
        
        if df_history.empty:
            st.warning("No se encontraron registros de archivos subidos en tu historial.")
        else:
            # Asegurar que el timestamp sea datetime y ordenar
            df_history['timestamp'] = pd.to_datetime(df_history['timestamp'])
            df_history = df_history.sort_values('timestamp', ascending=False)
            
            # Mostrar solo columnas relevantes
            display_cols = ['timestamp', 'filename', 'patients', 'high_risk_count']
            
            if st.session_state.user_role == 'admin':
                display_cols.insert(0, 'usuario')
                
            df_history_display = df_history[display_cols].rename(columns={
                'timestamp': 'Fecha de Subida',
                'filename': 'Nombre del Archivo',
                'patients': 'Total Px. Procesados',
                'high_risk_count': 'Px. Riesgo Crítico',
                'usuario': 'Usuario'
            })
            
            st.dataframe(df_history_display, use_container_width=True)


# =================================================================
# 9. ADMIN PANEL (Visión Gerencial)
# =================================================================

if st.session_state.user_role == 'admin':
    st.markdown("---")
    st.markdown("<h2 style='color:#CE1126;'>🛠️ Panel de Administración y Monitoreo</h2>", unsafe_allow_html=True)
    
    tab_dashboard, tab_users = st.tabs(["📊 Dashboard Global", "👥 Gestión de Usuarios"])
    
    with tab_dashboard:
        st.markdown("### Visión General de Uso")
        
        all_file_history = get_global_history_db()
        if not all_file_history:
            st.warning("No hay datos de historial de archivos para mostrar en el dashboard.")
            st.stop()
        
        df_global = pd.DataFrame(all_file_history)
        df_global['timestamp'] = pd.to_datetime(df_global['timestamp'])
        
        # KPIs globales
        col_ad1, col_ad2, col_ad3 = st.columns(3)
        total_files = len(df_global)
        total_patients_processed = df_global['patients'].sum()
        total_critical_risk = df_global['high_risk_count'].sum()
        
        col_ad1.metric("Archivos Procesados", total_files)
        col_ad2.metric("Total Px. Procesados", total_patients_processed)
        col_ad3.metric("Total Px. Riesgo Crítico", total_critical_risk)
        
        st.markdown("---")
        
        # Uso por Doctor (Top 5)
        st.markdown("#### Top 5 Médicos por Cantidad de Pacientes Procesados")
        df_usage = df_global.groupby('usuario')['patients'].sum().sort_values(ascending=False).reset_index().head(5)
        
        chart_usage = alt.Chart(df_usage).mark_bar().encode(
            x=alt.X('patients', title='Pacientes Procesados'),
            y=alt.Y('usuario', sort='-x', title='Médico'),
            tooltip=['usuario', 'patients']
        ).properties(
            title='Uso del Sistema'
        )
        st.altair_chart(chart_usage, use_container_width=True)
        
        st.markdown("---")
        
        # Riesgo Crítico por Doctor
        st.markdown("#### Pacientes en Riesgo Crítico por Médico (Totales)")
        df_risk_summary = df_global.groupby('usuario')['high_risk_count'].sum().sort_values(ascending=False).reset_index()
        
        chart_risk_admin = alt.Chart(df_risk_summary).mark_bar().encode(
            x=alt.X('high_risk_count', title='Px. Riesgo Crítico'),
            y=alt.Y('usuario', sort='-x', title='Médico'),
            color=alt.value('#CE1126'),
            tooltip=['usuario', 'high_risk_count']
        ).properties(
            title='Impacto por Usuario'
        )
        st.altair_chart(chart_risk_admin, use_container_width=True)
        
    with tab_users:
        st.markdown("### Gestión de Cuentas de Usuarios")
        
        # --- 9.1 Crear Nuevo Usuario ---
        with st.expander("➕ Crear Nuevo Usuario Médico", expanded=False):
            with st.form("new_user_form"):
                new_username = st.text_input("Nombre de Usuario (único)", key="new_user_name").lower()
                new_password = st.text_input("Contraseña Temporal", type="password", key="new_user_pwd")
                
                submitted_new_user = st.form_submit_button("Crear Usuario")
                
                if submitted_new_user and new_username and new_password:
                    success, message = create_new_user_db(new_username, new_password, role="doctor")
                    if success:
                        st.success(message)
                        time.sleep(0.1)
                        st.rerun()
                    else:
                        st.error(message)

        st.markdown("---")
        
        # --- 9.2 Lista y Activación/Desactivación ---
        st.markdown("#### Lista de Cuentas Médicas")
        doctors = get_doctors_db()
        df_doctors = pd.DataFrame.from_dict(doctors, orient='index')
        df_doctors.index.name = 'Usuario'
        df_doctors = df_doctors.reset_index()
        
        if not df_doctors.empty:
            # Mostrar tabla con opciones de activación
            st.dataframe(df_doctors[['Usuario', 'id', 'active']], use_container_width=True)
            
            st.markdown("##### Cambiar Estado (Activar/Desactivar)")
            col_u1, col_u2 = st.columns(2)
            
            user_to_update = col_u1.selectbox("Seleccionar Usuario", df_doctors['Usuario'].tolist())
            current_status = doctors[user_to_update]['active']
            
            new_status = col_u2.radio(f"Estado Actual: {'Activo' if current_status else 'Inactivo'}", 
                                       options=[True, False], 
                                       index=0 if current_status else 1, 
                                       format_func=lambda x: "✅ Activo" if x else "❌ Inactivo",
                                       horizontal=True)
            
            if st.button("Actualizar Estado de Usuario", key="update_user_btn"):
                if new_status == current_status:
                    st.info(f"El usuario '{user_to_update}' ya tiene el estado seleccionado.")
                else:
                    db_store.update_user(user_to_update, {'active': new_status})
                    st.success(f"Estado de usuario '{user_to_update}' actualizado a {'ACTIVO' if new_status else 'INACTIVO'}.")
                    time.sleep(0.1)
                    st.rerun()

# --- Fin de la estructura principal ---

# Este es el código final, limpio de caracteres U+00A0.
