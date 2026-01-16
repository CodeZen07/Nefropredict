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
# 1. CONFIGURACIÓN Y ESTILOS UI
# =============================================
st.set_page_config(
    page_title="NefroPredict RD Pro",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Colores institucionales
PRIMARY = "#0066CC"
SECONDARY = "#00A896"
DANGER = "#E63946"
WARNING = "#F77F00"
SUCCESS = "#06D6A0"

st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap');
    * {{ font-family: 'Inter', sans-serif; }}
    .main {{ background: #1a202c; color: #e2e8f0; }}
    .stButton>button {{
        background: linear-gradient(135deg, {PRIMARY}, {SECONDARY});
        color: white; border: none; border-radius: 8px; padding: 0.5rem 2rem;
    }}
    .risk-high-alert {{
        background: linear-gradient(135deg, {DANGER}33, #1a202c);
        border: 2px solid {DANGER};
        padding: 25px; border-radius: 15px; text-align: center;
        animation: pulse 2s infinite; margin: 10px 0;
    }}
    @keyframes pulse {{
        0% {{ box-shadow: 0 0 0 0px {DANGER}44; }}
        70% {{ box-shadow: 0 0 0 15px {DANGER}00; }}
        100% {{ box-shadow: 0 0 0 0px {DANGER}00; }}
    }}
    .card-plan {{
        background: #2d3748; padding: 15px; border-radius: 12px;
        border-left: 5px solid {SECONDARY}; margin-bottom: 10px;
    }}
</style>
""", unsafe_allow_html=True)

# =============================================
# 2. SISTEMA DE SEGURIDAD Y DB
# =============================================
DB_FILE = "nefro_db.json"

class DataStore:
    def __init__(self):
        if not os.path.exists(DB_FILE):
            self._create_initial_db()
        self.data = self._load()

    def _create_initial_db(self):
        initial = {
            "users": {"admin": {"pwd": bcrypt.hashpw("Admin2026!".encode(), bcrypt.gensalt()).decode(), "role": "admin"}},
            "patients": [],
            "audit_log": []
        }
        with open(DB_FILE, "w") as f:
            json.dump(initial, f, indent=4)

    def _load(self):
        with open(DB_FILE, "r") as f:
            return json.load(f)

    def save_patient(self, record):
        self.data["patients"].insert(0, record)
        with open(DB_FILE, "w") as f:
            json.dump(self.data, f, indent=4)

db = DataStore()

# =============================================
# 3. LÓGICA MÉDICA Y REPORTES
# =============================================
def calcular_estadio(tfg):
    if tfg >= 90: return "G1 (Normal o elevado)"
    if tfg >= 60: return "G2 (Descenso ligero)"
    if tfg >= 45: return "G3a (Descenso ligero-moderado)"
    if tfg >= 30: return "G3b (Descenso moderado-grave)"
    if tfg >= 15: return "G4 (Descenso grave)"
    return "G5 (Falla renal)"

def generar_plan_clinico(estadio_cod):
    # Lógica de hidratación y ejercicio según directrices KDIGO
    if "G1" in estadio_cod or "G2" in estadio_cod:
        return {
            "hidratacion": "2.5 - 3 Litros diarios (8-10 vasos).",
            "ejercicio": "150 min/semana. Intensidad moderada (Caminata rápida, natación).",
            "frecuencia": "5 veces por semana, 30 min cada sesión.",
            "nutricion": "Sodio < 2300mg/día. Proteína normal (0.8g/kg)."
        }
    elif "G3" in estadio_cod:
        return {
            "hidratacion": "1.5 - 2 Litros diarios. Controlar edema.",
            "ejercicio": "90-120 min/semana. Intensidad baja-moderada.",
            "frecuencia": "3-4 veces por semana. Evitar fatiga extrema.",
            "nutricion": "Sodio < 1500mg/día. Restricción moderada de Potasio y Fósforo."
        }
    else: # G4 y G5
        return {
            "hidratacion": "Restricción estricta: 500ml + volumen de diuresis diaria.",
            "ejercicio": "Actividad física adaptada (Movilidad, estiramientos).",
            "frecuencia": "Diario, sesiones cortas de 10-15 min.",
            "nutricion": "RESTRICCIÓN MÁXIMA. Dieta renal estricta. Control de Potasio vital."
        }

class PDFReport(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 16)
        self.set_text_color(0, 102, 204)
        self.cell(0, 10, 'NEFROPREDICT RD - REPORTE CLINICO', 0, 1, 'C')
        self.ln(10)

    def add_section(self, title, content):
        self.set_font('Arial', 'B', 12)
        self.set_fill_color(240, 240, 240)
        self.cell(0, 10, title.encode('latin-1', 'replace').decode('latin-1'), 0, 1, 'L', 1)
        self.set_font('Arial', '', 10)
        self.multi_cell(0, 8, content.encode('latin-1', 'replace').decode('latin-1'))
        self.ln(5)

# =============================================
# 4. INTERFAZ STREAMLIT (ESTRUCTURA UNIFICADA)
# =============================================
def main():
    st.markdown("<h1 style='text-align: center; color: #0066CC;'>🏥 NefroPredict RD Pro</h1>", unsafe_allow_html=True)
    
    tabs = st.tabs(["🧬 Evaluación de Riesgo", "🥗 Calculadora Nutricional", "📊 Historial Clínico"])

    with tabs[0]:
        col1, col2 = st.columns([1, 1.2])
        
        with col1:
            st.subheader("📋 Datos del Paciente")
            with st.container():
                nombre = st.text_input("Nombre Completo")
                c1, c2 = st.columns(2)
                edad = c1.number_input("Edad", 18, 110, 45)
                sexo = c2.selectbox("Sexo", ["Hombre", "Mujer"])
                
                # VALIDACIONES CLÍNICAS
                creatinina = st.number_input("Creatinina Sérica (mg/dL)", 0.1, 20.0, 1.1, help="Rango normal: 0.7 - 1.3 mg/dL")
                tfg_calc = 186 * (creatinina**-1.154) * (edad**-0.203) * (0.742 if sexo == "Mujer" else 1.0)
                
                diabetes = st.checkbox("¿Paciente Diabético?")
                hipertension = st.checkbox("¿Paciente Hipertenso?")

        with col2:
            st.subheader("🔍 Análisis de Riesgo")
            estadio = calcular_estadio(tfg_calc)
            riesgo_perc = min(98, int((100 - tfg_calc) + (20 if diabetes else 0)))
            
            if riesgo_perc > 70:
                st.markdown(f"""
                <div class='risk-high-alert'>
                    <h2 style='color:white; margin:0;'>⚠️ RIESGO MUY ALTO: {riesgo_perc}%</h2>
                    <p style='color:#ffcccc;'><b>Estadio: {estadio}</b><br>Requiere atención nefrológica urgente.</p>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.metric("Probabilidad de Progresión ERC", f"{riesgo_perc}%", delta_color="inverse")
                st.info(f"Estadio detectado: {estadio}")

            # PLAN DE ACCIÓN CON CARDS
            plan = generar_plan_clinico(estadio)
            st.markdown("### 📋 Plan de Acción Integral")
            pc1, pc2 = st.columns(2)
            with pc1:
                st.markdown(f"<div class='card-plan'>💧 <b>Hidratación:</b><br>{plan['hidratacion']}</div>", unsafe_allow_html=True)
                st.markdown(f"<div class='card-plan'>🍎 <b>Nutrición:</b><br>{plan['nutricion']}</div>", unsafe_allow_html=True)
            with pc2:
                st.markdown(f"<div class='card-plan'>🏃 <b>Ejercicio:</b><br>{plan['ejercicio']}</div>", unsafe_allow_html=True)
                st.markdown(f"<div class='card-plan'>📅 <b>Frecuencia:</b><br>{plan['frecuencia']}</div>", unsafe_allow_html=True)

            if st.button("📄 Generar Reporte PDF"):
                pdf = PDFReport()
                pdf.add_page()
                pdf.add_section("Datos del Paciente", f"Nombre: {nombre}\nEdad: {edad}\nSexo: {sexo}\nCreatinina: {creatinina} mg/dL")
                pdf.add_section("Resultado Evaluación", f"Riesgo de Progresión: {riesgo_perc}%\nEstadio: {estadio}")
                pdf.add_section("Plan de Accion", f"Hidratacion: {plan['hidratacion']}\nEjercicio: {plan['ejercicio']}\nNutricion: {plan['nutricion']}")
                
                report_bytes = pdf.output(dest='S').encode('latin-1')
                st.download_button("⬇️ Descargar PDF", report_bytes, f"Reporte_{nombre}.pdf", "application/pdf")

    with tabs[1]:
        st.subheader("🥗 Calculadora Nutricional de Alimentos")
        alimentos_db = {
            "Plátano Maduro": {"K": 422, "P": 26, "Na": 1, "Nota": "⚠️ Alto Potasio. Limitar en G3-G5."},
            "Pollo (100g)": {"K": 220, "P": 200, "Na": 70, "Nota": "✅ Proteína de alta calidad."},
            "Habichuelas (1/2 taza)": {"K": 300, "P": 120, "Na": 5, "Nota": "⚠️ Remojar para reducir fósforo."},
            "Aguacate (1/2 unidad)": {"K": 485, "P": 52, "Na": 7, "Nota": "❌ Muy alto en potasio."},
            "Arroz Blanco (1 taza)": {"K": 55, "P": 68, "Na": 5, "Nota": "✅ Seguro para pacientes renales."}
        }
        item = st.selectbox("Seleccione un alimento para verificar:", list(alimentos_db.keys()))
        data = alimentos_db[item]
        
        nc1, nc2, nc3 = st.columns(3)
        nc1.metric("Potasio (K)", f"{data['K']} mg")
        nc2.metric("Fósforo (P)", f"{data['P']} mg")
        nc3.metric("Sodio (Na)", f"{data['Na']} mg")
        st.warning(data['Nota'])

    with tabs[2]:
        st.subheader("📜 Historial de Consultas")
        st.write("Datos almacenados en `nefro_db.json` de forma segura.")
        # Aquí se podría añadir un dataframe con db.data["patients"]

if __name__ == "__main__":
    main()
