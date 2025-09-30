#!/usr/bin/env python3
import os
import inspect
from typing import Optional, Dict, Any
import logging

from fastmcp import FastMCP
from kubernetes import client
from kubernetes.client.rest import ApiException

# Optional: enable basic logging for production-like tracing
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("kubernetes-mcp")

# FastMCP application
app = FastMCP("kubernetes-mcp")

# Global cache for initialized API clients
_APIS: Dict[str, Any] = {}


def _to_jsonable(obj: Any) -> Any:
    """Convert SDK objects to JSON-serializable format"""
    try:
        # If the object provides a to_dict() method (common in Kubernetes client),
        # prefer using it for a clean serializable representation.
        if hasattr(obj, "to_dict"):
            return obj.to_dict()
        if isinstance(obj, list):
            return [_to_jsonable(i) for i in obj]
        if isinstance(obj, dict):
            return {k: _to_jsonable(v) for k, v in obj.items()}
        if isinstance(obj, (str, int, float, bool)) or obj is None:
            return obj
        # Fallback to string representation
        return str(obj)
    except Exception:
        return str(obj)


def _get_default_token() -> Optional[str]:
    """Return the first available token from environment variables."""
    token_vars = ["API_TOKEN", "AUTH_TOKEN", "ACCESS_TOKEN", "KUBERNETES_TOKEN"]
    for var in token_vars:
        val = os.getenv(var)
        if val:
            return val
    return None


def _init_client(token: Optional[str] = None, api_server_url: Optional[str] = None,
                 verify_ssl: bool = True) -> Dict[str, Any]:
    """
    Initialize Kubernetes API clients with a token-based or config-based approach.

    Priority:
    1) If token and api_server_url are provided, use token-based authentication against the provided API server.
    2) Otherwise, fall back to in-cluster config or kubeconfig if available.
    """
    global _APIS
    apis: Dict[str, Any] = {}

    token_to_use = token or _get_default_token()
    server_url = api_server_url or os.getenv("KUBERNETES_API_SERVER")

    # Token-based initialization (GitHub-style) when both token and server URL are available
    if token_to_use and server_url:
        try:
            configuration = client.Configuration()
            configuration.host = server_url.rstrip("/")
            # Bearer token setup
            configuration.api_key = {"authorization": token_to_use}
            configuration.api_key_prefix = {"authorization": "Bearer"}
            configuration.verify_ssl = verify_ssl
            api_client = client.ApiClient(configuration)

            apis = {
                "core": client.CoreV1Api(api_client),
                "apps": client.AppsV1Api(api_client),
                "batch": client.BatchV1Api(api_client),
                "rbac": client.RbacAuthorizationV1Api(api_client),
            }

            _APIS = apis
            logger.info("Initialized Kubernetes clients using token-based auth against %s", server_url)
            return apis
        except Exception as ex:
            logger.warning("Token-based initialization failed: %s", ex)

    # Fallback: in-cluster config or kubeconfig
    try:
        from kubernetes import config as k8s_config

        # Try in-cluster first
        try:
            k8s_config.load_incluster_config()
            logger.info("Loaded in-cluster Kubernetes config")
        except Exception:
            # Fall back to kubeconfig
            k8s_config.load_kube_config()
            logger.info("Loaded kubeconfig for Kubernetes")

        k8s_api_client = client.ApiClient()
        apis = {
            "core": client.CoreV1Api(k8s_api_client),
            "apps": client.AppsV1Api(k8s_api_client),
            "batch": client.BatchV1Api(k8s_api_client),
            "rbac": client.RbacAuthorizationV1Api(k8s_api_client),
        }
        _APIS = apis
        logger.info("Initialized Kubernetes clients via kubeconfig/in-cluster config")
        return apis
    except Exception as ex:
        logger.error("Failed to initialize Kubernetes clients via config: %s", ex)
        raise RuntimeError("Could not initialize Kubernetes client configuration") from ex


