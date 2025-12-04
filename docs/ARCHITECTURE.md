# Architecture Documentation

## System Overview

The Game-Ready 3D Asset Generator is a production-ready ML pipeline consisting of four main components:

```
┌─────────────────────────────────────────────────────────────┐
│                        User Interface                        │
│  (CLI Demo Script, REST API, Web UI - future)               │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│                      API Layer                               │
│  • FastAPI Server                                            │
│  • Job Queue Manager (in-memory / Celery)                   │
│  • Request Validation (Pydantic)                             │
│  • Status Tracking & File Serving                            │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│                 Generation Backend                           │
│  • Shap-E Text-to-3D Model                                  │
│  • Parameter Control (steps, guidance, seed)                │
│  • Latent Diffusion → Mesh Decoding                         │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│              Post-Processing Pipeline                        │
│  • Validation: Geometry checks, quality metrics             │
│  • Decimation: Polycount reduction                           │
│  • LOD Generation: Multi-level detail                        │
│  • Format Conversion: GLB, OBJ, FBX export                  │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│                   Output Storage                             │
│  • Generated Assets (GLB files)                              │
│  • Validation Reports (JSON)                                 │
│  • Experiment Data                                           │
└─────────────────────────────────────────────────────────────┘
```

## Component Details

### 1. Generation Backend (`src/generation/`)

**ShapEGenerator** - Primary text-to-3D model

```python
class ShapEGenerator:
    - Models: text300M, transmitter, diffusion
    - Input: Text prompt + parameters
    - Output: Trimesh object with vertex colors
    - Device: CPU/GPU auto-detection
```

**Key Design Decisions:**
- Chose Shap-E for CPU-friendliness and speed
- Supports batch generation (future: parallel processing)
- Returns standardized Trimesh objects for compatibility

**Why Shap-E?**
- ✅ Fast: 20-30s on CPU (vs 5-10min for NeRF-based methods)
- ✅ Direct mesh output (no marching cubes needed)
- ✅ Good quality for game assets
- ✅ Easy installation and inference
- ✅ From OpenAI (well-maintained, documented)

**Alternatives Considered:**
- Point-E: Lower quality but faster
- DreamFusion: Higher quality but requires GPU, much slower
- GET3D: Good for vehicles but requires training
- Magic3D: Best quality but impractical for CPU

### 2. Post-Processing Pipeline (`src/postprocess/`)

**MeshDecimator** (`decimation.py`)
- Algorithm: Quadric edge collapse decimation
- Fallback: Vertex clustering if quadric fails
- Target: Reduce to N triangles while preserving shape
- Quality metrics: Hausdorff distance, aspect ratios

**LODGenerator** (`lod.py`)
- Generates multiple detail levels (LOD0, LOD1, LOD2, ...)
- Geometric reduction: 100%, 50%, 25%, 10%
- Calculates switch distances for game engines
- Exports Unity/Unreal LOD group settings

**MeshValidator** (`validator.py`)
- **Geometry checks**: Watertight, valid, Euler number
- **Quality metrics**: Degenerate faces, aspect ratios, duplicates
- **Game compatibility**: Polycount ratings, engine limits
- **Texturing**: UV coverage, vertex colors, materials

### 3. API Layer (`src/api/`)

**FastAPI Server** (`server.py`)
- RESTful endpoints for generation, status, download
- Async request handling with BackgroundTasks
- Static file serving for asset downloads
- Pydantic models for request/response validation

**Job Queue** (`queue.py`)
- In-memory queue for single-server deployment
- Celery adapter for distributed processing
- Status tracking: queued → processing → completed/failed
- Progress updates and error handling

**Endpoints:**
```
POST   /generate         - Submit generation job
GET    /status/{job_id}  - Check job status
GET    /download/{job_id} - Download result
GET    /queue/status     - Overall queue health
DELETE /jobs/{job_id}    - Cancel/delete job
```

### 4. Experiment System (`experiments/`)

