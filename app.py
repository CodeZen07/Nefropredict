import pandas as pd
import numpy as np
import time
import joblib
import json
import os
import io
import streamlit as st
import altair as alt
import streamlit.components.v1 as components

# =============================================
# CONFIGURACIÓN DE PÁGINA
# =============================================
st.set_page_config(page_title="NefroPredict RD", page_icon="Kidney", layout="wide")

# =============================================
# ESTILOS Y SCRIPTS DE IMPRESIÓN
# =============================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');
    html, body, [class*="css"] {font-family: 'Inter', sans-serif;}
    h1, h2, h3 {color: #002868 !important;}
    .stButton > button {
        background: #002868; 
        color: white; 
        border-radius: 12px; 
        padding: 0.7rem 1.5rem;
        transition: background-color 0.3s ease;
    }
    .stButton > button:hover {
        background: #004499;
    }
    .risk-gauge-bar {
        height: 40px; border-radius: 20px;
        background: linear-gradient(to right, #10B981 0%, #FACC15 40%, #F97316 70%, #EF4444 100%);
        position: relative; margin: 20px 0;
    }
    .risk-gauge-marker {
        position: absolute; top: -20px; left: var(--pos); transform: translateX(-50%);
        width: 12px; height: 80px; background: white; border: 4px solid black; border-radius: 6px;
    }
    
    /* ESTILOS PARA LA IMPRESIÓN PDF */
    @media print {
        /* Ocultar todos los elementos de Streamlit que no son el informe */
        header, footer, .stButton, .stTabs, .css-18e3th9, .stSuccess, .stWarning, .suggestions-box {
            display: none !important;
        }
        /* Mostrar solo el contenedor de impresión */
        #printable_report {
            display: block !important;
            width: 100%;
            margin: 0;
            padding: 0;
        }
        .stplot { /* Asegura que los gráficos de Altair se impriman */
            max-width: 100% !important;
        }
    }
    
    #printable_report {
        display: none; /* Por defecto invisible en pantalla */
    }
</style>

<script>
    function printReport(reportId, patientName, doctorName) {
        // Establecer el título del documento para el nombre del archivo PDF
        document.title = "Informe_ERC_" + patientName.replace(/\s/g, '_') + "_" + doctorName.replace(/\s/g, '_');
        
        // Mostrar el contenido del informe justo antes de imprimir
        const report = document.getElementById(reportId);
        report.style.display = 'block';

        window.print();

        // Ocultar el contenido del informe de nuevo después de imprimir/cancelar
        setTimeout(() => {
            report.style.display = 'none';
            // Restaurar el título original de la página
            document.title = "NefroPredict RD 2025";
        }, 100);
    }
</script>