def _get_apis(token: Optional[str] = None, api_server_url: Optional[str] = None) -> Dict[str, Any]:
    """Return initialized Kubernetes API clients, reinitializing if needed."""
    if not _APIS:
        # Try to initialize with provided token/server or rely on env/config
        return _init_client(token=token, api_server_url=api_server_url, verify_ssl=True)
    # If token override is requested, reinitialize to honor it
    if token is not None or api_server_url is not None:
        return _init_client(token=token, api_server_url=api_server_url, verify_ssl=True)
    return _APIS


@app.tool()
def kubernetes_list_all_pods(limit: int = 250, _continue: Optional[str] = None, token: Optional[str] = None,
                             api_server_url: Optional[str] = None) -> dict:
    """
    List all Pods across all namespaces with pagination support.

    Parameters:
        limit: Maximum number of Pods per API call.
        _continue: Pagination token for continuing a previous request.
        token: Optional bearer token to authenticate against the target cluster.
        api_server_url: Optional API server URL for token-based auth flow.

    Returns:
        dict: Tool response in the standard MCP tooling format.
    """
    operation = "kubernetes_list_all_pods"
    signature = "def kubernetes_list_all_pods(limit: int = 250, _continue: Optional[str] = None) -> dict"

    try:
        apis = _get_apis(token=token, api_server_url=api_server_url)
        core_v1 = apis.get("core")
        if core_v1 is None:
            raise RuntimeError("CoreV1Api client is not initialized")

        all_pods = []
        cont_token = _continue
        while True:
            resp = core_v1.list_pod_for_all_namespaces(limit=limit, _continue=cont_token)
            all_pods.extend([_to_jsonable(p) for p in resp.items])
            cont_token = resp.metadata._continue
            if not cont_token:
                break

        data = all_pods
        return {
            "operation": operation,
            "status": "success",
            "data": data,
            "class": "kubernetes.client.CoreV1Api",
            "method_signature": signature,
            "parameters_used": {"limit": limit, "_continue": _continue},
            "error_message": None
        }
    except ApiException as e:
        error = f"ApiException: {e.status} {e.reason}"
        return {
            "operation": operation,
            "status": "error",
            "data": None,
            "class": "kubernetes.client.CoreV1Api",
            "method_signature": signature,
            "parameters_used": {"limit": limit, "_continue": _continue},
            "error_message": error
        }
    except Exception as e:
        return {
            "operation": operation,
            "status": "error",
            "data": None,
            "class": "kubernetes.client.CoreV1Api",
            "method_signature": signature,
            "parameters_used": {"limit": limit, "_continue": _continue},
            "error_message": str(e)
        }


@app.tool()
def kubernetes_get_pod(name: str, namespace: str, token: Optional[str] = None,
                      api_server_url: Optional[str] = None) -> dict:
    """
    Read a single Pod by name in a given namespace.

    Parameters:
        name: Pod name.
        namespace: Pod's namespace.
        token, api_server_url: Optional auth overrides.

    Returns:
        dict
    """
    operation = "kubernetes_get_pod"
    signature = "def kubernetes_get_pod(name: str, namespace: str) -> dict"

    try:
        apis = _get_apis(token=token, api_server_url=api_server_url)
        core_v1 = apis.get("core")
        if core_v1 is None:
            raise RuntimeError("CoreV1Api client is not initialized")

        pod = core_v1.read_namespaced_pod(name=name, namespace=namespace)
        data = _to_jsonable(pod)
        return {
            "operation": operation,
            "status": "success",
            "data": data,
            "class": "kubernetes.client.CoreV1Api",
            "method_signature": signature,
            "parameters_used": {"name": name, "namespace": namespace},
            "error_message": None
        }
    except ApiException as e:
        error = f"ApiException: {e.status} {e.reason}"
        return {
            "operation": operation,
            "status": "error",
            "data": None,
            "class": "kubernetes.client.CoreV1Api",
            "method_signature": signature,
            "parameters_used": {"name": name, "namespace": namespace},
            "error_message": error
        }
    except Exception as e:
        return {
            "operation": operation,
            "status": "error",
            "data": None,
            "class": "kubernetes.client.CoreV1Api",
            "method_signature": signature,
            "parameters_used": {"name": name, "namespace": namespace},
            "error_message": str(e)
        }


