import pandas as pd
import numpy as np
import joblib
import json
import os
import bcrypt
import secrets
import sqlite3
from datetime import datetime
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from io import BytesIO
from fpdf import FPDF

# =============================================
# CONFIGURACIÓN Y ESTILOS
# =============================================
st.set_page_config(
    page_title="NefroPredict RD v2.0",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

PRIMARY = "#0066CC"
SECONDARY = "#00A896"
DANGER = "#E63946"
WARNING = "#F77F00"
SUCCESS = "#06D6A0"

# Inyectar CSS Mejorado
st.markdown(f"""
<style>
    .main {{ background-color: #0e1117; }}
    .stMetric {{ background-color: #1a202c; padding: 15px; border-radius: 10px; border: 1px solid #2d3748; }}
    .risk-card {{ padding: 25px; border-radius: 15px; text-align: center; margin: 10px 0; }}
    .risk-high {{ background: rgba(230, 57, 70, 0.1); border: 2px solid {DANGER}; }}
    .risk-med {{ background: rgba(247, 127, 0, 0.1); border: 2px solid {WARNING}; }}
    .risk-low {{ background: rgba(6, 214, 160, 0.1); border: 2px solid {SUCCESS}; }}
    h1, h2, h3 {{ color: white !important; }}
</style>
""", unsafe_allow_html=True)

# =============================================
# GESTIÓN DE BASE DE DATOS (SQLITE)
# =============================================
class DBManager:
    def __init__(self):
        self.conn = sqlite3.connect("nefro_v2.db", check_same_thread=False)
        self.create_tables()

    def create_tables(self):
        cursor = self.conn.cursor()
        # Tabla Usuarios
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                password TEXT,
                name TEXT,
                role TEXT,
                active INTEGER,
                last_login TEXT
            )
        """)
        # Tabla Pacientes/Evaluaciones
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS evaluations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_name TEXT,
                doctor_user TEXT,
                age INTEGER,
                sex TEXT,
                race TEXT,
                creatinine REAL,
                glucose REAL,
                systolic INTEGER,
                bmi REAL,
                tfg REAL,
                stage TEXT,
                risk_pct REAL,
                timestamp TEXT
            )
        """)
        # Crear admin por defecto si no existe
        cursor.execute("SELECT * FROM users WHERE username='admin'")
        if not cursor.fetchone():
            pwd = bcrypt.hashpw("Admin2024!".encode(), bcrypt.gensalt()).decode()
            cursor.execute("INSERT INTO users VALUES (?,?,?,?,?,?)", 
                          ("admin", pwd, "Administrador Principal", "admin", 1, None))
        self.conn.commit()

    def verify_login(self, user, pwd):
        cursor = self.conn.cursor()
        cursor.execute("SELECT password, name, role FROM users WHERE username=? AND active=1", (user,))
        res = cursor.fetchone()
        if res and bcrypt.checkpw(pwd.encode(), res[0].encode()):
            return {"name": res[1], "role": res[2]}
        return None

    def save_evaluation(self, data):
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO evaluations (patient_name, doctor_user, age, sex, race, creatinine, 
            glucose, systolic, bmi, tfg, stage, risk_pct, timestamp)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (data['name'], data['doctor'], data['age'], data['sex'], data['race'], 
              data['creat'], data['gluc'], data['pres'], data['bmi'], data['tfg'], 
              data['stage'], data['risk'], datetime.now().isoformat()))
        self.conn.commit()

    def get_history(self, user=None):
        query = "SELECT * FROM evaluations"
        params = ()
        if user and user != "admin":
            query += " WHERE doctor_user=?"
            params = (user,)
        return pd.read_sql_query(query, self.conn, params=params)

db = DBManager()

# =============================================
# MOTOR CLÍNICO Y MODELO
# =============================================
def calcular_tfg_ckdepi(creatinina, edad, sexo, raza):
    k = 0.7 if sexo == "Mujer" else 0.9
    alpha = -0.329 if sexo == "Mujer" else -0.411
    raza_factor = 1.159 if "Afro" in raza else 1.0
    sexo_factor = 1.018 if sexo == "Mujer" else 1.0
    
    min_k_cr = min(creatinina / k, 1)
    max_k_cr = max(creatinina / k, 1)
    tfg = 141 * (min_k_cr ** alpha) * (max_k_cr ** -1.209) * (0.993 ** edad) * sexo_factor * raza_factor
    return round(tfg, 1)

def clasificar_erc(tfg):
    if tfg >= 90: return "G1 (Normal)"
    if tfg >= 60: return "G2 (Levemente bajo)"
    if tfg >= 45: return "G3a (Moderadamente bajo)"
    if tfg >= 30: return "G3b (Severamente bajo)"
    if tfg >= 15: return "G4 (Fallo severo)"
    return "G5 (Fallo Renal)"

