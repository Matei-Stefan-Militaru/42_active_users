# api/auth.py

import streamlit as st
import requests
import urllib3
from config.settings import AUTH_URL

# Deshabilitar warnings de SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

@st.cache_data(ttl=3500)
def get_auth_token(client_id, client_secret):
    """Obtener token de acceso sin verificación SSL"""
    
    data = {
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret,
    }
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json',
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    
    try:
        st.info("🔑 Conectando con API 42 (SSL bypass)...")
        
        # Usar sesión persistente
        session = requests.Session()
        session.verify = False  # Sin verificación SSL
        session.headers.update(headers)
        
        response = session.post(
            AUTH_URL,
            data=data,
            timeout=15,
            allow_redirects=True
        )
        
        if response.status_code == 200:
            token_data = response.json()
            access_token = token_data.get("access_token")
            if access_token:
                st.success("✅ Conectado exitosamente")
                return access_token
            else:
                st.error("❌ Token no encontrado en respuesta")
                return None
        else:
            st.error(f"❌ Error de autenticación: {response.status_code}")
            st.error(f"Response: {response.text[:200]}")
            return None
            
    except Exception as e:
        st.error(f"❌ Error de conexión: {str(e)}")
        st.error("💡 Prueba: 1) Limpiar cache, 2) Verificar credenciales, 3) Esperar unos minutos")
        return None