@app.tool()
def kubernetes_list_all_deployments(all_namespaces: bool = True, namespace: Optional[str] = None,
                                    limit: int = 100, token: Optional[str] = None,
                                    api_server_url: Optional[str] = None) -> dict:
    """
    List Deployments across the cluster or within a specific namespace.

    Parameters:
        all_namespaces: If True, list across all namespaces; otherwise, list within `namespace`.
        namespace: Namespace to list deployments from (when all_namespaces is False).
        limit: Pagination limit per request.
        token, api_server_url: Optional auth overrides.

    Returns:
        dict
    """
    operation = "kubernetes_list_all_deployments"
    signature = "def kubernetes_list_all_deployments(all_namespaces: bool = True, namespace: Optional[str] = None, limit: int = 100) -> dict"

    try:
        apis = _get_apis(token=token, api_server_url=api_server_url)
        apps_v1 = apis.get("apps")
        if apps_v1 is None:
            raise RuntimeError("AppsV1Api client is not initialized")

        if all_namespaces:
            resp = apps_v1.list_deployment_for_all_namespaces(limit=limit)
        else:
            if not namespace:
                raise ValueError("namespace must be provided when all_namespaces=False")
            resp = apps_v1.list_namespaced_deployment(namespace=namespace, limit=limit)

        data = _to_jsonable(resp)
        return {
            "operation": operation,
            "status": "success",
            "data": data,
            "class": "kubernetes.client.AppsV1Api",
            "method_signature": signature,
            "parameters_used": {"all_namespaces": all_namespaces, "namespace": namespace, "limit": limit},
            "error_message": None
        }
    except ApiException as e:
        error = f"ApiException: {e.status} {e.reason}"
        return {
            "operation": operation,
            "status": "error",
            "data": None,
            "class": "kubernetes.client.AppsV1Api",
            "method_signature": signature,
            "parameters_used": {"all_namespaces": all_namespaces, "namespace": namespace, "limit": limit},
            "error_message": error
        }
    except Exception as e:
        return {
            "operation": operation,
            "status": "error",
            "data": None,
            "class": "kubernetes.client.AppsV1Api",
            "method_signature": signature,
            "parameters_used": {"all_namespaces": all_namespaces, "namespace": namespace, "limit": limit},
            "error_message": str(e)
        }


@app.tool()
def kubernetes_create_deployment(namespace: str, body: Any, token: Optional[str] = None,
                               api_server_url: Optional[str] = None) -> dict:
    """
    Create a new Deployment in the given namespace.

    Parameters:
        namespace: Target namespace.
        body: Deployment body as a dict or kubernetes client Deployment object.
        token, api_server_url: Optional auth overrides.

    Returns:
        dict
    """
    operation = "kubernetes_create_deployment"
    signature = "def kubernetes_create_deployment(namespace: str, body: dict) -> dict"

    try:
        apis = _get_apis(token=token, api_server_url=api_server_url)
        apps_v1 = apis.get("apps")
        if apps_v1 is None:
            raise RuntimeError("AppsV1Api client is not initialized")

        deployment_body = body
        if isinstance(body, dict):
            deployment_body = client.V1Deployment(**body)

        created = apps_v1.create_namespaced_deployment(namespace=namespace, body=deployment_body)
        data = _to_jsonable(created)
        return {
            "operation": operation,
            "status": "success",
            "data": data,
            "class": "kubernetes.client.AppsV1Api",
            "method_signature": signature,
            "parameters_used": {"namespace": namespace, "body": body},
            "error_message": None
        }
    except ApiException as e:
        error = f"ApiException: {e.status} {e.reason}"
        return {
            "operation": operation,
            "status": "error",
            "data": None,
            "class": "kubernetes.client.AppsV1Api",
            "method_signature": signature,
            "parameters_used": {"namespace": namespace, "body": body},
            "error_message": error
        }
    except Exception as e:
        return {
            "operation": operation,
            "status": "error",
            "data": None,
            "class": "kubernetes.client.AppsV1Api",
            "method_signature": signature,
            "parameters_used": {"namespace": namespace, "body": body},
            "error_message": str(e)
        }


