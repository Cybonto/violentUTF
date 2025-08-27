#!/Home.py

import logging  # Import base logging for potential direct use if needed
import os

import streamlit as st

# Load environment variables from .env file
# Load environment variables from .env file
from dotenv import load_dotenv
from utils.logging import get_logger, setup_logging

app_version = "0.1"
app_title = "ViolentUTF - Home"
app_description = "Welcome Red-teamers to Vi-Tuff! Please use the tools wisely."
app_icon = "	:house:"

load_dotenv()

# Get a logger for this specific file (Home.py)
logger = get_logger(__name__)

# Have to call Streamlit page config before anything else
st.set_page_config(page_title=app_title, page_icon=app_icon, layout="wide", initial_sidebar_state="collapsed")

# --- Setup Logging (Call this ONCE per session) ---
# Ensure this block runs before any other code that might log,
# and definitely before any other Streamlit elements are rendered.
if "logging_setup_done" not in st.session_state:
    try:
        # You can adjust the desired log levels here if needed
        setup_logging(log_level=logging.DEBUG, console_level=logging.INFO)
        st.session_state["logging_setup_done"] = True
        # Log that setup is complete (using the logger from the logging module itself)
        logging.getLogger("utils.logging").info("Central logging setup completed for Streamlit session.")
    except Exception as e:
        # Display error in Streamlit if setup fails critically
        st.error(f"CRITICAL ERROR: Failed to initialize application logging: {e}")
        # Optionally stop the app if logging is essential
        st.stop()
# --- End Setup Logging ---

# Hide the default Streamlit menu and footer, and remove the default sidebar navigation
st.markdown(
    """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    [data-testid="collapsedControl"] {display: none;}
    [data-testid="stSidebarNav"] {display: none;}

    </style>
    """,
    unsafe_allow_html=True,
)

# CSS to position the logout button at the bottom of the sidebar
st.markdown(
    """
    <style>
    [data-testid="stSidebar"] > div:first-child {
        display: flex;
        flex-direction: column;
    }
    [data-testid="stSidebar"] button {
        margin-top: auto;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Global button styling to ensure proper contrast
st.markdown(
    """
    <style>
    /* Ensure primary buttons have proper contrast */
    .stButton > button[kind="primary"] {
        background-color: #1f77b4 !important;
        color: white !important;
        border: 1px solid #1f77b4 !important;
    }
    .stButton > button[kind="primary"]:hover {
        background-color: #1565c0 !important;
        border-color: #1565c0 !important;
    }
    .stButton > button[kind="primary"]:disabled {
        background-color: #cccccc !important;
        color: #666666 !important;
        border-color: #cccccc !important;
    }

    /* Ensure secondary buttons have proper contrast */
    .stButton > button[kind="secondary"] {
        background-color: #f8f9fa !important;
        color: #212529 !important;
        border: 1px solid #dee2e6 !important;
    }
    .stButton > button[kind="secondary"]:hover {
        background-color: #e9ecef !important;
        color: #212529 !important;
        border-color: #adb5bd !important;
    }
    .stButton > button[kind="secondary"]:disabled {
        background-color: #f8f9fa !important;
        color: #6c757d !important;
        border-color: #dee2e6 !important;
    }

    /* Default button styling for better contrast */
    .stButton > button {
        background-color: #f8f9fa !important;
        color: #212529 !important;
        border: 1px solid #dee2e6 !important;
    }
    .stButton > button:hover {
        background-color: #e9ecef !important;
        color: #212529 !important;
        border-color: #adb5bd !important;
    }

    /* Form submit buttons */
    .stFormSubmitButton > button {
        background-color: #1f77b4 !important;
        color: white !important;
        border: 1px solid #1f77b4 !important;
    }
    .stFormSubmitButton > button:hover {
        background-color: #1565c0 !important;
        border-color: #1565c0 !important;
    }
    .stFormSubmitButton > button:disabled {
        background-color: #cccccc !important;
        color: #666666 !important;
        border-color: #cccccc !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Streamlit application code
st.title(app_title)
st.write(app_description)
st.text("")


# Function to extract variables from page files
def extract_variables(file_path) -> dict:
    variables = {}
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith("app_version"):
                variables["app_version"] = line.split("=", 1)[1].strip().strip("'\"")
            elif line.startswith("app_title"):
                variables["app_title"] = line.split("=", 1)[1].strip().strip("'\"")
            elif line.startswith("app_description"):
                variables["app_description"] = line.split("=", 1)[1].strip().strip("'\"")
            elif line.startswith("app_icon"):
                variables["app_icon"] = line.split("=", 1)[1].strip().strip("'\"")
            if len(variables) == 4:
                break
    return variables


# Directory containing the page files
pages_dir = "pages"
page_files = [f for f in os.listdir(pages_dir) if f.endswith(".py") and f != "__init__.py"]

# Sort page_files to ensure consistent order
# page_files.sort()

# Define the number of tiles per row
tiles_per_row = 2
cols = st.columns(tiles_per_row)

for idx, file_name in enumerate(page_files):
    file_path = os.path.join(pages_dir, file_name)
    variables = extract_variables(file_path)
    if len(variables) > 3:
        page_name = os.path.splitext(file_name)[0]
        app_icon = variables.get("app_icon", "")
        app_title = variables.get("app_title", "")
        app_version = variables.get("app_version", "")
        app_description = variables.get("app_description", "")

        # Use the emoji short code directly in the button label
        icon = f"{app_icon} " if app_icon else ""
        button_label = f"""{icon}\n**{app_title}** (v. {app_version})\n
        {app_description}"""

        with cols[idx % tiles_per_row]:
            if st.button(button_label, key=page_name):
                st.switch_page(f"pages/{file_name}")
