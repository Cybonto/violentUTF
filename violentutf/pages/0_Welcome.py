app_version = "0.1"
app_title = "Violent UTF - Welcome"
app_description = "Welcome to Violent UTF."
app_icon = ":wave:"

import streamlit as st
import os
import sys
import yaml
import pandas as pd
import tempfile
import shutil
import hashlib
import duckdb
from sqlalchemy.orm import Session # Import Session for stats query
from sqlalchemy.ext.declarative import DeclarativeMeta # Import for type checking models
# Import PyRIT memory components
import pyrit.memory
from pyrit.memory import CentralMemory, MemoryInterface, DuckDBMemory # Import specific classes
from typing import Optional, List
from dotenv import load_dotenv

# Use the centralized logging setup
from utils.logging import get_logger

logger = get_logger(__name__)

DEFAULT_PARAMS_FILE = "parameters/default_parameters.yaml"
load_dotenv()

# Initialize session state for parameters if not already done
if 'default_params' not in st.session_state:
    st.session_state.default_params = {}
if 'loaded_params_file' not in st.session_state:
    st.session_state.loaded_params_file = None
if 'APP_DATA_DIR' not in st.session_state:
    st.session_state.APP_DATA_DIR = None
if 'user_name' not in st.session_state:
    st.session_state.user_name = {}
# Initialize DB state flags
if 'db_initialized' not in st.session_state:
    st.session_state.db_initialized = False
if 'db_path' not in st.session_state:
    st.session_state.db_path = None


