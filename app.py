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
        font-size: 1.4rem;
        font-weight: bold;
        text-align: center;
        margin-bottom: 0.3rem;
    }
    .status-success { 
        background: #e8f5e8; 
        border-left: 3px solid #4caf50; 
        padding: 6px; 
        border-radius: 3px; 
        font-size: 0.75rem;
    }
    .status-info { 
        background: #e3f2fd; 
        border-left: 3px solid #2196f3; 
        padding: 6px; 
        border-radius: 3px; 
        font-size: 0.75rem;
    }
    .metric-card {
        background: white;
        padding: 0.3rem;
        border-radius: 4px;
        box-shadow: 0 1px 2px rgba(0,0,0,0.1);
        border-left: 2px solid #667eea;
    }
    /* Reducir espaciado general */
    .block-container {
        padding-top: 0.5rem;
        padding-bottom: 0.5rem;
    }
    /* Métricas más pequeñas */
    div[data-testid="metric-container"] {
        background-color: #f8f9fa;
        border-radius: 4px;
        padding: 0.25rem;
        border-left: 2px solid #667eea;
    }
    div[data-testid="metric-container"] > div {
        width: fit-content;
        margin: auto;
    }
    div[data-testid="metric-container"] label {
        font-size: 0.65rem !important;
        font-weight: 600;
    }
    div[data-testid="metric-container"] div[data-testid="metric-value"] {
        font-size: 0.9rem !important;
        font-weight: bold;
    }
    /* Sidebar más compacto */
    .css-1d391kg {
        padding-top: 0.5rem;
    }
    /* Títulos más pequeños */
    h1, h2, h3 {
        margin-bottom: 0.25rem !important;
        margin-top: 0.25rem !important;
    }
    h1 {
        font-size: 1.4rem !important;
    }
    h2 {
        font-size: 1rem !important;
    }
    h3 {
        font-size: 0.9rem !important;
    }
    /* Reducir espaciado de elementos */
    .stSelectbox, .stSlider, .stCheckbox, .stTextInput, .stNumberInput {
        margin-bottom: 0.25rem !important;
    }
    /* Texto general más pequeño */
    .stMarkdown p {
        font-size: 0.85rem;
    }
    /* Botones más pequeños */
    .stButton button {
        font-size: 0.8rem !important;
        padding: 0.25rem 0.5rem !important;
    }
    /* Dataframe más compacto */
    .stDataFrame {
        font-size: 0.75rem;
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
