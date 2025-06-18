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
        font-size: 1.2rem;
        font-weight: bold;
        text-align: center;
        margin-bottom: 0.2rem;
    }
    .status-success { 
        background: #e8f5e8; 
        border-left: 2px solid #4caf50; 
        padding: 4px; 
        border-radius: 2px; 
        font-size: 0.7rem;
    }
    .status-info { 
        background: #e3f2fd; 
        border-left: 2px solid #2196f3; 
        padding: 4px; 
        border-radius: 2px; 
        font-size: 0.7rem;
    }
    .metric-card {
        background: white;
        padding: 0.2rem;
        border-radius: 3px;
        box-shadow: 0 1px 2px rgba(0,0,0,0.1);
        border-left: 2px solid #667eea;
    }
    /* Reducir espaciado general */
    .block-container {
        padding-top: 0.3rem;
        padding-bottom: 0.3rem;
    }
    /* Métricas más pequeñas */
    div[data-testid="metric-container"] {
        background-color: #f8f9fa;
        border-radius: 3px;
        padding: 0.15rem;
        border-left: 2px solid #667eea;
    }
    div[data-testid="metric-container"] label {
        font-size: 0.6rem !important;
        font-weight: 600;
    }
    div[data-testid="metric-container"] div[data-testid="metric-value"] {
        font-size: 0.8rem !important;
        font-weight: bold;
    }
    /* Sidebar más compacto */
    .css-1d391kg {
        padding-top: 0.3rem;
    }
    /* Títulos más pequeños */
    h1, h2, h3, h4 {
        margin-bottom: 0.2rem !important;
        margin-top: 0.2rem !important;
    }
    h1 {
        font-size: 1.2rem !important;
    }
    h2 {
        font-size: 0.9rem !important;
    }
    h3 {
        font-size: 0.8rem !important;
    }
    h4 {
        font-size: 0.75rem !important;
    }
    /* Reducir espaciado de elementos */
    .stSelectbox, .stSlider, .stCheckbox, .stTextInput, .stNumberInput {
        margin-bottom: 0.2rem !important;
    }
    /* Texto general más pequeño */
    .stMarkdown p {
        font-size: 0.8rem;
        margin-bottom: 0.2rem;
    }
    /* Botones más pequeños */
    .stButton button {
        font-size: 0.75rem !important;
        padding: 0.2rem 0.4rem !important;
    }
    /* DataFrames más compactos */
    .stDataFrame {
        font-size: 0.7rem;
    }
    /* Sidebar elementos más pequeños */
    .stSidebar .stSelectbox label, .stSidebar .stSlider label {
        font-size: 0.7rem !important;
    }
    /* Expanders más compactos */
    .streamlit-expanderHeader {
        font-size: 0.75rem !important;
    }
    /* Caption más pequeño */
    .stCaption {
        font-size: 0.65rem !important;
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
