import pandas as pd
import sqlite3
import bcrypt
import streamlit as st
import plotly.express as px
from datetime import datetime
from fpdf import FPDF
from io import BytesIO

# =============================================
# 1. CONFIGURACIÓN Y MARCO LEGAL
# =============================================
st.set_page_config(page_title="NefroCardio SaaS RD", page_icon="🏥", layout="wide")

LEGAL_NOTICE = """AVISO: Esta herramienta es de apoyo clinico. Recomendaciones basadas en guias KDIGO/AHA. 
El uso de la informacion es responsabilidad exclusiva del facultativo."""

# =============================================
# 2. MOTOR DE BASE DE DATOS
# =============================================
class AppDatabase:
    def __init__(self):
        self.conn = sqlite3.connect("nefrocardio_final_v6.db", check_same_thread=False)
        self.init_db()
        self.repair_db()

    def init_db(self):
        cursor = self.conn.cursor()
        cursor.execute("""CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY, password TEXT, name TEXT, 
            role TEXT, specialty TEXT, active INT)""")
        cursor.execute("""CREATE TABLE IF NOT EXISTS records (
            id INTEGER PRIMARY KEY AUTOINCREMENT, px_id TEXT, px_name TEXT, 
            doctor TEXT, spec TEXT, weight REAL, height REAL, sys INT, 
            gluc REAL, creat REAL, tfg REAL, risk REAL, date TEXT,
            sleep_hours REAL, stress_level TEXT, exercise_min INT)""")
        
        cursor.execute("SELECT * FROM users WHERE username='admin'")
        if not cursor.fetchone():
            hashed = bcrypt.hashpw("Admin2026!".encode(), bcrypt.gensalt()).decode()
            cursor.execute("INSERT INTO users VALUES (?,?,?,?,?,?)", 
                          ("admin", hashed, "Administrador SaaS", "admin", "todas", 1))
        self.conn.commit()

    def repair_db(self):
        cursor = self.conn.cursor()
        cursor.execute("PRAGMA table_info(records)")
        cols = [c[1] for c in cursor.fetchall()]
        for col in ['sleep_hours', 'stress_level', 'exercise_min']:
            if col not in cols:
                cursor.execute(f"ALTER TABLE records ADD COLUMN {col} DEFAULT 0")
        self.conn.commit()

db = AppDatabase()

# =============================================
# 3. LÓGICA DE NEGOCIO Y PDF
# =============================================
def get_insights(w, h, sleep, stress, exercise):
    imc = round(w / ((h/100)**2), 1)
    plan = {
        "nutricion": f"Dieta DASH. Reducir {round(w*0.1, 1)}kg en 3 meses." if imc > 25 else "Dieta normocalorica saludable.",
        "ejercicio": f"Meta: 150 min/semana. Actual: {exercise} min.",
        "sueno": "Mejorar higiene del sueño (7-8h)." if sleep < 7 else "Horas de sueño optimas.",
        "estres": "Tecnicas de relajacion diaria recomendadas." if stress == "Alto" else "Gestion de estres adecuada."
    }
    return plan, imc

def export_pdf(p_data, doc_name):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_fill_color(0, 51, 102)
    pdf.rect(0, 0, 210, 40, 'F')
    pdf.set_font("Arial", 'B', 18)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 15, "PLAN DE SALUD INTEGRAL", 0, 1, 'C')
    
    pdf.set_text_color(0, 0, 0)
    pdf.ln(25)
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(0, 10, f"Paciente: {p_data['name']} | ID: {p_data['id']}", 0, 1)
    pdf.cell(0, 10, f"Doctor: {doc_name}", 0, 1)
    
    pdf.ln(5)
    for k, v in p_data['plan'].items():
        pdf.set_font("Arial", 'B', 10)
        pdf.cell(0, 7, f"{k.upper()}:", 0, 1)
        pdf.set_font("Arial", '', 10)
        pdf.multi_cell(0, 6, str(v).replace('ñ','n').replace('á','a').replace('é','e').replace('í','i').replace('ó','o').replace('ú','u'))
        pdf.ln(2)
        
    res = pdf.output(dest='S')
    return BytesIO(res.encode('latin-1', errors='replace')) if isinstance(res, str) else BytesIO(res)

# =============================================
# 4. INTERFAZ (LOGIN Y NAVEGACIÓN)
# =============================================
if "auth" not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.title("🏥 NefroCardio SaaS")
        u = st.text_input("Usuario")
        p = st.text_input("Clave", type="password")
        if st.button("Ingresar"):
            cursor = db.conn.cursor()
            cursor.execute("SELECT password, name, role, specialty FROM users WHERE username=?", (u,))
            res = cursor.fetchone()
            if res and bcrypt.checkpw(p.encode(), res[0].encode()):
                st.session_state.update({"auth":True, "user":u, "name":res[1], "role":res[2], "spec":res[3] if res[3] else "todas"})
                st.rerun()
    st.stop()

