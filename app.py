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
        """Crea el archivo DB con datos iniciales si no existe."""
        if not os.path.exists(self.file_path):
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
                    {"usuario": "dr.gomez", "user_id": "dr_gomez_uid_002", "timestamp": "2025-05-01 16:00", "filename": "Revision_Mensual.xlsx", "patients": 20},
                ]
            }
            self._write_db(initial_data)

    def _read_db(self):
        """Lee todos los datos del archivo DB."""
        if not os.path.exists(self.file_path):
            self._initialize_db()
        try:
            with open(self.file_path, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
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

    def update_user(self, username, updates):
        """Actualiza campos de un usuario (ej: 'active')."""
        db = self._read_db()
        if username in db['users']:
            db['users'][username].update(updates)
            self._write_db(db)
            return True
        return False

    def get_file_history(self):
        """Obtiene todo el historial de archivos subidos."""
        db = self._read_db()
        return db['file_history']

    def add_file_record(self, record):
        """Añade un nuevo registro de archivo al historial."""
        db = self._read_db()
        db['file_history'].insert(0, record) 
        self._write_db(db)

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
        
        st.sidebar.caption("Usuarios de prueba: `admin`/`admin` | `dr.perez`/`pass1` | `dr.sanchez`/`pass3` (Inactivo)")
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
    user_data = db_store.get_user(username)
    if user_data and user_data['role'] == 'doctor':
        return db_store.update_user(username, {'active': is_active})
    return False

def get_doctors_db():
    """Obtiene la lista de todos los médicos (no admin) de la DB."""
    all_users = db_store.get_all_users()
    return {k: v for k, v in all_users.items() if v['role'] == 'doctor'}

def get_global_history_db():
    """Obtiene todo el historial de archivos de la DB."""
    return db_store.get_file_history()


# --- 4. FUNCIONES DE PREDICCIÓN Y EXPLICACIÓN ---

def predict_risk(data_series):
    """Realiza la predicción de riesgo (real o simulada) a partir de una Serie de Pandas."""
    data = data_series[['edad', 'imc', 'presion_sistolica', 'glucosa_ayunas', 'creatinina']].to_frame().T
    
    if model_loaded:
        prediction_proba = nefro_model.predict_proba(data)[:, 1][0]
        return (prediction_proba * 100).round(1)
    else:
        # Simulación de riesgo
        base_risk = 30.0 
        adjustment = (data['creatinina'].iloc[0] * 10) + \
                     (data['glucosa_ayunas'].iloc[0] * 0.1) + \
                     (data['edad'].iloc[0] * 0.3)
        
        simulated_risk = base_risk + adjustment
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
    # Streamlit usa Altair, que maneja la interacción
    st.bar_chart(df_chart, x='Factor', y='Contribucion_Normalizada', color='Riesgo_Impacto', use_container_width=True)
    st.markdown("<p style='font-size: 0.8em; text-align: center; color: #888;'>Las barras rojas representan un factor que aumenta el riesgo. Las barras verdes lo disminuyen.</p>", unsafe_allow_html=True)


# --- 5. FUNCIÓN DE REPORTE INDIVIDUAL PERSONALIZADO (PDF SIMULADO) ---

def get_risk_level(risk):
    if risk > 70:
        return "MUY ALTO", "#CE1126", "Referir URGENTE a nefrólogo. Se requiere intervención intensiva y seguimiento inmediato."
    elif risk > 40:
        return "ALTO", "#FFC400", "Control estricto cada 3 meses. Monitorear biomarcadores y ajustar terapia farmacológica."
    else:
        return "MODERADO", "#4CAF50", "Control anual o bianual. Reafirmar hábitos de vida saludables y control de presión arterial."

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
        <title>Reporte NefroPredict - {patient_data['id_paciente']}</title>
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
                <p><strong>ID del Paciente:</strong> {patient_data['id_paciente']}</p>
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
        'id_paciente': ['P-1001', 'P-1002', 'P-1003'],
        'edad': [65, 48, 72],
        'imc': [32.5, 24.1, 28.9],
        'presion_sistolica': [150, 125, 140],
        'glucosa_ayunas': [180, 95, 115],
        'creatinina': [1.8, 0.9, 1.5],
    }
    df_template = pd.DataFrame(data)
    
    # FIX: Cambiando el motor a 'openpyxl' para evitar ModuleNotFoundError
    output = io.BytesIO()
    # Usamos openpyxl, que es más común en entornos Streamlit que xlsxwriter
    writer = pd.ExcelWriter(output, engine='openpyxl') 
    df_template.to_excel(writer, index=False, sheet_name='Plantilla_ERC')
    writer.close()
    processed_data = output.getvalue()
    return processed_data


