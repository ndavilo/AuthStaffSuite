import base64

def get_background_style(image_path="EFCC.jpg"):
    with open(image_path, "rb") as f:
        data = f.read()
    encoded = base64.b64encode(data).decode()

    return f"""
    <style>
    .stApp {{
        background-image: url("data:image/png;base64,{encoded}");
        background-size: cover;
        background-position: center;
        background-repeat: no-repeat;
    }}
    html {{
        scroll-behavior: smooth;
    }}
    </style>
    """

def get_topbar_style():
    """Returns CSS style for the top navigation bar"""
    return """
    <style>
    .top-bar {
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        height: 50px;
        background-color: var(--secondary-bg);
        display: flex;
        align-items: center;
        padding: 0 15px;
        z-index: 999999;
        box-shadow: 0 2px 10px rgba(0,0,0,0.2);
        border-bottom: 1px solid var(--border-color);
    }
    .top-bar-content {
        display: flex;
        align-items: center;
        width: 100%;
    }
    .top-bar-logo {
        margin-right: 5px;
        height: 40px;
        display: flex;
        align-items: center;
    }
    .top-bar-title {
        color: var(--sidebar-text);
        font-weight: bold;
        font-size: 18px;
    }
    .main-content {
        margin-top: 60px;
    }
    @media (max-width: 768px) {
        .top-bar {
            height: 45px;
            padding: 0 10px;
        }
        .top-bar-title {
            font-size: 16px;
        }
        .main-content {
            margin-top: 55px;
        }
    }
    </style>
    """

LAGOS_STYLE = """
<style>
:root {
    /* Dark mode colors */
    --black-bean: #320001;
    --dark-chocolate: #450302;
    --blood-red: #630001;
    --blood: #8C0402;
    --ue-red: #B70803;
    --ku-crimson: #E81509;
    --white: #FFFFFF;
    --black: #000000;
    
    /* Light mode colors */
    --light-bg: #f5f5f5;
    --light-card: #ffffff;
    --light-text: #333333;
    --light-border: #e0e0e0;
    --light-accent: #d32f2f;
}

/* System preference detection */
@media (prefers-color-scheme: dark) {
    :root {
        --primary-bg: var(--black-bean);
        --secondary-bg: var(--dark-chocolate);
        --primary-text: var(--white);
        --secondary-text: var(--white);
        --accent-color: var(--ku-crimson);
        --border-color: var(--blood-red);
        --input-bg: var(--dark-chocolate);
        --input-text: var(--white);
        --card-bg: linear-gradient(to right, var(--dark-chocolate), var(--black-bean));
        --sidebar-text: var(--white);
    }
}

@media (prefers-color-scheme: light) {
    :root {
        --primary-bg: var(--light-bg);
        --secondary-bg: var(--blood-red);
        --primary-text: var(--black);
        --secondary-text: var(--light-text);
        --accent-color: var(--light-accent);
        --border-color: var(--light-border);
        --input-bg: var(--light-card);
        --input-text: var(--light-text);
        --card-bg: var(--light-card);
        --sidebar-text: var(--white);
    }
}

/* Base styles */
.stApp {
    background-color: var(--primary-bg) !important;
    color: var(--primary-text) !important;
    font-family: 'Segoe UI', Arial, sans-serif !important;
}

/* Header styles */
.header-container {
    display: flex;
    flex-direction: column;
    align-items: center;
    text-align: center;
    margin: 20px auto 0 auto;
    max-width: 600px;
    padding-top: 10px;
}

.logo-container {
    margin: 0 auto 15px auto;
    transition: all 0.3s ease;
}

.logo-container:hover {
    transform: scale(1.02);
}

.header-title {
    font-size: 14pt;
    font-weight: bold;
    margin: 0;
    color: var(--primary-text);
}

.header-subtitle {
    font-size: 12pt;
    margin: 8px 0;
    color: var(--primary-text);
}

.app-title {
    color: var(--accent-color);
    margin-bottom: 8px;
}

.app-slogan {
    font-style: italic;
    color: var(--secondary-text);
    margin: 0;
    font-size: 0.95rem;
}

/* Responsive adjustments */
@media (max-width: 768px) {
    .header-container {
        padding: 10px 15px;
        margin-top: 10px;
    }
    .logo-container img {
        width: 150px;
    }
    .header-title {
        font-size: 13pt;
    }
    .header-subtitle {
        font-size: 11pt;
    }
}

/* Base styles */
.stApp {
    background-color: var(--primary-bg) !important;
    color: var(--primary-text) !important;
    font-family: 'Segoe UI', Arial, sans-serif !important;
}

/* Header styles */
.header-container {
    display: flex;
    flex-direction: column;
    align-items: center;
    text-align: center;
    margin: 0 auto 0 auto; 
    max-width: 600px;
}

.logo-container {
    margin-top: -10px;  /* Added negative margin to move logo up */
    margin-bottom: 20px;
}

.header-title {
    font-size: 14pt;
    font-weight: bold;
    margin: 0;
    color: var(--primary-text);
}

.header-subtitle {
    font-size: 12pt;
    margin: 8px 0;
    color: var(--primary-text);
}

.app-title {
    color: var(--accent-color);
    margin-bottom: 8px;
}

.app-slogan {
    font-style: italic;
    color: var(--secondary-text);
    margin: 0;
}

/* Input fields */
.stTextInput>div>div>input,
.stSelectbox>div>div>select,
.stTextArea>div>div>textarea {
    background-color: var(--input-bg) !important;
    color: var(--input-text) !important;
    border: 1px solid var(--border-color) !important;
    border-radius: 4px !important;
}

/* Buttons */
.stButton>button {
    background: var(--accent-color) !important;
    color: var(--white) !important;
    border: none !important;
    border-radius: 4px !important;
    font-weight: bold !important;
    transition: all 0.3s ease !important;
}

.stButton>button:hover {
    opacity: 0.9 !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 2px 6px rgba(0,0,0,0.2) !important;
}

/* Cards and containers */
.custom-card {
    background: var(--card-bg) !important;
    border: 1px solid var(--border-color) !important;
    border-radius: 8px !important;
    padding: 1.5rem !important;
    box-shadow: 0 4px 8px rgba(0,0,0,0.1) !important;
    color: var(--primary-text) !important;
}

/* Tables */
.stDataFrame {
    background-color: var(--secondary-bg) !important;
    color: var(--primary-text) !important;
}

/* Sidebar */
[data-testid="stSidebar"] {
    background: var(--secondary-bg) !important;
    border-right: 1px solid var(--border-color) !important;
}

/* Sidebar text elements */
[data-testid="stSidebar"] * {
    color: var(--sidebar-text) !important;
}

[data-testid="stSidebar"] .stMarkdown,
[data-testid="stSidebar"] .stText,
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] .stRadio > label,
[data-testid="stSidebar"] .stSelectbox > label,
[data-testid="stSidebar"] .stTextInput > label,
[data-testid="stSidebar"] .stButton > button {
    color: var(--sidebar-text) !important;
}

/* Headers */
.st-emotion-cache-10trblm, h1, h2, h3 {
    color: var(--accent-color) !important;
    border-bottom: 2px solid var(--border-color) !important;
    padding-bottom: 0.5rem !important;
}
</style>
"""

