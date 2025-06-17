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
                
                # Mostrar ayuda para errores comunes
                if response.status_code == 401:
                    st.warning("🔍 **Posibles causas:**")
                    st.info("• Client ID o Client Secret incorrectos\n• La aplicación OAuth no está configurada correctamente\n• Verifica que tengas los scopes correctos")
                elif response.status_code == 400:
                    st.warning("🔍 **Error de configuración:**")
                    st.info("• La aplicación debe usar 'Client Credentials' flow\n• Verifica los scopes de la aplicación")
                
        except requests.exceptions.RequestException as e:
            st.error(f"❌ Error de conexión: {str(e)}")
            st.info("Verifica tu conexión a internet")
    
    def _handle_rate_limit(self, response):
        """Manejar límites de rate limiting"""
        if 'X-RateLimit-Remaining' in response.headers:
            self.rate_limit_remaining = int(response.headers['X-RateLimit-Remaining'])
        
        if 'X-RateLimit-Reset' in response.headers:
            self.rate_limit_reset = int(response.headers['X-RateLimit-Reset'])
        
        # Si nos acercamos al límite, hacer pausa
        if self.rate_limit_remaining < 10:
            st.warning("⚠️ Acercándose al límite de rate limit, pausando...")
            time.sleep(2)
    
    def get_headers(self):
        return {'Authorization': f'Bearer {self.access_token}'}
    
    def get_users_by_campus(self, campus_id, max_pages=10):
        """Obtener usuarios de un campus específico con paginación mejorada"""
        all_users = []
        page = 1
        
        while page <= max_pages:
            url = f"{API_BASE}/v2/campus/{campus_id}/users"
            params = {
                'page': page,
                'per_page': 100,
                'sort': '-level'  # Ordenar por nivel descendente
            }
            
            try:
                response = requests.get(url, headers=self.get_headers(), params=params)
                self._handle_rate_limit(response)
                
                if response.status_code == 200:
                    users_data = response.json()
                    
                    # Si no hay usuarios, terminar
                    if not users_data or len(users_data) == 0:
                        break
                    
                    all_users.extend(users_data)
                    
                    # Si recibimos menos de 100, es la última página
                    if len(users_data) < 100:
                        break
                    
                    page += 1
                    time.sleep(0.5)  # Pausa para respetar rate limit
                    
                elif response.status_code == 429:
                    st.warning("⚠️ Rate limit alcanzado, pausando...")
                    time.sleep(60)  # Pausa de 1 minuto
                    continue
                else:
                    st.warning(f"⚠️ Error al obtener usuarios del campus {campus_id}: HTTP {response.status_code}")
                    break
                    
            except requests.exceptions.RequestException as e:
                st.error(f"❌ Error de conexión al obtener usuarios: {str(e)}")
                break
        
        return all_users
    
    def get_all_campus(self):
        """Obtener todos los campus con paginación"""
        all_campus = []
        page = 1
        
        while True:
            url = f"{API_BASE}/v2/campus"
            params = {
                'page': page,
                'per_page': 100,
                'sort': 'name'
            }
            
            try:
                response = requests.get(url, headers=self.get_headers(), params=params)
                self._handle_rate_limit(response)
                
                if response.status_code == 200:
                    campus_data = response.json()
                    
                    if not campus_data or len(campus_data) == 0:
                        break
                    
                    all_campus.extend(campus_data)
                    
                    if len(campus_data) < 100:
                        break
                    
                    page += 1
                    time.sleep(0.5)
                    
                else:
                    st.error(f"Error al obtener campus: HTTP {response.status_code}")
                    break
                    
            except requests.exceptions.RequestException as e:
                st.error(f"Error de conexión al obtener campus: {str(e)}")
                break
        
        return all_campus

