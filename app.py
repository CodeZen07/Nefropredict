import streamlit as st
import pandas as pd
import numpy as np
import time
import joblib # Necesario para cargar modelos guardados

# --- 1. Configuración de la página ---
# El layout wide aprovecha mejor el espacio horizontal
st.set_page_config(page_title="NefroPredict RD", page_icon="🫘", layout="wide")

# --- 2. Título y Branding (Colores de RD: Azul #002868, Rojo #CE1126) ---
st.markdown("<h1 style='text-align: center; color:#002868;'>🫘 NefroPredict RD 2025</h1>", unsafe_allow_html=True)
st.markdown("<h3 style='text-align: center;'>Detección temprana de enfermedad renal crónica</h3>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color:#CE1126; font-size:1.1em;'>República Dominicana 🇩🇴</p>", unsafe_allow_html=True)

# --- FUNCIÓN DE CARGA DE MODELO CON CACHÉ ---
# NOTA: Esta función cachea la carga para que sea rápida.
@st.cache_resource
def load_model(path):
    """Carga el modelo de Machine Learning y lo cachea para un rápido acceso."""
    try:
        model = joblib.load(path)
        st.sidebar.success("Modelo ML cargado correctamente.")
        return model
    except FileNotFoundError:
        st.sidebar.error("⚠️ Error: Archivo de modelo (modelo_erc.joblib) no encontrado. Usando modo simulación.")
        return None
    except Exception as e:
        st.sidebar.error(f"Error al cargar el modelo: {e}. Usando modo simulación.")
        return None

# *************************************************************************
# --- INICIO: CARGA DEL MODELO REAL ---
# Intentamos cargar el modelo real usando la función load_model.
nefro_model = load_model('modelo_erc.joblib')
model_loaded = nefro_model is not None
# *************************************************************************


# --- 3. Sistema de Login Simple ---
if 'logged' not in st.session_state:
    st.session_state.logged = False

def check_login():
    """Función que maneja el flujo de login simple."""
    if not st.session_state.logged:
        st.markdown("### 🔐 Acceso restringido")
        pwd = st.text_input("Contraseña", type="password", key="password_input")
        if st.button("Ingresar"):
            if pwd == "nefro2025":
                st.session_state.logged = True
                st.success("¡Acceso concedido!")
                time.sleep(0.1)
                st.rerun()
            else:
                st.error("Contraseña incorrecta")
        st.stop()
    return True

if not check_login():
    st.stop()

st.success("✅ Sesión activa - Bienvenido/a al sistema NefroPredict RD")
st.markdown("---")

# --- 4. Carga de Datos y Procesamiento ---
st.subheader("1. Carga de datos de pacientes")
uploaded = st.file_uploader("📁 Sube tu archivo Excel de pacientes", type=["xlsx", "xls"])