def get_header_style():
    """Returns the CSS style for the header section"""
    return """
    <style>
    .header-container {
        display: flex;
        flex-direction: column;
        align-items: center;
        text-align: center;
        margin: 20px auto 0 auto;
        max-width: 600px;
        padding-top: 10px;
    }
    .logo-container {
        margin: 0 auto 15px auto;
        transition: all 0.3s ease;
    }
    .logo-container:hover {
        transform: scale(1.02);
    }
    .header-title {
        font-size: 14pt;
        font-weight: bold;
        margin: 0;
        color: var(--primary-text);
    }
    .header-subtitle {
        font-size: 12pt;
        margin: 8px 0;
        color: var(--primary-text);
    }
    .app-title {
        color: var(--accent-color);
        margin-bottom: 8px;
    }
    .app-slogan {
        font-style: italic;
        color: var(--secondary-text);
        margin: 0;
        font-size: 0.95rem;
    }
    @media (max-width: 768px) {
        .header-container {
            padding: 10px 15px;
            margin-top: 10px;
        }
        .logo-container img {
            width: 150px;
        }
        .header-title {
            font-size: 13pt;
        }
        .header-subtitle {
            font-size: 11pt;
        }
    }
    </style>
    """

def get_sidebar_logo():
    """Returns HTML for sidebar logo with proper styling"""
    return """
    <div style="text-align: center; margin-bottom: 20px;">
        <img src="data:image/png;base64,{}" style="width: 80%; max-width: 150px; margin: 0 auto; filter: drop-shadow(0 2px 4px rgba(0,0,0,0.2));">
    </div>
    """.format(image_to_base64("EFCC1.png"))

def image_to_base64(image_path):
    """Converts image to base64 string"""
    with open(image_path, "rb") as f:
        data = f.read()
    return base64.b64encode(data).decode()

def get_topbar_html():
    """Returns complete HTML for the top navigation bar"""
    return f"""
    <div class="top-bar">
        <div class="top-bar-content">
            <div class="top-bar-logo">
                <img src="data:image/png;base64,{image_to_base64("EFCC1.png")}" width="40" style="filter: drop-shadow(0 1px 2px rgba(0,0,0,0.2));">
            </div>
            <div class="top-bar-title">EFCC StaffSuite</div>
        </div>
    </div>
    <div class="main-content">
    """