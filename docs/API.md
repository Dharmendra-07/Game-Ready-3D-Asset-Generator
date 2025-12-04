# API Documentation

Complete reference for the Game 3D Asset Generator REST API.

## Base URL

```
http://localhost:8000
```

## Authentication

Currently no authentication required. For production, use API keys:

```bash
curl -H "X-API-Key: your-api-key" ...
```

---

## Endpoints

### 1. Generate Asset

Create a new 3D asset generation job.

**Endpoint:** `POST /generate`

**Request Body:**
```json
{
  "prompt": "medieval wooden chair",
  "steps": 64,
  "guidance_scale": 15.0,
  "seed": 42,
  "postprocess": true,
  "target_tris": 2000,
  "generate_lods": false
}
```

**Parameters:**

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `prompt` | string | ✅ Yes | - | Text description of the object |
| `steps` | integer | No | 64 | Generation steps (16-128) |
| `guidance_scale` | float | No | 15.0 | Guidance scale (3.0-20.0) |
| `seed` | integer | No | random | Random seed for reproducibility |
| `postprocess` | boolean | No | true | Apply mesh optimization |
| `target_tris` | integer | No | 2000 | Target triangle count (100-50000) |
| `generate_lods` | boolean | No | false | Generate LOD levels |

**Response:** `200 OK`
```json
{
  "job_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "queued",
  "message": "Job queued for processing"
}
```

**Example:**
```bash
curl -X POST "http://localhost:8000/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "futuristic laser sword",
    "steps": 64,
    "guidance_scale": 15.0,
    "postprocess": true,
    "generate_lods": true
  }'
```

---

### 2. Check Job Status

Get the current status of a generation job.

**Endpoint:** `GET /status/{job_id}`

**Response:** `200 OK`

**Queued:**
```json
{
  "job_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "queued",
  "progress": 0.0,
  "message": "Waiting in queue"
}
```

**Processing:**
```json
{
  "job_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "processing",
  "progress": 0.65,
  "message": "Optimizing mesh..."
}
```

**Completed:**
```json
{
  "job_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "completed",
  "progress": 1.0,
  "message": "Generation complete",
  "download_url": "/download/a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "metadata": {
    "prompt": "futuristic laser sword",
    "parameters": {
      "steps": 64,
      "guidance_scale": 15.0,
      "seed": 42
    },
    "generation_time": 28.4,
    "vertex_count": 1847,
    "face_count": 2234,
    "validation": {
      "is_watertight": true,
      "quality_score": 83.2
    }
  }
}
```

**Failed:**
```json
{
  "job_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "failed",
  "error": "Generation failed: CUDA out of memory"
}
```

**Example:**
```bash
curl "http://localhost:8000/status/a1b2c3d4-e5f6-7890-abcd-ef1234567890"
```

---

### 3. Download Asset

Download the generated 3D asset.

**Endpoint:** `GET /download/{job_id}`

**Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `lod` | integer | No | LOD level (0, 1, 2) if LODs were generated |

**Response:** `200 OK`
- Content-Type: `model/gltf-binary`
- Binary GLB file

**Example:**
```bash
# Download main asset
curl "http://localhost:8000/download/a1b2c3d4-e5f6-7890-abcd-ef1234567890" \
  -o sword.glb

# Download specific LOD
curl "http://localhost:8000/download/a1b2c3d4-e5f6-7890-abcd-ef1234567890?lod=1" \
  -o sword_LOD1.glb
```

---

### 4. Queue Status

Get overall queue health and statistics.

**Endpoint:** `GET /queue/status`

**Response:** `200 OK`
```json
{
  "total_jobs": 147,
  "queued": 5,
  "processing": 2,
  "completed": 135,
  "failed": 5
}
```

**Example:**
```bash
curl "http://localhost:8000/queue/status"
```

---

### 5. Delete Job

Delete a job and its associated files.

**Endpoint:** `DELETE /jobs/{job_id}`

**Response:** `200 OK`
```json
{
  "message": "Job deleted"
}
```

**Example:**
```bash
curl -X DELETE "http://localhost:8000/jobs/a1b2c3d4-e5f6-7890-abcd-ef1234567890"
```

---

## Error Responses

### 400 Bad Request
```json
{
  "detail": "Validation error: steps must be between 16 and 128"
}
```

### 404 Not Found
```json
{
  "detail": "Job not found"
}
```

### 500 Internal Server Error
```json
{
  "detail": "Internal server error: [error details]"
}
```

---

## Usage Examples

### Python Client

```python
import requests
import time

API_URL = "http://localhost:8000"

# 1. Submit generation job
response = requests.post(f"{API_URL}/generate", json={
    "prompt": "medieval iron sword",
    "steps": 64,
    "guidance_scale": 15.0,
    "postprocess": True,
    "generate_lods": True
})
job_id = response.json()["job_id"]
print(f"Job created: {job_id}")

# 2. Poll for completion
while True:
    status = requests.get(f"{API_URL}/status/{job_id}").json()
    print(f"Status: {status['status']} ({status['progress']*100:.0f}%)")
    
    if status["status"] == "completed":
        print("Generation complete!")
        break
    elif status["status"] == "failed":
        print(f"Generation failed: {status['error']}")
        break
    
    time.sleep(2)

# 3. Download result
response = requests.get(f"{API_URL}/download/{job_id}")
with open("sword.glb", "wb") as f:
    f.write(response.content)
print("Downloaded sword.glb")

# 4. Download LODs
for lod in [0, 1, 2]:
    response = requests.get(f"{API_URL}/download/{job_id}?lod={lod}")
    with open(f"sword_LOD{lod}.glb", "wb") as f:
        f.write(response.content)
    print(f"Downloaded sword_LOD{lod}.glb")
```