# --- Main Page Function ---
def main():
    """Renders the Welcome page content and handles parameter loading."""
    logger.debug("Welcome page config set.")
    st.set_page_config(
        page_title=app_title,
        page_icon=app_icon,
        layout="wide",
        initial_sidebar_state="expanded"
    )
    # --- Authentication and Sidebar ---
    handle_authentication_and_sidebar() # must be executed early to set st.session_state.user_name

    # --- Page Content ---
    display_header()
    display_introduction()
    display_links()

    # Load parameters only if not already loaded
    if not st.session_state.default_params:
        st.write(f"Loading default parameters from: `{DEFAULT_PARAMS_FILE}`")
        try:
            with open(DEFAULT_PARAMS_FILE, 'r') as f:
                default_params = yaml.safe_load(f)
                st.session_state.default_params = default_params
                st.session_state.loaded_params_file = DEFAULT_PARAMS_FILE
                # Extract APP_DATA_DIR
                app_data_dir_from_config = default_params.get("APP_DATA_DIR")
                if app_data_dir_from_config:
                    st.session_state.APP_DATA_DIR = app_data_dir_from_config
                    st.success(f"Successfully loaded parameters and found APP_DATA_DIR: `{app_data_dir_from_config}`.")
                    # logger.info(f"Loaded default parameters from {DEFAULT_PARAMS_FILE}")
                else:
                    st.error(f"Error: 'APP_DATA_DIR' key not found in {DEFAULT_PARAMS_FILE}.")
                    st.session_state.APP_DATA_DIR = None # Ensure it's None if not found

                # Display loaded parameters (optional)
                with st.expander("View Default Parameters"):
                    st.json(st.session_state.default_params)

        except FileNotFoundError:
            st.error(f"Error: Default parameters file not found at {DEFAULT_PARAMS_FILE}.")
            # logger.error(f"Default parameters file not found at {DEFAULT_PARAMS_FILE}")
            st.session_state.default_params = {}
            st.session_state.loaded_params_file = None
            st.session_state.APP_DATA_DIR = None
        except yaml.YAMLError as e:
            st.error(f"Error parsing YAML file {DEFAULT_PARAMS_FILE}: {e}")
            # logger.error(f"Error parsing YAML file {DEFAULT_PARAMS_FILE}: {e}", exc_info=True)
            st.session_state.default_params = {}
            st.session_state.loaded_params_file = None
            st.session_state.APP_DATA_DIR = None
        except Exception as e:
            st.error(f"An unexpected error occurred while loading parameters: {e}")
            # logger.error(f"Unexpected error loading parameters: {e}", exc_info=True)
            st.session_state.default_params = {}
            st.session_state.loaded_params_file = None
            st.session_state.APP_DATA_DIR = None
    else:
        st.info(f"Parameters already loaded from {st.session_state.loaded_params_file}.")
        if not st.session_state.get("APP_DATA_DIR"):
            st.warning("APP_DATA_DIR was not found in the previously loaded parameters. Database initialization might fail.")

    # --- Initialize Database ---
    st.header("Initialize Database")

    # Retrieve necessary config values
    app_data_dir = st.session_state.get("APP_DATA_DIR")
    pyrit_db_salt = os.getenv("PYRIT_DB_SALT") # Load from environment
    current_user = st.session_state.get('user_name', None) # Get current user

    # Proceed only if prerequisites are met
    if not current_user:
        st.warning("User not logged in. Please log in to initialize the database.")
    elif not app_data_dir:
        st.error("Application data directory (`APP_DATA_DIR`) is not configured. Cannot initialize database. Check `parameters/default_parameters.yaml`.")
    elif not pyrit_db_salt:
        st.error("Database salt (`PYRIT_DB_SALT`) is not set as an environment variable. Cannot initialize database.")
    else:
        # All prerequisites met, proceed with DB logic
        db_path = get_db_path(current_user, pyrit_db_salt, app_data_dir)
        st.write(f"Database file for user '{current_user}' will be at: `{db_path}`")

        # Check session state first - if already initialized for THIS user and path, show success
        if st.session_state.get('db_initialized', False) and st.session_state.get('db_path') == db_path:
            st.success(f"Database connection previously established for user '{current_user}' at `{db_path}`.")
            # Verify the central memory instance is still set (optional but good practice)
            try:
                 if not CentralMemory.get_memory_instance():
                      logger.warning("DB state shows initialized, but CentralMemory instance is None. Re-initializing.")
                      st.session_state['db_initialized'] = False # Force re-init
                      st.rerun() # Rerun to trigger re-initialization logic below
            except Exception as e:
                 logger.error(f"Error checking CentralMemory instance: {e}")
                 st.session_state['db_initialized'] = False # Assume error means re-init needed
                 st.rerun()

        else:
            # Reset initialization status if user or config changed implicitly
            if st.session_state.get('db_path') != db_path:
                logger.info(f"User or DB path changed. Resetting DB initialization status.")
                st.session_state['db_initialized'] = False
                st.session_state['db_path'] = None # Clear old path

            # Check if file exists and attempt initialization
            if os.path.exists(db_path):
                st.info("Existing database file found.")
                if initialize_database(db_path): # This now uses CentralMemory.set_memory_instance
                    st.success(f"Successfully connected to existing database for user '{current_user}'.")
                    # No rerun needed here, state is set internally
                else:
                    st.error("Could not connect to the existing database. Check logs or permissions.")
            else:
                st.warning("Database file not found for this user.")
                if st.button("Initialize Database Now"):
                    if initialize_database(db_path): # This now uses CentralMemory.set_memory_instance
                        st.success(f"Database initialized successfully for user '{current_user}' at `{db_path}`.")
                        st.rerun() # Rerun to update state cleanly after creation
                    # Error message handled within initialize_database

    if not st.session_state.get('db_initialized', False):
        st.info("Please ensure the database is initialized to proceed with configuration.")
    else:
        # --- ADDED: Database Management Buttons ---
        st.divider()
        st.subheader("Database Management")
        col1, col2 = st.columns(2)

        with col1:
            if st.button("⚠️ Reset Database Tables", key="reset_db_button", help="Drops and recreates all PyRIT tables. Conversation history will be lost!"):
                try:
                    memory = CentralMemory.get_memory_instance()
                    if memory:
                        logger.warning(f"User '{st.session_state.get('user_name', 'Unknown')}' initiated database reset.")
                        if 'confirm_reset' not in st.session_state:
                             st.session_state.confirm_reset = True
                             st.rerun()

                        if st.session_state.get('confirm_reset', False):
                             st.warning("Are you sure you want to reset the database? All conversation history will be lost.")
                             if st.button("Confirm Reset", key="confirm_reset_button"):
                                  with st.spinner("Resetting database tables..."):
                                       logger.info("Calling memory.reset_database()...") # <-- Added Log
                                       memory.reset_database()
                                       logger.info("memory.reset_database() call completed.") # <-- Added Log
                                  st.success("Database tables reset successfully.")
                                  logger.info("Database tables reset successfully.")
                                  del st.session_state['confirm_reset']
                                  st.rerun()
                             if st.button("Cancel Reset", key="cancel_reset_button"):
                                  del st.session_state['confirm_reset']
                                  st.rerun()

                    else:
                        st.error("Database is not initialized. Cannot reset.")
                        logger.error("Reset Database called but memory instance is None.")
                        if 'confirm_reset' in st.session_state: del st.session_state['confirm_reset']
                except Exception as e:
                    st.error(f"An error occurred while resetting the database: {e}")
                    logger.exception("Error during database reset.") # logger.exception includes traceback
                    if 'confirm_reset' in st.session_state: del st.session_state['confirm_reset']

            elif 'confirm_reset' in st.session_state:
                 pass


        with col2:
            if st.button("📊 Display Table Statistics", key="display_stats_button"):
                try:
                    memory = CentralMemory.get_memory_instance()
                    if memory and isinstance(memory, DuckDBMemory):
                        logger.info("Fetching database statistics.")
                        with st.spinner("Fetching table statistics..."):
                             logger.info("Calling memory.get_all_table_models()...") # <-- Added Log
                             table_models = memory.get_all_table_models()
                             logger.info(f"memory.get_all_table_models() returned: {table_models}") # <-- Added Log

                             stats_data = []
                             if table_models: # <-- Check if models were returned
                                 session: Session = memory.get_session()
                                 logger.info("Obtained database session.") # <-- Added Log
                                 try:
                                     for model in table_models:
                                        # Check for __tablename__ and __mapper__ instead of DeclarativeMeta
                                        if hasattr(model, '__tablename__') and hasattr(model, '__mapper__'):
                                            table_name = model.__tablename__
                                            logger.debug(f"Querying count for table: {table_name}") # <-- Added Log
                                            count = session.query(model).count()
                                            logger.debug(f"Count for {table_name}: {count}") # <-- Added Log
                                            stats_data.append({"Table Name": table_name, "Row Count": count})
                                        else:
                                            logger.warning(f"Skipping non-table model found: {model}")
                                 finally:
                                     session.close()
                                     logger.info("Database session closed.") # <-- Added Log
                             else:
                                 logger.warning("get_all_table_models() returned empty list or None.") # <-- Added Log

                             if stats_data:
                                 st.dataframe(pd.DataFrame(stats_data), use_container_width=True)
                                 logger.info("Successfully displayed table statistics.")
                             else:
                                 st.info("No tables found or unable to get statistics.") # Message unchanged but logs added
                                 logger.info("No table statistics to display.")
                    # ... (rest of the error handling) ...
                except Exception as e:
                    st.error(f"An error occurred while fetching statistics: {e}")
                    logger.exception("Error during statistics display.") # logger.exception includes traceback
        # --- END ADDED: Database Management Buttons ---

    # Parameter file loading section
    parameter_file_path = display_parameter_loader()

    # Load selected/uploaded parameters into session state
    parameters_loaded = False
    if parameter_file_path:
        success = load_parameters_to_state(parameter_file_path)
        parameters_loaded = success
        if not success:
            st.error("Failed to load parameters from the selected/uploaded file.")
        # Clean up temporary uploaded file if it exists
        if 'uploaded_temp_file_path' in st.session_state and st.session_state['uploaded_temp_file_path'] == parameter_file_path:
             try:
                 os.remove(parameter_file_path)
                 logger.info(f"Removed temporary uploaded file: {parameter_file_path}")
                 del st.session_state['uploaded_temp_file_path'] # Clear the state var
             except OSError as e:
                 logger.error(f"Error removing temporary file {parameter_file_path}: {e}")

    elif 'default_parameters_used' not in st.session_state:
         # Only show warning once if no file is loaded initially
         st.warning("No parameter file loaded. Default settings will be used where applicable.")
         st.session_state['default_parameters_used'] = True # Flag that default path was taken

    # --- Start Button ---
    st.divider()
    # Disable button if DB is not initialized
    start_disabled = not st.session_state.get('db_initialized', False)
    if st.button("Start Configuration Workflow", type="primary", disabled=start_disabled):
        st.session_state['started'] = True # Optional flag if needed later
        logger.info(f"User '{st.user.name or 'User'}' clicked 'Start'. Navigating to Configure Generators.")
        st.switch_page("pages/2_ConfigureGenerators.py")
    elif start_disabled:
         st.warning("Database must be initialized before starting the workflow.")


