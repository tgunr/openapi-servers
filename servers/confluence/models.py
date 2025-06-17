from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Union
from enum import Enum
from datetime import datetime


class PageStatus(str, Enum):
    """Page status options"""
    current = "current"
    draft = "draft"
    archived = "archived"
    trashed = "trashed"
    deleted = "deleted"


class BodyRepresentation(str, Enum):
    """Body representation formats"""
    storage = "storage"
    atlas_doc_format = "atlas_doc_format"
    wiki = "wiki"
    view = "view"


class PageBody(BaseModel):
    """Page body content"""
    representation: BodyRepresentation = Field(
        default=BodyRepresentation.storage,
        description="The content format type"
    )
    value: str = Field(
        description="The body content in the specified representation format"
    )


class ParentPage(BaseModel):
    """Parent page reference"""
    id: int = Field(description="The ID of the parent page")


class Space(BaseModel):
    """Space reference"""
    id: int = Field(description="The ID of the space")


class Version(BaseModel):
    """Version information"""
    number: int = Field(description="The version number")
    message: Optional[str] = Field(None, description="Version message")


class CreatePageRequest(BaseModel):
    """Request model for creating a page"""
    spaceId: int = Field(description="The ID of the space to create the page in")
    status: Optional[PageStatus] = Field(
        default=PageStatus.current,
        description="The status of the page. Pages are created as published by default unless specified as draft"
    )
    title: Optional[str] = Field(
        None,
        description="The title of the page. Must be specified when creating a published page"
    )
    parentId: Optional[int] = Field(
        None,
        description="The ID of the parent page. If not specified, the page will be created at the root level"
    )
    body: Optional[PageBody] = Field(
        None,
        description="The body content of the page"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "spaceId": 123456,
                "status": "current",
                "title": "My New Page",
                "parentId": 789012,
                "body": {
                    "representation": "storage",
                    "value": "<p>This is the content of my new page.</p>"
                }
            }
        }


class UpdatePageRequest(BaseModel):
    """Request model for updating a page"""
    id: int = Field(description="The ID of the page to update")
    status: Optional[PageStatus] = Field(None, description="The status of the page")
    title: Optional[str] = Field(None, description="The title of the page")
    body: Optional[PageBody] = Field(None, description="The body content of the page")
    version: Version = Field(description="The version information")


class PageResponse(BaseModel):
    """Response model for page operations"""
    id: str = Field(description="The ID of the page")
    status: PageStatus = Field(description="The status of the page")
    title: str = Field(description="The title of the page")
    spaceId: str = Field(description="The ID of the space containing the page")
    parentId: Optional[str] = Field(None, description="The ID of the parent page")
    authorId: str = Field(description="The account ID of the page author")
    createdAt: str = Field(description="The creation timestamp")
    version: Version = Field(description="The current version information")
    body: Optional[PageBody] = Field(None, description="The body content of the page")
    links: Optional[Dict[str, Any]] = Field(None, description="Hypermedia links", alias="_links")


class ConfluenceError(Exception):
    """Custom exception for Confluence API errors"""
    def __init__(self, message: str, status_code: int = 500, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)


class AuthConfig(BaseModel):
    """Authentication configuration"""
    base_url: str = Field(
        description="Confluence instance base URL (e.g., https://your-domain.atlassian.net)"
    )
    email: str = Field(description="User email address")
    api_token: str = Field(description="API token")
    
    class Config:
        json_schema_extra = {
            "example": {
                "base_url": "https://your-domain.atlassian.net",
                "email": "your-email@example.com",
                "api_token": "your-api-token"
            }
        }


class PageListResponse(BaseModel):
    """Response model for listing pages"""
    results: List[PageResponse] = Field(description="List of pages")
    links: Optional[Dict[str, Any]] = Field(None, description="Pagination links", alias="_links")


class SpaceInfo(BaseModel):
    """Space information"""
    id: str = Field(description="The ID of the space")
    key: str = Field(description="The key of the space")
    name: str = Field(description="The name of the space")
    type: str = Field(description="The type of the space")
    status: str = Field(description="The status of the space")

