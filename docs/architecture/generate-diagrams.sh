#!/bin/bash

# ViolentUTF Architecture Diagram Generation Script
# This script generates all PlantUML diagrams in the architecture documentation

set -e

# Configuration
PLANTUML_JAR="plantuml.jar"
PLANTUML_URL="https://github.com/plantuml/plantuml/releases/latest/download/plantuml.jar"
DOCS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUTPUT_DIR="${DOCS_DIR}/generated"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if PlantUML is available
check_plantuml() {
    if command -v plantuml &> /dev/null; then
        log_info "Using system PlantUML installation"
        PLANTUML_CMD="plantuml"
    elif [ -f "$PLANTUML_JAR" ]; then
        log_info "Using local PlantUML JAR: $PLANTUML_JAR"
        PLANTUML_CMD="java -jar $PLANTUML_JAR"
    else
        log_warning "PlantUML not found. Downloading..."
        download_plantuml
    fi
}

# Download PlantUML JAR
download_plantuml() {
    if command -v curl &> /dev/null; then
        curl -L -o "$PLANTUML_JAR" "$PLANTUML_URL"
    elif command -v wget &> /dev/null; then
        wget -O "$PLANTUML_JAR" "$PLANTUML_URL"
    else
        log_error "Neither curl nor wget found. Please install PlantUML manually."
        exit 1
    fi

    if [ -f "$PLANTUML_JAR" ]; then
        log_success "PlantUML downloaded successfully"
        PLANTUML_CMD="java -jar $PLANTUML_JAR"
    else
        log_error "Failed to download PlantUML"
        exit 1
    fi
}

# Create output directory
create_output_dir() {
    mkdir -p "$OUTPUT_DIR"/{c4-model,data-flows,component-diagrams,code-diagrams}
    log_info "Created output directories in $OUTPUT_DIR"
}

# Generate diagram from PlantUML file
generate_diagram() {
    local puml_file="$1"
    local output_dir="$2"
    local filename=$(basename "$puml_file" .puml)

    log_info "Generating diagram: $filename"

    # Generate PNG
    $PLANTUML_CMD -tpng -o "$output_dir" "$puml_file"

    # Generate SVG for web viewing
    $PLANTUML_CMD -tsvg -o "$output_dir" "$puml_file"

    # Generate PDF for documentation
    if command -v java &> /dev/null; then
        $PLANTUML_CMD -tpdf -o "$output_dir" "$puml_file" 2>/dev/null || log_warning "PDF generation failed for $filename"
    fi

    log_success "Generated: $filename"
}