# --- Helper Functions ---

def handle_authentication_and_sidebar():
    """Checks user login status and displays sidebar elements."""
    # Initialize session state for login tracking if not present
    if 'previously_logged_in' not in st.session_state:
        st.session_state['previously_logged_in'] = False

    user_logged_in = st.user.is_logged_in

    # Check if login state has changed since last run
    if user_logged_in != st.session_state['previously_logged_in']:
        st.session_state['previously_logged_in'] = user_logged_in
        user_identifier = st.user.name or st.user.email or 'Unknown User'
        log_action = "logged in" if user_logged_in else "logged out"
        logger.info(f"User {log_action}: {user_identifier}")
        # If user just logged out, clear the username state
        if not user_logged_in:
            st.session_state['user_name'] = None
            st.session_state['db_initialized'] = False # Reset DB status on logout
            st.session_state['db_path'] = None

    # If user is not logged in, display login prompt and stop execution
    if not user_logged_in:
        st.title("Please Log In")
        st.info("You need to log in to access Violent UTF.")
        # Assuming 'keycloak' is the configured provider name in secrets.toml
        try:
            # Attempt to use the configured provider (e.g., 'keycloak')
            #provider = list(st.secrets.get('auth', {}).get('providers', {}).keys())[0]
            #st.login(provider)
            st.login("keycloak")
        except (IndexError, KeyError, Exception) as e:
            logger.error(f"Login provider issue or not configured: {e}")
            st.login() # Fallback to default login
        st.stop() # Stop script execution for non-logged-in users
    else:
        # If user is logged in, display sidebar greeting and logout button
        with st.sidebar:
            user_name = st.user.name or st.user.email or 'User'
            # Update user_name in session state ONLY if it changed or wasn't set
            if st.session_state.get('user_name') != user_name:
                 st.session_state['user_name'] = user_name
                 # If username changes, DB needs re-initialization
                 st.session_state['db_initialized'] = False
                 st.session_state['db_path'] = None
                 logger.info(f"User changed or logged in: {user_name}. Resetting DB state.")

            st.success(f"Hello, {user_name}!")
            st.divider()
            if st.button("Logout", key="sidebar_logout_welcome"):
                # Log out action
                st.session_state['previously_logged_in'] = False # Update state before logout call
                logger.info(f"User '{user_name}' clicked logout.")
                st.session_state['user_name'] = None # Clear username
                st.session_state['db_initialized'] = False # Reset DB status
                st.session_state['db_path'] = None
                st.logout()