def predecir_riesgo(datos):
    # Intentar cargar modelo real
    try:
        if os.path.exists("modelo_erc.joblib"):
            model = joblib.load("modelo_erc.joblib")
            # Preparar features (esto debe coincidir con tu entrenamiento)
            features = [[datos['age'], datos['creat'], datos['gluc'], datos['pres'], datos['bmi']]]
            return round(model.predict_proba(features)[0][1] * 100, 1)
    except:
        pass
    
    # Motor de reglas (Fallback comercial)
    score = 10
    if datos['creat'] > 1.2: score += 25
    if datos['gluc'] > 126: score += 20
    if datos['pres'] > 140: score += 15
    if datos['bmi'] > 30: score += 10
    if datos['age'] > 65: score += 10
    return min(99.9, score + np.random.uniform(-2, 5))

# =============================================
# INTERFAZ DE USUARIO (STREAMLIT)
# =============================================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("🏥 NefroPredict RD Login")
    with st.container():
        user = st.text_input("Usuario")
        pwd = st.text_input("Contraseña", type="password")
        if st.button("Entrar", use_container_width=True):
            res = db.verify_login(user, pwd)
            if res:
                st.session_state.logged_in = True
                st.session_state.user = user
                st.session_state.name = res['name']
                st.session_state.role = res['role']
                st.rerun()
            else:
                st.error("Credenciales inválidas")
    st.stop()

# Dashboard Principal
st.sidebar.title(f"Dr. {st.session_state.name}")
menu = st.sidebar.radio("Navegación", ["Nueva Evaluación", "Historial de Pacientes", "Panel de Control"])

if st.sidebar.button("Cerrar Sesión"):
    st.session_state.logged_in = False
    st.rerun()

if menu == "Nueva Evaluación":
    st.header("📋 Evaluación Individual")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        with st.form("eval_form"):
            name = st.text_input("Nombre del Paciente")
            age = st.number_input("Edad", 18, 100, 50)
            sex = st.selectbox("Sexo", ["Hombre", "Mujer"])
            race = st.selectbox("Etnia", ["No-Afroamericano", "Afroamericano"])
            creat = st.number_input("Creatinina (mg/dL)", 0.1, 15.0, 1.0)
            gluc = st.number_input("Glucosa (mg/dL)", 50, 400, 100)
            pres = st.number_input("Presión Sistólica", 80, 220, 120)
            bmi = st.number_input("IMC", 15.0, 50.0, 25.0)
            submit = st.form_submit_button("Calcular Riesgo")

    if submit:
        tfg = calcular_tfg_ckdepi(creat, age, sex, race)
        stage = clasificar_erc(tfg)
        risk = predecir_riesgo({'age':age, 'creat':creat, 'gluc':gluc, 'pres':pres, 'bmi':bmi})
        
        # Guardar en DB
        db.save_evaluation({
            'name': name, 'doctor': st.session_state.user, 'age': age, 'sex': sex,
            'race': race, 'creat': creat, 'gluc': gluc, 'pres': pres, 
            'bmi': bmi, 'tfg': tfg, 'stage': stage, 'risk': risk
        })
        
        with col2:
            st.subheader("Resultados")
            color = DANGER if risk > 70 else WARNING if risk > 40 else SUCCESS
            label = "ALTO RIESGO" if risk > 70 else "RIESGO MODERADO" if risk > 40 else "RIESGO BAJO"
            
            st.markdown(f"""
                <div class="risk-card risk-{'high' if risk>70 else 'med' if risk>40 else 'low'}">
                    <h1 style="color:{color}; font-size: 3rem;">{risk}%</h1>
                    <p style="font-size: 1.5rem;">{label}</p>
                </div>
            """, unsafe_allow_html=True)
            
            c1, c2 = st.columns(2)
            c1.metric("TFG", f"{tfg} ml/min")
            c2.metric("Estadio", stage)
            
            # Botón para PDF (Simplicado para el ejemplo)
            st.button("Generar Reporte PDF 📄")

elif menu == "Historial de Pacientes":
    st.header("📊 Historial de Evaluaciones")
    df = db.get_history(st.session_state.user)
    if not df.empty:
        st.dataframe(df.sort_values(by="timestamp", ascending=False), use_container_width=True)
        # Gráfico de tendencia
        fig = px.scatter(df, x="timestamp", y="risk_pct", color="stage", title="Evolución de Riesgo Detectado")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No hay registros aún.")

elif menu == "Panel de Control" and st.session_state.role == "admin":
    st.header("⚙️ Administración")
    st.write("Aquí puedes gestionar usuarios y ver logs de auditoría.")
    # Implementar CRUD de usuarios aquí si es necesario
