import streamlit as st
import pandas as pd
import numpy as np
import time
import joblib 
import json
import os
import io

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="NefroPredict RD", page_icon="🫘", layout="wide")

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
                {"usuario": "dr.perez", "user_id": "dr_perez_uid_001", "timestamp": "2025-05-02 14:30", "filename": "Mis_Pacientes_Q1_2025.xlsx", "patients": 55},
                {"usuario": "dr.gomez", "user_id": "dr_gomez_uid_002", "timestamp": "2025-05-01 11:00", "filename": "Pacientes_HTA.xlsx", "patients": 80},
            ],
            # COLECCIÓN PARA REGISTROS INDIVIDUALES DE PACIENTES - CLAVE CAMBIADA A 'nombre_paciente'
            "patient_records": [
                # Ejemplo 1: Paciente de Alto Riesgo Inicial que ha sido evaluado dos veces
                {"nombre_paciente": "Maria Almonte", "user_id": "dr_perez_uid_001", "usuario": "dr.perez", "timestamp": "2024-10-01 10:00:00", "edad": 60, "creatinina": 1.9, "glucosa_ayunas": 190, "risk": 78.0, "nivel": "MUY ALTO", "color": "#CE1126", "html_report": "<!-- Reporte inicial de Maria Almonte (simulado) -->"},
                {"nombre_paciente": "Maria Almonte", "user_id": "dr_perez_uid_001", "usuario": "dr.perez", "timestamp": "2025-01-15 11:30:00", "edad": 60, "creatinina": 1.5, "glucosa_ayunas": 140, "risk": 55.0, "nivel": "ALTO", "color": "#FFC400", "html_report": "<!-- Reporte intermedio de Maria Almonte (simulado) -->"},
                # Ejemplo 2: Paciente de Bajo Riesgo
                {"nombre_paciente": "Juan Perez", "user_id": "dr_gomez_uid_002", "usuario": "dr.gomez", "timestamp": "2025-05-02 12:00:00", "edad": 45, "creatinina": 1.0, "glucosa_ayunas": 95, "risk": 20.0, "nivel": "MODERADO", "color": "#4CAF50", "html_report": "<!-- Reporte único de Juan Perez (simulado) -->"},
            ]
        }
        
        if not os.path.exists(self.file_path):
            self._write_db(initial_data)
        else:
            db = self._read_db()
            if 'patient_records' not in db:
                db['patient_records'] = []
                self._write_db(db)
            # Limpiar y reescribir si el formato necesita el campo 'nombre_paciente'
            # Esta parte se deja comentada para no resetear la DB si ya se usó,
            # pero se asegura que exista el campo.
            # if len(db['patient_records']) < 1:
            #      db['patient_records'] = initial_data['patient_records']
            #      self._write_db(db)

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

    def get_file_history(self):
        """Obtiene todo el historial de archivos subidos."""
        db = self._read_db()
        return db['file_history']

    def add_file_record(self, record):
        """Añade un nuevo registro de archivo al historial."""
        db = self._read_db()
        db['file_history'].insert(0, record) 
        self._write_db(db)
        
    # FUNCIONES ACTUALIZADAS PARA HISTORIAL DE PACIENTES USANDO NOMBRE
    def add_patient_record(self, record):
        """Añade un nuevo registro individual de paciente."""
        db = self._read_db()
        # Insertar al inicio para que el más reciente aparezca primero
        db['patient_records'].insert(0, record) 
        self._write_db(db)

    def get_patient_records(self, patient_name):
        """Obtiene el historial de predicciones de un paciente por NOMBRE."""
        db = self._read_db()
        # Búsqueda insensible a mayúsculas/minúsculas
        return [
            record for record in db.get('patient_records', []) 
            if record.get('nombre_paciente', '').lower() == patient_name.lower()
        ]

# Inicializamos el DataStore (simulando la conexión a Firestore)
db_store = DataStore(DB_FILE_PATH)

# --- 1. Título y Branding ---
st.markdown("<h1 style='text-align: center; color:#002868;'>🫘 NefroPredict RD 2025</h1>", unsafe_allow_html=True)
st.markdown("<h3 style='text-align: center;'>Detección temprana de enfermedad renal crónica</h3>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color:#CE1126; font-size:1.1em;'>República Dominicana 🇩🇴</p>", unsafe_allow_html=True)

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