def get_db_filename(username: str, salt: str) -> str:
    """Generates a database filename based on a salted hash of the username."""
    if not username or not salt:
        return ""
    # Ensure salt is bytes
    salt_bytes = salt.encode('utf-8') if isinstance(salt, str) else salt
    hashed_username = hashlib.sha256(salt_bytes + username.encode('utf-8')).hexdigest()
    return f"pyrit_memory_{hashed_username}.db"

def get_db_path(username: str, salt: str, app_data_dir: str) -> str:
    """Constructs the full path for the user's database file."""
    if not app_data_dir:
        return ""
    filename = get_db_filename(username, salt)
    if not filename:
        return ""
    return os.path.join(app_data_dir, filename)


# --- MODIFIED: initialize_database function ---
def initialize_database(db_path: str) -> bool:
    """
    Initializes PyRIT memory with DuckDB at the specified path using CentralMemory,
    explicitly ensuring the database file exists and the schema is created.

    Args:
        db_path: The full path to the DuckDB database file.

    Returns:
        True if initialization was successful, False otherwise.
    """
    if not db_path:
        st.error("Database path cannot be empty (check APP_DATA_DIR in config).")
        logger.error("initialize_database called with empty db_path.")
        return False
    try:
        # Ensure the target directory exists
        db_dir = os.path.dirname(db_path)
        if not os.path.exists(db_dir):
            logger.info(f"Creating database directory: {db_dir}")
            os.makedirs(db_dir, exist_ok=True)
        else:
             logger.debug(f"Database directory already exists: {db_dir}")

        # --- ADDED: Explicitly ensure database FILE exists ---
        try:
            logger.info(f"Explicitly connecting to DuckDB path to ensure file exists: {db_path}")
            con = duckdb.connect(db_path)
            # We can execute a simple command to ensure connection works, though connect() often suffices
            con.execute("SELECT 42;")
            con.close()
            logger.info(f"DuckDB file check/creation successful for: {db_path}")
            if not os.path.exists(db_path):
                 # This shouldn't happen if duckdb.connect succeeded without error
                 logger.error(f"CRITICAL: duckdb.connect succeeded but file still doesn't exist at {db_path}")
                 st.error("Failed to physically create the database file, check permissions or disk space.")
                 return False
        except Exception as db_connect_error:
            logger.exception(f"Error explicitly connecting to DuckDB file {db_path}.")
            st.error(f"Failed to create or connect to the database file: {db_connect_error}")
            st.session_state['db_initialized'] = False
            st.session_state['db_path'] = None
            return False
        # --- END ADDED STEP ---

        # Now, instantiate PyRIT's memory interface for the existing file
        logger.info(f"Attempting to initialize PyRIT's DuckDBMemory wrapper for path: {db_path}")
        memory_interface = DuckDBMemory(db_path=db_path)

        # Ensure schema exists within the file
        try:
             logger.info("Ensuring database schema exists within the file using reset_database()...")
             memory_interface.reset_database()
             logger.info("Database schema check/creation step completed.")
        except Exception as schema_error:
             logger.exception("Error during explicit schema creation (reset_database).")
             st.error(f"Failed to create database schema within the file: {schema_error}")
             st.session_state['db_initialized'] = False
             st.session_state['db_path'] = None
             # Attempt to dispose if engine exists
             try: memory_interface.dispose_engine()
             except Exception: pass
             return False

        # Set the instance in CentralMemory
        logger.info("Setting the created DuckDBMemory instance using CentralMemory.set_memory_instance()")
        CentralMemory.set_memory_instance(memory_interface)

        # Optional: Verify the interface was set
        retrieved_instance = CentralMemory.get_memory_instance()
        if retrieved_instance is memory_interface:
            logger.debug("Successfully verified that CentralMemory instance was set.")
        else:
            logger.error("Verification failed: CentralMemory.get_memory_instance() did not return the expected instance.")
            st.error("Internal Error: Failed to set the central memory instance correctly.")
            st.session_state['db_initialized'] = False
            st.session_state['db_path'] = None
            return False

        # Update session state on success
        st.session_state['db_path'] = db_path
        st.session_state['db_initialized'] = True
        logger.info(f"PyRIT Central Memory interface set to DuckDB at: {db_path}")
        return True

    except ImportError as imp_err:
        # Separate check for duckdb import error
        if 'duckdb' in str(imp_err):
             st.error("Failed to import the 'duckdb' library. Please ensure it's installed (`pip install duckdb`).")
             logger.exception("ImportError for duckdb library.")
        else:
             st.error("Failed to import PyRIT memory components. Is PyRIT installed correctly?")
             logger.exception("ImportError during database initialization (PyRIT).")
        st.session_state['db_initialized'] = False
        st.session_state['db_path'] = None
        return False
    except Exception as e:
        st.error(f"An unexpected error occurred during database initialization at {db_path}: {e}")
        logger.exception(f"Failed to initialize database at {db_path}: {e}")
        st.session_state['db_initialized'] = False
        st.session_state['db_path'] = None
        return False
