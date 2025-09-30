# Kubernetes - MCP Server Analysis

**Repository:** https://github.com/kubernetes-client/python ([github.com](https://github.com/kubernetes-client/python))  
**Installation:** `pip install kubernetes` ([pypi.org](https://pypi.org/project/kubernetes/))  
**Main Entry Point:** `kubernetes.client`, `kubernetes.config`. ([kubernetes.io](https://kubernetes.io/docs/reference/generated/kubernetes-api/v1.27/))

Brief description (MCP-focused): The kubernetes Python SDK provides a comprehensive, programmatically accessible interface to the Kubernetes REST API. It enables the management of all Kubernetes resources, including core infrastructure components like Pods, Nodes, and Services, as well as application-level constructs such as Deployments, StatefulSets, and Custom Resources.1 The library is the officially supported Python client maintained by the Kubernetes SIG API Machinery.1A critical characteristic of this SDK for Management and Control Plane (MCP) architecture is that its structure, method names, and model classes are not arbitrarily designed. Instead, they are auto-generated directly from the canonical Kubernetes OpenAPI specification.3 This direct, machine-enforced correspondence between an API endpoint (e.g., POST /api/v1/namespaces/{namespace}/pods) and a corresponding SDK method (e.g., create_namespaced_pod) provides a highly predictable and stable interface. This predictability is a foundational advantage for MCP development. It allows for the construction of rule-based automation engines that can interact with Kubernetes resources generically, rather than requiring a hardcoded library of functions for every resource type. Consequently, an MCP built on this SDK can be designed to be forward-compatible. As new resources are added to the Kubernetes API and the SDK is regenerated, a well-designed MCP can automatically support them, significantly reducing long-term maintenance overhead and ensuring the control plane evolves in lockstep with Kubernetes itself.

## Authentication Setup

For server-side automation, such as in an MCP, authentication must be non-interactive, stateless, and capable of managing multiple, distinct target clusters. While the SDK supports loading credentials from a local kubeconfig file (config.load_kube_config()) or automatically from within a cluster pod (config.load_incluster_config()), these methods are ill-suited for a scalable MCP.5 The kubeconfig method couples the application to a local file system and user-specific context, which is fragile in containerized environments. The incluster method couples the application to the specific cluster it is running in, preventing it from managing external clusters.The most robust and flexible approach for an MCP is the direct, programmatic configuration of the client using a bearer token. This method completely decouples the client's identity and target from its execution environment. The MCP's identity is defined entirely by the token and API server URL it is provided at runtime. This architectural decoupling is paramount, as it allows the MCP to be deployed anywhere—on-premises, in a cloud virtual machine, or within a dedicated management cluster—and still manage any target Kubernetes cluster for which it possesses valid credentials. This capability is the cornerstone of building a true multi-cluster, multi-cloud, and hybrid management platform.

### Recommended Auth Method
**Method:** Service Account Bearer Token
**Setup:** To configure authentication for a target cluster, a dedicated Service Account with narrowly-scoped permissions should be created. This ensures the MCP operates under the principle of least privilege.

Create a Service Account: For each target cluster, create a dedicated ServiceAccount in a specific namespace (e.g., mcp-system).7
Bash
kubectl create serviceaccount mcp-agent -n mcp-system
Define Permissions: Create a Role or ClusterRole that grants the exact permissions required by the MCP. For example, to manage Deployments and Pods in the default namespace:YAML# mcp-role.yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  namespace: default
  name: mcp-manager-role
rules:
- apiGroups: ["apps"]
  resources: ["deployments"]
  verbs: ["get", "list", "create", "patch", "delete"]
- apiGroups: [""]
  resources: ["pods"]
  verbs: ["get", "list"]
Apply this with kubectl apply -f mcp-role.yaml.Bind the Role: Create a RoleBinding to grant the permissions defined in the Role to the ServiceAccount.7YAML# mcp-rolebinding.yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: mcp-manager-binding
  namespace: default
subjects:
- kind: ServiceAccount
  name: mcp-agent
  namespace: mcp-system
roleRef:
  kind: Role
  name: mcp-manager-role
  apiGroup: rbac.authorization.k8s.io
Apply this with kubectl apply -f mcp-rolebinding.yaml.Generate a Token: Generate a long-lived API token for the ServiceAccount. While newer Kubernetes versions favor short-lived tokens via the TokenRequest API, a long-lived token stored as a Secret is often more practical for server-to-server integration.7YAML# mcp-token-secret.yaml
apiVersion: v1
kind: Secret
metadata:
  name: mcp-agent-token
  namespace: mcp-system
  annotations:
    kubernetes.io/service-account.name: "mcp-agent"
type: kubernetes.io/service-account-token
Apply this, then extract the token:Bashkubectl get secret mcp-agent-token -n mcp-system -o jsonpath='{.data.token}' | base64 --decode
Secure Storage: The extracted token, along with the cluster's API server URL, should be stored securely in a vault or encrypted configuration store accessible by the MCP server.Python# MCP server authentication pattern
from kubernetes import client

# These values would be loaded from a secure vault for a specific target cluster
API_SERVER_URL = "https://<your-cluster-api-server-url>"
SERVICE_ACCOUNT_TOKEN = "your_extracted_service_account_token"

# 1. Create a client configuration object
configuration = client.Configuration()

# 2. Set the API server host
configuration.host = API_SERVER_URL

# 3. Configure the bearer token
configuration.api_key["authorization"] = SERVICE_ACCOUNT_TOKEN
configuration.api_key_prefix["authorization"] = "Bearer"

# 4. Configure SSL verification
# For production, provide the path to the cluster's CA certificate.
# For development or clusters with self-signed certs, you may disable verification.
# configuration.ssl_ca_cert = '/path/to/ca.crt'
configuration.verify_ssl = False

# 5. Create a general-purpose API client with the configuration
api_client = client.ApiClient(configuration)

# 6. Instantiate the specific API group clients needed for operations
core_v1_api = client.CoreV1Api(api_client)
apps_v1_api = client.AppsV1Api(api_client)
Resource Types & CRUD OperationsThe Kubernetes API is organized into logical groups (e.g., core, apps, batch), and the Python SDK mirrors this structure precisely. To manage a specific resource, an MCP must instantiate the corresponding API client class. For example, all operations on Pods and Services are handled by the CoreV1Api class, while Deployments and StatefulSets are managed via the AppsV1Api class.9 Understanding this mapping is the first step in building resource management tools.The following table provides a high-level mapping from Kubernetes API groups to the primary SDK client classes that an MCP will use.API Group/VersionPrimary SDK ClassManaged Resource Types (Examples)core/v1kubernetes.client.CoreV1ApiPod, Service, Namespace, ConfigMap, Secret, Node, PersistentVolumeapps/v1kubernetes.client.AppsV1ApiDeployment, StatefulSet, DaemonSet, ReplicaSetbatch/v1kubernetes.client.BatchV1ApiJob, CronJobrbac.authorization.k8s.io/v1kubernetes.client.RbacAuthorizationV1ApiRole, ClusterRole, RoleBinding, ClusterRoleBindingapiextensions.k8s.io/v1kubernetes.client.ApiextensionsV1ApiCustomResourceDefinitionBelow are detailed breakdowns of the most common resource types relevant to MCP automation.Deployment (apps/v1)Primary Class: kubernetes.client.AppsV1ApiDescription: A Deployment provides declarative updates for Pods and ReplicaSets. It is the standard and most common way to manage the lifecycle of stateless applications in Kubernetes.CRUD Operations:CREATE: create_namespaced_deployment(namespace, body) - Create a new Deployment.READ: read_namespaced_deployment(name, namespace) - Retrieve a single Deployment by its name.LIST: list_namespaced_deployment(namespace) or list_deployment_for_all_namespaces() - List multiple Deployments.UPDATE: patch_namespaced_deployment(name, namespace, body) or replace_namespaced_deployment(name, namespace, body) - Modify an existing Deployment. The patch method is generally preferred for targeted changes, such as scaling replicas, as it is more efficient than replacing the entire object.DELETE: delete_namespaced_deployment(name, namespace) - Remove a Deployment and its associated ReplicaSets and Pods.Key Parameters:name (str): The unique name of the Deployment within its namespace.namespace (str): The namespace where the Deployment resides.body (client.V1Deployment): The full Deployment object definition, constructed using the SDK's model classes. This is required for create, patch, and replace operations.2Python# MCP tool mapping examples
# Assumes 'apps_v1_api' is an initialized AppsV1Api client
namespace = "production"
deployment_name = "api-server"

# CREATE tool
# The 'body' would be constructed by the MCP based on user/system input
deployment_body = client.V1Deployment(...) # A complete V1Deployment object definition
apps_v1_api.create_namespaced_deployment(namespace=namespace, body=deployment_body)

# READ tool
deployment = apps_v1_api.read_namespaced_deployment(name=deployment_name, namespace=namespace)

# LIST tool
deployments = apps_v1_api.list_namespaced_deployment(namespace=namespace)

# UPDATE tool (patching replicas)
patch_body = {"spec": {"replicas": 5}}
apps_v1_api.patch_namespaced_deployment(name=deployment_name, namespace=namespace, body=patch_body)

# DELETE tool
apps_v1_api.delete_namespaced_deployment(name=deployment_name, namespace=namespace)
Pod (core/v1)Primary Class: kubernetes.client.CoreV1ApiDescription: A Pod is the smallest and simplest unit in the Kubernetes object model that you create or deploy. It represents a single instance of a running process in a cluster. While Deployments are used to manage Pods, direct interaction is sometimes necessary for debugging or specific workflows.CRUD Operations:CREATE: create_namespaced_pod(namespace, body) - Create a new Pod.READ: read_namespaced_pod(name, namespace) - Get a single Pod by name.LIST: list_namespaced_pod(namespace) or list_pod_for_all_namespaces() - List Pods.UPDATE: patch_namespaced_pod(name, namespace, body) or replace_namespaced_pod(name, namespace, body) - Modify an existing Pod. Note that most fields of a Pod's spec are immutable after creation.DELETE: delete_namespaced_pod(name, namespace) - Remove a Pod.Key Parameters:name (str): The name of the Pod.namespace (str): The namespace where the Pod resides.body (client.V1Pod): The complete V1Pod object definition for create/update operations.Python# MCP tool mapping examples
# Assumes 'core_v1_api' is an initialized CoreV1Api client
namespace = "logging"
pod_name = "fluentd-aggregator-0"

# CREATE tool (less common for Pods, usually managed by a higher-level controller)
pod_body = client.V1Pod(...)
core_v1_api.create_namespaced_pod(namespace=namespace, body=pod_body)

# READ tool
pod = core_v1_api.read_namespaced_pod(name=pod_name, namespace=namespace)

# LIST tool
pods = core_v1_api.list_namespaced_pod(namespace=namespace, label_selector="app=fluentd")

# UPDATE tool (e.g., adding a label)
patch_body = {"metadata": {"labels": {"processed": "true"}}}
core_v1_api.patch_namespaced_pod(name=pod_name, namespace=namespace, body=patch_body)

# DELETE tool
core_v1_api.delete_namespaced_pod(name=pod_name, namespace=namespace)
Service (core/v1)Primary Class: kubernetes.client.CoreV1ApiDescription: A Service is an abstract way to expose an application running on a set of Pods as a network service. It provides a stable endpoint (IP address and DNS name) for a group of Pods, whose own IPs are ephemeral.CRUD Operations:CREATE: create_namespaced_service(namespace, body) - Create a new Service.READ: read_namespaced_service(name, namespace) - Get a single Service by name.LIST: list_namespaced_service(namespace) or list_service_for_all_namespaces() - List Services.UPDATE: patch_namespaced_service(name, namespace, body) - Modify an existing Service.DELETE: delete_namespaced_service(name, namespace) - Remove a Service.Key Parameters:name (str): The name of the Service.namespace (str): The namespace where the Service resides.body (client.V1Service): The complete V1Service object definition.12Python# MCP tool mapping examples
# Assumes 'core_v1_api' is an initialized CoreV1Api client
namespace = "production"
service_name = "api-server-svc"

# CREATE tool
service_body = client.V1Service(
    api_version="v1",
    kind="Service",
    metadata=client.V1ObjectMeta(name=service_name),
    spec=client.V1ServiceSpec(
        selector={"app": "api-server"},
        ports=
    )
)
core_v1_api.create_namespaced_service(namespace=namespace, body=service_body)

# READ tool
service = core_v1_api.read_namespaced_service(name=service_name, namespace=namespace)

# LIST tool
services = core_v1_api.list_namespaced_service(namespace=namespace)

# UPDATE tool (changing the target port)
patch_body = {"spec": {"ports":}}
core_v1_api.patch_namespaced_service(name=service_name, namespace=namespace, body=patch_body)

# DELETE tool
core_v1_api.delete_namespaced_service(name=service_name, namespace=namespace)
Resource Operations for MCP ToolsThis section provides a consolidated reference for the specific SDK methods that map directly to CRUD operations. It is designed to be a quick-reference guide for developers building MCP automation tools.CRUD Operations SummaryThe method names follow a highly consistent pattern: [action]_[namespaced]_[resource].Create Operations:create_namespaced_pod(namespace, body) - Create a new Pod.create_namespaced_service(namespace, body) - Create a new Service.12create_namespaced_deployment(namespace, body) - Create a new Deployment.2create_namespaced_stateful_set(namespace, body) - Create a new StatefulSet.14create_namespaced_job(namespace, body) - Create a new Job.create_namespace(body) - Create a new Namespace.create_namespaced_config_map(namespace, body) - Create a new ConfigMap.create_namespaced_secret(namespace, body) - Create a new Secret.Read Operations:read_namespaced_pod(name, namespace) - Get a single Pod by name.list_namespaced_pod(namespace) - List all Pods in a specific namespace.9list_pod_for_all_namespaces() - List all Pods across all namespaces.4read_namespaced_deployment(name, namespace) - Get a single Deployment by name.16list_namespaced_deployment(namespace) - List all Deployments in a specific namespace.2list_deployment_for_all_namespaces() - List all Deployments across all namespaces.16read_namespaced_service(name, namespace) - Get a single Service by name.list_namespaced_service(namespace) - List all Services in a specific namespace.9Update Operations:patch_namespaced_pod(name, namespace, body) - Partially update a Pod's metadata or spec.replace_namespaced_pod(name, namespace, body) - Replace an entire Pod's specification.patch_namespaced_deployment(name, namespace, body) - Partially update a Deployment, e.g., for scaling.2replace_namespaced_deployment(name, namespace, body) - Replace an entire Deployment's specification.patch_namespaced_service(name, namespace, body) - Partially update a Service.replace_namespaced_service(name, namespace, body) - Replace an entire Service's specification.Delete Operations:delete_namespaced_pod(name, namespace, body=client.V1DeleteOptions()) - Delete a Pod.delete_namespaced_deployment(name, namespace, body=client.V1DeleteOptions()) - Delete a Deployment.2delete_namespaced_service(name, namespace, body=client.V1DeleteOptions()) - Delete a Service.delete_namespace(name, body=client.V1DeleteOptions()) - Delete a Namespace.delete_collection_namespaced_deployment(namespace) - Delete all Deployments in a namespace.13Detailed Operation DocumentationThis section provides in-depth documentation for key operations listed above, tailored for integration into an MCP.create_namespaced_deployment(namespace, body)Purpose: Creates a new Deployment resource within a specified namespace. This operation is asynchronous on the server side; the method returns successfully once the Deployment object is persisted in the cluster's data store (etcd), but the underlying Pods may still be in the process of being created and scheduled.MCP Tool Use Case: This method would be the backend for an MCP tool named "Deploy Application". The tool would present a user interface or accept API parameters for application details (image name, replica count, ports, environment variables), construct the V1Deployment object (body), and call this method to instantiate the application in the target cluster.Parameters:namespace (str): The target namespace for the new Deployment. This namespace must already exist in the cluster.body (kubernetes.client.V1Deployment): A fully-formed V1Deployment model object that defines the desired state of the Deployment. This includes its metadata (name, labels), spec (replicas), selector, and pod template (template).Returns: kubernetes.client.V1Deployment. The object returned is the representation of the Deployment as it was created in the API server, including server-populated fields like uid, resource_version, and creation_timestamp.Python# MCP-ready example
from kubernetes import client

# Assume 'apps_v1_api' is an initialized AppsV1Api client
# The MCP would build this body dynamically from tool inputs
container = client.V1Container(
    name="webapp",
    image="nginx:1.21.6",
    ports=[client.V1ContainerPort(container_port=80)],
)
template = client.V1PodTemplateSpec(
    metadata=client.V1ObjectMeta(labels={"app": "webapp"}),
    spec=client.V1PodSpec(containers=[container]),
)
spec = client.V1DeploymentSpec(
    replicas=2,
    template=template,
    selector=client.V1LabelSelector(match_labels={"app": "webapp"}),
)
deployment_body = client.V1Deployment(
    api_version="apps/v1",
    kind="Deployment",
    metadata=client.V1ObjectMeta(name="webapp-deployment"),
    spec=spec,
)

result = apps_v1_api.create_namespaced_deployment(
    namespace="default", body=deployment_body
)
# Expected result structure (simplified):
# {
#   "api_version": "apps/v1",
#   "kind": "Deployment",
#   "metadata": {"name": "webapp-deployment", "namespace": "default",...},
#   "spec": {"replicas": 2,...},
#   "status": {}
# }
list_pod_for_all_namespaces()Purpose: Retrieves a list of all Pods across all namespaces in the cluster. This is a powerful but potentially expensive operation on large clusters.MCP Tool Use Case: This method is ideal for building cluster-wide monitoring and reporting tools. For example, an MCP dashboard could use this call to display a global view of all running pods, their statuses, and resource consumption. It could also be used for a "Find Pod" tool that searches the entire cluster by name or label.Parameters:This method accepts numerous optional parameters for filtering, such as label_selector, field_selector, limit, and _continue for pagination.Returns: kubernetes.client.V1PodList. This is a list-type object containing two main fields: metadata (with list-level information like resource_version) and items (a standard Python list of V1Pod objects).Python# MCP-ready example
# Assume 'core_v1_api' is an initialized CoreV1Api client
pod_list_response = core_v1_api.list_pod_for_all_namespaces(watch=False)

for pod in pod_list_response.items:
    print(f"NS: {pod.metadata.namespace}, Pod: {pod.metadata.name}, Status: {pod.status.phase}")

# Expected result structure (simplified):
# {
#   "api_version": "v1",
#   "kind": "PodList",
#   "metadata": {"resource_version": "12345",...},
#   "items": [
#     {"metadata": {"name": "pod-a", "namespace": "ns-1"},...},
#     {"metadata": {"name": "pod-b", "namespace": "ns-2"},...}
#   ]
# }
patch_namespaced_deployment(name, namespace, body)Purpose: Modifies an existing Deployment resource using a patch strategy. This is more efficient than a full replace operation for small changes, as it only transmits the modified fields to the API server.MCP Tool Use Case: This is the core method for tools that perform scaling or rolling update operations. An MCP "Scale Application" tool would take a deployment name and a new replica count, construct a minimal patch body, and call this method. Similarly, an "Update Image" tool would patch the spec.template.spec.containers.image field to trigger a rolling update.Parameters:name (str): The name of the Deployment to patch.namespace (str): The namespace of the Deployment.body (dict or object): The patch payload. For a strategic merge patch (the default), this is a dictionary representing the fragment of the Deployment object to be changed.Returns: kubernetes.client.V1Deployment. The full state of the Deployment object after the patch has been applied.Python# MCP-ready example
# Assume 'apps_v1_api' is an initialized AppsV1Api client
deployment_name = "webapp-deployment"
namespace = "default"

# MCP tool for scaling replicas
patch_body = {
    "spec": {
        "replicas": 3
    }
}
updated_deployment = apps_v1_api.patch_namespaced_deployment(
    name=deployment_name, namespace=namespace, body=patch_body
)
print(f"Deployment scaled to {updated_deployment.spec.replicas} replicas.")

# Expected result structure:
# The full V1Deployment object, with spec.replicas now set to 3.
Common Usage Patterns for MCPThe following patterns represent fundamental workflows that will form the basis of most MCP tools built with this SDK.Pattern: List ResourcesThis is the most common read-only pattern, used for populating dashboards, generating reports, or as the first step in a more complex workflow. The key aspect is that all list methods return a list object (e.g., V1PodList, V1DeploymentList) which contains the actual resource objects in its .items attribute.4Python# Standard listing pattern for namespaced resources
# Assumes 'core_v1_api' is an initialized CoreV1Api client
pod_list = core_v1_api.list_namespaced_pod(namespace="kube-system")
print("Pods in kube-system namespace:")
for pod in pod_list.items:
    print(f"- {pod.metadata.name} (Status: {pod.status.phase})")

# Standard listing pattern for cluster-scoped resources (or all namespaces)
# Assumes 'apps_v1_api' is an initialized AppsV1Api client
deployment_list = apps_v1_api.list_deployment_for_all_namespaces()
print("\nAll Deployments in the cluster:")
for deployment in deployment_list.items:
    print(f"- NS: {deployment.metadata.namespace}, Name: {deployment.metadata.name}, Replicas: {deployment.spec.replicas}")
Pattern: CRUD WorkflowThis pattern demonstrates the full lifecycle of a resource, a common sequence in automated testing, temporary resource provisioning, or complex MCP operations. This example illustrates the create-read-update-delete flow for a Deployment, adapted from common examples.2Python# --- 1. CREATE ---
# (Using the 'deployment_body' object from the Detailed Operation Documentation section)
print("1. Creating Deployment...")
created_deployment = apps_v1_api.create_namespaced_deployment(
    namespace="default", body=deployment_body
)
print(f"   -> Created deployment: {created_deployment.metadata.name}")

# --- 2. READ ---
# Verify the creation by reading the resource back from the API server
print("\n2. Reading Deployment...")
read_deployment = apps_v1_api.read_namespaced_deployment(
    name=created_deployment.metadata.name, namespace="default"
)
print(f"   -> Read deployment, initial replicas: {read_deployment.spec.replicas}")

# --- 3. UPDATE ---
# Modify the resource using a patch operation (e.g., scale down)
print("\n3. Updating (Patching) Deployment...")
patch_body = {"spec": {"replicas": 1}}
updated_deployment = apps_v1_api.patch_namespaced_deployment(
    name=created_deployment.metadata.name, namespace="default", body=patch_body
)
print(f"   -> Patched deployment, new replicas: {updated_deployment.spec.replicas}")

# --- 4. DELETE ---
# Clean up the resource
print("\n4. Deleting Deployment...")
delete_status = apps_v1_api.delete_namespaced_deployment(
    name=created_deployment.metadata.name, namespace="default"
)
print("   -> Deployment deletion initiated.")
Technical Details for MCP IntegrationSuccessful integration of the SDK into a production MCP requires careful handling of API errors, rate limits, and pagination.Error HandlingThe SDK centralizes all HTTP API errors into a single exception class: kubernetes.client.rest.ApiException.17 This design choice has a profound implication for MCP development: robust error handling is not possible by catching different exception types. Instead, the logic must inspect the HTTP status code contained within the exception object to determine the nature of the failure.An MCP must differentiate between various error conditions. For instance, a 404 Not Found error when checking for a resource's existence is often an expected condition, not a failure. Conversely, a 401 Unauthorized or 403 Forbidden error indicates a critical misconfiguration of credentials or permissions that must be logged and escalated. Since the SDK raises ApiException for all these cases, inspecting the e.status attribute is the only way to implement this differential logic.18 This is a fundamental and non-negotiable error handling pattern for this SDK.Exception Types:kubernetes.client.rest.ApiException - The base exception for all API-level errors. It contains details from the HTTP response.e.status (int): The HTTP status code (e.g., 404, 503).e.reason (str): The HTTP reason phrase (e.g., "Not Found").e.body (str): The raw response body, often containing a detailed JSON error message from the API server.Common Status Codes to Handle:401 Unauthorized: Credentials (bearer token) are missing, invalid, or expired.403 Forbidden: Credentials are valid, but the authenticated Service Account lacks the necessary RBAC permissions for the requested operation.404 Not Found: The requested resource (e.g., a specific Pod or Deployment) does not exist.409 Conflict: An attempt was made to create a resource that already exists.422 Unprocessable Entity: The request body (e.g., a V1Deployment object) is syntactically correct but semantically invalid according to the API server's validation rules.429 Too Many Requests: The request was rejected due to server-side API rate limiting.Python# Error handling example for MCP tools
from kubernetes.client.rest import ApiException

def get_deployment_safely(apps_api, name, namespace):
    try:
        deployment = apps_api.read_namespaced_deployment(name=name, namespace=namespace)
        return {"success": True, "data": deployment.to_dict()}
    except ApiException as e:
        if e.status == 404:
            # Handle "not found" gracefully as a non-fatal condition
            return {"success": False, "error": "Deployment not found", "details": e.reason}
        elif e.status == 403:
            # Handle permission errors as a critical configuration issue
            return {"success": False, "error": "Permission denied", "details": "Check MCP agent RBAC roles."}
        else:
            # For other unexpected API errors, return a generic error
            return {"success": False, "error": "API Error", "details": f"Status {e.status}: {e.reason}"}

# Example usage:
# result = get_deployment_safely(apps_v1_api, "non-existent-app", "default")
# if not result['success']:
#     print(f"Failed to get deployment: {result['error']} - {result['details']}")
Rate Limits and PaginationRate Limit Check: The Kubernetes API server employs rate limiting to protect itself from abusive or misbehaving clients.21 The SDK does not provide a proactive method to check the current rate limit status (e.g., client.get_rate_limit_status()). Instead, rate limiting is a reactive mechanism. When an MCP exceeds its allowed request quota, the API server will respond with an HTTP 429 Too Many Requests status code. The SDK will wrap this response in an ApiException with e.status == 429. Therefore, the MCP's design must incorporate a reactive "act-then-handle-failure" model. The error handling logic for ApiException must include a specific case for status 429 that implements an exponential backoff-and-retry strategy to avoid overwhelming the API server.Pagination: For any list_* operation that could return a large number of resources, the Kubernetes API uses a token-based pagination system to ensure performance and stability. A list request can include a limit parameter to control the number of items returned per page. If more results exist beyond the current page, the response object's metadata field will contain a _continue token.23 To retrieve the next page, this token must be passed as the _continue parameter in the subsequent list call. The process is complete when the _continue token in a response is None or an empty string. An MCP must implement this looping mechanism to guarantee it retrieves all resources.Python# Pagination example for MCP
def get_all_namespaced_pods(core_v1_api, namespace):
    """
    Retrieves all pods in a namespace, handling pagination automatically.
    """
    all_pods =
    continue_token = None
    while True:
        try:
            # Set a reasonable limit per API call to avoid large responses
            pod_list = core_v1_api.list_namespaced_pod(
                namespace=namespace,
                limit=250,
                _continue=continue_token
            )
        except ApiException as e:
            # Handle potential errors during a long-running list operation
            print(f"Error listing pods: {e}")
            break

        all_pods.extend(pod_list.items)
        continue_token = pod_list.metadata._continue

        if not continue_token:
            # The API server returned no more continue token, so we are done.
            break

    return all_pods

# Example usage:
# all_default_pods = get_all_namespaced_pods(core_v1_api, "default")
# print(f"Found {len(all_default_pods)} total pods in the 'default' namespace.")
