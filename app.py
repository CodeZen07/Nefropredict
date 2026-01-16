import pandas as pd
import numpy as np
import json
import os
import bcrypt
from datetime import datetime
import streamlit as st
import plotly.graph_objects as go

# 1. CONFIGURACIÓN DE PÁGINA Y ESTILO PROFESIONAL
st.set_page_config(page_title="NefroPredict RD", page_icon="🏥", layout="wide")

# Colores de identidad médica
COLOR_NAVY = "#1B263B"      # Azul Marino
COLOR_MEDICAL_GREEN = "#2D6A4F" # Verde Médico
COLOR_ACCENT = "#415A77"

st.markdown(f"""
    <style>
    .main {{ background-color: #F8F9FA; }}
    .stButton>button {{
        background-color: {COLOR_MEDICAL_GREEN};
        color: white;
        border-radius: 8px;
        border: none;
        padding: 10px 24px;
    }}
    .stTabs [data-baseweb="tab-list"] {{ background-color: {COLOR_NAVY}; border-radius: 10px; padding: 5px; }}
    .stTabs [data-baseweb="tab"] {{ color: white; font-weight: bold; }}
    .medical-card {{
        background-color: white;
        padding: 20px;
        border-radius: 15px;
        border-left: 5px solid {COLOR_MEDICAL_GREEN};
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        margin-bottom: 20px;
    }}
    .disclaimer {{
        font-size: 0.85em;
        color: #6c757d;
        border: 1px solid #dee2e6;
        padding: 10px;
        border-radius: 5px;
        background-color: #fff3cd;
    }}
    </style>
""", unsafe_allow_html=True)

# 2. SISTEMA DE RECOMENDACIONES CIENTÍFICAS (KDIGO)
def obtener_guia_clinica(tfg):
    """Basado en las Guías KDIGO 2012 y actualizaciones 2024"""
    if tfg >= 90:
        return {
            "estadio": "G1 - Normal o elevado",
            "recom": "Seguimiento anual. Control de presión arterial (Meta <130/80 mmHg) y monitoreo de albuminuria. Fuente: Guías KDIGO.",
            "color": "#2D6A4F"
        }
    elif tfg >= 60:
        return {
            "estadio": "G2 - Disminución leve",
            "recom": "Evaluar progresión. Control estricto de diabetes y factores de riesgo cardiovascular. Fuente: National Kidney Foundation (NKF).",
            "color": "#95D5B2"
        }
    elif tfg >= 30:
        return {
            "estadio": "G3a/G3b - Disminución moderada",
            "recom": "Referencia a Nefrología recomendada. Ajustar dosis de medicamentos y evitar nefrotóxicos (AINES). Fuente: KDIGO 2024.",
            "color": "#FFB703"
        }
    else:
        return {
            "estadio": "G4/G5 - Disminución severa / Fallo",
            "recom": "REFERENCIA URGENTE A NEFROLOGÍA. Planificar terapia de reemplazo renal (Diálisis/Trasplante). Fuente: KDIGO Clinical Practice Guidelines.",
            "color": "#E63946"
        }

# 3. COMPONENTE GRÁFICO
def crear_gauge(tfg):
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=tfg,
        title={'text': "TFG (mL/min/1.73m²)", 'font': {'size': 20, 'color': COLOR_NAVY}},
        gauge={
            'axis': {'range': [0, 120]},
            'bar': {'color': COLOR_MEDICAL_GREEN},
            'steps': [
                {'range': [0, 30], 'color': "#FFD6D6"},
                {'range': [30, 60], 'color': "#FFF3CD"},
                {'range': [60, 120], 'color': "#D4EDDA"}
            ],
            'threshold': {'line': {'color': "red", 'width': 4}, 'thickness': 0.75, 'value': 60}
        }
    ))
    fig.update_layout(height=300, margin=dict(l=20, r=20, t=50, b=20))
    return fig

# 4. LÓGICA DE LA APLICACIÓN
st.markdown(f"<h1 style='color:{COLOR_NAVY}; text-align:center;'>🏥 NefroPredict RD</h1>", unsafe_allow_html=True)

# (Se asume la lógica de login del código anterior...)
if "logged_in" not in st.session_state:
    st.session_state.logged_in = True # Activado para visualización

tab1, tab2 = st.tabs(["🧪 Evaluación Clínica", "📊 Historial de Pacientes"])

with tab1:
    col_input, col_graph = st.columns([1, 1.2])
    
    with col_input:
        st.markdown(f"<h3 style='color:{COLOR_ACCENT};'>Datos del Paciente</h3>", unsafe_allow_html=True)
        with st.form("nefro_form"):
            nombre = st.text_input("Nombre Completo")
            edad = st.number_input("Edad", 18, 100, 55)
            sexo = st.selectbox("Sexo Biológico", ["Hombre", "Mujer"])
            creat = st.number_input("Creatinina Sérica (mg/dL)", 0.1, 15.0, 1.2)
            raza = st.selectbox("Etnicidad", ["No-Afroamericano", "Afroamericano"])
            submit = st.form_submit_button("Realizar Diagnóstico")

    if submit and nombre:
        # Cálculo TFG (Fórmula simplificada CKD-EPI)
        k = 0.7 if sexo == "Mujer" else 0.9
        a = -0.329 if sexo == "Mujer" else -0.411
        tfg_res = 141 * (min(creat/k, 1)**a) * (max(creat/k, 1)**-1.209) * (0.993**edad)
        if sexo == "Mujer": tfg_res *= 1.018
        if "Afro" in raza: tfg_res *= 1.159
        tfg_res = round(tfg_res, 1)

        guia = obtener_guia_clinica(tfg_res)

        with col_graph:
            st.plotly_chart(crear_gauge(tfg_res), use_container_width=True)
            
            st.markdown(f"""
                <div class="medical-card">
                    <h4 style="color:{COLOR_NAVY};">Resultado del Análisis</h4>
                    <p><b>Paciente:</b> {nombre}</p>
                    <p><b>Estadio:</b> <span style="color:{guia['color']}; font-weight:bold;">{guia['estadio']}</span></p>
                    <hr>
                    <p style="font-size:0.95em;"><b>Recomendación Basada en Evidencia:</b><br>{guia['recom']}</p>
                </div>
            """, unsafe_allow_html=True)
            
            st.markdown("""
                <div class="disclaimer">
                    <b>⚠️ AVISO LEGAL MÉDICO:</b> Esta herramienta es un recurso de apoyo basado en modelos matemáticos y guías 
                    clínicas internacionales. <b>No sustituye bajo ninguna circunstancia el juicio clínico, 
                    la exploración física o la opinión de un profesional de la salud colegiado.</b>
                </div>
            """, unsafe_allow_html=True)

with tab2:
    st.info("Aquí aparecerá la tabla de pacientes guardados en la base de datos JSON.")