@app.tool()
def kubernetes_patch_deployment(name: str, namespace: str, body: Any, token: Optional[str] = None,
                               api_server_url: Optional[str] = None) -> dict:
    """
    Patch an existing Deployment.

    Parameters:
        name: Deployment name.
        namespace: Namespace.
        body: Patch payload as dict.
        token, api_server_url: Optional auth overrides.

    Returns:
        dict
    """
    operation = "kubernetes_patch_deployment"
    signature = "def kubernetes_patch_deployment(name: str, namespace: str, body: dict) -> dict"

    try:
        apis = _get_apis(token=token, api_server_url=api_server_url)
        apps_v1 = apis.get("apps")
        if apps_v1 is None:
            raise RuntimeError("AppsV1Api client is not initialized")

        patch_body = body
        updated = apps_v1.patch_namespaced_deployment(name=name, namespace=namespace, body=patch_body)
        data = _to_jsonable(updated)
        return {
            "operation": operation,
            "status": "success",
            "data": data,
            "class": "kubernetes.client.AppsV1Api",
            "method_signature": signature,
            "parameters_used": {"name": name, "namespace": namespace, "body": body},
            "error_message": None
        }
    except ApiException as e:
        error = f"ApiException: {e.status} {e.reason}"
        return {
            "operation": operation,
            "status": "error",
            "data": None,
            "class": "kubernetes.client.AppsV1Api",
            "method_signature": signature,
            "parameters_used": {"name": name, "namespace": namespace, "body": body},
            "error_message": error
        }
    except Exception as e:
        return {
            "operation": operation,
            "status": "error",
            "data": None,
            "class": "kubernetes.client.AppsV1Api",
            "method_signature": signature,
            "parameters_used": {"name": name, "namespace": namespace, "body": body},
            "error_message": str(e)
        }


@app.tool()
def kubernetes_delete_deployment(name: str, namespace: str, token: Optional[str] = None,
                                api_server_url: Optional[str] = None) -> dict:
    """
    Delete a Deployment.

    Parameters:
        name: Deployment name.
        namespace: Namespace.
        token, api_server_url: Optional auth overrides.

    Returns:
        dict
    """
    operation = "kubernetes_delete_deployment"
    signature = "def kubernetes_delete_deployment(name: str, namespace: str) -> dict"

    try:
        apis = _get_apis(token=token, api_server_url=api_server_url)
        apps_v1 = apis.get("apps")
        if apps_v1 is None:
            raise RuntimeError("AppsV1Api client is not initialized")

        resp = apps_v1.delete_namespaced_deployment(name=name, namespace=namespace)
        data = _to_jsonable(resp)
        return {
            "operation": operation,
            "status": "success",
            "data": data,
            "class": "kubernetes.client.AppsV1Api",
            "method_signature": signature,
            "parameters_used": {"name": name, "namespace": namespace},
            "error_message": None
        }
    except ApiException as e:
        error = f"ApiException: {e.status} {e.reason}"
        return {
            "operation": operation,
            "status": "error",
            "data": None,
            "class": "kubernetes.client.AppsV1Api",
            "method_signature": signature,
            "parameters_used": {"name": name, "namespace": namespace},
            "error_message": error
        }
    except Exception as e:
        return {
            "operation": operation,
            "status": "error",
            "data": None,
            "class": "kubernetes.client.AppsV1Api",
            "method_signature": signature,
            "parameters_used": {"name": name, "namespace": namespace},
            "error_message": str(e)
        }


