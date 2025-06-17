#!/usr/bin/env python3
"""
Confluence Cloud REST API v2 Tool Server

A comprehensive OpenAPI tool server for Confluence Cloud REST API v2 page operations.
Provides secure authentication and full CRUD operations for Confluence pages.

Authentication:
- Uses Confluence Cloud API tokens with Basic Auth
- Requires: base_url, email, api_token

Features:
- Create, read, update, delete pages
- List spaces and pages
- Support for page hierarchies and content formatting
- Comprehensive error handling
- OpenAPI/Swagger documentation
"""

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
from typing import Optional, List
import os
from functools import lru_cache

from models import (
    CreatePageRequest, UpdatePageRequest, PageResponse, AuthConfig,
    ConfluenceError, SpaceInfo, PageListResponse
)
from client import ConfluenceAPIClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global client instance
_confluence_client: Optional[ConfluenceAPIClient] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    logger.info("Starting Confluence API Tool Server")
    yield
    logger.info("Shutting down Confluence API Tool Server")
    global _confluence_client
    if _confluence_client:
        _confluence_client.client.close()


app = FastAPI(
    title="Confluence Cloud REST API v2 Tool Server",
    description="""A comprehensive OpenAPI tool server for Confluence Cloud REST API v2 page operations.
    
## Authentication

This server requires Confluence Cloud API authentication. You need:

1. **Base URL**: Your Confluence Cloud instance URL (e.g., `https://your-domain.atlassian.net`)
2. **Email**: Your Atlassian account email
3. **API Token**: Generate one at https://id.atlassian.com/manage-profile/security/api-tokens

## Features

- ✅ **Create Pages**: Create new pages with rich content
- ✅ **Read Pages**: Retrieve page content and metadata
- ✅ **Update Pages**: Modify existing pages
- ✅ **Delete Pages**: Remove pages (with optional purge)
- ✅ **List Spaces**: Browse available Confluence spaces
- ✅ **List Pages**: Get pages within a space
- ✅ **Page Hierarchies**: Support for parent-child page relationships
- ✅ **Content Formats**: Support for storage, wiki, and other formats
- ✅ **Error Handling**: Comprehensive error responses

## Usage

1. Configure authentication using the `/configure` endpoint
2. Test connection with `/test-connection`
3. Use the various page and space operations

## Security

- Uses HTTPS for all API communications
- API tokens are handled securely
- No credentials are logged or exposed
    """,
    version="1.0.0",
    contact={
        "name": "OpenAPI Tool Servers",
        "url": "https://github.com/open-webui/openapi-servers",
    },
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT",
    },
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@lru_cache()
def get_settings():
    """Get settings from environment variables"""
    return {
        "confluence_base_url": os.getenv("CONFLUENCE_BASE_URL"),
        "confluence_email": os.getenv("CONFLUENCE_EMAIL"),
        "confluence_api_token": os.getenv("CONFLUENCE_API_TOKEN"),
    }


def get_confluence_client() -> ConfluenceAPIClient:
    """Get or create Confluence client instance"""
    global _confluence_client
    
    if _confluence_client is None:
        settings = get_settings()
        
        # Check if credentials are available from environment
        if all([settings["confluence_base_url"], settings["confluence_email"], settings["confluence_api_token"]]):
            auth_config = AuthConfig(
                base_url=settings["confluence_base_url"],
                email=settings["confluence_email"],
                api_token=settings["confluence_api_token"]
            )
            _confluence_client = ConfluenceAPIClient(auth_config)
            logger.info("Initialized Confluence client from environment variables")
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Confluence API not configured. Use /configure endpoint or set environment variables."
            )
    
    return _confluence_client


