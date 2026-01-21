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

LEGAL_NOTICE = """⚠️ AVISO LEGAL: Esta plataforma es una herramienta de apoyo clinico. 
No reemplaza el juicio medico. Datos basados en guias cientificas (KDIGO/AHA). 
El uso de la informacion es responsabilidad del profesional."""

# =============================================
# 2. MOTOR DE BASE DE DATOS (CON AUTO-REPARACIÓN)
# =============================================
class AppDatabase:
    def __init__(self):
        self.conn = sqlite3.connect("nefrocardio_saas_v4.db", check_same_thread=False)
        self.init_db()
        self.repair_db() # Verifica y agrega columnas faltantes

    def init_db(self):
        cursor = self.conn.cursor()
        cursor.execute("""CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY, password TEXT, name TEXT, 
            role TEXT, specialty TEXT, active INT)""")
        cursor.execute("""CREATE TABLE IF NOT EXISTS records (
            id INTEGER PRIMARY KEY AUTOINCREMENT, px_id TEXT, px_name TEXT, 
            doctor TEXT, spec TEXT, weight REAL, height REAL, sys INT, 
            gluc REAL, creat REAL, tfg REAL, risk REAL, date TEXT)""")
        
        cursor.execute("SELECT * FROM users WHERE username='admin'")
        if not cursor.fetchone():
            hashed = bcrypt.hashpw("Admin2026!".encode(), bcrypt.gensalt()).decode()
            cursor.execute("INSERT INTO users VALUES (?,?,?,?,?,?)", 
                          ("admin", hashed, "Administrador SaaS", "admin", "todas", 1))
        self.conn.commit()

    def repair_db(self):
        """Agrega la columna specialty si no existe por versiones antiguas"""
        cursor = self.conn.cursor()
        cursor.execute("PRAGMA table_info(users)")
        columns = [column[1] for column in cursor.fetchall()]
        if 'specialty' not in columns:
            cursor.execute("ALTER TABLE users ADD COLUMN specialty TEXT DEFAULT 'todas'")
            self.conn.commit()

    def create_user(self, u, p, n, r, s):
        try:
            hp = bcrypt.hashpw(p.encode(), bcrypt.gensalt()).decode()
            self.conn.execute("INSERT INTO users (username, password, name, role, specialty, active) VALUES (?,?,?,?,?,?)", 
                             (u, hp, n, r, s, 1))
            self.conn.commit()
            return True
        except: return False

db = AppDatabase()

# =============================================
# 3. LÓGICA CIENTÍFICA
# =============================================
def calcular_proyeccion_salud(w, h):
    imc = round(w / ((h/100)**2), 1)
    plan = {
        "nutricion": "Dieta equilibrada baja en sodio.",
        "estilo_vida": "Ejercicio aerobico 150 min/semana. Sueño 7-8h.",
        "proyeccion": ""
    }
    if imc > 25:
        perder_kg = round(w * 0.10, 1)
        semanas = int(perder_kg / 0.5)
        plan["nutricion"] = "Restriccion de 500 kcal/dia. Enfoque en dieta DASH."
        plan["proyeccion"] = f"Meta: Bajar {perder_kg} kg ({round(perder_kg*2.2, 1)} lbs) en {semanas} semanas."
    else:
        plan["proyeccion"] = "Mantenimiento de salud metabolica."
    return plan, imc

# =============================================
# 4. GENERADOR DE REPORTES PDF
# =============================================
def export_medical_report(p_data, doc_name, spec):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_fill_color(0, 102, 204)
    pdf.rect(0, 0, 210, 40, 'F')
    pdf.set_font("Arial", 'B', 16)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 15, "INFORME MEDICO Y PLAN DE SALUD", 0, 1, 'C')
    
    pdf.set_text_color(0, 0, 0)
    pdf.ln(25)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, f"Paciente: {p_data['name']} | Dr. {doc_name} ({spec})", 0, 1)
    pdf.line(10, 65, 200, 65)
    
    pdf.ln(5)
    for k, v in p_data['metrics'].items():
        pdf.set_font("Arial", 'B', 10)
        pdf.cell(50, 8, f"{k}:", 1)
        pdf.set_font("Arial", '', 10)
        pdf.cell(50, 8, str(v), 1, 1)
        
    pdf.ln(10)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, "RECOMENDACIONES:", 0, 1)
    pdf.set_font("Arial", '', 10)
    for tit, cont in p_data['plan'].items():
        pdf.multi_cell(0, 7, f"{tit.upper()}: {cont.replace('ñ','n').replace('ó','o')}")
    
    res = pdf.output(dest='S')
    return BytesIO(res.encode('latin-1', errors='replace')) if isinstance(res, str) else BytesIO(res)