""", unsafe_allow_html=True)

st.markdown("<h1 style='text-align: center;'>NefroPredict RD 2025</h1>", unsafe_allow_html=True)
st.markdown("<h3 style='text-align: center; color:#555;'>Detección temprana de ERC • República Dominicana</h3>", unsafe_allow_html=True)

# =============================================
# BASE DE DATOS SIMULADA (JSON) - CLASE DataStore ACTUALIZADA
# =============================================
DB_FILE = "nefro_db.json"

class DataStore:
    def __init__(self, path):
        self.path = path
        if not os.path.exists(path):
            self._init_db()

    def _init_db(self):
        data = {
            "users": {
                "admin": {"pwd": "admin", "role": "admin", "id": "admin_001", "active": True},
                "dr.perez": {"pwd": "pass1", "role": "doctor", "id": "dr_001", "active": True},
                "dr.gomez": {"pwd": "pass2", "role": "doctor", "id": "dr_002", "active": True}
            },
            "file_history": [],
            "patient_records": []
        }
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

    def _load(self):
        if not os.path.exists(self.path):
            self._init_db()
        with open(self.path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _save(self, data):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

    def get_user(self, username):
        return self._load().get("users", {}).get(username)

    def get_user_display_name(self, username):
        # Función para obtener un nombre legible si lo tuviéramos
        # Por ahora, usamos el username capitalizado
        return username.replace('.', ' ').title()
        
    def get_all_users(self):
        return self._load().get("users", {})
        
    def get_all_doctors(self):
        data = self._load()
        # Devuelve solo usuarios con rol 'doctor'
        return {
            username: user_data
            for username, user_data in data.get("users", {}).items()
            if user_data.get("role") == "doctor"
        }

    def add_user(self, username, password, role="doctor"):
        data = self._load()
        if username in data["users"]:
            return False, "Usuario ya existe."
        
        # Generar un ID simple para el nuevo doctor
        count = sum(1 for u in data["users"].values() if u["role"] == role)
        new_id = f"{role[:2]}_{count+1:03d}"
        
        data["users"][username] = {
            "pwd": password,
            "role": role,
            "id": new_id,
            "active": True
        }
        self._save(data)
        return True, "Usuario creado exitosamente."

    def delete_user(self, username):
        data = self._load()
        # No permitir eliminar al propio usuario o al admin
        if username == st.session_state.username or data["users"].get(username, {}).get("role") == "admin":
            return False
        
        if username in data["users"]:
            del data["users"][username]
            self._save(data)
            return True
        return False

    def update_user(self, username, updates): 
        data = self._load()
        if username in data["users"]:
            data["users"][username].update(updates)
            self._save(data)
            return True
        return False

    def add_patient_record(self, record):
        data = self._load()
        data["patient_records"].insert(0, record)
        self._save(data)

    def add_patient_records_bulk(self, records_list):
        data = self._load()
        data["patient_records"].extend(records_list)
        # Ordenar por timestamp, ya que los nuevos registros se agregan al final
        data["patient_records"].sort(key=lambda x: x["timestamp"], reverse=True)
        self._save(data)

    def get_patient_records(self, name):
        data = self._load()
        return sorted(
            [r for r in data["patient_records"] if r["nombre_paciente"].lower() == name.lower()],
            key=lambda x: x["timestamp"], reverse=True
        )

    def get_all_patient_names(self):
        data = self._load()
        names = {r["nombre_paciente"] for r in data["patient_records"] if "nombre_paciente" in r}
        return sorted(names)

db = DataStore(DB_FILE)

# =============================================
# CARGA DEL MODELO
# =============================================
@st.cache_resource
def load_model():
    try:
        # NOTA: Asegúrate de tener el archivo "modelo_erc.joblib"
        return joblib.load("modelo_erc.joblib")
    except FileNotFoundError:
        st.warning("Modelo no encontrado (modelo_erc.joblib) → Modo simulación activo.")
        return None

model = load_model()

# =============================================
# LOGIN
# =============================================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    
# Aseguramos un nombre de doctor para el PDF
if "doctor_name_display" not in st.session_state:
    st.session_state.doctor_name_display = ""

if not st.session_state.logged_in:
    st.markdown("### Iniciar Sesión")
    with st.form("login"):
        user = st.text_input("Usuario").lower()
        pwd = st.text_input("Contraseña", type="password")
        if st.form_submit_button("Entrar"):
            u = db.get_user(user)
            if u and u["pwd"] == pwd and u.get("active", True):
                st.session_state.logged_in = True
                st.session_state.username = user
                st.session_state.role = u["role"]
                st.session_state.user_id = u["id"]
                st.session_state.doctor_name_display = db.get_user_display_name(user)
                st.rerun()
            else:
                st.error("Credenciales incorrectas o usuario inactivo")
    st.stop()

# Logout
col1, col2 = st.columns([4,1])
with col1:
    st.success(f"Usuario: **{st.session_state.username.upper()}** • Rol: **{st.session_state.role.upper()}**")
with col2:
    if st.button("Salir"):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.rerun()

st.markdown("---")

# =============================================
# FUNCIONES CLAVE
# =============================================
def get_risk_level(risk):
    if risk > 70: return "MUY ALTO", "#CE1126", "Referir URGENTE al Nefrólogo. Requiere intervención inmediata."
    elif risk > 40: return "ALTO", "#F97316", "Control estricto. Seguimiento cada 3-6 meses."
    elif risk > 20: return "MODERADO", "#FACC15", "Control habitual. Fomentar cambios en el estilo de vida."
    else: return "BAJO", "#10B981", "Riesgo mínimo. Control anual."

def predict_risk(row):
    try:
        features = np.array([[row["edad"], row["imc"], row["presion_sistolica"], row["glucosa_ayunas"], row["creatinina"]]])
        if model:
            prob = model.predict_proba(features)[0][1]
            return round(prob * 100, 1)
        else:
            # Simulación simple si el modelo no carga
            base = 5 + (row["creatinina"] - 1.0) * 20 + max(0, row["glucosa_ayunas"] - 110) * 0.2 + (row["edad"] - 50) * 0.5
            return max(1.0, min(99.9, base + np.random.uniform(-5, 10)))
    except:
        return 50.0

def get_scientific_suggestions(row):
    suggestions = []
    
    # Fuentes: AHA, ADA, KDIGO Guidelines (simuladas para el ejemplo)
    
    # 1. Creatinina (Indicador directo de función renal)
    if row["creatinina"] >= 1.4:
        suggestions.append("**Creatinina Alta:** Un nivel de creatinina sérica > 1.4 mg/dL sugiere una reducción significativa en la tasa de filtración glomerular. Es crucial una medición de cistatina C o una fórmula de eGFR más precisa.")
    elif row["creatinina"] >= 1.0:
         suggestions.append("**Monitoreo de Creatinina:** Valores consistentemente por encima de 1.0 mg/dL requieren vigilancia, especialmente en pacientes con hipertensión o diabetes. [Image of the kidney cross-section] **(Mencionar solo para el usuario, no para el PDF)**.")

    # 2. Glucosa (Diabetes es la principal causa de ERC)
    if row["glucosa_ayunas"] >= 126:
        suggestions.append("**Hiperglicemia:** Un valor de glucosa en ayunas ≥ 126 mg/dL es diagnóstico de diabetes (o pre-diabetes si es menor, pero alto). La diabetes acelera el daño renal. Monitorear HbA1c y comenzar tratamiento intensivo.")
    
    # 3. Presión Sistólica (Control de la TA)
    if row["presion_sistolica"] >= 140:
        suggestions.append("**Hipertensión:** La presión arterial sistólica ≥ 140 mmHg es un factor de riesgo MAYOR para ERC. Se recomienda una meta de TA < 130/80 mmHg en pacientes con enfermedad renal, preferiblemente con inhibidores de la ECA o ARA II.")
        
    # 4. IMC (Obesidad)
    if row["imc"] >= 35:
        suggestions.append("**Obesidad Severa (IMC > 35):** La obesidad causa hiperfiltración glomerular. Se recomienda una pérdida de peso > 10% para reducir la proteinuria y el riesgo cardiovascular.")

    if not suggestions:
        suggestions.append("Los parámetros bioquímicos son favorables. Mantener los hábitos saludables y el control de riesgo cardiovascular.")
        
    return suggestions

def create_altair_chart(df_row):
    # Definición de rangos óptimos (simulados) y máximo para normalización
    ranges = {
        "edad": (18, 50, 80), # Óptimo, Riesgo Moderado, Riesgo Alto
        "imc": (18.5, 25, 35),
        "presion_sistolica": (90, 120, 160),
        "glucosa_ayunas": (70, 100, 126),
        "creatinina": (0.6, 1.0, 1.5)
    }
    
    data = []
    for param, (opt, mod, high) in ranges.items():
        data.append({
            'Parámetro': param.replace('_', ' ').title(),
            'Valor del Paciente': df_row[param],
            'Mínimo Óptimo': opt,
            'Máximo Óptimo': mod,
            'Riesgo Alto': high,
        })

    df_charts = pd.DataFrame(data)
    
    # Normalizar valores para el gráfico de radar (opcional, pero útil)
    df_melt = df_charts.melt(id_vars=['Parámetro'], 
                             value_vars=['Valor del Paciente', 'Máximo Óptimo'],
                             var_name='Tipo', 
                             value_name='Valor')
    
    base = alt.Chart(df_melt).encode(
        theta=alt.Theta("Parámetro", stack=True)
    ).properties(
        title="Parámetros Bioquímicos y Zonas de Riesgo"
    ).interactive()

    # Creación del gráfico de barras para cada parámetro
    charts = []
    for _, row in df_charts.iterrows():
        param_name = row['Parámetro']
        val = row['Valor del Paciente']
        opt = row['Mínimo Óptimo']
        mod = row['Máximo Óptimo']
        high = row['Riesgo Alto']
        
        # DataFrame para el gráfico de barras
        df_bar = pd.DataFrame({
            'Zona': ['Óptimo', 'Moderado', 'Alto'],
            'Rango Max': [mod - opt, high - mod, high * 2 - high], # Rango de color
            'Inicio': [opt, mod, high] # Punto de inicio
        })
        
        # Calcular el valor máximo para el eje
        max_val = max(val * 1.2, high * 1.5)

        chart = alt.Chart(df_bar).mark_bar().encode(
            x=alt.X('Inicio', title=param_name, axis=None, scale=alt.Scale(domain=[0, max_val])),
            x2='Rango Max',
            color=alt.Color('Zona', scale=alt.Scale(domain=['Óptimo', 'Moderado', 'Alto'], range=['#10B981', '#FACC15', '#EF4444']), legend=None),
            tooltip=['Zona', alt.Tooltip('Inicio', title='Mínimo'), alt.Tooltip('Rango Max', title='Máximo')]
        ).properties(
            title=param_name
        )

        # Marcador del paciente
        marker = alt.Chart(pd.DataFrame({'Valor': [val]})).mark_point(
            filled=True, 
            size=100, 
            color='black',
            shape='triangle-down'
        ).encode(
            x=alt.X('Valor', scale=alt.Scale(domain=[0, max_val])),
            tooltip=[alt.Tooltip('Valor', title='Valor del Paciente')]
        )
        
        # Combinar gráfico de barras y marcador
        combined = (chart + marker).encode(
            y=alt.value(20) # Posición vertical
        ).properties(
            height=80,
            width='container'
        )
        
        charts.append(combined)

    # Devolver una columna de gráficos apilados
    return charts

def get_general_analysis(records):
    if not records:
        return "N/A - No hay historial.", "gray"

    df = pd.DataFrame(records)
    
    # 1. Chequeo de riesgo CRÍTICO (MUY ALTO en cualquier momento)
    if 'MUY ALTO' in df['nivel'].values:
        return "CRÍTICO - Riesgo Extremo en Historial", "#CE1126"

    # 2. Chequeo de intervención (Alto y recurrente)
    high_risk_count = (df['nivel'] == 'ALTO').sum()
    if high_risk_count >= 2:
        return "INTERVENCIÓN - Riesgo Alto Recurrente", "#F97316"

    # 3. Chequeo de riesgo creciente
    if len(df) >= 2:
        latest_risk = df.iloc[0]['risk']
        oldest_risk = df.iloc[-1]['risk']
        
        if latest_risk > oldest_risk and latest_risk > 30:
            return "INTERVENCIÓN - Riesgo en Aumento", "#FACC15"
    
    # 4. Óptimo
    if all(level in ['BAJO', 'MODERADO'] for level in df['nivel'].values):
        return "ÓPTIMO - Riesgo Bien Controlado", "#10B981"
        
    return "MODERADO - Requiere Vigilancia", "#FACC15"


# =============================================
# DEFINICIÓN DE PESTAÑAS (Roles)
# =============================================
tabs_list = ["Predicción Individual", "Carga Masiva", "Historial"]
if st.session_state.role == "admin":
    tabs_list.append("Administración")

tabs = st.tabs(tabs_list)
tab_prediccion = tabs[0]
tab_carga = tabs[1]
tab_historial = tabs[2]
tab_admin = tabs[3] if st.session_state.role == "admin" else None


with tab_prediccion:
    st.subheader("Predicción Individual")
    
    # Inicializar valores por defecto si no existen en session_state
    if 'pred_nombre' not in st.session_state:
        st.session_state.pred_nombre = "María Almonte"
        st.session_state.pred_edad = 60
        st.session_state.pred_imc = 30.0
        st.session_state.pred_glucosa = 180
        st.session_state.pred_presion = 160
        st.session_state.pred_creat = 1.9

    with st.form("individual"):
        nombre = st.text_input("Nombre del paciente", st.session_state.pred_nombre, key="input_nombre")
        c1, c2 = st.columns(2)
        with c1:
            edad = st.number_input("Edad", 18, 120, st.session_state.pred_edad, key="input_edad")
            imc = st.number_input("IMC (kg/m²)", 10.0, 60.0, st.session_state.pred_imc, 0.1, key="input_imc")
            glucosa = st.number_input("Glucosa ayunas (mg/dL)", 50, 500, st.session_state.pred_glucosa, key="input_glucosa")
        with c2:
            presion = st.number_input("Presión sistólica (mmHg)", 80, 250, st.session_state.pred_presion, key="input_presion")
            creat = st.number_input("Creatinina (mg/dL)", 0.1, 10.0, st.session_state.pred_creat, 0.01, key="input_creat")

        if st.form_submit_button("Calcular Riesgo y Generar Informe"):
            if not nombre.strip():
                st.error("El nombre es obligatorio")
            else:
                # Almacenar valores en session_state para que persistan después del submit/rerun
                st.session_state.pred_nombre = nombre
                st.session_state.pred_edad = edad
                st.session_state.pred_imc = imc
                st.session_state.pred_glucosa = glucosa
                st.session_state.pred_presion = presion
                st.session_state.pred_creat = creat
                
                row = {"edad": edad, "imc": imc, "presion_sistolica": presion,
                       "glucosa_ayunas": glucosa, "creatinina": creat}
                risk = predict_risk(row)
                nivel, color, reco = get_risk_level(risk)

                # Guardar registro en DB
                record = {
                    "nombre_paciente": nombre,
                    "user_id": st.session_state.user_id,
                    "usuario": st.session_state.username,
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                    **row,
                    "risk": risk,
                    "nivel": nivel
                }
                db.add_patient_record(record)

                # Guardar el resultado en session state
                st.session_state.last_result = {
                    "risk": risk, "nivel": nivel, "color": color, "reco": reco, "row": row, "timestamp": record["timestamp"]
                }
                st.rerun()

    # =================================================================
    # Mostrar resultado y Generar Reporte
    # =================================================================
    if "last_result" in st.session_state:
        res = st.session_state.last_result
        r = res["risk"]
        n = res["nivel"]
        c = res["color"]
        reco = res["reco"]
        row = res["row"]
        ts = res["timestamp"]
        nombre = st.session_state.pred_nombre
        doctor_display_name = st.session_state.doctor_name_display

        # -------------------------------------------------------------
        # 1. MOSTRAR EN PANTALLA (Resultados Rápidos + Sugerencias)
        # -------------------------------------------------------------
        st.markdown(f"""
        <div style="text-align:center; padding:30px; background:#f9f9f9; border-radius:16px; border: 3px solid {c}">
            <h2 style="color:{c}">NIVEL DE RIESGO: {n}</h2>
            <h1 style="font-size:5rem; margin:10px; color:{c}">{r:.1f}%</h1>
            <div class="risk-gauge-bar"><div class="risk-gauge-marker" style="--pos: {r}%"></div></div>
            <p style="font-size:1.2rem; font-weight:bold;">{reco}</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Botón de Descarga
        st.markdown("---")
        st.button("Descargar/Imprimir Informe PDF", 
                  on_click=components.html, args=[
                      f'<script>printReport("printable_report", "{nombre}", "{doctor_display_name}")</script>'
                  ], key="pdf_button", type="primary")

        # Sugerencias (VISIBLES SOLO EN PANTALLA)
        with st.expander("📝 Análisis y Sugerencias Clínicas (Solo en Pantalla)", expanded=True):
            st.markdown('<div class="suggestions-box">', unsafe_allow_html=True)
            suggestions = get_scientific_suggestions(row)
            for suggestion in suggestions:
                st.info(suggestion)
            st.markdown('</div>', unsafe_allow_html=True)


        # -------------------------------------------------------------
        # 2. CONTENIDO IMPRIMIBLE (PDF Report)
        # -------------------------------------------------------------
        # Este div solo es visible cuando se activa la función printReport()
        st.markdown(f"""
        <div id="printable_report" style="padding: 20px;">
            <div style="border: 2px solid #002868; padding: 20px; border-radius: 10px;">
                <h1 style="text-align: center; color: #002868; font-size: 28px;">INFORME DE RIESGO DE ERC - NEFROPREDICT RD</h1>
                <hr style="border-top: 2px solid #ddd;"/>
                <table style="width: 100%; margin-top: 15px;">
                    <tr>
                        <td style="width: 50%;"><strong>PACIENTE:</strong> {nombre}</td>
                        <td style="width: 50%;"><strong>FECHA:</strong> {ts.split(' ')[0]}</td>
                    </tr>
                    <tr>
                        <td><strong>DOCTOR/A:</strong> {doctor_display_name} ({st.session_state.username.upper()})</td>
                        <td><strong>HORA:</strong> {ts.split(' ')[1]}</td>
                    </tr>
                </table>
                <hr style="border-top: 1px solid #ddd; margin-top: 10px;"/>
                
                <h2 style="color: {c}; text-align: center; font-size: 24px; margin-top: 20px;">RIESGO PREDICTIVO: {r:.1f}% ({n})</h2>
                <p style="text-align: center; font-size: 16px; margin-bottom: 20px;"><strong>Recomendación Principal:</strong> {reco}</p>

                <h3 style="color: #002868; font-size: 20px; margin-top: 30px;">Datos de Entrada</h3>
                <table style="width: 100%; border-collapse: collapse; margin-top: 10px;">
                    <thead><tr>
                        <th style="border: 1px solid #ddd; padding: 8px; text-align: left; background-color: #f2f2f2;">Parámetro</th>
                        <th style="border: 1px solid #ddd; padding: 8px; text-align: center; background-color: #f2f2f2;">Valor</th>
                        <th style="border: 1px solid #ddd; padding: 8px; text-align: left; background-color: #f2f2f2;">Unidad</th>
                    </tr></thead>
                    <tbody>
                        <tr><td style="border: 1px solid #ddd; padding: 8px;">Edad</td><td style="border: 1px solid #ddd; padding: 8px; text-align: center;">{row['edad']}</td><td style="border: 1px solid #ddd; padding: 8px;">años</td></tr>
                        <tr><td style="border: 1px solid #ddd; padding: 8px;">IMC</td><td style="border: 1px solid #ddd; padding: 8px; text-align: center;">{row['imc']:.1f}</td><td style="border: 1px solid #ddd; padding: 8px;">kg/m²</td></tr>
                        <tr><td style="border: 1px solid #ddd; padding: 8px;">Presión Sistólica</td><td style="border: 1px solid #ddd; padding: 8px; text-align: center;">{row['presion_sistolica']}</td><td style="border: 1px solid #ddd; padding: 8px;">mmHg</td></tr>
                        <tr><td style="border: 1px solid #ddd; padding: 8px;">Glucosa Ayunas</td><td style="border: 1px solid #ddd; padding: 8px; text-align: center;">{row['glucosa_ayunas']}</td><td style="border: 1px solid #ddd; padding: 8px;">mg/dL</td></tr>
                        <tr><td style="border: 1px solid #ddd; padding: 8px;">Creatinina</td><td style="border: 1px solid #ddd; padding: 8px; text-align: center;">{row['creatinina']:.2f}</td><td style="border: 1px solid #ddd; padding: 8px;">mg/dL</td></tr>
                    </tbody>
                </table>
                <p style="font-size: 12px; margin-top: 20px;">El riesgo se calcula basado en un modelo de Machine Learning entrenado con datos epidemiológicos dominicanos para la detección temprana de ERC (Enfermedad Renal Crónica).</p>
            </div>
            <div style="page-break-before: always; height: 1px;"></div>
            <h3 style="color: #002868; font-size: 20px; margin-top: 30px;">Gráficos de Comparación con Zonas de Riesgo</h3>
            <!-- Los gráficos de Altair se insertarán aquí por Streamlit y se imprimirán. -->
        </div>
        """, unsafe_allow_html=True)

        # Generar y mostrar los gráficos de Altair justo después del contenedor HTML (Streamlit los maneja bien)
        charts = create_altair_chart(row)
        for chart in charts:
            st.altair_chart(chart, use_container_width=True)