**ParameterSweep** (`param_sweep.py`)
- Systematic testing of generation parameters
- Automated result collection and validation
- JSON output for analysis
- Reproducible experiments with fixed seeds

**Tested Parameters:**
1. Steps: Effect on quality vs time
2. Guidance: Effect on prompt adherence
3. Seeds: Output variation analysis
4. Prompts: Engineering best practices

## Data Flow

### Generation Request Flow

```
User Request
    ↓
API Validation (Pydantic)
    ↓
Job Creation (UUID assigned)
    ↓
Queue (status: queued)
    ↓
Background Task Starts
    ↓
Status: processing (0%)
    ↓
Generate Mesh (Shap-E)
    ↓
Status: processing (50%)
    ↓
Validate Mesh
    ↓
Status: processing (60%)
    ↓
Optimize (decimate to target)
    ↓
Status: processing (80%)
    ↓
Generate LODs (if requested)
    ↓
Export GLB files
    ↓
Status: completed (100%)
    ↓
User downloads result
```

### File Storage Structure

```
outputs/
├── api/                    # API-generated assets
│   ├── {job_id}.glb       # Main asset
│   ├── {job_id}_LOD0.glb  # Highest detail
│   ├── {job_id}_LOD1.glb  # Medium detail
│   └── {job_id}_LOD2.glb  # Low detail
├── experiments/            # Experiment results
│   ├── steps_16.glb
│   ├── steps_32.glb
│   ├── results.json
│   └── analysis.json
└── demo/                   # Demo script outputs
    └── {timestamp}.glb
```

## Technology Stack

### Core ML
- **PyTorch** 2.0+: Deep learning framework
- **Shap-E**: Text-to-3D generation
- **Transformers**: NLP models for text encoding

### 3D Processing
- **Trimesh** 3.23+: Mesh operations, I/O
- **PyMeshLab** 2022+: Advanced mesh processing
- **Open3D** 0.17+: Visualization, analysis

### API & Queue
- **FastAPI** 0.104+: Modern async web framework
- **Uvicorn**: ASGI server
- **Pydantic** 2.4+: Data validation
- **Celery** 5.3+ (optional): Distributed task queue
- **Redis** 5.0+ (optional): Message broker

### Utilities
- **NumPy**: Numerical operations
- **Pillow**: Image processing
- **Matplotlib**: Visualization
- **PyYAML**: Configuration

## Design Patterns

### 1. Strategy Pattern (Generation Backends)

```python
class BaseGenerator(ABC):
    @abstractmethod
    def generate(self, prompt: str, **kwargs) -> trimesh.Trimesh:
        pass

class ShapEGenerator(BaseGenerator):
    def generate(self, prompt: str, **kwargs) -> trimesh.Trimesh:
        # Shap-E implementation
        
class PointEGenerator(BaseGenerator):
    def generate(self, prompt: str, **kwargs) -> trimesh.Trimesh:
        # Point-E implementation
```

Benefits:
- Easy to add new models
- Consistent interface
- Swappable backends

### 2. Pipeline Pattern (Post-Processing)

```python
def process_mesh(mesh):
    mesh = validate(mesh)
    mesh = clean(mesh)
    mesh = decimate(mesh)
    mesh = generate_lods(mesh)
    return mesh
```

Benefits:
- Modular processing steps
- Easy to reorder/skip steps
- Testable components

### 3. Job Queue Pattern (API)

```python
# Submit job
job_id = queue.create_job(params)

# Process asynchronously
background_tasks.add_task(process_job, job_id)

# Poll for results
status = queue.get_status(job_id)
```

Benefits:
- Non-blocking requests
- Scalable to multiple workers
- Graceful failure handling

## Scalability Considerations

### Current (Single Server)
- In-memory job queue
- Synchronous processing
- Local file storage
- Capacity: ~50-100 jobs/hour on CPU

### Production (Distributed)
```
Load Balancer
    ↓
Multiple API Servers (FastAPI)
    ↓
Redis (Job Queue + Cache)
    ↓
Celery Workers (5-10 workers)
    ↓
Shared Storage (S3, NFS)
```

