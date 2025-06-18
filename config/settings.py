# config/settings.py

# API Configuration
API_BASE_URL = "https://api.intra.42.fr"
AUTH_URL = f"{API_BASE_URL}/oauth/token"

# Default values
DEFAULT_DAYS_BACK = 7
DEFAULT_MAX_USERS = 200
DEFAULT_MAX_PAGES = 20
DEFAULT_PAGE_SIZE = 100
DETAIL_LIMIT = 50

# CSS Styles
MAIN_CSS = """
<style>
    /* ========== HEADER PRINCIPAL - VERSIÓN SIMPLE ========== */
    .main-header {
        color: #667eea;           /* Color sólido azul */
        font-size: 2rem;          /* Tamaño del título principal */
        font-weight: bold;
        text-align: center;
        margin-bottom: 0.5rem;    /* Espacio debajo del header */
        margin-top: 0rem;         /* Espacio arriba del header */
        text-shadow: 1px 1px 2px rgba(0,0,0,0.1); /* Sombra sutil */
    }
    
    /* ========== CAJAS DE ESTADO ========== */
    .status-success { 
        background: #e8f5e8; 
        border-left: 4px solid #4caf50; 
        padding: 10px;            /* Espacio interno de cajas verdes */
        border-radius: 4px; 
    }
    .status-info { 
        background: #e3f2fd; 
        border-left: 4px solid #2196f3; 
        padding: 10px;            /* Espacio interno de cajas azules */
        border-radius: 4px; 
    }
    .metric-card {
        background: white;
        padding: 1rem;            /* Espacio interno de tarjetas de métricas */
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        border-left: 4px solid #667eea;
    }
    
    /* ========== CONFIGURACIÓN GENERAL DE LAYOUT ========== */
    /* Sidebar pegado arriba y compacto */
    .css-1d391kg {
        padding-top: 0rem !important;     /* Qué tan arriba está el sidebar (0 = pegado) */
        margin-top: 0rem !important;
    }
    /* Contenido principal */
    .block-container {
        padding-top: 0.5rem !important;   /* Qué tan arriba está el contenido principal */
        margin-top: 0rem !important;
    }
    
    /* ========== SIDEBAR - Elementos más pequeños ========== */
    /* Títulos del sidebar */
    .stSidebar h2 {
        font-size: 0.9rem !important;     /* Tamaño títulos H2 en sidebar */
        margin-top: 0.2rem !important;    /* Espacio arriba de títulos H2 */
        margin-bottom: 0.3rem !important; /* Espacio debajo de títulos H2 */
    }
    .stSidebar h3 {
        font-size: 0.8rem !important;     /* Tamaño títulos H3 en sidebar */
        margin-top: 0.2rem !important;    /* Espacio arriba de títulos H3 */
        margin-bottom: 0.2rem !important; /* Espacio debajo de títulos H3 */
    }
    
    /* Elementos de entrada del sidebar (selectbox, slider, etc.) */
    .stSidebar .stSelectbox, .stSidebar .stSlider, .stSidebar .stCheckbox, .stSidebar .stTextInput, .stSidebar .stNumberInput {
        margin-bottom: 0.2rem !important; /* Espacio entre elementos del sidebar */
    }
    
    /* Labels de elementos del sidebar */
    .stSidebar .stSelectbox label, .stSidebar .stSlider label, .stSidebar .stCheckbox label {
        font-size: 0.75rem !important;    /* Tamaño de labels en sidebar */
        margin-bottom: 0.1rem !important; /* Espacio debajo de labels */
    }
    
    /* Botones del sidebar */
    .stSidebar .stButton button {
        font-size: 0.75rem !important;    /* Tamaño texto botones sidebar */
        padding: 0.3rem 0.5rem !important; /* Espacio interno botones sidebar */
        margin-bottom: 0.2rem !important; /* Espacio debajo botones sidebar */
    }
    
    /* Texto normal del sidebar */
    .stSidebar .stMarkdown p {
        font-size: 0.75rem !important;    /* Tamaño texto párrafos sidebar */
        margin-bottom: 0.2rem !important; /* Espacio debajo párrafos sidebar */
    }
    .stSidebar .stMarkdown strong {
        font-size: 0.75rem !important;    /* Tamaño texto en negrita sidebar */
    }
    
    /* Métricas del sidebar */
    .stSidebar .stMetric {
        margin-bottom: 0.1rem !important; /* Espacio entre métricas sidebar */
    }
    .stSidebar div[data-testid="metric-container"] label {
        font-size: 0.65rem !important;    /* Tamaño labels métricas sidebar */
    }
    .stSidebar div[data-testid="metric-container"] div[data-testid="metric-value"] {
        font-size: 0.8rem !important;     /* Tamaño valores métricas sidebar */
    }
    
    /* Expanders (menús desplegables) del sidebar */
    .stSidebar .streamlit-expanderHeader {
        font-size: 0.8rem !important;     /* Tamaño texto expanders sidebar */
        padding: 0.3rem !important;       /* Espacio interno expanders sidebar */
    }
    
    /* Separadores (líneas) del sidebar */
    .stSidebar hr {
        margin-top: 0.3rem !important;    /* Espacio arriba de separadores */
        margin-bottom: 0.3rem !important; /* Espacio debajo de separadores */
    }
    
    /* Info del campus seleccionado */
    .stSidebar .status-success {
        font-size: 0.7rem !important;     /* Tamaño texto info campus */
        padding: 4px !important;          /* Espacio interno info campus */
    }
    
    /* ========== CONTENIDO PRINCIPAL - Tamaño normal y legible ========== */
    /* Métricas principales (las 6 columnas de números) */
    div[data-testid="metric-container"] {
        background-color: #f8f9fa;
        border-radius: 6px;
        padding: 0.5rem;                   /* Espacio interno métricas principales */
        border-left: 3px solid #667eea;
    }
    div[data-testid="metric-container"] label {
        font-size: 0.8rem !important;     /* Tamaño labels métricas principales */
        font-weight: 600;
    }
    div[data-testid="metric-container"] div[data-testid="metric-value"] {
        font-size: 1.2rem !important;     /* Tamaño valores métricas principales */
        font-weight: bold;
    }
    
    /* Títulos principales del contenido */
    h1 {
        font-size: 2rem !important;       /* Tamaño título H1 (header principal) */
        margin-top: 0rem !important;      /* Espacio arriba H1 */
    }
    h2 {
        font-size: 1.5rem !important;     /* Tamaño títulos H2 contenido */
    }
    h3 {
        font-size: 1.3rem !important;     /* Tamaño títulos H3 contenido */
    }
    h4 {
        font-size: 1.1rem !important;     /* Tamaño títulos H4 contenido */
    }
    
    /* Texto principal del contenido */
    .stMarkdown p {
        font-size: 1rem;                  /* Tamaño texto párrafos principales */
    }
    
    /* Botones principales del contenido */
    .stButton button {
        font-size: 0.9rem !important;     /* Tamaño texto botones principales */
        padding: 0.5rem 1rem !important;  /* Espacio interno botones principales */
    }
    
    /* Tablas de datos principales */
    .stDataFrame {
        font-size: 0.85rem;               /* Tamaño texto en tablas */
    }
    
    /* Texto pequeño (captions) */
    .stCaption {
        font-size: 0.8rem !important;     /* Tamaño texto explicativo pequeño */
    }
    
    /* ========== TU CÓDIGO PERSONALIZADO ========== */
    /* Añade aquí tus modificaciones específicas */
    .st-emotion-cache-16txtl3 {
        padding: 1rem 1.5rem;              /* Tu modificación personalizada */
    }
    
    /* Cambiar altura del elemento específico */
    .st-emotion-cache-1r4qj8v {
        height: 500px !important;          /* Cambia 500px por la altura que quieras */
        /* O también puedes usar: */
        /* min-height: 300px !important; */
        /* max-height: 800px !important; */
    }
    
    /* Si quieres que sea más genérico y funcione siempre, usa esto en su lugar: */
    /*
    [class*="st-emotion-cache"] {
        padding: 1rem 1.5rem !important;   /* Aplica a todas las clases similares */
    }
    */
    
</style>
"""

# Search methods
SEARCH_METHODS = ["Híbrido", "Solo actividad reciente", "Solo ubicaciones activas"]

# App configuration
APP_CONFIG = {
    "page_title": "42 Network - Finding Your Evaluator",
    "page_icon": "🚀",
    "layout": "wide"
}

# Rate limiting
DEFAULT_RETRY_AFTER = 2
AUTO_REFRESH_INTERVAL = 60

# External app URLs
EXTERNAL_APPS = {
    "tickets": "https://42activeusers-tickets.streamlit.app/",
    "stats": "https://42stats.streamlit.app/"
}

# Headers para las requests
DEFAULT_HEADERS = {
    'User-Agent': '42-Network-Evaluator/2.3',
    'Accept': 'application/json',
    'Content-Type': 'application/json'
}