# Generate all C4 model diagrams
generate_c4_diagrams() {
    log_info "Generating C4 Model diagrams..."

    local c4_dir="${DOCS_DIR}/c4-model"
    local output_dir="${OUTPUT_DIR}/c4-model"

    if [ -d "$c4_dir" ]; then
        for puml_file in "$c4_dir"/*.puml; do
            if [ -f "$puml_file" ]; then
                generate_diagram "$puml_file" "$output_dir"
            fi
        done
    else
        log_warning "C4 model directory not found: $c4_dir"
    fi
}

# Generate all data flow diagrams
generate_dataflow_diagrams() {
    log_info "Generating Data Flow diagrams..."

    local dataflow_dir="${DOCS_DIR}/data-flows"
    local output_dir="${OUTPUT_DIR}/data-flows"

    if [ -d "$dataflow_dir" ]; then
        for puml_file in "$dataflow_dir"/*.puml; do
            if [ -f "$puml_file" ]; then
                generate_diagram "$puml_file" "$output_dir"
            fi
        done
    else
        log_warning "Data flows directory not found: $dataflow_dir"
    fi
}

# Generate component diagrams
generate_component_diagrams() {
    log_info "Generating Component diagrams..."

    local component_dir="${DOCS_DIR}/component-diagrams"
    local output_dir="${OUTPUT_DIR}/component-diagrams"

    if [ -d "$component_dir" ]; then
        for puml_file in "$component_dir"/*.puml; do
            if [ -f "$puml_file" ]; then
                generate_diagram "$puml_file" "$output_dir"
            fi
        done
    else
        log_warning "Component diagrams directory not found: $component_dir"
    fi
}

# Generate README with diagram links
generate_readme() {
    local readme_file="${OUTPUT_DIR}/README.md"

    log_info "Generating README with diagram links..."

    cat > "$readme_file" << 'EOF'
# ViolentUTF Architecture Diagrams

This directory contains auto-generated architecture diagrams for the ViolentUTF platform.

**⚠️ Warning**: This directory is auto-generated. Do not edit files directly.
To update diagrams, modify the source `.puml` files and run `generate-diagrams.sh`.

## C4 Model Diagrams

### System Context
![System Context](c4-model/system-context.svg)
- [PNG](c4-model/system-context.png) | [SVG](c4-model/system-context.svg) | [PDF](c4-model/system-context.pdf)

### Container Diagram
![Container Diagram](c4-model/container-diagram.svg)
- [PNG](c4-model/container-diagram.png) | [SVG](c4-model/container-diagram.svg) | [PDF](c4-model/container-diagram.pdf)

### Component Diagrams
![FastAPI Components](c4-model/fastapi-component-diagram.svg)
- [PNG](c4-model/fastapi-component-diagram.png) | [SVG](c4-model/fastapi-component-diagram.svg) | [PDF](c4-model/fastapi-component-diagram.pdf)

![MCP Components](c4-model/mcp-component-diagram.svg)
- [PNG](c4-model/mcp-component-diagram.png) | [SVG](c4-model/mcp-component-diagram.svg) | [PDF](c4-model/mcp-component-diagram.pdf)

## Data Flow Diagrams

### Authentication Flow
![Authentication Flow](data-flows/authentication-flow.svg)
- [PNG](data-flows/authentication-flow.png) | [SVG](data-flows/authentication-flow.svg) | [PDF](data-flows/authentication-flow.pdf)

### API Data Flow
![API Data Flow](data-flows/api-data-flow.svg)
- [PNG](data-flows/api-data-flow.png) | [SVG](data-flows/api-data-flow.svg) | [PDF](data-flows/api-data-flow.pdf)

### MCP Integration Flow
![MCP Integration](data-flows/mcp-integration-flow.svg)
- [PNG](data-flows/mcp-integration-flow.png) | [SVG](data-flows/mcp-integration-flow.svg) | [PDF](data-flows/mcp-integration-flow.pdf)

## Component Interaction Maps

### Database Interaction Map
![Database Interactions](component-diagrams/database-interaction-map.svg)
- [PNG](component-diagrams/database-interaction-map.png) | [SVG](component-diagrams/database-interaction-map.svg) | [PDF](component-diagrams/database-interaction-map.pdf)

## Generation Information

EOF

    echo "- **Generated**: $(date)" >> "$readme_file"
    echo "- **PlantUML Version**: $($PLANTUML_CMD -version 2>/dev/null | head -1 || echo 'Unknown')" >> "$readme_file"
    echo "- **Source**: [Architecture Documentation](../)" >> "$readme_file"
    echo "" >> "$readme_file"
    echo "## Regenerating Diagrams" >> "$readme_file"
    echo "" >> "$readme_file"
    echo '```bash' >> "$readme_file"
    echo "cd docs/architecture" >> "$readme_file"
    echo "./generate-diagrams.sh" >> "$readme_file"
    echo '```' >> "$readme_file"

    log_success "Generated README: $readme_file"
}

# Validate generated files
validate_output() {
    log_info "Validating generated files..."

    local file_count=0
    for format in png svg pdf; do
        local count=$(find "$OUTPUT_DIR" -name "*.$format" | wc -l)
        file_count=$((file_count + count))
        log_info "Found $count $format files"
    done

    if [ $file_count -gt 0 ]; then
        log_success "Validation complete: $file_count diagram files generated"
    else
        log_warning "No diagram files found - check for errors"
    fi
}

# Generate index HTML file for web viewing
generate_html_index() {
    local html_file="${OUTPUT_DIR}/index.html"

    log_info "Generating HTML index for web viewing..."

    cat > "$html_file" << 'EOF'
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ViolentUTF Architecture Diagrams</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; }
        .diagram-section { margin: 30px 0; }
        .diagram-links { margin: 10px 0; }
        .diagram-links a { margin-right: 15px; }
        img { max-width: 100%; height: auto; border: 1px solid #ddd; margin: 10px 0; }
        .warning { background-color: #fff3cd; border: 1px solid #ffeaa7; padding: 10px; border-radius: 5px; margin: 20px 0; }
    </style>
</head>
<body>
    <h1>ViolentUTF Architecture Diagrams</h1>

    <div class="warning">
        <strong>⚠️ Warning:</strong> This directory is auto-generated.
        To update diagrams, modify the source <code>.puml</code> files and run <code>generate-diagrams.sh</code>.
    </div>

    <h2>C4 Model Diagrams</h2>

    <div class="diagram-section">
        <h3>System Context</h3>
        <div class="diagram-links">
            <a href="c4-model/system-context.png">PNG</a>
            <a href="c4-model/system-context.svg">SVG</a>
            <a href="c4-model/system-context.pdf">PDF</a>
        </div>
        <img src="c4-model/system-context.svg" alt="System Context Diagram">
    </div>

    <div class="diagram-section">
        <h3>Container Diagram</h3>
        <div class="diagram-links">
            <a href="c4-model/container-diagram.png">PNG</a>
            <a href="c4-model/container-diagram.svg">SVG</a>
            <a href="c4-model/container-diagram.pdf">PDF</a>
        </div>
        <img src="c4-model/container-diagram.svg" alt="Container Diagram">
    </div>

    <h2>Data Flow Diagrams</h2>

    <div class="diagram-section">
        <h3>Authentication Flow</h3>
        <div class="diagram-links">
            <a href="data-flows/authentication-flow.png">PNG</a>
            <a href="data-flows/authentication-flow.svg">SVG</a>
            <a href="data-flows/authentication-flow.pdf">PDF</a>
        </div>
        <img src="data-flows/authentication-flow.svg" alt="Authentication Flow">
    </div>

    <div class="diagram-section">
        <h3>Database Interaction Map</h3>
        <div class="diagram-links">
            <a href="component-diagrams/database-interaction-map.png">PNG</a>
            <a href="component-diagrams/database-interaction-map.svg">SVG</a>
            <a href="component-diagrams/database-interaction-map.pdf">PDF</a>
        </div>
        <img src="component-diagrams/database-interaction-map.svg" alt="Database Interaction Map">
    </div>

    <hr>
    <p><small>Generated on: <span id="timestamp"></span></small></p>
    <script>
        document.getElementById('timestamp').textContent = new Date().toLocaleString();
    </script>
</body>
</html>
EOF

    log_success "Generated HTML index: $html_file"
}

# Main execution
main() {
    log_info "ViolentUTF Architecture Diagram Generation"
    log_info "==========================================="

    # Change to script directory
    cd "$DOCS_DIR"

    # Setup
    check_plantuml
    create_output_dir

    # Generate diagrams
    generate_c4_diagrams
    generate_dataflow_diagrams
    generate_component_diagrams

    # Generate documentation
    generate_readme
    generate_html_index

    # Validate
    validate_output

    log_success "Diagram generation complete!"
    log_info "View diagrams at: file://$OUTPUT_DIR/index.html"
}

# Error handling
trap 'log_error "Script failed at line $LINENO"' ERR

# Run main function
main "$@"
