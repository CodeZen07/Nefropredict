import pandas as pd
import numpy as np
import sqlite3
import bcrypt
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from fpdf import FPDF
from io import BytesIO

# =============================================
# 1. CONFIGURACIÓN Y MARCO LEGAL
# =============================================
st.set_page_config(page_title="NefroCardio SaaS RD", page_icon="🏥", layout="wide")

LEGAL_NOTICE = """⚠️ AVISO LEGAL: Esta plataforma es una herramienta de apoyo clinico para profesionales de la salud. 
No reemplaza el juicio medico ni la evaluacion presencial. Los datos generados son proyecciones 
basadas en literatura cientifica (KDIGO/AHA). El uso de la informacion es responsabilidad del medico."""

# =============================================
# 2. MOTOR DE BASE DE DATOS
# =============================================
class AppDatabase:
    def __init__(self):
        self.conn = sqlite3.connect("nefrocardio_saas.db", check_same_thread=False)
        self.init_db()

    def init_db(self):
        cursor = self.conn.cursor()
        # Usuarios (Suscripciones)
        cursor.execute("""CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY, password TEXT, name TEXT, 
            role TEXT, specialty TEXT, active INT)""")
        # Registros de Consultas
        cursor.execute("""CREATE TABLE IF NOT EXISTS records (
            id INTEGER PRIMARY KEY AUTOINCREMENT, px_id TEXT, px_name TEXT, 
            doctor TEXT, spec TEXT, weight REAL, height REAL, sys INT, 
            gluc REAL, creat REAL, tfg REAL, risk REAL, date TEXT)""")
        
        # Crear Admin Maestro
        cursor.execute("SELECT * FROM users WHERE username='admin'")
        if not cursor.fetchone():
            hashed = bcrypt.hashpw("Admin2026!".encode(), bcrypt.gensalt()).decode()
            cursor.execute("INSERT INTO users VALUES (?,?,?,?,?,?)", 
                          ("admin", hashed, "Administrador SaaS", "admin", "todas", 1))
        self.conn.commit()

    def create_user(self, u, p, n, r, s):
        try:
            hp = bcrypt.hashpw(p.encode(), bcrypt.gensalt()).decode()
            self.conn.execute("INSERT INTO users VALUES (?,?,?,?,?,?)", (u, hp, n, r, s, 1))
            self.conn.commit()
            return True
        except: return False

db = AppDatabase()

# =============================================
# 3. LÓGICA CIENTÍFICA: PROYECCIONES Y PLANES
# =============================================
def calcular_proyeccion_salud(w, h, sys, gluc):
    imc = round(w / ((h/100)**2), 1)
    plan = {
        "nutricion": "",
        "estilo_vida": "Ejercicio aerobico 150 min/semana. Higiene del sueno (7-8h). Manejo de estres mediante pausas activas.",
        "proyeccion": ""
    }
    
    # Lógica de peso
    if imc > 25:
        perder_kg = round(w * 0.10, 1)
        semanas = int(perder_kg / 0.5) # 0.5kg por semana es saludable
        plan["nutricion"] = "Restriccion calorica moderada (-500 kcal/dia). Enfoque en dieta DASH (baja en sodio)."
        plan["proyeccion"] = f"Meta: Reducir {perder_kg} kg ({round(perder_kg*2.204, 1)} lbs) en {semanas} semanas."
    else:
        plan["nutricion"] = "Dieta normocalorica equilibrada. Priorizar grasas insaturadas y carbohidratos complejos."
        plan["proyeccion"] = "Mantenimiento de parametros actuales y estabilidad endotelial."

    return plan, imc