if uploaded:
    try:
        df = pd.read_excel(uploaded)
        st.success(f"¡Cargados {len(df)} pacientes correctamente!")

        # Validación básica de columnas requeridas
        required_cols = ['edad', 'imc', 'presion_sistolica', 'glucosa_ayunas', 'creatinina']
        missing_cols = [col for col in required_cols if col not in df.columns]

        if missing_cols:
             st.error(f"⚠️ Error: Faltan las siguientes columnas requeridas en tu Excel: {', '.join(missing_cols)}. Por favor, revisa el formato.")
             st.stop()
        
        # Seleccionar las características necesarias para el modelo
        X = df[required_cols]

        # --- LÓGICA DE PREDICCIÓN REAL O SIMULACIÓN ---
        if model_loaded:
            # INTEGRACIÓN DEL MODELO REAL
            st.info(f"Usando el modelo cargado para predicción real: {type(nefro_model).__name__}")
            
            # Predict_proba devuelve la probabilidad de pertenecer a cada clase.
            predictions_proba = nefro_model.predict_proba(X)[:, 1]
            # Convertir probabilidad (0 a 1) a porcentaje (0 a 100)
            df['Riesgo_ERC_5años_%'] = (predictions_proba * 100).round(1)

        else:
            # SIMULACIÓN DE RIESGO (Fallback si el modelo no carga)
            st.warning("Usando simulación de riesgo: El modelo real no pudo cargarse debido a un problema con el archivo joblib.")
            np.random.seed(42)
            df['Riesgo_ERC_5años_%'] = np.random.uniform(10, 95, len(df)).round(1)
        # -----------------------------------------------

        # --- 5. Presentación de Resultados ---
        st.subheader("2. Resultados predictivos y recomendaciones")

        # Métricas de resumen general
        total_alto_riesgo = len(df[df['Riesgo_ERC_5años_%'] > 70])
        total_pacientes = len(df)
        
        col_res1, col_res2, col_res3 = st.columns(3)

        col_res1.metric("Total Pacientes Evaluados", total_pacientes)
        col_res2.metric("Pacientes con Riesgo MUY ALTO", total_alto_riesgo, f"{((total_alto_riesgo/total_pacientes)*100):.1f}% de la muestra")
        col_res3.info(f"El riesgo máximo encontrado fue: {df['Riesgo_ERC_5años_%'].max():.1f}%")

        st.markdown("---")

        for i, row in df.iterrows():
            riesgo = row['Riesgo_ERC_5años_%']
            # Obtener el ID del paciente, si existe, si no usar un nombre genérico
            paciente_id = row.get('id_paciente', f'Paciente {i+1}')
            
            # Determinación del nivel de riesgo y estilo
            if riesgo > 70:
                color_bg, color_txt, nivel = "#CE1126", "white", "MUY ALTO - Referir URGENTE a nefrólogo" # Rojo RD
                emoji = "🚨"
            elif riesgo > 40:
                color_bg, color_txt, nivel = "#FFC400", "black", "ALTO - Control estricto cada 3 meses" # Ámbar
                emoji = "⚠️"
            else:
                color_bg, color_txt, nivel = "#4CAF50", "white", "MODERADO - Control anual" # Verde
                emoji = "✅"

            # Personalización del Expander usando HTML para el color de fondo del encabezado
            expander_html = f"""
            <style>
                div[data-testid="stExpander"] > div[role="button"] {{
                    background-color: {color_bg};
                    color: {color_txt};
                    border-radius: 8px;
                    padding: 10px;
                    margin-top: 5px;
                    font-size: 1.1em;
                }}
            </style>
            """
            st.markdown(expander_html, unsafe_allow_html=True)

            with st.expander(f"{emoji} **{paciente_id}** | Riesgo: **{riesgo}%**"):
                # Mostrar el detalle de los biomarcadores
                st.markdown(f"#### Nivel de Riesgo: {nivel.split(' - ')[0]}")
                col1, col2, col3, col4 = st.columns(4)
                # Usamos .get() por si acaso el Excel no tiene las columnas, aunque ya validamos arriba
                col1.metric("Creatinina (mg/dL)", f"{row.get('creatinina', 'N/D')}", help="Indicador clave de función renal.")
                col2.metric("Glucosa Ayunas (mg/dL)", f"{row.get('glucosa_ayunas', 'N/D')}", help="Factor de riesgo de diabetes.")
                col3.metric("Presión Sistólica (mmHg)", f"{row.get('presion_sistolica', 'N/D')}", help="Factor principal de la ERC.")
                col4.metric("IMC", f"{row.get('imc', 'N/D'):.1f}", help="Índice de Masa Corporal")

                st.markdown(f"<div style='padding: 15px; border-left: 5px solid {color_bg}; background-color: #f0f2f6; border-radius: 5px; margin-top: 10px;'>**RECOMENDACIÓN MÉDICA:** {nivel}</div>", unsafe_allow_html=True)
        
        st.markdown("---")

        # --- 6. Descarga de resultados ---
        st.subheader("3. Exportar Datos")
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Descargar resultados completos (CSV)",
            data=csv,
            file_name="NefroPredict_resultados.csv",
            mime="text/csv",
            help="Incluye todas las variables originales más la columna de predicción de riesgo."
        )

    except Exception as e:
        # Manejo de error de carga (ej. si el archivo no es un Excel válido o si falla la predicción por datos)
        st.error(f"Ocurrió un error al procesar el archivo. Asegúrate de que el formato de Excel sea correcto y los datos sean válidos: {e}")

else:
    # Instrucciones si no hay archivo subido
    st.info("Sube tu archivo Excel para comenzar la evaluación de riesgo de ERC.")
    st.markdown("**Columnas esperadas:** `edad`, `imc`, `presion_sistolica`, `glucosa_ayunas`, `creatinina`, `id_paciente` (opcional)")
    if not model_loaded:
        st.warning("🚨 ADVERTENCIA: La aplicación está en modo **SIMULACIÓN** (el modelo real no se pudo cargar).")


# --- 7. Footer ---
st.markdown("---")
st.markdown("<p style='text-align: center; color:#002868; font-weight:bold;'>© 2025 NefroPredict RD - Soluciones de salud impulsadas por IA</p>", unsafe_allow_html=True)
           