# --- END MODIFIED FUNCTION ---

def display_header():
    """Displays the main page header."""
    st.title(f"{app_icon} {app_title}")

def display_introduction():
    """Displays the introductory text."""
    # Consider moving this to a separate Markdown file if it gets long
    st.write("""
    Violent UTF is a user-friendly red teaming tool that empowers domain experts, ethicists, legal professionals, and other non-technical stakeholders to actively engage in red teaming activities of Generative AI systems without requiring programming skills. Please use the tools wisely.
    """)
    st.write(f"Version: {app_version}")

def display_links():
    """Displays useful links (placeholders currently)."""
    # Update these links to actual URLs when available
    st.markdown("""
    ---
    **Useful Links:**

    * [Violent UTF Documentation](https://example.com/documentation)
    * [Tutorials](https://example.com/tutorials)
    * [PyRIT Documentation](https://github.com/Azure/PyRIT)
    """)

def display_parameter_loader() -> Optional[str]:
    """
    Displays widgets for selecting or uploading a parameter file.

    Returns:
        The validated path to the selected or uploaded parameter file, or None.
    """
    st.divider()
    st.subheader("Load Configuration Parameters (Optional)")
    st.caption("You can load parameters for generators, datasets, etc., from a YAML file.")

    parameter_file_path: Optional[str] = None
    parameter_dir = "parameters"
    available_files: List[str] = []

    # List files in the 'parameters' directory
    try:
        if os.path.exists(parameter_dir) and os.path.isdir(parameter_dir):
            available_files = sorted([
                f for f in os.listdir(parameter_dir)
                if f.endswith(('.yaml', '.yml')) and os.path.isfile(os.path.join(parameter_dir, f))
            ])
    except OSError as e:
        st.warning(f"Could not access parameter directory '{parameter_dir}': {e}")
        logger.warning(f"OSError accessing parameter directory '{parameter_dir}': {e}")

    # Selectbox for existing files
    if available_files:
        selected_file = st.selectbox(
            "Select an existing parameter file:",
            options=["-- Select --"] + available_files,
            index=0,
            key="param_select"
        )
        if selected_file and selected_file != "-- Select --":
            parameter_file_path = os.path.join(parameter_dir, selected_file)
            logger.info(f"User selected existing parameter file: {parameter_file_path}")
    else:
        st.info("No parameter files found in the 'parameters' folder.")

    st.markdown("<p style='text-align: center; margin-top: 1em; margin-bottom: 1em;'>OR</p>", unsafe_allow_html=True)

    # File uploader
    uploaded_file = st.file_uploader(
        "Upload a parameter file:",
        type=['yaml', 'yml'],
        key="param_upload"
    )
    if uploaded_file is not None:
        logger.info(f"User uploaded parameter file: {uploaded_file.name}")
        # Save uploaded file temporarily and return its path
        parameter_file_path = save_uploaded_file_temporarily(uploaded_file)
        if parameter_file_path:
             # Store temp path in session state ONLY if successfully saved
             st.session_state['uploaded_temp_file_path'] = parameter_file_path
        else:
             # Clear any previously selected path if upload save failed
             parameter_file_path = None


    if parameter_file_path:
         logger.debug(f"Parameter loader returning path: {parameter_file_path}")
    else:
         logger.debug("Parameter loader returning None.")

    return parameter_file_path


