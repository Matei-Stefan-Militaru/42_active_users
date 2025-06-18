# api/auth.py

import streamlit as st
import requests
from config.settings import AUTH_URL

@st.cache_data(ttl=3500)
def get_auth_token(client_id, client_secret):
    """Obtener token de acceso"""
    
    # Datos para la autenticación
    data = {
        "grant_type": "client_credentials",
        "client_id": str(client_id).strip(),
        "client_secret": str(client_secret).strip(),
    }
    
    # Headers
    headers = {
        'User-Agent': '42-Network-Evaluator/2.3',
        'Accept': 'application/json',
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    
    try:
        st.info("🔑 Autenticando con API 42...")
        
        response = requests.post(AUTH_URL, data=data, headers=headers, timeout=30)
        
        st.write(f"🔍 **Debug Auth:**")
        st.write(f"- URL: {AUTH_URL}")
        st.write(f"- Status: {response.status_code}")
        st.write(f"- Client ID: {str(client_id)[:10]}...")
        
        if response.status_code == 200:
            token_data = response.json()
            access_token = token_data.get("access_token")
            
            if access_token:
                st.success("✅ Autenticación exitosa")
                return access_token
            else:
                st.error("❌ Token no encontrado en respuesta")
                return None
                
        elif response.status_code == 401:
            st.error("❌ **Error 401: Credenciales incorrectas**")
            try:
                error_data = response.json()
                st.error(f"Detalle: {error_data}")
            except:
                st.error(f"Response: {response.text}")
            return None
            
        else:
            st.error(f"❌ **Error {response.status_code}:** {response.reason}")
            return None
            
    except Exception as e:
        st.error(f"❌ **Error:** {str(e)}")
        return None
