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
    .stButton > button {background: #002868; color: white; border-radius: 12px; padding: 0.7rem 1.5rem;}
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
# BASE DE DATOS SIMULADA (JSON)
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

    def update_user(self, username, updates):  # ← SIN ERROR DE SINTAXIS
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
        return joblib.load("modelo_erc.joblib")
    except:
        st.warning("Modelo no encontrado → Modo simulación")
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
    features = np.array([[row["edad"], row["imc"], row["presion_sistolica"], row["glucosa_ayunas"], row["creatinina"]]])
    if model:
        prob = model.predict_proba(features)[0][1]
        return round(prob * 100, 1)
    else:
        # Simulación simple
        base = 10 + (row["creatinina"] - 1) * 35 + max(0, row["glucosa_ayunas"] - 126) * 0.3
        return max(1, min(99, base + np.random.uniform(-10, 15)))

# =============================================
# PESTAÑAS
# =============================================
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

st.markdown("---")
st.caption("NefroPredict RD ")
