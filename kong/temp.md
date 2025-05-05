
### API1:2023 - Broken Object Level Authorization (BOLA)

* **Description:** APIs tend to expose endpoints handling object identifiers, creating a wide attack surface for Object Level Access Control issues. Authorization checks should verify if the authenticated user has permission to access the specific object requested [7].
* **Sub-issues:**
    * Attackers manipulate object IDs (e.g., UUIDs, integers) in requests to access data belonging to other users because the server fails to validate ownership or permissions for the *specific* object ID [7].
    * In agentic systems, this extends to controlling access to objects *manipulated by agent tools* (e.g., an agent attempting to read/write a file object belonging to another user via an MCP tool). Unauthorized actions performed by agents through tools often stem from underlying BOLA issues in the tool's implementation [22].
* **Relationship to other API issues:** Distinct from API5 (Function Level Authorization, which controls *actions*) and API3 (Object Property Level Authorization, which controls access to *fields within* an object). A failure here bypasses data access controls directly. Effective authentication (API2) is necessary but not sufficient if BOLA exists. Exploitation can be automated using fuzzing or specialized testing tools [3], [6].
* **Relationship to MCP issues:**
    * If an agent (acting as an MCP Client [21] or A2A Client [20]) calls a traditional API using an object ID, that target API still needs robust BOLA checks.
    * More directly, if an MCP Server tool [21] (e.g., `readFile(user_id, file_id)` or the filesystem tools described in [22]) provides access to user-specific objects based on IDs, BOLA checks are critical *within the tool's implementation*. The check must validate the permissions of the *original user* who initiated the agent request, not just the agent's service identity.
    * An agent with a compromised identity (an API2 issue manifested in agent authentication protocols like A2A or MCP client/server AuthN [20], [21]) could exploit BOLA in target APIs or tools.
    * A compromised or malicious agent/tool (an API10 issue) could actively probe for and exploit BOLA vulnerabilities in other services or tools it interacts with.
    * Malicious code execution or remote access achieved via vulnerable MCP tools [22] can bypass BOLA checks at the application layer entirely by interacting directly with backend resources.
* **Causative API Design Decisions:**
    * Relying on client-provided IDs without rigorous server-side validation of the requesting user's ownership or permission for *that specific object* [7].
    * Using easily guessable or predictable object identifiers (e.g., sequential integers) [7].
    * Lack of a centralized or consistently applied authorization mechanism across all data-accessing functions [11].
    * Designing agent tools (within MCP/A2A frameworks) that access user-specific resources based solely on IDs passed from the agent, without validating against the original user's context or permissions [21], [22].
    * Insufficient AuthZ checks within the implementation of MCP server tools or A2A agent capabilities [20], [21].
    * Insufficient testing focused specifically on authorization bypass scenarios, both for standard APIs and agent tool interactions [3], [6].
* **Mitigating API Design Decisions:**
    * Implement strong, non-guessable object identifiers (e.g., UUIDs) [7].
    * **Crucially:** Implement robust, server-side authorization checks in *every* function (API endpoint or agent tool logic) that accesses a data resource using a client/agent-supplied identifier. These checks must validate that the *initiating user* (identified via session/token, potentially passed through the agent context) has the necessary permissions for the *specific object ID* being requested [7], [20], [21].
    * Utilize a centralized authorization mechanism (e.g., policy engine, middleware integrated with user session data) to enforce checks consistently across both traditional APIs and agent-accessible tools [11].
    * When designing MCP tools or A2A agent capabilities, ensure authorization logic correctly uses the *end-user's identity and permissions*, not just the agent's service identity [20], [21].
    * Leverage automated testing frameworks, potentially enhanced by LLMs, specifically designed to generate test cases targeting BOLA vulnerabilities in both APIs and agent interactions [3].
    * Employ detailed logging of access attempts and authorization decisions to detect potential attacks [12], [21].
    * Regularly audit and test authorization logic, including within agent tools [6], [22]. Apply the principle of least privilege rigorously to agent capabilities [21].

### API2:2023 - Broken Authentication

* **Description:** Authentication mechanisms are implemented incorrectly, allowing attackers to compromise tokens, bypass checks, or assume other users' identities [7]. Compromising identity compromises overall API security.
* **Sub-issues:** Weak password policies, credential stuffing, brute-force attacks without rate limiting/lockout, insecure token transmission (e.g., in URL), improper JWT validation (e.g., accepting `alg=none`, weak secrets, ignoring expiration), using plain text or weakly hashed passwords, insufficient multi-factor authentication (MFA) [7]. In agent systems, this extends to insecure agent-to-agent (A2A) or agent-to-tool (MCP) authentication, including forged/stolen tokens or insecure key management [20], [21], [22].
* **Relationship to other API issues:** Authentication precedes authorization (API1, API3, API5); a break here compromises all subsequent controls. Misconfigurations (API8) like weak default keys or improper TLS settings directly impact authentication security. Unrestricted Resource Consumption (API4) can manifest as brute-force attacks against authentication endpoints. Credential theft attacks (demonstrated via MCP tools in [22]) directly target this vulnerability.
* **Relationship to MCP issues:**
    * MCP requires secure authentication between the Client and Server components [21], [18]. Lack of strong authentication allows unauthorized clients (malicious agents or users) to invoke tools or access resources.
    * A2A protocol relies heavily on secure agent authentication (often via OAuth/OIDC/JWT) to establish trust between collaborating agents [20]. Weaknesses allow agent impersonation [20].
    * The tools invoked via MCP might require their own authentication credentials (e.g., API keys for third-party services). If these are managed insecurely by the MCP server or exposed (e.g., via environment variables accessible by other tools like `printEnv` [22]), it constitutes an authentication failure. Credential Theft (CT) attacks explicitly target these [22].
    * Standard authentication attacks like token replay or validation bypass apply equally to agent protocol communications [20].
