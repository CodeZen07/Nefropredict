import pandas as pd
import numpy as np
import sqlite3
import bcrypt
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from fpdf import FPDF
from io import BytesIO

# =============================================
# 1. CONFIGURACIÓN Y SEGURIDAD LEGAL
# =============================================
st.set_page_config(page_title="NefroCardio RD Pro", page_icon="⚖️", layout="wide")

DISCLAIMER = """AVISO LEGAL: Esta herramienta es estrictamente de apoyo a la decision clinica y no sustituye el juicio profesional. 
Los resultados son estimaciones probabilisticas basadas en modelos matematicos. El uso de esta informacion es responsabilidad exclusiva del medico tratante."""

# =============================================
# 2. BASE DE DATOS EVOLUCIONADA
# =============================================
class SystemDB:
    def __init__(self):
        self.conn = sqlite3.connect("clinica_saas.db", check_same_thread=False)
        self.init_tables()

    def init_tables(self):
        c = self.conn.cursor()
        # Usuarios con especialidad
        c.execute("""CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY, password TEXT, name TEXT, 
            role TEXT, specialty TEXT, active INT)""")
        # Pacientes con datos clinicos extendidos
        c.execute("""CREATE TABLE IF NOT EXISTS records (
            id INTEGER PRIMARY KEY AUTOINCREMENT, patient_id TEXT, name TEXT, doctor TEXT,
            specialty TEXT, weight REAL, height REAL, systolic INT, glucose REAL, 
            creat REAL, tfg REAL, cv_risk REAL, date TEXT)""")
        
        c.execute("SELECT * FROM users WHERE username='admin'")
        if not c.fetchone():
            pw = bcrypt.hashpw("Admin2026!".encode(), bcrypt.gensalt()).decode()
            c.execute("INSERT INTO users VALUES (?,?,?,?,?,?)", ("admin", pw, "Admin Sistema", "admin", "all", 1))
        self.conn.commit()

db = SystemDB()

# =============================================
# 3. MOTOR DE RECOMENDACIONES CIENTÍFICAS
# =============================================
def get_personalized_plan(data):
    imc = data['weight'] / ((data['height']/100)**2)
    plan = {"dieta": "", "estilo": "", "proyeccion": ""}
    
    # Lógica de Dieta y Peso
    if imc > 25:
        deficit = 500 # kcal/dia
        semanas = round((data['weight'] * 0.10) / 0.5) # tiempo para bajar 10% del peso
        plan["dieta"] = f"Dieta Hipocalorica Mediterranea. Restriccion de 500kcal/dia. Priorizar proteinas magras y fibra."
        plan["proyeccion"] = f"Siguiendo el plan, proyectamos una perdida de {round(data['weight']*0.1, 1)} lbs en {semanas} semanas."
    else:
        plan["dieta"] = "Dieta Normocalorica Dash para mantenimiento de salud endotelial."
        plan["proyeccion"] = "Mantenimiento de estabilidad metabolica en 12 semanas."

    # Gestión de Estrés y Sueño
    if data['systolic'] > 140 or data['glucose'] > 110:
        plan["estilo"] = "Higiene del sueño: 7-8h diarias. Protocolo de respiracion guiada 10 min/noche. Ejercicio aerobico 30m/dia."
    else:
        plan["estilo"] = "Mantener actividad fisica actual. Incorporar entrenamiento de fuerza 2 veces por semana."
        
    return plan, round(imc, 1)

# =============================================
# 4. GENERADOR DE REPORTES PDF
# =============================================
def generate_medical_pdf(p_data, doc_info):
    pdf = FPDF()
    pdf.add_page()
    
    # Header
    pdf.set_fill_color(41, 128, 185)
    pdf.rect(0, 0, 210, 45, 'F')
    pdf.set_font("Arial", 'B', 20)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 15, "INFORME MEDICO PERSONALIZADO", 0, 1, 'C')
    pdf.set_font("Arial", 'I', 8)
    pdf.multi_cell(0, 5, DISCLAIMER)
    
    # Paciente
    pdf.ln(10)
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, f"Paciente: {p_data['name']} | Dr. {doc_info['name']} ({doc_info['spec']})", 0, 1)
    pdf.line(10, 65, 200, 65)
    
    # Resultados
    pdf.ln(5)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(90, 10, "Indicador", 1, 0, 'C', True)
    pdf.cell(90, 10, "Valor Actual", 1, 1, 'C', True)
    
    for k, v in p_data['metrics'].items():
        pdf.cell(90, 8, k, 1)
        pdf.cell(90, 8, str(v), 1, 1)

    # Plan
    pdf.ln(10)
    pdf.set_font("Arial", 'B', 14)
    pdf.set_text_color(41, 128, 185)
    pdf.cell(0, 10, "PLAN DE VIDA Y NUTRICION", 0, 1)
    pdf.set_font("Arial", '', 11)
    pdf.set_text_color(0, 0, 0)
    pdf.multi_cell(0, 7, f"DIETA: {p_data['plan']['dieta']}\n\nESTILO DE VIDA: {p_data['plan']['estilo']}\n\nPROYECCION: {p_data['plan']['proyeccion']}")
    
    out = pdf.output(dest='S')
    return BytesIO(out.encode('latin-1', errors='replace')) if isinstance(out, str) else BytesIO(out)

