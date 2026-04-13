# DebateEngine Deployment Guide

## Overview

This guide will help you deploy the DebateEngine API on Render (a free hosting service) and connect it to the frontend on GitHub Pages.

## Core Feature Enhancements

### Multi-API Key Support
- **Round-Robin Mechanism**: Automatically switches between multiple API keys using Round-Robin algorithm
- **Load Balancing**: Automatically distributes requests to avoid single key limits
- **Failover**: Automatically detects failed keys and switches to available keys
- **Cooldown Mechanism**: Failed keys automatically recover after 60 seconds
- **Stats Monitoring**: Real-time tracking of each key's usage

### Supported Environment Variables
- `NVIDIA_API_KEY`: Primary key (required)
- `NVIDIA_API_KEY_1` to `NVIDIA_API_KEY_10`: Backup keys (optional, up to 10)

## Deployment Steps

### 1. Deploy API on Render

#### Step 1: Register for Render Account
- Visit https://render.com
- Login with your GitHub account

#### Step 2: Deploy from GitHub Repository
1. Click "New +" button, select "Web Service"
2. Select your `1235357/debate-engine` repository
3. Select `main` branch

#### Step 3: Configure Deployment Settings
- **Name**: `debate-engine-api`
- **Language**: `Python 3`
- **Region**: Select the region closest to you (Singapore recommended)
- **Build Command**: `pip install -e .`
- **Start Command**: `python api_server.py`
- **Instance Type**: Select `Free`

#### Step 4: Add Environment Variables (Important!)
Add your API keys in the "Environment Variables" section:

**Single Key Configuration (Minimum)**:
- **Key**: `NVIDIA_API_KEY`
- **Value**: Enter your NVIDIA API key

**Multiple Key Configuration (Recommended)**:
- **Key**: `NVIDIA_API_KEY`
- **Value**: Enter your first NVIDIA API key

Then click "Add Environment Variable" to continue adding:
- **Key**: `NVIDIA_API_KEY_1`
- **Value**: Enter your second NVIDIA API key

Continue adding until all keys are configured (supports up to 11: NVIDIA_API_KEY + NVIDIA_API_KEY_1 to _10)

**Note**: Do NOT check the "sync" option for any keys

#### Step 5: Advanced Configuration (Optional)
- **Health Check Path**: `/health`
- **Auto-Deploy**: Keep `On Commit` (auto-deploy)

#### Step 6: Deploy
Click "Deploy web service" and wait for deployment to complete (usually 1-3 minutes)

#### Step 7: Get API Address
After deployment completes, you'll see a URL like:
`https://debate-engine-api.onrender.com`

### 2. Configure Frontend

#### Update Frontend API Address
Edit `demo/index.html` file, find the API_URL configuration:

```javascript
// Change this line:
const API_URL = '';

// To your Render API address, for example:
const API_URL = 'https://debate-engine-api.onrender.com';
```

#### Commit and Push Changes
```bash
git add demo/index.html
git commit -m "Update API URL to Render deployment"
git push origin main
```

### 3. GitHub Pages Will Update Automatically

GitHub Actions will automatically deploy changes to GitHub Pages.

## Monitoring and Debugging

### Check API Status
Visit the health check endpoint:
```
https://debate-engine-api.onrender.com/health
```

You'll see a response like this:
```json
{
  "status": "healthy",
  "model": "minimaxai/minimax-m2.7",
  "api_keys": {
    "total_keys": 3,
    "active_keys": 3,
    "key_details": {
      "key_0": {
        "success_count": 42,
        "failure_count": 0,
        "is_active": true
      },
      "key_1": {
        "success_count": 38,
        "failure_count": 1,
        "is_active": true
      },
      "key_2": {
        "success_count": 40,
        "failure_count": 0,
        "is_active": true
      }
    }
  }
}
```

### API Key Statistics
Visit the stats endpoint for detailed usage:
```
https://debate-engine-api.onrender.com/api/stats
```

## How It Works

### APIKeyManager Class
This is the core component for multi-key management, providing:

1. **Round-Robin Polling**: Cycles through each key in order
2. **Smart Failure Detection**: Automatically detects failed API calls
3. **Auto-Recovery**: Failed keys automatically reactivate after cooldown period
4. **Thread Safety**: Uses locking mechanism for concurrent safety
5. **Stats Tracking**: Records success/failure counts for each key

### Failover Flow
1. Request arrives → get next key
2. Call successful → record success stats
3. Call failed → mark key as failed, try next key
4. After cooldown period (60 seconds) → key automatically becomes available again

## File Descriptions

### `api_server.py` (v0.2.0 Enhanced)
FastAPI backend server, includes:
- **APIKeyManager**: Multi-key manager
- Load balancing and failover
- Streaming response support
- CORS configuration
- Health check and stats endpoints
- Automatic retry mechanism

### `render.yaml`
Render configuration file, includes:
- Service type and name
- Build and start commands
- Free tier configuration
- 11 API key environment variable configurations

### `.github/workflows/deploy-api.yml`
GitHub Actions workflow, includes:
- NVIDIA API connection test
- Project dependency installation
- Test runs

## Testing Deployment

### 1. Test API
Visit the health check endpoint of your Render API address:
```
https://debate-engine-api.onrender.com/health
```

### 2. Test Frontend
Visit GitHub Pages address:
```
https://1235357.github.io/debate-engine/
```

## Notes

### Free Tier Limitations
- Render free tier goes to sleep after 15 minutes of inactivity
- First request may take 30-60 seconds to wake up
- 750 hours of free runtime per month

### NVIDIA API Key Security
- Do NOT commit API keys to code repository
- Use Render's environment variable management
- Rotate API keys regularly
- Can use multiple keys to distribute load and reduce risk

### CORS Configuration
Current API configuration allows all origins (`*`), in production you should restrict to your GitHub Pages domain.

### Multi-Key Best Practices
1. Use at least 2-3 keys for better reliability
2. Monitor `/api/stats` endpoint for usage
3. Promptly replenish failed or quota-exhausted keys
4. All keys should use the same API endpoint and model

## Troubleshooting

### API Cannot Connect
1. Check if Render service is running
2. Confirm at least one NVIDIA_API_KEY is correctly set
3. Check Render logs
4. Visit `/health` endpoint to check status

### Frontend Shows Error
1. Check browser console for error messages
2. Confirm API_URL is correctly configured
3. Check CORS configuration
4. Confirm API service is fully started (may take 1-2 minutes)

### All Keys Failed
1. Check if your NVIDIA API keys are valid
2. Confirm keys have not exceeded quota
3. Check network connection
4. Check Render logs for detailed error information

## Next Steps

After deployment completes, you can:
1. Customize frontend interface
2. Add more API endpoints
3. Configure custom domain
4. Set up monitoring and alerts
5. Add more API keys to expand capacity
6. Use `/api/stats` to monitor key usage