* **Causative API Design Decisions:**
    * Implementing custom, non-standard authentication protocols instead of proven standards like OAuth2/OIDC for APIs and agent interactions [7], [20].
    * Failing to enforce strong password complexity requirements or MFA for user accounts that control agents or access APIs [7].
    * Using weak, default, or easily guessable keys/secrets for signing tokens (e.g., JWTs) used in API or agent communication flows [7], [20].
    * Transmitting credentials or tokens insecurely (e.g., in GET request URLs, over HTTP) during API calls or agent protocol exchanges [7], [9], [21].
    * Lack of rate limiting or account lockout mechanisms on authentication endpoints (for users or agents), enabling brute-force attacks [7], [21].
    * Improper validation of tokens (e.g., JWTs) in APIs, MCP servers, or A2A agents (not checking signature, expiration, issuer, audience) [7], [20].
    * Storing credentials (e.g., API keys for MCP tools) insecurely, such as in environment variables accessible via general-purpose tools [22].
* **Mitigating API Design Decisions:**
    * Utilize standard, well-vetted authentication frameworks and protocols (OAuth2, OpenID Connect, mTLS) for both user-API and agent-agent/agent-tool interactions [7], [20], [21]. Avoid "reinventing the wheel" [7].
    * Enforce strong password policies and mandate MFA for users [7]. Consider strong authentication methods (e.g., mTLS, signed requests) for agents/tools [21], [20].
    * Implement strict rate limiting and account lockout mechanisms on all authentication endpoints [7].
    * Use strong, randomly generated, and securely managed secrets for token signing; validate tokens rigorously (signature, expiration, claims) in receiving APIs and agent protocol endpoints [7], [20].
    * Ensure all communication transmitting credentials or tokens uses HTTPS/TLS [7], [21].
    * Require re-authentication (e.g., password confirmation) for sensitive user operations [7].
    * Employ specialized testing frameworks to identify authentication flaws in APIs and agent protocols [3].
    * Use ML-based systems to detect anomalous authentication patterns or brute-force attempts [9].
    * Centralize token issuance via dedicated OAuth servers rather than letting individual APIs or agents issue tokens [17].
    * Securely manage credentials needed by MCP tools (e.g., using secrets management vaults, not environment variables accessible by tools like `printEnv`) [21], [22]. Restrict access to tools that could expose credentials [22].

### API3:2023 - Broken Object Property Level Authorization (BOPLA)

* **Description:** Combines previous Excessive Data Exposure and Mass Assignment risks, focusing on the lack of or improper authorization checks at the *individual property level* within an object [7]. Allows unauthorized reading or modification of specific object fields.
* **Sub-issues:**
    * **Excessive Data Exposure:** API endpoints or agent tools return more data fields (properties) than the client/agent requires or the user is authorized to see, relying on the client/agent to filter [7]. This can leak sensitive information [12], [21].
    * **Mass Assignment:** Allowing client/agent input to directly update internal object properties without validation or an allow-list, enabling attackers (or malicious/compromised agents) to modify sensitive or hidden properties (e.g., `isAdmin`, `balance`) [7].
* **Relationship to other API issues:** Granular control compared to BOLA (API1). While BOLA protects the whole object, API3 protects specific fields. Security Misconfiguration (API8) can lead to verbose responses causing data exposure. Improper Inventory Management (API9) means sensitive properties might be exposed without developers realizing it. Data leakage is a key concern [12], [21].
* **Relationship to MCP issues:**
    * An MCP Server tool or resource could return an object with excessive sensitive properties to the requesting agent/LLM, potentially violating user privacy or exposing internal state [21].
    * An agent could use an MCP tool (e.g., `edit_file` [22], or a hypothetical `update_user_profile` tool) to perform mass assignment if the tool binds input data directly to backend object properties without filtering based on allowed fields or user permissions.
    * Data leakage is a significant MCP risk if servers/tools expose sensitive data fields inappropriately [21]. The interaction between multiple agents (A2A [20]) could also lead to unintended property exposure if one agent shares data received from a tool with another agent that shouldn't see specific fields.
* **Causative API Design Decisions:**
    * Designing API responses or MCP tool/resource outputs to return entire database records or internal object representations using generic serialization methods (`to_json()`, `to_string()`) without considering property sensitivity or user permissions [7], [21].
    * Using frameworks that automatically bind all incoming client/agent data fields to internal object properties without an explicit allow-list of mutable properties (Mass Assignment) [7]. This applies to both traditional APIs and the backend logic of MCP tools.
    * Lack of schema definition and enforcement for API or MCP tool responses, allowing sensitive data fields to leak [11], [21].
    * Absence of fine-grained authorization checks determining if the user (acting via an agent) should be able to *read* or *write* specific properties of an object they otherwise have access to [7].