@app.exception_handler(ConfluenceError)
async def confluence_error_handler(request, exc: ConfluenceError):
    """Handle Confluence API errors"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.message,
            "status_code": exc.status_code,
            "details": exc.details
        }
    )


@app.get("/", tags=["Health"])
async def root():
    """Root endpoint with basic information"""
    return {
        "name": "Confluence Cloud REST API v2 Tool Server",
        "version": "1.0.0",
        "description": "OpenAPI tool server for Confluence Cloud operations",
        "docs_url": "/docs",
        "openapi_url": "/openapi.json"
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "confluence-api-server"}


@app.post("/configure", tags=["Configuration"])
async def configure_authentication(auth_config: AuthConfig):
    """Configure Confluence API authentication"""
    global _confluence_client
    
    try:
        # Create new client instance
        _confluence_client = ConfluenceAPIClient(auth_config)
        
        # Test the connection
        test_result = _confluence_client.test_connection()
        
        if test_result["success"]:
            logger.info(f"Successfully configured Confluence API for {auth_config.base_url}")
            return {
                "message": "Authentication configured successfully",
                "base_url": auth_config.base_url,
                "email": auth_config.email,
                "status": "ready"
            }
        else:
            _confluence_client = None
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Authentication failed: {test_result['message']}"
            )
    
    except Exception as e:
        _confluence_client = None
        logger.error(f"Failed to configure authentication: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Configuration failed: {str(e)}"
        )


@app.get("/test-connection", tags=["Configuration"])
async def test_connection(client: ConfluenceAPIClient = Depends(get_confluence_client)):
    """Test the Confluence API connection"""
    return client.test_connection()


@app.get("/spaces", response_model=List[SpaceInfo], tags=["Spaces"])
async def list_spaces(
    limit: int = 25,
    client: ConfluenceAPIClient = Depends(get_confluence_client)
):
    """List available Confluence spaces"""
    return client.get_spaces(limit=limit)


@app.get("/spaces/{space_key}", response_model=Optional[SpaceInfo], tags=["Spaces"])
async def get_space_by_key(
    space_key: str,
    client: ConfluenceAPIClient = Depends(get_confluence_client)
):
    """Get space information by space key"""
    space = client.get_space_by_key(space_key)
    if not space:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Space with key '{space_key}' not found"
        )
    return space


@app.get("/spaces/{space_id}/pages", response_model=PageListResponse, tags=["Pages"])
async def list_pages_in_space(
    space_id: str,
    limit: int = 25,
    include_body: bool = False,
    client: ConfluenceAPIClient = Depends(get_confluence_client)
):
    """List pages in a specific space"""
    return client.get_pages_in_space(space_id, limit=limit, include_body=include_body)


@app.post("/pages", response_model=PageResponse, tags=["Pages"])
async def create_page(
    request: CreatePageRequest,
    embedded: bool = False,
    private: bool = False,
    root_level: bool = False,
    client: ConfluenceAPIClient = Depends(get_confluence_client)
):
    """Create a new page in Confluence
    
    - **spaceId**: The ID of the space to create the page in
    - **status**: Page status (current/draft) - pages are published by default
    - **title**: Page title (required for published pages)
    - **parentId**: Parent page ID (optional, creates root-level page if not specified)
    - **body**: Page content in specified format
    - **embedded**: Create as embedded content
    - **private**: Make page private (only creator can view/edit)
    - **root_level**: Create at space root level (ignores parentId)
    """
    return client.create_page(
        request, 
        embedded=embedded, 
        private=private, 
        root_level=root_level
    )


@app.get("/pages/{page_id}", response_model=PageResponse, tags=["Pages"])
async def get_page(
    page_id: str,
    include_body: bool = True,
    client: ConfluenceAPIClient = Depends(get_confluence_client)
):
    """Get a page by ID"""
    return client.get_page(page_id, include_body=include_body)


@app.put("/pages/{page_id}", response_model=PageResponse, tags=["Pages"])
async def update_page(
    page_id: str,
    request: UpdatePageRequest,
    client: ConfluenceAPIClient = Depends(get_confluence_client)
):
    """Update an existing page
    
    Note: The version number must be incremented from the current version.
    Use GET /pages/{page_id} to get the current version number first.
    """
    request.id = int(page_id)
    return client.update_page(request)


@app.delete("/pages/{page_id}", tags=["Pages"])
async def delete_page(
    page_id: str,
    purge: bool = False,
    client: ConfluenceAPIClient = Depends(get_confluence_client)
):
    """Delete a page
    
    - **purge**: If True, permanently delete the page. If False, move to trash.
    """
    success = client.delete_page(page_id, purge=purge)
    if success:
        return {"message": f"Page {page_id} {'purged' if purge else 'deleted'} successfully"}
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Page {page_id} not found or could not be deleted"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )

