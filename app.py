import pandas as pd
import numpy as np
import joblib
import sqlite3
import bcrypt
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from fpdf import FPDF
from io import BytesIO

# =============================================
# 1. CONFIGURACIÓN Y ESTÉTICA PROFESIONAL
# =============================================
st.set_page_config(
    page_title="NefroPredict RD Pro v2.0",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Paleta de colores médica
C_PRIM = "#0066CC"  # Azul Médico
C_SEC = "#00A896"   # Verde Salud
C_CRIT = "#E63946"  # Rojo Crítico
C_WARN = "#F77F00"  # Naranja Advertencia

st.markdown(f"""
<style>
    .stApp {{ background-color: #0b0e14; color: #e0e0e0; }}
    [data-testid="stSidebar"] {{ background-color: #151921; border-right: 1px solid #2d3748; }}
    .metric-card {{ 
        background: #1a202c; 
        padding: 20px; 
        border-radius: 15px; 
        border-left: 5px solid {C_PRIM};
        box-shadow: 0 4px 12px rgba(0,0,0,0.3);
    }}
    .risk-card {{ 
        padding: 30px; 
        border-radius: 20px; 
        text-align: center; 
        margin: 10px 0;
        box-shadow: 0 10px 25px rgba(0,0,0,0.2);
    }}
    .stButton>button {{ 
        border-radius: 8px; 
        font-weight: 600; 
        transition: 0.3s; 
        background: linear-gradient(135deg, {C_PRIM}, {C_SEC});
        color: white;
        border: none;
    }}
    .stButton>button:hover {{ transform: translateY(-2px); box-shadow: 0 5px 15px rgba(0,102,204,0.4); }}
</style>
""", unsafe_allow_html=True)

# =============================================
# 2. GESTIÓN DE DATOS (SQLite)
# =============================================
class SystemDB:
    def __init__(self):
        self.conn = sqlite3.connect("nefro_pro.db", check_same_thread=False)
        self.init_tables()

    def init_tables(self):
        c = self.conn.cursor()
        c.execute("""CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY, password TEXT, name TEXT, role TEXT, active INT)""")
        c.execute("""CREATE TABLE IF NOT EXISTS patients (
            id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, doctor TEXT, age INT, 
            sex TEXT, creat REAL, tfg REAL, risk REAL, stage TEXT, date TEXT)""")
        
        # Crear admin por defecto si no existe
        c.execute("SELECT * FROM users WHERE username='admin'")
        if not c.fetchone():
            hash_pw = bcrypt.hashpw("Admin2026!".encode(), bcrypt.gensalt()).decode()
            c.execute("INSERT INTO users VALUES (?,?,?,?,?)", ("admin", hash_pw, "Admin Central", "admin", 1))
        self.conn.commit()

    def add_user(self, user, pw, name, role):
        try:
            hash_pw = bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()
            self.conn.execute("INSERT INTO users VALUES (?,?,?,?,?)", (user, hash_pw, name, role, 1))
            self.conn.commit()
            return True
        except: return False

db = SystemDB()

# =============================================
# 3. LÓGICA CLÍNICA Y GRÁFICOS
# =============================================
def get_scientific_recom(stage, risk):
    if risk > 75:
        return "URGENTE: Referencia inmediata a Nefrologia. Evaluar inicio de terapia de reemplazo renal. Iniciar IECA/ARA-II si no hay contraindicacion. Restriccion estricta de sodio <2g/dia y control de potasio."
    if "G3" in stage or risk > 45:
        return "MONITOREO INTENSIVO: Evaluar relacion Albumina/Creatinina en orina. Ajustar dosis de Metformina y evitar AINEs (Ibuprofeno/Diclofenaco). Control de Presion Arterial meta <130/80 mmHg."
    return "PREVENCION PRIMARIA: Mantener Hemoglobina Glicosilada <7% en diabeticos. Actividad fisica regular (150 min/semana). Screening renal anual con Creatinina y TFG."

def draw_radar(data):
    categories = ['Creatinina', 'Glucosa', 'Presion Sist.', 'IMC', 'Edad']
    # Normalización para que el gráfico sea legible
    values = [
        min(data['creat'] * 10, 100), 
        min(data['gluc'] / 2, 100), 
        min(data['pres'] / 2, 100), 
        min(data['bmi'] * 2, 100), 
        data['age']
    ]
    
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(r=values, theta=categories, fill='toself', line_color=C_SEC, name="Perfil del Paciente"))
    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
        showlegend=False, 
        paper_bgcolor='rgba(0,0,0,0)', 
        plot_bgcolor='rgba(0,0,0,0)', 
        title="Analisis de Puntos Criticos Metabólicos",
        font=dict(color="white")
    )
    return fig