**Improvements for Scale:**
1. **Horizontal scaling**: Multiple API servers behind load balancer
2. **Worker pool**: Celery with 5-10 GPU workers
3. **Caching**: Redis for job status and results
4. **Object storage**: S3 for generated assets
5. **Database**: PostgreSQL for job metadata
6. **Monitoring**: Prometheus + Grafana

### Performance Optimizations

**Current:**
- Single-threaded generation
- CPU-only inference
- No batch processing

**Future:**
- GPU acceleration (3-5x speedup)
- Batch generation (process 4-8 prompts together)
- Model quantization (INT8 for 2x faster)
- Cached embeddings for common prompts
- Progressive rendering (stream partial results)

## Security Considerations

### Current Implementation
- Basic input validation (Pydantic)
- No authentication/authorization
- Local file storage only
- No rate limiting

### Production Requirements
1. **Authentication**: API keys or OAuth2
2. **Rate limiting**: Per-user quotas
3. **Input sanitization**: Prevent prompt injection
4. **File validation**: Check uploaded images/files
5. **HTTPS**: Encrypt data in transit
6. **Access control**: User-specific asset access
7. **Content moderation**: Filter inappropriate prompts

## Testing Strategy

### Unit Tests
- Individual component testing
- Mock external dependencies
- Fast execution (<1s per test)

### Integration Tests
- End-to-end pipeline testing
- Real model inference
- File I/O validation

### Performance Tests
- Load testing (Apache JMeter)
- Memory profiling
- Generation time benchmarks

**Test Coverage Goals:**
- Generation: 80%
- Post-processing: 90%
- API: 85%
- Overall: 85%+

## Monitoring & Observability

### Metrics to Track
1. **Generation metrics**: Success rate, average time, queue depth
2. **Quality metrics**: Average polycount, quality scores
3. **API metrics**: Request rate, latency, error rate
4. **System metrics**: CPU/GPU usage, memory, disk

### Logging
- Structured logging (JSON format)
- Log levels: DEBUG, INFO, WARNING, ERROR
- Request tracing (correlation IDs)
- Performance profiling

### Alerting
- Queue backlog > 100 jobs
- Generation failure rate > 10%
- API latency > 5s
- Disk usage > 90%

## Deployment

### Docker Container
```dockerfile
FROM python:3.10-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "src/api/server.py"]
```

### Kubernetes
- Deployment: API servers (3 replicas)
- StatefulSet: Celery workers (5 replicas)
- Services: Load balancer, Redis
- Volumes: Shared storage for assets

### CI/CD
```yaml
# GitHub Actions
- Test (pytest)
- Lint (black, flake8)
- Build Docker image
- Deploy to staging
- Integration tests
- Deploy to production
```

## Configuration Management

### Environment Variables
```bash
MODEL_DEVICE=cuda          # cpu, cuda, mps
API_HOST=0.0.0.0
API_PORT=8000
REDIS_URL=redis://localhost:6379
OUTPUT_DIR=outputs
LOG_LEVEL=INFO
```

### Config File (`config.yaml`)
```yaml
generation:
  default_steps: 64
  default_guidance: 15.0
  max_steps: 128

postprocess:
  target_tris: 2000
  generate_lods: true
  lod_levels: [1.0, 0.5, 0.25]

api:
  max_jobs_per_user: 10
  job_timeout: 600
  cleanup_age_hours: 24
```

## Future Architecture

### Microservices (if needed)
```
API Gateway
    ├── Generation Service (Shap-E workers)
    ├── Post-processing Service (mesh optimization)
    ├── Storage Service (S3 interface)
    └── Analytics Service (usage metrics)
```

Benefits:
- Independent scaling
- Technology diversity
- Fault isolation

Downsides:
- Increased complexity
- Network overhead
- Harder debugging

**Recommendation:** Start with monolith, split only when needed (10K+ requests/day).