# api/auth.py

import streamlit as st
import requests
import time
from config.settings import AUTH_URL

@st.cache_data(ttl=3500)
def get_auth_token(client_id, client_secret):
    """Obtener token de acceso con reintentos automáticos"""
    
    # Datos para la autenticación
    data = {
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret,
    }
    
    # Headers
    headers = {
        'User-Agent': '42-Network-Evaluator/2.3',
        'Accept': 'application/json',
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    
    # Intentar varias veces con diferentes configuraciones
    max_retries = 3
    
    for attempt in range(max_retries):
        try:
            # Configurar requests con SSL más permisivo
            response = requests.post(
                AUTH_URL, 
                data=data, 
                headers=headers, 
                timeout=30,
                verify=True,  # Primero intentar con verificación SSL
                allow_redirects=True
            )
            
            if response.status_code == 200:
                return response.json().get("access_token")
            elif response.status_code == 526:
                # Error SSL específico - intentar sin verificación SSL
                st.warning(f"⚠️ Error SSL (intento {attempt + 1}/{max_retries}). Reintentando...")
                time.sleep(2)
                
                # Segundo intento sin verificar SSL
                response = requests.post(
                    AUTH_URL, 
                    data=data, 
                    headers=headers, 
                    timeout=30,
                    verify=False,  # Sin verificación SSL
                    allow_redirects=True
                )
                
                if response.status_code == 200:
                    st.warning("⚠️ Conectado sin verificación SSL")
                    return response.json().get("access_token")
                    
            else:
                st.error(f"❌ Error de autenticación: {response.status_code}")
                if attempt < max_retries - 1:
                    st.info(f"🔄 Reintentando en 3 segundos... (intento {attempt + 1}/{max_retries})")
                    time.sleep(3)
                else:
                    return None
                    
        except requests.exceptions.SSLError as e:
            st.warning(f"⚠️ Error SSL (intento {attempt + 1}/{max_retries}): {str(e)}")
            if attempt < max_retries - 1:
                time.sleep(2)
            else:
                st.error("❌ Error SSL persistente. La API de 42 puede tener problemas temporales.")
                return None
                
        except Exception as e:
            st.error(f"❌ Error de conexión: {str(e)}")
            if attempt < max_retries - 1:
                time.sleep(2)
            else:
                return None
    
    return None