---

### JavaScript/Node.js Client

```javascript
const axios = require('axios');
const fs = require('fs');

const API_URL = 'http://localhost:8000';

async function generateAsset(prompt) {
  // Submit job
  const { data } = await axios.post(`${API_URL}/generate`, {
    prompt: prompt,
    steps: 64,
    guidance_scale: 15.0,
    postprocess: true
  });
  
  const jobId = data.job_id;
  console.log(`Job created: ${jobId}`);
  
  // Poll for completion
  while (true) {
    const status = await axios.get(`${API_URL}/status/${jobId}`);
    console.log(`Status: ${status.data.status} (${status.data.progress * 100}%)`);
    
    if (status.data.status === 'completed') {
      break;
    }
    
    await new Promise(resolve => setTimeout(resolve, 2000));
  }
  
  // Download
  const response = await axios.get(`${API_URL}/download/${jobId}`, {
    responseType: 'arraybuffer'
  });
  
  fs.writeFileSync('output.glb', response.data);
  console.log('Downloaded output.glb');
}

generateAsset('fantasy shield');
```

---

### cURL Examples

```bash
# Simple generation
JOB_ID=$(curl -s -X POST "http://localhost:8000/generate" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "wooden crate"}' | jq -r '.job_id')

echo "Job ID: $JOB_ID"

# Wait for completion
while true; do
  STATUS=$(curl -s "http://localhost:8000/status/$JOB_ID" | jq -r '.status')
  echo "Status: $STATUS"
  
  if [ "$STATUS" = "completed" ]; then
    break
  fi
  
  sleep 2
done

# Download
curl "http://localhost:8000/download/$JOB_ID" -o crate.glb
echo "Downloaded crate.glb"
```

---

## Rate Limiting

**Current:** No rate limiting

**Future (Production):**
- 10 requests/minute per IP
- 100 requests/hour per user
- 1000 requests/day per user

**Headers:**
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 87
X-RateLimit-Reset: 1699564800
```

---

## Webhooks (Future)

Subscribe to job completion events:

```python
# Register webhook
requests.post(f"{API_URL}/webhooks", json={
    "url": "https://your-server.com/webhook",
    "events": ["job.completed", "job.failed"]
})

# Webhook payload
{
  "event": "job.completed",
  "job_id": "...",
  "timestamp": "2024-03-15T10:30:00Z",
  "data": {
    "download_url": "/download/..."
  }
}
```

---

## Best Practices

### 1. Polling Interval
```python
# Good: Poll every 2-5 seconds
time.sleep(2)

# Bad: Poll every 100ms (unnecessary load)
time.sleep(0.1)
```

### 2. Error Handling
```python
try:
    response = requests.post(f"{API_URL}/generate", json=params)
    response.raise_for_status()
except requests.exceptions.HTTPError as e:
    print(f"HTTP error: {e}")
except requests.exceptions.ConnectionError:
    print("Connection failed")
except requests.exceptions.Timeout:
    print("Request timed out")
```

### 3. Async Generation (Multiple Jobs)
```python
import asyncio
import aiohttp

async def generate_multiple(prompts):
    async with aiohttp.ClientSession() as session:
        tasks = []
        for prompt in prompts:
            task = session.post(f"{API_URL}/generate", json={"prompt": prompt})
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        return [r.json()["job_id"] for r in results]

# Generate 10 assets in parallel
prompts = [f"weapon variant {i}" for i in range(10)]
job_ids = asyncio.run(generate_multiple(prompts))
```

### 4. Batch Download
```python
def download_all_lods(job_id, output_dir):
    """Download main asset and all LODs."""
    # Download main
    response = requests.get(f"{API_URL}/download/{job_id}")
    with open(f"{output_dir}/asset.glb", "wb") as f:
        f.write(response.content)
    
    # Try downloading LODs (may not exist)
    for lod in range(3):
        try:
            response = requests.get(f"{API_URL}/download/{job_id}?lod={lod}")
            if response.status_code == 200:
                with open(f"{output_dir}/asset_LOD{lod}.glb", "wb") as f:
                    f.write(response.content)
        except:
            break
```

---

## OpenAPI Schema

Full OpenAPI 3.0 specification available at:
```
http://localhost:8000/docs        # Swagger UI
http://localhost:8000/redoc       # ReDoc
http://localhost:8000/openapi.json # JSON schema
```

---

## SDK (Future)

```python
# Planned: Official Python SDK
from game_3d_generator import Client

client = Client(api_key="your-key")

# Simplified API
asset = client.generate(
    prompt="fantasy sword",
    wait=True  # Block until complete
)

asset.download("sword.glb")
asset.download_lods("./output")
print(asset.metadata)
```