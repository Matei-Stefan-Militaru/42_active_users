import streamlit as st
import pandas as pd
import requests
import plotly.express as px
from datetime import datetime, timedelta
import json

# Configuración de la API de 42
API_BASE = "https://api.intra.42.fr"

class FortyTwoAPI:
    def __init__(self, client_id, client_secret):
        self.client_id = client_id
        self.client_secret = client_secret
        self.access_token = None
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
                self.access_token = response.json()['access_token']
                st.success("✅ Autenticación exitosa con la API de 42")
            else:
                error_details = ""
                try:
                    error_info = response.json()
                    error_details = f" - {error_info.get('error_description', error_info.get('error', 'Error desconocido'))}"
                except:
                    error_details = f" - HTTP {response.status_code}"
                
                st.error(f"❌ Error al autenticar con la API de 42{error_details}")
                
                # Mostrar ayuda para errores comunes
                if response.status_code == 401:
                    st.warning("🔍 **Posibles causas:**")
                    st.info("• Client ID o Client Secret incorrectos\n• La aplicación OAuth no está configurada correctamente\n• Las credenciales han expirado")
                elif response.status_code == 400:
                    st.warning("🔍 **Error de configuración:**")
                    st.info("• Verifica que el grant_type sea 'client_credentials'\n• Revisa los parámetros de la aplicación OAuth")
                
        except requests.exceptions.RequestException as e:
            st.error(f"❌ Error de conexión: {str(e)}")
            st.info("Verifica tu conexión a internet")
    
    def get_headers(self):
        return {'Authorization': f'Bearer {self.access_token}'}
    
    def get_users_by_campus(self, campus_id, page=1, per_page=100):
        """Obtener usuarios de un campus específico"""
        url = f"{API_BASE}/v2/campus/{campus_id}/users"
        params = {
            'page': page,
            'per_page': per_page,
            'filter[kind]': 'student',  # Solo estudiantes
            'sort': 'level',
            'filter[active]': 'true'
        }
        response = requests.get(url, headers=self.get_headers(), params=params)
        return response.json() if response.status_code == 200 else []
    
    def get_all_campus(self):
        """Obtener todos los campus"""
        url = f"{API_BASE}/v2/campus"
        response = requests.get(url, headers=self.get_headers())
        return response.json() if response.status_code == 200 else []
    
    def get_user_cursus_details(self, user_id):
        """Obtener detalles del cursus de un usuario"""
        url = f"{API_BASE}/v2/users/{user_id}/cursus_users"
        response = requests.get(url, headers=self.get_headers())
        return response.json() if response.status_code == 200 else []

class RankingProcessor:
    def __init__(self):
        # Definir los rangos basados en niveles de 42
        self.level_ranges = {
            0: "Piscina",
            1: "Rango 1 (Básico)",
            2: "Rango 2 (Shell/C)",
            3: "Rango 3 (Algoritmos)",
            4: "Rango 4 (Sistemas)",
            5: "Rango 5 (Redes/Web)",
            6: "Rango 6 (Avanzado)",
            7: "Rango 7+ (Especialización)"
        }
    
    def determine_range(self, level):
        """Determinar el rango basado en el nivel"""
        if level is None:
            return "Sin datos"
        
        level_int = int(level)
        if level_int >= 7:
            return self.level_ranges[7]
        else:
            return self.level_ranges.get(level_int, "Desconocido")
    
    def filter_active_students(self, users):
        """Filtrar estudiantes activos (no en blackhole, activos recientes)"""
        filtered = []
        cutoff_date = datetime.now() - timedelta(days=90)  # 3 meses
        
        for user in users:
            # Filtrar cuentas test
            if user.get('kind') == 'test':
                continue
            
            # Filtrar blackholed
            if user.get('blackholed_at'):
                continue
            
            # Filtrar por actividad reciente
            last_seen = user.get('last_seen_at')
            if last_seen:
                last_seen_date = datetime.fromisoformat(last_seen.replace('Z', '+00:00'))
                if last_seen_date < cutoff_date:
                    continue
            
            filtered.append(user)
        
        return filtered
    
    def process_user_data(self, users, campus_info):
        """Procesar datos de usuarios para el ranking"""
        processed_data = []
        
        for user in users:
            cursus_data = user.get('cursus_users', [])
            main_cursus = None
            
            # Buscar el cursus principal (42cursus)
            for cursus in cursus_data:
                if cursus.get('cursus', {}).get('name') == '42cursus':
                    main_cursus = cursus
                    break
            
            if not main_cursus:
                continue
            
            user_data = {
                'login': user.get('login'),
                'display_name': user.get('displayname', user.get('login')),
                'level': main_cursus.get('level', 0),
                'range': self.determine_range(main_cursus.get('level')),
                'grade': main_cursus.get('grade'),
                'campus': campus_info.get('name', 'Unknown'),
                'country': campus_info.get('country', 'Unknown'),
                'city': campus_info.get('city', 'Unknown'),
                'blackholed_at': main_cursus.get('blackholed_at'),
                'last_seen': user.get('last_seen_at'),
                'wallet': user.get('wallet', 0),
                'correction_points': user.get('correction_point', 0)
            }
            
            processed_data.append(user_data)
        
        return processed_data

