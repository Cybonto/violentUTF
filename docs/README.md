# ViolentUTF Documentation

Comprehensive documentation for the ViolentUTF AI red-teaming platform, covering setup, usage, API integration, and development.

## 📋 Documentation Index

### 🚀 **Getting Started**
- **[Project Structure](structure.md)** - Complete project architecture and file organization
- **[Setup Guides](../setup_macos.sh)** - Platform-specific installation instructions
- **[Cleanup and Recovery Guide](guides/Guide_Cleanup_and_Recovery.md)** - Managing deployments and backups

### 📖 **User Guides**
- **[User Guides Hub](guides/README.md)** - Complete collection of user documentation
  - [IronUTF Defense Module](guides/Guide_IronUTF.md) - AI endpoint protection
  - [Red Teaming Methodology](guides/Guide_RedTeaming_GenAIsystems.md) - Security testing framework
  - [PyRIT Scorers](guides/Guide_Scorers.md) - Response evaluation systems
  - [Simple Chat Enhancement](guides/Guide_SimpleChat_enhancementStrip.md) - MCP-powered chat tools
  - [MCP Workflows](guides/Guide_SimpleChat_mcp-workflows.md) - Natural language configuration
  - [Database Cleanup](guides/Guide_Database_Cleanup.md) - Dashboard and PyRIT data management
  - [Cleanup and Recovery](guides/Guide_Cleanup_and_Recovery.md) - Deployment management and backup/restore

### 🔧 **API Documentation**
- **[API Hub](api/README.md)** - Complete API documentation ecosystem
  - [Authentication Guide](api/authentication.md) - JWT, Keycloak SSO, and API keys
  - [Endpoints Reference](api/endpoints.md) - Complete API endpoint documentation
  - [APISIX Gateway](api/gateway.md) - Gateway configuration and routing
  - [Framework Integration](api/frameworks.md) - PyRIT and Garak integration patterns

### 📡 **MCP Integration**
- **[MCP Documentation Hub](mcp/README.md)** - Model Context Protocol implementation
  - [Architecture Overview](mcp/architecture.md) - MCP system design
  - [Configuration Guide](mcp/configuration.md) - Setup and customization
  - [Development Guide](mcp/development.md) - Extending MCP capabilities
  - [API Reference](mcp/api-reference.md) - Complete MCP API documentation
  - [Working Endpoints](mcp/mcp_endpoints_working.md) - Verified functional endpoints
  - **[MCP API Reference](mcp/api/README.md)** - Client libraries and integration APIs

### 🛠️ **Step-by-Step Guides**
- **[Program Steps](violentUTF_programSteps/)** - Detailed workflow documentation
  - [Home Page Setup](violentUTF_programSteps/0_HomePage.md)
  - [Generator Configuration](violentUTF_programSteps/2_ConfigureGenerators.md)
  - [Dataset Management](violentUTF_programSteps/3_ConfigureDatasets.md)
  - [Converter Setup](violentUTF_programSteps/4_ConfigureConverters.md)
  - [Scoring Engine](violentUTF_programSteps/5_ConfigureScoringEngine.md)
  - [Orchestrator Management](violentUTF_programSteps/6_ConfigureOrchestrators.md)
  - [Reporting System](violentUTF_programSteps/7_Reporting.md)

### 🔍 **Troubleshooting**
- **[Troubleshooting Hub](troubleshooting/)** - Common issues and solutions
  - [Docker Network Issues](troubleshooting/DOCKER_NETWORK_TROUBLESHOOTING.md)
  - [Certificate Preparation](troubleshooting/cert_preparation.md)
  - [Memory Management](troubleshooting/lesson_memoryManagement.md)
  - [MCP Connection Issues](troubleshooting/mcp-connection.md)
  - [Backup and Recovery Issues](troubleshooting/Troubleshooting_Backup_Recovery.md)
- **[MCP Troubleshooting](mcp/troubleshooting.md)** - MCP-specific issue resolution

