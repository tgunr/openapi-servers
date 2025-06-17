# 🌟 Confluence Cloud REST API v2 Tool Server

A comprehensive OpenAPI tool server for Confluence Cloud REST API v2 page operations. This server provides secure authentication and full CRUD operations for Confluence pages, making it easy to integrate Confluence functionality into AI agents, workflows, and applications.

## ✨ Features

- ✅ **Complete Page Management**: Create, read, update, delete pages
- ✅ **Space Operations**: List and browse Confluence spaces
- ✅ **Page Hierarchies**: Support for parent-child page relationships
- ✅ **Content Formats**: Support for storage, wiki, atlas_doc_format, and view formats
- ✅ **Secure Authentication**: Uses Confluence Cloud API tokens with Basic Auth
- ✅ **Comprehensive Error Handling**: Detailed error responses and logging
- ✅ **OpenAPI/Swagger Documentation**: Auto-generated interactive API docs
- ✅ **Docker Support**: Easy deployment with Docker and docker-compose
- ✅ **Environment Configuration**: Flexible configuration via environment variables or API

## 🚀 Quick Start

### Option 1: Using Docker (Recommended)

```bash
cd servers/confluence
docker-compose up
```

### Option 2: Local Development

```bash
cd servers/confluence
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

The server will be available at:
- **API**: http://localhost:8000
- **Interactive Docs**: http://localhost:8000/docs
- **OpenAPI Schema**: http://localhost:8000/openapi.json

## 🔐 Authentication Setup

### Step 1: Get Confluence API Token

1. Go to [Atlassian API Tokens](https://id.atlassian.com/manage-profile/security/api-tokens)
2. Click "Create API token"
3. Give it a descriptive name (e.g., "OpenAPI Tool Server")
4. Copy the generated token

### Step 2: Configure Authentication

#### Option A: Environment Variables

```bash
cp .env.example .env
# Edit .env with your credentials
```

```bash
CONFLUENCE_BASE_URL=https://your-domain.atlassian.net
CONFLUENCE_EMAIL=your-email@example.com
CONFLUENCE_API_TOKEN=your-api-token
```

#### Option B: Runtime Configuration

Use the `/configure` endpoint to set credentials at runtime:

```bash
curl -X POST "http://localhost:8000/configure" \
  -H "Content-Type: application/json" \
  -d '{
    "base_url": "https://your-domain.atlassian.net",
    "email": "your-email@example.com",
    "api_token": "your-api-token"
  }'
```

### Step 3: Test Connection

```bash
curl http://localhost:8000/test-connection
```

## 📚 API Usage Examples

### 1. List Available Spaces

```bash
curl "http://localhost:8000/spaces"
```

### 2. Create a Page

```bash
curl -X POST "http://localhost:8000/pages" \
  -H "Content-Type: application/json" \
  -d '{
    "spaceId": 123456,
    "title": "My New Page",
    "body": {
      "representation": "storage",
      "value": "<p>This is my page content with <strong>formatting</strong>!</p>"
    }
  }'
```

### 3. Create a Child Page

```bash
curl -X POST "http://localhost:8000/pages" \
  -H "Content-Type: application/json" \
  -d '{
    "spaceId": 123456,
    "title": "Child Page",
    "parentId": 789012,
    "body": {
      "representation": "storage",
      "value": "<p>This is a child page.</p>"
    }
  }'
```

### 4. Create a Draft Page

```bash
curl -X POST "http://localhost:8000/pages" \
  -H "Content-Type: application/json" \
  -d '{
    "spaceId": 123456,
    "title": "Draft Page",
    "status": "draft",
    "body": {
      "representation": "storage",
      "value": "<p>This is a draft page.</p>"
    }
  }'
```

### 5. Get a Page

```bash
curl "http://localhost:8000/pages/123456789?include_body=true"
```

### 6. Update a Page

```bash
# First, get the current page to find the version number
curl "http://localhost:8000/pages/123456789"

# Then update with incremented version
curl -X PUT "http://localhost:8000/pages/123456789" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Updated Page Title",
    "body": {
      "representation": "storage",
      "value": "<p>Updated content goes here.</p>"
    },
    "version": {
      "number": 2
    }
  }'
```

### 7. List Pages in a Space

```bash
curl "http://localhost:8000/spaces/123456/pages?limit=10&include_body=false"
```

### 8. Delete a Page

```bash
# Move to trash
curl -X DELETE "http://localhost:8000/pages/123456789"