def save_uploaded_file_temporarily(uploaded_file) -> Optional[str]:
    """
    Saves the uploaded file to a temporary location.

    Returns:
        The path to the temporary file, or None if saving fails.
    """
    temp_file_path = None
    try:
        # Use mkstemp for secure temporary file creation
        fd, temp_file_path = tempfile.mkstemp(suffix=".yaml", prefix="uploaded_params_")
        logger.info(f"Created temporary file: {temp_file_path}")
        with os.fdopen(fd, 'wb') as tmp_file:
            # Copy buffer efficiently
            shutil.copyfileobj(uploaded_file, tmp_file)
        logger.info(f"Saved uploaded file '{uploaded_file.name}' to temporary path: {temp_file_path}")
        return temp_file_path
    except Exception as e:
        st.error(f"Error saving uploaded file temporarily: {e}")
        logger.exception(f"Error saving uploaded file '{uploaded_file.name}' temporarily.")
        # Clean up partially created file if it exists
        if temp_file_path and os.path.exists(temp_file_path):
             try:
                 os.remove(temp_file_path)
             except OSError:
                 pass
        return None


def load_parameters_to_state(parameter_file_path: str) -> bool:
    """
    Loads parameters from the specified YAML file into st.session_state.

    Parameters:
        parameter_file_path: The path to the YAML parameter file.

    Returns:
        True if loading and parsing were successful, False otherwise.
    """
    try:
        with open(parameter_file_path, 'r', encoding='utf-8') as f:
            params = yaml.safe_load(f)

        if not isinstance(params, dict):
            st.error(f"Invalid format: Parameter file '{os.path.basename(parameter_file_path)}' must contain a YAML dictionary (key-value pairs).")
            logger.error(f"Parameter file '{parameter_file_path}' does not contain a dictionary.")
            return False

        # Clear potentially conflicting previous state keys? (Optional, depends on desired behavior)
        # Example: Clear keys related to generators if loading a file that defines them
        # keys_to_clear = ['generators', 'datasets', ...]
        # for key in keys_to_clear:
        #     if key in st.session_state:
        #         del st.session_state[key]

        # Update session state with loaded parameters
        st.session_state.update(params)
        # Store the path of the loaded file for reference
        st.session_state['parameter_file_loaded_path'] = parameter_file_path
        # Reset default usage flag
        if 'default_parameters_used' in st.session_state:
            del st.session_state['default_parameters_used']

        st.success(f"Parameters loaded successfully from: {os.path.basename(parameter_file_path)}")
        user_identifier = st.user.name or st.user.email or 'User'
        logger.info(f"User '{user_identifier}' loaded parameters from '{parameter_file_path}' into session state.")
        # Log loaded keys for debugging (optional)
        logger.debug(f"Loaded parameter keys into session state: {list(params.keys())}")
        return True

    except FileNotFoundError:
        st.error(f"Parameter file not found: {parameter_file_path}")
        logger.error(f"FileNotFoundError loading parameters: {parameter_file_path}")
        return False
    except yaml.YAMLError as e:
        st.error(f"Error parsing YAML file '{os.path.basename(parameter_file_path)}': {e}")
        logger.error(f"YAMLError parsing {parameter_file_path}: {e}", exc_info=True)
        return False
    except Exception as e:
        st.error(f"An unexpected error occurred while loading parameters: {e}")
        logger.exception(f"Unexpected error loading parameters from {parameter_file_path}.")
        return False

# --- Run the app ---
if __name__ == "__main__":
    logger.info(f"Executing {os.path.basename(__file__)}")
    main()

