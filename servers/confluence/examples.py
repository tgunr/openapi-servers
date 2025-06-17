#!/usr/bin/env python3
"""
Confluence API Tool Server - Usage Examples

This script demonstrates how to use the Confluence API tool server
with various page creation scenarios and API payload examples.
"""

import httpx
import json
from typing import Dict, Any, Optional


class ConfluenceToolServerExample:
    """Example client for the Confluence Tool Server"""
    
    def __init__(self, server_url: str = "http://localhost:8000"):
        self.server_url = server_url.rstrip('/')
        self.client = httpx.Client(timeout=30.0)
    
    def configure_auth(self, base_url: str, email: str, api_token: str) -> Dict[str, Any]:
        """Configure authentication with the tool server"""
        response = self.client.post(
            f"{self.server_url}/configure",
            json={
                "base_url": base_url,
                "email": email,
                "api_token": api_token
            }
        )
        return response.json()
    
    def test_connection(self) -> Dict[str, Any]:
        """Test the connection to Confluence"""
        response = self.client.get(f"{self.server_url}/test-connection")
        return response.json()
    
    def list_spaces(self) -> Dict[str, Any]:
        """List available spaces"""
        response = self.client.get(f"{self.server_url}/spaces")
        return response.json()
    
    def create_simple_page(self, space_id: int, title: str, content: str) -> Dict[str, Any]:
        """Create a simple page with basic content"""
        payload = {
            "spaceId": space_id,
            "title": title,
            "body": {
                "representation": "storage",
                "value": f"<p>{content}</p>"
            }
        }
        
        response = self.client.post(
            f"{self.server_url}/pages",
            json=payload
        )
        return response.json()
    
    def create_child_page(self, space_id: int, parent_id: int, title: str, content: str) -> Dict[str, Any]:
        """Create a child page under a parent page"""
        payload = {
            "spaceId": space_id,
            "parentId": parent_id,
            "title": title,
            "body": {
                "representation": "storage",
                "value": content
            }
        }
        
        response = self.client.post(
            f"{self.server_url}/pages",
            json=payload
        )
        return response.json()
    
    def create_rich_content_page(self, space_id: int, title: str) -> Dict[str, Any]:
        """Create a page with rich content formatting"""
        rich_content = """
        <h1>Welcome to My Documentation</h1>
        <p>This page demonstrates various formatting options in Confluence.</p>
        
        <h2>Code Example</h2>
        <ac:structured-macro ac:name="code" ac:schema-version="1">
            <ac:parameter ac:name="language">python</ac:parameter>
            <ac:plain-text-body><![CDATA[
def hello_world():
    print("Hello, Confluence!")
    return "success"
]]></ac:plain-text-body>
        </ac:structured-macro>
        
        <h2>Information Panel</h2>
        <ac:structured-macro ac:name="info" ac:schema-version="1">
            <ac:rich-text-body>
                <p>This is an info panel with important information.</p>
            </ac:rich-text-body>
        </ac:structured-macro>
        
        <h2>Task List</h2>
        <ul>
            <li><ac:task-list><ac:task><ac:task-id>1</ac:task-id><ac:task-status>complete</ac:task-status><ac:task-body>Set up Confluence API</ac:task-body></ac:task></ac:task-list></li>
            <li><ac:task-list><ac:task><ac:task-id>2</ac:task-id><ac:task-status>incomplete</ac:task-status><ac:task-body>Create documentation pages</ac:task-body></ac:task></ac:task-list></li>
        </ul>
        
        <h2>Table</h2>
        <table>
            <tbody>
                <tr>
                    <th>Feature</th>
                    <th>Status</th>
                    <th>Notes</th>
                </tr>
                <tr>
                    <td>Page Creation</td>
                    <td><strong>✅ Complete</strong></td>
                    <td>Supports all formats</td>
                </tr>
                <tr>
                    <td>Page Updates</td>
                    <td><strong>✅ Complete</strong></td>
                    <td>Version management included</td>
                </tr>
            </tbody>
        </table>
        """
        
        payload = {
            "spaceId": space_id,
            "title": title,
            "body": {
                "representation": "storage",
                "value": rich_content
            }
        }
        
        response = self.client.post(
            f"{self.server_url}/pages",
            json=payload
        )
        return response.json()
    
    def create_draft_page(self, space_id: int, title: str, content: str) -> Dict[str, Any]:
        """Create a draft page"""
        payload = {
            "spaceId": space_id,
            "title": title,
            "status": "draft",
            "body": {
                "representation": "storage",
                "value": content
            }
        }
        
        response = self.client.post(
            f"{self.server_url}/pages",
            json=payload
        )
        return response.json()
    
    def create_private_page(self, space_id: int, title: str, content: str) -> Dict[str, Any]:
        """Create a private page"""
        payload = {
            "spaceId": space_id,
            "title": title,
            "body": {
                "representation": "storage",
                "value": content
            }
        }
        
        response = self.client.post(
            f"{self.server_url}/pages?private=true",
            json=payload
        )
        return response.json()
    
    def get_page(self, page_id: str, include_body: bool = True) -> Dict[str, Any]:
        """Get a page by ID"""
        params = {"include_body": include_body}
        response = self.client.get(
            f"{self.server_url}/pages/{page_id}",
            params=params
        )
        return response.json()
    
    def update_page(self, page_id: str, title: str, content: str, version_number: int) -> Dict[str, Any]:
        """Update a page"""
        payload = {
            "title": title,
            "body": {
                "representation": "storage",
                "value": content
            },
            "version": {
                "number": version_number
            }
        }
        
        response = self.client.put(
            f"{self.server_url}/pages/{page_id}",
            json=payload
        )
        return response.json()


