import streamlit as st
import pandas as pd
import numpy as np
import time
import joblib 

# --- CONFIGURACIÓN DE LA PÁGINA Y ESTADO INICIAL ---
st.set_page_config(page_title="NefroPredict RD", page_icon="🫘", layout="wide")

# --- 0. Inicialización de Sesión y Datos Simulación ---

# Inicialización de la Session State para persistencia temporal (simulando Firestore)
if 'MOCK_USERS' not in st.session_state:
    st.session_state.MOCK_USERS = {
        # 'active': True por defecto. Lo usamos para la gestión de cuentas.
        "admin": {"pwd": "admin", "role": "admin", "id": "admin_nefro", "active": True},
        "dr.perez": {"pwd": "pass1", "role": "doctor", "id": "dr_perez_uid_001", "active": True},
        "dr.gomez": {"pwd": "pass2", "role": "doctor", "id": "dr_gomez_uid_002", "active": True},
        "dr.sanchez": {"pwd": "pass3", "role": "doctor", "id": "dr_sanchez_uid_003", "active": False}, # Cuenta inactiva de prueba
    }

if 'MOCK_HISTORY' not in st.session_state:
    # Historial de archivos simulado por usuario.
    st.session_state.MOCK_HISTORY = {
        "admin_nefro": [
            {"usuario": "admin", "timestamp": "2025-05-01 10:00", "filename": "Test_Global.xlsx", "patients": 100},
        ],
        "dr_perez_uid_001": [
            {"usuario": "dr.perez", "timestamp": "2025-05-02 14:30", "filename": "Mis_Pacientes_Q1_2025.xlsx", "patients": 55},
            {"usuario": "dr.perez", "timestamp": "2025-05-03 09:15", "filename": "Consulta_Semanal.xlsx", "patients": 12},
        ],
        "dr_gomez_uid_002": [
            {"usuario": "dr.gomez", "timestamp": "2025-05-01 11:00", "filename": "Pacientes_HTA.xlsx", "patients": 80},
            {"usuario": "dr.gomez", "timestamp": "2025-05-01 16:00", "filename": "Revision_Mensual.xlsx", "patients": 20},
        ]
    }

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_id = None
    st.session_state.user_role = None
    st.session_state.username = None


# --- 1. Funciones de Acceso a Datos (Simulación de DB) ---

def create_new_user(username, password):
    """Simula la creación de un nuevo usuario en la DB."""
    if username in st.session_state.MOCK_USERS:
        return False, "Ese nombre de usuario ya existe."
    
    user_id = f"dr_{username}_uid_{len(st.session_state.MOCK_USERS) + 1}"
    # Guardar en Session State
    st.session_state.MOCK_USERS[username] = {"pwd": password, "role": "doctor", "id": user_id, "active": True}
    st.session_state.MOCK_HISTORY[user_id] = []
    return True, f"Médico '{username}' creado con éxito (ID: {user_id})."

def update_user_status(username, is_active):
    """Simula la activación/desactivación de un usuario en la DB."""
    if username in st.session_state.MOCK_USERS and st.session_state.MOCK_USERS[username]['role'] == 'doctor':
        st.session_state.MOCK_USERS[username]['active'] = is_active
        return True
    return False

def get_doctors():
    """Obtiene la lista de todos los médicos (no admin)."""
    return {k: v for k, v in st.session_state.MOCK_USERS.items() if v['role'] == 'doctor'}

def get_global_history():
    """Obtiene y combina el historial de todos los usuarios."""
    all_records = []
    for user_id, history_list in st.session_state.MOCK_HISTORY.items():
        all_records.extend(history_list)
    if all_records:
        return pd.DataFrame(all_records)
    return pd.DataFrame()


# --- 2. Título y Branding ---
st.markdown("<h1 style='text-align: center; color:#002868;'>🫘 NefroPredict RD 2025</h1>", unsafe_allow_html=True)
st.markdown("<h3 style='text-align: center;'>Detección temprana de enfermedad renal crónica</h3>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color:#CE1126; font-size:1.1em;'>República Dominicana 🇩🇴</p>", unsafe_allow_html=True)