# =============================================
# 5. INTERFAZ DE USUARIO
# =============================================
if "auth" not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:
    c1, c2, c3 = st.columns([1,1.5,1])
    with col2 := c2:
        st.title("🏥 NefroCardio SaaS")
        u = st.text_input("Usuario")
        p = st.text_input("Clave", type="password")
        if st.button("Acceder"):
            cursor = db.conn.cursor()
            cursor.execute("SELECT password, name, role, specialty FROM users WHERE username=?", (u,))
            res = cursor.fetchone()
            if res and bcrypt.checkpw(p.encode(), res[0].encode()):
                st.session_state.update({"auth":True, "user":u, "name":res[1], "role":res[2], "spec":res[3]})
                st.rerun()
        st.info(f"⚖️ {DISCLAIMER}")
    st.stop()

# --- SIDEBAR ---
with st.sidebar:
    st.write(f"🩺 **{st.session_state.name}**")
    st.write(f"Especialidad: {st.session_state.spec.upper()}")
    menu = st.radio("Acciones", ["Nueva Consulta", "Historial Pacientes", "Admin Panel"])
    if st.button("Salir"):
        st.session_state.auth = False
        st.rerun()

# --- MODULO: NUEVA CONSULTA ---
if menu == "Nueva Consulta":
    st.header(f"Evaluacion Especializada: {st.session_state.spec}")
    
    with st.form("main_form"):
        c1, c2 = st.columns(2)
        p_id = c1.text_input("Cedula/ID Paciente")
        p_name = c2.text_input("Nombre Completo")
        
        col1, col2, col3 = st.columns(3)
        w = col1.number_input("Peso (kg)", 40.0, 200.0, 75.0)
        h = col2.number_input("Altura (cm)", 100, 220, 170)
        syst = col3.number_input("Presion Sistolica", 80, 220, 120)
        
        # Inputs Dinamicos por Especialidad
        tfg, cv_risk = 0, 0
        if st.session_state.spec in ["nefrologia", "all"]:
            creat = st.number_input("Creatinina (mg/dL)", 0.5, 10.0, 1.0)
            tfg = round(141 * min(creat/0.9, 1)**-0.411 * 0.993**30, 1) # Simplificado
        
        if st.session_state.spec in ["cardiologia", "all"]:
            gluc = st.number_input("Glucosa (mg/dL)", 60, 300, 100)
            cv_risk = round((syst * 0.1) + (gluc * 0.05), 1)

        if st.form_submit_button("Generar Analisis y Proyeccion"):
            # Procesar
            plan, imc = get_personalized_plan({'weight':w, 'height':h, 'systolic':syst, 'glucose':100})
            
            # Guardar
            db.conn.execute("INSERT INTO records (patient_id, name, doctor, specialty, weight, height, systolic, glucose, creat, tfg, cv_risk, date) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                           (p_id, p_name, st.session_state.name, st.session_state.spec, w, h, syst, 100, 1.0, tfg, cv_risk, datetime.now().strftime('%Y-%m-%d')))
            db.conn.commit()

            # UI Resultados
            st.success("Analisis Completado")
            res_c1, res_c2 = st.columns(2)
            res_c1.metric("IMC", imc)
            res_c1.write(f"**Dieta:** {plan['dieta']}")
            res_c2.metric("Proyeccion", "Exito Estimado")
            res_c2.write(f"**Meta:** {plan['proyeccion']}")
            
            # PDF
            metrics = {"IMC": imc, "Presion": syst, "TFG": tfg, "Riesgo CV": cv_risk}
            pdf_data = {"name": p_name, "metrics": metrics, "plan": plan}
            pdf_buf = generate_medical_pdf(pdf_data, {"name": st.session_state.name, "spec": st.session_state.spec})
            st.download_button("Descargar Reporte y Plan", pdf_buf.getvalue(), f"Plan_{p_name}.pdf", "application/pdf")

# --- MODULO: HISTORIAL ---
elif menu == "Historial Pacientes":
    st.header("Seguimiento de Evolucion")
    p_id_search = st.text_input("Ingrese ID del Paciente para ver progreso")
    if p_id_search:
        df = pd.read_sql(f"SELECT * FROM records WHERE patient_id='{p_id_search}'", db.conn)
        if not df.empty:
            fig = px.line(df, x="date", y=["weight", "tfg", "cv_risk"], title="Evolucion Clinica")
            st.plotly_chart(fig)
            st.dataframe(df)

# --- MODULO: ADMIN ---
elif menu == "Admin Panel":
    if st.session_state.role != "admin":
        st.error("No tienes permisos")
    else:
        st.subheader("Gestion de Suscriptores (Medicos)")
        with st.form("new_doc"):
            new_u = st.text_input("ID Login")
            new_p = st.text_input("Clave")
            new_n = st.text_input("Nombre Dr.")
            new_s = st.selectbox("Especialidad", ["nefrologia", "cardiologia", "all"])
            if st.form_submit_button("Crear Suscriptor"):
                db.add_user(new_u, new_p, new_n, "doctor", new_s)
                st.success("Medico añadido con acceso especializado")