@app.tool()
def kubernetes_list_all_services(all_namespaces: bool = True, namespace: Optional[str] = None,
                                  limit: int = 100, token: Optional[str] = None,
                                  api_server_url: Optional[str] = None) -> dict:
    """
    List Services across the cluster or within a specific namespace.

    Parameters:
        all_namespaces: If True, list across all namespaces; else list within 'namespace'.
        namespace: Optional namespace to query when all_namespaces is False.
        limit: Pagination limit.
        token, api_server_url: Optional auth overrides.

    Returns:
        dict
    """
    operation = "kubernetes_list_all_services"
    signature = "def kubernetes_list_all_services(all_namespaces: bool = True, namespace: Optional[str] = None, limit: int = 100) -> dict"

    try:
        apis = _get_apis(token=token, api_server_url=api_server_url)
        core_v1 = apis.get("core")
        if core_v1 is None:
            raise RuntimeError("CoreV1Api client is not initialized")

        if all_namespaces:
            resp = core_v1.list_service_for_all_namespaces(limit=limit)
        else:
            if namespace is None:
                raise ValueError("namespace must be provided when all_namespaces is False")
            resp = core_v1.list_namespaced_service(namespace=namespace, limit=limit)

        data = _to_jsonable(resp)
        return {
            "operation": operation,
            "status": "success",
            "data": data,
            "class": "kubernetes.client.CoreV1Api",
            "method_signature": signature,
            "parameters_used": {"all_namespaces": all_namespaces, "namespace": namespace, "limit": limit},
            "error_message": None
        }
    except ApiException as e:
        error = f"ApiException: {e.status} {e.reason}"
        return {
            "operation": operation,
            "status": "error",
            "data": None,
            "class": "kubernetes.client.CoreV1Api",
            "method_signature": signature,
            "parameters_used": {"all_namespaces": all_namespaces, "namespace": namespace, "limit": limit},
            "error_message": error
        }
    except Exception as e:
        return {
            "operation": operation,
            "status": "error",
            "data": None,
            "class": "kubernetes.client.CoreV1Api",
            "method_signature": signature,
            "parameters_used": {"all_namespaces": all_namespaces, "namespace": namespace, "limit": limit},
            "error_message": str(e)
        }


@app.tool()
def kubernetes_create_service(namespace: str, body: Any, token: Optional[str] = None,
                            api_server_url: Optional[str] = None) -> dict:
    """
    Create a Service in the given namespace.

    Parameters:
        namespace: Target namespace.
        body: Service body as dict or V1Service object.
        token, api_server_url: Optional auth overrides.

    Returns:
        dict
    """
    operation = "kubernetes_create_service"
    signature = "def kubernetes_create_service(namespace: str, body: dict) -> dict"

    try:
        apis = _get_apis(token=token, api_server_url=api_server_url)
        core_v1 = apis.get("core")
        if core_v1 is None:
            raise RuntimeError("CoreV1Api client is not initialized")

        service_body = body
        if isinstance(body, dict):
            service_body = client.V1Service(**body)

        created = core_v1.create_namespaced_service(namespace=namespace, body=service_body)
        data = _to_jsonable(created)
        return {
            "operation": operation,
            "status": "success",
            "data": data,
            "class": "kubernetes.client.CoreV1Api",
            "method_signature": signature,
            "parameters_used": {"namespace": namespace, "body": body},
            "error_message": None
        }
    except ApiException as e:
        error = f"ApiException: {e.status} {e.reason}"
        return {
            "operation": operation,
            "status": "error",
            "data": None,
            "class": "kubernetes.client.CoreV1Api",
            "method_signature": signature,
            "parameters_used": {"namespace": namespace, "body": body},
            "error_message": error
        }
    except Exception as e:
        return {
            "operation": operation,
            "status": "error",
            "data": None,
            "class": "kubernetes.client.CoreV1Api",
            "method_signature": signature,
            "parameters_used": {"namespace": namespace, "body": body},
            "error_message": str(e)
        }