* **Mitigating API Design Decisions:**
    * **Prevent Exposure:** Never rely on the client/agent to filter data. Design API responses and MCP tool/resource outputs to *only* include properties necessary for the specific use case and authorized for the specific user [7], [21]. Use DTOs or specific view models.
    * **Prevent Mass Assignment:** Avoid automatically binding client/agent input to internal objects. Use an allow-list approach, explicitly defining which properties are permitted for client/agent modification in both APIs and MCP tool logic [7].
    * Implement schema-based request and response validation for APIs and MCP interactions, ensuring only expected properties are accepted and returned [7], [21].
    * Apply authorization checks not just at the object level (API1) but also at the property level, verifying read/write permissions for sensitive fields based on the initiating user's context [7].
    * Utilize API governance tools like linters to check for patterns leading to excessive data exposure [11].
    * Implement monitoring focused on detecting sensitive data in API/MCP responses [12].
    * Audit data flows between agents and tools to prevent leakage of sensitive properties [20].

### API4:2023 - Unrestricted Resource Consumption

* **Description:** Failure to impose limits on resources (CPU, memory, bandwidth, storage, number of requests, third-party service calls) consumed by API or agent tool requests, leading to Denial of Service (DoS) or increased operational costs [7]. This is a common concern for practitioners managing APIs [1].
* **Sub-issues:** Lack of rate limiting, missing limits on payload sizes (e.g., file uploads, large JSON), unbounded query results (no pagination), expensive API/tool operations without quotas, DoS attacks targeting resource exhaustion [7], [21]. Agents can potentially initiate resource exhaustion attacks against MCP servers or other agents [18], [21].
* **Relationship to other API issues:** Can be exploited via Broken Authentication (API2) if attackers use compromised accounts/agents to bypass per-user limits. Improper Inventory Management (API9) might leave old APIs/tools without proper limits exposed. Sensitive Business Flows (API6) abuse often involves high resource consumption.
* **Relationship to MCP issues:**
    * An agent could flood an MCP Server with requests, causing DoS on the server or the underlying resources/tools it connects to [21].
    * An agent could invoke a computationally or financially expensive MCP tool excessively.
    * Inefficient agent workflows involving recursive or numerous MCP calls could exhaust resources on the client, server, or LLM host [18].
    * Similar DoS risks exist in A2A communication between agents [20].
* **Causative API Design Decisions:**
    * Not implementing any rate limiting or request throttling mechanisms on API endpoints or MCP/A2A server endpoints [7], [21].
    * Allowing clients/agents to request unbounded numbers of records without pagination defaults or maximums [7].
    * Not defining or enforcing limits on request sizes, string lengths, number of elements in arrays, or file upload sizes in APIs or MCP tool inputs [7], [21].
    * Exposing computationally or financially expensive operations via APIs or MCP tools (e.g., complex searches, report generation, third-party API calls like SMS) without per-user, per-agent, or per-key quotas or concurrency limits [7].
    * Designing agent logic with inefficient loops or recursive calls to tools/APIs, leading to resource exhaustion [18].
* **Mitigating API Design Decisions:**
    * Implement robust rate limiting based on factors like user ID, API key, agent ID, or IP address for both traditional APIs and MCP/A2A endpoints [7], [1]. API Gateways are commonly used for this [1], [15].
    * Define and enforce maximum sizes for request bodies, query parameters, headers, and individual fields (e.g., string length, array elements) in API and MCP/A2A interactions [7], [21].
    * Implement pagination with sensible defaults and enforced maximum page sizes for endpoints or tools returning collections [7].
    * Set execution timeouts for API requests, MCP tool executions, and A2A task processing [7], [21].
    * Limit the number of operations allowed within a single request (e.g., GraphQL batching, multiple tool calls within one agent turn) [7].
    * Monitor resource consumption per API consumer/agent and apply stricter limits or quotas if necessary [12], [21].
    * Set spending limits or billing alerts for integrated third-party services called by APIs or MCP tools [7].
    * Use containerization or serverless functions to enforce limits on memory, CPU, and processes for API backends and MCP servers [7].
    * Design agent workflows carefully to avoid unnecessary recursion or excessive tool calls [18].

### API5:2023 - Broken Function Level Authorization (BFLA)

* **Description:** Access control policies are incorrectly applied at the function/operation level, allowing users or agents acting on their behalf to access functions or perform actions (e.g., admin operations, sensitive tool executions) they are not authorized for [7].
* **Sub-issues:** Regular users accessing admin endpoints, users/agents performing unauthorized actions (create, update, delete) by changing HTTP methods or invoking restricted tools [7], [22]. Users/agents accessing functionality intended for different roles/groups [7].
* **Relationship to other API issues:** Different from BOLA (API1)/BOPLA (API3) which deal with *data* access; BFLA deals with *action* or *capability* access. Security Misconfiguration (API8) can cause BFLA if authorization rules are set incorrectly. Improper Inventory Management (API9) may leave administrative endpoints or powerful tools exposed without proper documentation or checks.
* **Relationship to MCP issues:**
    * An agent, possibly authenticated correctly (passes API2), might invoke an MCP tool (e.g., `delete_user`, `edit_system_file` [22]) it shouldn't have permission for based on the *end user's* permissions.
    * The MCP server needs to perform function-level authorization checks *within its own logic* before executing a tool, based on the user context passed from the client/host [21]. Relying only on the tool's internal checks might be insufficient.
    * Demonstrated attacks show agents using filesystem tools (`edit_file`, `write_file`) for unauthorized privileged actions like modifying `.bashrc` or `authorized_keys` [22]. This is a BFLA issue within the context of the MCP server enabling those tools.
    * A2A task delegation requires careful authorization checks to ensure the calling agent has the right to request the specified task from the remote agent [20].