def main():
    """Main example function"""
    # Initialize the example client
    example = ConfluenceToolServerExample()
    
    print("🌟 Confluence API Tool Server Examples")
    print("======================================\n")
    
    # Note: You'll need to configure authentication first
    print("📝 Configuration Examples:")
    print("""# 1. Configure authentication
example.configure_auth(
    base_url="https://your-domain.atlassian.net",
    email="your-email@example.com",
    api_token="your-api-token"
)""")
    
    print("\n🔗 Connection Test:")
    print("# Test connection")
    print("result = example.test_connection()")
    
    print("\n📋 Basic Examples:")
    
    # Example 1: Simple page
    print("\n# Example 1: Create a simple page")
    simple_page_payload = {
        "spaceId": 123456,
        "title": "My First Page",
        "body": {
            "representation": "storage",
            "value": "<p>This is my first page created via the API!</p>"
        }
    }
    print(f"Payload: {json.dumps(simple_page_payload, indent=2)}")
    
    # Example 2: Child page
    print("\n# Example 2: Create a child page")
    child_page_payload = {
        "spaceId": 123456,
        "parentId": 789012,
        "title": "Child Page",
        "body": {
            "representation": "storage",
            "value": "<p>This is a child page under a parent.</p>"
        }
    }
    print(f"Payload: {json.dumps(child_page_payload, indent=2)}")
    
    # Example 3: Draft page
    print("\n# Example 3: Create a draft page")
    draft_page_payload = {
        "spaceId": 123456,
        "title": "Draft Page",
        "status": "draft",
        "body": {
            "representation": "storage",
            "value": "<p>This is a draft page that won't be published yet.</p>"
        }
    }
    print(f"Payload: {json.dumps(draft_page_payload, indent=2)}")
    
    # Example 4: Rich content
    print("\n# Example 4: Create a page with rich content")
    rich_content = """
    <h1>API Documentation</h1>
    <p>This page contains comprehensive API documentation.</p>
    
    <ac:structured-macro ac:name="code" ac:schema-version="1">
        <ac:parameter ac:name="language">bash</ac:parameter>
        <ac:plain-text-body><![CDATA[
curl -X POST "http://localhost:8000/pages" \
  -H "Content-Type: application/json" \
  -d '{
    "spaceId": 123456,
    "title": "API Example",
    "body": {
      "representation": "storage",
      "value": "<p>Hello World</p>"
    }
  }'
]]></ac:plain-text-body>
    </ac:structured-macro>
    """
    
    rich_page_payload = {
        "spaceId": 123456,
        "title": "Rich Content Page",
        "body": {
            "representation": "storage",
            "value": rich_content
        }
    }
    print(f"Payload: {json.dumps(rich_page_payload, indent=2)}")
    
    print("\n🔧 Advanced Examples:")
    
    # Example 5: Private page
    print("\n# Example 5: Create a private page")
    print("# Use query parameter: ?private=true")
    private_page_payload = {
        "spaceId": 123456,
        "title": "Private Page",
        "body": {
            "representation": "storage",
            "value": "<p>This page is private and only visible to me.</p>"
        }
    }
    print(f"Payload: {json.dumps(private_page_payload, indent=2)}")
    
    # Example 6: Root level page
    print("\n# Example 6: Create a root-level page")
    print("# Use query parameter: ?root_level=true")
    root_page_payload = {
        "spaceId": 123456,
        "title": "Root Level Page",
        "body": {
            "representation": "storage",
            "value": "<p>This page is at the root level of the space.</p>"
        }
    }
    print(f"Payload: {json.dumps(root_page_payload, indent=2)}")
    
    # Example 7: Update page
    print("\n# Example 7: Update an existing page")
    update_payload = {
        "title": "Updated Page Title",
        "body": {
            "representation": "storage",
            "value": "<p>This page has been updated with new content.</p>"
        },
        "version": {
            "number": 2,
            "message": "Updated via API"
        }
    }
    print(f"Payload: {json.dumps(update_payload, indent=2)}")
    
    print("\n✅ Examples completed! Check the server documentation at http://localhost:8000/docs")


if __name__ == "__main__":
    main()

