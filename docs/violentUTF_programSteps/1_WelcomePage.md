# 1. The Welcome Page

## Display in GUI:
- **Page Header**: Title "🌊 Violent UTF - Welcome" with app icon
- **Introduction Text**: Description of Violent UTF as a user-friendly red teaming tool for non-technical stakeholders
- **Version Display**: Shows current app version (0.1)
- **Useful Links Section**: Links to documentation, tutorials, and PyRIT documentation
- **Parameter Loading Section**: Interface for loading configuration parameters
- **Database Management Section**: Database initialization and management controls
- **Start Button**: Primary button to proceed to Configure Generators workflow

## Authentication & Session Management:
- **User Authentication**: Integrated SSO authentication via handle_authentication_and_sidebar()
- **Session State Initialization**: Manages default_params, APP_DATA_DIR, user_name, db_initialized flags
- **Parameter Loading**: Automatic loading of default_parameters.yaml on first visit

## Parameter Configuration:
- **Default Parameters**: Automatically loads from `parameters/default_parameters.yaml`
- **Parameter File Selection**: Dropdown to select existing YAML files from parameters/ directory
- **File Upload**: Upload custom YAML parameter files with temporary storage
- **Parameter Validation**: YAML parsing with error handling and user feedback
- **Session Persistence**: Loaded parameters stored in session state for workflow continuity

## Database Management:
- **User-Specific Database**: Creates hashed database filenames based on username and PYRIT_DB_SALT
- **Database Path Generation**: Constructs paths using APP_DATA_DIR from configuration
- **PyRIT Memory Integration**: Initializes DuckDBMemory with CentralMemory singleton pattern
- **Database Creation**: Creates database file and schema if not exists
- **Connection Validation**: Verifies database connectivity and schema integrity
- **Reset Database**: ⚠️ Button to drop and recreate all PyRIT tables (with confirmation)
- **Display Statistics**: 📊 Button to show table row counts and database statistics

## User Actions Available:
1. **View Default Parameters**: Expandable section showing loaded configuration
2. **Select Parameter File**: Choose from existing YAML files in parameters/ folder
3. **Upload Parameter File**: Upload custom YAML configuration file
4. **Initialize Database**: Create or connect to user-specific PyRIT database
5. **Reset Database Tables**: Clear all conversation history and recreate schema
6. **View Table Statistics**: Display row counts for all database tables
7. **Start Configuration Workflow**: Navigate to Configure Generators page

## Prerequisites & Validation:
- **User Authentication**: Must be logged in to access database functions
- **APP_DATA_DIR**: Must be configured in default_parameters.yaml
- **PYRIT_DB_SALT**: Environment variable required for database security
- **Database Initialization**: Required before starting the workflow
- **Parameter File Format**: YAML files must contain valid dictionary structures

## Error Handling:
- **File Not Found**: Graceful handling of missing parameter files
- **YAML Parsing**: Error reporting for malformed YAML files
- **Database Errors**: Connection, permission, and initialization error handling
- **Authentication Issues**: User login validation and error display
- **Configuration Validation**: Missing APP_DATA_DIR and PYRIT_DB_SALT detection

## Backend Implementation:
- **Logging Integration**: Comprehensive logging via utils.logging module
- **Temporary File Management**: Secure handling of uploaded parameter files
- **Database Schema Management**: PyRIT table creation and maintenance
- **Session State Management**: Persistence of user configuration across page navigation
- **Security Considerations**: Salted database filenames and secure temporary file handling
