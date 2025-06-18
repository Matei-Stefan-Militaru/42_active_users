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
        font-size: 2.5rem;
        font-weight: bold;
        text-align: center;
        margin-bottom: 1rem;
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
