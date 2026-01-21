import pandas as pd
import sqlite3
import bcrypt
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from fpdf import FPDF
from io import BytesIO

# =============================================
# 1. CONFIGURACIÓN Y MOTOR DE BASE DE DATOS
# =============================================
# Nota: st.set_page_config debe ser la primera instrucción de Streamlit
if 'setup_done' not in st.session_state:
    st.session_state.setup_done = True

class AppDatabase:
    def __init__(self):
        self.conn = sqlite3.connect("nefrocardio_v2026.db", check_same_thread=False)
        self.init_db()

    def init_db(self):
        c = self.conn.cursor()
        c.execute("""CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY, password TEXT, name TEXT, role TEXT, specialty TEXT)""")
        c.execute("""CREATE TABLE IF NOT EXISTS clinical_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT, px_name TEXT, px_id TEXT, date TEXT, doctor TEXT,
            weight REAL, height REAL, sys INT, tfg REAL, albuminuria REAL, potasio REAL, bun_cr REAL,
            fevi REAL, troponina REAL, bnp REAL, ldl REAL, sleep REAL, stress TEXT, exercise INT, obs TEXT)""")
        
        c.execute("SELECT * FROM users WHERE username='admin'")
        if not c.fetchone():
            pw = bcrypt.hashpw("Admin2026!".encode(), bcrypt.gensalt()).decode()
            c.execute("INSERT INTO users VALUES ('admin', ?, 'Admin Master', 'admin', 'todas')", (pw,))
        self.conn.commit()

db = AppDatabase()

# =============================================
# 2. MOTOR DE RECOMENDACIONES CIENTÍFICAS (Corregido)
# =============================================
def generar_plan_cientifico(d):
    """
    Recibe un diccionario 'd' con los valores clínicos.
    Usa .get() para evitar KeyErrors si falta algún dato.
    """
    recom = {"dieta": [], "estilo": [], "clinico": []}
    
    # --- Insights de Nefrología ---
    tfg_val = d.get('tfg', 90)
    pot_val = d.get('potasio', 4.0)
    alb_val = d.get('albuminuria', 10)

    if tfg_val < 60:
        recom['clinico'].append("Priorizar IECA/ARA-II y SGLT2i según tolerancia (KDIGO 2024).")
        recom['dieta'].append("Restricción de proteínas (0.8g/kg) para reducir carga glomerular.")
    
    if pot_val > 5.2:
        recom['dieta'].append("URGENTE: Hiperpotasemia detectada. Dieta baja en potasio (evitar guineo, cítricos).")
    
    if alb_val > 30:
        recom['clinico'].append("Albuminuria elevada: Sugiere daño en barrera de filtrado. Control estricto de PA.")

    # --- Insights de Cardiología ---
    fevi_val = d.get('fevi', 55)
    bnp_val = d.get('bnp', 50)
    ldl_val = d.get('ldl', 100)
    sys_val = d.get('sys', 120)

    if fevi_val < 40:
        recom['clinico'].append("IC con FEVI reducida: Optimizar terapia cuádruple (ARNI, BB, MRA, SGLT2i).")
    
    if bnp_val > 125:
        recom['estilo'].append("Restricción hídrica y control diario de peso por riesgo de congestión.")
    
    if ldl_val > 70:
        recom['clinico'].append("Meta LDL <55 o 70 mg/dL. Considerar estatinas de alta intensidad.")

    if sys_val >= 140:
        recom['clinico'].append("Hipertensión Sistólica: Riesgo de daño en órgano blanco (corazón/riñón).")

    # --- Bienestar General ---
    if d.get('sleep', 7.5) < 7:
        recom['estilo'].append("Higiene del sueño: Meta 7-8h para regular el eje RAA.")
    
    if d.get('stress') == "Alto":
        recom['estilo'].append("Gestión de Estrés: Mindfulness para reducir el tono simpático.")
    
    return recom

# =============================================
# 3. INTERFAZ DE USUARIO
# =============================================
if "auth" not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.title("🏥 NefroCardio SaaS")
        u = st.text_input("Usuario")
        p = st.text_input("Clave", type="password")
        if st.button("Acceder", use_container_width=True):
            cursor = db.conn.cursor()
            cursor.execute("SELECT password, name, role, specialty FROM users WHERE username=?", (u,))
            res = cursor.fetchone()
            if res and bcrypt.checkpw(p.encode(), res[0].encode()):
                st.session_state.update({"auth":True, "name":res[1], "role":res[2], "spec":res[3]})
                st.rerun()
            else:
                st.error("Credenciales incorrectas")
    st.stop()

# --- DASHBOARD PRINCIPAL ---
st.sidebar.title(f"Dr. {st.session_state.name}")
menu = st.sidebar.radio("Menú", ["Nueva Consulta", "Historial", "Panel Admin"])