# =============================================
# 4. GENERADOR DE REPORTES (SOLUCIÓN BYTESIO)
# =============================================
def export_medical_report(p_data, doc_name, spec):
    pdf = FPDF()
    pdf.add_page()
    
    # Cabecera Profesional
    pdf.set_fill_color(0, 102, 204)
    pdf.rect(0, 0, 210, 40, 'F')
    pdf.set_font("Arial", 'B', 16)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 15, "INFORME MEDICO Y RECOMENDACIONES", 0, 1, 'C')
    pdf.set_font("Arial", 'I', 7)
    pdf.multi_cell(0, 4, LEGAL_NOTICE)
    
    # Info Paciente
    pdf.ln(10)
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, f"Paciente: {p_data['name'].upper()} | ID: {p_data['id']}", 0, 1)
    pdf.cell(0, 10, f"Medico Tratante: {doc_name} ({spec.capitalize()})", 0, 1)
    pdf.line(10, 65, 200, 65)
    
    # Resultados
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(0, 10, "RESULTADOS CLINICOS:", 0, 1)
    pdf.set_font("Arial", '', 10)
    for k, v in p_data['metrics'].items():
        pdf.cell(90, 8, f"{k}:", 1)
        pdf.cell(90, 8, f"{v}", 1, 1)
        
    # Recomendaciones
    pdf.ln(10)
    pdf.set_font("Arial", 'B', 12)
    pdf.set_text_color(0, 102, 204)
    pdf.cell(0, 10, "PLAN DE SEGUIMIENTO PERSONALIZADO:", 0, 1)
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", '', 10)
    
    recoms = [
        ("NUTRICION", p_data['plan']['nutricion']),
        ("ESTILO DE VIDA", p_data['plan']['estilo_vida']),
        ("PROYECCION DE MEJORA", p_data['plan']['proyeccion'])
    ]
    
    for tit, cont in recoms:
        pdf.set_font("Arial", 'B', 10)
        pdf.cell(0, 7, f"{tit}:", 0, 1)
        pdf.set_font("Arial", '', 10)
        # Limpieza de caracteres latinos para FPDF
        txt = cont.replace('ñ','n').replace('á','a').replace('é','e').replace('í','i').replace('ó','o').replace('ú','u')
        pdf.multi_cell(0, 6, txt)
        pdf.ln(2)

    # Firma
    pdf.ln(20)
    pdf.line(70, pdf.get_y(), 140, pdf.get_y())
    pdf.cell(0, 10, f"Firma Dr. {doc_name}", 0, 1, 'C')

    # Retorno de bytes
    res = pdf.output(dest='S')
    if isinstance(res, str):
        return BytesIO(res.encode('latin-1', errors='replace'))
    return BytesIO(res)

# =============================================
# 5. INTERFAZ Y NAVEGACIÓN
# =============================================
if "auth" not in st.session_state:
    st.session_state.auth = False

# --- PANTALLA DE LOGIN ---
if not st.session_state.auth:
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.markdown("<h2 style='text-align: center;'>🔐 Acceso Suscriptores</h2>", unsafe_allow_html=True)
        user = st.text_input("Usuario")
        password = st.text_input("Contraseña", type="password")
        if st.button("Iniciar Sesión", use_container_width=True):
            cursor = db.conn.cursor()
            cursor.execute("SELECT password, name, role, specialty FROM users WHERE username=?", (user,))
            data = cursor.fetchone()
            if data and bcrypt.checkpw(password.encode(), data[0].encode()):
                st.session_state.update({"auth":True, "user":user, "name":data[1], "role":data[2], "spec":data[3]})
                st.rerun()
            else: st.error("Credenciales invalidas")
        st.caption(LEGAL_NOTICE)
    st.stop()

# --- SIDEBAR NAVEGACIÓN ---
with st.sidebar:
    st.markdown(f"### Dr. {st.session_state.name}")
    st.write(f"💼 Especialidad: {st.session_state.spec.upper()}")
    st.markdown("---")
    menu = st.radio("MODULOS", ["📊 Nueva Consulta", "📈 Historial & Evolucion", "⚙️ Panel Administrativo"])
    if st.button("Cerrar Sesión"):
        st.session_state.auth = False
        st.rerun()

# =============================================
# 6. LÓGICA DE MÓDULOS
# =============================================