# --- FUNCIÓN DE CARGA DE MODELO (Mantener para referencia) ---
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


# --- 3. SISTEMA DE AUTENTICACIÓN Y ROLES ---

def check_login():
    """Maneja el flujo de login y verifica el estado 'active'."""
    if not st.session_state.logged_in:
        st.markdown("### 🔐 Acceso de Usuario")
        
        with st.form("login_form"):
            user = st.text_input("Nombre de Usuario (ej: admin, dr.perez)", key="user_input").lower()
            pwd = st.text_input("Contraseña", type="password", key="password_input")
            
            submitted = st.form_submit_button("Ingresar")

            if submitted:
                if user in st.session_state.MOCK_USERS and st.session_state.MOCK_USERS[user]['pwd'] == pwd:
                    user_data = st.session_state.MOCK_USERS[user]
                    
                    # Verificar si la cuenta está activa
                    if not user_data.get('active', True):
                        st.error("Tu cuenta ha sido desactivada. Por favor, contacta al administrador.")
                        return False

                    # Login exitoso
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
with col_user:
    status = "Activo" if st.session_state.MOCK_USERS[st.session_state.username].get('active', True) else "INACTIVO"
    st.success(f"✅ Sesión activa | Usuario: **{st.session_state.username}** | Rol: **{st.session_state.user_role.capitalize()}** | Estado: **{status}**")
with col_logout:
    if st.button("Cerrar Sesión"):
        st.session_state.logged_in = False
        st.session_state.user_id = None
        st.session_state.user_role = None
        st.session_state.username = None
        st.rerun()

st.markdown("---")

# --- PANEL DE ADMINISTRACIÓN (SOLO PARA ADMIN) ---
if st.session_state.user_role == 'admin':
    st.subheader("⚙️ Panel de Administración")
    
    tab_dashboard, tab_users, tab_files = st.tabs(["Dashboard de Uso", "Gestión de Médicos", "Historial Global"])

    # --- TAB 1: DASHBOARD DE USO (KPIs) ---
    with tab_dashboard:
        st.markdown("#### 📊 Dashboard de Uso (KPIs)")
        
        df_history = get_global_history()
        
        if not df_history.empty:
            
            # Cálculo de Métricas Clave
            total_files = len(df_history)
            total_patients_evaluated = df_history['patients'].sum()
            
            col_kpi1, col_kpi2, col_kpi3 = st.columns(3)
            
            col_kpi1.metric("Total Histórico de Pacientes Evaluados", f"{total_patients_evaluated:,}")
            col_kpi2.metric("Archivos Totales Procesados", total_files)
            
            # Conteo de Médicos Activos/Inactivos
            all_doctors = get_doctors()
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
            st.info("Nota: Estos cambios son persistentes mientras la sesión de Streamlit esté activa.")
            
            # Formulario para añadir médico
            new_user = st.text_input("Nombre de Usuario del Nuevo Médico", key="new_user_input")
            new_pwd = st.text_input("Contraseña Temporal", type="password", key="new_pwd_input")
            if st.button("Crear Médico y Acceso"):
                if new_user and new_pwd:
                    success, message = create_new_user(new_user.lower(), new_pwd)
                    if success:
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)
                else:
                    st.warning("Debes llenar ambos campos.")
                    
        with col_list:
            st.markdown("#### 📋 Listado de Médicos")
            doctors = get_doctors()
            
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
                user_to_manage = st.selectbox("Selecciona un Médico para Gestionar", sorted(list(doctors.keys())), key="user_to_manage")
                current_status = doctors[user_to_manage].get('active', True)
                
                # Usamos el estado actual para la selección inicial
                default_index = 0 if current_status else 1 
                
                new_status = st.radio(
                    "Estado de la Cuenta", 
                    ["Activo", "Inactivo"], 
                    index=default_index,
                    key="status_radio"
                )
                
                if st.button("Aplicar Cambio de Estado"):
                    is_active = (new_status == "Activo")
                    if update_user_status(user_to_manage, is_active):
                        st.success(f"Estado de '{user_to_manage}' actualizado a: {new_status}")
                        st.rerun()
                    else:
                        st.error("Error al actualizar el estado del usuario.")
            else:
                st.info("No hay médicos para gestionar.")


    # --- TAB 3: HISTORIAL GLOBAL DE ARCHIVOS ---
    with tab_files:
        st.markdown("#### 📁 Archivos Subidos por Todos los Médicos")
        st.info("Vista global de auditoría de uso de la plataforma.")
        
        all_history_df = get_global_history()
        
        if not all_history_df.empty:
            # Asegurar que el usuario y la marca de tiempo estén presentes
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
    
    # 1. Creatinina (El factor más fuerte)
    if creatinina > 2.0:
        contributions['Creatinina'] = 0.40 # Muy Alta
    elif creatinina > 1.3:
        contributions['Creatinina'] = 0.25 # Alta
    else:
        contributions['Creatinina'] = -0.10 # Baja el riesgo
    
    # 2. Glucosa en Ayunas
    if glucosa > 125:
        contributions['Glucosa Ayunas'] = 0.20 # Alta
    elif glucosa > 100:
        contributions['Glucosa Ayunas'] = 0.05 # Media
    else:
        contributions['Glucosa Ayunas'] = -0.05 # Baja el riesgo

    # 3. Presión Sistólica
    if presion > 140:
        contributions['Presión Sistólica'] = 0.15 # Alta
    elif presion > 130:
        contributions['Presión Sistólica'] = 0.05 # Media
    else:
        contributions['Presión Sistólica'] = -0.05 # Baja el riesgo
        
    # 4. Edad
    if edad > 65:
        contributions['Edad'] = 0.10 # Media
    else:
        contributions['Edad'] = -0.03 # Baja el riesgo

    # 5. IMC
    if imc > 30.0:
        contributions['IMC (Obesidad)'] = 0.08 # Media
    elif imc < 18.5:
        contributions['IMC (Bajo Peso)'] = 0.03 # Baja
    else:
        contributions['IMC'] = -0.02 # Baja el riesgo (peso normal)

    # Normalizar para que la suma absoluta no exceda un valor razonable (esto es solo visual)
    total_abs = sum(abs(v) for v in contributions.values())
    if total_abs > 0:
        contributions = {k: v / total_abs for k, v in contributions.items()}

    return contributions

