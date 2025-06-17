import streamlit as st
import requests
import pandas as pd
import plotly.express as px

st.set_page_config(layout="wide")

st.title("📊 42 Active Users - API Stats")

# Mostrar cómo deben ser los secrets en la interfaz
with st.expander("🔐 Cómo configurar tus secrets"):
    st.markdown("Agrega esto a tus secrets en Streamlit:")
    st.code("""
[api]
client_id = "TU_CLIENT_ID"
client_secret = "TU_CLIENT_SECRET"
""", language="toml")

# Obtener credenciales de st.secrets
credentials = st.secrets.get("api", {})
client_id = credentials.get("client_id")
client_secret = credentials.get("client_secret")

if not client_id or not client_secret:
    st.error("Faltan credenciales en los secrets. Verifica que estén correctamente configuradas.")
    st.stop()

# Autenticación con la API de 42
auth_url = "https://api.intra.42.fr/oauth/token"
data = {
    "grant_type": "client_credentials",
    "client_id": client_id,
    "client_secret": client_secret,
}
auth_response = requests.post(auth_url, data=data)

if auth_response.status_code != 200:
    st.error("Error al obtener el token de acceso de la API 42")
    st.write(auth_response.json())
    st.stop()

access_token = auth_response.json().get("access_token")
headers = {"Authorization": f"Bearer {access_token}"}

# Obtener usuarios activos
campus_id = 46  # Ajusta este valor a tu campus si es necesario
url = f"https://api.intra.42.fr/v2/campus/{campus_id}/locations?per_page=100"

users = []
while url:
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        st.error("Error al obtener datos de usuarios.")
        break

    data = response.json()
    users.extend(data)

    # Paginación
    url = response.links.get("next", {}).get("url")

# Procesar datos
if users:
    df = pd.DataFrame(users)
    if "user" in df.columns:
        df["login"] = df["user"].apply(lambda u: u["login"] if isinstance(u, dict) else None)
    else:
        st.warning("No se encontró la columna 'user' en los datos recibidos.")
        st.stop()

    st.subheader("👤 Usuarios activos actualmente")
    st.write(df[["login", "begin_at", "end_at"]])

    # Gráfico de barras
    df["hora"] = pd.to_datetime(df["begin_at"]).dt.hour
    counts = df["hora"].value_counts().sort_index()
    chart = px.bar(x=counts.index, y=counts.values, labels={"x": "Hora", "y": "Cantidad de usuarios"}, title="Actividad por hora")
    st.plotly_chart(chart, use_container_width=True)

else:
    st.info("No hay usuarios activos en este momento.")

