import pandas as pd
import numpy as np
import joblib
import json
import os
import bcrypt
import secrets
from datetime import datetime
import streamlit as st
import plotly.graph_objects as go
from io import BytesIO
from fpdf import FPDF 

# =============================================
# CONFIGURACIÓN Y CONSTANTES
# =============================================
st.set_page_config(
    page_title="NefroPredict RD",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="collapsed"
)

PRIMARY = "#0066CC"
SECONDARY = "#00A896"
DANGER = "#E63946"
WARNING = "#F77F00"
SUCCESS = "#06D6A0"

# --- [INICIO DE ESTILOS CSS - MANTENIDOS SEGÚN TU DISEÑO] ---
# (Se asume que el CSS del prompt original se inserta aquí)
# --- [FIN DE ESTILOS CSS] ---

# =============================================
# UTILIDADES Y SEGURIDAD
# =============================================

def hex_to_rgba(hex_color, alpha):
    hex_color = hex_color.lstrip('#')
    r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    return f'rgba({r}, {g}, {b}, {alpha})'

class DataStore:
    """Clase mejorada para manejo de persistencia JSON"""
    def __init__(self):
        self.db_file = "nefro_db.json"
        if not os.path.exists(self.db_file):
            self._create_initial_db()
        self.data = self._load()

    def _create_initial_db(self):
        initial = {
            "users": {
                "admin": {
                    "pwd": bcrypt.hashpw("Admin2024!".encode(), bcrypt.gensalt()).decode(),
                    "role": "admin", "name": "Administrador", "active": True,
                    "created_at": datetime.now().isoformat(), "login_attempts": 0
                }
            },
            "patients": [], "audit_log": []
        }
        self._save_to_disk(initial)

    def _load(self):
        with open(self.db_file, "r", encoding="utf-8") as f:
            return json.load(f)

    def _save_to_disk(self, data_to_save):
        with open(self.db_file, "w", encoding="utf-8") as f:
            json.dump(data_to_save, f, indent=4, ensure_ascii=False)

    def save(self):
        self._save_to_disk(self.data)

    def log_audit(self, user, action, action_type="INFO"):
        entry = {
            "timestamp": datetime.now().isoformat(),
            "user": user, "action": action, "type": action_type
        }
        self.data.setdefault("audit_log", []).insert(0, entry)
        self.data["audit_log"] = self.data["audit_log"][:2000]
        self.save()

    def verify_login(self, username, password):
        user = self.data["users"].get(username)
        if not user or not user.get("active"): return None
        if bcrypt.checkpw(password.encode(), user["pwd"].encode()):
            return user
        return None

db = DataStore()

# =============================================
# LÓGICA CLÍNICA
# =============================================

def calcular_tfg_ckdepi(creatinina, edad, sexo, raza):
    # Fórmula CKD-EPI 2009
    k = 0.7 if sexo == "Mujer" else 0.9
    alpha = -0.329 if sexo == "Mujer" else -0.411
    raza_factor = 1.159 if "Afro" in raza else 1.0
    sexo_factor = 1.018 if sexo == "Mujer" else 1.0
    
    tfg = 141 * (min(creatinina/k, 1)**alpha) * (max(creatinina/k, 1)**-1.209) * (0.993**edad) * sexo_factor * raza_factor
    return round(tfg, 1)

def clasificar_erc(tfg):
    if tfg >= 90: return "G1 (Normal)"
    if tfg >= 60: return "G2 (Leve)"
    if tfg >= 45: return "G3a (Moderado Leve)"
    if tfg >= 30: return "G3b (Moderado Severo)"
    if tfg >= 15: return "G4 (Severo)"
    return "G5 (Fallo Renal)"

# =============================================
# GENERACIÓN DE PDF PROFESIONAL
# =============================================

