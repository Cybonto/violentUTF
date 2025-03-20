// Define the ViolentUTF system
system ViolentUTF {

  // Define the API Layer
  part APILayer {
    // ViolentUTFAPI wraps around Microsoft PyRIT API and potentially other related APIs
    part ViolentUTFAPI {
      // Attributes
      attribute name : String = "ViolentUTFAPI"
      attribute apiVersion : String = "v0.1"
      attribute description : String = "Wraps around Microsoft PyRIT API and other related APIs"

      // Submodules
      part PyRITIntegrationModule {
          operation integratePyRITCommands(command:String):CommandResponse
      }

      part DatasetManagement {
          operation loadDataset(datasetInfo:DatasetInfo):LoadDatasetResult
          operation transformDataset(transformation:DatasetTransformation):TransformationResult
      }

      part ConverterManagement {
          operation configureConverter(converterDetails:ConverterDetails):Boolean
          operation executeConverter(input:ConversionInput):ConversionOutput
      }

      part ScoringEngineManagement {
          operation addScorer(scorerDetails:ScorerDetails):Boolean
          operation executeScorer(input: ScoringInput):ScoringOutput
      }

      part MemoryManagement {
          operation configureMemory(memoryConfig:MemoryConfiguration):Boolean
      }

      // Operations
      operation initialize()
      operation handleRequests()
      operation integratePyRITAPI()

      // Port to communicate with StreamlitFrontend
      port apiPort {
        flowDirection : inout
        flowProperty : APIRequestResponse
      }

      // Port to receive memory configuration
      port memoryConfigPort {
        flowDirection : in
        flowProperty : MemoryConfiguration
      }

      // Relationships (explicitly stated)
      Uses: ViolentUTFAPI.PyRITIntegrationModule
      Uses: ViolentUTFAPI.DatasetManagement
      Uses: ViolentUTFAPI.ConverterManagement
      Uses: ViolentUTFAPI.ScoringEngineManagement
      Uses: ViolentUTFAPI.MemoryManagement

      // Relationship to ConfigureMemory
      Uses: ViolentUTFAPI->ConfigureMemory
    }

    // FastAPI provides RESTful API endpoints
    part FastAPI {
      // Existing attributes
      attribute name : String = "FastAPI"
      attribute description : String = "Provides RESTful API endpoints"

      // Existing operations
      operation startServer()
      operation handleAPIRequests()

      // Existing port
      port apiPort {
          flowDirection : inout
          flowProperty : APIRequestResponse
      }

      // New Sub-parts (Modules)
      part RequestHandler {
          operation handleRequest(request: APIRequest) : APIResponse
          operation parseAPIRequest(request: APIRequest):ParsedRequest
          operation executeHandler(parsedRequest:ParsedRequest):APIResponse
      }

      part APIEndpoints {
          attribute endpoints : EndpointDefinition[]
          operation defineEndpoints()
          operation defineGETResourceEndpoints()
          operation definePOSTResourceEndpoints()
          operation definePUTResourceEndpoints()
          operation definePATCHResourceEndpoints()
          operation defineDELETEResourceEndpoints()
          operation getEndpoint(path: String) : EndpointDefinition
      }

      part SecurityMiddleware {
        attribute authDomain : String = "https://auth.violentutf.com"
        attribute validationCacheTime : Integer = 300 // seconds
        operation cacheTokenValidation(token: String, validation: Boolean):Boolean
        operation verifyRBAC(userRoles:String[], requiredRoles:String[]):Boolean
        operation validateAuthentication(request: APIRequest) : Boolean
        operation enforceAuthorization(request: APIRequest) : Boolean
      }

      part OpenAPIGenerator {
          operation autoGenerateOpenAPISchema(apiEndpoints: APIEndpointList):OpenAPISpecification
      }

      part DataValidation {
          operation validateData(data: Any) : ValidationResult
      }

      part DocumentationGenerator {
          operation generateOpenAPISpec() : OpenAPISpecification
      }

      part ErrorHandler {
          operation handleError(error: Exception) : APIResponse
      }

      // Define Interfaces
      interface APIRequest {
        attribute method : String
        attribute path : String
        attribute headers : Map<String, String>
        attribute body : Any
        attribute method : HTTPMethodEnum
        attribute path : String
        attribute queryParams : Map<String, String>
        attribute headers : Map<String, String>
        attribute body : JSON
      }

      interface APIResponse {
        attribute statusCode : Integer
        attribute headers : Map<String, String>
        attribute body : ResponsePayload
      }
      
      interface CommandResponse {
        attribute success : Boolean
        attribute output : JSON
        attribute error : String?
      }

      interface DatasetInfo {
          attribute sourceURL : String?
          attribute localFile : String?
          attribute datasetType : String
      }

      interface LoadDatasetResult {
          attribute datasetID : String
          attribute entriesLoaded : Integer
          attribute validationReport : JSON
      }

      interface ConverterDetails {
          attribute converterID : String
          attribute converterType : String
          attribute parameters : JSON
      }

      interface ConversionInput {
          attribute converterID : String
          attribute inputData : JSON
      }

      interface ConversionOutput {
          attribute convertedData : JSON
          attribute executionReport : JSON?
      }

      interface ScorerDetails {
          attribute scorerID : String
          attribute scorerType : String
          attribute configuration : JSON
      }

      interface ScoringInput {
          attribute scorerID : String
          attribute responseToEvaluate : JSON
      }

      interface ScoringOutput {
          attribute score : Float
          attribute category : String
          attribute detailedReport : JSON?
      }

      interface MemoryConfiguration {
          attribute memoryType : MemoryTypeEnum
          attribute parameters : JSON
      }

      interface AuthRequestResponse {
        flowProperty authRequest : AuthRequest
        flowProperty authResponse : AuthResponse
      }

      interface LogEntry {
        attribute timestamp : DateTime
        attribute level : String
        attribute message : String
        attribute context : Map<String, Any>
      }

      interface OpenAPISpecification {
        attribute spec : String // Contains the OpenAPI JSON or YAML content
      }

      interface MetricsData {
        attribute metricName : String
        attribute metricValue : Float
      }
      interface APIRequestResponse {
          flowProperty apiRequest : APIRequest
          flowProperty apiResponse : APIResponse
      }

      interface ValidationResult {
          attribute isValid : Boolean
          attribute errors : String[]
      }

      interface EndpointDefinition {
          attribute path : String
          attribute method : String
          attribute handler : Function
      }

      // Additional Ports
      port authPort {
          flowDirection : out
          flowProperty : AuthRequestResponse
      }

      port loggingPort {
          flowDirection : out
          flowProperty : LogEntry
      }

      // Relationships
      Uses: FastAPI.RequestHandler
      Uses: FastAPI.APIEndpoints
      Uses: FastAPI.SecurityMiddleware
      Uses: FastAPI.DataValidation
      Uses: FastAPI.DocumentationGenerator
      Uses: FastAPI.ErrorHandler
      Uses: FastAPI.RequestHandler
      Uses: FastAPI.APIEndpoints
      Uses: FastAPI.SecurityMiddleware
      Uses: FastAPI.OpenAPIGenerator

      enum HTTPMethodEnum {GET, POST, PUT, PATCH, DELETE}
      enum MemoryTypeEnum {InMemory, DuckDB, AzureSQL}
      datatype JSON {data: String} // simplified representation

    }

    // KongGateway serves as API gateway for routing, authentication, rate limiting
    part KongGateway {

      // Existing attributes
      attribute name : String = "KongGateway"
      attribute description : String = "Serves as API gateway for routing, authentication, rate limiting"

      // Existing operations
      operation handleRouting()
      operation enforcePolicies()

      // Existing ports
      port apiPort {
          flowDirection : inout
          flowProperty : APIRequestResponse
      }
      port authPort {
          flowDirection : out
          flowProperty : AuthRequestResponse
      }

      // New Sub-parts (Plugins)
      part RoutingEngine {
          operation routeRequest(request: APIRequest) : APIResponse
          operation defineRoute(routeDefinition:RouteDefinition):Boolean
          operation updateRoute(routeId:String, updatedDefinition:RouteDefinition):Boolean
      }

      part AuthenticationPlugin {
          operation validateToken(token: String) : Boolean
          attribute keycloakURL : String = "https://auth.violentutf.com/auth/realms/violentutf"
          operation validateOIDCToken(oidcToken:String):Boolean
      }

      part RateLimitingPlugin {
          operation checkRateLimit(clientID: String) : Boolean
      }

      part RequestTransformerPlugin {
          operation transformRequest(request: APIRequest) : APIRequest
      }

      part ResponseTransformerPlugin {
          operation transformResponse(response: APIResponse) : APIResponse
      }

      part LoggingPlugin {
          operation logRequest(request: APIRequest)
          operation logResponse(response: APIResponse)
          operation captureRequest(request:APIRequest):LogEntry
          operation captureAPIErrors(errorDetails:APIErrorInfo):LogEntry
      }

      part Monitoring {
          operation collectMetrics()
          operation healthCheck() : Boolean
      }

      // Define Interfaces
      interface APIRequestResponse {
          flowProperty apiRequest : APIRequest
          flowProperty apiResponse : APIResponse
      }

      interface MetricsData {
          attribute metricName : String
          attribute metricValue : Float
      }

      // Additional Ports
      port monitoringPort {
          flowDirection : out
          flowProperty : MetricsData
      }

      // Relationships
      Uses: KongGateway.RoutingEngine
      Uses: KongGateway.AuthenticationPlugin
      Uses: KongGateway.RateLimitingPlugin
      Uses: KongGateway.RequestTransformerPlugin
      Uses: KongGateway.ResponseTransformerPlugin
      Uses: KongGateway.LoggingPlugin
      Uses: KongGateway.Monitoring
    }

    port apiPort {
      flowDirection : bidirectional
      flowProperty : APIInteractionPackage
    }

    interface APIInteractionPackage {
      flowProperty request:APIRequest
      flowProperty response:APIResponse
      flowProperty authRequest:AuthRequest
      flowProperty authResponse:AuthResponse
    }
  }

  // Define the Database Layer
  part DatabaseLayer {

    // Abstract Database block
    block Database {
      // Attributes common to all databases
      attribute connectionString : String

      // Operations
      operation connect()
      operation disconnect()
      operation executeQuery(query : String)
    }

    // DuckDB extends Database
    block DuckDB extends Database {
      attribute databaseFile : String
    }

    // AzureDB extends Database
    block AzureDB extends Database {
      attribute azureConnectionString : String
    }

    // FileSystem for file-based data storage
    block FileSystem {
      attribute rootDirectory : String

      // Operations
      operation readFile(filePath : String)
      operation writeFile(filePath : String, data : String)

      // Port for file interactions
      port filePort {
          flowDirection : inout
          flowProperty : FileTransfer
      }
    }
  }

  // Define the Streamlit Frontend
  part StreamlitFrontend {
    // Interface for User Actions
    interface UserAction {
      attribute actionType : String
      attribute actionData : Any
    }

    // Port for User Actions in HomePage
    port userActionPort {
      flowDirection : inout
      flowProperty : UserAction
    }
    // Sub-parts representing different pages and functionalities
    part HomePage {
        attribute name : String = "HomePage"
        attribute description : String = "The main entry point of the Violent UTF application"

        // Operations
        operation displayHomePage()
        operation handleUserLogin()
        operation handleUserLogout()
        operation displayAvailableApps()
        operation loadParameterFile(file: File)
        operation startApplication()

        // Ports for interaction
        port apiPort {
          flowDirection : inout
          flowProperty : APIRequestResponse
        }
        port authPort {
          flowDirection : inout
          flowProperty : AuthRequestResponse
        }
        port userActionPort {
          flowDirection : inout
          flowProperty : UserAction
        }

        // Interfaces
        interface UserAction {
          attribute actionType : String
          attribute actionData : Any
        }

        // Relationships
        Uses: HomePage->APILayer.ViolentUTFAPI
        Uses: HomePage->AuthenticationAuthorizationLayer.Keycloak

        // Constraints
        constraint HomePage_SecurityConstraint {
          text = "HomePage shall only display applications to authenticated users."
          constrain : handleUserLogin
        }
      }
    
    part WelcomePage {
        attribute name : String = "WelcomePage"
        attribute description : String = "The initial page displayed to the user upon accessing the Violent UTF application."

        // Operations
        operation displayWelcomePage()
        operation loadParameterFile(file : File)
        operation initializeSession(parameters : Parameters)
        operation proceedToNextStep()
        operation handleFileUpload(file : File)
        operation handleFileSelection(fileName : String)
        operation displayError(message : String)
        operation displayLinks()
        operation checkExistingParameterFiles() : String[]

        // Ports
        // Port to communicate with the ViolentUTFAPI for parameter loading
        port apiPort {
            flowDirection : inout
            flowProperty : APIRequestResponse
        }

        // Port to interact with the FileSystem to read parameter files
        port fileSystemPort {
            flowDirection : inout
            flowProperty : FileTransfer
        }

        // Interfaces
        interface FileTransfer {
            flowProperty uploadedFile : File
            flowProperty fileContent : String
        }

        // Relationships
        Uses: WelcomePage->APILayer.ViolentUTFAPI
        Uses: WelcomePage->DatabaseLayer.FileSystem

        // Constraints
        constraint WelcomePage_LoadParameterFileConstraint {
            text = "WelcomePage shall only accept valid YAML parameter files."
            constrain : loadParameterFile
        }
    }

    part ConfigureMemory {
      attribute name : String = "ConfigureMemory"
      attribute memoryType : String
      attribute memoryParameters : Map<String, String>

      // Operations
      operation displayMemoryOptions()
      operation captureMemoryParameters()
      operation validateMemoryConfiguration()
      operation initializeMemory()

      // Interface for memory configuration data
      interface MemoryConfiguration {
        attribute memoryType : String
        attribute memoryParameters : Map<String, String>
      }

      // Port to output memory configuration to other parts
      port memoryConfigPort {
        flowDirection : out
        flowProperty : MemoryConfiguration
      }

      // Relationships to other parts
      Uses: ConfigureMemory->APILayer.ViolentUTFAPI
      Uses: ConfigureMemory->DatabaseLayer
      Uses: ConfigureMemory->FileSystem
    }  

    part SetPromptTarget {
        attribute name : String = "SetPromptTarget"

        // New attributes
        attribute existingTargets : TargetDefinition[]
        attribute selectedInteractionType : String
        attribute selectedProvider : String
        attribute targetConfiguration : TargetConfiguration

        // New operations
        operation displayExistingTargets()
        operation addNewTarget()
        operation deleteExistingTarget(targetID : String)
        operation selectInteractionType(type : String)
        operation selectProvider(provider : String)
        operation configureTargetParameters(parameters : Map<String, Any>)
        operation saveConfiguration()
        operation testConnection(testPrompt : String) : TestResult

        // Ports
        port apiPort {
            flowDirection : inout
            flowProperty : APIRequestResponse
        }

        port fileSystemPort {
            flowDirection : inout
            flowProperty : FileTransfer
        }

        // Interfaces
        interface TargetDefinition {
            attribute targetID : String
            attribute name : String
            attribute description : String
            attribute interactionType : String
            attribute provider : String
            attribute parameters : Map<String, Any>
        }

        interface TargetConfiguration {
            attribute provider : String
            attribute parameters : Map<String, Any>
        }

        interface TestResult {
            attribute success : Boolean
            attribute message : String
            attribute response : String
        }

        // Relationships
        Uses: SetPromptTarget->APILayer.ViolentUTFAPI
        Uses: SetPromptTarget->DatabaseLayer.FileSystem

        // Constraints
        constraint SetPromptTarget_MustHaveValidConfiguration {
            text = "SetPromptTarget shall validate target configurations before saving."
            constrain : saveConfiguration
        }
    }
    
    part ConfigureDatasets {
      attribute name : String = "ConfigureDatasets"

      // Sub-parts representing different functionalities
      part ChooseDatasetSource {
        attribute selectedSourceType : String

        // Operations
        operation displayOptions()
        operation captureUserSelection()
      }

      part UploadLocalDataset {
        attribute uploadedFile : File

        // Operations
        operation uploadFile()
        operation parseFile()
        operation validateFile()
        operation handleErrors()
      }

      part FetchOnlineDataset {
        attribute datasetUrl : String

        // Operations
        operation enterDatasetUrl()
        operation fetchDataset()
        operation parseDataset()
        operation validateDataset()
        operation handleErrors()
      }

      part CombineDatasets {
        attribute selectedDatasets : Dataset[]

        // Operations
        operation selectDatasets()
        operation combineDatasets()
        operation removeDuplicates()
        operation confirmCombination()
      }

      part TransformDataset {
        attribute selectedDataset : Dataset
        attribute transformationMethod : String
        attribute selectedTemplate : Template
        attribute newTemplate : Template

        // Operations
        operation selectDataset()
        operation selectTransformationMethod()
        operation selectOrCreateTemplate()
        operation validateTemplate()
        operation applyTemplate()
        operation previewTemplate()
        operation handleErrors()
      }

      part DatasetPreviewer {
        attribute dataset : Dataset

        // Operations
        operation displayPreview()
        operation mapFields()
        operation createAndSaveDataset()
        operation displayStatistics()
      }

      part FinalizeConfiguration {
        // Operations
        operation summarizeConfiguration()
        operation proceedToNextStep()
        operation configureAnotherDataset()
      }

      // Ports for interaction with other layers
      port apiPort {
        flowDirection : inout
        flowProperty : APIRequestResponse
      }

      port fileSystemPort {
        flowDirection : inout
        flowProperty : FileTransfer
      }

      port databasePort {
        flowDirection : inout
        flowProperty : DatabaseQuery
      }

      // Interfaces
      interface FileTransfer {
        flowProperty uploadedFile : File
        flowProperty fileContent : String
      }

      interface DatabaseQuery {
        flowProperty query : String
        flowProperty result : Any
      }

      interface Dataset {
        attribute name : String
        attribute data : Any
        attribute schema : Schema
        attribute statistics : Statistics
      }

      interface Template {
        attribute name : String
        attribute content : String
        attribute language : String
      }

      interface Schema {
        attribute fields : FieldDefinition[]
      }

      interface FieldDefinition {
        attribute fieldName : String
        attribute fieldType : String
        attribute isRequired : Boolean
      }

      interface Statistics {
        attribute numberOfRecords : Integer
        attribute numberOfFields : Integer
        attribute dataSize : Integer // in bytes
      }
      // Relationships to other parts
      Uses: ConfigureDatasets->APILayer.ViolentUTFAPI
      Uses: ConfigureDatasets->DatabaseLayer
      Uses: ConfigureDatasets->DatabaseLayer.FileSystem

      // Constraints
      constraint ConfigureDatasets_InputValidationConstraint {
        text = "ConfigureDatasets shall validate and sanitize all user inputs to prevent security vulnerabilities."
        constrain : UploadLocalDataset.validateFile
        constrain : FetchOnlineDataset.validateDataset
        constrain : TransformDataset.validateTemplate
      }

      constraint ConfigureDatasets_ErrorHandlingConstraint {
        text = "ConfigureDatasets shall handle errors gracefully and provide meaningful feedback to the user."
        constrain : UploadLocalDataset.handleErrors
        constrain : FetchOnlineDataset.handleErrors
        constrain : TransformDataset.handleErrors
      }
    }
    
    part ConfigureConverters {
      attribute name : String = "ConfigureConverters"

      // Sub-parts representing different functionalities
      part SelectConverterCategory {
        attribute selectedCategory : String

        // Operations
        operation displayCategories()
        operation selectCategory(category : String)
      }

      part SelectConverterClass {
        attribute selectedClass : String

        // Operations
        operation displayClasses(category : String)
        operation selectClass(converterClass : String)
      }

      part ConfigureConverterParameters {
        attribute converterParameters : Map<String, Any>

        // Operations
        operation displayParameters(converterClass : String)
        operation captureParameterValues(parameters : Map<String, Any>)
        operation validateParameters()
      }

      part AddConverter {
        // Operations
        operation addConverterToPipeline(converterClass : String, parameters : Map<String, Any>)
      }

      part ManageConverters {
        attribute converterPipeline : ConverterDefinition[]

        // Operations
        operation displayConverterPipeline()
        operation removeConverter(converterID : String)
        operation testConverter(converterID : String, testInput : String) : TestResult
        operation reorderConverters(converterOrder : Integer[])
      }

      // Ports
      port apiPort {
        flowDirection : inout
        flowProperty : APIRequestResponse
      }

      port fileSystemPort {
        flowDirection : inout
        flowProperty : FileTransfer
      }

      // Interfaces
      interface ConverterDefinition {
        attribute converterID : String
        attribute converterClass : String
        attribute parameters : Map<String, Any>
      }

      interface TestResult {
        attribute success : Boolean
        attribute message : String
        attribute output : String
      }

      // Relationships to other parts
      Uses: ConfigureConverters->APILayer.ViolentUTFAPI
      Uses: ConfigureConverters->DatabaseLayer.FileSystem
      Uses: StreamlitFrontend.ConfigureConverters->APILayer.ViolentUTFAPI
      Uses: StreamlitFrontend.ConfigureConverters->DatabaseLayer
      Uses: StreamlitFrontend.ConfigureConverters->DatabaseLayer.FileSystem

      // Constraints
      constraint ConfigureConverters_ValidConfiguration {
        text = "ConfigureConverters shall validate converter configurations before adding to the pipeline."
        constrain : AddConverter.addConverterToPipeline
        constrain : ConfigureConverterParameters.validateParameters
      }

      // Operations
      operation displayConverterConfiguration()
      operation proceedToNextStep()
    }

  part ConfigureScoring {
    attribute name : String = "ConfigureScoring"
    attribute description : String = "Handles the configuration of scoring engines"

    // Sub-parts representing different functionalities
    part ScorerSelection {
      // Attributes
      attribute selectedScorerType : String
      attribute availableScorers : ScorerDefinition[]

      // Operations
      operation displayScorerOptions()
      operation selectScorerType(type: String)
    }

    part ScorerConfiguration {
      // Attributes
      attribute scorerParameters : Map<String, Any>
      attribute configuredScorers : ConfiguredScorer[]

      // Operations
      operation configureScorerParameters(parameters: Map<String, Any>)
      operation validateScorerConfiguration()
      operation saveScorerConfiguration()
      operation testScorer(scorerID: String, testData: Any) : TestResult
      operation removeScorer(scorerID: String)
    }

    part ScorerTesting {
      // Attributes
      attribute testData : Any
      attribute testResults : TestResult

      // Operations
      operation inputTestData(data: Any)
      operation runTest(scorerID: String)
      operation displayTestResults()
    }

    // Ports for interaction with other layers
    port apiPort {
      flowDirection : inout
      flowProperty : APIRequestResponse
    }

    port fileSystemPort {
      flowDirection : inout
      flowProperty : FileTransfer
    }

    // Interfaces
    interface ScorerDefinition {
      attribute scorerID : String
      attribute name : String
      attribute description : String
      attribute parameters : ParameterDefinition[]
      attribute scorerClass : String
    }

    interface ParameterDefinition {
      attribute parameterName : String
      attribute parameterType : String
      attribute isRequired : Boolean
      attribute defaultValue : Any
    }

    interface ConfiguredScorer {
      attribute scorerID : String
      attribute name : String
      attribute scorerType : String
      attribute parameters : Map<String, Any>
      attribute description : String
    }

    interface TestResult {
      attribute success : Boolean
      attribute scoreValue : Any
      attribute message : String
      attribute detailedResults : Any
    }

    // Relationships to other parts
    Uses: ConfigureScoring->APILayer.ViolentUTFAPI
    Uses: ConfigureScoring->DatabaseLayer
    Uses: ConfigureScoring->DatabaseLayer.FileSystem

    // Constraints
    constraint ConfigureScoring_ValidScorerConfig {
      text = "ConfigureScoring shall validate the scorer configurations before saving."
      constrain : ScorerConfiguration.validateScorerConfiguration
    }

    constraint ConfigureScoring_MaxScorers {
      text = "The number of configured scorers shall not exceed MaxNumberOfScorers."
      constrain : ScorerConfiguration.saveScorerConfiguration
      constrain : MaxNumberOfScorers
    }
  }

  part Reporting {

    attribute name : String = "Reporting"

    // Sub-parts

    part ReportConfiguration {
      // Attributes
      attribute generateReport : Boolean = true
      attribute reportFormat : String = "HTML" // Options: "HTML", "PDF", "Markdown"
      attribute includeInteractiveVisualizations : Boolean = true
      attribute reportTemplate : String = "templates/default_report_template.html" // Path to the template file
      attribute outputDirectory : String = "reports/"
      attribute additionalOptions : Map<String, Any>

      // Operations
      operation displayConfigurationOptions()
      operation captureUserPreferences()
      operation validateConfiguration()
      operation saveConfiguration()
    }

    part DataExtractor {
      // Operations
      operation extractData()
      operation retrieveConversationData()
      operation useConversationAnalytics()
    }

    part DataTransformer {
      // Operations
      operation transformData()
      operation convertToDataFrames()
      operation filterAndGroupData()
      operation prepareDataForVisualization()
    }

    part Visualizer {
      // Operations
      operation generateVisualizations()
      operation createCharts()
      operation saveFigures()
    }

    part ReportGenerator {
      // Operations
      operation generateReport()
      operation renderTemplate()
      operation exportReport()
    }

    part TemplateManager {
      // Operations
      operation loadTemplate(templatePath : String)
      operation selectTemplate()
      operation handleUserUploadedTemplate(file : File)
      operation manageTemplates()
    }

    part Exporter {
      // Operations
      operation exportToHTML()
      operation exportToPDF()
      operation exportToMarkdown()
    }

    // Ports for communication

    port apiPort {
      flowDirection : inout
      flowProperty : APIRequestResponse
    }

    port fileSystemPort {
      flowDirection : inout
      flowProperty : FileTransfer
    }

    port databasePort {
      flowDirection : inout
      flowProperty : DatabaseQuery
    }

    // Interfaces

    interface ReportConfigurationData {
      attribute generateReport : Boolean
      attribute reportFormat : String
      attribute includeInteractiveVisualizations : Boolean
      attribute reportTemplate : String
      attribute outputDirectory : String
      attribute additionalOptions : Map<String, Any>
    }

    interface Data {
      attribute conversationData : Any
      attribute analysisResults : Any
      attribute visualizations : Any
    }

    interface Report {
      attribute content : String
      attribute format : String
    }

    // Relationships

    Uses: Reporting.ReportConfiguration
    Uses: Reporting.DataExtractor
    Uses: Reporting.DataTransformer
    Uses: Reporting.Visualizer
    Uses: Reporting.ReportGenerator
    Uses: Reporting.TemplateManager
    Uses: Reporting.Exporter

    // Relationships with other parts

    // Reporting uses ViolentUTFAPI
    Uses: Reporting->APILayer.ViolentUTFAPI

    // Reporting uses DatabaseLayer
    Uses: Reporting->DatabaseLayer

    // Reporting uses FileSystem
    Uses: Reporting->DatabaseLayer.FileSystem

    // Constraints and Parameters can be added as needed
  }

    // Port to communicate with APILayer
    port apiPort {
      flowDirection : inout
      flowProperty : APIRequestResponse
    }

    // Port for authentication with AuthenticationAuthorizationLayer
    port authPort {
      flowDirection : inout
      flowProperty : AuthRequestResponse
    }

    port fileSystemPort {
      flowDirection : inout
      flowProperty : FileTransfer
    }
  }

  // Define Logging
  part Logging {
    attribute logLevel : String
    operation log(message : String, level : String)
  }

  // Define the Authentication and Authorization Layer
  part AuthenticationAuthorizationLayer {
    // Keycloak for centralized identity management
    part Keycloak {
      // Attributes
      attribute name : String = "Keycloak"
      attribute version : String = "15.0.2"
      attribute baseUrl : String = "https://auth.violentutf.com"

      // Operations
      operation authenticateUser(username : String, password : String) : Boolean
      operation authorizeRequest(request : AuthRequest) : Boolean
      operation manageUsers()
      operation manageRoles()
      operation issueTokens(request : TokenRequest) : TokenResponse

      // Ports
      port authPort {
        flowDirection : inout
        flowProperty : AuthRequestResponse
      }

      // Port for administration interface
      port adminPort {
        flowDirection : inout
        flowProperty : AdminRequestResponse
      }
    }

    // StreamlitAuthentication for frontend authentication
    part StreamlitAuthentication extends OIDCClient {
      attribute name : String = "StreamlitAuthentication"
      attribute redirectURI : String = "https://app.violentutf.com/oauth2callback"

      // Operations
      operation initiateLogin()
      operation handleCallback(authCode : String)
      operation getUserInfo() : UserInfo

      // Ports
      port authPort {
        flowDirection : inout
        flowProperty : AuthRequestResponse
      }
    }

    // KongGatewayAuthPlugin for API authentication and authorization
    part KongGatewayAuthPlugin extends OIDCClient {
      attribute name : String = "KongGatewayAuthPlugin"

      // Operations
      operation validateJWT(token : String) : Boolean
      operation enforceAccessControl(request : APIRequest) : Boolean

      // Ports
      port authPort {
        flowDirection : inout
        flowProperty : AuthRequestResponse
      }
    }

    // Define Interfaces

    interface AuthRequestResponse {
      // Flow properties for authentication
      flowProperty authRequest : AuthRequest
      flowProperty authResponse : AuthResponse
    }

    interface AdminRequestResponse {
      // Flow properties for administration
      flowProperty adminRequest : AdminRequest
      flowProperty adminResponse : AdminResponse
    }

    interface TokenExchange {
      // Flow properties for token exchange
      flowProperty tokenRequest : TokenRequest
      flowProperty tokenResponse : TokenResponse
    }

    interface ScorerDefinition {
      attribute scorerID : String
      attribute name : String
      attribute description : String
      attribute parameters : ParameterDefinition[]
      attribute scorerClass : String
    }

    interface ParameterDefinition {
      attribute parameterName : String
      attribute parameterType : String
      attribute isRequired : Boolean
      attribute defaultValue : Any
    }

    interface ConfiguredScorer {
      attribute scorerID : String
      attribute name : String
      attribute scorerType : String
      attribute parameters : Map<String, Any>
      attribute description : String
    }

    interface TestResult {
      attribute success : Boolean
      attribute scoreValue : Any
      attribute message : String
      attribute detailedResults : Any
    }

    // Define Value Types for Tokens and Requests

    value type AuthRequest {
      attribute clientID : String
      attribute redirectURI : String
      attribute responseType : String
      attribute scope : String
      attribute state : String
    }

    value type AuthResponse {
      attribute code : String // Authorization code
      attribute state : String
      attribute error : String
    }

    value type TokenRequest {
      attribute grantType : String
      attribute code : String
      attribute redirectURI : String
      attribute clientID : String
      attribute clientSecret : String
    }

    value type TokenResponse {
      attribute accessToken : String
      attribute tokenType : String
      attribute expiresIn : Integer
      attribute refreshToken : String
      attribute scope : String
      attribute idToken : String
    }

    value type AdminRequest {
      attribute action : String
      attribute parameters : Map<String, String>
    }

    value type AdminResponse {
      attribute status : String
      attribute message : String
    }

    value type UserInfo {
      attribute userID : String
      attribute username : String
      attribute email : String
      attribute roles : String[]
      attribute groups : String[]
    }

    // Relationships among parts within AuthenticationAuthorizationLayer
    dependencies {
      // StreamlitAuthentication uses Keycloak for authentication
      Uses: StreamlitAuthentication->Keycloak

      // KongGatewayAuthPlugin uses Keycloak for token validation
      Uses: KongGatewayAuthPlugin->Keycloak

      // Keycloak uses Logging for auditing
      Uses: Keycloak->Logging
    }

    // Connectors within AuthenticationAuthorizationLayer
    connectors {
      // Connect StreamlitAuthentication to Keycloak
      connector streamlitAuthToKeycloak {
        end1 : StreamlitAuthentication.authPort
        end2 : Keycloak.authPort
      }

      // Connect KongGatewayAuthPlugin to Keycloak
      connector kongPluginToKeycloak {
        end1 : KongGatewayAuthPlugin.authPort
        end2 : Keycloak.authPort
      }
      
    }
  }

  // Define Test Module
  part TestModule {
    attribute name : String = "TestModule"
    operation runTests()
  }

  // Define external PyRITAPI block
  external block PyRITAPI {
    attribute name : String = "PyRITAPI"

    // Operations
    operation initialize()
    operation executeCommand(command : String)

    // Port for communication
    port apiPort {
      flowDirection : inout
      flowProperty : APIRequestResponse
    }
  }

  // Define Dependencies and Usages
  dependencies {

    // Dependencies for FastAPI
    Uses: FastAPI.SecurityMiddleware->AuthenticationAuthorizationLayer.KongGatewayAuthPlugin
    Uses: FastAPI.ErrorHandler->Logging

    // Dependencies for KongGateway
    Uses: KongGateway.AuthenticationPlugin->AuthenticationAuthorizationLayer.Keycloak
    Uses: KongGateway.LoggingPlugin->Logging

    // StreamlitFrontend uses StreamlitAuthentication
    Uses: StreamlitFrontend->AuthenticationAuthorizationLayer.StreamlitAuthentication

    // APILayer.KongGateway uses KongGatewayAuthPlugin
    Uses: APILayer.KongGateway->AuthenticationAuthorizationLayer.KongGatewayAuthPlugin

    // Update Logging dependencies
    Uses: AuthenticationAuthorizationLayer.StreamlitAuthentication->Logging
    Uses: AuthenticationAuthorizationLayer.KongGatewayAuthPlugin->Logging
    Uses: AuthenticationAuthorizationLayer.Keycloak->Logging

    // StreamlitFrontend uses ViolentUTFAPI
    Uses: StreamlitFrontend->APILayer.ViolentUTFAPI

    // StreamlitFrontend uses StreamlitAuthentication
    Uses: StreamlitFrontend->AuthenticationAuthorizationLayer.StreamlitAuthentication

    // StreamlitFrontend uses Logging
    Uses: StreamlitFrontend->Logging

    // APILayer.ViolentUTFAPI uses PyRITAPI
    Uses: APILayer.ViolentUTFAPI->PyRITAPI

    // APILayer.ViolentUTFAPI uses DatabaseLayer
    Uses: APILayer.ViolentUTFAPI->DatabaseLayer

    // APILayer.FastAPI uses Logging
    Uses: APILayer.FastAPI->Logging

    // APILayer.KongGateway uses Keycloak
    Uses: APILayer.KongGateway->AuthenticationAuthorizationLayer.Keycloak

    // APILayer.KongGateway uses Logging
    Uses: APILayer.KongGateway->Logging

    // AuthenticationAuthorizationLayer.StreamlitAuthentication uses Keycloak
    Uses: AuthenticationAuthorizationLayer.StreamlitAuthentication->AuthenticationAuthorizationLayer.Keycloak

    // AuthenticationAuthorizationLayer.StreamlitAuthentication uses Logging
    Uses: AuthenticationAuthorizationLayer.StreamlitAuthentication->Logging

    // DatabaseLayer uses Logging
    Uses: DatabaseLayer->Logging

    // TestModule tests various components
    Tests: TestModule->StreamlitFrontend
    Tests: TestModule->APILayer
    Tests: TestModule->DatabaseLayer
    Tests: TestModule->Logging
    Tests: TestModule->AuthenticationAuthorizationLayer

    // HomePage uses ViolentUTFAPI
    Uses: StreamlitFrontend.HomePage->APILayer.ViolentUTFAPI

    // HomePage uses StreamlitAuthentication (which interacts with Keycloak)
    Uses: StreamlitFrontend.HomePage->AuthenticationAuthorizationLayer.StreamlitAuthentication

    // HomePage uses Logging for event logging
    Uses: StreamlitFrontend.HomePage->Logging

    // WelcomePage uses ViolentUTFAPI
    Uses: StreamlitFrontend.WelcomePage->APILayer.ViolentUTFAPI

    // WelcomePage uses FileSystem
    Uses: StreamlitFrontend.WelcomePage->DatabaseLayer.FileSystem

    // Ensure Logging is used by WelcomePage for event logging
    Uses: StreamlitFrontend.WelcomePage->Logging

    Uses: StreamlitFrontend.SetPromptTarget->APILayer.ViolentUTFAPI
    Uses: StreamlitFrontend.SetPromptTarget->DatabaseLayer.FileSystem
  }

  // Define Connectors
  connectors {

    // Connect StreamlitFrontend to StreamlitAuthentication
    connector frontendToStreamlitAuth {
      end1 : StreamlitFrontend.authPort
      end2 : AuthenticationAuthorizationLayer.StreamlitAuthentication.authPort
    }

    // Connect APILayer.KongGateway to KongGatewayAuthPlugin
    connector kongToKongAuthPlugin {
      end1 : APILayer.KongGateway.authPort
      end2 : AuthenticationAuthorizationLayer.KongGatewayAuthPlugin.authPort
    }

    // Connect StreamlitFrontend to ViolentUTFAPI
    connector frontendToAPIconnection {
      end1 : StreamlitFrontend.apiPort
      end2 : APILayer.ViolentUTFAPI.apiPort
    }

    // Connect StreamlitFrontend to StreamlitAuthentication
    connector frontendToAuthConnection {
      end1 : StreamlitFrontend.authPort
      end2 : AuthenticationAuthorizationLayer.StreamlitAuthentication.authPort
    }

    // Connect StreamlitAuthentication to Keycloak
    connector authToKeycloakConnection {
      end1 : AuthenticationAuthorizationLayer.StreamlitAuthentication.authPort
      end2 : AuthenticationAuthorizationLayer.Keycloak.authPort
    }

    // Connect KongGateway to Keycloak
    connector kongToKeycloakConnection {
      end1 : APILayer.KongGateway.authPort
      end2 : AuthenticationAuthorizationLayer.Keycloak.authPort
    }

    // Connect ViolentUTFAPI to PyRITAPI
    connector violentUTFAPItoPyRITAPI {
      end1 : APILayer.ViolentUTFAPI.apiPort
      end2 : PyRITAPI.apiPort
    }

    // Connect ViolentUTFAPI to DatabaseLayer
    connector violentUTFAPItoDatabaseLayer {
      end1 : APILayer.ViolentUTFAPI
      end2 : DatabaseLayer
    }

    // Connect FastAPI to KongGateway
    connector fastAPItoKongGateway {
      end1 : APILayer.FastAPI.apiPort
      end2 : APILayer.KongGateway.apiPort
    }

    // Connect FastAPI to Authentication and Logging
    connector fastAPItoAuth {
      end1 : FastAPI.authPort
      end2 : AuthenticationAuthorizationLayer.KongGatewayAuthPlugin.authPort
    }

    connector fastAPItoLogging {
      end1 : FastAPI.loggingPort
      end2 : Logging.loggingPort
    }

    // Connect KongGateway to Monitoring
    connector kongGatewayToMonitoring {
      end1 : KongGateway.monitoringPort
      end2 : Monitoring.monitoringPort
    }

    // Connect HomePage to ViolentUTFAPI
    connector homePageToAPIconnection {
      end1 : StreamlitFrontend.HomePage.apiPort
      end2 : APILayer.ViolentUTFAPI.apiPort
    }

    // Connect HomePage to Keycloak via StreamlitAuthentication
    connector homePageToAuthConnection {
      end1 : StreamlitFrontend.HomePage.authPort
      end2 : AuthenticationAuthorizationLayer.StreamlitAuthentication.authPort
    }

    // Connect WelcomePage to ViolentUTFAPI
    connector welcomePageToAPIconnection {
        end1 : StreamlitFrontend.WelcomePage.apiPort
        end2 : APILayer.ViolentUTFAPI.apiPort
    }

    // Connect WelcomePage to FileSystem
    connector welcomePageToFileSystemConnection {
        end1 : StreamlitFrontend.WelcomePage.fileSystemPort
        end2 : DatabaseLayer.FileSystem.filePort
    }

    connector configureMemoryToViolentUTFAPI {
      end1 : StreamlitFrontend.ConfigureMemory.memoryConfigPort
      end2 : APILayer.ViolentUTFAPI.memoryConfigPort
    }

    connector setPromptTargetToAPIconnection {
        end1 : StreamlitFrontend.SetPromptTarget.apiPort
        end2 : APILayer.ViolentUTFAPI.apiPort
    }

    connector setPromptTargetToFileSystemConnection {
        end1 : StreamlitFrontend.SetPromptTarget.fileSystemPort
        end2 : DatabaseLayer.FileSystem.filePort
    }

    connector configureConvertersToAPIconnection {
        end1 : StreamlitFrontend.ConfigureConverters.apiPort
        end2 : APILayer.ViolentUTFAPI.apiPort
    }

    connector configureConvertersToFileSystemConnection {
        end1 : StreamlitFrontend.ConfigureConverters.fileSystemPort
        end2 : DatabaseLayer.FileSystem.filePort
    }
  }

  // Define Requirement Blocks

  // High-Level System Objective for User Interaction

  requirement SystemObjective_UserInteraction {
      id : "OBJ-USER-INTERACTION"
      name : "Intuitive and Efficient User Interaction"
      text = "The system shall provide an intuitive and efficient user interface to enhance user experience and productivity."
  }

  // High-Level System Objective
  requirement SystemObjective_SecureAccess {
    id : "OBJ-SECURE-ACCESS"
    name : "Secure Access"
    text = "The system shall ensure that only authorized users can access protected resources."
  }

  // Top-Level Requirement for Authentication and Authorization
  requirement REQ-AUTH-000 {
    id : "REQ-AUTH-000"
    name : "Authentication and Authorization Functionality"
    text = "The system shall provide secure authentication and authorization mechanisms to control access to resources."
    derive : SystemObjective_SecureAccess
  }

  // Functional Requirements

  requirement REQ-AUTH-001_UserAuthentication {
    id : "REQ-AUTH-001"
    name : "User Authentication"
    text = "The system shall authenticate users via the OpenID Connect (OIDC) protocol."
    derive : REQ-AUTH-000
  }

  requirement REQ-AUTH-002_SingleSignOn {
    id : "REQ-AUTH-002"
    name : "Single Sign-On"
    text = "The system shall support Single Sign-On (SSO) across all integrated applications."
    derive : REQ-AUTH-000
  }

  requirement REQ-AUTH-003_RoleBasedAccessControl {
    id : "REQ-AUTH-003"
    name : "Role-Based Access Control"
    text = "The system shall implement Role-Based Access Control (RBAC) to manage user permissions."
    derive : REQ-AUTH-000
  }

  requirement REQ-AUTH-004_MultiFactorAuthentication {
    id : "REQ-AUTH-004"
    name : "Multi-Factor Authentication"
    text = "The system shall support Multi-Factor Authentication (MFA) for enhanced security."
    derive : REQ-AUTH-000
  }

  requirement REQ-AUTH-005_TokenValidation {
    id : "REQ-AUTH-005"
    name : "Token Validation"
    text = "The system shall validate tokens for authentication and authorization purposes."
    derive : REQ-AUTH-000
  }

  requirement REQ-AUTH-006_APIProtection {
    id : "REQ-AUTH-006"
    name : "API Protection"
    text = "The system shall protect APIs using OAuth2 and JWT token validation."
    derive : REQ-AUTH-000
  }

  // Non-Functional Requirements

  requirement REQ-SEC-001_SecureCodingPractices {
    id : "REQ-SEC-001"
    name : "Secure Coding Practices"
    text = "The system shall implement secure coding practices to prevent common vulnerabilities."
    refine : REQ-AUTH-000
  }

  requirement REQ-SEC-002_SecretsManagement {
    id : "REQ-SEC-002"
    name : "Secrets Management"
    text = "The system shall securely store secrets (API keys, passwords) using environment variables or a secrets management tool."
    refine : REQ-AUTH-000
  }

  requirement REQ-SEC-003_PrincipleOfLeastPrivilege {
    id : "REQ-SEC-003"
    name : "Principle of Least Privilege"
    text = "The system shall follow the principle of least privilege in access control."
    refine : REQ-AUTH-000
  }

  requirement REQ-SEC-004_ComplianceStandards {
    id : "REQ-SEC-004"
    name : "Compliance with Security Standards"
    text = "The system shall comply with relevant security standards and regulations."
    refine : REQ-AUTH-000
  }

  // Requirements for ViolentUTF API
  requirement REQ-API-100 {
    id : "REQ-API-100"
    name : "ViolentUTFAPI Management Functionalities"
    text : "ViolentUTFAPI shall provide comprehensive management of PyRIT, datasets, converters, scoring engines, and memory configurations."
  }

  contain REQ-API-101 : REQ-API-100
  requirement REQ-API-101 {
    id : "REQ-API-101"
    name : "Dataset Management"
    text : "ViolentUTFAPI shall manage dataset loading, validation, transformation and provide appropriate dataset IDs."
  }

  contain REQ-API-102 : REQ-API-100
  requirement REQ-API-102 {
    id : "REQ-API-102"
    name : "Converter Management"
    text : "ViolentUTFAPI shall allow defining, configuration, execution, and testing of converters for use in orchestrators."
  }

  contain REQ-API-103 : REQ-API-100
  requirement REQ-API-103 {
      id : "REQ-API-103"
      name : "Scoring Engine Management"
      text : "ViolentUTFAPI shall manage the creation, configuration, execution and testing of scoring engines to evaluate responses."
  }

  requirement REQ-API-NF-200 {
      id : "REQ-API-NF-200"
      name : "API Layer Non-Functional Requirements"
      text : "The API Layer shall ensure security, scalability, high performance, and maintainability."
  }

  refine REQ-SEC-001_SecureCodingPractices : REQ-API-NF-200
  derive REQ-FAPI-NF-001_HighPerformance : REQ-API-NF-200
  derive REQ-FAPI-NF-002_Scalability : REQ-API-NF-200
  derive REQ-FAPI-NF-003_Maintainability : REQ-API-NF-200

  // Functional Requirements for FastAPI

  requirement REQ-FAPI-000 {
    id : "REQ-FAPI-000"
    name : "FastAPI Functional Requirements"
    text = "Defines the functional requirements for the FastAPI component."
    derive : SystemObjective_SecureAccess
  }

  requirement REQ-FAPI-001_ProvideRESTfulEndpoints {
    id : "REQ-FAPI-001"
    name : "Provide RESTful API Endpoints"
    text = "FastAPI shall provide RESTful API endpoints for all core functionalities."
    derive : REQ-FAPI-000
  }

  requirement REQ-FAPI-002_SupportAPIVersioning {
    id : "REQ-FAPI-002"
    name : "Support API Versioning"
    text = "FastAPI shall support API versioning to maintain backward compatibility."
    derive : REQ-FAPI-000
  }

  requirement REQ-FAPI-003_ValidateIncomingRequests {
    id : "REQ-FAPI-003"
    name : "Validate Incoming Requests"
    text = "FastAPI shall validate all incoming requests for correctness and security."
    derive : REQ-FAPI-000
  }

  requirement REQ-FAPI-004_GenerateOpenAPIDocs {
    id : "REQ-FAPI-004"
    name : "Generate OpenAPI Documentation"
    text = "FastAPI shall automatically generate OpenAPI documentation for all endpoints."
    derive : REQ-FAPI-000
  }

  requirement REQ-FAPI-005_SupportRateLimiting {
    id : "REQ-FAPI-005"
    name : "Support Rate Limiting"
    text = "FastAPI shall support rate limiting mechanisms."
    derive : REQ-FAPI-000
  }

  // Non-Functional Requirements for FastAPI

  requirement REQ-FAPI-NF-000 {
    id : "REQ-FAPI-NF-000"
    name : "FastAPI Non-Functional Requirements"
    text = "Defines the non-functional requirements for the FastAPI component."
    derive : SystemObjective_SecureAccess
  }

  requirement REQ-FAPI-NF-001_HighPerformance {
    id : "REQ-FAPI-NF-001"
    name : "High Performance"
    text = "FastAPI shall have high performance with minimal latency."
    derive : REQ-FAPI-NF-000
  }

  requirement REQ-FAPI-NF-002_Scalability {
    id : "REQ-FAPI-NF-002"
    name : "Scalability"
    text = "FastAPI shall be scalable to handle increasing workloads."
    derive : REQ-FAPI-NF-000
  }

  requirement REQ-FAPI-NF-003_Maintainability {
    id : "REQ-FAPI-NF-003"
    name : "Maintainability"
    text = "FastAPI shall be maintainable with modular architecture and clean code practices."
    derive : REQ-FAPI-NF-000
  }

  requirement REQ-FAPI-NF-004_SecurityCompliance {
    id : "REQ-FAPI-NF-004"
    name : "Security Compliance"
    text = "FastAPI shall comply with all security standards and prevent common vulnerabilities."
    derive : REQ-FAPI-NF-000
  }

  // Functional Requirements for KongGateway

  requirement REQ-KONG-000 {
    id : "REQ-KONG-000"
    name : "KongGateway Functional Requirements"
    text = "Defines the functional requirements for the KongGateway component."
    derive : SystemObjective_SecureAccess
  }

  requirement REQ-KONG-001_RouteRequests {
    id : "REQ-KONG-001"
    name : "Route Incoming Requests"
    text = "KongGateway shall route incoming API requests to the appropriate backend services."
    derive : REQ-KONG-000
  }

  requirement REQ-KONG-002_ValidateTokens {
    id : "REQ-KONG-002"
    name : "Validate Authentication Tokens"
    text = "KongGateway shall validate authentication tokens via Keycloak."
    derive : REQ-KONG-000
  }

  requirement REQ-KONG-003_EnforceRateLimits {
    id : "REQ-KONG-003"
    name : "Enforce Rate Limiting Policies"
    text = "KongGateway shall enforce rate limiting policies to prevent abuse."
    derive : REQ-KONG-000
  }

  requirement REQ-KONG-004_TransformRequestsResponses {
    id : "REQ-KONG-004"
    name : "Transform Requests and Responses"
    text = "KongGateway shall modify requests and responses as necessary using plugins."
    derive : REQ-KONG-000
  }

  requirement REQ-KONG-005_ProvideLoggingMonitoring {
    id : "REQ-KONG-005"
    name : "Provide Logging and Monitoring"
    text = "KongGateway shall provide logging and monitoring capabilities."
    derive : REQ-KONG-000
  }

  // Non-Functional Requirements for KongGateway

  requirement REQ-KONG-NF-000 {
    id : "REQ-KONG-NF-000"
    name : "KongGateway Non-Functional Requirements"
    text = "Defines the non-functional requirements for the KongGateway component."
    derive : SystemObjective_SecureAccess
  }

  requirement REQ-KONG-NF-001_HighAvailability {
    id : "REQ-KONG-NF-001"
    name : "High Availability"
    text = "KongGateway shall be highly available and fault-tolerant."
    derive : REQ-KONG-NF-000
  }

  requirement REQ-KONG-NF-002_Scalability {
    id : "REQ-KONG-NF-002"
    name : "Scalability"
    text = "KongGateway shall be scalable to handle increasing traffic."
    derive : REQ-KONG-NF-000
  }

  requirement REQ-KONG-NF-003_SecurityCompliance {
    id : "REQ-KONG-NF-003"
    name : "Security Compliance"
    text = "KongGateway shall comply with security standards and protect against common threats."
    derive : REQ-KONG-NF-000
  }

  // Derived Requirements for FastAPI
  derive REQ-FAPI-000 : SystemObjective_SecureAccess

  // Derived Requirements for KongGateway
  derive REQ-KONG-000 : SystemObjective_SecureAccess

  // Requirements related to HomePage

  requirement REQ-HP-000 {
    id : "REQ-HP-000"
    name : "HomePage Requirements"
    text = "Defines the functional and non-functional requirements for the HomePage component."
    derive : SystemObjective_SecureAccess
  }

  // Functional Requirements for HomePage

  requirement REQ-HP-001_DisplayHomePage {
    id : "REQ-HP-001"
    name : "Display Home Page"
    text = "The HomePage shall display a welcome message and options to log in or explore the application."
    derive : REQ-HP-000
  }

  requirement REQ-HP-002_UserAuthentication {
    id : "REQ-HP-002"
    name : "User Authentication from HomePage"
    text = "The HomePage shall allow users to log in via Keycloak using the OpenID Connect (OIDC) protocol."
    derive : REQ-HP-000
    derive : REQ-AUTH-001_UserAuthentication
  }

  requirement REQ-HP-003_DisplayAvailableApps {
    id : "REQ-HP-003"
    name : "Display Available Applications"
    text = "After successful authentication, the HomePage shall display a list of available Violent UTF applications to the user."
    derive : REQ-HP-000
  }

  requirement REQ-HP-004_UserLogout {
    id : "REQ-HP-004"
    name : "User Logout from HomePage"
    text = "The HomePage shall allow users to log out, terminating their session securely."
    derive : REQ-HP-000
  }

  requirement REQ-HP-005_SecureAccess {
    id : "REQ-HP-005"
    name : "Secure Access Control"
    text = "The HomePage shall ensure that only authenticated users can access protected resources or applications."
    refine : SystemObjective_SecureAccess
    derive : REQ-HP-000
  }

  // Non-Functional Requirements for HomePage

  requirement REQ-HP-NF-001_UserFriendlyUI {
    id : "REQ-HP-NF-001"
    name : "User-Friendly Interface"
    text = "The HomePage shall provide an intuitive and user-friendly interface to enhance user experience."
    derive : REQ-HP-000
  }

  requirement REQ-HP-NF-002_ResponseTime {
    id : "REQ-HP-NF-002"
    name : "Fast Response Time"
    text = "The HomePage shall load and respond to user actions within 2 seconds under normal load."
    derive : REQ-HP-000
  }

  requirement REQ-HP-NF-003_AccessibilityCompliance {
    id : "REQ-HP-NF-003"
    name : "Accessibility Compliance"
    text = "The HomePage shall comply with WCAG 2.1 accessibility guidelines."
    derive : REQ-HP-000
  }

  // Constraints and Parameters for HomePage

  constraint CST-HP-001_AuthenticationTimeout {
    text = "The HomePage login process shall timeout after 30 seconds if the user does not complete authentication."
    constrain : REQ-HP-002_UserAuthentication
  }

  parameter HomePageResponseTime : Integer = 2000 // in milliseconds

  constraint CST-HP-002_ResponseTime {
    text = "The HomePage shall respond within HomePageResponseTime milliseconds."
    constrain : REQ-HP-NF-002_ResponseTime
    constrain : HomePageResponseTime
  }

  // Requirements related to WelcomePage

  requirement REQ-WP-000 {
      id : "REQ-WP-000"
      name : "WelcomePage Requirements"
      text = "Defines the functional and non-functional requirements for the WelcomePage component."
      derive : SystemObjective_UserInteraction
  }

  // Functional Requirements for WelcomePage

  requirement REQ-WP-001_DisplayWelcomePage {
      id : "REQ-WP-001"
      name : "Display Welcome Page"
      text = "The WelcomePage shall display a heading and introduction to Violent UTF, along with links to documentation and tutorials."
      derive : REQ-WP-000
  }

  requirement REQ-WP-002_LoadParameterFile {
      id : "REQ-WP-002"
      name : "Load Parameter File"
      text = "The WelcomePage shall provide options to load previously saved parameter files from the system or upload from the user's local machine."
      derive : REQ-WP-000
  }

  requirement REQ-WP-003_ValidateParameterFile {
      id : "REQ-WP-003"
      name : "Validate Parameter File"
      text = "The WelcomePage shall validate the selected or uploaded parameter file for correctness and completeness."
      derive : REQ-WP-000
  }

  requirement REQ-WP-004_InitializeSession {
      id : "REQ-WP-004"
      name : "Initialize Session"
      text = "The WelcomePage shall initialize the session state with default values if no parameter file is provided."
      derive : REQ-WP-000
  }

  requirement REQ-WP-005_ProceedToNextStep {
      id : "REQ-WP-005"
      name : "Proceed to Next Step"
      text = "The WelcomePage shall proceed to the 'Configure Memory' step upon the user clicking the 'Start' button."
      derive : REQ-WP-000
  }

  // Non-Functional Requirements for WelcomePage

  requirement REQ-WP-NF-001_UserFriendlyUI {
      id : "REQ-WP-NF-001"
      name : "User-Friendly Interface"
      text = "The WelcomePage shall provide an intuitive and user-friendly interface to enhance user experience."
      derive : REQ-WP-000
  }

  requirement REQ-WP-NF-002_ResponseTime {
      id : "REQ-WP-NF-002"
      name : "Fast Response Time"
      text = "The WelcomePage shall load and respond to user actions within 2 seconds under normal load."
      derive : REQ-WP-000
  }

  requirement REQ-WP-NF-003_ErrorHandling {
      id : "REQ-WP-NF-003"
      name : "Robust Error Handling"
      text = "The WelcomePage shall provide meaningful error messages and guidance when invalid parameter files are selected or uploaded."
      derive : REQ-WP-000
  }

  // New requirement for Configurable Architecture
  requirement SystemObjective_ConfigurableArchitecture {
    id : "OBJ-CONFIG-ARCH"
    name : "Configurable Architecture"
    text = "The system shall allow configuration of its components and architecture to meet diverse deployment needs."
  }

  // New requirement block for ConfigureMemory
  requirement REQ-CMEM-000 {
    id : "REQ-CMEM-000"
    name : "ConfigureMemory Functional Requirements"
    text = "Defines the functional requirements for the ConfigureMemory component."
    derive : SystemObjective_ConfigurableArchitecture
  }

  // Functional requirements for ConfigureMemory
  requirement REQ-CMEM-001_MemoryTypeSelection {
    id : "REQ-CMEM-001"
    name : "Memory Type Selection"
    text = "The ConfigureMemory component shall allow users to select a memory type from available options (InMemory, DuckDB, AzureSQL)."
    derive : REQ-CMEM-000
  }

  requirement REQ-CMEM-002_MemoryParameterConfiguration {
    id : "REQ-CMEM-002"
    name : "Memory Parameter Configuration"
    text = "The ConfigureMemory component shall allow users to input and edit parameters for the selected memory type."
    derive : REQ-CMEM-000
  }

  requirement REQ-CMEM-003_ParameterValidation {
    id : "REQ-CMEM-003"
    name : "Memory Parameter Validation"
    text = "The ConfigureMemory component shall validate the provided memory configuration parameters before initialization."
    derive : REQ-CMEM-000
  }

  requirement REQ-CMEM-004_MemoryInitialization {
    id : "REQ-CMEM-004"
    name : "Memory Initialization"
    text = "The ConfigureMemory component shall initialize the memory system with the provided configuration."
    derive : REQ-CMEM-000
  }

  // Non-Functional requirements for ConfigureMemory
  requirement REQ-CMEM-NF-001_UserFriendlyInterface {
    id : "REQ-CMEM-NF-001"
    name : "User-Friendly Interface"
    text = "The ConfigureMemory component shall provide a user-friendly interface with clear instructions and help text."
    derive : REQ-CMEM-000
  }

  requirement REQ-CMEM-NF-002_SecureParameterHandling {
    id : "REQ-CMEM-NF-002"
    name : "Secure Parameter Handling"
    text = "The ConfigureMemory component shall securely handle sensitive information, such as connection strings, to prevent unauthorized access."
    derive : REQ-CMEM-000
    refine : REQ-SEC-002_SecretsManagement
  }

  // System Objective for Prompt Target Configuration
  requirement SystemObjective_PromptTargetConfiguration {
      id : "OBJ-PROMPT-TARGET-CONFIG"
      name : "Prompt Target Configuration"
      text = "The system shall allow users to configure and manage prompt targets for sending prompts."
  }

  // High-Level Requirement for SetPromptTarget
  requirement REQ-PT-000 {
      id : "REQ-PT-000"
      name : "SetPromptTarget Functional Requirements"
      text = "Defines the functional requirements for the SetPromptTarget component."
      derive : SystemObjective_PromptTargetConfiguration
  }

  // Functional Requirements for SetPromptTarget
  requirement REQ-PT-001_ManageExistingTargets {
      id : "REQ-PT-001"
      name : "Manage Existing Targets"
      text = "SetPromptTarget shall display a list of existing targets, allowing users to add or delete targets."
      derive : REQ-PT-000
  }

  requirement REQ-PT-002_SelectInteractionType {
      id : "REQ-PT-002"
      name : "Select Target Interaction Type"
      text = "SetPromptTarget shall allow users to select the target interaction type (HTTP Target, PromptTarget, PromptChatTarget)."
      derive : REQ-PT-000
  }

  requirement REQ-PT-003_SelectProviderTechnology {
      id : "REQ-PT-003"
      name : "Select Target Provider or Technology"
      text = "SetPromptTarget shall allow users to select the target provider or technology based on the selected interaction type."
      derive : REQ-PT-000
  }

  requirement REQ-PT-004_ConfigureTargetParameters {
      id : "REQ-PT-004"
      name : "Configure Target Parameters"
      text = "SetPromptTarget shall provide input fields for users to configure parameters specific to the selected provider or technology."
      derive : REQ-PT-000
  }

  requirement REQ-PT-005_SaveAndTestConfiguration {
      id : "REQ-PT-005"
      name : "Save and Test Target Configuration"
      text = "SetPromptTarget shall allow users to save the target configuration and test the connection by sending a test prompt."
      derive : REQ-PT-000
  }

  requirement REQ-PT-006_DeleteTarget {
      id : "REQ-PT-006"
      name : "Delete Target"
      text = "SetPromptTarget shall allow users to delete an existing target after confirmation."
      derive : REQ-PT-000
  }

  // Non-Functional Requirements for SetPromptTarget
  requirement REQ-PT-NF-001_UserFriendlyInterface {
      id : "REQ-PT-NF-001"
      name : "User-Friendly Interface"
      text = "SetPromptTarget shall provide an intuitive and user-friendly interface with clear instructions."
      derive : REQ-PT-000
  }

  requirement REQ-PT-NF-002_SecureParameterHandling {
      id : "REQ-PT-NF-002"
      name : "Secure Parameter Handling"
      text = "SetPromptTarget shall securely handle sensitive information such as API keys and endpoints."
      derive : REQ-PT-000
      refine : REQ-SEC-002_SecretsManagement
  }

  // Define new Requirement Blocks for ConfigureDatasets

  requirement REQ-CD-000 {
    id : "REQ-CD-000"
    name : "ConfigureDatasets Functional Requirements"
    text = "Defines the functional requirements for the ConfigureDatasets component."
    derive : SystemObjective_UserInteraction
  }

  requirement REQ-CD-001_ChooseDatasetSource {
    id : "REQ-CD-001"
    name : "Choose Dataset Source"
    text = "The ConfigureDatasets component shall allow users to select a dataset source, including options to upload a local file, fetch from an online dataset, combine datasets, or transform an existing dataset."
    derive : REQ-CD-000
  }

  requirement REQ-CD-002_UploadLocalDataset {
    id : "REQ-CD-002"
    name : "Upload Local Dataset File"
    text = "The system shall allow users to upload a local dataset file in supported formats (CSV, TSV, JSON, YAML, or TXT)."
    derive : REQ-CD-000
  }

  requirement REQ-CD-003_FetchOnlineDataset {
    id : "REQ-CD-003"
    name : "Fetch Online Dataset"
    text = "The system shall allow users to fetch a dataset from an online source by providing a valid URL."
    derive : REQ-CD-000
  }

  requirement REQ-CD-004_CombineDatasets {
    id : "REQ-CD-004"
    name : "Combine Datasets"
    text = "The system shall allow users to combine existing configured datasets into a new dataset."
    derive : REQ-CD-000
  }

  requirement REQ-CD-005_TransformDataset {
    id : "REQ-CD-005"
    name : "Transform Dataset"
    text = "The system shall allow users to transform an existing dataset using a selected or new prompt template."
    derive : REQ-CD-000
  }

  requirement REQ-CD-006_DatasetPreviewAndMapping {
    id : "REQ-CD-006"
    name : "Dataset Preview and Field Mapping"
    text = "The system shall provide a preview of the dataset and allow users to map dataset fields to the required SeedPrompt attributes."
    derive : REQ-CD-000
  }

  requirement REQ-CD-007_CreateAndSaveDataset {
    id : "REQ-CD-007"
    name : "Create and Save Dataset"
    text = "The system shall allow users to create and save the configured dataset for use in subsequent steps."
    derive : REQ-CD-000
  }

  requirement REQ-CD-008_FinalizeConfiguration {
    id : "REQ-CD-008"
    name : "Finalize Dataset Configuration"
    text = "The system shall summarize the dataset configuration and allow users to proceed to the next step or configure another dataset."
    derive : REQ-CD-000
  }

  requirement REQ-CD-NF-001_UserFriendlyInterface {
    id : "REQ-CD-NF-001"
    name : "User-Friendly Interface"
    text = "The ConfigureDatasets component shall provide an intuitive and user-friendly interface with clear instructions and feedback."
    derive : REQ-CD-000
  }

  requirement REQ-CD-NF-002_Security {
    id : "REQ-CD-NF-002"
    name : "Security and Data Validation"
    text = "The system shall validate and sanitize all user inputs and handle files securely to prevent security vulnerabilities."
    derive : REQ-CD-000
    refine : REQ-SEC-001_SecureCodingPractices
  }

  requirement REQ-CD-NF-003_ErrorHandling {
    id : "REQ-CD-NF-003"
    name : "Robust Error Handling"
    text = "The system shall handle errors gracefully and provide meaningful feedback to the user."
    derive : REQ-CD-000
  }

  requirement REQ-CD-NF-004_Performance {
    id : "REQ-CD-NF-004"
    name : "Performance"
    text = "The ConfigureDatasets component shall load and respond to user actions within 2 seconds under normal load."
    derive : REQ-CD-000
  }

  // System Objective for Converter Configuration
  requirement SystemObjective_ConverterConfiguration {
      id : "OBJ-CONVERTER-CONFIG"
      name : "Converter Configuration"
      text = "The system shall allow users to configure and manage converters to transform prompts before sending to targets."
  }

  // High-Level Requirement for ConfigureConverters
  requirement REQ-CCV-000 {
      id : "REQ-CCV-000"
      name : "ConfigureConverters Functional Requirements"
      text = "Defines the functional requirements for the ConfigureConverters component."
      derive : SystemObjective_ConverterConfiguration
  }

  // Functional Requirements for ConfigureConverters
  requirement REQ-CCV-001_DisplayConverterCategories {
      id : "REQ-CCV-001"
      name : "Display Converter Categories"
      text = "The system shall display a list of converter categories for the user to select."
      derive : REQ-CCV-000
  }

  requirement REQ-CCV-002_SelectConverterCategory {
      id : "REQ-CCV-002"
      name : "Select Converter Category"
      text = "The system shall allow the user to select a converter category."
      derive : REQ-CCV-000
  }

  requirement REQ-CCV-003_DisplayConverterClasses {
      id : "REQ-CCV-003"
      name : "Display Converter Classes"
      text = "The system shall display a list of converter classes within the selected category."
      derive : REQ-CCV-000
  }

  requirement REQ-CCV-004_SelectConverterClass {
      id : "REQ-CCV-004"
      name : "Select Converter Class"
      text = "The system shall allow the user to select a converter class."
      derive : REQ-CCV-000
  }

  requirement REQ-CCV-005_DisplayConverterParameters {
      id : "REQ-CCV-005"
      name : "Display Converter Parameters"
      text = "The system shall display input fields for parameters specific to the selected converter class."
      derive : REQ-CCV-000
  }

  requirement REQ-CCV-006_CaptureParameterValues {
      id : "REQ-CCV-006"
      name : "Capture Parameter Values"
      text = "The system shall allow the user to input and edit parameter values for the selected converter."
      derive : REQ-CCV-000
  }

  requirement REQ-CCV-007_ValidateConverterParameters {
      id : "REQ-CCV-007"
      name : "Validate Converter Parameters"
      text = "The system shall validate the provided parameter values before adding the converter."
      derive : REQ-CCV-000
  }

  requirement REQ-CCV-008_AddConverterToPipeline {
      id : "REQ-CCV-008"
      name : "Add Converter to Pipeline"
      text = "The system shall allow the user to add the configured converter to the converter pipeline."
      derive : REQ-CCV-000
  }

  requirement REQ-CCV-009_DisplayConverterPipeline {
      id : "REQ-CCV-009"
      name : "Display Converter Pipeline"
      text = "The system shall display the list of converters in the current pipeline in order."
      derive : REQ-CCV-000
  }

  requirement REQ-CCV-010_ManageConverters {
      id : "REQ-CCV-010"
      name : "Manage Converters"
      text = "The system shall allow the user to remove, reorder, and test converters in the pipeline."
      derive : REQ-CCV-000
  }

  requirement REQ-CCV-011_TestConverter {
      id : "REQ-CCV-011"
      name : "Test Converter"
      text = "The system shall allow the user to test a converter with a sample input and display the result."
      derive : REQ-CCV-000
  }

  // Non-Functional Requirements
  requirement REQ-CCV-NF-001_UserFriendlyInterface {
      id : "REQ-CCV-NF-001"
      name : "User-Friendly Interface"
      text = "ConfigureConverters shall provide an intuitive and user-friendly interface with clear instructions and help text."
      derive : REQ-CCV-000
  }

  requirement REQ-CCV-NF-002_ErrorHandling {
      id : "REQ-CCV-NF-002"
      name : "Error Handling"
      text = "ConfigureConverters shall handle errors gracefully and provide meaningful feedback to the user."
      derive : REQ-CCV-000
  }

  requirement REQ-CCV-NF-003_ResponseTime {
      id : "REQ-CCV-NF-003"
      name : "Performance"
      text = "ConfigureConverters shall respond to user actions within 2 seconds under normal load."
      derive : REQ-CCV-000
  }

  // System Objective for Scorer Configuration
  requirement SystemObjective_ScorerConfiguration {
    id : "OBJ-SCORER-CONFIG"
    name : "Scorer Configuration"
    text = "The system shall allow users to configure and manage scorers for evaluating responses."
  }

  // High-Level Requirement for ConfigureScoring
  requirement REQ-CS-000 {
    id : "REQ-CS-000"
    name : "ConfigureScoring Functional Requirements"
    text = "Defines the functional requirements for the ConfigureScoring component."
    derive : SystemObjective_ScorerConfiguration
  }

  // Functional Requirements for ConfigureScoring
  requirement REQ-CS-001_DisplayScorerOptions {
    id : "REQ-CS-001"
    name : "Display Scorer Options"
    text = "The ConfigureScoring component shall display a list of available scorers for selection."
    derive : REQ-CS-000
  }

  requirement REQ-CS-002_SelectScorerType {
    id : "REQ-CS-002"
    name : "Select Scorer Type"
    text = "The ConfigureScoring component shall allow users to select a scorer type from available options."
    derive : REQ-CS-000
  }

  requirement REQ-CS-003_ConfigureScorerParameters {
    id : "REQ-CS-003"
    name : "Configure Scorer Parameters"
    text = "The ConfigureScoring component shall allow users to input and edit parameters specific to the selected scorer."
    derive : REQ-CS-000
  }

  requirement REQ-CS-004_ValidateScorerConfiguration {
    id : "REQ-CS-004"
    name : "Validate Scorer Configuration"
    text = "The ConfigureScoring component shall validate the scorer configuration parameters before saving."
    derive : REQ-CS-000
  }

  requirement REQ-CS-005_SaveScorerConfiguration {
    id : "REQ-CS-005"
    name : "Save Scorer Configuration"
    text = "The ConfigureScoring component shall allow users to save the configured scorer."
    derive : REQ-CS-000
  }

  requirement REQ-CS-006_TestScorer {
    id : "REQ-CS-006"
    name : "Test Scorer"
    text = "The ConfigureScoring component shall allow users to test the configured scorer with sample data."
    derive : REQ-CS-000
  }

  requirement REQ-CS-007_ManageConfiguredScorers {
    id : "REQ-CS-007"
    name : "Manage Configured Scorers"
    text = "The ConfigureScoring component shall allow users to view, edit, and remove configured scorers."
    derive : REQ-CS-000
  }

  // Non-Functional Requirements for ConfigureScoring

  requirement REQ-CS-NF-001_UserFriendlyInterface {
    id : "REQ-CS-NF-001"
    name : "User-Friendly Interface"
    text = "The ConfigureScoring component shall provide an intuitive and user-friendly interface with clear instructions."
    derive : REQ-CS-000
  }

  requirement REQ-CS-NF-002_SecureParameterHandling {
    id : "REQ-CS-NF-002"
    name : "Secure Parameter Handling"
    text = "The ConfigureScoring component shall securely handle sensitive information such as API keys and endpoints."
    derive : REQ-CS-000
    refine : REQ-SEC-002_SecretsManagement
  }

  // System Objective for Reporting

  requirement SystemObjective_Reporting {
    id : "OBJ-REPORTING"
    name : "Reporting Objective"
    text = "The system shall provide detailed and professional reports based on the results of red teaming activities."
  }

  // High-Level Requirement for Reporting

  requirement REQ-REP-000 {
    id : "REQ-REP-000"
    name : "Reporting Functional Requirements"
    text = "Defines the functional requirements for the Reporting component."
    derive : SystemObjective_Reporting
  }

  // Functional Requirements for Reporting

  requirement REQ-REP-001_ConfigureReportingParameters {
    id : "REQ-REP-001"
    name : "Configure Reporting Parameters"
    text = "The Reporting component shall allow users to configure reporting parameters such as generating reports, report format, including interactive visualizations, selecting report templates, and specifying output directory."
    derive : REQ-REP-000
  }

  requirement REQ-REP-002_DataExtraction {
    id : "REQ-REP-002"
    name : "Data Extraction"
    text = "The Reporting component shall extract necessary data from memory and other sources to generate reports."
    derive : REQ-REP-000
  }

  requirement REQ-REP-003_DataTransformation {
    id : "REQ-REP-003"
    name : "Data Transformation"
    text = "The Reporting component shall transform extracted data into appropriate formats for reporting."
    derive : REQ-REP-000
  }

  requirement REQ-REP-004_Visualization {
    id : "REQ-REP-004"
    name : "Visualization"
    text = "The Reporting component shall generate visualizations such as charts and graphs to incorporate into reports."
    derive : REQ-REP-000
  }

  requirement REQ-REP-005_ReportGeneration {
    id : "REQ-REP-005"
    name : "Report Generation"
    text = "The Reporting component shall generate reports based on templates and user configurations, supporting formats like HTML, PDF, and Markdown."
    derive : REQ-REP-000
  }

  requirement REQ-REP-006_IncludeConversationAnalytics {
    id : "REQ-REP-006"
    name : "Include Conversation Analytics"
    text = "The Reporting component shall incorporate conversation analytics to provide insights into repeated content or embedding-based similarity."
    derive : REQ-REP-000
  }

  requirement REQ-REP-007_InteractiveVisualizations {
    id : "REQ-REP-007"
    name : "Interactive Visualizations"
    text = "The Reporting component shall include interactive visualizations in reports when supported by the report format."
    derive : REQ-REP-000
  }

  // Non-Functional Requirements for Reporting

  requirement REQ-REP-NF-001_UserFriendlyInterface {
    id : "REQ-REP-NF-001"
    name : "User-Friendly Interface"
    text = "The Reporting component shall provide an intuitive and user-friendly interface for configuring and generating reports."
    derive : REQ-REP-000
  }

  requirement REQ-REP-NF-002_Performance {
    id : "REQ-REP-NF-002"
    name : "Performance"
    text = "The Reporting component shall generate reports efficiently, with minimal impact on system performance."
    derive : REQ-REP-000
  }

  requirement REQ-REP-NF-003_ErrorHandling {
    id : "REQ-REP-NF-003"
    name : "Robust Error Handling"
    text = "The Reporting component shall handle errors gracefully and provide meaningful feedback to the user."
    derive : REQ-REP-000
  }

  requirement REQ-REP-NF-004_Security {
    id : "REQ-REP-NF-004"
    name : "Security"
    text = "The Reporting component shall securely handle sensitive data and configurations, preventing unauthorized access."
    derive : REQ-REP-000
  }

  // Constraints and Parameters for WelcomePage

  constraint CST-WP-001_ParameterFileFormat {
      text = "The WelcomePage shall accept only valid YAML parameter files."
      constrain : REQ-WP-003_ValidateParameterFile
  }

  parameter WelcomePageResponseTime : Integer = 2000 // in milliseconds

  constraint CST-WP-002_ResponseTime {
      text = "The WelcomePage shall respond within WelcomePageResponseTime milliseconds."
      constrain : REQ-WP-NF-002_ResponseTime
      constrain : WelcomePageResponseTime
  }

  // Constraints

  constraint CST-AUTH-001_TokenExpiration {
    text = "Tokens shall expire after a configurable period (e.g., access tokens after 15 minutes, refresh tokens after 7 days)."
    constrain : REQ-AUTH-005_TokenValidation
  }

  constraint CST-AUTH-002_PasswordPolicy {
    text = "User passwords shall meet the minimum complexity requirements (e.g., at least 12 characters, including uppercase, lowercase, numbers, and special characters)."
    constrain : REQ-AUTH-001_UserAuthentication
  }

  constraint CST-AUTH-003_SessionTimeout {
    text = "User sessions shall timeout after 30 minutes of inactivity."
    constrain : REQ-AUTH-001_UserAuthentication
  }

  constraint CST-AUTH-004_MFAEnforcement {
    text = "MFA shall be enforced for users with administrative roles."
    constrain : REQ-AUTH-004_MultiFactorAuthentication
  }

  parameter APILayerResponseTimeMS : Integer = 200  // FastAPI response under normal load
  constraint FastAPI_Response_Performance {
    constrain : REQ-FAPI-NF-001_HighPerformance
    text = "FastAPI requests shall respond within APILayerResponseTimeMS milliseconds."
  }

  parameter MaxRequestsPerMinute : Integer = 1000
  constraint KongGateway_RateLimiting {
    constrain : REQ-KONG-003_EnforceRateLimits
    text = "KongGateway shall limit requests to MaxRequestsPerMinute per client."
  }
  constraint CST-FAPI-001_ResponseTime {
    text = "FastAPI shall respond to API requests within 200 milliseconds under normal load."
    constrain : REQ-FAPI-NF-001_HighPerformance
  }

  constraint CST-FAPI-002_MaxRequestSize {
    text = "FastAPI shall limit the maximum size of incoming requests to 10 MB."
    constrain : REQ-FAPI-003_ValidateIncomingRequests
  }

  parameter MaxRequestSize : Integer = 10 // in Megabytes

  constraint CST-KONG-001_RateLimit {
    text = "KongGateway shall limit API requests to 1000 requests per minute per client."
    constrain : REQ-KONG-003_EnforceRateLimits
  }

  parameter SupportedMemoryTypes : String[] = ["InMemory", "DuckDB", "AzureSQL"]

  constraint CST-CMEM-001_SupportedMemoryTypes {
    text = "The system shall support the memory types: 'InMemory', 'DuckDB', and 'AzureSQL'."
    constrain : REQ-CMEM-001_MemoryTypeSelection
    constrain : SupportedMemoryTypes
  }

  constraint CST-CMEM-002_SecureStorageOfParameters {
    text = "Sensitive memory parameters shall not be stored in plain text in parameter files."
    constrain : REQ-CMEM-NF-002_SecureParameterHandling
  }

  // Constraints
  constraint CST-PT-001_ValidConfigurations {
      text = "SetPromptTarget shall validate that all required fields are filled and parameters are correct before saving."
      constrain : REQ-PT-005_SaveAndTestConfiguration
  }

  constraint CST-PT-002_MaxTargets {
      text = "The number of configured targets shall not exceed MaxNumberOfTargets."
      constrain : REQ-PT-001_ManageExistingTargets
      constrain : MaxNumberOfTargets
  }

  // Parameters
  parameter MaxNumberOfTargets : Integer = 10

  parameter RateLimitPerClient : Integer = 1000 // requests per minute

  parameter SupportedFileTypes : String[] = ["csv", "tsv", "json", "yaml", "yml", "txt"]

  constraint CST-CD-001_SupportedFileTypes {
    text = "The system shall support the following dataset file types: csv, tsv, json, yaml, yml, txt."
    constrain : REQ-CD-002_UploadLocalDataset
    constrain : SupportedFileTypes
  }

  constraint CST-CD-002_MaxUploadFileSize {
    text = "The system shall limit the maximum size of uploaded dataset files to 50 MB."
    constrain : REQ-CD-NF-002_Security
  }

  parameter MaxUploadFileSize : Integer = 50 // in Megabytes

  constraint CST-CD-003_ResponseTime {
    text = "The ConfigureDatasets component shall respond to user actions within ConfigureDatasetsResponseTime milliseconds."
    constrain : REQ-CD-NF-004_Performance
    constrain : ConfigureDatasetsResponseTime
  }

  parameter ConfigureDatasetsResponseTime : Integer = 2000 // in milliseconds

  parameter TokenExpirationTime : Integer = 900 // in seconds (15 minutes)
  parameter SessionTimeout : Integer = 1800 // in seconds (30 minutes)
  parameter PasswordMinLength : Integer = 12

  constraint CST-PARAM-001 {
    text = "TokenExpirationTime shall be less than or equal to SessionTimeout."
    constrain : TokenExpirationTime <= SessionTimeout
  }

  constraint CST-CCV-001_ValidConverterConfiguration {
      text = "The system shall validate that all required converter parameters are provided and correct before adding the converter to the pipeline."
      constrain : REQ-CCV-007_ValidateConverterParameters
  }

  constraint CST-CCV-002_MaxConverters {
      text = "The number of configured converters in the pipeline shall not exceed MaxNumberOfConverters."
      constrain : REQ-CCV-008_AddConverterToPipeline
      constrain : MaxNumberOfConverters
  }

  // Constraints for ConfigureScoring

  constraint CST-CS-001_ValidScorerConfiguration {
    text = "ConfigureScoring shall validate that all required fields are filled and parameters are correct before saving."
    constrain : REQ-CS-004_ValidateScorerConfiguration
  }

  constraint CST-CS-002_MaxScorers {
    text = "The number of configured scorers shall not exceed MaxNumberOfScorers."
    constrain : REQ-CS-005_SaveScorerConfiguration
    constrain : MaxNumberOfScorers
  }

  parameter MaxNumberOfScorers : Integer = 10

  // Parameters
  parameter MaxNumberOfConverters : Integer = 20 // Maximum number of converters in pipeline

  constraint CST-REP-001_SupportedFormats {
    text = "The Reporting component shall support the following report formats: 'HTML', 'PDF', and 'Markdown'."
    constrain : REQ-REP-005_ReportGeneration
    constrain : SupportedReportFormats
  }

  parameter SupportedReportFormats : String[] = ["HTML", "PDF", "Markdown"]

  constraint CST-REP-002_ResponseTime {
    text = "The Reporting component shall generate reports within ReportingResponseTime milliseconds under normal load."
    constrain : REQ-REP-NF-002_Performance
    constrain : ReportingResponseTime
  }

  parameter ReportingResponseTime : Integer = 5000 // in milliseconds

  constraint CST-REP-003_TemplatesExistence {
    text = "The Reporting component shall validate that the selected report template exists before generating the report."
    constrain : REQ-REP-005_ReportGeneration
  }

  // Satisfy relationships

  satisfy AuthenticationAuthorizationLayer.Keycloak : REQ-AUTH-001_UserAuthentication
  satisfy AuthenticationAuthorizationLayer.Keycloak : REQ-AUTH-002_SingleSignOn
  satisfy AuthenticationAuthorizationLayer.Keycloak : REQ-AUTH-003_RoleBasedAccessControl
  satisfy AuthenticationAuthorizationLayer.Keycloak : REQ-AUTH-004_MultiFactorAuthentication
  satisfy AuthenticationAuthorizationLayer.Keycloak : REQ-AUTH-005_TokenValidation
  satisfy AuthenticationAuthorizationLayer.Keycloak : REQ-SEC-001_SecureCodingPractices
  satisfy AuthenticationAuthorizationLayer.Keycloak : REQ-SEC-003_PrincipleOfLeastPrivilege
  satisfy AuthenticationAuthorizationLayer.Keycloak : REQ-SEC-004_ComplianceStandards

  satisfy AuthenticationAuthorizationLayer.StreamlitAuthentication : REQ-AUTH-001_UserAuthentication
  satisfy AuthenticationAuthorizationLayer.StreamlitAuthentication : REQ-AUTH-002_SingleSignOn
  satisfy AuthenticationAuthorizationLayer.StreamlitAuthentication : REQ-SEC-002_SecretsManagement

  satisfy AuthenticationAuthorizationLayer.KongGatewayAuthPlugin : REQ-AUTH-005_TokenValidation
  satisfy AuthenticationAuthorizationLayer.KongGatewayAuthPlugin : REQ-AUTH-006_APIProtection

  satisfy Logging : REQ-SEC-001_SecureCodingPractices

  // ViolentUTFAPI satisfy relationships
  satisfy APILayer.ViolentUTFAPI.DatasetManagement : REQ-API-101
  satisfy APILayer.ViolentUTFAPI.ConverterManagement : REQ-API-102
  satisfy APILayer.ViolentUTFAPI.ScoringEngineManagement : REQ-API-103

  satisfy FastAPI.APIEndpoints : REQ-FAPI-001_ProvideRESTfulEndpoints
  satisfy FastAPI.APIEndpoints : REQ-FAPI-002_SupportAPIVersioning
  satisfy FastAPI.DataValidation : REQ-FAPI-003_ValidateIncomingRequests
  satisfy FastAPI.DocumentationGenerator : REQ-FAPI-004_GenerateOpenAPIDocs
  satisfy FastAPI : REQ-FAPI-005_SupportRateLimiting
  satisfy FastAPI : REQ-FAPI-NF-001_HighPerformance
  satisfy FastAPI : REQ-FAPI-NF-002_Scalability
  satisfy FastAPI : REQ-FAPI-NF-003_Maintainability
  satisfy FastAPI.SecurityMiddleware : REQ-FAPI-NF-004_SecurityCompliance
  satisfy APILayer.FastAPI.SecurityMiddleware : REQ-FAPI-NF-004_SecurityCompliance
  satisfy APILayer.FastAPI.OpenAPIGenerator : REQ-FAPI-004_GenerateOpenAPIDocs

  satisfy KongGateway.RoutingEngine : REQ-KONG-001_RouteRequests
  satisfy KongGateway.AuthenticationPlugin : REQ-KONG-002_ValidateTokens
  satisfy KongGateway.RateLimitingPlugin : REQ-KONG-003_EnforceRateLimits
  satisfy KongGateway.RequestTransformerPlugin
  satisfy KongGateway.ResponseTransformerPlugin : REQ-KONG-004_TransformRequestsResponses
  satisfy KongGateway.LoggingPlugin
  satisfy KongGateway.Monitoring : REQ-KONG-005_ProvideLoggingMonitoring
  satisfy KongGateway : REQ-KONG-NF-001_HighAvailability
  satisfy KongGateway : REQ-KONG-NF-002_Scalability
  satisfy KongGateway.AuthenticationPlugin : REQ-KONG-NF-003_SecurityCompliance
  satisfy APILayer.KongGateway.AuthenticationPlugin : REQ-KONG-002_ValidateTokens
  satisfy APILayer.KongGateway.LoggingPlugin : REQ-KONG-005_ProvideLoggingMonitoring

  satisfy StreamlitFrontend.HomePage.displayHomePage : REQ-HP-001_DisplayHomePage
  satisfy StreamlitFrontend.HomePage.handleUserLogin : REQ-HP-002_UserAuthentication
  satisfy StreamlitFrontend.HomePage.displayAvailableApps : REQ-HP-003_DisplayAvailableApps
  satisfy StreamlitFrontend.HomePage.handleUserLogout : REQ-HP-004_UserLogout
  satisfy StreamlitFrontend.HomePage : REQ-HP-005_SecureAccess
  satisfy StreamlitFrontend.HomePage : REQ-HP-NF-001_UserFriendlyUI
  satisfy StreamlitFrontend.HomePage : REQ-HP-NF-002_ResponseTime
  satisfy StreamlitFrontend.HomePage : REQ-HP-NF-003_AccessibilityCompliance

  satisfy StreamlitFrontend.WelcomePage.displayWelcomePage : REQ-WP-001_DisplayWelcomePage
  satisfy StreamlitFrontend.WelcomePage.loadParameterFile : REQ-WP-002_LoadParameterFile
  satisfy StreamlitFrontend.WelcomePage.validateParameterFile : REQ-WP-003_ValidateParameterFile
  satisfy StreamlitFrontend.WelcomePage.initializeSession : REQ-WP-004_InitializeSession
  satisfy StreamlitFrontend.WelcomePage.proceedToNextStep : REQ-WP-005_ProceedToNextStep
  satisfy StreamlitFrontend.WelcomePage : REQ-WP-NF-001_UserFriendlyUI
  satisfy StreamlitFrontend.WelcomePage : REQ-WP-NF-002_ResponseTime
  satisfy StreamlitFrontend.WelcomePage : REQ-WP-NF-003_ErrorHandling

  satisfy ConfigureMemory : REQ-CMEM-001_MemoryTypeSelection
  satisfy ConfigureMemory : REQ-CMEM-002_MemoryParameterConfiguration
  satisfy ConfigureMemory : REQ-CMEM-003_ParameterValidation
  satisfy ConfigureMemory : REQ-CMEM-004_MemoryInitialization
  satisfy ConfigureMemory : REQ-CMEM-NF-001_UserFriendlyInterface
  satisfy ConfigureMemory : REQ-CMEM-NF-002_SecureParameterHandling

  satisfy SetPromptTarget.displayExistingTargets : REQ-PT-001_ManageExistingTargets
  satisfy SetPromptTarget.addNewTarget : REQ-PT-001_ManageExistingTargets
  satisfy SetPromptTarget.deleteExistingTarget : REQ-PT-006_DeleteTarget
  satisfy SetPromptTarget.selectInteractionType : REQ-PT-002_SelectInteractionType
  satisfy SetPromptTarget.selectProvider : REQ-PT-003_SelectProviderTechnology
  satisfy SetPromptTarget.configureTargetParameters : REQ-PT-004_ConfigureTargetParameters
  satisfy SetPromptTarget.saveConfiguration : REQ-PT-005_SaveAndTestConfiguration
  satisfy SetPromptTarget.testConnection : REQ-PT-005_SaveAndTestConfiguration

  satisfy SetPromptTarget : REQ-PT-NF-001_UserFriendlyInterface
  satisfy SetPromptTarget : REQ-PT-NF-002_SecureParameterHandling

  satisfy ConfigureDatasets.ChooseDatasetSource : REQ-CD-001_ChooseDatasetSource

  satisfy ConfigureDatasets.UploadLocalDataset : REQ-CD-002_UploadLocalDataset
  satisfy ConfigureDatasets.UploadLocalDataset.validateFile : REQ-CD-NF-002_Security
  satisfy ConfigureDatasets.UploadLocalDataset.handleErrors : REQ-CD-NF-003_ErrorHandling

  satisfy ConfigureDatasets.FetchOnlineDataset : REQ-CD-003_FetchOnlineDataset
  satisfy ConfigureDatasets.FetchOnlineDataset.validateDataset : REQ-CD-NF-002_Security
  satisfy ConfigureDatasets.FetchOnlineDataset.handleErrors : REQ-CD-NF-003_ErrorHandling

  satisfy ConfigureDatasets.CombineDatasets : REQ-CD-004_CombineDatasets

  satisfy ConfigureDatasets.TransformDataset : REQ-CD-005_TransformDataset
  satisfy ConfigureDatasets.TransformDataset.validateTemplate : REQ-CD-NF-002_Security
  satisfy ConfigureDatasets.TransformDataset.handleErrors : REQ-CD-NF-003_ErrorHandling

  satisfy ConfigureDatasets.DatasetPreviewer : REQ-CD-006_DatasetPreviewAndMapping

  satisfy ConfigureDatasets.DatasetPreviewer.createAndSaveDataset : REQ-CD-007_CreateAndSaveDataset

  satisfy ConfigureDatasets.FinalizeConfiguration : REQ-CD-008_FinalizeConfiguration

  satisfy ConfigureDatasets : REQ-CD-NF-001_UserFriendlyInterface
  satisfy ConfigureDatasets : REQ-CD-NF-004_Performance

  satisfy ConfigureConverters.SelectConverterCategory.displayCategories : REQ-CCV-001_DisplayConverterCategories
  satisfy ConfigureConverters.SelectConverterCategory.selectCategory : REQ-CCV-002_SelectConverterCategory

  satisfy ConfigureConverters.SelectConverterClass.displayClasses : REQ-CCV-003_DisplayConverterClasses
  satisfy ConfigureConverters.SelectConverterClass.selectClass : REQ-CCV-004_SelectConverterClass

  satisfy ConfigureConverters.ConfigureConverterParameters.displayParameters : REQ-CCV-005_DisplayConverterParameters
  satisfy ConfigureConverters.ConfigureConverterParameters.captureParameterValues : REQ-CCV-006_CaptureParameterValues
  satisfy ConfigureConverters.ConfigureConverterParameters.validateParameters : REQ-CCV-007_ValidateConverterParameters

  satisfy ConfigureConverters.AddConverter.addConverterToPipeline : REQ-CCV-008_AddConverterToPipeline

  satisfy ConfigureConverters.ManageConverters.displayConverterPipeline : REQ-CCV-009_DisplayConverterPipeline
  satisfy ConfigureConverters.ManageConverters.removeConverter : REQ-CCV-010_ManageConverters
  satisfy ConfigureConverters.ManageConverters.reorderConverters : REQ-CCV-010_ManageConverters
  satisfy ConfigureConverters.ManageConverters.testConverter : REQ-CCV-011_TestConverter

  satisfy ConfigureConverters : REQ-CCV-NF-001_UserFriendlyInterface
  satisfy ConfigureConverters : REQ-CCV-NF-002_ErrorHandling
  satisfy ConfigureConverters : REQ-CCV-NF-003_ResponseTime

  // Satisfy Relationships

  satisfy ConfigureScoring.ScorerSelection : REQ-CS-001_DisplayScorerOptions

  satisfy ConfigureScoring.ScorerSelection.selectScorerType : REQ-CS-002_SelectScorerType

  satisfy ConfigureScoring.ScorerConfiguration.configureScorerParameters : REQ-CS-003_ConfigureScorerParameters

  satisfy ConfigureScoring.ScorerConfiguration.validateScorerConfiguration : REQ-CS-004_ValidateScorerConfiguration

  satisfy ConfigureScoring.ScorerConfiguration.saveScorerConfiguration : REQ-CS-005_SaveScorerConfiguration

  satisfy ConfigureScoring.ScorerConfiguration.testScorer : REQ-CS-006_TestScorer

  satisfy ConfigureScoring.ScorerConfiguration.removeScorer : REQ-CS-007_ManageConfiguredScorers

  satisfy ConfigureScoring : REQ-CS-NF-001_UserFriendlyInterface

  satisfy ConfigureScoring : REQ-CS-NF-002_SecureParameterHandling

  // 5. Satisfy Relationships for Reporting

  satisfy Reporting.ReportConfiguration : REQ-REP-001_ConfigureReportingParameters

  satisfy Reporting.DataExtractor : REQ-REP-002_DataExtraction

  satisfy Reporting.DataTransformer : REQ-REP-003_DataTransformation

  satisfy Reporting.Visualizer : REQ-REP-004_Visualization

  satisfy Reporting.ReportGenerator : REQ-REP-005_ReportGeneration

  satisfy Reporting.DataExtractor.useConversationAnalytics : REQ-REP-006_IncludeConversationAnalytics

  satisfy Reporting.ReportGenerator : REQ-REP-007_InteractiveVisualizations

  satisfy Reporting : REQ-REP-NF-001_UserFriendlyInterface

  satisfy Reporting : REQ-REP-NF-002_Performance

  satisfy Reporting : REQ-REP-NF-003_ErrorHandling

  satisfy Reporting : REQ-REP-NF-004_Security

  // Traceability

  trace REQ-AUTH-000 to SystemObjective_SecureAccess {
    text = "Ensures that only authorized users can access protected resources."
  }

  // Indicate that REQ-AUTH-000 derives from the system objective

  derive REQ-AUTH-000 : SystemObjective_SecureAccess

  trace REQ-HP-000 to SystemObjective_SecureAccess {
    text = "HomePage requirements derive from the system objective to ensure secure and user-friendly access."
  }

  derive REQ-HP-000 : SystemObjective_SecureAccess

  // Traceability for WelcomePage Requirements

  trace REQ-WP-000 to SystemObjective_UserInteraction {
      text = "WelcomePage requirements derive from the system objective to ensure intuitive and efficient user interaction."
  }

  // Indicate that REQ-WP-000 derives from the system objective

  derive REQ-WP-000 : SystemObjective_UserInteraction

  // Traceability relationships
  trace REQ-CMEM-000 to SystemObjective_ConfigurableArchitecture {
    text = "ConfigureMemory requirements derive from the system objective to allow configurable architecture."
  }

  // Refinement relationship to existing security requirement
  refine REQ-CMEM-NF-002_SecureParameterHandling : REQ-SEC-002_SecretsManagement

  // Traceability
  trace REQ-PT-000 to SystemObjective_PromptTargetConfiguration {
      text = "SetPromptTarget requirements derive from the system objective to allow users to configure and manage prompt targets."
  }

  // Indicate that REQ-PT-000 derives from the system objective
  derive REQ-PT-000 : SystemObjective_PromptTargetConfiguration

  // Refinement relationship to existing security requirement
  refine REQ-PT-NF-002_SecureParameterHandling : REQ-SEC-002_SecretsManagement

  trace REQ-CD-000 to SystemObjective_UserInteraction {
    text = "ConfigureDatasets requirements derive from the system objective to ensure intuitive and efficient user interaction."
  }

  // Refinement relationship to existing security requirement

  refine REQ-CD-NF-002_Security : REQ-SEC-001_SecureCodingPractices

  // Relationships among requirements

  derive REQ-CD-002_UploadLocalDataset : REQ-CD-001_ChooseDatasetSource
  derive REQ-CD-003_FetchOnlineDataset : REQ-CD-001_ChooseDatasetSource
  derive REQ-CD-004_CombineDatasets : REQ-CD-001_ChooseDatasetSource
  derive REQ-CD-005_TransformDataset : REQ-CD-001_ChooseDatasetSource

  trace REQ-CCV-000 to SystemObjective_ConverterConfiguration {
      text = "ConfigureConverters requirements derive from the system objective to allow users to configure and manage converters."
  }

  // Indicate that REQ-CCV-000 derives from the system objective
  derive REQ-CCV-000 : SystemObjective_ConverterConfiguration

  // Refinement relationship to existing security requirement
  refine REQ-CCV-NF-002_ErrorHandling : REQ-SEC-001_SecureCodingPractices
  refine REQ-CS-NF-002_SecureParameterHandling : REQ-SEC-002_SecretsManagement

  // Traceability and Derive Relationships

  trace REQ-CS-000 to SystemObjective_ScorerConfiguration {
    text = "ConfigureScoring requirements derive from the system objective to allow users to configure and manage scorers."
  }

  trace REQ-CS-000 to SystemObjective_ScorerConfiguration {
    text = "ConfigureScoring requirements derive from the system objective to allow users to configure and manage scorers."
  }

  derive REQ-CS-000 : SystemObjective_ScorerConfiguration

}