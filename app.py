import pandas as pd
import numpy as np
import time
import joblib
import json
import os
import io
import streamlit as st
import altair as alt
import streamlit.components.v1 as components

# =============================================
# CONFIGURACIÓN DE PÁGINA
# =============================================
st.set_page_config(page_title="NefroPredict RD", page_icon="Kidney", layout="wide")

# =============================================
# ESTILOS
# =============================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');
    html, body, [class*="css"] {font-family: 'Inter', sans-serif;}
    h1, h2, h3 {color: #002868 !important;}
    .stButton > button {
        background: #002868; 
        color: white; 
        border-radius: 12px; 
        padding: 0.7rem 1.5rem;
        transition: background-color 0.3s ease;
    }
    .stButton > button:hover {
        background: #004499;
    }
    .risk-gauge-bar {
        height: 40px; border-radius: 20px;
        background: linear-gradient(to right, #10B981 0%, #FACC15 40%, #F97316 70%, #EF4444 100%);
        position: relative; margin: 20px 0;
    }
    .risk-gauge-marker {
        position: absolute; top: -20px; left: var(--pos); transform: translateX(-50%);
        width: 12px; height: 80px; background: white; border: 4px solid black; border-radius: 6px;
    }
</style>
""", unsafe_allow_html=True)

st.markdown("<h1 style='text-align: center;'>NefroPredict RD 2025</h1>", unsafe_allow_html=True)
st.markdown("<h3 style='text-align: center; color:#555;'>Detección temprana de ERC • República Dominicana</h3>", unsafe_allow_html=True)

# =============================================
# BASE DE DATOS SIMULADA (JSON) - CLASE DataStore ACTUALIZADA
# =============================================
DB_FILE = "nefro_db.json"

class DataStore:
    def __init__(self, path):
        self.path = path
        if not os.path.exists(path):
            self._init_db()

    def _init_db(self):
        data = {
            "users": {
                "admin": {"pwd": "admin", "role": "admin", "id": "admin_001", "active": True},
                "dr.perez": {"pwd": "pass1", "role": "doctor", "id": "dr_001", "active": True},
                "dr.gomez": {"pwd": "pass2", "role": "doctor", "id": "dr_002", "active": True}
            },
            "file_history": [],
            "patient_records": []
        }
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

    def _load(self):
        if not os.path.exists(self.path):
            self._init_db()
        with open(self.path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _save(self, data):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

    def get_user(self, username):
        return self._load().get("users", {}).get(username)

    def get_all_users(self):
        return self._load().get("users", {})
        
    def get_all_doctors(self):
        data = self._load()
        # Devuelve solo usuarios con rol 'doctor'
        return {
            username: user_data
            for username, user_data in data.get("users", {}).items()
            if user_data.get("role") == "doctor"
        }

    def add_user(self, username, password, role="doctor"):
        data = self._load()
        if username in data["users"]:
            return False, "Usuario ya existe."
        
        # Generar un ID simple para el nuevo doctor
        count = sum(1 for u in data["users"].values() if u["role"] == role)
        new_id = f"{role[:2]}_{count+1:03d}"
        
        data["users"][username] = {
            "pwd": password,
            "role": role,
            "id": new_id,
            "active": True
        }
        self._save(data)
        return True, "Usuario creado exitosamente."

    def delete_user(self, username):
        data = self._load()
        # No permitir eliminar al propio usuario o al admin
        if username == st.session_state.username or data["users"].get(username, {}).get("role") == "admin":
            return False
        
        if username in data["users"]:
            del data["users"][username]
            self._save(data)
            return True
        return False

    def update_user(self, username, updates): 
        data = self._load()
        if username in data["users"]:
            data["users"][username].update(updates)
            self._save(data)
            return True
        return False

    def add_patient_record(self, record):
        data = self._load()
        data["patient_records"].insert(0, record)
        self._save(data)

    def add_patient_records_bulk(self, records_list):
        data = self._load()
        data["patient_records"].extend(records_list)
        # Ordenar por timestamp, ya que los nuevos registros se agregan al final
        data["patient_records"].sort(key=lambda x: x["timestamp"], reverse=True)
        self._save(data)

    def get_patient_records(self, name):
        data = self._load()
        return sorted(
            [r for r in data["patient_records"] if r["nombre_paciente"].lower() == name.lower()],
            key=lambda x: x["timestamp"], reverse=True
        )

    def get_all_patient_names(self):
        data = self._load()
        names = {r["nombre_paciente"] for r in data["patient_records"] if "nombre_paciente" in r}
        return sorted(names)

db = DataStore(DB_FILE)

# =============================================
# CARGA DEL MODELO
# =============================================
@st.cache_resource
def load_model():
    try:
        # NOTA: Asegúrate de tener el archivo "modelo_erc.joblib"
        return joblib.load("modelo_erc.joblib")
    except FileNotFoundError:
        st.warning("Modelo no encontrado (modelo_erc.joblib) → Modo simulación activo.")
        return None

model = load_model()

# =============================================
# LOGIN
# =============================================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.markdown("### Iniciar Sesión")
    with st.form("login"):
        user = st.text_input("Usuario").lower()
        pwd = st.text_input("Contraseña", type="password")
        if st.form_submit_button("Entrar"):
            u = db.get_user(user)
            if u and u["pwd"] == pwd and u.get("active", True):
                st.session_state.logged_in = True
                st.session_state.username = user
                st.session_state.role = u["role"]
                st.session_state.user_id = u["id"]
                st.rerun()
            else:
                st.error("Credenciales incorrectas o usuario inactivo")
    st.stop()

# Logout
col1, col2 = st.columns([4,1])
with col1:
    st.success(f"Usuario: **{st.session_state.username.upper()}** • Rol: **{st.session_state.role.upper()}**")
with col2:
    if st.button("Salir"):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.rerun()

st.markdown("---")

# =============================================
# FUNCIONES CLAVE
# =============================================
def get_risk_level(risk):
    if risk > 70: return "MUY ALTO", "#CE1126", "Referir URGENTE"
    elif risk > 40: return "ALTO", "#FFC400", "Control estricto"
    else: return "MODERADO", "#4CAF50", "Control habitual"

def predict_risk(row):
    # Asegurar que los valores sean floats y manejen datos faltantes si es necesario
    try:
        features = np.array([[row["edad"], row["imc"], row["presion_sistolica"], row["glucosa_ayunas"], row["creatinina"]]])
        if model:
            prob = model.predict_proba(features)[0][1]
            return round(prob * 100, 1)
        else:
            # Simulación simple si el modelo no carga
            base = 10 + (row["creatinina"] - 1) * 35 + max(0, row["glucosa_ayunas"] - 126) * 0.3
            return max(1, min(99, base + np.random.uniform(-10, 15)))
    except:
        # Si hay error en la conversión o cálculo, devolver un riesgo neutral (50%)
        return 50.0

# =============================================
# PESTAÑAS
# =============================================
if st.session_state.role == "admin":
    tab1, tab2, tab3, tab4 = st.tabs(["Predicción Individual", "Carga Masiva", "Historial", "Administración"])
else:
    tab1, tab2, tab3 = st.tabs(["Predicción Individual", "Carga Masiva", "Historial"])


with tab1:
    st.subheader("Predicción Individual")
    with st.form("individual"):
        nombre = st.text_input("Nombre del paciente", "María Almonte")
        c1, c2 = st.columns(2)
        with c1:
            edad = st.number_input("Edad", 18, 120, 60)
            imc = st.number_input("IMC", 10.0, 60.0, 30.0, 0.1)
            glucosa = st.number_input("Glucosa ayunas", 50, 500, 180)
        with c2:
            presion = st.number_input("Presión sistólica", 80, 250, 160)
            creat = st.number_input("Creatinina", 0.1, 10.0, 1.9, 0.01)

        if st.form_submit_button("Calcular"):
            if not nombre.strip():
                st.error("El nombre es obligatorio")
            else:
                row = {"edad": edad, "imc": imc, "presion_sistolica": presion,
                       "glucosa_ayunas": glucosa, "creatinina": creat}
                risk = predict_risk(row)
                nivel, color, reco = get_risk_level(risk)

                # Guardar
                record = {
                    "nombre_paciente": nombre,
                    "user_id": st.session_state.user_id,
                    "usuario": st.session_state.username,
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                    **row,
                    "risk": risk,
                    "nivel": nivel
                }
                db.add_patient_record(record)

                st.session_state.last_risk = risk
                st.session_state.last_nivel = nivel
                st.session_state.last_color = color
                st.session_state.last_reco = reco
                st.rerun()

    # Mostrar resultado
    if "last_risk" in st.session_state:
        r = st.session_state.last_risk
        n = st.session_state.last_nivel
        c = st.session_state.last_color
        reco = st.session_state.last_reco

        st.markdown(f"""
        <div style="text-align:center; padding:30px; background:#f9f9f9; border-radius:16px; border: 3px solid {c}">
            <h2 style="color:{c}">{n}</h2>
            <h1 style="font-size:5rem; margin:10px; color:{c}">{r:.1f}%</h1>
            <div class="risk-gauge-bar"><div class="risk-gauge-marker" style="--pos: {r}%"></div></div>
            <p style="font-size:1.2rem"><strong>Recomendación:</strong> {reco}</p>
        </div>
        """, unsafe_allow_html=True)


with tab2:
    st.subheader("Carga Masiva de Pacientes (Excel/CSV)")
    
    if st.session_state.role != "admin":
        st.warning("Esta funcionalidad es solo para usuarios Administradores.")
    else:
        st.info("Formato esperado: Las columnas deben llamarse: 'nombre_paciente', 'edad', 'imc', 'presion_sistolica', 'glucosa_ayunas', 'creatinina'.")
        uploaded_file = st.file_uploader("Subir archivo de pacientes (.xlsx o .csv)", type=["csv", "xlsx"])
        
        if uploaded_file:
            try:
                # Lectura de archivo
                if uploaded_file.name.endswith('.csv'):
                    df_upload = pd.read_csv(uploaded_file)
                else:
                    df_upload = pd.read_excel(uploaded_file)
                
                required_cols = ["nombre_paciente", "edad", "imc", "presion_sistolica", "glucosa_ayunas", "creatinina"]
                missing_cols = [col for col in required_cols if col not in df_upload.columns]
                
                if missing_cols:
                    st.error(f"El archivo debe contener las siguientes columnas: {', '.join(required_cols)}. Faltan: {', '.join(missing_cols)}")
                elif len(df_upload) < 1:
                    st.warning("El archivo está vacío.")
                else:
                    st.success(f"Archivo cargado. {len(df_upload)} registros encontrados. Procesando...")
                    
                    processed_records = []
                    start_time = time.time()
                    
                    # 1. Asegurar tipos de datos y manejar errores
                    df_upload['nombre_paciente'] = df_upload['nombre_paciente'].astype(str).fillna('Paciente Desconocido')
                    
                    # 2. Aplicar la predicción a cada fila
                    for index, row in df_upload.iterrows():
                        try:
                            # Convertir a float y validar rangos básicos (simplificado)
                            patient_row = {
                                "edad": float(row["edad"]), 
                                "imc": float(row["imc"]), 
                                "presion_sistolica": float(row["presion_sistolica"]),
                                "glucosa_ayunas": float(row["glucosa_ayunas"]), 
                                "creatinina": float(row["creatinina"])
                            }
                            
                            risk = predict_risk(patient_row)
                            nivel, _, _ = get_risk_level(risk)
                            
                            record = {
                                "nombre_paciente": row["nombre_paciente"],
                                "user_id": st.session_state.user_id,
                                "usuario": st.session_state.username,
                                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                                **patient_row,
                                "risk": risk,
                                "nivel": nivel
                            }
                            processed_records.append(record)
                        except Exception:
                            # Capturar cualquier error de conversión o dato faltante/nulo
                            st.warning(f"Fila {index+1} ({row.get('nombre_paciente', 'N/A')}): Datos inválidos o faltantes. Ignorando.")

                    if processed_records:
                        db.add_patient_records_bulk(processed_records)
                        end_time = time.time()
                        
                        st.balloons()
                        st.success(f"¡Carga masiva completada! Se procesaron {len(processed_records)} registros en {end_time - start_time:.2f} segundos.")
                        
                        # Mostrar una vista previa de los primeros 10 registros procesados
                        st.markdown("#### Vista Previa de Registros Cargados")
                        st.dataframe(pd.DataFrame(processed_records)[required_cols + ["risk", "nivel"]].head(10), use_container_width=True)
                        st.info("Ahora puedes ver los pacientes en la pestaña 'Historial'.")
                    else:
                        st.error("No se pudo procesar ningún registro válido del archivo.")
            
            except Exception as e:
                st.error(f"Error general al procesar el archivo. Asegúrate de que el formato sea correcto. Error: {e}")
                # st.exception(e) # Comentado para evitar mostrar traceback al usuario final


with tab3:
    st.subheader("Historial de pacientes")
    names = db.get_all_patient_names()
    if names:
        selected = st.selectbox("Seleccionar paciente", [""] + names)
        if selected:
            records = db.get_patient_records(selected)
            df = pd.DataFrame(records)
            st.dataframe(df[["timestamp", "risk", "nivel", "creatinina", "glucosa_ayunas"]], use_container_width=True)
    else:
        st.info("Aún no hay registros")


# =============================================
# PESTAÑA DE ADMINISTRACIÓN (SOLO ADMIN)
# =============================================
if st.session_state.role == "admin":
    with tab4:
        st.subheader("Panel de Administración de Usuarios")
        
        # --- 1. Crear Doctor ---
        st.markdown("#### Crear Nuevo Usuario Doctor")
        with st.form("new_doctor"):
            new_user = st.text_input("Nombre de Usuario (Login)").lower()
            new_pwd = st.text_input("Contraseña", type="password")
            # En este contexto, solo permitimos crear doctores, pero se mantiene la estructura
            # new_role = st.selectbox("Rol", ["doctor"], disabled=True) 
            
            if st.form_submit_button("Crear Usuario Doctor"):
                if new_user and new_pwd:
                    # El rol por defecto en add_user es "doctor"
                    success, message = db.add_user(new_user, new_pwd, "doctor") 
                    if success:
                        st.success(message)
                        time.sleep(1)
                        st.rerun() # Recargar la página para actualizar la lista
                    else:
                        st.error(message)
                else:
                    st.error("El usuario y la contraseña son obligatorios.")

        st.markdown("---")
        
        # --- 2. Lista y Eliminar Doctores ---
        st.markdown("#### Doctores Registrados")
        doctors_data = db.get_all_doctors()
        
        if doctors_data:
            df_doctors = pd.DataFrame.from_dict(doctors_data, orient='index')
            df_doctors['Username'] = df_doctors.index
            df_doctors['Role'] = df_doctors['role']
            df_doctors = df_doctors[['Username', 'Role', 'id', 'active']]
            df_doctors = df_doctors.rename(columns={'id': 'ID de Sistema', 'active': 'Activo', 'Role': 'Rol'})
            
            st.dataframe(df_doctors, use_container_width=True, hide_index=True)
            
            st.markdown("##### Eliminar Doctor")
            
            # Crear una lista de opciones para el selectbox, excluyendo al usuario actual y al admin.
            deletable_users = sorted([
                u for u in doctors_data.keys() 
                if u != st.session_state.username 
            ])
            
            user_to_delete = st.selectbox("Seleccionar Doctor a Eliminar", 
                                          [""] + deletable_users)
            
            if st.button("Confirmar Eliminación", type="primary"):
                if user_to_delete:
                    if db.delete_user(user_to_delete):
                        st.success(f"Doctor '{user_to_delete}' eliminado.")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(f"Error al eliminar al doctor '{user_to_delete}'.")
                else:
                    st.warning("Selecciona un doctor para eliminar.")
        else:
            st.info("No hay doctores registrados.")


st.markdown("---")
st.caption("En NefroPredict cuidamos tu salud")
