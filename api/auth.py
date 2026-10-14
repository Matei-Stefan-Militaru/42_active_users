# api/auth.py

import streamlit as st
import requests
from config.settings import AUTH_URL, DEFAULT_HEADERS

@st.cache_data(ttl=3500)
def get_auth_token(client_id, client_secret):
    """Obtener token de acceso"""
    data = {
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret,
    }
    
    try:
        response = requests.post(AUTH_URL, headers=DEFAULT_HEADERS, data=data, timeout=10)
        if response.status_code == 200:
            return response.json().get("access_token")
        elif response.status_code == 403 and "just a moment" in response.text.lower():
            st.error("❌ Cloudflare bloqueó la petición (403). Reintenta en unos segundos.")
            return None
        else:
            st.error(f"❌ Error de autenticación: {response.status_code}")
            return None
    except Exception as e:
        st.error(f"❌ Error de conexión: {str(e)}")
        return None
