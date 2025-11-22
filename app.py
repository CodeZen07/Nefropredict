import pandas as pd
import numpy as np
import time
import joblib
import json
import os
import io
import streamlit as st
import altair as alt
import streamlit.components.v1 as components  # ← Import corregido aquí

# =============================================
# CONFIGURACIÓN + ESTILOS KHAZAD (NARANJA + AZUL OSCURO)
# =============================================
st.set_page_config(page_title="KHAZAD • NefroPredict RD", page_icon="Kidney", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');
    html, body, [class*="css"] {font-family: 'Inter', sans-serif;}
    .stApp {background-color: #0F172A; color: #F1F5F9;}
    h1, h2, h3, h4 {color: #F97316 !important; font-weight: 800;}
    .stButton > button {
        background: linear-gradient(135deg, #F97316, #EA580C) !important;
        color: white !important;
        border-radius: 12px !important;
        font-weight: 600 !important;
        padding: 0.7rem 1.5rem !important;
        box-shadow: 0 4px 15px rgba(249, 115, 22, 0.4) !important;
    }
    .stButton > button:hover {transform: translateY(-2px);}
    [data-testid="stMetricValue"] {color: #F97316 !important; font-size: 2rem !important;}
    .risk-gauge-container {
        background: #1E293B; padding: 2rem; border-radius: 16px; text-align: center;
        border: 2px solid #334155; box-shadow: 0 10px 30px rgba(0,0,0,0.5);
    }
    .risk-gauge-bar {
        height: 40px; border-radius: 20px;
        background: linear-gradient(to right, #10B981 0%, #FACC15 40%, #F97316 70%, #EF4444 100%);
        position: relative; margin: 20px 0;
    }
    .risk-gauge-marker {
        position: absolute; top: -20px; left: var(--pos); transform: translateX(-50%);
        width: 12px; height: 80px; background: #FACC15; border-radius: 6px;
        box-shadow: 0 0 20px #FACC15; border: 3px solid #0F172A;
    }
</style>
""", unsafe_allow_html=True)

# Header KHAZAD
st.markdown("""
<div style="background: linear-gradient(135deg, #F97316, #EA580C); padding: 2rem; border-radius: 16px; text-align: center; margin-bottom: 2rem; box-shadow: 0 10px 30px rgba(249,115,22,0.3);">
    <h1 style="margin:0; color:white; font-size:3.5rem;">KHAZAD • NefroPredict RD 2025</h1>
    <p style="margin:5px 0 0; font-size:1.4rem; color:#FFEDD5;">Detección temprana de ERC • República Dominicana</p>
</div>
""", unsafe_allow_html=True)

# =============================================
# BASE DE DATOS SIMULADA
# =============================================
DB_FILE_PATH = "nefro_db.json"

class DataStore:
    def __init__(self, file_path):
        self.file_path = file_path
        self._initialize_db()

    def _initialize_db(self):
        if not os.path.exists(self.file_path):
            initial_data = {
                "users": {
                    "admin": {"pwd": "admin", "role": "admin", "id": "admin_nefro", "active": True},
                    "dr.perez": {"pwd": "pass1", "role": "doctor", "id": "dr_perez_uid_001", "active": True},
                    "dr.gomez": {"pwd": "pass2", "role": "doctor", "id": "dr_gomez_uid_002", "active": True},
                },
                "file_history": [],
                "patient_records": [
                    {"nombre_paciente": "Maria Almonte", "user_id": "dr_perez_uid_001", "usuario": "dr.perez",
                     "timestamp": "2024-10-01 10:00:00", "edad": 60, "imc": 30.1, "presion_sistolica": 160,
                     "creatinina": 1.9, "glucosa_ayunas": 190, "risk": 78.0, "nivel": "MUY ALTO", "color": "#EF4444"},
                    {"nombre_paciente": "Maria Almonte", "user_id": "dr_perez_uid_001", "usuario": "dr.perez",
                     "timestamp": "2025-01-15 11:30:00", "edad": 60, "imc": 28.5, "presion_sistolica": 140,
                     "creatinina": 1.5, "glucosa_ayunas": 140, "risk": 55.0, "nivel": "ALTO", "color": "#F97316"},
                    {"nombre_paciente": "Juan Perez", "user_id": "dr_gomez_uid_002", "usuario": "dr.gomez",
                     "timestamp": "2025-05-02 12:00:00", "edad": 45, "imc": 24.0, "presion_sistolica": 120,
                     "creatinina": 1.0, "glucosa_ayunas": 95, "risk": 20.0, "nivel": "MODERADO", "color": "#10B981"}
                ]
            }
            self._write_db(initial_data)

    def _read_db(self):
        if not os.path.exists(self.file_path): self._initialize_db()
        with open(self.file_path, 'r') as f:
            return json.load(f)

    def _write_db(self, data):
        with open(self.file_path, 'w') as f:
            json.dump(data, f, indent=4)

    def get_user(self, username): return self._read_db()['users'].get(username)
    def get_all_users(self): return self._read_db()['users']
    def create_user(self, username, user_data):
        db = self._read_db()
        db['users'][username] = user_data
        self._write_db(db)
    def def update_user(self, username, updates):
        db = self._read_db()
        if username in db['users']:
            db['users'][username].update(updates)
            self._write_db(db)
            return True
        return False

    def get_file_history(self): return self._read_db().get('file_history', [])
    def add_file_record(self, record):
        db = self._read_db()
        db['file_history'].insert(0, record)
        self._write_db(db)

    def add_patient_record(self, record):
        db = self._read_db()
        db['patient_records'].insert(0, record)
        self._write_db(db)

    def get_patient_records(self, patient_name):
        db = self._read_db()
        return sorted([
            r for r in db.get('patient_records', [])
            if r.get('nombre_paciente', '').lower() == patient_name.lower()
        ], key=lambda x: x['timestamp'], reverse=True)

    def get_all_patient_names(self):
        db = self._read_db()
        names = [r.get('nombre_paciente') for r in db.get('patient_records', []) if r.get('nombre_paciente')]
        return sorted(list(set(names)))

db_store = DataStore(DB_FILE_PATH)

# =============================================
# CARGA DEL MODELO
# =============================================
@st.cache_resource
def load_model(path):
    try:
        model = joblib.load(path)
        st.sidebar.success("Modelo ML cargado")
        return model
    except:
        st.sidebar.warning("Modelo no encontrado → Modo simulación")
        return None

nefro_model = load_model('modelo_erc.joblib')
model_loaded = nefro_model is not None

# =============================================
# SESSION STATE + LOGIN
# =============================================
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = None
    st.session_state.user_role = None
    st.session_state.user_id = None
    st.session_state.last_individual_report = None
    st.session_state.last_mass_df = None

def check_login():
    if not st.session_state.logged_in:
        st.markdown("### Iniciar Sesión")
        with st.form("login_form"):
            user = st.text_input("Usuario").lower()
            pwd = st.text_input("Contraseña", type="password")
            if st.form_submit_button("Acceder"):
                user_data = db_store.get_user(user)
                if user_data and user_data['pwd'] == pwd and user_data.get('active', True):
                    st.session_state.update({
                        'logged_in': True, 'username': user,
                        'user_role': user_data['role'], 'user_id': user_data['id']
                    })
                    st.success("Acceso concedido")
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.error("Credenciales incorrectas o usuario inactivo")
        st.stop()

check_login()

# Logout + Info
col1, col2 = st.columns([4,1])
with col1:
    st.success(f"Usuario: **{st.session_state.username.upper()}** | Rol: **{st.session_state.user_role.upper()}**")
with col2:
    if st.button("Cerrar Sesión"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

st.markdown("---")

# =============================================
# FUNCIONES CLAVE
# =============================================
def get_risk_level(risk):
    if risk > 70: return "MUY ALTO", "#EF4444", "Referir URGENTE a nefrólogo"
    elif risk > 40: return "ALTO", "#F97316", "Control estricto cada 3 meses"
    else: return "MODERADO", "#10B981", "Control anual"

def predict_risk(data_series):
    data = data_series[['edad','imc','presion_sistolica','glucosa_ayunas','creatinina']].to_frame().T
    if model_loaded:
        prob = nefro_model.predict_proba(data)[:,1][0]
        return round(prob * 100, 1)
    else:
        base = 15 + (data['creatinina'].iloc[0]-1)*20 + (data['glucosa_ayunas'].iloc[0]-100)*0.2
        return max(1, min(99.9, base + np.random.uniform(-8,12)))

def generate_individual_report_html(patient_data, risk, doctor, explanation):
    nivel, color, rec = get_risk_level(risk)
    now = time.strftime("%Y-%m-%d %H:%M")
    rows = ""
    for k, v in explanation.items():
        arrow = "Up" if v > 0 else "Down"
        rows += f"<tr><td>{k}</td><td style='color:{'#EF4444' if v>0 else '#10B981'}'>{arrow} {abs(v*100):.1f}%</td></tr>"
    return f"""
    <!DOCTYPE html><html><head><style>
        body {{font-family:Arial; margin:40px; background:#f4f4f4;}}
        .container {{background:white; padding:30px; border-radius:12px; box-shadow:0 0 20px rgba(0,0,0,0.1);}}
        .header {{background:#F97316; color:white; padding:20px; text-align:center; border-radius:12px;}}
        .risk {{font-size:4em; color:{color};}}
    </style></head><body>
    <div class="container">
        <div class="header"><h1>NefroPredict RD</h1><h3>Reporte de Riesgo ERC</h3></div>
        <p><strong>Paciente:</strong> {patient_data['nombre_paciente']} | <strong>Médico:</strong> {doctor.upper()}</p>
        <h2 style="color:{color};">Riesgo: {risk:.1f}% → {nivel}</h2>
        <p><strong>Recomendación:</strong> {rec}</p>
        <h3>Datos</h3>
        <table border="1" cellpadding="8"><tr><th>Parámetro</th><th>Valor</th></tr>
        <tr><td>Edad</td><td>{patient_data['edad']}</td></tr>
        <tr><td>IMC</td><td>{patient_data['imc']:.1f}</td></tr>
        <tr><td>Presión Sistólica</td><td>{patient_data['presion_sistolica']}</td></tr>
        <tr><td>Glucosa</td><td>{patient_data['glucosa_ayunas']}</td></tr>
        <tr><td>Creatinina</td><td>{patient_data['creatinina']:.2f}</td></tr>
        </table>
        <h3>Contribución de Factores</h3>
        <table border="1" cellpadding="8">{rows}</table>
    </div>
    </body></html>
    """

def get_excel_template():
    df = pd.DataFrame({
        'nombre_paciente': ['P-1001', 'P-1002', 'P-1003'],
        'edad': [65, 48, 72],
        'imc': [32.5, 24.1, 28.9],
        'presion_sistolica': [150, 125, 140],
        'glucosa_ayunas': [180, 95, 115],
        'creatinina': [1.8, 0.9, 1.5],
    })
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Plantilla_ERC')
    return output.getvalue()

# =============================================
# INTERFAZ PRINCIPAL
# =============================================
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Predicción Individual",
    "Carga Masiva",
    "Historial Clínico",
    "eGFR",
    "Mi Historial"
])

with tab1:
    st.markdown("#### Predicción Individual")
    with st.form("form_individual"):
        nombre = st.text_input("Nombre Completo del Paciente", "María Almonte")
        c1, c2 = st.columns(2)
        with c1:
            edad = st.number_input("Edad", 18, 120, 60)
            imc = st.number_input("IMCm", 15.0, 50.0, 30.0, 0.1)
            glucosa = st.number_input("Glucosa Ayunas", 50, 500, 180)
        with c2:
            presion = st.number_input("Presión Sistólica", 90, 250, 160)
            creat = st.number_input("Creatinina", 0.1, 10.0, 1.9, 0.01)

        if st.form_submit_button("Calcular Riesgo"):
            if not nombre.strip():
                st.error("Ingresa el nombre del paciente")
            else:
                data = pd.Series({
                    'nombre_paciente': nombre, 'edad': edad, 'imc': imc,
                    'presion_sistolica': presion, 'glucosa_ayunas': glucosa, 'creatinina': creat
                })
                risk = predict_risk(data)
                explanation = generate_explanation_data(data)  # ← Usa tu función original
                html = generate_individual_report_html(data.to_dict(), risk, st.session_state.username, explanation)

                record = {**data.to_dict(), "risk": risk, "nivel": get_risk_level(risk)[0],
                          "user_id": st.session_state.user_id, "usuario": st.session_state.username,
                          "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"), "html_report": html}
                db_store.add_patient_record(record)

                st.session_state.last_individual_report = {"risk": risk, "html_report": html, "data": data.to_dict()}
                st.rerun()

    if st.session_state.last_individual_report:
        r = st.session_state.last_individual_report
        nivel, color, rec = get_risk_level(r['risk'])
        st.markdown(f"""
        <div class="risk-gauge-container">
            <h2 style="color:{color};">{nivel}</h2>
            <h1 style="font-size:4rem; color:#FACC15;">{r['risk']:.1f}%</h1>
            <div class="risk-gauge-bar"><div class="risk-gauge-marker" style="--pos: {r['risk']}%;"></div></div>
            <p>{rec}</p>
        </div>
        """, unsafe_allow_html=True)

        if st.button("Generar PDF Imprimible"):
            js = f"""
            <script>
                var win = window.open('', '_blank');
                win.document.write(`{r['html_report'].replace('`', '\\`')}`);
                win.document.close();
            </script>
            """
            components.html(js, height=0, width=0)
            st.success("Reporte abierto en nueva pestaña → Imprimir → Guardar como PDF")

# (El resto de pestañas funcionan igual — puedes copiar tu código original aquí)

st.caption("Tecnología al servicio de la salud dominicana")
