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
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 2rem;
        font-weight: bold;
        text-align: center;
        margin-bottom: 0.5rem;
        margin-top: 0rem;
    }
    .status-success { 
        background: #e8f5e8; 
        border-left: 4px solid #4caf50; 
        padding: 10px; 
        border-radius: 4px; 
    }
    .status-info { 
        background: #e3f2fd; 
        border-left: 4px solid #2196f3; 
        padding: 10px; 
        border-radius: 4px; 
    }
    .metric-card {
        background: white;
        padding: 1rem;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        border-left: 4px solid #667eea;
    }
    /* SIDEBAR MÁS COMPACTO Y PEGADO ARRIBA */
    .css-1d391kg {
        padding-top: 0rem !important;
        margin-top: 0rem !important;
    }
    /* Contenido principal más arriba */
    .block-container {
        padding-top: 0.5rem !important;
        margin-top: 0rem !important;
    }
    /* SIDEBAR - Elementos más pequeños */
    .stSidebar h2 {
        font-size: 0.9rem !important;
        margin-top: 0.2rem !important;
        margin-bottom: 0.3rem !important;
    }
    .stSidebar h3 {
        font-size: 0.8rem !important;
        margin-top: 0.2rem !important;
        margin-bottom: 0.2rem !important;
    }
    .stSidebar .stSelectbox, .stSidebar .stSlider, .stSidebar .stCheckbox, .stSidebar .stTextInput, .stSidebar .stNumberInput {
        margin-bottom: 0.2rem !important;
    }
    .stSidebar .stSelectbox label, .stSidebar .stSlider label, .stSidebar .stCheckbox label {
        font-size: 0.75rem !important;
        margin-bottom: 0.1rem !important;
    }
    .stSidebar .stButton button {
        font-size: 0.75rem !important;
        padding: 0.3rem 0.5rem !important;
        margin-bottom: 0.2rem !important;
    }
    .stSidebar .stMarkdown p {
        font-size: 0.75rem !important;
        margin-bottom: 0.2rem !important;
    }
    .stSidebar .stMarkdown strong {
        font-size: 0.75rem !important;
    }
    .stSidebar .stMetric {
        margin-bottom: 0.1rem !important;
    }
    .stSidebar div[data-testid="metric-container"] label {
        font-size: 0.65rem !important;
    }
    .stSidebar div[data-testid="metric-container"] div[data-testid="metric-value"] {
        font-size: 0.8rem !important;
    }
    /* Expanders del sidebar más compactos */
    .stSidebar .streamlit-expanderHeader {
        font-size: 0.8rem !important;
        padding: 0.3rem !important;
    }
    /* Separadores más pequeños en sidebar */
    .stSidebar hr {
        margin-top: 0.3rem !important;
        margin-bottom: 0.3rem !important;
    }
    /* Campus info más compacto */
    .stSidebar .status-success {
        font-size: 0.7rem !important;
        padding: 4px !important;
    }
    
    /* CONTENIDO PRINCIPAL - Tamaño normal y legible */
    /* Métricas principales normales */
    div[data-testid="metric-container"] {
        background-color: #f8f9fa;
        border-radius: 6px;
        padding: 0.5rem;
        border-left: 3px solid #667eea;
    }
    div[data-testid="metric-container"] label {
        font-size: 0.8rem !important;
        font-weight: 600;
    }
    div[data-testid="metric-container"] div[data-testid="metric-value"] {
        font-size: 1.2rem !important;
        font-weight: bold;
    }
    /* Títulos principales normales */
    h1 {
        font-size: 2rem !important;
        margin-top: 0rem !important;
    }
    h2 {
        font-size: 1.5rem !important;
    }
    h3 {
        font-size: 1.3rem !important;
    }
    h4 {
        font-size: 1.1rem !important;
    }
    /* Texto principal normal */
    .stMarkdown p {
        font-size: 1rem;
    }
    /* Botones principales normales */
    .stButton button {
        font-size: 0.9rem !important;
        padding: 0.5rem 1rem !important;
    }
    /* DataFrames normales */
    .stDataFrame {
        font-size: 0.85rem;
    }
    /* Captions normales */
    .stCaption {
        font-size: 0.8rem !important;
    }
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
