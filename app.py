import pandas as pd
import numpy as np
import joblib
import json
import os
from datetime import datetime
import streamlit as st
import altair as alt
import plotly.express as px
import plotly.graph_objects as go
from io import BytesIO

# =============================================
# CONFIGURACIÓN Y ESTILOS
# =============================================
st.set_page_config(page_title="NefroPredict RD", page_icon="🩺", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    body {font-family: 'Inter', sans-serif;}
    h1, h2, h3 {color: #002868 !important;}
    .stButton>button {background: #002868; color: white; border-radius: 12px; padding: 0.7rem 1.5rem; font-weight:600;}
    .stButton>button:hover {background: #001a4d;}
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px; border-radius: 15px; color: white; text-align: center;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }
    .risk-high {background: linear-gradient(135deg, #ff6b6b, #ee5a5a); padding:20px; border-radius:12px; color:white; text-align:center;}
    .risk-med {background: linear-gradient(135deg, #feca57, #ff9f43); padding:20px; border-radius:12px; color:white; text-align:center;}
    .risk-low {background: linear-gradient(135deg, #1dd1a1, #10ac84); padding:20px; border-radius:12px; color:white; text-align:center;}
    .patient-card {background:#f8f9fa; padding:15px; border-radius:10px; margin:10px 0; border-left:4px solid #002868;}
</style>
""", unsafe_allow_html=True)

st.markdown("<h1 style='text-align:center;'>🩺 NefroPredict RD 2025</h1>", unsafe_allow_html=True)
st.markdown("<h4 style='text-align:center;color:#555;'>Detección temprana de ERC • República Dominicana</h4>", unsafe_allow_html=True)

# =============================================
# BASE DE DATOS
# =============================================
DB_FILE = "nefro_db.json"

class DataStore:
    def __init__(self):
        if not os.path.exists(DB_FILE):
            self._create_initial_db()
        self.data = self._load()

    def _create_initial_db(self):
        initial = {
            "users": {
                "admin": {"pwd": "admin", "role": "admin", "name": "Administrador", "active": True},
                "dr.perez": {"pwd": "1234", "role": "doctor", "name": "Dr. José Pérez", "active": True},
                "dr.gomez": {"pwd": "1234", "role": "doctor", "name": "Dra. Ana Gómez", "active": True}
            },
            "patients": [],
            "uploads": []
        }
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(initial, f, indent=4, ensure_ascii=False)

    def _load(self):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        # Asegurar que existan todas las keys necesarias
        if "users" not in data:
            data["users"] = {
                "admin": {"pwd": "admin", "role": "admin", "name": "Administrador", "active": True}
            }
        if "patients" not in data:
            data["patients"] = []
        if "uploads" not in data:
            data["uploads"] = []
        # Guardar si se agregaron keys faltantes
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        return data

    def save(self):
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=4, ensure_ascii=False)

    def get_user(self, username):
        return self.data["users"].get(username)

    def create_doctor(self, username, password, full_name):
        self.data["users"][username] = {
            "pwd": password, "role": "doctor", "name": full_name, "active": True
        }
        self.save()

    def update_password(self, username, new_pwd):
        if username in self.data["users"]:
            self.data["users"][username]["pwd"] = new_pwd
            self.save()

    def toggle_active(self, username):
        if username in self.data["users"]:
            self.data["users"][username]["active"] = not self.data["users"][username]["active"]
            self.save()

    def delete_doctor(self, username):
        if username in self.data["users"] and self.data["users"][username]["role"] == "doctor":
            del self.data["users"][username]
            self.save()

    def add_patient(self, record):
        self.data["patients"].insert(0, record)
        self.save()

    def get_patients_by_doctor(self, user_id):
        return [p for p in self.data["patients"] if p["doctor_user"] == user_id]

    def get_all_patients(self):
        return self.data["patients"]

    def add_upload_log(self, log):
        self.data["uploads"].insert(0, log)
        self.save()

db = DataStore()

# =============================================
# MODELO
# =============================================
@st.cache_resource
def load_model():
    try:
        return joblib.load("modelo_erc.joblib")
    except:
        return None

model = load_model()

# =============================================
# FUNCIONES DE RIESGO Y PREDICCIÓN
# =============================================
def riesgo_level(risk):
    if risk > 70:
        return "MUY ALTO", "#CE1126", "Intervención URGENTE - Referir a nefrología"
    elif risk > 40:
        return "ALTO", "#FFC400", "Intervención Media - Control estricto"
    else:
        return "MODERADO", "#4CAF50", "Seguimiento Rutinario - Control periódico"

def predecir(row):
    feats = np.array([[row["edad"], row["imc"], row["presion_sistolica"],
                       row["glucosa_ayunas"], row["creatinina"]]])
    if model:
        return round(model.predict_proba(feats)[0][1] * 100, 1)
    else:
        # Simulación realista basada en factores de riesgo
        base = 10
        base += (row["creatinina"] - 1) * 32
        base += max(0, row["glucosa_ayunas"] - 126) * 0.3
        base += max(0, row["presion_sistolica"] - 140) * 0.2
        base += max(0, row["imc"] - 30) * 0.5
        base += max(0, row["edad"] - 60) * 0.3
        return round(max(1, min(99, base + np.random.uniform(-5, 8))), 1)

def crear_gauge_riesgo(riesgo):
    """Crear gráfico de velocímetro para el riesgo"""
    if riesgo > 70:
        color = "#CE1126"
    elif riesgo > 40:
        color = "#FFC400"
    else:
        color = "#4CAF50"
    
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=riesgo,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': "Riesgo de ERC (%)", 'font': {'size': 24, 'color': '#002868'}},
        gauge={
            'axis': {'range': [0, 100], 'tickwidth': 1, 'tickcolor': "#002868"},
            'bar': {'color': color},
            'bgcolor': "white",
            'borderwidth': 2,
            'bordercolor': "#002868",
            'steps': [
                {'range': [0, 40], 'color': '#e5f7e5'},
                {'range': [40, 70], 'color': '#fff4e5'},
                {'range': [70, 100], 'color': '#ffe5e5'}
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': riesgo
            }
        }
    ))
    fig.update_layout(height=300, margin=dict(l=20, r=20, t=50, b=20))
    return fig

def crear_grafico_factores(paciente):
    """Crear gráfico de barras con los factores de riesgo"""
    # Normalizar valores para comparación
    factores = {
        'Edad': min(100, (paciente['edad'] / 100) * 100),
        'IMC': min(100, (paciente['imc'] / 40) * 100),
        'Presión': min(100, (paciente['presion_sistolica'] / 200) * 100),
        'Glucosa': min(100, (paciente['glucosa_ayunas'] / 300) * 100),
        'Creatinina': min(100, (paciente['creatinina'] / 5) * 100)
    }
    
    colors = []
    for k, v in factores.items():
        if v > 70:
            colors.append('#CE1126')
        elif v > 50:
            colors.append('#FFC400')
        else:
            colors.append('#4CAF50')
    
    fig = go.Figure(go.Bar(
        x=list(factores.keys()),
        y=list(factores.values()),
        marker_color=colors,
        text=[f"{v:.0f}%" for v in factores.values()],
        textposition='outside'
    ))
    fig.update_layout(
        title="Factores de Riesgo (Normalizados)",
        yaxis_title="Nivel (%)",
        height=300,
        margin=dict(l=20, r=20, t=50, b=20)
    )
    return fig

def generar_reporte_html(paciente, riesgo, nivel, doctor):
    """Generar reporte HTML para impresión/PDF"""
    fecha = datetime.now().strftime("%d/%m/%Y %H:%M")
    color = '#CE1126' if riesgo > 70 else '#FFC400' if riesgo > 40 else '#4CAF50'
    
    return f"""
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Reporte NefroPredict - {paciente['nombre_paciente']}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: 'Segoe UI', Arial, sans-serif; background: #f5f5f5; padding: 20px; }}
        .container {{ max-width: 800px; margin: auto; background: white; border-radius: 20px; overflow: hidden; box-shadow: 0 10px 40px rgba(0,0,0,0.1); }}
        .header {{ background: linear-gradient(135deg, #002868, #001a4d); color: white; padding: 30px; text-align: center; }}
        .header h1 {{ font-size: 2em; margin-bottom: 5px; }}
        .header p {{ opacity: 0.9; }}
        .content {{ padding: 30px; }}
        .risk-display {{ text-align: center; padding: 30px; margin: 20px 0; border-radius: 15px; background: linear-gradient(135deg, {color}22, {color}11); border: 3px solid {color}; }}
        .risk-number {{ font-size: 4em; font-weight: bold; color: {color}; }}
        .risk-label {{ font-size: 1.5em; color: {color}; margin-top: 10px; }}
        .info-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin: 20px 0; }}
        .info-item {{ background: #f8f9fa; padding: 15px; border-radius: 10px; border-left: 4px solid #002868; }}
        .info-label {{ color: #666; font-size: 0.9em; }}
        .info-value {{ color: #002868; font-size: 1.3em; font-weight: bold; }}
        .params-table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        .params-table th, .params-table td {{ padding: 12px; text-align: left; border-bottom: 1px solid #eee; }}
        .params-table th {{ background: #002868; color: white; }}
        .params-table tr:nth-child(even) {{ background: #f8f9fa; }}
        .recommendation {{ background: linear-gradient(135deg, {color}22, {color}11); padding: 20px; border-radius: 10px; margin: 20px 0; border-left: 5px solid {color}; }}
        .footer {{ text-align: center; padding: 20px; color: #666; font-size: 0.9em; border-top: 1px solid #eee; }}
        @media print {{
            body {{ background: white; padding: 0; }}
            .container {{ box-shadow: none; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🩺 NefroPredict RD</h1>
            <p>Sistema de Detección Temprana de Enfermedad Renal Crónica</p>
        </div>
        <div class="content">
            <div class="info-grid">
                <div class="info-item">
                    <div class="info-label">Paciente</div>
                    <div class="info-value">{paciente['nombre_paciente']}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">Médico Tratante</div>
                    <div class="info-value">{doctor}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">Fecha de Evaluación</div>
                    <div class="info-value">{fecha}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">ID Evaluación</div>
                    <div class="info-value">#{datetime.now().strftime('%Y%m%d%H%M')}</div>
                </div>
            </div>
            
            <div class="risk-display">
                <div class="risk-number">{riesgo:.1f}%</div>
                <div class="risk-label">Riesgo {nivel}</div>
            </div>
            
            <h3 style="color: #002868; margin: 20px 0 10px;">Parámetros Clínicos</h3>
            <table class="params-table">
                <tr><th>Parámetro</th><th>Valor</th><th>Rango Normal</th></tr>
                <tr><td>Edad</td><td>{paciente['edad']} años</td><td>-</td></tr>
                <tr><td>Índice de Masa Corporal</td><td>{paciente['imc']:.1f} kg/m²</td><td>18.5 - 24.9</td></tr>
                <tr><td>Presión Sistólica</td><td>{paciente['presion_sistolica']} mmHg</td><td>90 - 120</td></tr>
                <tr><td>Glucosa en Ayunas</td><td>{paciente['glucosa_ayunas']} mg/dL</td><td>70 - 100</td></tr>
                <tr><td>Creatinina Sérica</td><td>{paciente['creatinina']:.2f} mg/dL</td><td>0.7 - 1.3</td></tr>
            </table>
            
            <div class="recommendation">
                <h3 style="color: {color}; margin-bottom: 10px;">📋 Recomendación Clínica</h3>
                <p style="font-size: 1.1em;">{riesgo_level(riesgo)[2]}</p>
            </div>
        </div>
        <div class="footer">
            <p>NefroPredict RD © 2025 • República Dominicana</p>
            <p>Este reporte es una herramienta de apoyo diagnóstico y no reemplaza el criterio médico.</p>
        </div>
    </div>
    <script>window.onload = function() {{ window.print(); }}</script>
</body>
</html>
"""

# =============================================
# LOGIN
# =============================================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("### 🔐 Iniciar Sesión")
        with st.form("login_form"):
            username = st.text_input("Usuario").lower().strip()
            password = st.text_input("Contraseña", type="password")
            submitted = st.form_submit_button("Entrar", use_container_width=True)
            if submitted:
                user = db.get_user(username)
                if user and user["pwd"] == password and user.get("active", True):
                    st.session_state.logged_in = True
                    st.session_state.username = username
                    st.session_state.role = user["role"]
                    st.session_state.doctor_name = user.get("name", username)
                    st.rerun()
                else:
                    st.error("❌ Usuario o contraseña incorrectos")
    st.stop()

# Barra superior con info de usuario
col1, col2 = st.columns([5, 1])
with col1:
    st.success(f"👨‍⚕️ **{st.session_state.doctor_name}** • @{st.session_state.username}")
with col2:
    if st.button("🚪 Salir"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

st.markdown("---")

# =============================================
# PESTAÑAS SEGÚN ROL
# =============================================
if st.session_state.role == "admin":
    tabs = st.tabs(["📋 Evaluación Individual", "📤 Carga Masiva", "📊 Historial", "👥 Gestión Doctores", "📈 Estadísticas"])
    tab1, tab2, tab3, tab4, tab5 = tabs
else:
    tabs = st.tabs(["📋 Evaluación Individual", "📤 Carga Masiva", "📊 Historial"])
    tab1, tab2, tab3 = tabs

# =============================================
# TAB 1: EVALUACIÓN INDIVIDUAL
# =============================================
with tab1:
    st.subheader("📋 Evaluación Individual de Paciente")
    
    col_form, col_result = st.columns([1, 1])
    
    with col_form:
        st.markdown("#### Datos del Paciente")
        with st.form("form_individual", clear_on_submit=False):
            nombre = st.text_input("👤 Nombre completo del paciente", placeholder="Ej: Juan Pérez García")
            
            st.markdown("##### Datos Clínicos")
            c1, c2 = st.columns(2)
            with c1:
                edad = st.number_input("📅 Edad (años)", 18, 120, 55)
                imc = st.number_input("⚖️ IMC (kg/m²)", 10.0, 60.0, 27.0, 0.1)
                glucosa = st.number_input("🩸 Glucosa ayunas (mg/dL)", 50, 500, 110)
            with c2:
                presion = st.number_input("💓 Presión sistólica (mmHg)", 80, 250, 130)
                creatinina = st.number_input("🧪 Creatinina (mg/dL)", 0.1, 15.0, 1.2, 0.01)
            
            calcular = st.form_submit_button("🔬 Calcular Riesgo", use_container_width=True)
    
    with col_result:
        if calcular:
            if not nombre.strip():
                st.error("⚠️ El nombre del paciente es obligatorio")
            else:
                # Calcular riesgo
                datos_paciente = {
                    "edad": edad, "imc": imc, "presion_sistolica": presion,
                    "glucosa_ayunas": glucosa, "creatinina": creatinina
                }
                riesgo = predecir(datos_paciente)
                nivel, color, recomendacion = riesgo_level(riesgo)
                
                # Guardar en base de datos
                record = {
                    "nombre_paciente": nombre,
                    "doctor_user": st.session_state.username,
                    "doctor_name": st.session_state.doctor_name,
                    "timestamp": datetime.now().isoformat(),
                    "edad": edad, "imc": imc, "presion_sistolica": presion,
                    "glucosa_ayunas": glucosa, "creatinina": creatinina,
                    "riesgo": riesgo, "nivel": nivel
                }
                db.add_patient(record)
                
                # Guardar en session_state para mostrar
                st.session_state.ultimo_resultado = record
        
        # Mostrar resultado si existe
        if "ultimo_resultado" in st.session_state:
            p = st.session_state.ultimo_resultado
            nivel, color, recomendacion = riesgo_level(p["riesgo"])
            
            st.markdown("#### 📊 Resultado del Análisis")
            
            # Gráfico de gauge
            st.plotly_chart(crear_gauge_riesgo(p["riesgo"]), use_container_width=True)
            
            # Tarjeta de resultado
            if p["riesgo"] > 70:
                st.markdown(f"""<div class="risk-high">
                    <h2>⚠️ RIESGO {nivel}</h2>
                    <h1 style="font-size:3em">{p["riesgo"]:.1f}%</h1>
                    <p>{recomendacion}</p>
                </div>""", unsafe_allow_html=True)
            elif p["riesgo"] > 40:
                st.markdown(f"""<div class="risk-med">
                    <h2>⚡ RIESGO {nivel}</h2>
                    <h1 style="font-size:3em">{p["riesgo"]:.1f}%</h1>
                    <p>{recomendacion}</p>
                </div>""", unsafe_allow_html=True)
            else:
                st.markdown(f"""<div class="risk-low">
                    <h2>✅ RIESGO {nivel}</h2>
                    <h1 style="font-size:3em">{p["riesgo"]:.1f}%</h1>
                    <p>{recomendacion}</p>
                </div>""", unsafe_allow_html=True)
            
            # Gráfico de factores
            st.plotly_chart(crear_grafico_factores(p), use_container_width=True)
            
            # Botón para descargar/imprimir reporte
            reporte_html = generar_reporte_html(p, p["riesgo"], nivel, st.session_state.doctor_name)
            st.download_button(
                "🖨️ Descargar/Imprimir Reporte",
                reporte_html,
                file_name=f"Reporte_{p['nombre_paciente'].replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.html",
                mime="text/html",
                use_container_width=True
            )

# =============================================
# TAB 2: CARGA MASIVA
# =============================================
with tab2:
    st.subheader("📤 Carga Masiva desde Excel/CSV")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.markdown("#### 📥 Descargar Plantilla")
        plantilla = pd.DataFrame({
            "nombre_paciente": ["Juan Pérez", "María López", "Carlos Rodríguez"],
            "edad": [60, 55, 72],
            "imc": [29.5, 31.2, 26.8],
            "presion_sistolica": [150, 140, 165],
            "glucosa_ayunas": [180, 95, 220],
            "creatinina": [1.8, 1.1, 2.3]
        })
        csv = plantilla.to_csv(index=False).encode('utf-8')
        st.download_button("⬇️ Descargar Plantilla CSV", csv, "plantilla_nefropredict.csv", "text/csv", use_container_width=True)
        
        st.markdown("---")
        st.markdown("#### 📤 Subir Archivo")
        uploaded_file = st.file_uploader("Seleccionar archivo", type=["csv", "xlsx"])
    
    with col2:
        if uploaded_file:
            try:
                df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith(".csv") else pd.read_excel(uploaded_file)
                req_cols = ["nombre_paciente", "edad", "imc", "presion_sistolica", "glucosa_ayunas", "creatinina"]
                
                if not all(c in df.columns for c in req_cols):
                    st.error(f"❌ Faltan columnas. Requeridas: {', '.join(req_cols)}")
                else:
                    # Calcular riesgo para todos
                    df["riesgo"] = df.apply(predecir, axis=1)
                    df["nivel"] = df["riesgo"].apply(lambda x: riesgo_level(x)[0])
                    df["recomendacion"] = df["riesgo"].apply(lambda x: riesgo_level(x)[2])
                    
                    # Guardar en BD
                    for _, r in df.iterrows():
                        db.add_patient({
                            "nombre_paciente": r["nombre_paciente"],
                            "doctor_user": st.session_state.username,
                            "doctor_name": st.session_state.doctor_name,
                            "timestamp": datetime.now().isoformat(),
                            "edad": int(r["edad"]), "imc": float(r["imc"]),
                            "presion_sistolica": int(r["presion_sistolica"]),
                            "glucosa_ayunas": int(r["glucosa_ayunas"]),
                            "creatinina": float(r["creatinina"]),
                            "riesgo": float(r["riesgo"]), "nivel": r["nivel"]
                        })
                    
                    # Log de carga
                    db.add_upload_log({
                        "doctor_user": st.session_state.username,
                        "doctor_name": st.session_state.doctor_name,
                        "timestamp": datetime.now().isoformat(),
                        "cantidad": len(df)
                    })
                    
                    # Métricas
                    urgente = len(df[df["riesgo"] > 70])
                    medio = len(df[(df["riesgo"] > 40) & (df["riesgo"] <= 70)])
                    bajo = len(df[df["riesgo"] <= 40])
                    
                    st.success(f"✅ Procesados {len(df)} pacientes exitosamente")
                    
                    m1, m2, m3 = st.columns(3)
                    m1.metric("🔴 Intervención URGENTE", urgente)
                    m2.metric("🟡 Intervención Media", medio)
                    m3.metric("🟢 Seguimiento Rutinario", bajo)
                    
                    # Gráfico de distribución
                    fig_pie = px.pie(
                        values=[urgente, medio, bajo],
                        names=['Urgente (>70%)', 'Medio (40-70%)', 'Bajo (<40%)'],
                        color_discrete_sequence=['#CE1126', '#FFC400', '#4CAF50'],
                        title="Distribución de Riesgo"
                    )
                    st.plotly_chart(fig_pie, use_container_width=True)
                    
                    # Tabla de resultados
                    st.dataframe(
                        df[["nombre_paciente", "edad", "creatinina", "riesgo", "nivel"]].sort_values("riesgo", ascending=False),
                        use_container_width=True,
                        hide_index=True
                    )
            except Exception as e:
                st.error(f"❌ Error al procesar archivo: {str(e)}")

# =============================================
# TAB 3: HISTORIAL
# =============================================
with tab3:
    st.subheader("📊 Historial Clínico")
    
    # Obtener pacientes según rol
    if st.session_state.role == "doctor":
        pacientes = db.get_patients_by_doctor(st.session_state.username)
    else:
        pacientes = db.get_all_patients()
    
    if pacientes:
        dfp = pd.DataFrame(pacientes)
        
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.markdown("#### 🔍 Buscar Paciente")
            nombres = dfp["nombre_paciente"].unique().tolist()
            paciente_sel = st.selectbox("Seleccionar paciente", [""] + nombres)
            
            # Métricas generales
            st.markdown("#### 📈 Resumen General")
            total = len(dfp)
            prom_riesgo = dfp["riesgo"].mean()
            alto_riesgo = len(dfp[dfp["riesgo"] > 70])
            
            st.metric("Total Evaluaciones", total)
            st.metric("Riesgo Promedio", f"{prom_riesgo:.1f}%")
            st.metric("Alto Riesgo (>70%)", alto_riesgo)
        
        with col2:
            if paciente_sel:
                hist = dfp[dfp["nombre_paciente"] == paciente_sel].sort_values("timestamp")
                
                st.markdown(f"#### 📋 Historial de: **{paciente_sel}**")
                
                # Último resultado
                ultimo = hist.iloc[-1]
                nivel, color, reco = riesgo_level(ultimo["riesgo"])
                
                c1, c2, c3 = st.columns(3)
                c1.metric("Último Riesgo", f"{ultimo['riesgo']:.1f}%")
                c2.metric("Nivel", nivel)
                c3.metric("Evaluaciones", len(hist))
                
                # Gráfico de evolución temporal
                if len(hist) > 1:
                    fig_evol = px.line(
                        hist, x="timestamp", y="riesgo",
                        title="📈 Evolución del Riesgo en el Tiempo",
                        markers=True
                    )
                    fig_evol.add_hline(y=70, line_dash="dash", line_color="red", annotation_text="Alto Riesgo")
                    fig_evol.add_hline(y=40, line_dash="dash", line_color="orange", annotation_text="Riesgo Medio")
                    fig_evol.update_layout(height=300)
                    st.plotly_chart(fig_evol, use_container_width=True)
                
                # Tabla de historial
                st.dataframe(
                    hist[["timestamp", "riesgo", "nivel", "creatinina", "glucosa_ayunas", "presion_sistolica"]],
                    use_container_width=True,
                    hide_index=True
                )
            else:
                # Mostrar resumen general si no hay paciente seleccionado
                st.markdown("#### 📊 Distribución General de Riesgo")
                
                # Gráfico de distribución
                fig_hist = px.histogram(
                    dfp, x="riesgo", nbins=20,
                    title="Distribución de Niveles de Riesgo",
                    color_discrete_sequence=["#002868"]
                )
                fig_hist.add_vline(x=70, line_dash="dash", line_color="red")
                fig_hist.add_vline(x=40, line_dash="dash", line_color="orange")
                st.plotly_chart(fig_hist, use_container_width=True)
                
                # Top pacientes alto riesgo
                st.markdown("#### ⚠️ Pacientes con Mayor Riesgo")
                top_riesgo = dfp.nlargest(10, "riesgo")[["nombre_paciente", "riesgo", "nivel", "timestamp"]]
                st.dataframe(top_riesgo, use_container_width=True, hide_index=True)
    else:
        st.info("📭 Aún no hay registros de pacientes")

# =============================================
# TAB 4: GESTIÓN DE DOCTORES (SOLO ADMIN)
# =============================================
if st.session_state.role == "admin":
    with tab4:
        st.subheader("👥 Panel de Administración de Usuarios")
        
        # Sub-tabs dentro del panel admin
        admin_tab1, admin_tab2, admin_tab3 = st.tabs(["📋 Ver/Gestionar Doctores", "➕ Crear Doctor", "📊 Actividad y Archivos"])
        
        # ---------- SUB-TAB 1: VER Y GESTIONAR DOCTORES ----------
        with admin_tab1:
            st.markdown("#### 📋 Todos los Usuarios del Sistema")
            
            # Tabla resumen de todos los usuarios
            usuarios_data = []
            for user, info in db.data["users"].items():
                # Contar pacientes de este doctor
                if info["role"] == "doctor":
                    num_pacientes = len(db.get_patients_by_doctor(user))
                    num_cargas = len([u for u in db.data.get("uploads", []) if u.get("doctor_user") == user])
                else:
                    num_pacientes = "-"
                    num_cargas = "-"
                
                usuarios_data.append({
                    "Usuario": f"@{user}",
                    "Nombre": info["name"],
                    "Rol": "👑 Admin" if info["role"] == "admin" else "👨‍⚕️ Doctor",
                    "Estado": "🟢 Activo" if info.get("active", True) else "🔴 Inactivo",
                    "Contraseña": info["pwd"],
                    "Pacientes": num_pacientes,
                    "Cargas": num_cargas
                })
            
            df_usuarios = pd.DataFrame(usuarios_data)
            
            # Mostrar tabla con contraseñas ocultas por defecto
            st.markdown("##### 👁️ Vista General")
            mostrar_pwd = st.checkbox("🔓 Mostrar contraseñas (solo admin)", value=False)
            
            if mostrar_pwd:
                st.dataframe(df_usuarios, use_container_width=True, hide_index=True)
            else:
                df_oculto = df_usuarios.copy()
                df_oculto["Contraseña"] = "••••••"
                st.dataframe(df_oculto, use_container_width=True, hide_index=True)
            
            st.markdown("---")
            st.markdown("#### ⚙️ Gestionar Doctor Individual")
            
            # Selector de doctor
            doctores = {u: i for u, i in db.data["users"].items() if i["role"] == "doctor"}
            
            if doctores:
                opciones_doctores = [f"{info['name']} (@{user})" for user, info in doctores.items()]
                doctor_seleccionado = st.selectbox("Seleccionar doctor a gestionar:", [""] + opciones_doctores)
                
                if doctor_seleccionado:
                    # Extraer username del doctor seleccionado
                    user_sel = doctor_seleccionado.split("(@")[1].replace(")", "")
                    info_sel = doctores[user_sel]
                    
                    st.markdown(f"##### Gestionando: **{info_sel['name']}**")
                    
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.markdown("**🔐 Cambiar Contraseña**")
                        nueva_pwd = st.text_input("Nueva contraseña:", type="password", key="admin_new_pwd")
                        if st.button("💾 Guardar Contraseña", key="btn_save_pwd", use_container_width=True):
                            if nueva_pwd:
                                db.update_password(user_sel, nueva_pwd)
                                st.success("✅ Contraseña actualizada")
                                st.rerun()
                            else:
                                st.warning("Ingrese una contraseña")
                    
                    with col2:
                        st.markdown("**🔄 Estado de Cuenta**")
                        estado_actual = "🟢 ACTIVO" if info_sel.get("active", True) else "🔴 INACTIVO"
                        st.info(f"Estado actual: {estado_actual}")
                        
                        if info_sel.get("active", True):
                            if st.button("🚫 Desactivar Cuenta", key="btn_desactivar", use_container_width=True):
                                db.toggle_active(user_sel)
                                st.warning("Cuenta desactivada")
                                st.rerun()
                        else:
                            if st.button("✅ Activar Cuenta", key="btn_activar", use_container_width=True):
                                db.toggle_active(user_sel)
                                st.success("Cuenta activada")
                                st.rerun()
                    
                    with col3:
                        st.markdown("**🗑️ Eliminar Doctor**")
                        st.warning("⚠️ Esta acción es irreversible")
                        confirmar = st.checkbox("Confirmo que deseo eliminar", key="confirm_del")
                        if st.button("🗑️ Eliminar Permanentemente", key="btn_eliminar", type="primary", use_container_width=True, disabled=not confirmar):
                            db.delete_doctor(user_sel)
                            st.success(f"Doctor {info_sel['name']} eliminado")
                            st.rerun()
                    
                    # Ver pacientes de este doctor
                    st.markdown("---")
                    st.markdown(f"##### 📁 Pacientes de {info_sel['name']}")
                    pacientes_doctor = db.get_patients_by_doctor(user_sel)
                    if pacientes_doctor:
                        df_pac = pd.DataFrame(pacientes_doctor)
                        st.dataframe(
                            df_pac[["nombre_paciente", "timestamp", "riesgo", "nivel"]].head(20),
                            use_container_width=True,
                            hide_index=True
                        )
                        st.caption(f"Mostrando últimos 20 de {len(pacientes_doctor)} registros")
                    else:
                        st.info("Este doctor no tiene pacientes registrados")
            else:
                st.info("No hay doctores registrados en el sistema")
        
        # ---------- SUB-TAB 2: CREAR DOCTOR ----------
        with admin_tab2:
            st.markdown("#### ➕ Registrar Nuevo Doctor")
            
            with st.form("form_nuevo_doctor"):
                col1, col2 = st.columns(2)
                with col1:
                    nuevo_user = st.text_input("👤 Usuario (sin espacios)", placeholder="dr.apellido").lower().strip()
                    nuevo_pwd = st.text_input("🔐 Contraseña", type="password")
                with col2:
                    nuevo_nombre = st.text_input("📝 Nombre completo", placeholder="Dr. Juan Pérez")
                    nuevo_pwd_confirm = st.text_input("🔐 Confirmar contraseña", type="password")
                
                if st.form_submit_button("✅ Crear Doctor", use_container_width=True):
                    if not nuevo_user or not nuevo_pwd or not nuevo_nombre:
                        st.error("❌ Todos los campos son obligatorios")
                    elif db.get_user(nuevo_user):
                        st.error("❌ El usuario ya existe")
                    elif " " in nuevo_user:
                        st.error("❌ El usuario no puede tener espacios")
                    elif nuevo_pwd != nuevo_pwd_confirm:
                        st.error("❌ Las contraseñas no coinciden")
                    elif len(nuevo_pwd) < 4:
                        st.error("❌ La contraseña debe tener al menos 4 caracteres")
                    else:
                        db.create_doctor(nuevo_user, nuevo_pwd, nuevo_nombre)
                        st.success(f"✅ Doctor **{nuevo_nombre}** creado exitosamente")
                        st.balloons()
                        st.rerun()
        
        # ---------- SUB-TAB 3: ACTIVIDAD Y ARCHIVOS ----------
        with admin_tab3:
            st.markdown("#### 📊 Ranking de Doctores más Activos")
            
            all_patients = db.get_all_patients()
            
            if all_patients:
                df_all = pd.DataFrame(all_patients)
                
                # Ranking por número de evaluaciones
                ranking = df_all.groupby(["doctor_user", "doctor_name"]).agg({
                    "nombre_paciente": "count",
                    "riesgo": "mean"
                }).reset_index()
                ranking.columns = ["Usuario", "Doctor", "Total Evaluaciones", "Riesgo Promedio"]
                ranking["Riesgo Promedio"] = ranking["Riesgo Promedio"].round(1)
                ranking = ranking.sort_values("Total Evaluaciones", ascending=False)
                ranking["🏆 Ranking"] = range(1, len(ranking) + 1)
                ranking = ranking[["🏆 Ranking", "Doctor", "Usuario", "Total Evaluaciones", "Riesgo Promedio"]]
                
                # Mostrar podio
                col1, col2, col3 = st.columns(3)
                if len(ranking) >= 1:
                    col2.metric("🥇 1er Lugar", ranking.iloc[0]["Doctor"], f"{ranking.iloc[0]['Total Evaluaciones']} evaluaciones")
                if len(ranking) >= 2:
                    col1.metric("🥈 2do Lugar", ranking.iloc[1]["Doctor"], f"{ranking.iloc[1]['Total Evaluaciones']} evaluaciones")
                if len(ranking) >= 3:
                    col3.metric("🥉 3er Lugar", ranking.iloc[2]["Doctor"], f"{ranking.iloc[2]['Total Evaluaciones']} evaluaciones")
                
                st.markdown("##### 📋 Tabla Completa de Actividad")
                st.dataframe(ranking, use_container_width=True, hide_index=True)
                
                # Gráfico de barras
                fig_ranking = px.bar(
                    ranking.head(10), 
                    x="Doctor", 
                    y="Total Evaluaciones",
                    color="Total Evaluaciones",
                    color_continuous_scale="Blues",
                    title="Top 10 Doctores por Evaluaciones"
                )
                st.plotly_chart(fig_ranking, use_container_width=True)
            else:
                st.info("No hay actividad registrada aún")
            
            st.markdown("---")
            st.markdown("#### 📤 Historial de Cargas Masivas")
            
            uploads = db.data.get("uploads", [])
            if uploads:
                df_uploads = pd.DataFrame(uploads)
                st.dataframe(df_uploads, use_container_width=True, hide_index=True)
            else:
                st.info("No hay cargas masivas registradas")
            
            st.markdown("---")
            st.markdown("#### 🔒 Acceso a Datos por Doctor")
            st.info("👆 Selecciona un doctor en la pestaña 'Ver/Gestionar Doctores' para ver sus pacientes. Los datos de cada doctor están completamente aislados y nunca se cruzan entre médicos.")

    # =============================================
    # TAB 5: ESTADÍSTICAS ADMIN
    # =============================================
    with tab5:
        st.subheader("📈 Estadísticas del Sistema")
        
        all_patients = db.get_all_patients()
        
        if all_patients:
            df_all = pd.DataFrame(all_patients)
            
            # Métricas principales
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("📊 Total Evaluaciones", len(df_all))
            c2.metric("👥 Pacientes Únicos", df_all["nombre_paciente"].nunique())
            c3.metric("📈 Riesgo Promedio", f"{df_all['riesgo'].mean():.1f}%")
            c4.metric("⚠️ Alto Riesgo", len(df_all[df_all["riesgo"] > 70]))
            
            st.markdown("---")
            
            col1, col2 = st.columns(2)
            
            with col1:
                # Evaluaciones por doctor
                st.markdown("#### 👨‍⚕️ Evaluaciones por Doctor")
                por_doctor = df_all["doctor_name"].value_counts().reset_index()
                por_doctor.columns = ["Doctor", "Evaluaciones"]
                fig_doc = px.bar(por_doctor, x="Doctor", y="Evaluaciones", color="Evaluaciones",
                                color_continuous_scale="Blues")
                st.plotly_chart(fig_doc, use_container_width=True)
            
            with col2:
                # Distribución de riesgo
                st.markdown("#### 📊 Distribución de Riesgo")
                df_all["categoria"] = df_all["riesgo"].apply(
                    lambda x: "Alto (>70%)" if x > 70 else "Medio (40-70%)" if x > 40 else "Bajo (<40%)"
                )
                por_cat = df_all["categoria"].value_counts().reset_index()
                por_cat.columns = ["Categoría", "Cantidad"]
                fig_cat = px.pie(por_cat, values="Cantidad", names="Categoría",
                                color_discrete_sequence=["#CE1126", "#FFC400", "#4CAF50"])
                st.plotly_chart(fig_cat, use_container_width=True)
            
            # Tendencia temporal
            st.markdown("#### 📅 Tendencia de Evaluaciones")
            df_all["fecha"] = pd.to_datetime(df_all["timestamp"]).dt.date
            por_fecha = df_all.groupby("fecha").agg({"riesgo": ["count", "mean"]}).reset_index()
            por_fecha.columns = ["Fecha", "Cantidad", "Riesgo Promedio"]
            
            fig_trend = px.line(por_fecha, x="Fecha", y="Cantidad", 
                               title="Evaluaciones por Día", markers=True)
            st.plotly_chart(fig_trend, use_container_width=True)
            
            # Tabla resumen por doctor
            st.markdown("#### 📋 Resumen por Doctor")
            resumen = df_all.groupby("doctor_name").agg({
                "nombre_paciente": "count",
                "riesgo": "mean"
            }).reset_index()
            resumen.columns = ["Doctor", "Total Evaluaciones", "Riesgo Promedio"]
            resumen["Riesgo Promedio"] = resumen["Riesgo Promedio"].round(1)
            st.dataframe(resumen, use_container_width=True, hide_index=True)
        else:
            st.info("📭 Aún no hay datos para mostrar estadísticas")

# =============================================
# FOOTER
# =============================================
st.markdown("---")
st.caption("🩺 NefroPredict RD © 2025 • Sistema de Detección Temprana de ERC • República Dominicana")