# =============================================
# 4. GENERADOR DE PDF PROFESIONAL (CORREGIDO)
# =============================================
def generate_pdf(p_data, doctor_name):
    pdf = FPDF()
    pdf.add_page()
    
    # Encabezado Institucional
    pdf.set_fill_color(0, 102, 204)
    pdf.rect(0, 0, 210, 40, 'F')
    
    pdf.set_font("Arial", 'B', 22)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 20, "NefroPredict RD - Reporte Clinico", 0, 1, 'C')
    
    # Datos de Evaluación
    pdf.set_text_color(0, 0, 0)
    pdf.ln(25)
    pdf.set_font("Arial", 'B', 12)
    fecha_hoy = datetime.now().strftime('%d/%m/%Y %H:%M')
    pdf.cell(0, 10, f"Paciente: {p_data['name'].upper()} | Fecha: {fecha_hoy}", 0, 1)
    pdf.line(10, 55, 200, 55)
    
    # Tabla de Resultados Clinicos
    pdf.ln(10)
    pdf.set_font("Arial", 'B', 11)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(90, 10, "Parametro", 1, 0, 'C', True)
    pdf.cell(90, 10, "Valor / Resultado", 1, 1, 'C', True)
    
    pdf.set_font("Arial", '', 11)
    results = [
        ("Tasa Filtrado (TFG)", f"{p_data['tfg']} ml/min/1.73m2"),
        ("Estadio ERC", p_data['stage']),
        ("Riesgo Predictivo", f"{p_data['risk']}%"),
        ("Creatinina Serica", f"{p_data['creat']} mg/dL")
    ]
    for param, val in results:
        pdf.cell(90, 8, param, 1)
        pdf.cell(90, 8, val, 1, 1)
    
    # Seccion de Recomendaciones
    pdf.ln(10)
    pdf.set_font("Arial", 'B', 12)
    pdf.set_text_color(0, 102, 204)
    pdf.cell(0, 10, "Observaciones y Recomendaciones (Guias KDIGO):", 0, 1)
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", '', 11)
    pdf.multi_cell(0, 7, p_data['recom'])
    
    # Pie de pagina y Firma
    pdf.ln(35)
    curr_y = pdf.get_y()
    pdf.line(70, curr_y, 140, curr_y)
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(0, 8, f"Dr(a). {doctor_name}", 0, 1, 'C')
    pdf.set_font("Arial", 'I', 8)
    pdf.cell(0, 5, "Firma y Sello del Profesional Autorizado", 0, 1, 'C')
    
    # Retorno seguro de bytes (CORRECCIÓN ATTRIBUTE ERROR)
    pdf_output = pdf.output(dest='S')
    if isinstance(pdf_output, str):
        return pdf_output.encode('latin-1', errors='replace')
    return pdf_output

# =============================================
# 5. LOGICA DE NAVEGACIÓN Y LOGIN
# =============================================
if "auth" not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.markdown("<div style='text-align: center; padding: 20px;'>", unsafe_allow_html=True)
        st.image("https://cdn-icons-png.flaticon.com/512/2773/2773193.png", width=100)
        st.markdown("<h1 style='color: #0066CC;'>NefroPredict RD</h1><h3>Acceso Profesional</h3>", unsafe_allow_html=True)
        u = st.text_input("Usuario (ID)")
        p = st.text_input("Contraseña", type="password")
        if st.button("INICIAR SESIÓN", use_container_width=True):
            cursor = db.conn.cursor()
            cursor.execute("SELECT password, name, role FROM users WHERE username=?", (u,))
            res = cursor.fetchone()
            if res and bcrypt.checkpw(p.encode(), res[0].encode()):
                st.session_state.auth = True
                st.session_state.user = u
                st.session_state.name = res[1]
                st.session_state.role = res[2]
                st.rerun()
            else: st.error("Credenciales incorrectas o cuenta inactiva.")
    st.stop()

# Menú Lateral
with st.sidebar:
    st.markdown(f"### Bienvenido/a<br><span style='color:{C_SEC}'>Dr. {st.session_state.name}</span>", unsafe_allow_html=True)
    st.markdown("---")
    opt = st.radio("MENÚ PRINCIPAL", ["🩺 Nueva Evaluación", "📅 Historial Clínico", "👥 Gestión de Usuarios"])
    st.markdown("---")
    if st.button("🚪 Cerrar Sesión", use_container_width=True):
        st.session_state.auth = False
        st.rerun()