if menu == "Nueva Consulta":
    st.header("Evaluación Clínica Multidisciplinaria")
    
    # Buscador por nombre
    cursor = db.conn.cursor()
    cursor.execute("SELECT DISTINCT px_name FROM clinical_records")
    px_list = [r[0] for r in cursor.fetchall()]
    sel_px = st.selectbox("🔍 Buscar Paciente:", ["-- Nuevo Registro --"] + px_list)
    
    with st.form("main_form"):
        c1, c2, c3 = st.columns(3)
        p_name = c1.text_input("Nombre Paciente", value="" if sel_px == "-- Nuevo Registro --" else sel_px)
        p_id = c2.text_input("Cédula/ID")
        sys_p = c3.number_input("Presión Sistólica (mmHg)", 80, 220, 120)

        st.divider()
        st.subheader("🧫 Módulo Nefrología")
        n1, n2, n3, n4 = st.columns(4)
        tfg_val = n1.number_input("TFG (ml/min)", 0.0, 150.0, 90.0)
        alb_val = n2.number_input("Albuminuria (mg/g)", 0.0, 5000.0, 10.0)
        pot_val = n3.number_input("Potasio (K+)", 2.0, 8.0, 4.0)
        bun_val = n4.number_input("BUN/Cr Ratio", 0.0, 50.0, 15.0)

        st.subheader("🫀 Módulo Cardiología")
        ca1, ca2, ca3, ca4 = st.columns(4)
        fevi_val = ca1.number_input("FEVI (%)", 5.0, 80.0, 55.0)
        trop_val = ca2.number_input("Troponina (ng/L)", 0.0, 1000.0, 10.0)
        bnp_val = ca3.number_input("BNP (pg/mL)", 0.0, 5000.0, 50.0)
        ldl_val = ca4.number_input("Colesterol LDL (mg/dL)", 0.0, 300.0, 100.0)

        st.subheader("🧘 Estilo de Vida y Notas")
        e1, e2, e3 = st.columns(3)
        sleep_val = e1.slider("Horas Sueño", 3.0, 12.0, 7.5)
        stress_val = e2.selectbox("Estrés", ["Bajo", "Moderado", "Alto"])
        exer_val = e3.number_input("Ejercicio (min/sem)", 0, 500, 150)
        obs_val = st.text_area("Observaciones Médicas Personalizadas")
        
        submit = st.form_submit_button("ANALIZAR Y GENERAR REPORTE")

    if submit:
        # CONSTRUCCIÓN DEL DICCIONARIO (Corrección del KeyError)
        datos_clinicos = {
            "tfg": tfg_val,
            "potasio": pot_val,
            "albuminuria": alb_val,
            "fevi": fevi_val,
            "bnp": bnp_val,
            "ldl": ldl_val,
            "sys": sys_p,
            "sleep": sleep_val,
            "stress": stress_val
        }

        # Llamada segura a la función
        recoms = generar_plan_cientifico(datos_clinicos)

        # Guardado en Base de Datos
        db.conn.execute("""INSERT INTO clinical_records (px_name, px_id, date, doctor, sys, tfg, albuminuria, potasio, 
            bun_cr, fevi, troponina, bnp, ldl, sleep, stress, exercise, obs) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (p_name, p_id, datetime.now().strftime('%Y-%m-%d'), st.session_state.name, sys_p, tfg_val, alb_val, 
             pot_val, bun_val, fevi_val, trop_val, bnp_val, ldl_val, sleep_val, stress_val, exer_val, obs_val))
        db.conn.commit()

        # Visualizaciones
        st.divider()
        st.subheader("📊 Visualización de Riesgos")
        v1, v2 = st.columns(2)
        
        with v1:
            fig_tfg = go.Figure(go.Indicator(
                mode = "gauge+number", value = tfg_val, title = {'text': "Función Renal (TFG)"},
                gauge = {'axis': {'range': [0, 120]}, 'bar': {'color': "darkblue"},
                         'steps': [{'range': [0, 30], 'color': "red"}, {'range': [30, 60], 'color': "orange"}, {'range': [60, 120], 'color': "green"}]}))
            st.plotly_chart(fig_tfg, use_container_width=True)

        with v2:
            fig_cardio = px.line_polar(r=[fevi_val, 100-(bnp_val/50), 100-(ldl_val/3), 100-(trop_val/10)], 
                theta=['FEVI', 'BNP (Presión)', 'LDL (Lípidos)', 'Troponina'], line_close=True, title="Perfil Cardiaco")
            st.plotly_chart(fig_cardio, use_container_width=True)

        # Sugerencias Científicas con Formato
        st.info("### 🧬 Sugerencias Sustentadas")
        for cat, items in recoms.items():
            if items:
                st.markdown(f"**{cat.capitalize()}:**")
                for item in items:
                    st.write(f"- {item}")

        st.success("Análisis completado y guardado en historial.")

# --- HISTORIAL ---
elif menu == "Historial":
    st.header("Seguimiento del Paciente")
    h_px = st.text_input("Nombre del Paciente")
    if h_px:
        df = pd.read_sql(f"SELECT * FROM clinical_records WHERE px_name LIKE '%{h_px}%'", db.conn)
        if not df.empty:
            st.plotly_chart(px.line(df, x="date", y=["tfg", "fevi", "ldl"], title="Evolución de Biomarcadores"))
            st.dataframe(df)
        else:
            st.warning("No se encontraron registros para este paciente.")
