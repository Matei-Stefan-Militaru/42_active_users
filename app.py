import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta

# Título de la app
st.set_page_config(page_title="42 Active Users", layout="wide")
st.title("👨‍💻 Usuarios activos en 42")

# Leer credenciales desde [api42] en st.secrets
credentials = st.secrets.get("api42", {})
client_id = credentials.get("client_id")
client_secret = credentials.get("client_secret")

if not client_id or not client_secret:
    st.error("Faltan credenciales en los secrets. Verifica que estén correctamente configuradas en [api42].")
    st.stop()

# Obtener token de acceso
auth_url = "https://api.intra.42.fr/oauth/token"
data = {
    "grant_type": "client_credentials",
    "client_id": client_id,
    "client_secret": client_secret,
}
response = requests.post(auth_url, data=data)
access_token = response.json().get("access_token")

if not access_token:
    st.error("No se pudo obtener el token de acceso.")
    st.stop()

headers = {"Authorization": f"Bearer {access_token}"}

# Función para obtener los campus
@st.cache_data(ttl=3600)
def get_campus():
    res = requests.get("https://api.intra.42.fr/v2/campus", headers=headers)
    return res.json()

campus_list = get_campus()
campus_dict = {campus["name"]: campus["id"] for campus in campus_list}

# Selección de campus
selected_campus = st.selectbox("Selecciona un campus", list(campus_dict.keys()))
campus_id = campus_dict[selected_campus]

# Función para obtener usuarios activos en el último día
def get_active_users(campus_id):
    users = []
    page = 1
    now = datetime.utcnow()
    yesterday = now - timedelta(days=1)
    date_filter = yesterday.strftime("%Y-%m-%dT%H:%M:%SZ")

    while True:
        url = (
            f"https://api.intra.42.fr/v2/campus/{campus_id}/users?"
            f"page[size]=100&page[number]={page}&"
            f"sort=-updated_at&filter[updated_at]={date_filter},"
        )
        res = requests.get(url, headers=headers)
        data = res.json()
        if not data:
            break
        users.extend(data)
        page += 1

    return users

if st.button("🔍 Ver usuarios activos"):
    with st.spinner("Cargando usuarios activos..."):
        users = get_active_users(campus_id)
        if not users:
            st.info("No se encontraron usuarios activos en las últimas 24 horas.")
        else:
            df = pd.DataFrame([
                {
                    "Login": user["login"],
                    "Nombre": user["displayname"],
                    "Correo": user["email"],
                    "Última conexión": user["updated_at"]
                }
                for user in users
            ])
            df["Última conexión"] = pd.to_datetime(df["Última conexión"]).dt.tz_localize(None)
            st.success(f"Usuarios activos en las últimas 24 horas: {len(df)}")
            st.dataframe(df, use_container_width=True)
