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
        font-size: 1.8rem;
        font-weight: bold;
        text-align: center;
        margin-bottom: 0.5rem;
    }
    .status-success { 
        background: #e8f5e8; 
        border-left: 4px solid #4caf50; 
        padding: 8px; 
        border-radius: 4px; 
        font-size: 0.85rem;
    }
    .status-info { 
        background: #e3f2fd; 
        border-left: 4px solid #2196f3; 
        padding: 8px; 
        border-radius: 4px; 
        font-size: 0.85rem;
    }
    .metric-card {
        background: white;
        padding: 0.5rem;
        border-radius: 6px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        border-left: 3px solid #667eea;
    }
    /* Reducir espaciado general */
    .block-container {
        padding-top: 1rem;
        padding-bottom: 1rem;
    }
    /* Métricas más compactas */
    div[data-testid="metric-container"] {
        background-color: #f8f9fa;
        border-radius: 6px;
        padding: 0.5rem;
        border-left: 3px solid #667eea;
    }
    div[data-testid="metric-container"] > div {
        width: fit-content;
        margin: auto;
    }
    div[data-testid="metric-container"] label {
        font-size: 0.75rem !important;
        font-weight: 600;
    }
    div[data-testid="metric-container"] div[data-testid="metric-value"] {
        font-size: 1.1rem !important;
        font-weight: bold;
    }
    /* Sidebar más compacto */
    .css-1d391kg {
        padding-top: 1rem;
    }
    /* Títulos más pequeños */
    h1, h2, h3 {
        margin-bottom: 0.5rem !important;
        margin-top: 0.5rem !important;
    }
    h2 {
        font-size: 1.3rem !important;
    }
    h3 {
        font-size: 1.1rem !important;
    }
    /* Reducir espaciado de elementos */
    .stSelectbox, .stSlider, .stCheckbox {
        margin-bottom: 0.5rem !important;
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