# =============================================
# 6. MÓDULOS DE LA APLICACIÓN
# =============================================
if opt == "🩺 Nueva Evaluación":
    st.header("🔬 Evaluación de Riesgo Nefrológico")
    c1, c2 = st.columns([1, 1.2])
    
    with c1:
        st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
        with st.form("eval_form"):
            px_name = st.text_input("Nombre Completo del Paciente", placeholder="Ej. Juan Pérez")
            c_a, c_b = st.columns(2)
            age = c_a.number_input("Edad", 18, 110, 50)
            sex = c_b.selectbox("Sexo Biológico", ["Hombre", "Mujer"])
            
            creat = st.number_input("Creatinina Sérica (mg/dL)", 0.2, 15.0, 1.1, help="Valor clave para el filtrado glomerular.")
            gluc = st.number_input("Glucosa en Ayunas (mg/dL)", 50, 500, 100)
            pres = st.number_input("Presión Sistólica (mmHg)", 80, 250, 125)
            bmi = st.number_input("IMC (Indice Masa Corporal)", 10.0, 50.0, 26.0)
            
            btn = st.form_submit_button("EJECUTAR ANÁLISIS")
        st.markdown("</div>", unsafe_allow_html=True)

    if btn:
        # Fórmulas de Cálculo Clínico
        k = 0.7 if sex == "Mujer" else 0.9
        a = -0.329 if sex == "Mujer" else -0.411
        tfg = 141 * min(creat/k, 1)**a * max(creat/k, 1)**-1.209 * 0.993**age
        if sex == "Mujer": tfg *= 1.018
        
        tfg = round(tfg, 1)
        risk = round(min(99.5, (creat*18) + (age*0.15) + (gluc*0.08) + (pres*0.05)), 1)
        stage = "G1 (Normal)" if tfg >= 90 else "G2 (Leve)" if tfg >= 60 else "G3a (Moderado)" if tfg >= 45 else "G3b (Severo)" if tfg >= 30 else "G4 (Crítico)" if tfg >= 15 else "G5 (Falla)"
        recom = get_scientific_recom(stage, risk)
        
        # Guardar en DB
        db.conn.execute("INSERT INTO patients (name, doctor, age, sex, creat, tfg, risk, stage, date) VALUES (?,?,?,?,?,?,?,?,?)",
                       (px_name, st.session_state.name, age, sex, creat, tfg, risk, stage, datetime.now().strftime('%Y-%m-%d %H:%M')))
        db.conn.commit()

        with c2:
            st.plotly_chart(draw_radar(locals()), use_container_width=True)
            
            color = C_CRIT if risk > 70 else C_WARN if risk > 40 else C_SEC
            st.markdown(f"""
                <div class='risk-card' style='border: 2px solid {color}; background: {color}11;'>
                    <h2 style='color: white;'>Riesgo de Progresión ERC</h2>
                    <h1 style='color: {color}; font-size: 4rem;'>{risk}%</h1>
                    <p style='font-size: 1.2rem;'>Estadio Detectado: <b>{stage}</b></p>
                </div>
            """, unsafe_allow_html=True)
            
            # Preparar PDF
            p_data = {'name': px_name, 'tfg': tfg, 'stage': stage, 'risk': risk, 'creat': creat, 'recom': recom}
            pdf_bytes = generate_pdf(p_data, st.session_state.name)
            st.download_button(
                label="📄 DESCARGAR REPORTE PARA PACIENTE",
                data=pdf_bytes,
                file_name=f"Reporte_Nefrologia_{px_name.replace(' ','_')}.pdf",
                mime="application/pdf",
                use_container_width=True
            )

elif opt == "📅 Historial Clínico":
    st.header("Historico General de Consultas")
    df = pd.read_sql("SELECT id, name as Paciente, age as Edad, tfg as TFG, stage as Estadio, risk as Riesgo, date as Fecha FROM patients ORDER BY id DESC", db.conn)
    
    # Filtros rápidos
    c1, c2 = st.columns(2)
    search = c1.text_input("🔍 Buscar por nombre de paciente")
    if search:
        df = df[df['Paciente'].str.contains(search, case=False)]
    
    st.dataframe(df, use_container_width=True, hide_index=True)
    
    if not df.empty:
        fig_trend = px.line(df, x="Fecha", y="Riesgo", title="Tendencia de Riesgo en Consultas", markers=True)
        st.plotly_chart(fig_trend, use_container_width=True)

elif opt == "👥 Gestión de Usuarios":
    if st.session_state.role != "admin":
        st.warning("🔒 Esta sección es exclusiva para el Administrador del Sistema.")
    else:
        st.header("Administración de Personal Médico")
        
        with st.expander("➕ Registrar Nuevo Médico / Usuario"):
            with st.form("new_user"):
                new_u = st.text_input("Usuario (ID para login)")
                new_p = st.text_input("Contraseña Temporal", type="password")
                new_n = st.text_input("Nombre y Apellidos del Doctor")
                new_r = st.selectbox("Rol de Sistema", ["doctor", "admin"])
                if st.form_submit_button("CREAR CUENTA"):
                    if new_u and new_p and new_n:
                        if db.add_user(new_u, new_p, new_n, new_r):
                            st.success(f"Médico {new_n} registrado exitosamente.")
                        else: st.error("El nombre de usuario ya existe.")
                    else: st.error("Todos los campos son obligatorios.")
        
        st.subheader("Personal con Acceso al Sistema")
        users_df = pd.read_sql("SELECT username as ID, name as Nombre, role as Rol, active as Activo FROM users", db.conn)
        st.table(users_df)