def display_explanation(data):
    """Muestra los datos de contribución como un gráfico de barras horizontal."""
    
    # Estilos CSS para las barras
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
    
    # Calcular el rango máximo para escalar las barras (simulando el eje central)
    max_val = max(abs(v) for v in data.values()) * 1.2
    
    # Renderizar cada barra
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
        
        # HTML para la barra
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


# --- 4. Carga de Datos y Procesamiento ---
st.subheader("1. Carga de datos de pacientes")
uploaded = st.file_uploader("📁 Sube tu archivo Excel de pacientes", type=["xlsx", "xls"])

if uploaded:
    try:
        df = pd.read_excel(uploaded)
        st.success(f"¡Cargados {len(df)} pacientes correctamente!")

        # ... (rest of the processing logic)
        required_cols = ['edad', 'imc', 'presion_sistolica', 'glucosa_ayunas', 'creatinina']
        missing_cols = [col for col in required_cols if col not in df.columns]

        if missing_cols:
             st.error(f"⚠️ Error: Faltan las siguientes columnas requeridas en tu Excel: {', '.join(missing_cols)}. Por favor, revisa el formato.")
             st.stop()
        
        # Seleccionar las características necesarias para el modelo
        X = df[required_cols]

        # --- LÓGICA DE PREDICCIÓN REAL O SIMULACIÓN ---
        if model_loaded:
            st.info(f"Usando el modelo cargado para predicción real: {type(nefro_model).__name__}")
            predictions_proba = nefro_model.predict_proba(X)[:, 1]
            df['Riesgo_ERC_5años_%'] = (predictions_proba * 100).round(1)
        else:
            st.warning("Usando simulación de riesgo: El modelo real no pudo cargarse.")
            np.random.seed(42)
            df['Riesgo_ERC_5años_%'] = np.random.uniform(10, 95, len(df)).round(1)
        # -----------------------------------------------

        # --- 5. Presentación de Resultados ---
        st.subheader("2. Resultados predictivos y recomendaciones")

        # Registro del archivo subido en el historial (simulando guardado)
        now = time.strftime("%Y-%m-%d %H:%M:%S")
        record = {
            "usuario": st.session_state.username,
            "timestamp": now,
            "filename": uploaded.name,
            "patients": len(df)
        }
        
        # Agregar al historial del usuario actual
        if st.session_state.user_id not in st.session_state.MOCK_HISTORY:
            st.session_state.MOCK_HISTORY[st.session_state.user_id] = []
        
        st.session_state.MOCK_HISTORY[st.session_state.user_id].insert(0, record)

        # Métricas de resumen general
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
            
            # Determinación del nivel de riesgo y estilo
            if riesgo > 70:
                color_bg, color_txt, nivel = "#CE1126", "white", "MUY ALTO - Referir URGENTE a nefrólogo" # Rojo RD
                emoji = "🚨"
            elif riesgo > 40:
                color_bg, color_txt, nivel = "#FFC400", "black", "ALTO - Control estricto cada 3 meses" # Ámbar
                emoji = "⚠️"
            else:
                color_bg, color_txt, nivel = "#4CAF50", "white", "MODERADO - Control anual" # Verde
                emoji = "✅"

            # Personalización del Expander usando HTML para el color de fondo del encabezado
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
                # Mostrar el detalle de los biomarcadores
                st.markdown(f"#### Nivel de Riesgo: {nivel.split(' - ')[0]} ({riesgo:.1f}%)")
                
                # Biomatricadores actuales
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Creatinina (mg/dL)", f"{row.get('creatinina', 'N/D')}", help="Indicador clave de función renal.")
                col2.metric("Glucosa Ayunas (mg/dL)", f"{row.get('glucosa_ayunas', 'N/D')}", help="Factor de riesgo de diabetes.")
                col3.metric("Presión Sistólica (mmHg)", f"{row.get('presion_sistolica', 'N/D')}", help="Factor principal de la ERC.")
                col4.metric("IMC", f"{row.get('imc', 'N/D'):.1f}", help="Índice de Masa Corporal")
                
                st.markdown("---")

                # Interpretación del Modelo (SHAP SIMULADO)
                st.subheader("Análisis de Contribución al Riesgo")
                st.markdown("<p style='font-size: 0.9em; color: #666;'>El riesgo es el resultado de la combinación de estos factores en el paciente:</p>", unsafe_allow_html=True)
                explanation_data = generate_explanation_data(row)
                display_explanation(explanation_data)

                # Recomendación final
                st.markdown(f"<div style='padding: 15px; border-left: 5px solid {color_bg}; background-color: #f0f2f6; border-radius: 5px; margin-top: 20px;'>**RECOMENDACIÓN MÉDICA:** {nivel}</div>", unsafe_allow_html=True)
        
        st.markdown("---")

        # --- 6. Descarga de resultados ---
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


# --- 7. Historial de Archivos (Aislamiento) ---
st.markdown("---")
st.subheader("Historial de Archivos del Usuario Actual")
st.info(f"Solo se muestra el historial asociado a tu ID: **{st.session_state.user_id}**")

current_history = st.session_state.MOCK_HISTORY.get(st.session_state.user_id, [])

if current_history:
    history_df = pd.DataFrame(current_history)
    st.dataframe(history_df, use_container_width=True, hide_index=True)
    st.caption("Esta información estaría guardada en Firestore bajo una ruta exclusiva para tu ID (`/users/{tu_id}/archivos`).")
else:
    st.info("No has subido ningún archivo aún.")

# --- 8. Footer ---
st.markdown("---")
st.markdown("<p style='text-align: center; color:#002868; font-weight:bold;'>© 2025 NefroPredict RD - Soluciones de salud impulsadas por IA</p>", unsafe_allow_html=True)
