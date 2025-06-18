import httpx
import base64
from typing import Optional, Dict, Any, List
from urllib.parse import urljoin
import logging
from models import (
    CreatePageRequest, UpdatePageRequest, PageResponse, 
    ConfluenceError, AuthConfig, SpaceInfo, PageListResponse,
    CreateSpaceRequest
)

logger = logging.getLogger(__name__)


class ConfluenceAPIClient:
    """Confluence Cloud REST API v2 client with authentication"""
    
    def __init__(self, auth_config: AuthConfig):
        self.base_url = auth_config.base_url.rstrip('/')
        self.email = auth_config.email
        self.api_token = auth_config.api_token
        
        # Create basic auth header
        credentials = f"{self.email}:{self.api_token}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        
        self.headers = {
            "Authorization": f"Basic {encoded_credentials}",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        
        # API base URL - use the standard REST API endpoint
        self.api_base = urljoin(self.base_url, "/wiki/rest/api")
        
        # HTTP client with timeouts
        self.client = httpx.Client(
            headers=self.headers,
            timeout=30.0,
            follow_redirects=True
        )
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.client.close()
    
    def _handle_response(self, response: httpx.Response) -> Dict[str, Any]:
        """Handle API response and errors"""
        try:
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            error_data = {}
            try:
                error_data = response.json()
            except:
                error_data = {"message": response.text or "Unknown error"}
            
            logger.error(f"Confluence API error {response.status_code}: {error_data}")
            raise ConfluenceError(
                message=error_data.get("message", f"HTTP {response.status_code} error"),
                status_code=response.status_code,
                details=error_data
            )
        except Exception as e:
            logger.error(f"Request failed: {e}")
            raise ConfluenceError(
                message=f"Request failed: {str(e)}",
                status_code=500,
                details={"original_error": str(e)}
            )
    
    def test_connection(self) -> Dict[str, Any]:
        """Test the API connection and authentication"""
        try:
            url = f"{self.api_base}/space"
            response = self.client.get(url, params={"limit": 1})
            data = self._handle_response(response)
            return {
                "success": True,
                "message": "Connection successful",
                "api_version": "v1",
                "base_url": self.base_url
            }
        except ConfluenceError as e:
            return {
                "success": False,
                "message": e.message,
                "status_code": e.status_code
            }
    
    def get_spaces(self, limit: int = 25) -> List[SpaceInfo]:
        """Get list of spaces"""
        url = f"{self.api_base}/space"
        response = self.client.get(url, params={"limit": limit})
        data = self._handle_response(response)
        
        spaces = []
        for space_data in data.get("results", []):
            spaces.append(SpaceInfo(
                id=str(space_data["id"]),
                key=space_data["key"],
                name=space_data["name"],
                type=space_data.get("type", "unknown"),
                status=space_data.get("status", "unknown")
            ))
        return spaces
    
    def get_space_by_key(self, space_key: str) -> Optional[SpaceInfo]:
        """Get space information by key"""
        spaces = self.get_spaces(limit=250)  # Get more spaces to search
        for space in spaces:
            if space.key.lower() == space_key.lower():
                return space
        return None
    
    def create_space(self, request: CreateSpaceRequest) -> SpaceInfo:
        """Create a new space in Confluence"""
        body_data = {
            "key": request.key.upper(),  # Space keys should be uppercase
            "name": request.name,
            "type": "global"  # Default to global space type
        }
        
        if request.description:
            body_data["description"] = {
                "representation": "plain",
                "value": request.description
            }
        
        logger.info(f"Creating space with data: {body_data}")
        
        url = urljoin(self.api_base, "/spaces")
        response = self.client.post(url, json=body_data)
        data = self._handle_response(response)
        
        return SpaceInfo(
            id=str(data["id"]),
            key=data["key"],
            name=data["name"],
            type=data.get("type", "global"),
            status=data.get("status", "current")
        )
    
    def create_page(
        self, 
        request: CreatePageRequest,
        embedded: bool = False,
        private: bool = False,
        root_level: bool = False
    ) -> PageResponse:
        """Create a new page in Confluence"""
        
        # Validate required fields for published pages
        if request.status == "current" and not request.title:
            raise ConfluenceError(
                message="Title is required when creating a published page",
                status_code=400
            )
        
        # Build query parameters
        params = {}
        if embedded:
            params["embedded"] = "true"
        if private:
            params["private"] = "true"
        if root_level:
            params["root-level"] = "true"
        
        # Prepare request body
        body_data = {
            "spaceId": request.spaceId,
            "status": request.status
        }
        
        if request.title:
            body_data["title"] = request.title
        
        if request.parentId and not root_level:
            body_data["parentId"] = request.parentId
        
        if request.body:
            body_data["body"] = {
                "representation": request.body.representation,
                "value": request.body.value
            }
        
        # For REST API v1, we need to restructure the data
        # Convert space ID to space key if needed
        space_key = request.spaceId
        if isinstance(request.spaceId, int) or str(request.spaceId).isdigit():
            # Look up space key by ID
            spaces = self.get_spaces(limit=250)
            for space in spaces:
                if str(space.id) == str(request.spaceId):
                    space_key = space.key
                    break
        
        rest_body_data = {
            "type": "page",
            "title": request.title,
            "space": {"key": space_key},
            "body": {
                "storage": {
                    "value": request.body.value if request.body else "",
                    "representation": "storage"
                }
            }
        }
        
        if request.parentId:
            rest_body_data["ancestors"] = [{"id": str(request.parentId)}]
        
        logger.info(f"Creating page with data: {rest_body_data}")
        
        url = f"{self.api_base}/content"
        response = self.client.post(url, json=rest_body_data)
        data = self._handle_response(response)
        
        return self._parse_rest_api_page_response(data)
    
    def get_page(self, page_id: str, include_body: bool = True) -> PageResponse:
        """Get a page by ID"""
        url = urljoin(self.api_base, f"/pages/{page_id}")
        params = {}
        if include_body:
            params["body-format"] = "storage"
        
        response = self.client.get(url, params=params)
        data = self._handle_response(response)
        
        return self._parse_page_response(data)
    
    def update_page(self, request: UpdatePageRequest) -> PageResponse:
        """Update an existing page"""
        body_data = {
            "version": {
                "number": request.version.number
            }
        }
        
        if request.title:
            body_data["title"] = request.title
        
        if request.status:
            body_data["status"] = request.status
        
        if request.body:
            body_data["body"] = {
                "representation": request.body.representation,
                "value": request.body.value
            }
        
        if request.version.message:
            body_data["version"]["message"] = request.version.message
        
        url = urljoin(self.api_base, f"/pages/{request.id}")
        response = self.client.put(url, json=body_data)
        data = self._handle_response(response)
        
        return self._parse_page_response(data)
    
    def delete_page(self, page_id: str, purge: bool = False) -> bool:
        """Delete a page"""
        url = urljoin(self.api_base, f"/pages/{page_id}")
        params = {}
        if purge:
            params["purge"] = "true"
        
        response = self.client.delete(url, params=params)
        try:
            self._handle_response(response)
            return True
        except ConfluenceError:
            return False
    
    def get_pages_in_space(
        self, 
        space_id: str, 
        limit: int = 25,
        include_body: bool = False
    ) -> PageListResponse:
        """Get pages in a space"""
        url = urljoin(self.api_base, f"/spaces/{space_id}/pages")
        params = {"limit": limit}
        if include_body:
            params["body-format"] = "storage"
        
        response = self.client.get(url, params=params)
        data = self._handle_response(response)
        
        pages = []
        for page_data in data.get("results", []):
            pages.append(self._parse_page_response(page_data))
        
        return PageListResponse(
            results=pages,
            links=data.get("_links")
        )
    
    def _parse_page_response(self, data: Dict[str, Any]) -> PageResponse:
        """Parse page data from API response"""
        from models import PageBody, Version, BodyRepresentation, PageStatus
        
        # Parse body if present
        body = None
        if "body" in data and data["body"]:
            body_data = data["body"]
            if isinstance(body_data, dict) and "storage" in body_data:
                body = PageBody(
                    representation=BodyRepresentation.storage,
                    value=body_data["storage"]["value"]
                )
            elif isinstance(body_data, dict):
                # Handle other body formats
                for repr_type in ["storage", "atlas_doc_format", "wiki", "view"]:
                    if repr_type in body_data:
                        body = PageBody(
                            representation=repr_type,
                            value=body_data[repr_type].get("value", "")
                        )
                        break
        
        # Parse version
        version_data = data.get("version", {"number": 1})
        version = Version(
            number=version_data.get("number", 1),
            message=version_data.get("message")
        )
        
        return PageResponse(
            id=str(data["id"]),
            status=PageStatus(data.get("status", "current")),
            title=data.get("title", ""),
            spaceId=str(data.get("spaceId", "")),
            parentId=str(data["parentId"]) if data.get("parentId") else None,
            authorId=data.get("authorId", ""),
            createdAt=data.get("createdAt", ""),
            version=version,
            body=body,
            links=data.get("_links")
        )
    
    def _parse_rest_api_page_response(self, data: Dict[str, Any]) -> PageResponse:
        """Parse page data from REST API v1 response"""
        from models import PageBody, Version, BodyRepresentation, PageStatus
        
        # Parse body if present
        body = None
        if "body" in data and "storage" in data["body"]:
            body = PageBody(
                representation=BodyRepresentation.storage,
                value=data["body"]["storage"]["value"]
            )
        
        # Parse version
        version_data = data.get("version", {"number": 1})
        version = Version(
            number=version_data.get("number", 1),
            message=version_data.get("message")
        )
        
        # Extract space ID from space object
        space_id = ""
        if "space" in data:
            space_id = str(data["space"].get("id", ""))
        
        return PageResponse(
            id=str(data["id"]),
            status=PageStatus(data.get("status", "current")),
            title=data.get("title", ""),
            spaceId=space_id,
            parentId=None,  # REST API v1 handles this differently
            authorId=data.get("history", {}).get("createdBy", {}).get("accountId", ""),
            createdAt=data.get("history", {}).get("createdDate", ""),
            version=version,
            body=body,
            links=data.get("_links")
        )