def create_streamlit_dashboard():
    st.set_page_config(
        page_title="42 Global Ranking",
        page_icon="🚀",
        layout="wide"
    )
    
    st.title("🚀 42 Network Global Ranking")
    st.markdown("### Ranking global de estudiantes de 42 con filtros avanzados")
    
    # Sidebar para configuración
    with st.sidebar:
        st.header("⚙️ Configuración API")
        st.info("**Límites:** 2 req/segundo, 1200 req/hora")
        
        # Usar secrets para credenciales
        try:
            client_id = st.secrets["api"]["client_id"]
            client_secret = st.secrets["api"]["client_secret"]
            st.success("🔒 Credenciales configuradas correctamente")
        except (KeyError, FileNotFoundError):
            st.warning("⚠️ Usando modo desarrollo - configura secrets.toml para producción")
            
            # Campos temporales para desarrollo
            with st.expander("🔧 Configuración temporal (solo para desarrollo)"):
                st.markdown("**📋 Instrucciones para obtener credenciales:**")
                st.markdown("""
                1. Ve a [profile.intra.42.fr/oauth/applications](https://profile.intra.42.fr/oauth/applications)
                2. Haz clic en "New Application"
                3. Configura:
                   - **Name**: Cualquier nombre (ej: "42 Ranking Dashboard")
                   - **Redirect URI**: `urn:ietf:wg:oauth:2.0:oob`
                   - **Scopes**: Selecciona `public`
                4. Copia las credenciales generadas
                """)
                
                client_id = st.text_input("Client ID", type="password", help="UID de tu aplicación OAuth")
                client_secret = st.text_input("Client Secret", type="password", help="Secret de tu aplicación OAuth")
                
                if client_id and client_secret:
                    st.success("🔑 Credenciales introducidas - Haz clic en 'Cargar Ranking' para probar")
                else:
                    st.warning("⚠️ Introduce ambas credenciales para continuar")
                    
                if not (client_id and client_secret):
                    return
    
    # Inicializar API
    try:
        api = FortyTwoAPI(client_id, client_secret)
        processor = RankingProcessor()
    except Exception as e:
        st.error(f"Error al conectar con la API: {e}")
        return
    
    # Obtener campus disponibles
    with st.spinner("Cargando campus disponibles..."):
        all_campus = api.get_all_campus()
    
    if not all_campus:
        st.error("No se pudieron cargar los campus")
        return
    
    # Crear diccionario de países y campus
    countries = {}
    for campus in all_campus:
        country = campus.get('country', 'Unknown')
        if country not in countries:
            countries[country] = []
        countries[country].append(campus)
    
    # Filtros principales
    st.header("🔍 Filtros")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        selected_countries = st.multiselect(
            "Países",
            options=list(countries.keys()),
            default=list(countries.keys())[:5]  # Primeros 5 países por defecto
        )
    
    with col2:
        # Campus disponibles según países seleccionados
        available_campus = []
        for country in selected_countries:
            available_campus.extend(countries[country])
        
        campus_options = {f"{c['name']} ({c['country']})": c for c in available_campus}
        selected_campus = st.multiselect(
            "Campus",
            options=list(campus_options.keys()),
            default=list(campus_options.keys())
        )
    
    with col3:
        selected_ranges = st.multiselect(
            "Rangos",
            options=list(processor.level_ranges.values()),
            default=list(processor.level_ranges.values())
        )
    
    # Botón para cargar datos
    if st.button("🔄 Cargar Ranking", type="primary"):
        all_student_data = []
        
        # Barra de progreso
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        selected_campus_objects = [campus_options[name] for name in selected_campus]
        
        for i, campus in enumerate(selected_campus_objects):
            status_text.text(f"Cargando {campus['name']}...")
            
            # Obtener estudiantes del campus
            students = api.get_users_by_campus(campus['id'])
            
            # Filtrar estudiantes activos
            active_students = processor.filter_active_students(students)
            
            # Procesar datos
            processed_students = processor.process_user_data(active_students, campus)
            all_student_data.extend(processed_students)
            
            # Actualizar progreso
            progress_bar.progress((i + 1) / len(selected_campus_objects))
        
        status_text.text("¡Datos cargados!")
        
        # Crear DataFrame
        df = pd.DataFrame(all_student_data)
        
        if df.empty:
            st.warning("No se encontraron datos con los filtros seleccionados")
            return
        
        # Filtrar por rangos seleccionados
        df_filtered = df[df['range'].isin(selected_ranges)]
        
        # Mostrar estadísticas generales
        st.header("📊 Estadísticas Generales")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Estudiantes", len(df_filtered))
        
        with col2:
            avg_level = df_filtered['level'].mean()
            st.metric("Nivel Promedio", f"{avg_level:.2f}")
        
        with col3:
            active_campus = df_filtered['campus'].nunique()
            st.metric("Campus Activos", active_campus)
        
        with col4:
            countries_count = df_filtered['country'].nunique()
            st.metric("Países", countries_count)
        
        # Gráfico de distribución por rangos
        st.header("📈 Distribución por Rangos")
        range_counts = df_filtered['range'].value_counts()
        fig = px.bar(
            x=range_counts.index,
            y=range_counts.values,
            title="Estudiantes por Rango",
            labels={'x': 'Rango', 'y': 'Número de Estudiantes'}
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # Ranking principal
        st.header("🏆 Ranking Global")
        
        # Ordenar por nivel descendente
        df_sorted = df_filtered.sort_values('level', ascending=False)
        
        # Añadir posición en el ranking
        df_sorted['posicion'] = range(1, len(df_sorted) + 1)
        
        # Mostrar tabla
        display_columns = ['posicion', 'login', 'display_name', 'level', 'range', 'campus', 'country']
        st.dataframe(
            df_sorted[display_columns],
            column_config={
                'posicion': st.column_config.NumberColumn('Pos.', width="small"),
                'login': st.column_config.TextColumn('Login', width="medium"),
                'display_name': st.column_config.TextColumn('Nombre', width="medium"),
                'level': st.column_config.NumberColumn('Nivel', width="small", format="%.2f"),
                'range': st.column_config.TextColumn('Rango', width="medium"),
                'campus': st.column_config.TextColumn('Campus', width="medium"),
                'country': st.column_config.TextColumn('País', width="small")
            },
            hide_index=True,
            use_container_width=True
        )
        
        # Top 10 por país
        st.header("🌍 Top 10 por País")
        for country in selected_countries:
            country_data = df_filtered[df_filtered['country'] == country].head(10)
            if not country_data.empty:
                st.subheader(f"🏁 {country}")
                st.dataframe(
                    country_data[['login', 'level', 'range', 'campus']],
                    hide_index=True
                )

if __name__ == "__main__":
    create_streamlit_dashboard()
