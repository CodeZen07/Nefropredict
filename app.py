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
from datetime import datetime

# =============================================
# CONFIGURACIÓN
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
    .risk-high {background-color: #FEF2F2; border-left: 6px solid #EF4444;}
    .risk-medium {background-color: #FFFBEB; border-left: 6px solid #F97316;}
    .risk-low {background-color: #F0FDF4; border-left: 6px solid #10B981;}
</style>
""", unsafe_allow_html=True)

st.markdown("<h1 style='text-align: center;'>NefroPredict RD 2025</h1>", unsafe_allow_html=True)
st.markdown("<h3 style='text-align: center; color:#555;'>Detección temprana de ERC • República Dominicana</h3>", unsafe_allow_html=True)

# =============================================
# BASE DE DATOS
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
                "admin": {"pwd": "admin2025", "role": "admin", "id": "admin_001", "active": True},
                "dr.perez": {"pwd": "pass1", "role": "doctor", "id": "dr_001", "active": True},
                "dr.gomez": {"pwd": "pass2", "role": "doctor", "id": "dr_002", "active": True}
            },
            "patient_records": [],
            "mass_uploads": []
        }
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

    def _load(self):
        if not os.path.exists(self.path): self._init_db()
        with open(self.path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _save(self, data):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

    def get_user(self, username):
        return self._load().get("users", {}).get(username)

    def update_user(self, username, updates):
        data = self._load()
        if username in data["users"]:
            data["users"][username].update(updates)
            self._save(data)
            return True
        return False

    def delete_user(self, username):
        data = self._load()
        if username in data["users"] and data["users"][username]["role"] == "doctor":
            del data["users"][username]
            self._save(data)
            return True
        return False

    def add_patient_record(self, record):
        data = self._load()
        data["patient_records"].insert(0, record)
        self._save(data)

    def add_mass_upload(self, record):
        data = self._load()
        data["mass_uploads"].insert(0, record)
        self._save(data)

    def get_records_by_user(self, user_id):
        data = self._load()
        return [r for r in data["patient_records"] if r["user_id"] == user_id]

    def get_all_records(self):
        return self._load().get("patient_records", [])

    def get_mass_uploads_by_user(self, user_id):
        data = self._load()
        return [r for r in data["mass_uploads"] if r["user_id"] == user_id]

db = DataStore(DB_FILE)

# =============================================
# MODELO
# =============================================
@st.cache_resource
def load_model():
    try:
        return joblib.load("modelo_erc.joblib")
    except:
        st.sidebar.warning("Modo simulación activado")
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
                st.error("Credenciales incorrectas")
    st.stop()

col1, col2 = st.columns([4,1])
with col1:
    st.success(f"**{st.session_state.username.upper()}** • {st.session_state.role.upper()}")
with col2:
    if st.button("Salir"):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.rerun()

# =============================================
# FUNCIONES
# =============================================
def get_risk_level(risk):
    if risk > 70: return "MUY ALTO", "#EF4444", "Intervención urgente"
    elif risk > 40: return "ALTO", "#F97316", "Intervención media"
    else: return "MODERADO", "#10B981", "Sin intervención urgente"

def predict_risk(row):
    features = np.array([[row["edad"], row["imc"], row["presion_sistolica"], row["glucosa_ayunas"], row["creatinina"]]])
    if model:
        return round(model.predict_proba(features)[0][1] * 100, 1)
    else:
        base = 15 + (row["creatinina"]-1)*30 + max(0, row["glucosa_ayunas"]-125)*0.25
        return max(1, min(99, base + np.random.uniform(-8, 12)))

def generate_pdf_html(patient_name, risk, nivel, doctor_name, data):
    color = {"MUY ALTO": "#EF4444", "ALTO": "#F97316", "MODERADO": "#10B981"}[nivel]
    return f"""
    <!DOCTYPE html>
    <html><head><style>
        body {{font-family: Arial; margin: 40px; background: #f4f4f4;}}
        .card {{background: white; padding: 30px; border-radius: 15px; box-shadow: 0 10px 30px rgba(0,0,0,0.1); max-width: 800px; margin: auto;}}
        .header {{background: #002868; color: white; padding: 20px; text-align: center; border-radius: 15px 15px 0 0; margin: -30px -30px 20px -30px;}}
        .risk {{font-size: 4em; color: {color}; text-align: center;}}
    </style></head><body>
    <div class="card">
        <div class="header"><h1>NefroPredict RD</h1><h3>Reporte de Riesgo ERC</h3></div>
        <h2>Paciente: <strong>{patient_name}</strong></h2>
        <p><strong>Médico:</strong> {doctor_name} • <strong>Fecha:</strong> {datetime.now().strftime("%d/%m/%Y %H:%M")}</p>
        <h1 class="risk">{risk:.1f}% → {nivel}</h1>
        <p><strong>Recomendación:</strong> {get_risk_level(risk)[2]}</p>
        <hr>
        <table width="100%"><tr><td><strong>Edad:</strong> {data['edad']}</td><td><strong>IMC:</strong> {data['imc']:.1f}</td></tr>
        <tr><td><strong>Presión:</strong> {data['presion_sistolica']} mmHg</td><td><strong>Glucosa:</strong> {data['glucosa_ayunas']} mg/dL</td></tr>
        <tr><td colspan="2"><strong>Creatinina:</strong> {data['creatinina']:.2f} mg/dL</td></tr></table>
    </div>
    </body></html>
    """

# =============================================
# PESTAÑAS
# =============================================
tab1, tab2, tab3, tab4 = st.tabs(["Individual", "Carga Masiva", "Historial", "Admin"])

with tab1:
    st.subheader("Evaluación Individual")
    with st.form("individual_form"):
        nombre = st.text_input("Nombre del paciente")
        col1, col2 = st.columns(2)
        with col1:
            edad = st.number_input("Edad", 18, 120, 60)
            imc = st.number_input("IMC", 10.0, 60.0, 28.0, 0.1)
            glucosa = st.number_input("Glucosa ayunas", 50, 500, 120)
        with col2:
            presion = st.number_input("Presión sistólica", 80, 250, 140)
            creatinina = st.number_input("Creatinina", 0.1, 10.0, 1.5, 0.01)
        submitted = st.form_submit_button("Calcular Riesgo")
        if submitted and nombre:
            row = {"edad": edad, "imc": imc, "presion_sistolica": presion, "glucosa_ayunas": glucosa, "creatinina": creatinina}
            risk = predict_risk(row)
            nivel, color, reco = get_risk_level(risk)
            record = {"nombre_paciente": nombre, "user_id": st.session_state.user_id, "usuario": st.session_state.username,
                      "timestamp": datetime.now().isoformat(), "risk": risk, "nivel": nivel, **row}
            db.add_patient_record(record)

            st.markdown(f"<h2 style='color:{color}; text-align:center'>{nivel} • {risk:.1f}%</h2>", unsafe_allow_html=True)
            if st.button("Descargar PDF"):
                html = generate_pdf_html(nombre, risk, nivel, st.session_state.username, row)
                st.download_button("Descargar Reporte PDF", html, f"Reporte_{nombre.replace(' ', '_')}.html", "text/html")

with tab2:
    st.subheader("Carga Masiva (Excel)")
    uploaded = st.file_uploader("Subir archivo Excel", type=["xlsx", "csv"])
    if uploaded:
        df = pd.read_excel(uploaded) if uploaded.name.endswith('.xlsx') else pd.read_csv(uploaded)
        required = ["nombre_paciente", "edad", "imc", "presion_sistolica", "glucosa_ayunas", "creatinina"]
        if all(c in df.columns for c in required):
            df["risk"] = df.apply(predict_risk, axis=1)
            df["nivel"], df["color"], df["recomendacion"] = zip(*df["risk"].apply(lambda x: get_risk_level(x)))
            urgente = len(df[df["nivel"] == "MUY ALTO"])
            media = len(df[df["nivel"] == "ALTO"])
            baja = len(df) - urgente - media

            col1, col2, col3 = st.columns(3)
            col1.metric("Intervención Urgente", urgente, delta="Prioridad 1")
            col2.metric("Intervención Media", media)
            col3.metric("Sin Urgencia", baja)

            st.dataframe(df[["nombre_paciente", "risk", "nivel", "recomendacion"]], use_container_width=True)
            csv = df.to_csv(index=False).encode()
            st.download_button("Descargar Resultados", csv, "resultados_grupal.csv", "text/csv")

            db.add_mass_upload({"user_id": st.session_state.user_id, "timestamp": datetime.now().isoformat(),
                                "filename": uploaded.name, "total": len(df), "urgente": urgente})
        else:
            st.error("Faltan columnas obligatorias")

# =============================================
# ADMIN PANEL
# =============================================
if st.session_state.role == "admin":
    with tab4:
        st.markdown("### Panel Administrativo")
        tab_a, tab_b, tab_c = st.tabs(["Doctores", "Estadísticas", "Crear Usuario"])

        with tab_a:
            users = db._load()["users"]
            doctores = {k: v for k, v in users.items() if v["role"] == "doctor"}
            df_docs = pd.DataFrame([
                {"Usuario": k, "Contraseña": v["pwd"], "Estado": "Activo" if v.get("active", True) else "Inactivo"}
                for k, v in doctores.items()
            ])
            st.dataframe(df_docs, use_container_width=True)

            with st.expander("Modificar Doctor"):
                doc = st.selectbox("Seleccionar", list(doctores.keys()))
                nueva_pwd = st.text_input("Nueva contraseña", type="password")
                if st.button("Cambiar contraseña"):
                    db.update_user(doc, {"pwd": nueva_pwd})
                    st.success("Contraseña actualizada")
                if st.button("Eliminar doctor", type="primary"):
                    db.delete_user(doc)
                    st.success("Eliminado")
                    st.rerun()

        with tab_b:
            uploads = db._load().get("mass_uploads", [])
            df_usage = pd.DataFrame(uploads)
            if not df_usage.empty:
                ranking = df_usage["user_id"].value_counts().reset_index()
                ranking.columns = ["user_id", "cargas"]
                ranking = ranking.merge(pd.DataFrame([(u["id"], k) for k, u in users.items() if u["role"]=="doctor"],
                                                    columns=["user_id", "usuario"]), on="user_id", how="left")
                st.bar_chart(ranking.set_index("usuario")["cargas"])

        with tab_c:
            with st.form("nuevo_doc"):
                nuevo = st.text_input("Usuario nuevo")
                pwd = st.text_input("Contraseña", type="password")
                if st.form_submit_button("Crear"):
                    if db.get_user(nuevo):
                        st.error("Ya existe")
                    else:
                        db._load()["users"][nuevo] = {"pwd": pwd, "role": "doctor", "id": f"dr_{int(time.time())}", "active": True}
                        db._save(db._load())
                        st.success("Creado!")
                        st.rerun()

st.caption("NefroPredict RD © 2025 • Confidencialidad garantizada • Solo admin ve todo")
