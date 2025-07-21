# Docker Setup for Meeting Agent

## Quick Start

### 1. Setup Environment Variables
```bash
# Copy the example environment file
cp config/.env.example config/.env

# Edit the .env file with your actual API keys and configuration
nano config/.env  # or vim/code/your-preferred-editor
```

### 2. Required Environment Variables
Make sure to set these in `config/.env`:
- `NOTION_TOKEN` - Your Notion integration token
- `DATABASE_ID` - Your meetings database ID  
- `TASKS_DATABASE_ID` - Your tasks database ID
- `OPENAI_API_KEY` - Your OpenAI API key
- `ANTHROPIC_API_KEY` - Your Anthropic API key
- `DEFAULT_ASSIGNEE` - Your name for task assignments
- `MEM0_API_KEY` - (Optional) For memory features
- `DEFAULT_USER_ID` - (Optional) Unique user ID for memory

### 3. Run with Docker Compose
```bash
# Build and start the container
docker-compose up --build

# Run in detached mode (background)
docker-compose up -d --build

# View logs
docker-compose logs -f meeting-agent

# Stop the container
docker-compose down
```

### 4. Run with Docker directly
```bash
# Build the image
docker build -t meeting-agent .

# Run the container
docker run -it --rm \
  --env-file config/.env \
  -v $(pwd)/config:/app/config:ro \
  meeting-agent
```

## Development

### Building the Image
```bash
docker build -t meeting-agent .
```

### Running Interactive Shell
```bash
docker run -it --rm \
  --env-file config/.env \
  --entrypoint /bin/bash \
  meeting-agent
```

### Updating Dependencies
If you modify `requirements.txt`, rebuild the image:
```bash
docker-compose up --build
```

## Troubleshooting

### Common Issues

1. **Permission Denied**: Make sure the `config/.env` file exists and is readable
2. **API Key Errors**: Verify all required environment variables are set in `config/.env`
3. **Interactive Mode**: The container runs in interactive mode by default. Use `docker-compose logs -f` to see output

### Logs
Container logs are available via:
```bash
docker-compose logs meeting-agent
```

### Environment Variable Debugging
To check what environment variables are loaded:
```bash
docker run --rm --env-file config/.env meeting-agent env | grep -E "(NOTION|OPENAI|ANTHROPIC|MEM0)"
```