### 🔧 **Technical Documentation**
- **[PyRIT-Garak Alignment](pyrit_garak_alignment_analysis.md)** - Framework integration analysis
- **[Simple Chat Next-Gen](simpleChat_nextgen.md)** - Advanced chat features
- **[ViolentUTF Dashboard](violentutf_Dash.md)** - Dashboard documentation
- **[PyRIT Orchestrator](pyrit-orchestrator.txt)** - Orchestrator implementation notes

## 🎯 Quick Navigation

### **For New Users**
1. **Start here**: [Project Structure](structure.md) - Understand the platform architecture
2. **Setup**: Follow [setup scripts](../setup_macos.sh) for your platform
3. **First Steps**: [User Guides](guides/README.md) for platform usage
4. **Security Testing**: [Red Teaming Guide](guides/Guide_RedTeaming_GenAIsystems.md)

### **For Developers**
1. **API Integration**: [API Documentation](api/README.md)
2. **MCP Development**: [MCP Development Guide](mcp/development.md)
3. **Testing**: [API Testing](api/frameworks.md) and [Troubleshooting](troubleshooting/)
4. **Architecture**: [MCP Architecture](mcp/architecture.md)

### **For Security Professionals**
1. **Methodology**: [Red Teaming GenAI Systems](guides/Guide_RedTeaming_GenAIsystems.md)
2. **Defense**: [IronUTF Defense Module](guides/Guide_IronUTF.md)
3. **Evaluation**: [PyRIT Scorers Guide](guides/Guide_Scorers.md)
4. **Testing Tools**: [MCP API Reference](mcp/api-reference.md)

### **For System Administrators**
1. **Setup**: [Project Structure](structure.md) and setup scripts
2. **Authentication**: [SSO with Keycloak](guides/Guide_SSO_with_KeyCloak.md)
3. **Gateway**: [APISIX Gateway Configuration](api/gateway.md)
4. **Monitoring**: [Troubleshooting Guides](troubleshooting/)
5. **Maintenance**: [Database Cleanup Guide](guides/Guide_Database_Cleanup.md)

## 🔑 Key Features Documented

### **Platform Capabilities**
- ✅ **AI Red-Teaming**: Complete PyRIT and Garak integration
- ✅ **MCP Protocol**: 23+ tools and 12+ security testing prompts
- ✅ **Defense Modules**: IronUTF for real-time AI endpoint protection
- ✅ **Authentication**: Enterprise-grade Keycloak SSO integration
- ✅ **API Gateway**: APISIX with OAuth 2.0 and rate limiting

### **Documentation Coverage**
- ✅ **Complete API Reference**: All endpoints with examples
- ✅ **MCP Implementation**: Full Model Context Protocol documentation
- ✅ **Security Methodology**: Comprehensive red-teaming framework
- ✅ **Troubleshooting**: Common issues and detailed solutions
- ✅ **Development Guides**: Extending and customizing the platform

## 🔗 External Resources

- **[PyRIT Framework](https://github.com/Azure/PyRIT)** - Microsoft's risk identification toolkit
- **[Garak Documentation](https://garak.ai/)** - LLM vulnerability scanner
- **[Model Context Protocol](https://modelcontextprotocol.io/)** - Official MCP specification
- **[APISIX Gateway](https://apisix.apache.org/)** - API gateway documentation
- **[Keycloak Documentation](https://www.keycloak.org/documentation)** - Identity management

## 📊 Documentation Statistics

- **Total Guides**: 15+ comprehensive user and developer guides
- **API Endpoints**: Complete documentation for 20+ REST endpoints
- **MCP Tools**: Documentation for 23+ specialized security testing tools
- **MCP Prompts**: 12+ security testing prompt templates
- **Troubleshooting**: 10+ detailed problem resolution guides

---

**⚠️ Security Notice**: This platform provides powerful AI security testing capabilities. Always ensure proper authorization before testing any systems.

**📋 License**: See the main project [LICENSE](../LICENSE) file for licensing information.