with tab_carga:
    st.subheader("Carga Masiva de Pacientes (Excel/CSV)")
    
    if st.session_state.role != "admin":
        # Esta pestaña ahora es visible para doctores, pero solo el Admin puede cargar archivos
        st.warning("La carga masiva de archivos está reservada para usuarios Administradores.")
    else:
        st.info("Formato esperado: Las columnas deben llamarse: 'nombre_paciente', 'edad', 'imc', 'presion_sistolica', 'glucosa_ayunas', 'creatinina'.")
        uploaded_file = st.file_uploader("Subir archivo de pacientes (.xlsx o .csv)", type=["csv", "xlsx"])
        
        if uploaded_file:
            try:
                # Lectura de archivo
                if uploaded_file.name.endswith('.csv'):
                    df_upload = pd.read_csv(uploaded_file)
                else:
                    df_upload = pd.read_excel(uploaded_file)
                
                required_cols = ["nombre_paciente", "edad", "imc", "presion_sistolica", "glucosa_ayunas", "creatinina"]
                missing_cols = [col for col in required_cols if col not in df_upload.columns]
                
                if missing_cols:
                    st.error(f"El archivo debe contener las siguientes columnas: {', '.join(required_cols)}. Faltan: {', '.join(missing_cols)}")
                elif len(df_upload) < 1:
                    st.warning("El archivo está vacío.")
                else:
                    st.success(f"Archivo cargado. {len(df_upload)} registros encontrados. Procesando...")
                    
                    processed_records = []
                    start_time = time.time()
                    
                    # 1. Asegurar tipos de datos y manejar errores
                    df_upload['nombre_paciente'] = df_upload['nombre_paciente'].astype(str).fillna('Paciente Desconocido')
                    
                    # 2. Aplicar la predicción a cada fila
                    for index, row in df_upload.iterrows():
                        try:
                            # Convertir a float y validar rangos básicos (simplificado)
                            patient_row = {
                                "edad": float(row["edad"]), 
                                "imc": float(row["imc"]), 
                                "presion_sistolica": float(row["presion_sistolica"]),
                                "glucosa_ayunas": float(row["glucosa_ayunas"]), 
                                "creatinina": float(row["creatinina"])
                            }
                            
                            risk = predict_risk(patient_row)
                            nivel, _, _ = get_risk_level(risk)
                            
                            record = {
                                "nombre_paciente": row["nombre_paciente"],
                                "user_id": st.session_state.user_id,
                                "usuario": st.session_state.username,
                                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                                **patient_row,
                                "risk": risk,
                                "nivel": nivel
                            }
                            processed_records.append(record)
                        except Exception:
                            # Capturar cualquier error de conversión o dato faltante/nulo
                            st.warning(f"Fila {index+1} ({row.get('nombre_paciente', 'N/A')}): Datos inválidos o faltantes. Ignorando.")

                    if processed_records:
                        db.add_patient_records_bulk(processed_records)
                        end_time = time.time()
                        
                        st.balloons()
                        st.success(f"¡Carga masiva completada! Se procesaron {len(processed_records)} registros en {end_time - start_time:.2f} segundos.")
                        
                        # Mostrar una vista previa de los primeros 10 registros procesados
                        st.markdown("#### Vista Previa de Registros Cargados")
                        st.dataframe(pd.DataFrame(processed_records)[required_cols + ["risk", "nivel"]].head(10), use_container_width=True)
                        st.info("Ahora puedes ver los pacientes en la pestaña 'Historial'.")
                    else:
                        st.error("No se pudo procesar ningún registro válido del archivo.")
            
            except Exception as e:
                st.error(f"Error general al procesar el archivo. Asegúrate de que el formato sea correcto. Error: {e}")
                # st.exception(e) # Comentado para evitar mostrar traceback al usuario final


