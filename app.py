import streamlit as st
import pandas as pd
import numpy as np
import time
import joblib 
import json
import os

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="NefroPredict RD", page_icon="🫘", layout="wide")

# --- 0. CLASE DE PERSISTENCIA SIMULADA (REEMPLAZO DE FIRESTORE) ---
# Esta clase simula la conexión y las operaciones CRUD de Firestore.
# Usamos un archivo JSON local para que los datos persistan entre interacciones de Streamlit.

DB_FILE_PATH = "nefro_db.json"

class DataStore:
    def __init__(self, file_path):
        self.file_path = file_path
        self._initialize_db()

    def _initialize_db(self):
        """Crea el archivo DB con datos iniciales si no existe."""
        if not os.path.exists(self.file_path):
            initial_data = {
                # Datos de usuarios (simulando una colección 'doctors' o 'users')
                "users": {
                    "admin": {"pwd": "admin", "role": "admin", "id": "admin_nefro", "active": True},
                    "dr.perez": {"pwd": "pass1", "role": "doctor", "id": "dr_perez_uid_001", "active": True},
                    "dr.gomez": {"pwd": "pass2", "role": "doctor", "id": "dr_gomez_uid_002", "active": True},
                    "dr.sanchez": {"pwd": "pass3", "role": "doctor", "id": "dr_sanchez_uid_003", "active": False},
                },
                # Historial de archivos subidos (simulando una colección 'file_history' pública)
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
        db['file_history'].insert(0, record) # Insertar al inicio para que el más reciente salga primero
        self._write_db(db)

# Inicializamos el DataStore (simulando la conexión a Firestore)
db_store = DataStore(DB_FILE_PATH)

# --- 1. CONFIGURACIÓN DEL ENTORNO (Globales de Firebase) ---
# Aunque no usamos el SDK de Firebase en Python, estos placeholders simulan
# las variables que el entorno Canvas proveería si se usara el SDK JS.

# const appId = typeof __app_id !== 'undefined' ? __app_id : 'default-app-id';
# const firebaseConfig = JSON.parse(__firebase_config);
# const auth = getAuth(db);
# if (typeof __initial_auth_token !== 'undefined') { await signInWithCustomToken(auth, __initial_auth_token); } else { await signInAnonymously(auth); }

# st.info("Estructura lista para Firebase. Actualmente usando persistencia local (nefro_db.json).")


# --- 2. Título y Branding ---
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


# --- 3. SISTEMA DE AUTENTICACIÓN Y ROLES (Ahora usa DataStore) ---

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_id = None
    st.session_state.user_role = None
    st.session_state.username = None

def check_login():
    """Maneja el flujo de login usando DataStore (simulación Firestore)."""
    if not st.session_state.logged_in:
        st.markdown("### 🔐 Acceso de Usuario")
        
        with st.form("login_form"):
            user = st.text_input("Nombre de Usuario (ej: admin, dr.perez)", key="user_input").lower()
            pwd = st.text_input("Contraseña", type="password", key="password_input")
            
            submitted = st.form_submit_button("Ingresar")

            if submitted:
                # 1. Buscar usuario en DataStore
                user_data = db_store.get_user(user)

                if user_data and user_data['pwd'] == pwd:
                    
                    # 2. Verificar si la cuenta está activa
                    if not user_data.get('active', True):
                        st.error("Tu cuenta ha sido desactivada. Por favor, contacta al administrador.")
                        return False

                    # 3. Login exitoso
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


# --- 4. FUNCIONES DE GESTIÓN (Ahora usan DataStore) ---

def create_new_user_db(username, password):
    """Crea un nuevo usuario en la DB (DataStore)."""
    if db_store.get_user(username):
        return False, "Ese nombre de usuario ya existe."
    
    user_id = f"dr_{username}_uid_{int(time.time())}"
    user_data = {"pwd": password, "role": "doctor", "id": user_id, "active": True}
    db_store.create_user(username, user_data)
    return True, f"Médico '{username}' creado con éxito (ID: {user_id})."

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


# --- PANEL DE ADMINISTRACIÓN (SOLO PARA ADMIN) ---
if st.session_state.user_role == 'admin':
    st.subheader("⚙️ Panel de Administración")
    
    tab_dashboard, tab_users, tab_files = st.tabs(["Dashboard de Uso", "Gestión de Médicos", "Historial Global"])

    # --- TAB 1: DASHBOARD DE USO (KPIs) ---
    with tab_dashboard:
        st.markdown("#### 📊 Dashboard de Uso (KPIs)")
        
        df_history = pd.DataFrame(get_global_history_db())
        
        if not df_history.empty:
            
            # Cálculo de Métricas Clave
            total_files = len(df_history)
            total_patients_evaluated = df_history['patients'].sum()
            
            col_kpi1, col_kpi2, col_kpi3 = st.columns(3)
            
            col_kpi1.metric("Total Histórico de Pacientes Evaluados", f"{total_patients_evaluated:,}")
            col_kpi2.metric("Archivos Totales Procesados", total_files)
            
            # Conteo de Médicos Activos/Inactivos
            all_doctors = get_doctors_db()
            active_doctors = sum(1 for d in all_doctors.values() if d.get('active', True))
            inactive_doctors = len(all_doctors) - active_doctors
            col_kpi3.metric("Médicos Activos", active_doctors, delta=-inactive_doctors, delta_color="inverse")
            
            st.markdown("---")
            st.markdown("#### 📈 Top 5 Médicos por Uso (Pacientes Evaluados)")
            
            # Uso por médico
            usage_by_doctor = df_history.groupby('usuario')['patients'].sum().sort_values(ascending=False).head(5)
            st.bar_chart(usage_by_doctor, color="#CE1126") # Rojo RD
        else:
            st.info("No hay datos históricos para mostrar métricas.")


    # --- TAB 2: GESTIÓN DE MÉDICOS ---
    with tab_users:
        col_add, col_list = st.columns(2)
        
        with col_add:
            st.markdown("#### ➕ Crear Nuevo Médico")
            st.info("Nota: Estos cambios se guardan de forma persistente en el archivo `nefro_db.json`.")
            
            # Formulario para añadir médico
            new_user = st.text_input("Nombre de Usuario del Nuevo Médico", key="new_user_input")
            new_pwd = st.text_input("Contraseña Temporal", type="password", key="new_pwd_input")
            if st.button("Crear Médico y Acceso"):
                if new_user and new_pwd:
                    success, message = create_new_user_db(new_user.lower(), new_pwd)
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
                # Excluir al admin de la gestión
                doctor_names = sorted([k for k, v in doctors.items() if v['role'] == 'doctor'])
                if not doctor_names:
                    st.info("No hay médicos para gestionar.")
                else:
                    user_to_manage = st.selectbox("Selecciona un Médico para Gestionar", doctor_names, key="user_to_manage")
                    
                    # Cargar el estado actual del médico seleccionado
                    selected_doctor_data = db_store.get_user(user_to_manage)
                    current_status_bool = selected_doctor_data.get('active', True)
                    
                    default_index = 0 if current_status_bool else 1 
                    
                    new_status = st.radio(
                        "Estado de la Cuenta", 
                        ["Activo", "Inactivo"], 
                        index=default_index,
                        key="status_radio"
                    )
                    
                    if st.button("Aplicar Cambio de Estado"):
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
        st.info("Vista global de auditoría de uso de la plataforma. (Datos obtenidos de la 'Colección Pública').")
        
        all_history_df = pd.DataFrame(get_global_history_db())
        
        if not all_history_df.empty:
            cols = ['usuario', 'timestamp', 'filename', 'patients']
            display_df = all_history_df[cols].sort_values(by='timestamp', ascending=False)
            st.dataframe(display_df, use_container_width=True, hide_index=True)
        else:
            st.info("Aún no hay ningún archivo subido por ningún usuario.")
    
    st.markdown("---")
# --- FIN PANEL DE ADMINISTRACIÓN ---


# --- FUNCIONES DE INTERPRETACIÓN DEL MODELO (SIMULACIÓN SHAP) ---
# ... (funciones generate_explanation_data y display_explanation se mantienen igual)
def generate_explanation_data(row):
    """
    Simula la contribución de cada característica al riesgo (como los valores SHAP).
    La lógica se basa en umbrales clínicos comunes.
    """
    contributions = {}
    
    # Valores de referencia de riesgo (umbrales simplificados)
    creatinina = row.get('creatinina', 1.0) # Alto riesgo si > 1.3
    glucosa = row.get('glucosa_ayunas', 90) # Alto riesgo si > 125
    presion = row.get('presion_sistolica', 120) # Alto riesgo si > 140
    edad = row.get('edad', 50) # Alto riesgo si > 65
    imc = row.get('imc', 25.0) # Alto riesgo si > 30

    # Lógica de Contribución:
    if creatinina > 2.0:
        contributions['Creatinina'] = 0.40
    elif creatinina > 1.3:
        contributions['Creatinina'] = 0.25
    else:
        contributions['Creatinina'] = -0.10
    
    if glucosa > 125:
        contributions['Glucosa Ayunas'] = 0.20
    elif glucosa > 100:
        contributions['Glucosa Ayunas'] = 0.05
    else:
        contributions['Glucosa Ayunas'] = -0.05

    if presion > 140:
        contributions['Presión Sistólica'] = 0.15
    elif presion > 130:
        contributions['Presión Sistólica'] = 0.05
    else:
        contributions['Presión Sistólica'] = -0.05
        
    if edad > 65:
        contributions['Edad'] = 0.10
    else:
        contributions['Edad'] = -0.03

    if imc > 30.0:
        contributions['IMC (Obesidad)'] = 0.08
    elif imc < 18.5:
        contributions['IMC (Bajo Peso)'] = 0.03
    else:
        contributions['IMC'] = -0.02

    total_abs = sum(abs(v) for v in contributions.values())
    if total_abs > 0:
        contributions = {k: v / total_abs for k, v in contributions.items()}

    return contributions

def display_explanation(data):
    """Muestra los datos de contribución como un gráfico de barras horizontal."""
    
    style = """
    <style>
        .contribution-bar-container {
            display: flex;
            align-items: center;
            margin-bottom: 5px;
            font-size: 0.9em;
        }
        .contribution-label {
            width: 150px;
            font-weight: bold;
        }
        .bar-wrapper {
            flex-grow: 1;
            height: 20px;
            background: #f0f0f0;
            border-radius: 4px;
            position: relative;
        }
        .bar-filler {
            height: 100%;
            position: absolute;
            border-radius: 4px;
        }
    </style>
    """
    st.markdown(style, unsafe_allow_html=True)
    
    max_val = max(abs(v) for v in data.values()) * 1.2
    
    for feature, contribution in data.items():
        width_percent = (abs(contribution) / max_val) * 50
        
        if contribution > 0:
            color = "#CE1126" # Rojo (Aumenta el riesgo)
            position = f"left: 50%; width: {width_percent}%;"
            icon = "🔺"
        else:
            color = "#4CAF50" # Verde (Disminuye el riesgo)
            position = f"right: 50%; width: {width_percent}%;"
            icon = "🔻"
        
        bar_html = f"""
        <div class="contribution-bar-container">
            <div class="contribution-label">{feature}</div>
            <div class="bar-wrapper">
                <div style="background-color: #888; width: 1px; height: 100%; position: absolute; left: 50%;"></div>
                <div class="bar-filler" style="background-color: {color}; {position}"></div>
            </div>
            <div style="width: 50px; margin-left: 10px; text-align: right;">{icon} {abs(contribution*100):.1f}%</div>
        </div>
        """
        st.markdown(bar_html, unsafe_allow_html=True)

    st.markdown("<p style='font-size: 0.8em; text-align: center; color: #888; margin-top: 10px;'>Las barras rojas 🔺 indican un factor que aumenta el riesgo. Las barras verdes 🔻 indican un factor que lo disminuye.</p>", unsafe_allow_html=True)
# -----------------------------------------------


# --- 5. Carga de Datos y Procesamiento ---
st.subheader("1. Carga de datos de pacientes")
uploaded = st.file_uploader("📁 Sube tu archivo Excel de pacientes", type=["xlsx", "xls"])

if uploaded:
    try:
        df = pd.read_excel(uploaded)
        st.success(f"¡Cargados {len(df)} pacientes correctamente!")

        required_cols = ['edad', 'imc', 'presion_sistolica', 'glucosa_ayunas', 'creatinina']
        missing_cols = [col for col in required_cols if col not in df.columns]

        if missing_cols:
             st.error(f"⚠️ Error: Faltan las siguientes columnas requeridas en tu Excel: {', '.join(missing_cols)}. Por favor, revisa el formato.")
             st.stop()
        
        X = df[required_cols]

        # LÓGICA DE PREDICCIÓN
        if model_loaded:
            predictions_proba = nefro_model.predict_proba(X)[:, 1]
            df['Riesgo_ERC_5años_%'] = (predictions_proba * 100).round(1)
        else:
            np.random.seed(42)
            df['Riesgo_ERC_5años_%'] = np.random.uniform(10, 95, len(df)).round(1)

        # --- REGISTRO DE ARCHIVO EN DB (Persistencia real) ---
        now = time.strftime("%Y-%m-%d %H:%M:%S")
        record = {
            "usuario": st.session_state.username,
            "user_id": st.session_state.user_id,
            "timestamp": now,
            "filename": uploaded.name,
            "patients": len(df)
        }
        # Usa la función de la capa de persistencia simulada
        db_store.add_file_record(record)
        # -----------------------------------------------------

        # --- 6. Presentación de Resultados ---
        st.subheader("2. Resultados predictivos y recomendaciones")

        total_alto_riesgo = len(df[df['Riesgo_ERC_5años_%'] > 70])
        total_pacientes = len(df)
        
        col_res1, col_res2, col_res3 = st.columns(3)

        col_res1.metric("Total Pacientes Evaluados", total_pacientes)
        col_res2.metric("Pacientes con Riesgo MUY ALTO", total_alto_riesgo, f"{((total_alto_riesgo/total_pacientes)*100):.1f}% de la muestra")
        col_res3.info(f"El riesgo máximo encontrado fue: {df['Riesgo_ERC_5años_%'].max():.1f}%")

        st.markdown("---")

        for i, row in df.iterrows():
            riesgo = row['Riesgo_ERC_5años_%']
            paciente_id = row.get('id_paciente', f'Paciente {i+1}')
            
            if riesgo > 70:
                color_bg, color_txt, nivel = "#CE1126", "white", "MUY ALTO - Referir URGENTE a nefrólogo" # Rojo RD
                emoji = "🚨"
            elif riesgo > 40:
                color_bg, color_txt, nivel = "#FFC400", "black", "ALTO - Control estricto cada 3 meses" # Ámbar
                emoji = "⚠️"
            else:
                color_bg, color_txt, nivel = "#4CAF50", "white", "MODERADO - Control anual" # Verde
                emoji = "✅"

            expander_html = f"""
            <style>
                div[data-testid="stExpander"] > div[role="button"] {{
                    background-color: {color_bg};
                    color: {color_txt};
                    border-radius: 8px;
                    padding: 10px;
                    margin-top: 5px;
                    font-size: 1.1em;
                }}
            </style>
            """
            st.markdown(expander_html, unsafe_allow_html=True)

            with st.expander(f"{emoji} **{paciente_id}** | Riesgo: **{riesgo}%**"):
                st.markdown(f"#### Nivel de Riesgo: {nivel.split(' - ')[0]} ({riesgo:.1f}%)")
                
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Creatinina (mg/dL)", f"{row.get('creatinina', 'N/D')}", help="Indicador clave de función renal.")
                col2.metric("Glucosa Ayunas (mg/dL)", f"{row.get('glucosa_ayunas', 'N/D')}", help="Factor de riesgo de diabetes.")
                col3.metric("Presión Sistólica (mmHg)", f"{row.get('presion_sistolica', 'N/D')}", help="Factor principal de la ERC.")
                col4.metric("IMC", f"{row.get('imc', 'N/D'):.1f}", help="Índice de Masa Corporal")
                
                st.markdown("---")

                st.subheader("Análisis de Contribución al Riesgo")
                st.markdown("<p style='font-size: 0.9em; color: #666;'>El riesgo es el resultado de la combinación de estos factores en el paciente:</p>", unsafe_allow_html=True)
                explanation_data = generate_explanation_data(row)
                display_explanation(explanation_data)

                st.markdown(f"<div style='padding: 15px; border-left: 5px solid {color_bg}; background-color: #f0f2f6; border-radius: 5px; margin-top: 20px;'>**RECOMENDACIÓN MÉDICA:** {nivel}</div>", unsafe_allow_html=True)
        
        st.markdown("---")

        # --- 7. Descarga de resultados ---
        st.subheader("3. Exportar Datos")
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Descargar resultados completos (CSV)",
            data=csv,
            file_name="NefroPredict_resultados.csv",
            mime="text/csv",
            help="Incluye todas las variables originales más la columna de predicción de riesgo."
        )

    except Exception as e:
        st.error(f"Ocurrió un error al procesar el archivo: {e}")