nefro_model = load_model('modelo_erc.joblib')
model_loaded = nefro_model is not None


# --- 2. SISTEMA DE AUTENTICACIÓN Y ROLES ---

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_id = None
    st.session_state.user_role = None
    st.session_state.username = None

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
    if st.button("Cerrar Sesión"):
        st.session_state.logged_in = False
        st.session_state.user_id = None
        st.session_state.user_role = None
        st.session_state.username = None
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

def update_user_status_db(username, is_active):
    """Actualiza el estado 'active' de un usuario en la DB (DataStore)."""
    # Función dummy para el ejemplo, pero debe ser implementada
    return True 

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
    data = data_series[['edad', 'imc', 'presion_sistolica', 'glucosa_ayunas', 'creatinina']].to_frame().T
    
    if model_loaded:
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

    # Lógica de Contribución:
    if creatinina > 2.0: contributions['Creatinina'] = 0.40
    elif creatinina > 1.3: contributions['Creatinina'] = 0.25
    else: contributions['Creatinina'] = -0.10
    
    if glucosa > 125: contributions['Glucosa Ayunas'] = 0.20
    elif glucosa > 100: contributions['Glucosa Ayunas'] = 0.05
    else: contributions['Glucosa Ayunas'] = -0.05

    if presion > 140: contributions['Presión Sistólica'] = 0.15
    elif presion > 130: contributions['Presión Sistólica'] = 0.05
    else: contributions['Presión Sistólica'] = -0.05
        
    if edad > 65: contributions['Edad'] = 0.10
    else: contributions['Edad'] = -0.03

    if imc > 30.0: contributions['IMC (Obesidad)'] = 0.08
    elif imc < 18.5: contributions['IMC (Bajo Peso)'] = 0.03
    else: contributions['IMC'] = -0.02

    total_abs = sum(abs(v) for v in contributions.values())
    if total_abs > 0:
        contributions = {k: v / total_abs for k, v in contributions.items()}

    return contributions