# --- 7. Interfaz del Médico (Estructura de pestañas) ---
if st.session_state.user_role == 'doctor' or st.session_state.user_role == 'admin':
    
    st.subheader("Selección de Modo de Evaluación")
    
    tab_individual, tab_masiva, tab_historial = st.tabs(["🩺 Predicción Individual", "📁 Carga Masiva (Excel)", "⏱️ Mi Historial"])

    # =================================================================
    # 7.1 PESTAÑA DE PREDICCIÓN INDIVIDUAL
    # =================================================================
    with tab_individual:
        st.markdown("#### Ingreso de Datos de un Único Paciente")
        st.info("Ingresa los 5 biomarcadores clave para obtener un riesgo instantáneo y un reporte descargable.")
        
        with st.form("individual_patient_form"):
            col_id, col_edad = st.columns(2)
            with col_id:
                id_paciente = st.text_input("ID del Paciente / Nombre", value="Paciente_Nuevo_001", key="input_id")
            with col_edad:
                edad = st.number_input("Edad (años)", min_value=1, max_value=120, value=55, key="input_edad")

            col_1, col_2 = st.columns(2)
            with col_1:
                imc = st.number_input("IMC (kg/m²)", min_value=10.0, max_value=60.0, value=25.0, step=0.1, key="input_imc", help="Índice de Masa Corporal")
                glucosa_ayunas = st.number_input("Glucosa en Ayunas (mg/dL)", min_value=50, max_value=500, value=90, key="input_glucosa")
            with col_2:
                presion_sistolica = st.number_input("Presión Sistólica (mmHg)", min_value=80, max_value=250, value=120, key="input_presion")
                creatinina = st.number_input("Creatinina (mg/dL)", min_value=0.1, max_value=10.0, value=1.0, step=0.01, format="%.2f", key="input_creatinina")
            
            submitted = st.form_submit_button("Calcular Riesgo y Generar Reporte")
            
            if submitted:
                patient_data = pd.Series({
                    'id_paciente': id_paciente,
                    'edad': edad,
                    'imc': imc,
                    'presion_sistolica': presion_sistolica,
                    'glucosa_ayunas': glucosa_ayunas,
                    'creatinina': creatinina
                })
                
                risk_percentage = predict_risk(patient_data)
                explanation_data = generate_explanation_data(patient_data)

                st.session_state.last_individual_report = {
                    'data': patient_data.to_dict(),
                    'risk': risk_percentage,
                    'explanation': explanation_data,
                }
                st.success(f"Cálculo completado para {id_paciente}.")
                st.rerun() 

        if 'last_individual_report' in st.session_state:
            report_data = st.session_state.last_individual_report
            risk_percentage = report_data['risk']
            nivel, color, _ = get_risk_level(risk_percentage)
            
            st.markdown("---")
            st.markdown("### 3. Resultados y Reporte Instantáneo")
            
            col_res_risk, col_res_level = st.columns(2)
            
            with col_res_risk:
                st.markdown(f"<div style='background-color: {color}; color: white; padding: 20px; border-radius: 8px; text-align: center;'><h2>RIESGO DE ERC</h2><h1 style='font-size: 3em;'>{risk_percentage:.1f}%</h1></div>", unsafe_allow_html=True)
            
            with col_res_level:
                st.markdown(f"<div style='border: 2px solid {color}; padding: 20px; border-radius: 8px; height: 100%;'><h3>Nivel de Riesgo</h3><h2 style='color: {color};'>{nivel}</h2></div>", unsafe_allow_html=True)

            st.markdown("---")
            
            display_explanation_charts(report_data['explanation'])
            
            st.markdown("---")
            
            st.markdown("### 4. Generar Documento Imprimible (PDF)")
            st.warning("Pulsa el botón, y luego usa la opción 'Imprimir' y selecciona 'Guardar como PDF' en tu navegador.")
            
            html_report = generate_individual_report_html(
                report_data['data'], 
                risk_percentage, 
                st.session_state.username, 
                report_data['explanation']
            )

            st.components.v1.html(
                f"""
                <button onclick="window.printReport()" style="background-color: #002868; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; font-size: 1.1em;">
                    Imprimir / Guardar Reporte PDF (Dr. {st.session_state.username.upper()})
                </button>
                {html_report}
                """,
                height=50,
            )


    # =================================================================
    # 7.2 PESTAÑA DE CARGA MASIVA (EXCEL)
    # =================================================================
    with tab_masiva:
        st.markdown("#### Carga de Archivo Excel para Lotes de Pacientes")

        col_upload, col_template = st.columns([3, 1])

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

                st.subheader("2. Resultados Predictivos y Clasificación")

                total_alto_riesgo = len(df[df['Riesgo_ERC_5años_%'] > 70])
                total_pacientes = len(df)
                
                col_res1, col_res2 = st.columns(2)

                col_res1.metric("Total Pacientes Evaluados", total_pacientes)
                col_res2.metric("Pacientes con Riesgo MUY ALTO", total_alto_riesgo, f"{((total_alto_riesgo/total_pacientes)*100):.1f}% de la muestra")

                st.markdown("---")
                
                st.markdown("#### Vista Previa de Riesgos Calculados (Top 50)")
                df_display = df.sort_values(by='Riesgo_ERC_5años_%', ascending=False).head(50)
                df_display['Recomendacion'] = df_display['Riesgo_ERC_5años_%'].apply(lambda x: get_risk_level(x)[0])
                st.dataframe(df_display[['id_paciente', 'Riesgo_ERC_5años_%', 'Recomendacion', 'creatinina', 'glucosa_ayunas']], 
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

            except Exception as e:
                st.error(f"Ocurrió un error al procesar el archivo: {e}")
        else:
            st.info("Sube tu archivo Excel para comenzar la evaluación de riesgo de ERC.")
            if not model_loaded:
                st.warning("🚨 ADVERTENCIA: La aplicación está en modo **SIMULACIÓN** (el modelo real no se pudo cargar).")


    # =================================================================
    # 7.3 PESTAÑA DE MI HISTORIAL
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
            
            col_kpi1.metric("Total Histórico de Pacientes Evaluados", f"{total_patients_evaluated:,}")
            col_kpi2.metric("Archivos Totales Procesados", total_files)
            
            all_doctors = get_doctors_db()
            active_doctors = sum(1 for d in all_doctors.values() if d.get('active', True))
            inactive_doctors = len(all_doctors) - active_doctors
            col_kpi3.metric("Médicos Activos", active_doctors, delta=-inactive_doctors, delta_color="inverse")
            
            st.markdown("---")
            st.markdown("#### 📈 Top 5 Médicos por Uso (Pacientes Evaluados)")
            
            usage_by_doctor = df_history.groupby('usuario')['patients'].sum().sort_values(ascending=False).head(5)
            st.bar_chart(usage_by_doctor, color="#002868") # Azul RD
        else:
            st.info("No hay datos históricos para mostrar métricas.")


    # --- TAB 2: GESTIÓN DE MÉDICOS ---
    with tab_users:
        col_add, col_list = st.columns(2)
        
        with col_add:
            st.markdown("#### ➕ Crear Nuevo Médico")
            st.info("Nota: Los usuarios creados aquí serán persistentes.")
            
            # Formulario para añadir médico
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
            
            # Lógica para suspender/activar
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
                    if update_user_status_db(user_to_manage, is_active):
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