* **Causative API Design Decisions:**
    * Relying on client-side or agent-side logic to control access to functions/tools rather than enforcing checks server-side (in the API backend or MCP/A2A server) [16].
    * Mixing administrative and regular user endpoints/tools within the same API structure without distinct and rigorous authorization checks for each function/tool based on user context [7], [22].
    * Using easily guessable names or paths for administrative API endpoints or powerful MCP tools without proper authorization enforcement [7].
    * Having complex or poorly defined user roles and permissions, making it hard to implement checks correctly for both API functions and agent capabilities [7], [20].
    * Implementing authorization logic inconsistently across different API functions or MCP tools [11].
    * MCP servers granting broad execution permissions to tools (like filesystem access) without scoping them based on the initiating user's privileges [22].
* **Mitigating API Design Decisions:**
    * Implement a centralized and consistent authorization module invoked by *all* business functions in APIs and before executing *any* tool via MCP/A2A [7], [11].
    * Enforce a "deny by default" policy, requiring explicit grants for specific roles/users to access each API function or agent tool/capability [7], [20].
    * Rigorously check permissions based on the *initiating user's role and context* for *every* incoming API request or agent tool invocation before executing the logic [7], [21].
    * Clearly separate administrative functions/tools from regular user ones (e.g., using different API base paths, requiring specific admin roles/permissions for tool invocation) [7].
    * Design authorization logic based on the required *action* (function/tool level), not just the data being accessed [7].
    * Conduct thorough testing, including attempting to access functions/tools directly with different user roles and methods [6], [22].
    * Apply the principle of least privilege rigorously to agent tool access, restricting dangerous tools like arbitrary file editors or command executors [21], [22].

### API6:2023 - Unrestricted Access to Sensitive Business Flows

* **Description:** APIs or agent-accessible tools expose business flows (e.g., purchasing, commenting, booking) without controls to prevent automated abuse that could harm the business (e.g., scalping, spamming, resource hoarding), even if individual API calls seem secure [7].
* **Sub-issues:** Scalping (buying all available stock), spamming content (comments, reviews), denial of inventory (booking all slots), exploiting logical flaws in multi-step processes, generating excessive load on specific business logic [7]. Agents can automate these abuses at scale [18]. RADE attacks could trick agents into performing harmful steps in a business flow [22].
* **Relationship to other API issues:** Often involves high resource consumption (API4), but the primary impact is on the business logic/outcome. Exploitation may involve bypassing authentication (API2) or authorization (API1/API5) on intermediate steps. Requires understanding the inventory of flows and involved components (API9).
* **Relationship to MCP issues:**
    * AI agents can use MCP/A2A tools to interact with business logic APIs at high speed and scale, amplifying the potential for abuse of sensitive flows [18].
    * Complex workflows involving multiple agents (via A2A [20]) or chained MCP tool calls could bypass controls designed for single-step interactions.
    * Agents might be deliberately programmed or inadvertently tricked (e.g., via RADE attacks [22] or prompt injection) into executing steps of a business flow maliciously or excessively.
    * The logic for controlling sensitive flows might reside partially in the agent and partially in the API/tool, creating potential gaps if not designed cohesively.
* **Causative API Design Decisions:**
    * Failing to identify and analyze critical business flows exposed via APIs or agent tools for potential abuse scenarios [7].
    * Not implementing business-level velocity checks or logical constraints within the API, the agent logic, or the mediating tools (e.g., purchase limits per user/period, sequence validation) [7].
    * Designing APIs or agent tools purely technically without considering the business implications of automated or excessive usage (e.g., assuming human interaction speeds) [16].
    * Lack of monitoring specifically for business flow anomalies (e.g., unusually high success rate for purchases from one source, rapid commenting) [12].
    * Decentralized implementation of flow logic across agents and APIs without end-to-end validation [20].
* **Mitigating API Design Decisions:**
    * Identify and map out critical business flows exposed by APIs and accessible via agents/tools [7].
    * Analyze potential abuse cases for each sensitive flow (scalping, spamming, denial of inventory, logic bypass) considering automated execution by agents [7], [22].
    * Implement business-level restrictions, velocity checks, and sequence validation within the core API logic, enforced regardless of whether access is direct or via an agent/tool [7].
    * Use techniques like device fingerprinting, CAPTCHAs, or behavioral analysis (potentially ML-based [9]) for high-risk flows to deter bots and automated agents [7].
    * Monitor business transactions and user/agent activity patterns for anomalies suggestive of automated abuse [12].
    * Model expected interaction flows (e.g., using Finite State Machines [10]) to detect deviations or unexpected sequences, especially in agent-driven scenarios.
    * Design flows to be resilient and transactional, ensuring atomicity and preventing partial execution exploits.

### API7:2023 - Server-Side Request Forgery (SSRF)

