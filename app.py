import pandas as pd
import numpy as np
import joblib
import json
import os
import bcrypt
import secrets
from datetime import datetime
import streamlit as st
import plotly.graph_objects as go
from io import BytesIO
from fpdf import FPDF

# 1. CONFIGURACIÓN (Debe ser lo primero)
st.set_page_config(
    page_title="NefroPredict RD",
    page_icon="🏥",
    layout="wide"
)

# 2. BASE DE DATOS LOCAL (JSON)
DB_FILE = "nefro_db.json"

class DataStore:
    def __init__(self):
        if not os.path.exists(DB_FILE):
            self._create_db()
        self.data = self._load()

    def _create_db(self):
        admin_pwd = bcrypt.hashpw("Admin2024!".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        initial = {
            "users": {
                "admin": {
                    "pwd": admin_pwd,
                    "role": "admin",
                    "name": "Administrador",
                    "active": True
                }
            },
            "patients": [],
            "audit_log": []
        }
        with open(DB_FILE, "w") as f:
            json.dump(initial, f, indent=4)

    def _load(self):
        with open(DB_FILE, "r") as f:
            return json.load(f)

    def save(self):
        with open(DB_FILE, "w") as f:
            json.dump(self.data, f, indent=4)

    def verify_login(self, username, password):
        user = self.data["users"].get(username)
        if user and user["active"]:
            if bcrypt.checkpw(password.encode('utf-8'), user["pwd"].encode('utf-8')):
                return user
        return None

db = DataStore()

# 3. FUNCIONES CLÍNICAS
def calcular_tfg(creatinina, edad, sexo, raza):
    # Simplificación de CKD-EPI para estabilidad
    k = 0.7 if sexo == "Mujer" else 0.9
    a = -0.329 if sexo == "Mujer" else -0.411
    f_raza = 1.159 if "Afro" in raza else 1.0
    f_sexo = 1.018 if sexo == "Mujer" else 1.0
    
    tfg = 141 * (min(creatinina/k, 1)**a) * (max(creatinina/k, 1)**-1.209) * (0.993**edad) * f_sexo * f_raza
    return round(tfg, 1)

# 4. INTERFAZ DE LOGIN
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("🏥 NefroPredict RD")
    with st.container():
        st.subheader("Acceso al Sistema")
        user_input = st.text_input("Usuario").lower().strip()
        pass_input = st.text_input("Contraseña", type="password")
        
        if st.button("Entrar"):
            user_data = db.verify_login(user_input, pass_input)
            if user_data:
                st.session_state.logged_in = True
                st.session_state.user = user_input
                st.session_state.role = user_data["role"]
                st.session_state.name = user_data["name"]
                st.rerun()
            else:
                st.error("Credenciales incorrectas")
    st.stop()

# 5. DASHBOARD PRINCIPAL (Si está logueado)
st.sidebar.title(f"Bienvenido, {st.session_state.name}")
if st.sidebar.button("Cerrar Sesión"):
    st.session_state.logged_in = False
    st.rerun()

tab1, tab2 = st.tabs(["Evaluación", "Historial"])

with tab1:
    st.header("Nueva Evaluación")
    with st.form("eval_form"):
        col1, col2 = st.columns(2)
        with col1:
            nombre = st.text_input("Nombre del Paciente")
            edad = st.number_input("Edad", 18, 100, 50)
            sexo = st.selectbox("Sexo", ["Hombre", "Mujer"])
        with col2:
            creat = st.number_input("Creatinina (mg/dL)", 0.1, 15.0, 1.0)
            raza = st.selectbox("Raza", ["No-Afroamericano", "Afroamericano"])
            
        submit = st.form_submit_button("Analizar")
        
    if submit and nombre:
        tfg_res = calcular_tfg(creat, edad, sexo, raza)
        riesgo = "Alto" if tfg_res < 60 else "Bajo"
        
        # Guardar resultado
        nuevo_paciente = {
            "fecha": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "nombre": nombre,
            "tfg": tfg_res,
            "riesgo": riesgo
        }
        db.data["patients"].append(nuevo_paciente)
        db.save()
        
        st.success(f"Análisis completado para {nombre}")
        st.metric("TFG (Tasa de Filtración)", f"{tfg_res} mL/min")
        st.info(f"Nivel de Riesgo detectado: {riesgo}")

with tab2:
    st.header("Pacientes Evaluados")
    if db.data["patients"]:
        df = pd.DataFrame(db.data["patients"])
        st.dataframe(df, use_container_width=True)
    else:
        st.write("No hay registros aún.")