# --- MÓDULO CONSULTA ---
if menu == "📊 Nueva Consulta":
    st.header(f"Calculadora Medica Especializada: {st.session_state.spec.capitalize()}")
    
    with st.form("form_px"):
        c1, c2 = st.columns(2)
        px_id = c1.text_input("ID Paciente (Cedula/Pasaporte)")
        px_name = c2.text_input("Nombre Completo")
        
        m1, m2, m3 = st.columns(3)
        weight = m1.number_input("Peso (kg)", 35.0, 250.0, 75.0)
        height = m2.number_input("Talla (cm)", 110, 220, 170)
        sys_p = m3.number_input("Presion Sistolica", 80, 220, 120)
        
        # Filtros por especialidad
        tfg, cv_risk = 0, 0
        if st.session_state.spec in ["nefrologia", "todas"]:
            st.markdown("**Seccion Nefrologia**")
            creat = st.number_input("Creatinina Serica (mg/dL)", 0.4, 15.0, 1.0)
            # CKD-EPI Simplificada
            tfg = round(141 * min(creat/0.9, 1)**-0.411 * 0.993**40, 1)
        
        if st.session_state.spec in ["cardiologia", "todas"]:
            st.markdown("**Seccion Cardiologia**")
            gluc = st.number_input("Glucosa (mg/dL)", 60, 400, 105)
            cv_risk = round((sys_p * 0.1) + (gluc * 0.04), 1) # Indice de riesgo educativo
            
        btn_calc = st.form_submit_button("ANALIZAR Y GENERAR PLAN")

    if btn_calc:
        plan, imc = calcular_proyeccion_salud(weight, height, sys_p, 100)
        
        # Guardar en DB
        db.conn.execute("""INSERT INTO records 
            (px_id, px_name, doctor, spec, weight, height, sys, gluc, creat, tfg, risk, date) 
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (px_id, px_name, st.session_state.name, st.session_state.spec, weight, height, sys_p, 100, 1.0, tfg, cv_risk, datetime.now().strftime('%Y-%m-%d')))
        db.conn.commit()
        
        st.success("Analisis Clinico Finalizado")
        
        # UI de Resultados
        res1, res2 = st.columns(2)
        res1.metric("IMC Actual", imc)
        res2.write(f"**Proyeccion de Mejora:** {plan['proyeccion']}")
        
        # Generar PDF
        metrics = {"IMC": imc, "Presion": sys_p, "TFG": tfg, "Riesgo CV": cv_risk}
        p_data = {"id": px_id, "name": px_name, "metrics": metrics, "plan": plan}
        pdf_buf = export_medical_report(p_data, st.session_state.name, st.session_state.spec)
        
        st.download_button(
            label="📥 DESCARGAR PLAN PARA PACIENTE",
            data=pdf_buf.getvalue(),
            file_name=f"Plan_{px_name}.pdf",
            mime="application/pdf",
            use_container_width=True
        )

# --- MÓDULO HISTORIAL ---
elif menu == "📈 Historial & Evolucion":
    st.header("Seguimiento de Evolucion Clinica")
    search_id = st.text_input("Buscar ID de Paciente")
    
    if search_id:
        df = pd.read_sql(f"SELECT * FROM records WHERE px_id='{search_id}'", db.conn)
        if not df.empty:
            st.write(f"Historial de {df['px_name'].iloc[0]}")
            # Gráfico de mejora
            fig = px.line(df, x="date", y=["weight", "tfg"], title="Evolucion de Peso y Funcion Renal", markers=True)
            st.plotly_chart(fig, use_container_width=True)
            st.dataframe(df, use_container_width=True)
        else:
            st.warning("No se encontraron registros.")

# --- MÓDULO ADMIN ---
elif menu == "⚙️ Panel Administrativo":
    if st.session_state.role != "admin":
        st.error("Acceso restringido al Administrador del SaaS.")
    else:
        st.header("Gestion de Suscripciones Medicas")
        with st.form("new_doc"):
            st.write("Registrar Nuevo Medico")
            nu, np = st.text_input("Usuario (Login)"), st.text_input("Password", type="password")
            nn = st.text_input("Nombre Completo")
            ns = st.selectbox("Especialidad Permitida", ["nefrologia", "cardiologia", "todas"])
            if st.form_submit_button("Activar Suscripcion"):
                if db.create_user(nu, np, nn, "doctor", ns):
                    st.success("Médico activado correctamente.")
                else: st.error("El usuario ya existe.")