else:
    # Instrucciones si no hay archivo subido
    st.info("Sube tu archivo Excel para comenzar la evaluación de riesgo de ERC.")
    st.markdown("**Columnas esperadas:** `edad`, `imc`, `presion_sistolica`, `glucosa_ayunas`, `creatinina`, `id_paciente` (opcional)")
    if not model_loaded:
        st.warning("🚨 ADVERTENCIA: La aplicación está en modo **SIMULACIÓN** (el modelo real no se pudo cargar).")


# --- 8. Historial de Archivos (Aislamiento) ---
st.markdown("---")
st.subheader("Historial de Archivos del Usuario Actual")
st.info(f"Solo se muestra el historial asociado a tu ID: **{st.session_state.user_id}**")

# Filtrar el historial global para el usuario actual
global_history = db_store.get_file_history()
current_user_history = [
    record for record in global_history 
    if record.get('user_id') == st.session_state.user_id
]

if current_user_history:
    history_df = pd.DataFrame(current_user_history)
    st.dataframe(history_df, use_container_width=True, hide_index=True)
    st.caption("Esta información es persistente. En Firebase, se leería de tu ruta de usuario.")
else:
    st.info("No has subido ningún archivo aún.")

# --- 9. Footer ---
st.markdown("---")
st.markdown("<p style='text-align: center; color:#002868; font-weight:bold;'>© 2025 NefroPredict RD - Soluciones de salud impulsadas por IA</p>", unsafe_allow_html=True)
          
