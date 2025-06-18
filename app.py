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
        font-size: 0.9rem;
        font-weight: bold;
        text-align: center;
        margin-bottom: 0.1rem;
    }
    .status-success { 
        background: #e8f5e8; 
        border-left: 1px solid #4caf50; 
        padding: 2px; 
        border-radius: 1px; 
        font-size: 0.55rem;
    }
    .status-info { 
        background: #e3f2fd; 
        border-left: 1px solid #2196f3; 
        padding: 2px; 
        border-radius: 1px; 
        font-size: 0.55rem;
    }
    .metric-card {
        background: white;
        padding: 0.1rem;
        border-radius: 2px;
        box-shadow: 0 1px 1px rgba(0,0,0,0.1);
        border-left: 1px solid #667eea;
    }
    /* Reducir espaciado general */
    .block-container {
        padding-top: 0.1rem;
        padding-bottom: 0.1rem;
    }
    /* Métricas súper pequeñas */
    div[data-testid="metric-container"] {
        background-color: #f8f9fa;
        border-radius: 2px;
        padding: 0.1rem;
        border-left: 1px solid #667eea;
    }
    div[data-testid="metric-container"] label {
        font-size: 0.5rem !important;
        font-weight: 600;
    }
    div[data-testid="metric-container"] div[data-testid="metric-value"] {
        font-size: 0.65rem !important;
        font-weight: bold;
    }
    /* Sidebar más compacto */
    .css-1d391kg {
        padding-top: 0.1rem;
    }
    /* Títulos súper pequeños */
    h1, h2, h3, h4, h5, h6 {
        margin-bottom: 0.1rem !important;
        margin-top: 0.1rem !important;
    }
    h1 {
        font-size: 0.9rem !important;
    }
    h2 {
        font-size: 0.7rem !important;
    }
    h3 {
        font-size: 0.65rem !important;
    }
    h4 {
        font-size: 0.6rem !important;
    }
    /* Reducir espaciado de elementos */
    .stSelectbox, .stSlider, .stCheckbox, .stTextInput, .stNumberInput {
        margin-bottom: 0.1rem !important;
    }
    /* Texto general súper pequeño */
    .stMarkdown p {
        font-size: 0.6rem;
        margin-bottom: 0.1rem;
    }
    /* Botones súper pequeños */
    .stButton button {
        font-size: 0.6rem !important;
        padding: 0.1rem 0.2rem !important;
        height: 1.5rem !important;
    }
    /* DataFrames súper compactos */
    .stDataFrame {
        font-size: 0.55rem;
    }
    /* Sidebar elementos súper pequeños */
    .stSidebar .stSelectbox label, .stSidebar .stSlider label, .stSidebar .stCheckbox label {
        font-size: 0.55rem !important;
    }
    /* Expanders súper compactos */
    .streamlit-expanderHeader {
        font-size: 0.6rem !important;
    }
    /* Caption súper pequeño */
    .stCaption {
        font-size: 0.5rem !important;
    }
    /* Input labels más pequeños */
    label {
        font-size: 0.55rem !important;
    }
    /* Plotly charts más pequeños */
    .js-plotly-plot .plotly .modebar {
        height: 20px !important;
    }
    /* Reducir altura de inputs */
    .stSelectbox > div > div {
        min-height: 1.5rem !important;
    }
    .stTextInput > div > div > input {
        height: 1.5rem !important;
        font-size: 0.6rem !important;
    }
    /* Slider más pequeño */
    .stSlider > div > div > div {
        height: 1rem !important;
    }
    /* Checkbox más pequeño */
    .stCheckbox > label {
        font-size: 0.55rem !important;
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
