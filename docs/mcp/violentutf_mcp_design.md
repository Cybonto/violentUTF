# ViolentUTF Model Context Protocol Server Design Document

> **Document Type**: Design Specification & Implementation Guide
> **Status**: PLANNED - Not Yet Implemented
> **Last Updated**: January 2025

## ⚠️ Important Notice

This document describes the **planned design** for ViolentUTF's Model Context Protocol (MCP) server. The MCP functionality is not currently implemented in the codebase. This specification serves as a blueprint for future development.

## Table of Contents

1. [Introduction & System Overview](#1-introduction--system-overview)
2. [Current State Analysis](#2-current-state-analysis)
3. [Implementation Roadmap](#3-implementation-roadmap)
4. [System Architecture](#4-system-architecture)
5. [MCP Primitives Design](#5-mcp-primitives-design)
6. [API Integration Architecture](#6-api-integration-architecture)
7. [Security Architecture](#7-security-architecture)
8. [Operational Considerations](#8-operational-considerations)
9. [Future-Proofing Strategy](#9-future-proofing-strategy)
10. [Appendices](#10-appendices)

---

## 1. Introduction & System Overview

### 1.1 Purpose
This document defines ViolentUTF's MCP Server which acts as a critical bridge, enabling LLMs to perform sophisticated AI red-teaming tasks through a secure, standardized interface connecting to the ViolentUTF's platform. The ViolentUTF MCP Server addresses the "MxN" integration problem, eliminating the need for custom integrations between each AI model and various security tool.

### 1.2 Goals and Objectives

#### 1.2.1 Primary Goals
- **Enable AI-Driven Security Testing**: Provide LLMs with direct access to enterprise-grade security testing capabilities through MCP
- **Standardize Security Tool Access**: Create a unified interface for AI models to interact with PyRIT, Garak, and other security tools
- **Enhance Red-teaming Workflows**: Support agentic AI security testing through standardized MCP interface integration

#### 1.2.2 Specific Objectives
- **Objective 1**: Expose ViolentUTF Tools with comprehensive parameter validation
- **Objective 2**: Provide security datasets, test results, and vulnerability reports as MCP Resources
- **Objective 3**: Offer guided red-teaming workflows and analysis templates through MCP Prompts
- **Objective 4**: Support agentic AI security testing via MCP Sampling with safety constraints
- **Objective 5**: Implement zero-configuration setup for existing ViolentUTF API endpoints
- **Objective 6**: Maintain full backward compatibility with existing ViolentUTF workflows

#### 1.2.3 Success Metrics
- **95%+ API coverage**: Expose 95% of ViolentUTF API functionality via MCP primitives
- **Sub-second response times**: Tool invocation latency under 1 second for 95% of operations
- **Zero security incidents**: No unauthorized access or privilege escalation through MCP interface
- **100% audit compliance**: Complete audit trail for all AI-initiated security testing activities

### 1.3 Scope

#### 1.3.1 In Scope
**Core MCP Functionality:**
- Complete ViolentUTF API exposure via FastAPI-MCP integration
- Real-time security test execution and monitoring
- Dynamic security dataset management and caching
- Comprehensive authentication and authorization via Keycloak/APISIX
- Multi-transport support (stdio, HTTP/SSE)

**Security Testing Integration:**
- PyRIT orchestrator lifecycle management (create, start, stop, monitor)
- Garak vulnerability scanner integration and result processing
- Custom security tool plugin architecture
- Attack vector generation and validation
- Vulnerability assessment and reporting automation

**Data Management:**
- Security dataset versioning and access control
- Test result aggregation and analysis
- Real-time progress tracking and notifications
- Robust audit logging and compliance reporting

#### 1.3.2 Out of Scope
**Explicitly Excluded:**
- Direct model inference or hosting (delegated to MCP clients)
- Keycloak user provisioning and identity management (authentication delegation only)
- Raw database access or direct data manipulation (abstracted through ViolentUTF API)
- Direct AI model hosting, training, or inference capabilities
- Legacy security tool support outside of security tool for AI ecosystem
- Custom MCP protocol extensions beyond standard specification

#### 1.3.3 Assumptions and Dependencies
**Key Assumptions:**
- ViolentUTF API remains stable and backward-compatible
- APISIX gateway maintains consistent authentication flows
- Keycloak SSO integration continues to function reliably
- MCP clients support JSON-RPC 2.0 and required transport mechanisms

**Critical Dependencies:**
- ViolentUTF API availability and performance
- APISIX gateway operational status
- Keycloak authentication service reliability
- Redis caching infrastructure for performance
- Docker/Kubernetes container orchestration platform

### 1.4 Key Definitions

#### 1.4.1 MCP-Specific Terms
- **MCP**: Model Context Protocol - open standard for LLM-external system integration
- **MCP Host**: LLM application that initiates connections (e.g., Claude Desktop, custom apps)
- **MCP Client**: Component within host that maintains 1:1 server connections
- **MCP Server**: ViolentUTF's implementation providing security testing context and tools
- **MCP Primitives**: Core interaction types (Resources, Tools, Prompts, Sampling)
- **JSON-RPC 2.0**: Wire format protocol for MCP message exchange

#### 1.4.2 ViolentUTF Architecture Terms
- **PyRIT**: Python Risk Identification Tool for AI red-teaming and adversarial testing
- **Garak**: LLM vulnerability scanner for identifying security weaknesses
- **APISIX**: API gateway handling authentication, routing, and rate limiting
- **Keycloak**: Identity and access management system providing SSO authentication
- **FastAPI-MCP**: Zero-configuration library for exposing FastAPI endpoints as MCP tools
- **Red-teaming**: Adversarial testing methodology for AI systems security validation

#### 1.4.3 Security and Operational Terms
- **Orchestrator**: PyRIT component managing complex multi-step security test campaigns
- **Attack Vector**: Specific method or technique used to exploit security vulnerabilities
- **Vulnerability Assessment**: Systematic evaluation of security weaknesses and risks
- **Zero-Configuration**: Automatic MCP server setup requiring no manual tool definitions
- **Human-in-the-Loop**: Safety mechanism requiring human approval for critical operations

### 1.5 ViolentUTF Workflows

The ViolentUTF platform implements a structured workflow for comprehensive AI red-teaming operations, guiding users through systematic security testing processes from initial setup to results analysis.

#### 1.5.1 Core Workflow Architecture

**Sequential Configuration Pattern**:
ViolentUTF follows a guided configuration workflow with six primary phases:
1. **System Initialization** (Start page): Database setup, authentication, and session management
2. **Generator Configuration**: AI model and target system setup
3. **Dataset Management**: Security testing data preparation and validation
4. **Converter Configuration**: Prompt transformation and evasion technique setup
5. **Scorer Configuration**: Vulnerability assessment and evaluation criteria definition
6. **Execution and Analysis** (Dashboard): Test execution monitoring and results visualization

**API-Driven State Management**:
Each workflow phase maintains persistent state through ViolentUTF API endpoints, enabling session continuity, progress tracking, and collaborative configuration management. Workflow progression is enforced through readiness validation at each phase transition.

#### 1.5.2 Detailed Workflow Phases

**Phase 1: System Initialization (0_Start.py)**
- **Database Setup**: Automatic PyRIT memory database initialization with `/api/v1/database/status`
- **Session Management**: User session creation and restoration via `/api/v1/sessions`
- **Authentication Validation**: JWT token generation and Keycloak SSO integration using `/api/v1/auth/token/info`
- **Configuration Loading**: Parameter and session state management through session endpoints
- **Readiness Check**: Database connection validation and system health verification

**Phase 2: Generator Configuration (1_Configure_Generators.py)**
- **Generator Discovery**: Available AI model discovery through `/api/v1/generators/types`
- **APISIX Model Integration**: Dynamic model enumeration via `/api/v1/generators/apisix/models`
- **Configuration Creation**: Generator parameter setup via `/api/v1/generators/types/{generator_type}/params` and storage through `/api/v1/generators`
- **Interactive Testing**: Real-time generator testing through `/api/v1/orchestrators` with execution via `/api/v1/orchestrators/{orchestrator_id}/executions`
- **Readiness Validation**: At least one configured and tested generator required for progression

**Phase 3: Dataset Management (2_Configure_Datasets.py)**
- **Dataset Discovery**: Built-in and user dataset enumeration via `/api/v1/datasets`
- **Upload Capability**: Custom dataset upload with format validation
- **Data Transformation**: Field mapping and structure normalization
- **Preview and Validation**: Dataset content preview and integrity checking
- **Memory Integration**: Dataset registration for orchestrator consumption

**Phase 4: Converter Configuration (3_Configure_Converters.py)**
- **Converter Discovery**: Available transformation techniques via `/api/v1/converters/types`
- **Parameter Configuration**: Converter-specific parameter setup via `/api/v1/converters/params/{converter_type}` and creation through `/api/v1/converters`
- **Preview Functionality**: Real-time conversion preview via `/api/v1/converters/{converter_id}/preview`
- **Application Testing**: Dataset transformation through `/api/v1/converters/{converter_id}/apply`
- **Dataset Integration**: Converter testing with datasets from `/api/v1/datasets`

**Phase 5: Scorer Configuration (4_Configure_Scorers.py)**
- **Scorer Discovery**: Available scoring engines via `/api/v1/scorers/types`
- **Configuration Setup**: Scorer parameter configuration via `/api/v1/scorers/params/{scorer_type}` and creation through `/api/v1/scorers`
- **Test Execution**: Orchestrator-based scoring through `/api/v1/orchestrators/{orchestrator_id}/executions` with generator and dataset integration
- **Health Validation**: Scorer testing with generators from `/api/v1/generators` and datasets from `/api/v1/datasets`
- **Readiness Assessment**: Scorer operational status confirmation

**Phase 6: Execution and Analysis (5_Dashboard.py)**
- **Results Retrieval**: Test results access via `/api/v1/orchestrators/executions/{execution_id}/results`
- **Real-time Monitoring**: Live progress tracking and status updates through orchestrator status endpoints
- **Results Aggregation**: Multi-scorer result compilation and analysis
- **Visualization**: Interactive charts, metrics, and trend analysis based on retrieved results
- **Report Generation**: Comprehensive security assessment report creation with export capabilities

#### 1.5.3 Workflow State Management

**Progressive Validation Pattern**:
Each workflow phase implements readiness validation with advisory guidance:
- **Generator Phase**: Recommends at least one configured and tested generator
- **Dataset Phase**: Checks dataset availability and format compliance
- **Converter Phase**: Validates converter functionality and parameters
- **Scorer Phase**: Tests scorer connectivity and operational readiness
- **Dashboard Phase**: Aggregates all components for comprehensive testing execution

Note: In the current implementation, phase progression is advisory rather than enforced, allowing users flexibility to navigate between phases as needed.

**Session Persistence**:
Workflow state persistence through `/api/v1/sessions` endpoints enables:
- **Configuration Recovery**: Restoration of partial configurations across sessions
- **Progress Tracking**: Workflow completion status and component readiness monitoring
- **Collaborative Configuration**: Multi-user configuration sharing and handoff capabilities
- **Audit Trail**: Complete configuration history and change tracking

**Error Recovery and Validation**:
- **Component Health Monitoring**: Continuous validation of configured components
- **Graceful Degradation**: Partial functionality maintenance during component failures
- **Configuration Rollback**: Ability to revert to previous working configurations
- **Validation Feedback**: Real-time configuration validation with corrective guidance

#### 1.5.4 Workflow Integration Points

**MCP Tool Mapping**:
Each workflow phase directly corresponds to MCP tool categories:
- **System Initialization** → System management and health monitoring tools
- **Generator Configuration** → AI model configuration and testing tools
- **Dataset Management** → Data upload, validation, and transformation tools
- **Converter Configuration** → Prompt transformation and preview tools
- **Scorer Configuration** → Assessment engine configuration and testing tools
- **Dashboard Execution** → Orchestrator management and results analysis tools

**Resource Exposure**:
Workflow artifacts become MCP resources mapped to actual ViolentUTF API endpoints:
- **Configuration State** → `vutf://generators/{generator_id}`, `vutf://datasets/{dataset_id}`, `vutf://converters/{converter_id}`, `vutf://scorers/{scorer_id}`
- **Test Results** → `vutf://orchestrators/executions/{execution_id}/results`
- **Component Status** → `vutf://database/status`, `vutf://auth/token/info`
- **Session Data** → `vutf://sessions/{session_id}` for workflow state and progress tracking

**Sampling Integration**:
Workflow phases integrate sampling requests for:
- **Configuration Optimization** → LLM-assisted parameter tuning
- **Attack Scenario Generation** → Creative security testing approach development
- **Results Analysis** → AI-powered vulnerability assessment and reporting
- **Remediation Guidance** → Automated security improvement recommendations

---

## 2. Current State Analysis

### 2.1 Existing ViolentUTF Infrastructure

#### 2.1.1 Verified API Endpoints
The following API endpoints have been verified to exist and are ready for MCP exposure:

**System Management**
- ✅ `/api/v1/health/*` - Health checks and monitoring
- ✅ `/api/v1/database/*` - Database initialization, status, and management
- ✅ `/api/v1/sessions/*` - Session state persistence and recovery
- ✅ `/api/v1/config/*` - Configuration parameter management

**Authentication & Security**
- ✅ `/api/v1/auth/*` - JWT token management and user authentication
- ✅ `/api/v1/keys/*` - JWT key rotation and management

**Workflow Components**
- ✅ `/api/v1/generators/*` - AI model configuration and testing
- ✅ `/api/v1/datasets/*` - Security dataset upload and management
- ✅ `/api/v1/converters/*` - Prompt transformation tools
- ✅ `/api/v1/scorers/*` - Vulnerability assessment engines
- ✅ `/api/v1/orchestrators/*` - Test campaign management

**Additional Services**
- ✅ `/api/v1/files/*` - File upload/download operations
- ✅ `/api/v1/redteam/*` - PyRIT and Garak tool integration
- ✅ `/api/v1/echo/*` - Testing and diagnostic endpoints

#### 2.1.2 Security Features Currently Implemented
- ✅ **APISIX Gateway Validation**: All requests must include `X-API-Gateway: APISIX` header
- ✅ **Comprehensive Rate Limiting**: Using SlowAPI with configurable limits per endpoint
- ✅ **Input Validation Framework**: Extensive sanitization and validation for all inputs
- ✅ **JWT Authentication**: Dual support for Keycloak SSO and environment credentials
- ✅ **Role-Based Access Control**: Permission checks based on user roles
- ✅ **Security Headers**: CSP, HSTS, XSS protection, and frame options

#### 2.1.3 Workflow Implementation Status
The six-phase workflow is implemented but with more flexibility than originally documented:
- **Phase Progression**: Advisory rather than enforced - users can navigate freely
- **Readiness Validation**: Informational checks without blocking progression
- **Session Persistence**: Basic state saving for UI preferences and workflow progress
- **Component Dependencies**: Loosely coupled allowing independent configuration

### 2.2 Gap Analysis

#### 2.2.1 MCP Components Not Yet Implemented
- ❌ MCP Server infrastructure
- ❌ FastAPI-MCP library integration
- ❌ MCP primitive handlers (Tools, Resources, Prompts, Sampling)
- ❌ OAuth proxy for MCP client compatibility
- ❌ WebSocket subscriptions for real-time updates
- ❌ MCP-specific caching layer

#### 2.2.2 Required Infrastructure Additions
- Redis for caching and subscription management
- WebSocket support for real-time resource updates
- MCP-specific authentication bridge
- Response transformation layer for LLM optimization

---

## 3. Implementation Roadmap

### 3.1 Phase 1: Foundation (Weeks 1-2)

#### 3.1.1 Core Infrastructure Setup
- [ ] Install FastAPI-MCP library and dependencies
- [ ] Create MCP server module structure in `violentutf_api/mcp/`
- [ ] Implement basic MCP server with stdio transport support
- [ ] Add MCP server mount point to main FastAPI application

#### 3.1.2 Authentication Integration
- [ ] Create Keycloak OAuth proxy for MCP clients
- [ ] Implement JWT token bridge between Keycloak and ViolentUTF
- [ ] Add MCP-specific authentication handlers
- [ ] Configure APISIX routes for `/mcp/*` endpoints

### 3.2 Phase 2: Core Primitives (Weeks 3-4)

#### 3.2.1 Tools Implementation
- [ ] Create tool registration framework
- [ ] Implement system management tools (database, sessions)
- [ ] Add generator configuration tools
- [ ] Implement orchestrator lifecycle tools
- [ ] Add dataset management tools

#### 3.2.2 Resources Implementation
- [ ] Create resource URI schema (`vutf://`)
- [ ] Implement configuration resources
- [ ] Add dataset and result resources
- [ ] Create documentation resources
- [ ] Implement access control for resources

### 3.3 Phase 3: Advanced Features (Weeks 5-6)

#### 3.3.1 Prompts and Sampling
- [ ] Design prompt template engine
- [ ] Implement red-teaming workflow prompts
- [ ] Add sampling for AI-assisted analysis
- [ ] Create safety filters for sampling
- [ ] Implement human-in-the-loop controls

#### 3.3.2 Real-Time Features
- [ ] Implement WebSocket subscription manager
- [ ] Add real-time resource updates
- [ ] Create progress monitoring subscriptions
- [ ] Implement notification system
- [ ] Add subscription cleanup mechanisms

### 3.4 Phase 4: Optimization & Hardening (Weeks 7-8)

#### 3.4.1 Performance Optimization
- [ ] Implement Redis caching layer
- [ ] Add response aggregation for complex operations
- [ ] Optimize database query patterns
- [ ] Implement connection pooling
- [ ] Add performance monitoring

#### 3.4.2 Security Hardening
- [ ] Comprehensive security testing
- [ ] Rate limiting tuning for MCP operations
- [ ] Audit logging implementation
- [ ] Penetration testing
- [ ] Security documentation

### 3.5 Phase 5: Testing & Documentation (Weeks 9-10)

#### 3.5.1 Testing Strategy
- [ ] Unit tests for all MCP primitives
- [ ] Integration tests with ViolentUTF API
- [ ] End-to-end tests with MCP clients
- [ ] Performance benchmarking
- [ ] Load testing

#### 3.5.2 Documentation & Training
- [ ] API documentation for MCP endpoints
- [ ] Client integration guides
- [ ] Security best practices
- [ ] Troubleshooting guides
- [ ] Video tutorials

### 3.6 Success Criteria

| Milestone | Success Criteria | Target Date |
|-----------|-----------------|-------------|
| Foundation Complete | Basic MCP server running with auth | Week 2 |
| Tools Operational | 80% of API endpoints exposed as tools | Week 4 |
| Resources Available | All core resources accessible | Week 5 |
| Advanced Features | Prompts and sampling functional | Week 6 |
| Production Ready | All tests passing, documented | Week 10 |

### 3.7 Risk Mitigation

**Technical Risks**
- **FastAPI-MCP Compatibility**: Early prototype to validate integration
- **Performance Impact**: Continuous monitoring and optimization
- **Security Vulnerabilities**: Regular security reviews and testing

**Schedule Risks**
- **Dependency Updates**: Pin versions for stability
- **Resource Availability**: Identify backup resources
- **Scope Creep**: Strict adherence to MVP features

---

## 4. System Architecture

### 4.1 Architectural Overview

#### 4.1.1 Architecture Style and Patterns
**Primary Architecture**: Microservice API Gateway Pattern with MCP Façade
- **MCP Server Role**: Standardized interface exposing ViolentUTF security testing capabilities
- **FastAPI-MCP Integration**: Zero-configuration conversion of FastAPI endpoints to MCP tools
- **Gateway Pattern**: APISIX provides centralized authentication, routing, and rate limiting
- **Façade Pattern**: Simplified, LLM-optimized interface over complex ViolentUTF API

#### 4.1.2 Transport Architecture
**Multi-Transport Support with Co-located Deployment**:
The ViolentUTF MCP Server is deployed as part of the same FastAPI instance as the ViolentUTF API, enabling efficient direct integration while supporting external client access:

- **HTTP/SSE Transport**: Primary transport for external MCP clients (Claude Desktop, Cursor, Windsurf, ViolentUTF Simple Chat app) communicating with the MCP Server from outside the deployment instance
- **ASGI Transport**: Internal FastAPI integration for optimal performance within the same instance
- **Stdio Transport**: Development and testing support for local process communication
- **Bridge Support**: mcp-remote compatibility for authentication and legacy clients

**Wire Protocol**: JSON-RPC 2.0 with MCP-specific message types:
- **Requests**: Client-initiated operations requiring responses
- **Responses**: Server replies to client requests
- **Notifications**: One-way messages for events and updates

#### 4.1.3 Integration Strategy
**ViolentUTF API Façade**:
- **API-First Design**: MCP interface designed for LLM consumption patterns
- **Aggregated Endpoints**: Combining multiple API calls into single MCP tools
- **Response Transformation**: API responses optimized for MCP resource format
- **Error Harmonization**: Consistent error handling across all MCP primitives

### 4.2 Component Architecture

#### 4.2.1 Core MCP Infrastructure

**MCP Protocol Handler**

The MCP Protocol Handler manages all JSON-RPC 2.0 message parsing and validation, routing requests to appropriate primitive managers, formatting responses and handling errors, negotiating protocol versions and capability exchange, and managing connection lifecycle including initialization, handshake, and termination phases.

**Transport Manager**

The Transport Manager handles multiple communication protocols including stdio transport for local process communication, HTTP/SSE transport for web-based MCP clients, ASGI transport for direct FastAPI integration, connection multiplexing and session management across different transport types, and transport-specific error handling and recovery mechanisms.

**Primitive Managers**

The Primitive Manager system includes specialized managers for each MCP primitive type: ToolManager for FastAPI endpoint exposure and execution, ResourceManager for security dataset and result management, PromptManager for red-teaming workflow template handling, SamplingManager for AI-assisted analysis and generation, and SubscriptionManager for real-time update notifications.

#### 4.2.2 Authentication and Security Layer

**Authentication Bridge**

The Authentication Bridge provides APISIX gateway integration with JWT token handling, Keycloak SSO authentication flow management, role-based access control enforcement, token refresh and session management capabilities, and multi-factor authentication support when configured.

**Security Context Manager**

The Security Context Manager handles user role and permission resolution, enforces resource access control policies, maintains audit logging and compliance tracking, implements rate limiting and abuse prevention mechanisms, and provides security event monitoring with alerting capabilities.

#### 4.2.3 ViolentUTF Integration Layer

**API Adapter**

The ViolentUTF API Adapter provides automatic FastAPI endpoint discovery and registration, request/response transformation and validation, error mapping with enhanced messaging, pagination handling for large datasets, and async operation management with progress tracking capabilities.

**Orchestrator Manager**
```python
class OrchestratorManager:
    - PyRIT orchestrator lifecycle management
    - Garak scanner integration and execution
    - Campaign planning and execution coordination
    - Real-time progress monitoring and reporting
    - Resource allocation and cleanup
```

**Dataset Manager**
```python
class DatasetManager:
    - Security dataset caching and versioning
    - Access control and data classification
    - Dynamic content generation and transformation
    - Subscription-based update notifications
    - Data integrity and validation
```

**Results Processor**
```python
class ResultsProcessor:
    - Test result aggregation and analysis
    - Vulnerability assessment report generation
    - Statistical analysis and trend identification
    - Export format transformation (JSON, CSV, PDF)
    - Integration with external reporting systems
```

#### 4.2.4 Configuration and Management

**Configuration Manager**
```python
class ConfigurationManager:
    - Environment-based configuration loading
    - Runtime feature flag management
    - Security policy enforcement
    - Performance tuning parameters
    - Health check and monitoring configuration
```

**Cache Manager**
```python
class CacheManager:
    - Redis-backed caching for frequent operations
    - Cache invalidation and consistency management
    - Performance metrics and optimization
    - Distributed caching coordination
    - Cache warming and preloading strategies
```

### 4.3 Communication Flow

#### 4.3.1 Detailed Architecture Diagram
```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   MCP Clients   │    │  ViolentUTF MCP  │    │ ViolentUTF API  │
│                 │    │     Server       │    │                 │
│ • Claude Desktop│◄──►│                  │◄──►│ • Orchestrators │
│ • Cursor        │    │ • FastAPI-MCP    │    │ • Datasets      │
│ • Windsurf      │    │ • Auth Bridge    │    │ • Results       │
│ • Custom Apps   │    │ • Cache Layer    │    │ • Config        │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │                        │
                                ▼                        ▼
                       ┌─────────────────┐    ┌─────────────────┐
                       │ APISIX Gateway  │    │ PyRIT/Garak     │
                       │                 │    │                 │
                       │ • Authentication│    │ • Orchestrators │
                       │ • Rate Limiting │    │ • Scanners      │
                       │ • Monitoring    │    │ • Tools         │
                       └─────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │ Keycloak SSO    │
                       │                 │
                       │ • Identity Mgmt │
                       │ • Role Mapping  │
                       │ • OAuth 2.0     │
                       └─────────────────┘
```

#### 4.3.2 Message Flow Patterns

**Tool Invocation Flow**:
1. **Client Request**: MCP client sends `tools/call` with parameters
2. **Authentication**: APISIX validates JWT token and extracts user roles
3. **Authorization**: Security context manager verifies tool access permissions
4. **Execution**: Tool manager routes to appropriate ViolentUTF API endpoint
5. **Processing**: API adapter transforms request and handles async operations
6. **Response**: Results formatted and returned through MCP protocol

**Resource Subscription Flow**:
1. **Subscription**: Client subscribes to resource updates (e.g., test results)
2. **Registration**: Subscription manager registers client for notifications
3. **Event Detection**: Results processor detects changes in monitored resources
4. **Notification**: Real-time updates sent via SSE or notification messages
5. **Cleanup**: Subscription automatically cleaned up on client disconnection

**Sampling Request Flow**:
1. **Server Initiation**: ViolentUTF MCP server requests LLM assistance
2. **Human Review**: Client presents sampling request for user approval
3. **LLM Generation**: Client generates completion using preferred model
4. **Result Validation**: Client reviews and potentially modifies response
5. **Return**: Final result returned to server for processing

### 4.4 Data Management Strategy

#### 4.4.1 Configuration Management
**Environment-Based Configuration**:
```python
# Core MCP server configuration
MCP_SERVER_NAME = "ViolentUTF Security Testing"
MCP_SERVER_DESCRIPTION = "AI red-teaming and security testing platform"
MCP_MOUNT_PATH = "/mcp"
MCP_TRANSPORT_TYPES = ["http", "stdio"]

# Authentication configuration
APISIX_GATEWAY_URL = "http://localhost:9080"
KEYCLOAK_REALM = "violentutf"
KEYCLOAK_CLIENT_ID = "mcp-server"
JWT_SECRET_KEY = "${JWT_SECRET_KEY}"

# Performance and caching
REDIS_URL = "redis://localhost:6379"
CACHE_TTL_SECONDS = 300
MAX_CONCURRENT_TOOLS = 10
REQUEST_TIMEOUT_SECONDS = 30
```

#### 4.4.2 Authentication and Session Management
**Keycloak JWT Token Flow**:
- **Token Validation**: APISIX validates JWT signatures and expiration
- **Role Extraction**: User roles and groups extracted from token claims
- **Permission Mapping**: Roles mapped to MCP resource/tool permissions
- **Automatic Refresh**: Tokens refreshed proactively before expiration
- **Session Tracking**: User sessions tracked for audit and security

#### 4.4.3 Caching Architecture
**Redis-Backed Multi-Layer Caching**:
```python
class CacheStrategy:
    # L1 Cache: In-memory for frequently accessed data
    memory_cache_size = 100MB
    memory_cache_ttl = 60_seconds

    # L2 Cache: Redis for shared caching across instances
    redis_cache_ttl = 300_seconds
    redis_cache_max_size = 1GB

    # L3 Cache: API response caching
    api_response_cache_ttl = 60_seconds
    api_response_max_entries = 1000
```

**Cache Invalidation Strategies**:
- **Time-based**: Automatic expiration for time-sensitive data
- **Event-based**: Cache invalidation triggered by data changes
- **Manual**: Administrative cache clearing for maintenance
- **Dependency-based**: Cascading invalidation for related data

#### 4.4.4 State Management
**Orchestrator Session Tracking**:
- **Session Creation**: New sessions registered with unique identifiers
- **Progress Monitoring**: Real-time status updates via ViolentUTF API
- **Resource Allocation**: CPU/memory tracking for running orchestrators
- **Cleanup Management**: Automatic cleanup of completed/failed sessions
- **Audit Trail**: Complete history of session lifecycle events

#### 4.4.5 Data Persistence Strategy
**API-Mediated Database Access**:
- **Abstracted Database Operations**: All data operations performed through ViolentUTF API endpoints, with database status and monitoring exposed as MCP resources
- **Transactional Consistency**: API ensures data integrity and transactions while providing status visibility
- **Backup and Recovery**: Handled by underlying ViolentUTF infrastructure
- **Data Migration**: API versioning handles schema changes transparently
- **Audit Compliance**: API provides comprehensive audit logging accessible through MCP resources

#### 4.4.6 Performance Optimization
**Async Operation Management**:
```python
class AsyncOperationManager:
    # Connection pooling for API calls
    api_connection_pool_size = 20
    api_connection_timeout = 30_seconds

    # Concurrent operation limits
    max_concurrent_tools = 10
    max_concurrent_resources = 50

    # Background task management
    background_task_queue_size = 100
    background_task_workers = 5
```

**Resource Optimization**:
- **Lazy Loading**: Resources loaded only when requested
- **Pagination**: Large datasets paginated automatically
- **Compression**: Response compression for large data transfers
- **Connection Reuse**: HTTP connection pooling for API calls
- **Memory Management**: Automatic garbage collection and memory limits

---

## 5. MCP Primitives Design

*Enhanced with ViolentUTF Application Workflow Integration*

### 5.1 Resources Design

*Enhanced with ViolentUTF Workflow Integration*

#### 5.1.1 Resource Categories and Implementation

**ViolentUTF Configuration Resources**
Based on the Start page workflow, the MCP server exposes comprehensive configuration management resources enabling LLMs to access and monitor ViolentUTF system state. Configuration resources follow URI patterns `vutf://config/{component_type}/{config_id}` and provide real-time access to system parameters, database status, environment configuration, and session state information.

Configuration resources include database initialization status accessible through `vutf://config/database/status` with content covering connection status, table statistics, record counts, and backup information. Environment configuration resources at `vutf://config/environment/current` expose system settings, API endpoints, authentication parameters, and operational flags enabling LLMs to understand current system capabilities and constraints.

Session state resources following `vutf://config/session/{session_id}` patterns provide workflow progress tracking, user preferences, temporary configuration data, and step completion status enabling context-aware assistance and workflow resumption guidance.

**Security Datasets**
Security datasets are exposed as MCP resources with standardized URI patterns following the format `vutf://datasets/{dataset_id}`. Each dataset resource includes comprehensive metadata covering dataset classification levels (public, internal, confidential, restricted), version information, creation timestamps, content statistics, and descriptive tags for categorization.

Dataset resources support multiple MIME types including application/json for structured data, text/csv for tabular datasets, and application/octet-stream for binary formats. The metadata structure provides detailed information about dataset types (attack_patterns, test_cases, prompts, targets), size metrics including byte counts and record counts, and temporal tracking with created_at and updated_at timestamps.

**Workflow-Integrated Dataset Resources**
Dataset resources integrate with the Configure Datasets workflow phase through specialized URIs: `vutf://datasets/built-in` exposing system-provided security datasets, `vutf://datasets/user-uploaded` providing access to custom uploaded datasets, and `vutf://datasets/preview/{dataset_id}` offering content preview and validation status. Dataset transformation resources at `vutf://datasets/{dataset_id}/transformed` provide field-mapped and normalized versions for orchestrator consumption.

Dataset memory integration resources following `vutf://datasets/memory-entries/{dataset_id}` expose PyRIT memory entries created from dataset processing, enabling LLMs to understand dataset utilization patterns and historical usage statistics.

**Test Results and Reports**
Test execution results are provided as dynamic MCP resources using URI patterns like `vutf://results/{session_id}/{result_id}` for individual results and session-based access. These resources contain comprehensive execution information including orchestrator identification, real-time status tracking (running, completed, failed, cancelled), temporal execution data with start and optional end times, and detailed progress percentages.

Test result content includes structured vulnerability findings arrays, performance metrics covering response times and success rates, and raw output data for detailed analysis. Each test result resource provides a subscription URI following the pattern `vutf://subscriptions/results/{session_id}` enabling real-time updates and progress monitoring through WebSocket connections.

**Dashboard-Integrated Results Resources**
Results resources enhance the Dashboard workflow through specialized aggregation URIs: `vutf://results/summary/current` providing real-time metrics compilation, `vutf://results/critical-findings` exposing high-severity vulnerabilities, and `vutf://results/trends/{time_range}` offering temporal analysis data.

Historical results resources following `vutf://results/history/{orchestrator_id}` provide execution timeline data, while comparative analysis resources at `vutf://results/comparison/{baseline_id}` enable trend analysis and regression detection across multiple test campaigns.

**System Status and Health**
System health information is accessible through dedicated status resources using predefined URIs: `vutf://status/system` for overall system health, `vutf://status/orchestrators` for PyRIT orchestrator status, and `vutf://status/api` for API service health. These resources provide real-time system monitoring data with standardized status indicators (healthy, degraded, down) and component-level health tracking.

Status resources include comprehensive metrics covering active user sessions, execution queue depths, and detailed resource utilization statistics for CPU, memory, and network resources. Each status resource automatically refreshes every 30 seconds to provide current system state information and includes timestamp tracking for monitoring data freshness.

**Workflow-Specific Status Resources**
Status resources integrate with workflow phases through component-specific URIs: `vutf://status/generators` providing generator configuration and testing status, `vutf://status/converters` exposing converter health and parameter validation, and `vutf://status/scorers` offering scorer connectivity and operational status. Database status resources at `vutf://status/database` provide initialization status, connection health, and storage metrics.

Workflow progression status resources following `vutf://status/workflow/{phase}` track configuration completeness, component readiness, and validation status enabling LLMs to guide users through proper workflow execution sequences.

**Documentation and Guides**
Documentation resources are organized using hierarchical URI patterns `vutf://docs/{doc_type}/{doc_id}` enabling categorized access to guides, tutorials, API documentation, and best practices. These resources support multiple content formats including text/markdown for structured documentation, text/plain for simple guides, and application/pdf for comprehensive manuals.

Documentation content includes version tracking, structured content with embedded examples, cross-references to related MCP tools, and temporal metadata for content freshness tracking. Each documentation resource maintains relationships to relevant ViolentUTF tools and provides contextual examples to assist LLMs in understanding proper usage patterns.

**Workflow-Contextual Documentation Resources**
Documentation resources provide workflow-specific guidance through phase-oriented URIs: `vutf://docs/workflow/generator-setup` offering generator configuration guidance, `vutf://docs/workflow/dataset-management` providing dataset handling best practices, and `vutf://docs/workflow/converter-configuration` explaining prompt transformation techniques. Troubleshooting documentation at `vutf://docs/troubleshooting/{component}` provides component-specific error resolution guidance.

Interactive help resources following `vutf://docs/help/{current_page}` provide context-sensitive assistance based on user's current workflow phase, while API integration documentation at `vutf://docs/api/{endpoint_category}` explains proper usage of ViolentUTF API endpoints exposed through MCP tools.

#### 5.1.2 Resource Schema Strategy

**JSON Schema Validation Framework**
The ResourceSchemaManager implements comprehensive schema validation for all MCP resource types using JSON Schema specifications. The manager maintains a registry of versioned schemas including security_dataset_v1.json for dataset validation, test_result_v1.json for execution results, system_status_v1.json for health monitoring, and documentation_v1.json for content resources.

Schema validation occurs at resource creation and update time through the validate_resource method, which enforces structural consistency and data type requirements. The framework supports schema evolution through versioned schema files and provides detailed error reporting for validation failures, ensuring all MCP resources maintain consistent structure and content format.

**Versioned Schema Management**:
- **Schema Versioning**: Semantic versioning (v1.0.0) for all resource schemas
- **Backward Compatibility**: Support for multiple schema versions simultaneously
- **Migration Paths**: Automatic content migration between schema versions
- **Deprecation Policy**: 6-month notice before removing old schema versions

#### 5.1.3 Dynamic Content Sourcing

**ViolentUTF API Integration**
The ResourceContentSource implements dynamic content sourcing through direct integration with ViolentUTF API endpoints. Security datasets are retrieved via the `/api/v1/datasets` endpoint with optional filtering support, enabling dynamic resource discovery based on user permissions and content classification levels.

Test results are accessed through session-specific endpoints at `/api/v1/sessions/{session_id}/results` providing real-time execution data and progress tracking. The integration supports real-time updates through WebSocket subscriptions to `/api/v1/subscriptions/{resource_uri}` endpoints, enabling live resource content updates as orchestrator executions progress and system status changes occur.

#### 5.1.4 Access Control and Security

**Role-Based Access Control**
The ResourceAccessControl system implements fine-grained permission management based on Keycloak user roles and resource classification levels. The permission matrix defines hierarchical access control where security datasets support four classification levels: public datasets accessible to security_analyst, red_team, and administrator roles; internal datasets restricted to red_team and administrator; confidential datasets limited to administrator access; and restricted datasets requiring system_administrator privileges.

Test result access follows ownership-based permissions where users can access their own session results with security_analyst, red_team, or administrator roles, while viewing all user sessions requires administrator privileges, and system-level results access is restricted to system_administrator roles. The access control evaluation uses role intersection logic to determine resource accessibility based on user's assigned Keycloak roles.

#### 5.1.5 Resource URI Patterns and Management

**URI Schema Design**
The ViolentUTF MCP server uses a standardized URI schema with the `vutf://` custom scheme for resource identification. Dataset resources follow the pattern `vutf://datasets/{dataset_id}` for direct dataset access, while test execution results use hierarchical URIs `vutf://results/{session_id}/{result_id}` enabling session-based organization and result lookup.

System components are accessible through `vutf://status/{component}` URIs for health monitoring, and documentation follows categorized patterns `vutf://docs/{category}/{document_id}` for organized content access. Real-time subscriptions use `vutf://subscriptions/{resource_type}/{id}` for WebSocket connectivity, and cached resources utilize `vutf://cache/{cache_key}` for performance optimization and temporary data storage.

**Subscription Management**
The SubscriptionManager implements comprehensive real-time update distribution for MCP resources through client subscription tracking and notification delivery. Active subscriptions are maintained in a registry mapping resource URIs to sets of subscribed client identifiers, enabling efficient multi-client notification distribution.

Subscription management includes automatic monitoring initiation for subscribed resources through the _start_monitoring method, which establishes WebSocket connections to ViolentUTF API endpoints for live data streaming. The notification system uses asynchronous queue processing to deliver updates to all registered subscribers, ensuring real-time resource change distribution across multiple MCP clients simultaneously.

### 5.2 Tools Design

*Enhanced with ViolentUTF Generator and Dataset Configuration Workflows*

#### 5.2.1 Tool Categories and Implementation

**Generator Configuration Tools**
Based on the Configure Generators workflow (1_Configure_Generators.py), the MCP server exposes comprehensive generator management tools enabling LLM-driven AI model configuration and testing. Generator tools integrate with APISIX Gateway routes for dynamic model discovery and provide real-time testing capabilities through orchestrator-based execution patterns.

The discover_generator_types tool queries `/api/v1/generators/types` to enumerate available AI model categories including OpenAI models, Anthropic models, local Ollama instances, and custom API endpoints. Model-specific parameter discovery through `/api/v1/generators/types/{generator_type}/params` provides dynamic schema information for configuration validation.

APISIX model discovery tools interface with `/api/v1/generators/apisix/models?provider={provider}` endpoints enabling real-time model availability checking across different AI providers. This integration supports dynamic provider selection and model availability validation essential for robust generator configuration workflows.

**Orchestrator Management Tools**
```python
**Orchestrator Management Tools**
The OrchestratorTools class exposes PyRIT orchestrator lifecycle management through MCP tools with comprehensive parameter validation and API integration. The create_pyrit_orchestrator tool accepts configuration parameters including orchestrator name, target AI model specification, attack strategy selection from predefined options (jailbreak, prompt_injection, adversarial), optional dataset references, and execution limits with validated ranges.

Orchestrator creation involves multi-stage processing: input validation and sanitization through _validate_orchestrator_params, orchestrator instantiation via POST requests to `/api/v1/orchestrators`, and formatted response generation including unique orchestrator identifiers, creation status confirmation, complete configuration details, and estimated execution duration for planning purposes.

**Generator-Orchestrator Integration Tools**
Generator testing tools integrate orchestrator-based execution patterns replacing deprecated direct testing endpoints. The test_generator_via_orchestrator tool creates temporary PromptSendingOrchestrator instances targeting configured generators, executes test prompts through `/api/v1/orchestrators/{orchestrator_id}/executions`, and provides comprehensive response analysis including success status, response content, execution duration, and error diagnostics.

Generator management tools support lifecycle operations through `/api/v1/generators` endpoints: create_generator for new generator configuration, update_generator for parameter modification, delete_generator for resource cleanup, and list_generators for discovery and inventory management. Each tool integrates with session state management for workflow continuity and progress tracking.

The start_orchestrator tool manages orchestrator execution initiation with configurable priority levels (low, normal, high) and comprehensive permission validation. Execution startup includes permission verification through _check_orchestrator_permissions ensuring users can only start orchestrators they own or have appropriate role-based access to.

Orchestrator execution begins through POST requests to `/api/v1/orchestrators/{orchestrator_id}/executions` with priority specification and input data configuration supporting both prompt_list and dataset execution types. The tool returns execution session identifiers, status confirmation, and dynamically generated progress URIs following the pattern `vutf://results/{session_id}/progress` for real-time monitoring integration.

**Interactive Generator Testing Tools**
Interactive testing tools enable real-time generator validation through chat-like interfaces. The send_test_message tool accepts generator identifiers and test prompts, creates temporary orchestrator instances for execution, and returns formatted responses including clean AI output extraction, technical diagnostic information, and performance metrics.

Conversation management tools maintain chat history through session state, provide response formatting options (clean vs. technical views), and support conversation clearing and export functionality. These tools integrate with the interactive testing workflow enabling immediate generator validation and iterative configuration refinement.
```

**Dataset Operations Tools**
```python
**Dataset Operations Tools**
The DatasetTools class provides comprehensive dataset management capabilities through the upload_security_dataset tool, supporting multiple dataset types (attack_patterns, test_cases, prompts, targets) and formats (json, csv, yaml) with configurable classification levels for access control.

Dataset upload processing involves multi-stage validation: Base64 content decoding and format validation through _decode_and_validate_content, size limit enforcement against MAX_DATASET_SIZE constraints, and structured API submission to `/api/v1/datasets` with complete metadata including name, description, type classification, decoded content, format specification, and security classification defaulting to internal level.

Successful uploads return comprehensive response data including unique dataset identifiers, upload status confirmation, detailed validation results from content parsing and structure verification, and generated resource URIs following the pattern `vutf://datasets/{dataset_id}` for immediate MCP resource access.

**Dataset Configuration Workflow Tools**
Dataset workflow tools integrate with the Configure Datasets phase through specialized operations: discover_datasets queries `/api/v1/datasets` for available datasets with built-in and user-uploaded categorization, preview_dataset provides content sampling and structure analysis through `/api/v1/datasets/preview`, and validate_dataset_format performs format compliance checking and field mapping validation.

Dataset transformation tools support field mapping and normalization through `/api/v1/datasets/{dataset_id}/transform` enabling compatibility with different orchestrator types. Memory integration tools via `/api/v1/datasets/memory` provide PyRIT memory entry creation and dataset utilization tracking for comprehensive workflow integration.

**Dataset Testing and Validation Tools**
Dataset testing tools enable validation through orchestrator execution: test_dataset_with_generator creates temporary test orchestrators using configured generators and selected datasets, executes sample prompts through the dataset, and provides validation results including prompt processing success rates, response quality assessment, and dataset utilization statistics.

Dataset analysis tools provide statistical analysis through content inspection, field distribution analysis, prompt complexity assessment, and compatibility checking with different generator types. These tools support the dataset selection and validation processes essential for effective red-teaming campaign configuration.
```

**Result Analysis Tools**
```python
**Result Analysis Tools**
The ResultAnalysisTools class implements comprehensive vulnerability assessment analysis through the analyze_vulnerability_results tool, supporting multiple analysis types (summary, detailed, comparison) with configurable data inclusion options and export format selection (json, csv, pdf).

Result analysis processing begins with test result retrieval from `/api/v1/orchestrators/{orchestrator_id}/results` followed by analysis execution through _perform_analysis based on specified analysis type. The tool supports optional raw data inclusion for detailed examination and provides export functionality through _export_analysis for non-JSON formats.

Analysis output includes session identification, structured analysis results with vulnerability summaries and metrics, optional export data for alternative formats, and generation timestamps for result tracking and audit purposes.

**Dashboard Integration Tools**
Dashboard tools integrate with the results analysis workflow through specialized visualization and aggregation functions: generate_security_metrics compiles comprehensive security assessment metrics, create_vulnerability_timeline provides temporal analysis of findings, and export_assessment_report generates comprehensive security reports in multiple formats.

Real-time monitoring tools interface with orchestrator execution endpoints to provide live progress tracking, status updates, and result streaming. These tools support the Dashboard workflow's requirement for continuous monitoring and analysis of ongoing security testing campaigns.
```

#### 5.2.2 Tool Security and Validation Design

**Workflow-Integrated Security Framework**
Security validation integrates with ViolentUTF workflow phases through phase-specific validation rules: generator configuration tools validate APISIX API key requirements and model availability, dataset tools enforce size limits and format compliance, converter tools validate parameter ranges and transformation safety, and orchestrator tools implement execution quotas and resource limits.

Workflow progression validation ensures proper configuration sequences: generator readiness validation before dataset configuration, dataset availability verification before converter setup, converter functionality confirmation before scorer configuration, and comprehensive component validation before orchestrator execution initiation.

**Authentication Integration with ViolentUTF Workflows**
Authentication validation integrates with the centralized JWT management system used throughout ViolentUTF pages. The get_auth_headers pattern provides consistent authentication across all MCP tools using jwt_manager.get_valid_token() for automatic token refresh, APISIX gateway identification headers, and API key management for AI model access.

Session-based authentication validation ensures workflow continuity through token persistence, automatic refresh on expiration, and graceful degradation handling for authentication failures. User context extraction from JWT tokens enables personalized configuration management and role-based access control for sensitive operations.

**Comprehensive Input Validation**:
```python
**Comprehensive Input Validation**
The ToolSecurityManager implements multi-layered input validation combining JSON Schema validation with additional security-focused sanitization. The validation framework supports multiple data types through dedicated validators for string, integer, array, and object inputs, ensuring comprehensive parameter checking for all MCP tool invocations.

Input sanitization includes removal of potential injection patterns targeting SQL injection vulnerabilities (semicolons, quotes, backslashes), command injection risks (backticks, dollar signs, parentheses, braces), and path traversal attacks (dot-dot-slash sequences). Length validation enforces 10,000 character limits on string inputs to prevent buffer overflow and resource exhaustion attacks.

The validation process combines schema-based structure validation through jsonschema.validate with field-by-field sanitization through _sanitize_input, ensuring both structural correctness and content security for all tool parameters.

**Workflow-Specific Validation Rules**
Validation rules adapt to workflow phase requirements: generator configuration validation ensures valid APISIX provider selection and model availability verification, dataset validation enforces format compliance and size constraints, converter validation checks parameter ranges and transformation safety, and scorer validation confirms connectivity and threshold validity.

Configuration dependency validation prevents invalid workflow states: generators must be configured before datasets can be tested, datasets must be available before converters can be applied, converters must be functional before scoring can be configured, and all components must be ready before orchestrator execution can begin.
```

**Rate Limiting and Abuse Prevention**:
```python
**Rate Limiting and Abuse Prevention**
The ToolRateLimiter implements Redis-backed rate limiting with tool-specific quotas designed to prevent abuse while maintaining usability. Rate limits are configured based on tool resource requirements: create_orchestrator limited to 10 calls per hour for resource-intensive operations, start_orchestrator restricted to 5 calls per 5 minutes to prevent execution flooding, upload_dataset capped at 5 calls per hour for storage management, and analyze_results allowing 100 calls per hour for analysis operations.

Rate limit checking follows a Redis-based sliding window approach using user-specific keys formatted as `rate_limit:{user_id}:{tool_name}`. The system increments usage counters and sets expiration windows automatically, returning boolean approval status for tool invocation requests. Rate limit enforcement occurs before tool execution, preventing resource consumption by blocked requests.

**Workflow-Aware Rate Limiting**
Rate limiting adapts to workflow phases with progressive quotas: initial configuration phases (generators, datasets) allow higher quotas for setup activities, while execution phases (orchestrator operations) implement stricter limits to prevent resource exhaustion. Interactive testing operations receive moderate quotas balancing usability with resource protection.

Session-based rate limiting tracks workflow progression and adjusts limits based on configuration completeness: users with incomplete configurations receive educational quotas encouraging proper setup, while users with complete configurations receive operational quotas supporting productive testing activities.
```

#### 5.2.3 Tool Naming and Discovery

**ViolentUTF Workflow-Aligned Tool Naming**
Tool naming follows ViolentUTF workflow patterns with phase-specific prefixes: `generator_*` tools for AI model configuration, `dataset_*` tools for data management, `converter_*` tools for prompt transformation, `scorer_*` tools for assessment configuration, and `orchestrator_*` tools for execution management. This naming convention enables workflow-aware tool discovery and phase-appropriate functionality exposure.

Workflow progression tools use action-oriented naming: `configure_generator` for setup operations, `test_generator` for validation activities, `save_generator` for persistence, and `delete_generator` for cleanup operations. Interactive tools follow conversational patterns: `send_test_message`, `clear_conversation`, and `export_chat_history` providing intuitive LLM interaction interfaces.

**FastAPI-MCP Tool Registration**
The ViolentUTFMCPServer implements zero-configuration tool registration using the FastAPI-MCP library, automatically exposing ViolentUTF API endpoints as MCP tools. The integration configuration specifies server metadata ("ViolentUTF Security Testing" name and "AI red-teaming and security testing platform" description) and implements comprehensive tool filtering.

Tool filtering includes selective operation exposure covering orchestrator lifecycle operations (create_orchestrator, start_orchestrator, stop_orchestrator), dataset management functions (upload_dataset, validate_dataset, list_datasets), result analysis capabilities (analyze_results, export_results), and system monitoring (get_system_status). Administrative and debug operations are explicitly excluded from MCP exposure for security purposes.

Custom tool metadata enhancement provides LLM-optimized descriptions with display names like "Create PyRIT Security Test" and "Start Security Test Execution", categorization for organizational clarity, risk level assessment (medium, high), and approval requirement flags for human-in-the-loop safety controls.

**Tool Naming Best Practices Implementation**
The ToolNamingStrategy implements systematic tool naming conversion from REST API patterns to action-oriented MCP tool names following best practices for LLM comprehension. The naming pattern registry maps HTTP method and endpoint combinations to descriptive tool names: POST /orchestrators becomes create_orchestrator, GET /orchestrators/{id} maps to get_orchestrator_details, PUT /orchestrators/{id}/start converts to start_orchestrator.

Dataset operations follow consistent naming patterns with POST /datasets becoming upload_security_dataset, GET /datasets mapping to list_security_datasets, and result retrieval endpoints like GET /sessions/{id}/results converting to get_test_results. Fallback naming uses method and endpoint transformation for unmapped patterns.

Tool name validation enforces MCP specification constraints including alphabetic first characters, alphanumeric characters with underscores only, and 64-character length limits for client compatibility. The validation process ensures all generated tool names meet protocol requirements and maintain consistency across the MCP interface.

### 5.3 Prompts Design

#### 5.3.1 Prompt Categories and Templates

**Red-teaming Workflow Prompts**
Red-teaming prompts provide structured templates for AI security testing scenarios with standardized argument patterns for target model specification, attack vector definition, and complexity level configuration. The prompt interface supports three primary workflow types: generate_attack_scenario for creating comprehensive testing scenarios, analyze_target_model for systematic model assessment, and assess_vulnerability for detailed security evaluation.

Prompt arguments include required target_model specification identifying the AI system under test, mandatory attack_vector definition specifying the testing approach, and optional complexity_level parameter with three levels (basic, intermediate, advanced) for scaling attack sophistication. Each prompt maintains template structures for consistent LLM interaction patterns.

**Example Red-teaming Prompt Implementation**
The RedTeamingPrompts class implements the generate_attack_scenario prompt with comprehensive template structure for AI security testing guidance. The prompt template establishes the LLM role as "Expert AI Security Researcher" and defines specific task requirements including step-by-step attack methodology development, specific test input generation, success criteria definition, defensive measure suggestions, and risk assessment with impact estimation.

The template incorporates dynamic context injection from ViolentUTF resources through the _gather_context method, providing available dataset information, previous test result summaries, and target model capability assessments. Context integration enables personalized prompt generation based on current system state and historical testing data.

Prompt formatting produces structured attack plans with clear execution phases, specific test case definitions, and measurable outcome criteria. The template uses parameter substitution for target_model, attack_vector, complexity_level, and dynamically gathered context variables to create comprehensive testing scenarios.

**Orchestrator Configuration Prompts**
The OrchestratorPrompts class implements the optimize_orchestrator_config prompt for generating optimal PyRIT orchestrator configurations based on specific testing objectives and constraints. The prompt establishes the LLM role as "PyRIT Configuration Expert" and defines comprehensive configuration requirements including attack strategy selection, dataset combination optimization, iteration and timeout parameter setting, success/failure criteria definition, and resource efficiency optimization.

The template incorporates dynamic context through _get_pyrit_components and _get_config_best_practices methods, providing current PyRIT component availability and established configuration best practices. This ensures generated configurations align with available system capabilities and proven optimization strategies.

Prompt output generates JSON configuration files with detailed parameter explanations, enabling direct orchestrator instantiation while providing clear rationale for configuration choices. The template uses parameter substitution for test_objective, target_type, resource_constraints, and dynamically gathered context about PyRIT components and best practices.

#### 5.3.2 Prompt Management and Versioning

**Template Engine with Context Injection**
The PromptTemplateEngine implements dynamic prompt rendering using Jinja2 templating with comprehensive context injection capabilities. The engine maintains context providers for violentutf_datasets (available security datasets), system_status (current system health), user_history (previous testing activities), and model_capabilities (target model information) enabling rich, context-aware prompt generation.

Prompt rendering follows a multi-stage process: template loading through _load_prompt_template, dynamic context gathering via _gather_all_context across all registered providers, argument and context merging for complete data availability, and Jinja2 template rendering with merged data for final prompt generation.

Context gathering includes error handling for provider failures, ensuring partial context availability when individual providers encounter issues. The system logs provider failures while maintaining prompt generation capability with available context data, providing resilient operation under varying system conditions.

**Prompt Version Control and A/B Testing**
The PromptVersionManager implements comprehensive version control and A/B testing for prompt optimization across different user groups and use cases. Version registration through register_prompt_version maintains complete prompt history including template content, creation timestamps, usage statistics, and performance scores for data-driven prompt improvement.

A/B testing functionality distributes users across different prompt versions through _assign_user_to_test_group, enabling comparative performance evaluation. The system automatically selects appropriate prompt versions based on active test configurations or defaults to latest stable versions for users not participating in experiments.

Performance tracking through record_prompt_performance maintains running averages of success rates and user ratings, enabling statistical analysis of prompt effectiveness. Performance metrics accumulate usage counts and calculate weighted performance scores using running average algorithms to identify optimal prompt versions for production deployment.

### 5.4 Sampling Design

#### 5.4.1 Sampling Use Cases and Implementation

**Attack Vector Generation via Sampling**

The MCP Server can implement sampling requests for generating attack vectors and analysis through LLM creativity. Attack vector generation configures LLM requests with expert security researcher context, providing structured requirements for attack technique development, methodology description, test prompt creation, outcome specification, and difficulty assessment.

Sampling configuration balances creative output with responsible constraints, using appropriate temperature settings for varied generation while maintaining focus on legitimate security testing purposes. Generated content integrates with ViolentUTF workflows through existing API endpoints for dataset creation and test execution.

**AI-Assisted Vulnerability Analysis**
The VulnerabilityAnalysis class implements the analyze_vulnerability_findings sampling request for comprehensive security assessment using LLM analytical capabilities. The analysis process begins with findings summarization through _summarize_findings, preparing structured test result data for LLM consumption including target model identification, test duration metrics, and attack strategy enumeration.

Sampling configuration optimizes for analytical precision through reduced temperature (0.3) and maximum intelligence priority (10/10) model selection. The analysis prompt requests structured vulnerability assessment including severity classification (Critical/High/Medium/Low), root cause analysis, specific remediation recommendations, risk and business impact assessment, and follow-up testing suggestions formatted as structured JSON.

Low-risk approval classification reflects the analytical nature of the operation (analysis only, no generation), streamlining the approval process while maintaining security oversight. Result processing through _process_analysis_result structures LLM output for integration with ViolentUTF reporting and remediation workflows.

#### 5.4.2 Sampling Integration with ViolentUTF Workflows

**Direct Integration with Existing Components**

Sampling requests integrate directly with the existing ViolentUTF workflow through API-mediated operations. Vulnerability analysis sampling leverages existing scorer results from `/api/v1/scorer_results` and orchestrator results from `/api/v1/orchestrators/{orchestrator_id}/results` to provide comprehensive security assessment analysis.

Attack vector generation sampling can create new dataset entries through `/api/v1/datasets` endpoints, enabling generated attack scenarios to be immediately available for testing through the standard ViolentUTF workflow. Generated content follows existing validation patterns used throughout the ViolentUTF interface.

#### 5.4.3 Context-Aware Sampling with Safety Constraints

*Enhanced with ViolentUTF Component Integration and Workflow Validation*

**Safety Constraint Framework**
The SamplingSafetyManager implements comprehensive safety validation through multi-layered filtering and content policy enforcement enhanced with ViolentUTF workflow integration. Safety filters include _filter_harmful_content for malicious content detection with converter-aware pattern recognition, _filter_personal_information for privacy protection integrated with dataset validation patterns, _filter_proprietary_data for intellectual property safeguarding aligned with ViolentUTF configuration security, and _filter_illegal_activities for compliance enforcement considering organizational security policies.

Workflow-aware content policies define request-type-specific constraints enhanced with component context: attack_generation operations limited to testing_only severity levels with workflow-validated prohibited targets (production_systems excluded through generator configuration validation, third_party_systems blocked via APISIX gateway restrictions) and required disclaimers (ethical_testing_only, controlled_environment with Dashboard compliance tracking); converter_optimization restricted to safe transformation techniques with parameter boundary validation; scorer_configuration limited to approved assessment categories with threshold safety verification; dashboard_analysis restricted to anonymized metrics with 30-day data retention and internal_only sharing requirements.

Safety validation through validate_sampling_request applies all filters sequentially with workflow state awareness, accumulating warnings and modifications while calculating safety scores informed by current component configurations. Harmful content detection uses pattern matching enhanced with ViolentUTF context for malware creation prevention, unauthorized access attempts blocking, credential theft detection, real system attack prevention, and production security bypass protection integrated with workflow validation patterns.

**Workflow-Integrated Safety Validation**
Safety validation incorporates ViolentUTF workflow state providing context-aware safety assessment. Generator-based safety validation ensures sampling requests align with configured AI model capabilities and APISIX gateway restrictions preventing requests that exceed established model boundaries or bypass security controls.

Converter safety validation analyzes transformation pipeline safety ensuring sampling-generated converter parameters maintain prompt injection prevention and avoid creating dangerous transformation sequences. Scorer safety validation prevents sampling requests from generating assessment configurations that could bypass security thresholds or create evaluation blind spots.

Dashboard safety integration ensures sampling requests for analysis and insight generation maintain data confidentiality and comply with organizational security policies while providing valuable security intelligence within approved boundaries.

**Post-Processing with Workflow Context**
Post-processing through post_process_sampling_result adds mandatory safety disclaimers with workflow-specific context, anonymizes sensitive information using patterns established in dataset configuration workflows, and includes context-specific warnings informed by current workflow state for responsible usage guidance. The post-processing system integrates with ViolentUTF session management ensuring safety compliance tracking and audit trail maintenance across workflow progression.

Workflow-aware post-processing includes component-specific safety validation ensuring sampling results integrate safely with existing configurations and maintain security boundaries established through the multi-phase workflow system. This provides comprehensive safety coverage while enabling productive security testing within approved parameters.

---

## 6. API Integration Architecture

### 6.1 FastAPI-MCP Zero-Configuration Integration

#### 6.1.1 FastAPI-MCP Implementation Foundation
**Core Integration Pattern**:
The ViolentUTF MCP integration leverages the FastAPI-MCP library to automatically expose existing ViolentUTF API endpoints as MCP tools without requiring manual tool definitions. The integration class initializes with comprehensive Keycloak authentication configuration, including OAuth proxy setup for compatibility with MCP clients that may not fully support the latest OAuth specifications.

**Authentication Configuration**:
- **Keycloak Integration**: Uses the violentutf realm with dedicated mcp-server client credentials
- **OAuth Proxy Setup**: Enables proxy endpoints to bridge compatibility gaps between Keycloak and MCP clients
- **Dynamic Client Registration**: Implements fake dynamic registration to simplify client onboarding
- **JWT Token Validation**: Custom authentication handler integrates with ViolentUTF's existing JWT manager

**Tool Filtering and Security**:
The MCP server implements strict tool filtering to expose only security-relevant endpoints while blocking administrative and debug operations. Included operations encompass orchestrator management, dataset operations, result analysis, scorer configuration, and system health monitoring. Excluded operations include destructive administrative commands and internal debugging interfaces.

**Enhanced Documentation**:
The integration configures comprehensive response documentation and full JSON schema descriptions to optimize LLM understanding of available tools and their expected inputs/outputs.

#### 6.1.2 ViolentUTF API Façade Strategy
**API-First Design Implementation**:
The API façade implements a simplified, LLM-optimized interface over the complex ViolentUTF API structure. This pattern follows API-first design principles where the MCP interface is designed for optimal LLM consumption rather than direct mapping from existing API endpoints.

**Aggregated Endpoint Strategy**:
Complex operations like orchestrator overview retrieval combine multiple parallel API calls into a single, comprehensive response. For example, retrieving orchestrator status aggregates session details, execution results, progress metrics, and performance data into a unified structure that provides complete context for LLM decision-making.

**Response Structure Optimization**:
- **Session Overview**: Core orchestrator metadata including status, type, target model, and timing information
- **Execution Progress**: Real-time completion percentages, current phase, test counts, and time estimates
- **Security Findings**: Vulnerability counts, severity breakdowns, top findings, and calculated risk scores
- **Performance Metrics**: Request rates, success rates, error rates, and resource utilization statistics

**Caching and Performance**:
The façade implements TTL-based caching for frequently accessed aggregated data to reduce API load and improve response times for LLM interactions.

**Error Handling and Resilience**:
Comprehensive error handling ensures graceful degradation when individual API calls fail, providing partial results where possible and clear error messages for complete failures.

### 6.2 OAuth 2.0 Flow with Keycloak/APISIX Integration

#### 6.2.1 OAuth Flow Implementation
**Complete OAuth 2.0 Authorization Code Flow**:
The Keycloak OAuth manager implements a comprehensive OAuth 2.0 authorization code flow specifically designed for MCP client compatibility. The implementation addresses common integration challenges between Keycloak's enterprise-grade OAuth implementation and MCP clients that may have varying levels of OAuth specification compliance.

**OAuth Configuration Management**:
The OAuth manager maintains essential configuration parameters including the Keycloak server URL, realm identifier, client credentials, and redirect URI patterns. The redirect URI is specifically configured to work with mcp-remote bridge clients that facilitate MCP connectivity for authentication-enabled deployments.

**OAuth Metadata Generation**:
The system generates MCP-compliant OAuth metadata that includes all necessary endpoints for the authorization flow. Key components include the Keycloak realm-specific issuer URL, authorization and token endpoints, and supported authentication methods. The metadata specifically supports PKCE (Proof Key for Code Exchange) with SHA256 challenge method for enhanced security.

**Supported OAuth Features**:
- **Authorization Code Flow**: Primary OAuth flow with PKCE for secure client authentication
- **Refresh Token Support**: Long-lived refresh tokens for session persistence
- **Multiple Authentication Methods**: Support for both client secret post and basic authentication
- **Scope Management**: OpenID Connect scopes plus custom violentutf-api scope for API access
- **Development Mode Flexibility**: Conditional client secret exposure for development environments

**Token Exchange Process**:
The token exchange process retrieves stored PKCE code verifiers, validates the authorization code against Keycloak, and creates dual tokens: the original Keycloak access token for SSO purposes and a ViolentUTF-compatible API token for internal API authentication. This dual-token approach enables seamless integration with existing ViolentUTF authentication while maintaining OAuth compliance.

**ViolentUTF API Token Creation**:
The system extracts user identity information from the Keycloak token payload and creates a corresponding ViolentUTF API token using the existing JWT manager. This ensures consistent user identity and role mapping across the entire platform while enabling MCP clients to authenticate against ViolentUTF APIs.

#### 6.2.2 APISIX Gateway Route Configuration
**Dynamic Route Setup for MCP Server**:
The APISIX route manager provides automated configuration of gateway routes to properly expose the ViolentUTF MCP server through the existing API gateway infrastructure. This ensures consistent authentication, monitoring, and rate limiting policies across all ViolentUTF services.

**Route Manager Configuration**:
The route manager connects to the APISIX administrative interface using configurable admin URL and API key credentials. It maintains the ability to programmatically create, modify, and delete routes to support dynamic deployment scenarios and configuration changes.

**Primary MCP Route Configuration**:
The main MCP route handles all MCP-related traffic through the `/mcp/*` path pattern with round-robin load balancing to the ViolentUTF MCP server. The route configuration includes comprehensive plugin setup for security, monitoring, and performance management.

**Integrated Security Features**:
- **CORS Support**: Cross-origin resource sharing enablement for web-based MCP clients
- **JWT Authentication**: Integration with ViolentUTF's JWT authentication system using shared secret keys and HS256 algorithm
- **Rate Limiting**: Request throttling with configurable limits (100 requests per minute by default) to prevent abuse
- **Monitoring Integration**: Prometheus metrics collection for operational visibility and performance tracking

**OAuth-Specific Route Handling**:
Separate route configurations handle OAuth-specific endpoints that require different authentication policies. OAuth callback and metadata endpoints bypass JWT authentication requirements while maintaining rate limiting and monitoring capabilities.

**Route Management Automation**:
The route manager includes automated route creation, validation, and error handling to ensure consistent gateway configuration across different deployment environments. Routes are created programmatically with proper error handling and logging for troubleshooting deployment issues.

### 6.3 API Response Transformation and Error Handling

#### 6.3.1 Response Normalization for LLM Consumption
**Standardized Response Format**:
The MCP response transformer ensures all ViolentUTF API responses are converted into a consistent, LLM-friendly format that optimizes AI model understanding and decision-making capabilities. The transformation process standardizes response structures across different API endpoints while preserving essential information and context.

**Response Transformation Process**:
The transformation system analyzes incoming API responses to extract success indicators, transform data structures for optimal LLM consumption, generate contextual metadata, identify error conditions, and produce actionable suggestions for next steps. This comprehensive processing ensures LLMs receive complete, actionable information for effective tool usage.

**Standardized Response Structure**:
All transformed responses follow a consistent format containing success status indicators, transformed data payloads, comprehensive metadata for context, detailed error information when applicable, and LLM-friendly suggestions for follow-up actions. This structure enables reliable LLM interpretation across different tool operations.

**Tool-Specific Data Transformation**:
The transformer applies tool-specific optimizations to ensure data structures match LLM expectations for different operation types. For example, orchestrator responses emphasize status and progress information, while dataset operations focus on validation results and usage statistics.

**Contextual Suggestion Generation**:
The system generates intelligent, context-aware suggestions based on tool outcomes and current system state. For successful operations, suggestions guide LLMs toward logical next steps such as starting created orchestrators or validating uploaded datasets. For failed operations, suggestions focus on troubleshooting and corrective actions.

**Error Response Handling**:
When API responses indicate errors or when transformation itself fails, the system creates standardized error responses that maintain the expected format while providing clear diagnostic information and recovery guidance.

#### 6.3.2 Enhanced Error Handling and Recovery
**MCP-Compatible Error Management**:
The MCP error handler provides comprehensive error management specifically designed for LLM consumption, transforming various error conditions into actionable insights that enable AI models to understand failures and determine appropriate recovery strategies.

**Error Classification System**:
The error handling system maintains a comprehensive mapping of HTTP status codes to semantic error types that are meaningful for LLM interpretation. This includes parameter validation errors, authentication failures, permission denials, resource conflicts, rate limiting, and various service availability issues.

**Error Type Mapping**:
- **INVALID_PARAMETERS**: Client-side parameter validation failures requiring input correction
- **AUTHENTICATION_FAILED**: Token expiration or validation failures requiring re-authentication
- **INSUFFICIENT_PERMISSIONS**: Access control violations requiring elevated privileges
- **RESOURCE_NOT_FOUND**: Missing or inaccessible resources requiring different resource selection
- **RATE_LIMIT_EXCEEDED**: Request throttling requiring delay or frequency reduction
- **Backend Service Errors**: Various upstream service failures requiring retry or fallback strategies

**Recovery Strategy Framework**:
The system implements automated recovery strategies for recoverable error conditions. Authentication failures trigger token refresh attempts, rate limiting implements backoff delays, backend unavailability suggests alternative approaches, and timeout conditions recommend retry with adjusted parameters.

**Contextual Error Suggestions**:
Error suggestions are generated based on both error type and tool context, providing LLMs with specific, actionable guidance. Authentication errors suggest token validation and refresh procedures, parameter errors provide tool-specific parameter requirements, and rate limiting errors recommend request frequency adjustments.

**Recovery Information Integration**:
When automated recovery attempts are made, the results are integrated into error responses to inform LLMs about attempted solutions and their outcomes. This enables more sophisticated LLM decision-making about whether to retry operations or attempt alternative approaches.

### 6.4 WebSocket Subscriptions for Real-Time Updates

#### 6.4.1 Real-Time Resource Updates
**WebSocket Integration for Dynamic Resources**:
The MCP WebSocket Manager implements a comprehensive subscription system for real-time updates to ViolentUTF resources. The manager maintains active subscription registries and establishes WebSocket connections to the ViolentUTF API for live data streaming.

**Subscription Management Framework**:
The system supports multiple subscription types including orchestrator progress monitoring, test result streaming, system status updates, and dataset validation notifications. Each subscription type has dedicated handlers that process incoming updates and transform them into MCP-compatible format.

**Resource Subscription Process**:
When clients subscribe to resource updates, the manager validates the resource type against supported subscription handlers, registers client callback functions for notification delivery, and initializes WebSocket connections as needed. The subscription process includes extracting resource filters and sending properly formatted subscription messages to the ViolentUTF API.

**Orchestrator Progress Update Handling**:
Real-time orchestrator progress updates are transformed into comprehensive MCP resource format containing session identification, detailed progress metrics, status information, and latest security findings. The transformation process ensures completion percentages, current execution phases, test counts, and time estimates are properly structured for LLM consumption.

**MCP Resource Format Optimization**:
All WebSocket updates are converted to standardized MCP resource structures containing URI identification, structured content payloads, and comprehensive metadata. This ensures consistent format across different update types and enables reliable LLM interpretation of real-time information.

**Client Notification Distribution**:
The system maintains subscriber lists for each resource URI and distributes updates to all registered clients through asynchronous notification mechanisms. This enables multiple MCP clients to receive simultaneous updates about the same resource changes.

### 6.5 Legacy System Integration and State Synchronization

#### 6.5.1 PyRIT/Garak Wrapper Implementation
**Bridging Legacy Tools to MCP Interface**:
The PyRIT MCP Wrapper provides seamless integration between the Model Context Protocol and existing PyRIT orchestrator infrastructure. This wrapper translates MCP tool parameters into PyRIT-compatible configurations while maintaining full access to PyRIT's security testing capabilities.

**Orchestrator Creation and Management**:
The wrapper system receives MCP tool parameters and performs comprehensive translation to PyRIT orchestrator configurations. This process includes validating configuration parameters, instantiating PyRIT orchestrator instances, and maintaining active orchestrator registries with complete lifecycle tracking.

**Configuration Translation Process**:
MCP parameters are systematically converted to PyRIT configuration format through a dedicated configuration bridge. This translation determines appropriate orchestrator types, maps target model specifications, converts attack strategy parameters, configures data source settings, and establishes execution parameters with proper timeout and retry settings.

**Legacy System Parameter Mapping**:
The configuration bridge implements sophisticated parameter mapping between MCP standardized parameters and PyRIT-specific configuration requirements. This includes determining orchestrator types based on MCP parameters, extracting model provider information, mapping attack strategies to PyRIT implementations, and configuring data source references with appropriate sampling strategies.

**State Synchronization Framework**:
The system maintains bidirectional state synchronization between PyRIT orchestrators and the ViolentUTF dashboard through comprehensive status update mechanisms. Dashboard synchronization includes orchestrator status updates, progress tracking, results summary generation, and real-time notification delivery.

**Dashboard Integration Management**:
State synchronization with the ViolentUTF dashboard occurs through authenticated API calls that update orchestrator status, progress metrics, and results summaries. The synchronization process includes error handling for failed updates, comprehensive logging for troubleshooting, and automatic retry mechanisms for transient failures.

**Error Handling and Recovery**:
The wrapper implements robust error handling for PyRIT orchestrator creation failures, configuration validation errors, and dashboard synchronization issues. Recovery mechanisms include detailed error logging, graceful degradation for non-critical failures, and comprehensive status reporting to enable effective troubleshooting.

---

## 7. Security Architecture

### 7.1 MCP-Specific Security Threats

#### 7.1.1 Creation Phase Threats
- **Server impersonation** - unique server identification
- **Code injection** - secure dependency management
- **Supply chain** - verified distribution channels

#### 7.1.2 Operation Phase Threats
- **Tool name conflicts** - unique, descriptive naming
- **Malicious code execution** - strict input validation
- **Credential theft** - secure API key management
- **Privilege escalation** - least privilege enforcement

#### 7.1.3 Update Phase Threats
- **Configuration drift** - infrastructure-as-code practices
- **Vulnerable rollbacks** - version integrity checks
- **Privilege persistence** - automated credential rotation

### 7.2 Authentication & Authorization
- **Dual Authentication Support**: Keycloak SSO for production and environment-based credentials for development
- **JWT Manager Integration**: Centralized JWT token management with `jwt_manager.get_valid_token()` for automatic refresh
- **API Token Creation**: Compatible API token generation using `jwt_manager.create_token()` for ViolentUTF API access
- **APISIX Gateway Integration**: JWT token validation through `X-API-Gateway: APISIX` headers with API key support
- **Session State Management**: Token persistence in Streamlit session state with fallback mechanisms
- **Authentication Flow**: Keycloak SSO primary with environment credentials fallback (`KEYCLOAK_USERNAME`/`KEYCLOAK_PASSWORD`)
- **Token Lifecycle**: 10-minute proactive refresh with automatic renewal and error handling

### 7.3 Data Protection Strategy
- **Encryption in transit** - TLS 1.3 for all communications
- **Sensitive data handling** - no credentials in logs
- **Data minimization** - only necessary information exposed
- **Access logging** - comprehensive audit trail

### 7.4 Secure Tool Design
- **Parameter sanitization** for all tool inputs
- **Command injection prevention** via parameterized calls
- **Resource exhaustion protection** through timeouts
- **Sandbox isolation** for orchestrator execution (planned - not yet implemented)

---

## 8. Operational Considerations

### 8.1 Deployment Strategy
- **Containerized deployment** via Docker/Kubernetes
- **Environment configuration** through sealed secrets
- **CI/CD integration** with automated security scanning
- **Blue/green deployment** for zero-downtime updates

### 8.2 Monitoring & Observability
- **MCP metrics**: Request rates, error rates, latency
- **Business metrics**: Orchestrator success rates, resource usage
- **Security metrics**: Authentication failures, suspicious patterns
- **Performance metrics**: API response times, cache hit rates

### 8.3 Scalability Architecture
- **Horizontal scaling** via load balancers
- **Caching strategy** with Redis for frequently accessed resources
- **Async processing** for long-running security tests
- **Resource pooling** for orchestrator instances

### 8.4 Maintenance Procedures
- **Rolling updates** with health checks
- **Database migrations** via ViolentUTF API versioning
- **Configuration updates** through centralized management
- **Backup/recovery** procedures for critical data

---

## 9. Future-Proofing Strategy

### 9.1 Extensibility Design
- **Plugin architecture** for new security tools
- **Modular primitives** allowing independent updates
- **Configuration-driven** tool/resource definitions
- **API versioning** strategy for backward compatibility

### 9.2 MCP Evolution Adaptability
- **Protocol abstraction** layer for MCP changes
- **Feature flags** for experimental capabilities
- **Backward compatibility** maintenance strategy
- **Migration tooling** for breaking changes

### 9.3 AI Model Evolution
- **Model-agnostic** prompt design
- **Capability detection** for client models
- **Performance monitoring** across model versions
- **Adaptive sampling** based on model characteristics

### 9.4 Ethical AI Integration
- **Transparency** in security test automation
- **Bias monitoring** in AI-generated test cases
- **Human oversight** for critical security decisions
- **Audit trails** for AI-assisted security assessments

---

## 10. Implementation Notes

### 10.1 Current Implementation Status
As of January 2025, the ViolentUTF MCP Server is in the design phase:
- **ViolentUTF REST API**: Fully implemented and operational
- **MCP Server**: Not yet implemented
- **FastAPI-MCP Integration**: Planned but not started
- **Documentation**: This design document represents the intended architecture

### 10.2 Getting Started with Implementation
When implementation begins, developers should:
1. Review this design document thoroughly
2. Set up a development environment with FastAPI-MCP
3. Start with Phase 1 (Foundation) as outlined in the roadmap
4. Coordinate with the ViolentUTF team for API access
5. Follow the security guidelines strictly

### 10.3 Contributing to MCP Development
- Code contributions should follow ViolentUTF coding standards
- All MCP primitives must have comprehensive tests
- Security review is mandatory before merging
- Documentation updates required for all changes

### 10.4 Document Maintenance
This document should be updated:
- When implementation begins (mark completed items)
- As API endpoints change
- When new security requirements emerge
- Based on testing feedback
- Following production deployment

For questions about this design, please contact the ViolentUTF development team.

---