* **Description:** An API or agent tool fetches a remote resource based on a user/agent-supplied URL/URI without proper validation, allowing an attacker to coerce the server into sending requests to unintended destinations, including internal network services [7].
* **Sub-issues:** Scanning internal networks, accessing internal services (cloud metadata, databases, admin interfaces), data exfiltration, interacting with other internal/external systems via the exploited server, potential for Remote Code Execution (RCE) in some cases [7], [13]. SSRF via webhooks in agent protocols [20].
* **Relationship to other API issues:** Can be caused by Security Misconfiguration (API8), such as overly permissive network egress rules or flawed URL parsing libraries. Exploiting SSRF might be easier if inventory of internal systems (API9) is poor. Unsafe Consumption of APIs (API10) can lead to SSRF if a consumed API/tool returns a malicious URL that is then fetched by the agent or calling API.
* **Relationship to MCP issues:**
    * If an MCP Server tool is designed to fetch resources based on a URL provided by the agent (e.g., "summarize this webpage," "get data from this API endpoint"), it's vulnerable to SSRF if the URL isn't validated [21].
    * If a compromised MCP Server or tool *returns* a malicious URL, and the consuming agent blindly fetches it, SSRF occurs in the agent's environment.
    * The optional push notification feature in the A2A protocol uses webhooks. If the A2A server doesn't rigorously validate the client-provided webhook URL before sending notifications, it creates an SSRF vulnerability [20].
* **Causative API Design Decisions:**
    * Accepting full URLs, hostnames, or paths from user or agent input to determine the target of a server-side request without strict validation and sanitization [7]. This applies to both API endpoints and MCP tool parameters.
    * Not using or improperly implementing allow-lists for permitted protocols (e.g., only `http`, `https`), domains, IP addresses, and ports for outgoing requests initiated by the API or MCP server/tool [7], [21].
    * Using HTTP client libraries that follow redirects by default without limiting the number of redirects or validating the redirection target against the allow-list [7].
    * Inconsistent URL parsing between validation logic and the actual request library [7].
    * Designing features (APIs, MCP tools, A2A capabilities) that inherently require fetching external resources based on dynamic input (webhooks, URL previews, file imports from URL) without sufficient safeguards [7], [20].
* **Mitigating API Design Decisions:**
    * Strictly validate and sanitize any user or agent-supplied input used to construct target URLs for server-side requests. Avoid accepting full URLs; prefer allowing only specific identifiers or path components [7].
    * Implement and enforce strict allow-lists for permitted protocols (typically `http`, `https`), target domains/IP addresses, and ports for all server-side requests originating from the API or MCP server/tool [7], [21]. Deny by default.
    * Disable HTTP redirects in the client library if not strictly necessary. If required, validate the `Location` header against the allow-list before following the redirect [7].
    * Use robust, well-maintained URL parsing libraries consistently [7].
    * Isolate the network environment where resource fetching occurs (for APIs or MCP servers), limiting its ability to reach sensitive internal services [7], [21].
    * Use dynamic taint analysis techniques to track user/agent-supplied data and detect if it flows into sensitive request-issuing functions [10].
    * Rigorously validate webhook URLs provided by clients in A2A implementations supporting push notifications [20].

### API8:2023 - Security Misconfiguration

* **Description:** Vulnerabilities arising from insecure default settings, incomplete or ad-hoc configurations, missing patches, overly permissive settings (like CORS or file permissions), verbose error messages, or unnecessary enabled features across the API and agent system stack [7], [22].
* **Sub-issues:** Missing security hardening, use of default credentials, unpatched systems, unnecessary HTTP verbs enabled, permissive CORS policies, verbose errors exposing stack traces or internal paths, insecure cloud service permissions, missing TLS or use of weak ciphers/protocols [7]. For agent systems, this includes misconfigured authentication/authorization between components, insecure defaults in MCP/A2A servers, and improper permissions for server processes [20], [21], [22].
* **Relationship to other API issues:** Can be the root cause of many other issues (e.g., weak ciphers for API2, verbose errors for API3, permissive CORS for API7, improper permissions enabling API1/API5 via MCP tools [22]). Lack of inventory (API9) makes consistent configuration management difficult. Evading monitoring (relevant to API6/API9 mitigation) might be possible if monitoring tools rely on standard configurations that are altered [4].
* **Relationship to MCP issues:**
    * Insecure default configurations in standard MCP server implementations (e.g., the filesystem server allowing broad write access) can directly lead to exploits like MCE or RAC [22].
    * Misconfigured authentication or authorization between the MCP Client and Server, or between collaborating A2A agents, can lead to unauthorized access [21], [20].
    * Lack of enforced TLS for MCP or A2A communication channels exposes data in transit [21], [20].
    * Verbose errors returned by MCP servers or tools can leak internal system information useful to attackers [21].
    * Running the MCP server process with excessive operating system permissions allows tools like the filesystem server to modify critical system files [22].
    * Improper configuration of agent frameworks or orchestration platforms [20].
* **Causative API Design Decisions:**
    * Failing to follow security hardening guidelines for all components (OS, web server, application server, database, framework, MCP/A2A servers) [7], [21].
    * Leaving default configurations, accounts, or passwords enabled, especially in packaged MCP server implementations [7], [22].
    * Manual and inconsistent configuration processes across environments instead of using automated tools (e.g., Infrastructure as Code) [11].
    * Lack of a robust patching schedule for all software components, including API frameworks and agent protocol libraries [7].
    * Implementing overly permissive CORS policies (`*`) on API endpoints or MCP servers [7].
    * Not handling exceptions properly in API or MCP tool logic, leading to verbose error messages being returned [7], [21].
    * Deploying MCP servers or agent applications with excessive file system or network permissions [22].