class PDFReport(FPDF):
    def header(self):
        self.set_fill_color(0, 102, 204)
        self.rect(0, 0, 210, 25, 'F')
        self.set_text_color(255, 255, 255)
        self.set_font('Arial', 'B', 16)
        self.cell(0, 10, 'NEFROPREDICT RD - REPORTE CLINICO', 0, 1, 'C')
        self.ln(10)

    def patient_box(self, data):
        self.set_fill_color(240, 240, 240)
        self.set_text_color(0, 0, 0)
        self.set_font('Arial', 'B', 12)
        self.cell(0, 10, f" Datos del Paciente: {data['nombre_paciente']}", 1, 1, 'L', True)
        self.set_font('Arial', '', 10)
        info = f"Edad: {data['edad']} | Sexo: {data['sexo']} | Creatinina: {data['creatinina']} mg/dL | TFG: {data['tfg']}"
        self.cell(0, 10, info, 1, 1, 'L')
        self.ln(5)

def generar_pdf_bytes(datos):
    pdf = PDFReport()
    pdf.add_page()
    pdf.patient_box(datos)
    
    # Resultado de Riesgo
    pdf.set_font('Arial', 'B', 14)
    color = (230, 57, 70) if datos['riesgo'] > 70 else (6, 214, 160)
    pdf.set_text_color(*color)
    pdf.cell(0, 10, f"NIVEL DE RIESGO: {datos['nivel']} ({datos['riesgo']}%)", 0, 1, 'C')
    
    # Recomendación
    pdf.ln(5)
    pdf.set_text_color(0, 0, 0)
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, "Recomendacion Medica:", 0, 1, 'L')
    pdf.set_font('Arial', '', 11)
    pdf.multi_cell(0, 7, datos['reco_privada'])
    
    return pdf.output(dest='S').encode('latin-1')

# =============================================
# INTERFAZ STREAMLIT (TAB 1: EVALUACIÓN)
# =============================================

# ... (Lógica de login omitida por brevedad, se mantiene la tuya) ...

def render_evaluacion():
    st.markdown("## 📋 Evaluación de Riesgo")
    col_form, col_res = st.columns([1, 1])
    
    with col_form:
        with st.form("eval_form"):
            nombre = st.text_input("Nombre del Paciente")
            c1, c2 = st.columns(2)
            edad = c1.number_input("Edad", 18, 100, 50)
            sexo = c2.selectbox("Sexo", ["Hombre", "Mujer"])
            creat = c1.number_input("Creatinina (mg/dL)", 0.1, 15.0, 1.0)
            raza = c2.selectbox("Raza", ["No-Afroamericano", "Afroamericano"])
            
            # Otros campos... (Glucosa, Presión, IMC)
            
            btn = st.form_submit_button("Calcular")
            
            if btn and nombre:
                tfg = calcular_tfg_ckdepi(creat, edad, sexo, raza)
                estadio = clasificar_erc(tfg)
                # Lógica de riesgo simplificada para el ejemplo
                riesgo_val = min(99, max(5, (1.2/creat * 20) + (edad/2))) 
                
                res = {
                    "nombre_paciente": nombre, "edad": edad, "sexo": sexo,
                    "creatinina": creat, "tfg": tfg, "estadio_erc": estadio,
                    "riesgo": round(riesgo_val, 1),
                    "nivel": "ALTO" if riesgo_val > 60 else "BAJO",
                    "reco_privada": "Se sugiere seguimiento nefrológico inmediato."
                }
                st.session_state.ultimo_resultado = res
                db.add_patient(res)

    with col_res:
        if "ultimo_resultado" in st.session_state:
            res = st.session_state.ultimo_resultado
            st.metric("TFG Calculada", f"{res['tfg']} mL/min")
            st.subheader(f"Riesgo: {res['riesgo']}%")
            
            # Botón de Descarga PDF
            pdf_data = generar_pdf_bytes(res)
            st.download_button(
                label="📥 Descargar Reporte PDF",
                data=pdf_data,
                file_name=f"Reporte_{res['nombre_paciente']}.pdf",
                mime="application/pdf"
            )

# Ejecución
if st.session_state.get("logged_in"):
    render_evaluacion()