# Permanently delete (purge)
curl -X DELETE "http://localhost:8000/pages/123456789?purge=true"
```

## 🎯 Advanced Usage

### Creating Private Pages

```bash
curl -X POST "http://localhost:8000/pages?private=true" \
  -H "Content-Type: application/json" \
  -d '{
    "spaceId": 123456,
    "title": "Private Page",
    "body": {
      "representation": "storage",
      "value": "<p>Only I can see this page.</p>"
    }
  }'
```

### Creating Root-Level Pages

```bash
curl -X POST "http://localhost:8000/pages?root_level=true" \
  -H "Content-Type: application/json" \
  -d '{
    "spaceId": 123456,
    "title": "Root Level Page",
    "body": {
      "representation": "storage",
      "value": "<p>This page is at the space root level.</p>"
    }
  }'
```

### Using Different Content Formats

#### Storage Format (Default)
```json
{
  "body": {
    "representation": "storage",
    "value": "<p>HTML-like content with Confluence storage format.</p>"
  }
}
```

#### Wiki Format
```json
{
  "body": {
    "representation": "wiki",
    "value": "h1. This is a heading\n\nThis is *bold* text."
  }
}
```

## 🔧 Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `CONFLUENCE_BASE_URL` | Your Confluence Cloud instance URL | Yes* |
| `CONFLUENCE_EMAIL` | Your Atlassian account email | Yes* |
| `CONFLUENCE_API_TOKEN` | Your Confluence API token | Yes* |
| `LOG_LEVEL` | Logging level (debug, info, warning, error) | No |

*Required if not configured via the `/configure` endpoint

### Query Parameters

#### Page Creation
- `embedded`: Tag content as embedded (boolean)
- `private`: Make page private (boolean)
- `root_level`: Create at space root level (boolean)

#### Page Retrieval
- `include_body`: Include page content in response (boolean)
- `limit`: Maximum number of results (integer, 1-250)

## 📋 API Endpoints

### Configuration
- `POST /configure` - Configure authentication
- `GET /test-connection` - Test API connection

### Health & Info
- `GET /` - Service information
- `GET /health` - Health check
- `GET /docs` - Interactive API documentation

### Spaces
- `GET /spaces` - List spaces
- `GET /spaces/{space_key}` - Get space by key
- `GET /spaces/{space_id}/pages` - List pages in space

### Pages
- `POST /pages` - Create page
- `GET /pages/{page_id}` - Get page by ID
- `PUT /pages/{page_id}` - Update page
- `DELETE /pages/{page_id}` - Delete page

## 🛠️ Development

### Local Development Setup

```bash
# Clone the repository
git clone https://github.com/open-webui/openapi-servers
cd openapi-servers/servers/confluence

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env
# Edit .env with your credentials

# Run the server
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Testing

```bash
# Test connection
curl http://localhost:8000/health

# View interactive docs
open http://localhost:8000/docs
```

### Docker Development

```bash
# Build and run
docker-compose up --build

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

## 🚨 Error Handling

The server provides comprehensive error handling with detailed messages:

```json
{
  "error": "Title is required when creating a published page",
  "status_code": 400,
  "details": {
    "field": "title",
    "requirement": "required for published pages"
  }
}
```

Common error scenarios:
- **401 Unauthorized**: Invalid API credentials
- **403 Forbidden**: Insufficient permissions
- **404 Not Found**: Page/space not found
- **409 Conflict**: Duplicate page title in space
- **413 Payload Too Large**: Request body too large (>5MB)

## 🔒 Security

- API tokens are transmitted securely using HTTPS
- Credentials are not logged or exposed in responses
- Basic Authentication follows Atlassian's recommended approach
- No sensitive data is stored persistently

## 📖 Confluence API Documentation

For detailed information about the Confluence Cloud REST API v2:
- [Official Documentation](https://developer.atlassian.com/cloud/confluence/rest/v2/)
- [API Reference](https://developer.atlassian.com/cloud/confluence/rest/v2/api-group-page/)
- [Authentication Guide](https://developer.atlassian.com/cloud/confluence/basic-auth-for-rest-apis/)

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](../../LICENSE) file for details.

## 🙋‍♂️ Support

For questions or issues:
1. Check the [interactive API documentation](http://localhost:8000/docs)
2. Review the error messages and logs
3. Open an issue on [GitHub](https://github.com/open-webui/openapi-servers/issues)