with tab_historial:
    st.subheader("Historial de pacientes")
    names = db.get_all_patient_names()
    
    if names:
        selected = st.selectbox("Seleccionar paciente", [""] + names)
        
        if selected:
            records = db.get_patient_records(selected)
            df = pd.DataFrame(records)
             
            # Análisis General del Historial
            analysis_text, analysis_color = get_general_analysis(records)
            st.markdown(f"""
                <div style="border: 2px solid {analysis_color}; padding: 15px; border-radius: 10px; margin-bottom: 20px;">
                    <h4 style="color: #002868; margin: 0 0 5px 0;">Análisis General de Historial</h4>
                    <p style="color: {analysis_color}; font-weight: bold; font-size: 1.1rem; margin: 0;">{analysis_text}</p>
                </div>
            """, unsafe_allow_html=True)
             
            # Mostrar historial de registros
            st.markdown("#### Registros de Predicción Previos")
            st.dataframe(df[["timestamp", "usuario", "risk", "nivel", "creatinina", "glucosa_ayunas", "presion_sistolica"]].rename(columns={"usuario": "Doctor"}), use_container_width=True)
    else:
        st.info("Aún no hay registros de pacientes en la base de datos.")


# =============================================
# PESTAÑA DE ADMINISTRACIÓN (SOLO ADMIN)
# =============================================
if tab_admin is not None:
    with tab_admin:
        st.subheader("Panel de Administración de Usuarios")
        
        # --- 1. Crear Doctor ---
        st.markdown("#### Crear Nuevo Usuario Doctor")
        with st.form("new_doctor"):
            new_user = st.text_input("Nombre de Usuario (Login)").lower()
            new_pwd = st.text_input("Contraseña", type="password")
            
            if st.form_submit_button("Crear Usuario Doctor"):
                if new_user and new_pwd:
                    success, message = db.add_user(new_user, new_pwd, "doctor") 
                    if success:
                        st.success(message)
                        time.sleep(1)
                        st.rerun() 
                    else:
                        st.error(message)
                else:
                    st.error("El usuario y la contraseña son obligatorios.")

        st.markdown("---")
        
        # --- 2. Lista y Eliminar Doctores ---
        st.markdown("#### Doctores Registrados")
        doctors_data = db.get_all_doctors()
        
        if doctors_data:
            df_doctors = pd.DataFrame.from_dict(doctors_data, orient='index')
            df_doctors['Username'] = df_doctors.index
            df_doctors['Rol'] = df_doctors['role']
            df_doctors = df_doctors[['Username', 'Rol', 'id', 'active']]
            df_doctors = df_doctors.rename(columns={'id': 'ID de Sistema', 'active': 'Activo'})
            
            st.dataframe(df_doctors, use_container_width=True, hide_index=True)
            
            st.markdown("##### Eliminar Doctor")
            
            deletable_users = sorted([
                u for u in doctors_data.keys() 
                if doctors_data[u].get("role") == "doctor" and u != st.session_state.username
            ])
            
            user_to_delete = st.selectbox("Seleccionar Doctor a Eliminar", 
                                          [""] + deletable_users)
            
            if st.button("Confirmar Eliminación", type="primary"):
                if user_to_delete:
                    if db.delete_user(user_to_delete):
                        st.success(f"Doctor '{user_to_delete}' eliminado.")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(f"Error al eliminar al doctor '{user_to_delete}'.")
                else:
                    st.warning("Selecciona un doctor para eliminar.")
        else:
            st.info("No hay doctores registrados.")


st.markdown("---")
st.caption("En NefroPredict cuidamos tu salud")