@app.tool()
def kubernetes_patch_service(name: str, namespace: str, body: Any, token: Optional[str] = None,
                            api_server_url: Optional[str] = None) -> dict:
    """
    Patch an existing Service.

    Parameters:
        name: Service name.
        namespace: Namespace.
        body: Patch payload (dict).
        token, api_server_url: Optional auth overrides.

    Returns:
        dict
    """
    operation = "kubernetes_patch_service"
    signature = "def kubernetes_patch_service(name: str, namespace: str, body: dict) -> dict"

    try:
        apis = _get_apis(token=token, api_server_url=api_server_url)
        core_v1 = apis.get("core")
        if core_v1 is None:
            raise RuntimeError("CoreV1Api client is not initialized")

        patch_body = body
        updated = core_v1.patch_namespaced_service(name=name, namespace=namespace, body=patch_body)
        data = _to_jsonable(updated)
        return {
            "operation": operation,
            "status": "success",
            "data": data,
            "class": "kubernetes.client.CoreV1Api",
            "method_signature": signature,
            "parameters_used": {"name": name, "namespace": namespace, "body": body},
            "error_message": None
        }
    except ApiException as e:
        error = f"ApiException: {e.status} {e.reason}"
        return {
            "operation": operation,
            "status": "error",
            "data": None,
            "class": "kubernetes.client.CoreV1Api",
            "method_signature": signature,
            "parameters_used": {"name": name, "namespace": namespace, "body": body},
            "error_message": error
        }
    except Exception as e:
        return {
            "operation": operation,
            "status": "error",
            "data": None,
            "class": "kubernetes.client.CoreV1Api",
            "method_signature": signature,
            "parameters_used": {"name": name, "namespace": namespace, "body": body},
            "error_message": str(e)
        }


@app.tool()
def kubernetes_delete_service(name: str, namespace: str, token: Optional[str] = None,
                             api_server_url: Optional[str] = None) -> dict:
    """
    Delete a Service.

    Parameters:
        name: Service name.
        namespace: Namespace.
        token, api_server_url: Optional auth overrides.

    Returns:
        dict
    """
    operation = "kubernetes_delete_service"
    signature = "def kubernetes_delete_service(name: str, namespace: str) -> dict"

    try:
        apis = _get_apis(token=token, api_server_url=api_server_url)
        core_v1 = apis.get("core")
        if core_v1 is None:
            raise RuntimeError("CoreV1Api client is not initialized")

        resp = core_v1.delete_namespaced_service(name=name, namespace=namespace)
        data = _to_jsonable(resp)
        return {
            "operation": operation,
            "status": "success",
            "data": data,
            "class": "kubernetes.client.CoreV1Api",
            "method_signature": signature,
            "parameters_used": {"name": name, "namespace": namespace},
            "error_message": None
        }
    except ApiException as e:
        error = f"ApiException: {e.status} {e.reason}"
        return {
            "operation": operation,
            "status": "error",
            "data": None,
            "class": "kubernetes.client.CoreV1Api",
            "method_signature": signature,
            "parameters_used": {"name": name, "namespace": namespace},
            "error_message": error
        }
    except Exception as e:
        return {
            "operation": operation,
            "status": "error",
            "data": None,
            "class": "kubernetes.client.CoreV1Api",
            "method_signature": signature,
            "parameters_used": {"name": name, "namespace": namespace},
            "error_message": str(e)
        }


@app.tool()
def kubernetes_list_nodes(limit: int = 100, _continue: Optional[str] = None, token: Optional[str] = None,
                         api_server_url: Optional[str] = None) -> dict:
    """
    List Nodes across the cluster with optional pagination.

    Parameters:
        limit: Number of nodes per page.
        _continue: Continuation token for pagination.
        token, api_server_url: Optional auth overrides.

    Returns:
        dict
    """
    operation = "kubernetes_list_nodes"
    signature = "def kubernetes_list_nodes(limit: int = 100, _continue: Optional[str] = None) -> dict"

    try:
        apis = _get_apis(token=token, api_server_url=api_server_url)
        core_v1 = apis.get("core")
        if core_v1 is None:
            raise RuntimeError("CoreV1Api client is not initialized")

        resp = core_v1.list_node(limit=limit, _continue=_continue)
        data = _to_jsonable(resp)
        return {
            "operation": operation,
            "status": "success",
            "data": data,
            "class": "kubernetes.client.CoreV1Api",
            "method_signature": signature,
            "parameters_used": {"limit": limit, "_continue": _continue},
            "error_message": None
        }
    except ApiException as e:
        error = f"ApiException: {e.status} {e.reason}"
        return {
            "operation": operation,
            "status": "error",
            "data": None,
            "class": "kubernetes.client.CoreV1Api",
            "method_signature": signature,
            "parameters_used": {"limit": limit, "_continue": _continue},
            "error_message": error
        }
    except Exception as e:
        return {
            "operation": operation,
            "status": "error",
            "data": None,
            "class": "kubernetes.client.CoreV1Api",
            "method_signature": signature,
            "parameters_used": {"limit": limit, "_continue": _continue},
            "error_message": str(e)
        }