* **Mitigating API Design Decisions:**
    * Establish repeatable hardening processes and use automated tools for configuration management (e.g., IaC) for APIs and agent systems [7], [11], [21].
    * Develop a strict patching policy and process for all components [7].
    * Disable unnecessary HTTP verbs and features on APIs and MCP servers [7].
    * Configure CORS policies with a strict allow-list of trusted origins [7].
    * Implement custom, non-verbose error handling in APIs and MCP tools [7], [21].
    * Enforce secure communication via TLS with up-to-date protocols and strong ciphers for all API and agent protocol traffic [7], [21], [20].
    * Regularly audit configurations (including cloud service permissions and file permissions for MCP servers) and use security scanning tools [11], [21], [22].
    * Utilize API governance frameworks and tools (like linters) to enforce configuration standards [11].
    * Apply the principle of least privilege to the operating system user/process running the MCP server [22].
    * Use security auditing tools like McpSafetyScanner to proactively identify misconfigurations and vulnerabilities in MCP servers [22].

### API9:2023 - Improper Inventory Management

* **Description:** Lack of a complete, accurate, and up-to-date inventory of all APIs, agents, tools, versions, environments, dependencies, and data flows. This leads to exposed "shadow" or "zombie" APIs/agents/tools, often unpatched and insecure [7], [10].
* **Sub-issues:** Exposed non-production environments, outdated/unpatched API/agent versions, lack of documentation leading to misuse or missed security requirements, shadow APIs/agents deployed without oversight, inconsistent security postures between versions/environments, lack of clarity on data flows to third parties [7], [10]. Asset discovery is key [10]. A2A AgentCard spoofing exploits poor inventory/discovery validation [20].
* **Relationship to other API issues:** Fundamental to addressing most other risks. Without knowing what exists, security controls cannot be consistently applied. Old, uninventoried APIs/agents/tools are likely vulnerable (API1, API2, API4, API5, API8). Understanding data flows is crucial for API3 and API10. Defending against hooking evasion [4] requires understanding implementation details, often missing without good inventory/documentation.
* **Relationship to MCP issues:**
    * Crucial to inventory all deployed MCP servers, their versions, the specific tools/resources/prompts they expose, and the environments they run in [21]. Unknown or unmanaged MCP servers (especially powerful ones like filesystem access [22]) pose significant risks.
    * In A2A ecosystems, maintaining an inventory of known/trusted agents and their capabilities (AgentCards) is essential for secure discovery and preventing spoofing [20].
    * Lack of documentation for MCP tools or A2A agent capabilities makes secure consumption (API10) difficult and increases the risk of misuse (API5).
    * Shadow agents or MCP servers deployed outside of governance processes bypass security reviews and policy enforcement [11].
    * Understanding data flows between agents and MCP resources/tools is necessary to manage risks like API3 (Data Exposure) [21].
* **Causative API Design Decisions:**
    * Absence of a centralized API and agent/tool catalog or registry where all components are documented [7], [11], [21].
    * Lack of formal processes for API, agent, and tool lifecycle management (design, deployment, versioning, retirement) [11].
    * Insufficient or outdated documentation standards and practices for APIs and agent capabilities [7], [11], [20].
    * Allowing teams to deploy APIs, MCP servers, or A2A agents without central visibility or security review (leading to shadow components) [7].
    * Not tracking dependencies or data flows between APIs, agents, and integrated services/tools [7], [21].
    * Failing to decommission retired API/agent versions or environments promptly [7].
* **Mitigating API Design Decisions:**
    * Maintain a comprehensive, real-time inventory of all API hosts, endpoints, versions, environments, owners, agents, MCP servers, tools, resources, prompts, A2A AgentCards, and dependencies [7], [10], [20], [21]. Utilize automated discovery tools where possible [10].
    * Implement strong API and agent governance covering the entire lifecycle, including design reviews, documentation standards, versioning strategies, and retirement procedures [11].
    * Use API gateways, service meshes, or agent management platforms to centralize visibility, control, and policy enforcement [1].
    * Automate API/AgentCard/tool documentation generation from code annotations or specifications [7], [11], [20].
    * Regularly scan networks, cloud accounts, and code repositories for undocumented or "shadow" APIs/agents/servers [7].
    * Explicitly retire and block access to deprecated API/agent versions and decommission unused environments [7].
    * Document all integrated services/tools and the data exchanged with them (data flow mapping) [7], [21].
    * Treat non-production deployments handling production data with the same security rigor as production APIs/agents [7].
    * Validate discovered A2A AgentCards against a trusted registry or use signature verification [20].

### API10:2023 - Unsafe Consumption of APIs