def display_explanation_charts(data):
    """Muestra los datos de contribución como un gráfico de barras horizontal (interactivo)."""
    
    df_chart = pd.DataFrame(data.items(), columns=['Factor', 'Contribucion_Normalizada'])
    df_chart['Riesgo_Impacto'] = np.where(df_chart['Contribucion_Normalizada'] > 0, 'Aumenta Riesgo', 'Disminuye Riesgo')

    st.markdown("#### 📈 Contribución Individual de Factores")
    st.bar_chart(df_chart, x='Factor', y='Contribucion_Normalizada', color='Riesgo_Impacto', use_container_width=True)
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

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Reporte NefroPredict - {patient_data['nombre_paciente']}</title>
        <style>
            @media print {{
                body {{ font-family: 'Times New Roman', Times, serif; color: #333; margin: 0; padding: 0; }}
                h1, h2, h3 {{ margin-top: 0; }}
                .report-container {{ width: 210mm; margin: 0 auto; padding: 20mm; }}
                .header {{ text-align: center; border-bottom: 2px solid #002868; padding-bottom: 10px; margin-bottom: 20px; }}
                .doctor-info {{ text-align: right; font-size: 0.9em; }}
                .risk-box {{ 
                    padding: 15px; 
                    margin-top: 10px; 
                    border: 2px solid {color}; 
                    background-color: {color}20;
                    text-align: center;
                }}
                .risk-level {{ font-size: 2.5em; font-weight: bold; color: {color}; }}
                .data-table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
                .data-table th, .data-table td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                .data-table th {{ background-color: #f2f2f2; }}
                .recommendation {{ margin-top: 30px; padding: 15px; border-left: 5px solid {color}; background-color: #f0f0f0; }}
                .explanation-table {{ width: 50%; border-collapse: collapse; margin-top: 10px; float: right;}}
                .explanation-table th, .explanation-table td {{ padding: 5px; text-align: left; border: none; border-bottom: 1px dotted #ccc;}}
            }}
            /* Estilos para visualización en Streamlit */
            .printable-report {{ border: 1px solid #ccc; padding: 20px; border-radius: 8px; background-color: white; }}
        </style>
    </head>
    <body>
        <div class="report-container printable-report">
            <div class="header">
                <h1 style="color:#002868;">NefroPredict RD</h1>
                <h3>Reporte de Riesgo de Enfermedad Renal Crónica</h3>
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
                <tr><th>Factor</th><th>Impacto</th></tr>
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


# --- 6. FUNCIÓN DE LA PLANTILLA EXCEL (Fix de Motor) ---

def get_excel_template():
    """Genera la plantilla Excel recomendada para la carga masiva."""
    data = {
        'id_paciente': ['P-1001', 'P-1002', 'P-1003'], # Aquí mantenemos ID para la carga masiva de anonimización
        'edad': [65, 48, 72],
        'imc': [32.5, 24.1, 28.9],
        'presion_sistolica': [150, 125, 140],
        'glucosa_ayunas': [180, 95, 115],
        'creatinina': [1.8, 0.9, 1.5],
    }
    df_template = pd.DataFrame(data)
    
    # FIX: Cambiando el motor a 'openpyxl' para evitar ModuleNotFoundError
    output = io.BytesIO()
    writer = pd.ExcelWriter(output, engine='openpyxl') 
    df_template.to_excel(writer, index=False, sheet_name='Plantilla_ERC')
    writer.close()
    processed_data = output.getvalue()
    return processed_data


# --- 7. Interfaz del Médico (Estructura de pestañas) ---
if st.session_state.user_role == 'doctor' or st.session_state.user_role == 'admin':
    
    st.subheader("Selección de Modo de Evaluación")
    
    tab_individual, tab_masiva, tab_patient_history, tab_historial = st.tabs(["🩺 Predicción Individual", "📁 Carga Masiva (Excel)", "📂 Historial Clínico", "⏱️ Mi Historial"])

    # =================================================================
    # 7.1 PESTAÑA DE PREDICCIÓN INDIVIDUAL
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
                    'nombre_paciente': nombre_paciente, # CAMBIADO
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

        if 'last_individual_report' in st.session_state:
            report_data = st.session_state.last_individual_report
            patient_name = report_data['data']['nombre_paciente']
            risk_percentage = report_data['risk']
            nivel, color, _ = get_risk_level(risk_percentage)
            
            st.markdown("---")
            st.markdown("### 3. Resultados y Reporte Instantáneo")
            
            col_res_risk, col_res_level = st.columns([2, 2])
            
            with col_res_risk:
                st.markdown(f"<div style='background-color: {color}; color: white; padding: 20px; border-radius: 8px; text-align: center;'><h2>RIESGO DE ERC</h2><h1 style='font-size: 3em;'>{risk_percentage:.1f}%</h1></div>", unsafe_allow_html=True)
            
            with col_res_level:
                st.markdown(f"<div style='border: 2px solid {color}; padding: 20px; border-radius: 8px; height: 100%;'><h3>Nivel de Riesgo Actual</h3><h2 style='color: {color};'>{nivel}</h2></div>", unsafe_allow_html=True)

            st.markdown("---")
            
            display_explanation_charts(report_data['explanation'])
            
            st.markdown("---")
            
            st.markdown("### 4. Generar Documento Imprimible (PDF)")
            st.warning("Pulsa el botón, y luego usa la opción 'Imprimir' y selecciona 'Guardar como PDF' en tu navegador.")
            
            st.components.v1.html(
                f"""
                <button onclick="window.printReport()" style="background-color: #002868; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; font-size: 1.1em;">
                    Imprimir / Guardar Reporte PDF (Dr. {st.session_state.username.upper()})
                </button>
                <div style="height: 10px;"></div>
                """,
                height=50,
            )
            st.components.v1.html(report_data['html_report'], height=700, scrolling=True)


    # =================================================================
    # 7.2 PESTAÑA DE CARGA MASIVA (EXCEL)
    # =================================================================
    with tab_masiva:
        st.markdown("#### Carga de Archivo Excel para Lotes de Pacientes")

        col_upload, col_template = st.columns([3, 1])

        uploaded = None
        if 'last_mass_df' in st.session_state:
            df = st.session_state.last_mass_df
            st.success(f"Mostrando resultados del último archivo cargado: {st.session_state.last_mass_filename} ({len(df)} pacientes)")
            
        else:
            with col_upload:
                uploaded = st.file_uploader("📁 Sube tu archivo Excel de pacientes", type=["xlsx", "xls"], key="mass_upload_file")
        
        with col_template:
            excel_data = get_excel_template()
            st.download_button(
                label="⬇️ Descargar Plantilla",
                data=excel_data,
                file_name="NefroPredict_Plantilla_Vaciado.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                help="Utiliza esta plantilla para asegurar el formato de columna correcto."
            )
            
        if uploaded:
            try:
                df = pd.read_excel(uploaded)
                st.success(f"¡Cargados {len(df)} pacientes correctamente!")

                required_cols = ['edad', 'imc', 'presion_sistolica', 'glucosa_ayunas', 'creatinina']
                missing_cols = [col for col in required_cols if col not in df.columns]

                if missing_cols:
                     st.error(f"⚠️ Error: Faltan las siguientes columnas requeridas en tu Excel: {', '.join(missing_cols)}. Por favor, revisa el formato.")
                     st.stop()
                
                df['Riesgo_ERC_5años_%'] = df.apply(lambda row: predict_risk(row), axis=1)

                now = time.strftime("%Y-%m-%d %H:%M:%S")
                record = {
                    "usuario": st.session_state.username,
                    "user_id": st.session_state.user_id,
                    "timestamp": now,
                    "filename": uploaded.name,
                    "patients": len(df)
                }
                db_store.add_file_record(record)
                
                st.session_state.last_mass_df = df
                st.session_state.last_mass_filename = uploaded.name
                
                st.rerun()

            except Exception as e:
                st.error(f"Ocurrió un error al procesar el archivo: {e}")
        
        # Lógica de Visualización y Resultados Masivos
        if 'last_mass_df' in st.session_state:
            df = st.session_state.last_mass_df
            st.subheader("2. Resultados Predictivos y Clasificación")

            total_alto_riesgo = len(df[df['Riesgo_ERC_5años_%'] > 70])
            total_pacientes = len(df)
            
            col_res1, col_res2, col_res3 = st.columns(3)

            col_res1.metric("Total Pacientes Evaluados", total_pacientes)
            col_res2.metric("Pacientes con Riesgo MUY ALTO", total_alto_riesgo, f"{((total_alto_riesgo/total_pacientes)*100):.1f}% de la muestra")
            col_res3.metric("Riesgo Promedio de la Cohorte", f"{df['Riesgo_ERC_5años_%'].mean():.1f}%")

            st.markdown("---")
            
            # Histograma de Distribución de Riesgo
            st.markdown("#### 📊 Distribución de Riesgo de ERC en la Muestra")
            
            df['Rango_Riesgo'] = pd.cut(
                df['Riesgo_ERC_5años_%'], 
                bins=[0, 40, 70, 100], 
                labels=['MODERADO (0-40%)', 'ALTO (41-70%)', 'MUY ALTO (71-100%)'], 
                right=True
            )
            
            risk_counts = df['Rango_Riesgo'].value_counts().reset_index()
            risk_counts.columns = ['Rango', 'Pacientes']
            
            color_map = {
                'MODERADO (0-40%)': '#4CAF50', 
                'ALTO (41-70%)': '#FFC400', 
                'MUY ALTO (71-100%)': '#CE1126'
            }
            
            # Ordenar las categorías para el gráfico
            order = {'MODERADO (0-40%)': 0, 'ALTO (41-70%)': 1, 'MUY ALTO (71-100%)': 2}
            risk_counts['Order'] = risk_counts['Rango'].map(order)
            risk_counts = risk_counts.sort_values('Order')
            
            st.bar_chart(risk_counts, x='Rango', y='Pacientes', color='Rango', use_container_width=True)
            st.markdown("<p style='font-size: 0.8em; text-align: center; color: #888;'>Visualización de la distribución de pacientes en rangos de riesgo.</p>", unsafe_allow_html=True)

            st.markdown("---")
            
            st.markdown("#### Vista Previa de Riesgos Calculados (Top 50)")
            df_display = df.sort_values(by='Riesgo_ERC_5años_%', ascending=False).head(50)
            df_display['Recomendacion'] = df_display['Riesgo_ERC_5años_%'].apply(lambda x: get_risk_level(x)[0])
            st.dataframe(df_display[['id_paciente', 'Riesgo_ERC_5años_%', 'Recomendacion', 'creatinina', 'glucosa_ayunas', 'edad']], 
                            use_container_width=True, hide_index=True)

            st.markdown("---")

            st.subheader("3. Exportar Datos Masivos")
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Descargar todos los resultados (CSV)",
                data=csv,
                file_name="NefroPredict_resultados_masivos.csv",
                mime="text/csv",
                help="Incluye todas las variables originales más la columna de predicción de riesgo."
            )

        elif not uploaded:
            st.info("Sube tu archivo Excel para comenzar la evaluación de riesgo de ERC.")
            if not model_loaded:
                st.warning("🚨 ADVERTENCIA: La aplicación está en modo **SIMULACIÓN** (el modelo real no se pudo cargar).")
    
    # =================================================================
    # 7.3 PESTAÑA DE HISTORIAL CLÍNICO (NUEVA)
    # =================================================================
    with tab_patient_history:
        st.markdown("#### 🔍 Búsqueda de Historial Clínico por Paciente")
        st.info("Busca el historial de predicciones guardado para dar seguimiento a un paciente específico.")
        
        # CAMBIADO: Input de búsqueda por nombre
        patient_search_name = st.text_input("Ingresa el Nombre Completo del Paciente a buscar (Ej: Maria Almonte)", key="search_patient_name")
        
        if patient_search_name:
            # Búsqueda por nombre
            records = db_store.get_patient_records(patient_search_name)
            
            if records:
                st.success(f"Historial encontrado para el paciente: **{patient_search_name}** ({len(records)} evaluaciones)")
                
                # Conversión a DataFrame y orden cronológico
                history_df = pd.DataFrame(records)
                history_df['timestamp'] = pd.to_datetime(history_df['timestamp'])
                history_df = history_df.sort_values(by='timestamp')
                
                # --- ANÁLISIS LONGITUDINAL ---
                st.markdown("---")
                st.markdown("#### 💡 Resumen de Tendencia de Riesgo")
                
                current_risk = history_df.iloc[-1]['risk']
                initial_risk = history_df.iloc[0]['risk']
                risk_change = current_risk - initial_risk
                
                status_color = "#3498db" # Azul por defecto
                
                if risk_change < -10:
                    status = "Mejoría Significativa"
                    description = f"El riesgo ha **disminuido** significativamente en {abs(risk_change):.1f} puntos porcentuales (de {initial_risk:.1f}% a {current_risk:.1f}%). La intervención está funcionando."
                    status_color = "#27ae60" # Verde
                elif risk_change < 0:
                    status = "Riesgo en Mejoría"
                    description = f"El riesgo ha **disminuido** en {abs(risk_change):.1f} puntos porcentuales. Continuar con el seguimiento actual."
                    status_color = "#2ecc71" # Verde claro
                elif risk_change > 10:
                    status = "Riesgo Progresivo (Alarma)"
                    description = f"El riesgo ha **aumentado** significativamente en {risk_change:.1f} puntos porcentuales (de {initial_risk:.1f}% a {current_risk:.1f}%). Requiere revisión inmediata del plan de tratamiento."
                    status_color = "#e74c3c" # Rojo
                elif risk_change > 0:
                    status = "Riesgo en Aumento Leve"
                    description = f"El riesgo ha **aumentado** ligeramente en {risk_change:.1f} puntos porcentuales. Monitorear los biomarcadores en la próxima consulta."
                    status_color = "#f39c12" # Naranja
                else:
                    status = "Riesgo Estable"
                    description = f"El riesgo se ha mantenido **estable** ({initial_risk:.1f}% vs {current_risk:.1f}%). Mantener la vigilancia."
                    status_color = "#3498db" # Azul
                    
                st.markdown(f"""
                    <div style='border-left: 5px solid {status_color}; padding: 10px; background-color: #f7f7f7; border-radius: 4px;'>
                        <h4 style='color: {status_color}; margin-top: 0;'>Estado Actual: {status}</h4>
                        <p>{description}</p>
                    </div>
                """, unsafe_allow_html=True)
                
                st.markdown("---")
                st.markdown("#### 📉 Tendencia Histórica del Riesgo de ERC")
                
                st.line_chart(history_df, x='timestamp', y='risk', color='#002868', use_container_width=True)
                
                st.markdown("---")
                st.markdown("#### 📋 Evaluaciones Anteriores (Archivos Guardados)")
                
                # Iterar sobre los registros y mostrar los detalles y el reporte
                for i, row in history_df.iloc[::-1].iterrows(): # Iterar en orden inverso (más reciente primero)
                    timestamp = row['timestamp'].strftime("%Y-%m-%d %H:%M:%S")
                    
                    with st.expander(f"Evaluación del {timestamp} | Riesgo: {row['risk']:.1f}% ({row['nivel']})"):
                        st.markdown(f"**Evaluado por:** Dr./Dra. {row['usuario']}")
                        
                        col_details, col_biomarkers = st.columns(2)
                        with col_details:
                            st.metric("Nivel de Riesgo", row['nivel'], delta=f"{row['risk']:.1f}%")
                        with col_biomarkers:
                            st.metric("Creatinina (mg/dL)", row['creatinina'])
                            st.metric("Glucosa Ayunas (mg/dL)", row['glucosa_ayunas'])
                        
                        st.markdown("---")
                        st.subheader("Reporte PDF Simulado (Detalle y Diferencias)")
                        st.warning("Utiliza la opción 'Imprimir' y selecciona 'Guardar como PDF' para obtener el documento.")

                        # Mostrar el reporte HTML guardado
                        st.components.v1.html(row['html_report'], height=500, scrolling=True)
                
            else:
                st.warning(f"No se encontraron registros de predicciones guardadas para el paciente: **{patient_search_name}**. Realiza una predicción individual para guardar el primer registro.")


    # =================================================================
    # 7.4 PESTAÑA DE MI HISTORIAL
    # =================================================================
    with tab_historial:
        st.markdown("#### Archivos Subidos por Ti")
        st.info(f"Aquí puedes ver el historial de los archivos subidos por el usuario: **{st.session_state.username}**")

        global_history = db_store.get_file_history()
        current_user_history = [
            record for record in global_history 
            if record.get('user_id') == st.session_state.user_id
        ]

        if current_user_history:
            history_df = pd.DataFrame(current_user_history)
            st.dataframe(history_df[['timestamp', 'filename', 'patients']], use_container_width=True, hide_index=True)
            st.caption("Esta información es persistente.")
        else:
            st.info("No has subido ningún archivo aún.")

# --- 8. PANEL DE ADMINISTRACIÓN (SOLO PARA ADMIN - Restaurado) ---
if st.session_state.user_role == 'admin':
    st.markdown("---")
    st.markdown("<h2 style='color:#CE1126;'>⚙️ Panel de Administración y Gestión</h2>", unsafe_allow_html=True)
    
    tab_dashboard, tab_users, tab_files = st.tabs(["Dashboard de Uso", "Gestión de Médicos", "Historial Global"])

    # --- TAB 1: DASHBOARD DE USO (KPIs) ---
    with tab_dashboard:
        st.markdown("#### 📊 Dashboard de Uso (KPIs)")
        
        df_history = pd.DataFrame(get_global_history_db())
        
        if not df_history.empty:
            
            total_files = len(df_history)
            total_patients_evaluated = df_history['patients'].sum()
            
            col_kpi1, col_kpi2, col_kpi3 = st.columns(3)
            
            col_kpi1.metric("Total Histórico de Pacientes Evaluados (Lote)", f"{total_patients_evaluated:,}")
            col_kpi2.metric("Archivos Totales Procesados", total_files)
            
            all_doctors = get_doctors_db()
            active_doctors = sum(1 for d in all_doctors.values() if d.get('active', True))
            inactive_doctors = len(all_doctors) - active_doctors
            col_kpi3.metric("Médicos Activos", active_doctors)
            
            st.markdown("---")
            st.markdown("#### 📈 Top 5 Médicos por Uso (Pacientes Evaluados)")
            
            usage_by_doctor = df_history.groupby('usuario')['patients'].sum().sort_values(ascending=False).head(5)
            st.bar_chart(usage_by_doctor, color="#002868")
        else:
            st.info("No hay datos históricos para mostrar métricas.")


    # --- TAB 2: GESTIÓN DE MÉDICOS ---
    with tab_users:
        col_add, col_list = st.columns(2)
        
        with col_add:
            st.markdown("#### ➕ Crear Nuevo Médico")
            st.info("Nota: Los usuarios creados aquí serán persistentes.")
            
            new_user = st.text_input("Nombre de Usuario del Nuevo Médico", key="new_user_input").lower()
            new_pwd = st.text_input("Contraseña Temporal", type="password", key="new_pwd_input")
            if st.button("Crear Médico y Acceso", key="btn_create_user"):
                if new_user and new_pwd:
                    success, message = create_new_user_db(new_user, new_pwd, role="doctor")
                    if success:
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)
                else:
                    st.warning("Debes llenar ambos campos.")
                    
        with col_list:
            st.markdown("#### 📋 Listado de Médicos")
            doctors = get_doctors_db()
            
            if doctors:
                doctor_list = [{"Usuario": user, "ID de Sistema": details['id'], "Estado": "✅ Activo" if details.get('active', True) else "🚫 Inactivo"} for user, details in doctors.items()]
                st.dataframe(pd.DataFrame(doctor_list), use_container_width=True, hide_index=True)
                st.caption(f"Total de Médicos: {len(doctors)}")
            else:
                st.info("Aún no hay médicos registrados.")

            st.markdown("---")
            st.markdown("#### 🚫 Suspender/Activar Cuentas")
            
            if doctors:
                doctor_names = sorted([k for k, v in doctors.items() if v['role'] == 'doctor'])
                
                user_to_manage = st.selectbox("Selecciona un Médico para Gestionar", doctor_names, key="user_to_manage")
                
                selected_doctor_data = db_store.get_user(user_to_manage)
                current_status_bool = selected_doctor_data.get('active', True)
                
                default_index = 0 if current_status_bool else 1 
                
                new_status = st.radio(
                    "Estado de la Cuenta", 
                    ["Activo", "Inactivo"], 
                    index=default_index,
                    key="status_radio"
                )
                
                if st.button("Aplicar Cambio de Estado", key="btn_update_status"):
                    is_active = (new_status == "Activo")
                    # Lógica de actualización (simulada)
                    if db_store.update_user(user_to_manage, {'active': is_active}):
                        st.success(f"Estado de '{user_to_manage}' actualizado a: {new_status}")
                        st.rerun()
                    else:
                        st.error("Error al actualizar el estado del usuario.")
            else:
                st.info("No hay médicos para gestionar.")


    # --- TAB 3: HISTORIAL GLOBAL DE ARCHIVOS ---
    with tab_files:
        st.markdown("#### 📁 Archivos Subidos por Todos los Médicos")
        st.info("Vista global de auditoría de uso de la plataforma. (Simula la 'Colección Pública').")
        
        all_history_df = pd.DataFrame(get_global_history_db())
        
        if not all_history_df.empty:
            cols = ['usuario', 'timestamp', 'filename', 'patients']
            display_df = all_history_df[cols].sort_values(by='timestamp', ascending=False)
            st.dataframe(display_df, use_container_width=True, hide_index=True)
        else:
            st.info("Aún no hay ningún archivo subido por ningún usuario.")
    
    st.markdown("---")
# --- FIN PANEL DE ADMINISTRACIÓN ---


# --- 9. Footer ---
st.markdown("---")
st.markdown("<p style='text-align: center; color:#002868; font-weight:bold;'>© 2025 NefroPredict RD - Soluciones de salud impulsadas por IA</p>", unsafe_allow_html=True)