@app.tool()
def kubernetes_get_node(name: str, token: Optional[str] = None, api_server_url: Optional[str] = None) -> dict:
    """
    Get details of a single Node by name.

    Parameters:
        name: Node name.
        token, api_server_url: Optional auth overrides.

    Returns:
        dict
    """
    operation = "kubernetes_get_node"
    signature = "def kubernetes_get_node(name: str) -> dict"

    try:
        apis = _get_apis(token=token, api_server_url=api_server_url)
        core_v1 = apis.get("core")
        if core_v1 is None:
            raise RuntimeError("CoreV1Api client is not initialized")

        node = core_v1.read_node(name=name)
        data = _to_jsonable(node)
        return {
            "operation": operation,
            "status": "success",
            "data": data,
            "class": "kubernetes.client.CoreV1Api",
            "method_signature": signature,
            "parameters_used": {"name": name},
            "error_message": None
        }
    except ApiException as e:
        error = f"ApiException: {e.status} {e.reason}"
        return {
            "operation": operation,
            "status": "error",
            "data": None,
            "class": "kubernetes.client.CoreV1Api",
            "method_signature": signature,
            "parameters_used": {"name": name},
            "error_message": error
        }
    except Exception as e:
        return {
            "operation": operation,
            "status": "error",
            "data": None,
            "class": "kubernetes.client.CoreV1Api",
            "method_signature": signature,
            "parameters_used": {"name": name},
            "error_message": str(e)
        }


@app.tool()
def kubernetes_scale_deployment(name: str, namespace: str, replicas: int, token: Optional[str] = None,
                               api_server_url: Optional[str] = None) -> dict:
    """
    Scale a Deployment by patching its replicas count.

    Parameters:
        name: Deployment name.
        namespace: Namespace.
        replicas: Desired replica count.
        token, api_server_url: Optional auth overrides.

    Returns:
        dict
    """
    operation = "kubernetes_scale_deployment"
    signature = "def kubernetes_scale_deployment(name: str, namespace: str, replicas: int) -> dict"

    try:
        apis = _get_apis(token=token, api_server_url=api_server_url)
        apps_v1 = apis.get("apps")
        if apps_v1 is None:
            raise RuntimeError("AppsV1Api client is not initialized")

        patch_body = {"spec": {"replicas": replicas}}
        updated = apps_v1.patch_namespaced_deployment(name=name, namespace=namespace, body=patch_body)
        data = _to_jsonable(updated)
        return {
            "operation": operation,
            "status": "success",
            "data": data,
            "class": "kubernetes.client.AppsV1Api",
            "method_signature": signature,
            "parameters_used": {"name": name, "namespace": namespace, "replicas": replicas},
            "error_message": None
        }
    except ApiException as e:
        error = f"ApiException: {e.status} {e.reason}"
        return {
            "operation": operation,
            "status": "error",
            "data": None,
            "class": "kubernetes.client.AppsV1Api",
            "method_signature": signature,
            "parameters_used": {"name": name, "namespace": namespace, "replicas": replicas},
            "error_message": error
        }
    except Exception as e:
        return {
            "operation": operation,
            "status": "error",
            "data": None,
            "class": "kubernetes.client.AppsV1Api",
            "method_signature": signature,
            "parameters_used": {"name": name, "namespace": namespace, "replicas": replicas},
            "error_message": str(e)
        }


if __name__ == "__main__":
    # Optional: Initialize API clients at startup using environment-based configuration
    try:
        _get_apis()  # warm-up
        logger.info("Kubernetes MCP server initialized.")
    except Exception as init_err:
        logger.warning("Kubernetes MCP initialization warning: %s", init_err)

    app.run()