* **Description:** Developers or agents implicitly trust data received from third-party APIs, other internal agents (A2A), or tools (MCP), applying weaker security standards (e.g., input validation) compared to direct user input. This leads to vulnerabilities if the consumed source is compromised, malicious, or returns unexpected/malicious data [7].
* **Sub-issues:** Injection attacks (SQLi, XSS, Command Injection) if data from consumed APIs/tools is used directly in sensitive operations, SSRF (API7) if a consumed API/tool returns a malicious URL, DoS if the consumed API/tool is slow/unresponsive, data exposure if interactions are not encrypted, issues from blindly following redirects, agents executing malicious commands/code returned by tools [22], tool poisoning [21], cross-agent attacks [20], RADE attacks [22].
* **Relationship to other API issues:** Can lead to Injection flaws if data is not sanitized. Can lead to SSRF (API7). Security Misconfiguration (API8) in how the external API/tool/agent is called. Requires understanding data flows (API9). Exploits trust assumptions, bypassing AuthN/AuthZ (API2/API1/API5) in downstream actions if the consumed data dictates behavior.
* **Relationship to MCP issues:**
    * This is a central risk in agent ecosystems built with MCP and A2A. Agents *must* treat data and instructions received from MCP tools/resources or other A2A agents as potentially untrusted [21], [20].
    * Failure to validate data from an MCP resource before using it in prompts or subsequent tool calls can lead to prompt injection or incorrect actions [21].
    * Blindly executing commands or code suggested by an MCP tool's output is extremely dangerous, as demonstrated by MCE/RAC attacks [22].
    * Tool poisoning, where malicious actors craft misleading tool descriptions to trick the agent/LLM into harmful actions, is a specific variant of unsafe consumption [21].
    * Agents consuming artifacts or messages from other agents via A2A must validate the content to prevent propagation of malicious data or commands [20].
    * Retrieval-Agent Deception (RADE) attacks are a prime example: the agent unsafely consumes malicious content retrieved via an MCP tool (Chroma) and executes harmful actions suggested by that content using other MCP tools (filesystem, Slack) [22].
* **Causative API Design Decisions:**
    * Agents implicitly trusting the validity, safety, format, or intent of data, instructions, or tool descriptions received from external APIs, MCP tools/resources, or other A2A agents [7], [21], [20], [22].
    * Failing to perform input validation and sanitization on data received via APIs, MCP, or A2A before processing it, using it in prompts, passing it to other components, or rendering it [7], [21].
    * Designing agents to blindly execute instructions, commands, or code snippets returned or suggested by consumed APIs, tools, or agents [22].
    * Lack of secure parsing and handling for structured data received from external sources [20].
    * Not verifying the source or integrity of consumed APIs or tools (e.g., connecting to spoofed MCP servers or agents) [21], [20].
* **Mitigating API Design Decisions:**
    * **Crucially:** Treat data, instructions, and descriptions received from *any* external source (APIs, MCP tools/resources, A2A agents) with the same (or higher) level of scrutiny as direct user input. **Validate** format, type, length; **sanitize** to remove malicious content; **encode** appropriately before use in different contexts [7], [21], [20].
    * **Never** design agents to blindly execute arbitrary code, commands, or highly privileged instructions suggested by external sources [22]. Implement strict sandboxing or interpretation layers if dynamic execution is unavoidable.
    * Always use secure, encrypted channels (HTTPS/TLS) for all interactions with consumed APIs, tools, and agents [7], [21].
    * Implement robust error handling, timeouts, and potentially circuit breaker patterns for external calls [7], [21].
    * Validate and limit redirects when interacting with external APIs/tools/agents [7]. Do not follow blindly [7].
    * Assess the security posture of critical third-party APIs and tools before integration [7], [21].
    * Verify the identity and integrity of consumed APIs/tools/agents (e.g., using mTLS, validating AgentCards) [20], [21].
    * Implement defenses against tool poisoning by carefully validating tool descriptions and potentially restricting tool discovery [21].
    * Defend against RADE by carefully controlling data sources for retrieval agents and validating retrieved content before allowing the agent to act upon it [22].

---

### References

