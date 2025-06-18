# api/auth.py

import streamlit as st
import requests
import time
from config.settings import AUTH_URL, DEFAULT_HEADERS

@st.cache_data(ttl=3500)
def get_auth_token(client_id, client_secret):
    """Obtener token de acceso con mejor manejo de errores"""
    
    # Validar credenciales
    if not client_id or not client_secret:
        st.error("❌ Credenciales vacías. Verifica client_id y client_secret en secrets.")
        return None
    
    if client_id == "TU_CLIENT_ID" or client_secret == "TU_CLIENT_SECRET":
        st.error("❌ Credenciales de ejemplo detectadas. Configura las credenciales reales.")
        return None
    
    # Datos para la autenticación
    data = {
        "grant_type": "client_credentials",
        "client_id": str(client_id).strip(),
        "client_secret": str(client_secret).strip(),
    }
    
    # Headers mejorados
    headers = {
        'User-Agent': '42-Network-Evaluator/2.3',
        'Accept': 'application/json',
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    
    try:
        st.info("🔑 Autenticando con API 42...")
        
        # Hacer request con timeout más largo
        response = requests.post(
            AUTH_URL, 
            data=data, 
            headers=headers,
            timeout=30,
            verify=True
        )
        
        # Debug información
        st.write(f"🔍 **Debug Auth:**")
        st.write(f"- URL: {AUTH_URL}")
        st.write(f"- Status: {response.status_code}")
        st.write(f"- Client ID (primeros 10 chars): {str(client_id)[:10]}...")
        
        if response.status_code == 200:
            token_data = response.json()
            access_token = token_data.get("access_token")
            
            if access_token:
                st.success("✅ Autenticación exitosa")
                return access_token
            else:
                st.error("❌ Token no encontrado en respuesta")
                st.json(token_data)
                return None
                
        elif response.status_code == 401:
            st.error("❌ **Error 401: Credenciales incorrectas**")
            st.error("Verifica que client_id y client_secret sean correctos")
            
            # Mostrar información adicional para debug
            try:
                error_data = response.json()
                st.error(f"Detalle del error: {error_data}")
            except:
                st.error(f"Response text: {response.text}")
            return None
            
        elif response.status_code == 403:
            st.error("❌ **Error 403: Permisos denegados**")
            st.error("Tu aplicación no tiene permisos para acceder a la API")
            return None
            
        elif response.status_code == 429:
            st.error("❌ **Error 429: Rate limit**")
            st.error("Demasiadas requests. Espera un momento e intenta de nuevo.")
            return None
            
        else:
            st.error(f"❌ **Error {response.status_code}:** {response.reason}")
            try:
                error_data = response.json()
                st.json(error_data)
            except:
                st.text(response.text)
            return None
            
    except requests.exceptions.Timeout:
        st.error("❌ **Timeout:** La API tardó demasiado en responder")
        return None
        
    except requests.exceptions.ConnectionError:
        st.error("❌ **Error de conexión:** No se pudo conectar a la API de 42")
        st.error("Verifica tu conexión a internet")
        return None
        
    except requests.exceptions.RequestException as e:
        st.error(f"❌ **Error de request:** {str(e)}")
        return None
        
    except Exception as e:
        st.error(f"❌ **Error inesperado:** {str(e)}")
        return None

def test_token(token):
    """Probar si el token funciona"""
    if not token:
        return False
        
    headers = {
        "Authorization": f"Bearer {token}",
        **DEFAULT_HEADERS
    }
    
    try:
        # Probar con endpoint simple
        test_url = "https://api.intra.42.fr/v2/me"
        response = requests.get(test_url, headers=headers, timeout=10)
        
        st.write(f"🧪 **Test token:** Status {response.status_code}")
        
        if response.status_code == 200:
            user_data = response.json()
            st.success(f"✅ Token válido para usuario: {user_data.get('login', 'unknown')}")
            return True
        elif response.status_code == 401:
            st.error("❌ Token inválido o expirado")
            return False
        else:
            st.warning(f"⚠️ Response inesperado: {response.status_code}")
            return False
            
    except Exception as e:
        st.error(f"❌ Error probando token: {str(e)}")
        return False
