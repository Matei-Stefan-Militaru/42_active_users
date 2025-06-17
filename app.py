import streamlit as st
import pandas as pd
import requests
import plotly.express as px
from datetime import datetime, timedelta
import json
import time

# Configuración de la API de 42
API_BASE = "https://api.intra.42.fr"

class FortyTwoAPI:
    def __init__(self, client_id, client_secret):
        self.client_id = client_id
        self.client_secret = client_secret
        self.access_token = None
        self.rate_limit_remaining = 1200
        self.rate_limit_reset = None
        self._authenticate()
    
    def _authenticate(self):
        """Obtener token de acceso de la API de 42"""
        auth_url = f"{API_BASE}/oauth/token"
        
        data = {
            'grant_type': 'client_credentials',
            'client_id': self.client_id,
            'client_secret': self.client_secret
        }
        
        try:
            response = requests.post(auth_url, data=data)
            
            if response.status_code == 200:
                token_data = response.json()
                self.access_token = token_data['access_token']
                st.success("✅ Autenticación exitosa con la API de 42")
            else:
                error_details = ""
                try:
                    error_info = response.json()
                    error_details = f" - {error_info.get('error_description', error_info.get('error', 'Error desconocido'))}"
                except:
                    error_details = f" - HTTP {response.status_code}"
                
                st.error(f"❌ Error al autenticar con la API de 42{error_details}")
                return
                
        except requests.exceptions.RequestException as e:
            st.error(f"❌ Error de conexión: {str(e)}")
            return
    
    def get_headers(self):
        return {'Authorization': f'Bearer {self.access_token}'}
    
    def test_api_endpoints(self):
        """Probar diferentes endpoints para debugging"""
        st.header("🔍 Probando Endpoints de la API")
        
        # Probar endpoint de usuario actual
        st.subheader("1. Probando /v2/me")
        try:
            response = requests.get(f"{API_BASE}/v2/me", headers=self.get_headers())
            st.write(f"Status: {response.status_code}")
            if response.status_code == 200:
                st.json(response.json())
            else:
                st.write(f"Error: {response.text}")
        except Exception as e:
            st.error(f"Error: {e}")
        
        # Probar endpoint de usuarios generales
        st.subheader("2. Probando /v2/users (primeros 10)")
        try:
            params = {'page': 1, 'per_page': 10}
            response = requests.get(f"{API_BASE}/v2/users", headers=self.get_headers(), params=params)
            st.write(f"Status: {response.status_code}")
            if response.status_code == 200:
                users = response.json()
                st.write(f"Usuarios obtenidos: {len(users)}")
                if users:
                    st.json(users[0])  # Mostrar primer usuario
            else:
                st.write(f"Error: {response.text}")
        except Exception as e:
            st.error(f"Error: {e}")
        
        # Probar endpoint de campus
        st.subheader("3. Probando /v2/campus (primeros 5)")
        try:
            params = {'page': 1, 'per_page': 5}
            response = requests.get(f"{API_BASE}/v2/campus", headers=self.get_headers(), params=params)
            st.write(f"Status: {response.status_code}")
            if response.status_code == 200:
                campus_list = response.json()
                st.write(f"Campus obtenidos: {len(campus_list)}")
                if campus_list:
                    st.json(campus_list[0])  # Mostrar primer campus
            else:
                st.write(f"Error: {response.text}")
        except Exception as e:
            st.error(f"Error: {e}")
    
    def get_users_simple(self, max_pages=3):
        """Obtener usuarios de forma simple sin filtros por campus"""
        st.subheader("4. Obteniendo usuarios generales")
        all_users = []
        
        for page in range(1, max_pages + 1):
            st.write(f"Página {page}...")
            try:
                params = {
                    'page': page,
                    'per_page': 100
                }
                
                response = requests.get(f"{API_BASE}/v2/users", headers=self.get_headers(), params=params)
                st.write(f"Status página {page}: {response.status_code}")
                
                if response.status_code == 200:
                    users_data = response.json()
                    st.write(f"Usuarios en página {page}: {len(users_data)}")
                    
                    if not users_data:
                        break
                    
                    all_users.extend(users_data)
                    
                    if len(users_data) < 100:
                        break
                        
                    time.sleep(1)  # Pausa entre requests
                    
                else:
                    st.error(f"Error en página {page}: {response.text}")
                    break
                    
            except Exception as e:
                st.error(f"Error en página {page}: {e}")
                break
        
        st.success(f"Total usuarios obtenidos: {len(all_users)}")
        return all_users
    
    def test_campus_endpoint(self, campus_id):
        """Probar endpoint específico de campus"""
        st.subheader(f"5. Probando campus específico (ID: {campus_id})")
        
        # Probar diferentes variaciones del endpoint
        endpoints_to_test = [
            f"/v2/campus/{campus_id}/users",
            f"/v2/campus/{campus_id}/users?page=1&per_page=10",
            f"/v2/users?filter[campus_id]={campus_id}&page=1&per_page=10"
        ]
        
        for endpoint in endpoints_to_test:
            st.write(f"Probando: {endpoint}")
            try:
                response = requests.get(f"{API_BASE}{endpoint}", headers=self.get_headers())
                st.write(f"Status: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    st.write(f"Resultados: {len(data) if isinstance(data, list) else 'No es lista'}")
                    if isinstance(data, list) and data:
                        st.json(data[0])
                    elif isinstance(data, dict):
                        st.json(data)
                else:
                    st.write(f"Error: {response.text}")
                    
            except Exception as e:
                st.error(f"Error: {e}")
            
            st.write("---")
    
    def get_all_campus(self):
        """Obtener todos los campus"""
        all_campus = []
        page = 1
        
        while True:
            try:
                params = {
                    'page': page,
                    'per_page': 100
                }
                
                response = requests.get(f"{API_BASE}/v2/campus", headers=self.get_headers(), params=params)
                
                if response.status_code == 200:
                    campus_data = response.json()
                    
                    if not campus_data:
                        break
                    
                    all_campus.extend(campus_data)
                    
                    if len(campus_data) < 100:
                        break
                    
                    page += 1
                    time.sleep(0.5)
                    
                else:
                    st.error(f"Error al obtener campus: HTTP {response.status_code}")
                    break
                    
            except Exception as e:
                st.error(f"Error: {e}")
                break
        
        return all_campus

def analyze_users_data(users):
    """Analizar datos de usuarios obtenidos"""
    if not users:
        st.warning("No hay usuarios para analizar")
        return
    
    st.header("📊 Análisis de Datos Obtenidos")
    
    # Estadísticas básicas
    st.subheader("Estadísticas Básicas")
    st.write(f"Total usuarios: {len(users)}")
    
    # Analizar estructura de un usuario
    if users:
        st.subheader("Estructura de Usuario (primer usuario)")
        st.json(users[0])
        
    # Analizar campus
    campus_info = {}
    cursus_info = {}
    kinds = {}
    
    for user in users:
        # Campus
        campus_users = user.get('campus_users', [])
        for campus_user in campus_users:
            campus_name = campus_user.get('campus', {}).get('name', 'Unknown')
            campus_info[campus_name] = campus_info.get(campus_name, 0) + 1
        
        # Cursus
        cursus_users = user.get('cursus_users', [])
        for cursus_user in cursus_users:
            cursus_name = cursus_user.get('cursus', {}).get('name', 'Unknown')
            cursus_info[cursus_name] = cursus_info.get(cursus_name, 0) + 1
        
        # Kind
        kind = user.get('kind', 'Unknown')
        kinds[kind] = kinds.get(kind, 0) + 1
    
    # Mostrar análisis
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.subheader("Campus (Top 10)")
        sorted_campus = sorted(campus_info.items(), key=lambda x: x[1], reverse=True)[:10]
        for campus, count in sorted_campus:
            st.write(f"{campus}: {count}")
    
    with col2:
        st.subheader("Cursus (Top 10)")
        sorted_cursus = sorted(cursus_info.items(), key=lambda x: x[1], reverse=True)[:10]
        for cursus, count in sorted_cursus:
            st.write(f"{cursus}: {count}")
    
    with col3:
        st.subheader("Tipos de Usuario")
        for kind, count in kinds.items():
            st.write(f"{kind}: {count}")

def create_streamlit_dashboard():
    st.set_page_config(
        page_title="42 API Debug",
        page_icon="🔍",
        layout="wide"
    )
    
    st.title("🔍 42 API Debug Tool")
    st.markdown("### Herramienta de debugging para la API de 42")
    
    # Sidebar para configuración
    with st.sidebar:
        st.header("⚙️ Configuración")
        
        # Usar secrets para credenciales
        try:
            client_id = st.secrets["api"]["client_id"]
            client_secret = st.secrets["api"]["client_secret"]
            st.success("🔒 Credenciales cargadas desde secrets.toml")
        except (KeyError, FileNotFoundError):
            st.error("❌ No se encontraron credenciales en secrets.toml")
            st.info("Crea un archivo .streamlit/secrets.toml con:")
            st.code("""
[api]
client_id = "tu_client_id"
client_secret = "tu_client_secret"
""")
            return
        
        # Configuración de debugging
        st.header("🔧 Opciones de Debug")
        max_pages_users = st.slider("Páginas de usuarios a obtener", 1, 10, 3)
        test_specific_campus = st.checkbox("Probar campus específico")
        
        if test_specific_campus:
            campus_id_to_test = st.number_input("ID del campus a probar", min_value=1, value=1)
    
    # Inicializar API
    try:
        api = FortyTwoAPI(client_id, client_secret)
        
        if not api.access_token:
            st.error("❌ No se pudo obtener token de acceso")
            return
            
    except Exception as e:
        st.error(f"Error al conectar con la API: {e}")
        return
    
    # Botones de testing
    st.header("🚀 Pruebas de API")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🔍 Probar Endpoints Básicos", type="primary"):
            api.test_api_endpoints()
    
    with col2:
        if st.button("👥 Obtener Usuarios Generales", type="primary"):
            users = api.get_users_simple(max_pages=max_pages_users)
            if users:
                st.session_state['users_data'] = users
                analyze_users_data(users)
    
    with col3:
        if test_specific_campus and st.button("🏫 Probar Campus Específico", type="primary"):
            api.test_campus_endpoint(campus_id_to_test)
    
    # Mostrar datos guardados si existen
    if 'users_data' in st.session_state:
        st.header("💾 Datos Guardados en Sesión")
        users_data = st.session_state['users_data']
        st.write(f"Usuarios en memoria: {len(users_data)}")
        
        if st.button("🔄 Re-analizar Datos"):
            analyze_users_data(users_data)
        
        if st.button("📥 Descargar Datos JSON"):
            json_data = json.dumps(users_data, indent=2)
            st.download_button(
                label="Descargar JSON",
                data=json_data,
                file_name=f"42_users_debug_{datetime.now().strftime('%Y%m%d_%H%M')}.json",
                mime="application/json"
            )

if __name__ == "__main__":
    create_streamlit_dashboard()