[1] E. dos Santos and S. Casas, “An empirical study of API Management and ISO/IEC SQuaRE: a practitioners’ perspective,” in *XX Workshop de Ingeniería de Software*, CACIC 2023, Rio Gallegos, Argentina, 2023.
[2] E. M. Pasca, R. Erdei, D. Delinschi, and O. Matei, “Augmenting API Security Testing with Automated LLM-Driven Test Generation,” in *Intelligent Systems Design and Applications*, H. Quintián *et al.*, Eds., Cham: Springer Nature Switzerland, 2024, pp. 112–121. doi: 10.1007/978-3-031-75016-8\_11.
[3] E. M. Pasca, R. Erdei, D. Delinschi, and O. Matei, “Enhancing API Security Testing Against BOLA and Authentication Vulnerabilities Through an LLM-Enhanced Framework,” in *Soft Computing Models in Industrial and Environmental Applications*, H. Quintián *et al.*, Eds., Cham: Springer Nature Switzerland, 2025, pp. 231–240. doi: 10.1007/978-3-031-75010-6\_23.
[4] C. Assaiante, S. Nicchi, D. C. D'Elia, and L. Querzoni, “Evading Userland API Hooking, Again: Novel Attacks and a Principled Defense Method,” in *Detection of Intrusions and Malware, and Vulnerability Assessment*, F. Maggi *et al.*, Eds., Cham: Springer Nature Switzerland, 2024, pp. 150–173. doi: 10.1007/978-3-031-64171-8\_8.
[5] T. Dias, E. Maia, and I. Praça, “FuzzTheREST: An Intelligent Automated Black-Box RESTful API Fuzzer,” in *Distributed Computing and Artificial Intelligence*, R. Chinthaginjala *et al.*, Eds., Cham: Springer Nature Switzerland, 2025, pp. 160–169. doi: 10.1007/978-3-031-82073-1\_16.
[6] A. Golmohammadi, M. Zhang, and A. Arcuri, “Testing RESTful APIs: A Survey,” *ACM Trans. Softw. Eng. Methodol.*, vol. 33, no. 1, pp. 27:1–27:41, Nov. 2023, doi: 10.1145/3617175.
[7] OWASP API Security Project, “OWASP API Security Top 10 2023,” OWASP Foundation, 2023. [Online]. Available: `owasp-api-security.txt` (provided file).
[8] V. Atlidakis, P. Godefroid, and M. Polishchuk, “Checking Security Properties of Cloud Service REST APIs,” in *Proc. IEEE Int. Conf. Softw. Test. Verif. Valid. (ICST)*, 2020, pp. 387–397. doi: 10.1109/ICST46399.2020.00043.
[9] I. Sharma, A. Kaur, K. Kaushik, and G. Chhabra, “Machine Learning-Based Detection of API Security Attacks,” in *Data Science and Applications*, S. J. Nanda *et al.*, Eds., Singapore: Springer Nature Singapore, 2024, pp. 285–297. doi: 10.1007/978-981-99-7814-4\_23.
[10] R. Sun, Q. Wang, and L. Guo, “Research Towards Key Issues of API Security,” in *Proc. China Natl. Conf. Emerg. Comput. Technol. (CNCERT)*, W. Lu *et al.*, Eds., Singapore: Springer Nature Singapore, 2022, pp. 179–192. doi: 10.1007/978-981-16-9229-1\_11.
[11] M. Ahmad, J. Geewax, A. Macvean, D. Karger, and K.-L. Ma, “API Governance at Scale,” in *Proc. 46th Int. Conf. Softw. Eng.: Softw. Eng. Pract. (ICSE-SEIP '24)*, Lisbon, Portugal, Apr. 2024, pp. 430–440. doi: 10.1145/3639477.3639713.
[12] R. E. C. Valencia, A. C. Villegas, A. F. Morales, and C. Á. Carmona, “Monitoring Software Tool to Prevent Data Leaks in a RESTful API,” in *Communication, Innovation and Insights Forum*, R. Valencia-García *et al.*, Eds., Cham: Springer Nature Switzerland, 2025, pp. 187–199. doi: 10.1007/978-3-031-75702-0\_14.
[13] M. S. Khan, R. S. F. Siam, and M. A. Adnan, “A framework for checking and mitigating the security vulnerabilities of cloud service RESTful APIs,” *Serv. Orient. Comput. Appl.*, May 2024, doi: 10.1007/s11761-024-00404-z.
[14] V. Atlidakis, P. Godefroid, and M. Polishchuk, “RESTler: Stateful REST API Fuzzing,” in *Proc. 41st Int. Conf. Softw. Eng. (ICSE '19)*, Montreal, QC, Canada, May 2019, pp. 748–758. doi: 10.1109/ICSE.2019.00083.
[15] F. Aydemir and F. Başçiftçi, “Performance and Availability Analysis of API Design Techniques for API Gateways,” *Arab. J. Sci. Eng.*, Aug. 2024, doi: 10.1007/s13369-024-09474-9.
[16] J. Bloch, “How to design a good API and why it matters,” presented at the Companion to the 21st ACM SIGPLAN Conf. Object-Oriented Program. Syst. Lang. Appl. (OOPSLA '06), Portland, OR, USA, Oct. 2006, pp. 506–508. doi: 10.1145/1176617.1176622.
[17] Curity, “API Security Best Practices,” Curity Identity Server. [Online]. Available: [https://curity.io/resources/learn/api-security-best-practices/](https://curity.io/resources/learn/api-security-best-practices/) (Accessed: May 2025).
[18] Y. Yang *et al.*, “A Survey of AI Agent Protocols,” *arXiv preprint arXiv:2504.16736*, Apr. 2025. [Online]. Available: [https://arxiv.org/abs/2504.16736](https://arxiv.org/abs/2504.16736)
[19] P. P. Ray, “A Survey on Model Context Protocol: Architecture, State-of-the-art, Challenges and Future Directions,” *Affiliation not available*, Apr. 2025. (Note: File was empty, citation based on filename/metadata).
[20] I. Habler, K. Huang, V. S. Narajala, and P. Kulkarni, “Building A Secure Agentic AI Application Leveraging Google’s A2A Protocol,” *arXiv preprint arXiv:2504.16902*, Apr. 2025. [Online]. Available: [https://arxiv.org/abs/2504.16902](https://arxiv.org/abs/2504.16902)
[21] V. S. Narajala and I. Habler, “Enterprise-Grade Security for the Model Context Protocol (MCP): Frameworks and Mitigation Strategies,” *arXiv preprint arXiv:2504.08623*, Apr. 2025. [Online]. Available: [https://arxiv.org/abs/2504.08623](https://arxiv.org/abs/2504.08623)
[22] B. Radosevich and J. T. Halloran, “MCP Safety Audit: LLMs with the Model Context Protocol Allow Major Security Exploits,” *arXiv preprint arXiv:2504.03767*, Apr. 2025. [Online]. Available: [https://arxiv.org/abs/2504.03767](https://arxiv.org/abs/2504.03767)