class RankingProcessor:
    def __init__(self):
        # Definir los rangos basados en niveles de 42
        self.level_ranges = {
            0: "Piscina (0-1)",
            1: "Rango 1 (1-2)",
            2: "Rango 2 (2-3)",
            3: "Rango 3 (3-4)",
            4: "Rango 4 (4-5)",
            5: "Rango 5 (5-6)",
            6: "Rango 6 (6-7)",
            7: "Rango 7+ (7+)"
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
        """Filtrar estudiantes con criterios más flexibles"""
        filtered = []
        cutoff_date = datetime.now() - timedelta(days=365)  # 1 año (más flexible)
        
        for user in users:
            # Filtrar cuentas test y admin
            if user.get('kind') in ['test', 'admin', 'staff']:
                continue
            
            # Incluir usuarios aunque estén en blackhole (algunos pueden estar temporalmente)
            # Solo filtrar si han estado en blackhole por más de 6 meses
            blackholed_at = user.get('blackholed_at')
            if blackholed_at:
                try:
                    blackhole_date = datetime.fromisoformat(blackholed_at.replace('Z', '+00:00'))
                    if datetime.now() - blackhole_date > timedelta(days=180):
                        continue
                except:
                    pass
            
            # Filtro de actividad más flexible
            last_seen = user.get('last_seen_at')
            if last_seen:
                try:
                    last_seen_date = datetime.fromisoformat(last_seen.replace('Z', '+00:00'))
                    if last_seen_date < cutoff_date:
                        continue
                except:
                    pass
            
            filtered.append(user)
        
        return filtered
    
    def process_user_data(self, users, campus_info):
        """Procesar datos de usuarios para el ranking"""
        processed_data = []
        
        for user in users:
            cursus_data = user.get('cursus_users', [])
            main_cursus = None
            
            # Buscar el cursus principal (42cursus o 42)
            for cursus in cursus_data:
                cursus_name = cursus.get('cursus', {}).get('name', '').lower()
                if cursus_name in ['42cursus', '42', 'common core']:
                    main_cursus = cursus
                    break
            
            # Si no encontramos cursus principal, tomar el primero disponible
            if not main_cursus and cursus_data:
                main_cursus = cursus_data[0]
            
            if not main_cursus:
                continue
            
            level = main_cursus.get('level', 0)
            
            # Solo incluir usuarios con nivel > 0 para filtrar inactive
            if level <= 0:
                continue
            
            user_data = {
                'login': user.get('login'),
                'display_name': user.get('displayname', user.get('login')),
                'level': level,
                'range': self.determine_range(level),
                'grade': main_cursus.get('grade'),
                'campus': campus_info.get('name', 'Unknown'),
                'country': campus_info.get('country', 'Unknown'),
                'city': campus_info.get('city', 'Unknown'),
                'blackholed_at': main_cursus.get('blackholed_at'),
                'last_seen': user.get('last_seen_at'),
                'wallet': user.get('wallet', 0),
                'correction_points': user.get('correction_point', 0),
                'cursus_name': main_cursus.get('cursus', {}).get('name', 'Unknown')
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
        
        # Configuración adicional
        st.header("🔧 Configuración Avanzada")
        max_pages = st.slider("Máximo páginas por campus", 1, 20, 5, help="Más páginas = más datos pero más lento")
        min_level = st.slider("Nivel mínimo", 0.0, 10.0, 0.1, 0.1, help="Filtrar estudiantes por nivel mínimo")
    
    # Inicializar API
    try:
        api = FortyTwoAPI(client_id, client_secret)
        processor = RankingProcessor()
        
        if not api.access_token:
            st.error("❌ No se pudo obtener token de acceso")
            return
            
    except Exception as e:
        st.error(f"Error al conectar con la API: {e}")
        return
    
    # Obtener campus disponibles
    with st.spinner("Cargando campus disponibles..."):
        all_campus = api.get_all_campus()
    
    if not all_campus:
        st.error("No se pudieron cargar los campus")
        return
    
    st.success(f"✅ Cargados {len(all_campus)} campus")
    
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
        # Mostrar países con número de campus
        country_options = {f"{country} ({len(campus_list)} campus)": country 
                          for country, campus_list in countries.items()}
        
        selected_country_labels = st.multiselect(
            "Países",
            options=list(country_options.keys()),
            default=list(country_options.keys())[:3]  # Primeros 3 países por defecto
        )
        
        selected_countries = [country_options[label] for label in selected_country_labels]
    
    with col2:
        # Campus disponibles según países seleccionados
        available_campus = []
        for country in selected_countries:
            available_campus.extend(countries[country])
        
        campus_options = {f"{c['name']} ({c['country']})": c for c in available_campus}
        selected_campus_labels = st.multiselect(
            "Campus",
            options=list(campus_options.keys()),
            default=list(campus_options.keys())[:5]  # Máximo 5 campus por defecto
        )
        
        selected_campus = [campus_options[label] for label in selected_campus_labels]
    
    with col3:
        selected_ranges = st.multiselect(
            "Rangos",
            options=list(processor.level_ranges.values()),
            default=list(processor.level_ranges.values())  # Seleccionar todos por defecto
        )
    
    # Mostrar información antes de cargar
    if selected_campus:
        st.info(f"📊 Se cargarán datos de {len(selected_campus)} campus. Estimado: {len(selected_campus) * max_pages * 100} usuarios máximo.")
    
    # Botón para cargar datos
    if st.button("🔄 Cargar Ranking", type="primary"):
        if not selected_campus:
            st.warning("⚠️ Selecciona al menos un campus")
            return
        
        all_student_data = []
        
        # Barra de progreso
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for i, campus in enumerate(selected_campus):
            status_text.text(f"Cargando {campus['name']} ({i+1}/{len(selected_campus)})...")
            
            # Obtener estudiantes del campus
            students = api.get_users_by_campus(campus['id'], max_pages=max_pages)
            st.write(f"📊 {campus['name']}: {len(students)} usuarios obtenidos")
            
            if len(students) == 0:
                st.warning(f"⚠️ {campus['name']}: No se obtuvieron usuarios. Puede ser un campus vacío o con restricciones de acceso.")
                continue
            
            # Filtrar estudiantes activos
            active_students = processor.filter_active_students(students)
            st.write(f"✅ {campus['name']}: {len(active_students)} estudiantes filtrados")
            
            # Procesar datos
            processed_students = processor.process_user_data(active_students, campus)
            st.write(f"🎯 {campus['name']}: {len(processed_students)} estudiantes procesados")
            
            # Filtrar por nivel mínimo
            processed_students = [s for s in processed_students if s['level'] >= min_level]
            st.write(f"📈 {campus['name']}: {len(processed_students)} estudiantes con nivel >= {min_level}")
            
            all_student_data.extend(processed_students)
            
            # Actualizar progreso
            progress_bar.progress((i + 1) / len(selected_campus))
        
        status_text.text("¡Datos cargados!")
        
        # Crear DataFrame
        df = pd.DataFrame(all_student_data)
        
        # Debug: mostrar información sobre los datos
        if len(all_student_data) > 0:
            st.success(f"📈 Total de estudiantes cargados: {len(all_student_data)}")
            if len(df) > 0:
                ranges_found = df['range'].value_counts()
                st.write("🏷️ Rangos encontrados:", ranges_found.to_dict())
                
                cursus_found = df['cursus_name'].value_counts()
                st.write("📚 Cursus encontrados:", cursus_found.to_dict())
        
        if df.empty:
            st.warning("⚠️ No se encontraron estudiantes válidos en los campus seleccionados")
            st.info("💡 Posibles causas:")
            st.info("• Los campus seleccionados no tienen estudiantes activos")
            st.info("• El nivel mínimo es muy alto")
            st.info("• Problemas de permisos con la API")
            st.info("• Los estudiantes no tienen cursus configurado")
            return
        
        # Filtrar por rangos seleccionados
        df_filtered = df[df['range'].isin(selected_ranges)]
        
        if df_filtered.empty:
            st.warning("⚠️ No se encontraron datos con los rangos seleccionados")
            st.info(f"💡 Rangos disponibles en los datos: {', '.join(df['range'].unique())}")
            st.info(f"🎯 Rangos seleccionados: {', '.join(selected_ranges)}")
            return
        
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
        
        # Distribución por país
        st.header("🌍 Distribución por País")
        country_counts = df_filtered['country'].value_counts()
        fig2 = px.pie(
            values=country_counts.values,
            names=country_counts.index,
            title="Estudiantes por País"
        )
        st.plotly_chart(fig2, use_container_width=True)
        
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
                country_data['posicion_pais'] = range(1, len(country_data) + 1)
                st.dataframe(
                    country_data[['posicion_pais', 'login', 'level', 'range', 'campus']],
                    column_config={
                        'posicion_pais': st.column_config.NumberColumn('Pos.', width="small"),
                        'login': st.column_config.TextColumn('Login', width="medium"),
                        'level': st.column_config.NumberColumn('Nivel', width="small", format="%.2f"),
                        'range': st.column_config.TextColumn('Rango', width="medium"),
                        'campus': st.column_config.TextColumn('Campus', width="medium")
                    },
                    hide_index=True
                )
        
        # Opción de descarga
        st.header("💾 Descargar Datos")
        csv = df_sorted.to_csv(index=False)
        st.download_button(
            label="📥 Descargar ranking completo (CSV)",
            data=csv,
            file_name=f"42_ranking_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv"
        )

if __name__ == "__main__":
    create_streamlit_dashboard()
