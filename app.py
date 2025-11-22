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
    .stButton > button {background: #002868; color: white; border-radius: 12px; padding: 0.7rem 1.5rem; font-weight:600;}
    .risk-high {background-color: #FFE5E5; border-left: 6px solid #CE1126; padding: 10px; border-radius: 8px;}
    .risk-medium {background-color: #FFF4E5; border-left: 6px solid #FFC400; padding: 10px; border-radius: 8px;}
    .risk-low {background-color: #E5F7E5; border-left: 6px solid #4CAF50; padding: 10px; border-radius: 8px;}
    .metric-card {background: white; padding: 1.5rem; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); text-align: center;}
</style>
""", unsafe_allow_html=True)

st.markdown("<h1 style='text-align: center;'>NefroPredict RD 2025</h1>", unsafe_allow_html=True)
st.markdown("<h3 style='text-align: center; color:#555;'>Detección temprana de enfermedad renal crónica • República Dominicana</h3>", unsafe_allow_html=True)

# =============================================
# BASE DE DATOS SIMULADA
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
                "admin": {"pwd": "admin", "role": "admin", "id": "admin_001", "active": True, "name": "Administrador"},
                "dr.perez": {"pwd": "pass1", "role": "doctor", "id": "dr_001", "active": True, "name": "Dr. Pérez"},
                "dr.gomez": {"pwd": "pass2", "role": "doctor", "id": "dr_002", "active": True, "name": "Dr. Gómez"}
            },
            "patient_records": [],
            "file_uploads": []  # Historial de cargas masivas
        }
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

    def _load(self):
        if not os.path.exists(self.path):
            self._init_db()
        with open(self.path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _save(self, data):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

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

    def get_patient_records_by_doctor(self, user_id):
        data = self._load()
        return [r for r in data["patient_records"] if r["user_id"] == user_id]

    def get_all_patient_records(self):
        return self._load()["patient_records"]

    def get_file_uploads(self):
        return self._load().get("file_uploads", [])

    def add_file_upload(self, record):
        data = self._load()
        data["file_uploads"].insert(0, record)
        self._save(data)

db = DataStore(DB_FILE)

# =============================================
# CARGA DEL MODELO
# =============================================
@st.cache_resource
def load_model():
    try:
        return joblib.load("modelo_erc.joblib")
    except:
        st.sidebar.warning("Modelo no encontrado → Modo simulación")
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
        user = st.text_input("Usuario").lower().strip()
        pwd = st.text_input("Contraseña", type="password")
        if st.form_submit_button("Entrar"):
            u = db.get_user(user)
            if u and u["pwd"] == pwd and u.get("active", True):
                st.session_state.logged_in = True
                st.session_state.username = user
                st.session_state.role = u["role"]
                st.session_state.user_id = u["id"]
                st.session_state.doctor_name = u.get("name", user)
                st.success("¡Bienvenido!")
                time.sleep(0.5)
                st.rerun()
            else:
                st.error("Credenciales incorrectas o cuenta inactiva")
    st.stop()

# Header con logout
col1, col2 = st.columns([4,1])
with col1:
    st.success(f"Doctor: **{st.session_state.doctor_name}** • Usuario: **{st.session_state.username}**")
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
    if risk > 70: return "MUY ALTO", "#CE1126", "Intervención URGENTE"
    elif risk > 40: return "ALTO", "#FFC400", "Intervención Media"
    else: return "MODERADO", "#4CAF50", "Seguimiento Rutinario"

def predict_risk(row):
    features = np.array([[row["edad"], row["imc"], row["presion_sistolica"], row["glucosa_ayunas"], row["creatinina"]]])
    if model:
        prob = model.predict_proba(features)[0][1]
        return round(prob * 100, 1)
    else:
        base = 15 + (row["creatinina"] - 1)*30 + max(0, row["glucosa_ayunas"]-126)*0.25 + max(0, row["presion_sistolica"]-140)*0.2
        return max(1.0, min(99.9, base + np.random.uniform(-8, 12)))

def generate_pdf_report(patient_data, risk, nivel, doctor_name):
    now = datetime.now().strftime("%d/%m/%Y %H:%M")
    html = f"""
    <!DOCTYPE html>
    <html><head><meta charset="utf-8">
    <style>
        body {{font-family: Arial; margin: 40px; background: #f9f9f9;}}
        .container {{background: white; padding: 30px; border-radius: 15px; box-shadow: 0 0 20px rgba(0,0,0,0.1); max-width: 800px; margin: auto;}}
        .header {{background: #002868; color: white; padding: 20px; text-align: center; border-radius: 12px;}}
        .risk {{font-size: 4em; color: {('#CE1126' if risk>70 else '#FFC400' if risk>40 else '#4CAF50')}}}}
        table {{width: 100%; border-collapse: collapse; margin: 20px 0;}}
        th, td {{border: 1px solid #ddd; padding: 12px; text-align: left;}}
        th {{background: #f0f0f0;}}
    </style></head>
    <body>
    <div class="container">
        <div class="header"><h1>NefroPredict RD</h1><h3>Reporte de Riesgo ERC</h3></div>
        <p><strong>Paciente:</strong> {patient_data['nombre_paciente']}</p>
        <p><strong>Médico:</strong> {doctor_name}</p>
        <p><strong>Fecha:</strong> {now}</p>
        <h2 style="text-align:center; color:{('#CE1126' if risk>70 else '#FFC400' if risk>40 else '#4CAF50')}">
            Riesgo: {risk:.1f}% → {nivel}
        </h2>
        <table>
            <tr><th>Parámetro</th><th>Valor</th></tr>
            <tr><td>Edad</td><td>{patient_data['edad']}</td></tr>
            <tr><td>IMC</td><td>{patient_data['imc']:.1f}</td></tr>
            <tr><td>Presión Sistólica</td><td>{patient_data['presion_sistolica']}</td></tr>
            <tr><td>Glucosa Ayunas</td><td>{patient_data['glucosa_ayunas']}</td></tr>
            <tr><td>Creatinina</td><td>{patient_data['creatinina']:.2f}</td></tr>
        </table>
        <h3>Recomendación: {get_risk_level(risk)[2]}</h3>
    </div>
    </body></html>
    """
    return html

# =============================================
# PESTAÑAS
# =============================================
if st.session_state.role == "admin":
    tabs = st.tabs(["Predicción Individual", "Carga Masiva", "Historial Clínico", "Admin: Usuarios", "Admin: Estadísticas"])
else:
    tabs = st.tabs(["Predicción Individual", "Carga Masiva", "Historial Clínico"])

# === INDIVIDUAL ===
with tabs[0]:
    st.subheader("Evaluación Individual")
    with st.form("form_individual"):
        nombre = st.text_input("Nombre del paciente", "Juan Pérez")
        c1, c2 = st.columns(2)
        with c1:
            edad = st.number_input("Edad", 18, 120, 60)
            imc = st.number_input("IMC", 10.0, 60.0, 28.0, 0.1)
            glucosa = st.number_input("Glucosa ayunas", 50, 500, 140)
        with c2:
            presion = st.number_input("Presión sistólica", 80, 250, 150)
            creat = st.number_input("Creatinina", 0.1, 10.0, 1.5, 0.01)

        if st.form_submit_button("Calcular Riesgo"):
            row = {"edad": edad, "imc": imc, "presion_sistolica": presion, "glucosa_ayunas": glucosa, "creatinina": creat}
            risk = predict_risk(row)
            nivel, color, reco = get_risk_level(risk)

            record = {
                "nombre_paciente": nombre, "user_id": st.session_state.user_id,
                "doctor_name": st.session_state.doctor_name,
                "usuario": st.session_state.username, "timestamp": datetime.now().isoformat(),
                **row, "risk": risk, "nivel": nivel
            }
            db.add_patient_record(record)
            st.session_state.last_result = record
            st.rerun()

    if "last_result" in st.session_state:
        r = st.session_state.last_result
        nivel, color, _ = get_risk_level(r["risk"])
        st.markdown(f"<div style='text-align:center; padding:30px; background:#f9f9f9; border-radius:16px; border: 5px solid {color}'>"
                    f"<h2 style='color:{color}'>{nivel}</h2>"
                    f"<h1 style='font-size:5rem; color:{color}'>{r['risk']:.1f}%</h1>"
                    f"<p><strong>Recomendación:</strong> {get_risk_level(r['risk'])[2]}</p></div>", unsafe_allow_html=True)

        if st.button("Descargar Reporte PDF"):
            pdf_html = generate_pdf_report(r, r["risk"], nivel, st.session_state.doctor_name)
            st.download_button("Confirmar descarga PDF", pdf_html, f"Reporte_{r['nombre_paciente'].replace(' ', '_')}.html", "text/html")

# === CARGA MASIVA ===
with tabs[1]:
    st.subheader("Carga Masiva de Pacientes")
    st.download_button("Descargar Plantilla Excel", 
                       data=pd.DataFrame({"nombre_paciente": ["Juan Pérez"], "edad": [60], "imc": [30.0], 
                                        "presion_sistolica": [150], "glucosa_ayunas": [180], "creatinina": [1.8]}).to_csv(index=False).encode(),
                       file_name="plantilla_nefropredict.csv", mime="text/csv")

    uploaded = st.file_uploader("Subir archivo Excel o CSV", type=["xlsx", "csv"])
    if uploaded:
        df = pd.read_excel(uploaded) if uploaded.name.endswith("xlsx") else pd.read_csv(uploaded)
        required = ["nombre_paciente", "edad", "imc", "presion_sistolica", "glucosa_ayunas", "creatinina"]
        if not all(c in df.columns for c in required):
            st.error(f"Faltan columnas: {set(required) - set(df.columns)}")
        else:
            df["risk"] = df.apply(predict_risk, axis=1)
            df["nivel"] = df["risk"].apply(lambda x: get_risk_level(x)[0])
            df["recomendacion"] = df["risk"].apply(lambda x: get_risk_level(x)[2])

            # Guardar cada paciente
            for _, row in df.iterrows():
                record = {
                    "nombre_paciente": row["nombre_paciente"],
                    "user_id": st.session_state.user_id,
                    "doctor_name": st.session_state.doctor_name,
                    "usuario": st.session_state.username,
                    "timestamp": datetime.now().isoformat(),
                    "edad": int(row["edad"]), "imc": float(row["imc"]),
                    "presion_sistolica": int(row["presion_sistolica"]),
                    "glucosa_ayunas": int(row["glucosa_ayunas"]),
                    "creatinina": float(row["creatinina"]),
                    "risk": float(row["risk"]), "nivel": row["nivel"]
                }
                db.add_patient_record(record)

            # Resumen
            urgente = len(df[df["risk"] > 70])
            media = len(df[(df["risk"] > 40) & (df["risk"] <= 70)])
            rutinario = len(df[df["risk"] <= 40])

            col1, col2, col3 = st.columns(3)
            col1.metric("Intervención Urgente", urgente, delta="Prioridad máxima")
            col2.metric("Intervención Media", media)
            col3.metric("Seguimiento Rutinario", rutinario)

            st.dataframe(df[["nombre_paciente", "risk", "nivel", "recomendacion"]].sort_values("risk", ascending=False), use_container_width=True)

            db.add_file_upload({
                "user_id": st.session_state.user_id,
                "doctor_name": st.session_state.doctor_name,
                "timestamp": datetime.now().isoformat(),
                "filename": uploaded.name,
                "total": len(df),
                "urgente": urgente
            })

# === HISTORIAL ===
with tabs[2]:
    st.subheader("Historial Clínico")
    records = db.get_patient_records_by_doctor(st.session_state.user_id) if st.session_state.role == "doctor" else db.get_all_patient_records()
    if records:
        df_hist = pd.DataFrame(records)
        pacientes = df_hist["nombre_paciente"].unique()
        selected = st.selectbox("Paciente", options=pacientes)
        if selected:
            df_p = df_hist[df_hist["nombre_paciente"] == selected].sort_values("timestamp", ascending=False)
            st.dataframe(df_p[["timestamp", "risk", "nivel", "creatinina"]], use_container_width=True)

            chart = alt.Chart(df_p).mark_line(point=True).encode(
                x="timestamp:T", y="risk:Q", tooltip=["timestamp", "risk", "nivel"]
            ).properties(title=f"Evolución del riesgo - {selected}")
            st.altair_chart(chart, use_container_width=True)
    else:
        st.info("No hay registros aún")

# === ADMIN: GESTIÓN DE USUARIOS ===
if st.session_state.role == "admin" and len(tabs) > 3:
    with tabs[3]:
        st.subheader("Gestión de Doctores")
        with st.expander("Crear Nuevo Doctor"):
            with st.form("new_doc"):
                new_user = st.text_input("Usuario").lower().strip()
                new_pwd = st.text_input("Contraseña", type="password")
                new_name = st.text_input("Nombre completo")
                if st.form_submit_button("Crear"):
                    if db.get_user(new_user):
                        st.error("Usuario ya existe")
                    else:
                        data = db._load()
                        data["users"][new_user] = {
                            "pwd": new_pwd, "role": "doctor", "id": f"dr_{int(time.time())}",
                            "active": True, "name": new_name
                        }
                        db._save(data)
                        st.success("Doctor creado")
                        st.rerun()

        doctores = {k: v for k, v in db._load()["users"].items() if v["role"] == "doctor"}
        for user, data in doctores.items():
            with st.expander(f"{data['name']} ({user}) - {'Activo' if data['active'] else 'Inactivo'}"):
                col1, col2 = st.columns(2)
                with col1:
                    new_pwd = st.text_input(f"Nueva contraseña para {user}", type="password", key=f"pwd_{user}")
                    if st.button("Cambiar contraseña", key=f"chg_{user}"):
                        db.update_user(user, {"pwd": new_pwd})
                        st.success("Contraseña actualizada")
                with col2:
                    if st.button("Eliminar", key=f"del_{user}", type="primary"):
                        db.delete_user(user)
                        st.success("Eliminado")
                        st.rerun()
                    st.checkbox("Activo", value=data["active"], key=f"act_{user}",
                                on_change=lambda u=user, v=not data["active"]: db.update_user(u, {"active": v}))

    # === ADMIN: ESTADÍSTICAS ===
    with tabs[4]:
        st.subheader("Doctores Más Activos")
        uploads = db.get_file_uploads()
        if uploads:
            df_up = pd.DataFrame(uploads)
            top = df_up["doctor_name"].value_counts().head(10)
            st.bar_chart(top)
        st.info("Estadísticas en desarrollo")

st.caption("NefroPredict RD © 2025 • Sistema completo con confidencialidad y gestión avanzada")