# --- SIDEBAR ---
with st.sidebar:
    st.header(f"Dr. {st.session_state.get('name', 'Usuario')}")
    st.caption(f"Especialidad: {st.session_state.get('spec', 'todas').upper()}")
    menu = st.radio("Menú", ["🩺 Consulta", "📅 Historial", "⚙️ Admin"])
    if st.button("Cerrar Sesión"):
        st.session_state.clear()
        st.rerun()

# --- MÓDULO CONSULTA ---
if menu == "🩺 Consulta":
    st.header("Evaluación Clínica")
    
    # 1. BUSCADOR POR NOMBRE
    cursor = db.conn.cursor()
    cursor.execute("SELECT DISTINCT px_name FROM records")
    lista_pacientes = [row[0] for row in cursor.fetchall()]
    
    selected_name = st.selectbox("🔍 Buscar Paciente Existente (Escriba el nombre):", ["-- Nuevo Paciente --"] + lista_pacientes)
    
    px_id_val, px_name_val, w_val, h_val = "", "", 70.0, 165.0
    
    if selected_name != "-- Nuevo Paciente --":
        cursor.execute("SELECT px_id, weight, height FROM records WHERE px_name=? ORDER BY id DESC LIMIT 1", (selected_name,))
        prev = cursor.fetchone()
        if prev:
            px_id_val, px_name_val, w_val, h_val = prev[0], selected_name, prev[1], prev[2]
            st.info(f"Datos cargados para: {selected_name} (ID: {px_id_val})")

    with st.form("consulta_form"):
        c1, c2 = st.columns(2)
        f_name = c1.text_input("Nombre Completo", value=px_name_val)
        f_id = c2.text_input("ID / Cédula", value=px_id_val)
        
        st.markdown("### 📊 Biometría y Estilo de Vida")
        col1, col2, col3 = st.columns(3)
        weight = col1.number_input("Peso (kg)", 30.0, 250.0, w_val)
        height = col2.number_input("Talla (cm)", 100, 220, int(h_val))
        sys_p = col3.number_input("Presión Sistólica", 80, 200, 120)
        
        b1, b2, b3 = st.columns(3)
        sleep = b1.slider("Horas de Sueño", 3.0, 12.0, 7.0)
        exercise = b2.number_input("Minutos Ejercicio/Semana", 0, 600, 150)
        stress = b3.selectbox("Nivel de Estrés", ["Bajo", "Moderado", "Alto"])
        
        # Filtros de especialidad con .get() para evitar el error AttributeError
        tfg, gl = 0, 100
        current_spec = st.session_state.get('spec', 'todas')
        
        if current_spec in ["nefrologia", "todas"]:
            cr = st.number_input("Creatinina (mg/dL)", 0.4, 15.0, 1.0)
            tfg = round(141 * min(cr/0.9, 1)**-0.411 * 0.993**45, 1)
        if current_spec in ["cardiologia", "todas"]:
            gl = st.number_input("Glucosa (mg/dL)", 60, 400, 105)

        if st.form_submit_button("GUARDAR Y GENERAR REPORTE"):
            if f_name and f_id:
                plan, imc = get_insights(weight, height, sleep, stress, exercise)
                
                # Inserción con Blindaje de st.session_state
                db.conn.execute("""INSERT INTO records 
                    (px_id, px_name, doctor, spec, weight, height, sys, gluc, creat, tfg, date, sleep_hours, stress_level, exercise_min) 
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (f_id, f_name, st.session_state.get('name'), current_spec, weight, height, sys_p, gl, 1.0, tfg, 
                     datetime.now().strftime('%Y-%m-%d'), sleep, stress, exercise))
                db.conn.commit()
                
                st.success("Consulta guardada exitosamente.")
                
                # PDF
                p_data = {"id": f_id, "name": f_name, "plan": plan}
                pdf_buf = export_pdf(p_data, st.session_state.get('name'))
                st.download_button("📥 Descargar Reporte Completo", pdf_buf.getvalue(), f"Reporte_{f_name}.pdf", "application/pdf")
            else:
                st.error("Por favor complete Nombre e ID.")

elif menu == "📅 Historial":
    st.header("Historial de Pacientes")
    h_name = st.text_input("Buscar por Nombre")
    if h_name:
        df = pd.read_sql(f"SELECT * FROM records WHERE px_name LIKE '%{h_name}%'", db.conn)
        if not df.empty:
            st.plotly_chart(px.line(df, x="date", y="weight", title="Evolución de Peso"), use_container_width=True)
            st.dataframe(df)

elif menu == "⚙️ Admin":
    if st.session_state.get('role') != "admin":
        st.error("Acceso denegado.")
    else:
        st.subheader("Registrar Nuevo Médico")
        with st.form("admin_form"):
            new_u = st.text_input("Usuario")
            new_p = st.text_input("Password")
            new_n = st.text_input("Nombre Completo")
            new_s = st.selectbox("Especialidad", ["nefrologia", "cardiologia", "todas"])
            if st.form_submit_button("Crear Acceso"):
                hashed_p = bcrypt.hashpw(new_p.encode(), bcrypt.gensalt()).decode()
                db.conn.execute("INSERT INTO users VALUES (?,?,?,?,?,?)", (new_u, hashed_p, new_n, "doctor", new_s, 1))
                db.conn.commit()
                st.success("Médico registrado.")