# =============================================
# 5. INTERFAZ DE USUARIO
# =============================================
if "auth" not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:
    c1, c2, c3 = st.columns([1, 1.5, 1])
    with c2:
        st.title("🏥 NefroCardio SaaS")
        user = st.text_input("Usuario")
        password = st.text_input("Contraseña", type="password")
        if st.button("Acceder", use_container_width=True):
            cursor = db.conn.cursor()
            cursor.execute("SELECT password, name, role, specialty FROM users WHERE username=?", (user,))
            data = cursor.fetchone()
            if data and bcrypt.checkpw(password.encode(), data[0].encode()):
                st.session_state.auth = True
                st.session_state.user = user
                st.session_state.name = data[1]
                st.session_state.role = data[2]
                st.session_state.spec = data[3] if data[3] else "todas"
                st.rerun()
            else: st.error("Credenciales incorrectas")
    st.stop()

# --- SIDEBAR (SEGURA) ---
with st.sidebar:
    st.markdown(f"### Bienvenido Dr. {st.session_state.name}")
    # Uso de .get() para evitar AttributeError
    role_view = st.session_state.get('spec', 'todas').upper()
    st.write(f"🩺 Especialidad: {role_view}")
    menu = st.radio("MENÚ", ["Consulta", "Historial", "Admin"])
    if st.button("Cerrar Sesión"):
        st.session_state.clear()
        st.rerun()

# --- MÓDULOS ---
if menu == "Consulta":
    st.header("Nueva Evaluación Clínica")
    with st.form("cons"):
        c1, c2 = st.columns(2)
        px_id = c1.text_input("ID Paciente")
        px_n = c2.text_input("Nombre")
        w = st.number_input("Peso (kg)", 40.0, 200.0, 75.0)
        h = st.number_input("Talla (cm)", 120, 210, 170)
        
        tfg, risk = 0, 0
        if st.session_state.get('spec') in ["nefrologia", "todas"]:
            cr = st.number_input("Creatinina", 0.5, 12.0, 1.0)
            tfg = round(141 * min(cr/0.9, 1)**-0.411 * 0.993**45, 1)
        if st.session_state.get('spec') in ["cardiologia", "todas"]:
            gl = st.number_input("Glucosa", 60, 400, 100)
            risk = round(gl * 0.1, 1)
            
        if st.form_submit_button("Analizar"):
            plan, imc = calcular_proyeccion_salud(w, h)
            db.conn.execute("INSERT INTO records (px_id, px_name, doctor, spec, weight, height, sys, gluc, creat, tfg, risk, date) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                           (px_id, px_n, st.session_state.name, st.session_state.spec, w, h, 120, 100, 1.0, tfg, risk, datetime.now().strftime('%Y-%m-%d')))
            db.conn.commit()
            st.success("Guardado")
            
            p_data = {"id": px_id, "name": px_n, "metrics": {"IMC": imc, "TFG": tfg, "Riesgo": risk}, "plan": plan}
            buf = export_medical_report(p_data, st.session_state.name, st.session_state.spec)
            st.download_button("Descargar PDF", buf.getvalue(), f"{px_n}.pdf", "application/pdf")

elif menu == "Historial":
    st.header("Historial de Pacientes")
    search = st.text_input("ID Paciente")
    if search:
        df = pd.read_sql(f"SELECT * FROM records WHERE px_id='{search}'", db.conn)
        if not df.empty:
            st.plotly_chart(px.line(df, x="date", y="weight", title="Evolución de Peso"), use_container_width=True)
            st.table(df)

elif menu == "Admin":
    if st.session_state.get('role') != "admin":
        st.error("No autorizado")
    else:
        st.subheader("Registrar Médico")
        with st.form("add"):
            nu, np = st.text_input("Usuario"), st.text_input("Clave")
            nn = st.text_input("Nombre Dr.")
            ns = st.selectbox("Especialidad", ["nefrologia", "cardiologia", "todas"])
            if st.form_submit_button("Crear"):
                if db.create_user(nu, np, nn, "doctor", ns): st.success("Creado")
                else: st.error("Error")
