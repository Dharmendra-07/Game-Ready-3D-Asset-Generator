# Game-Ready 3D Asset Generator

A production-ready ML pipeline for generating and optimizing 3D game assets from text prompts. Features include automated post-processing, quality validation, LOD generation, and a REST API with job queue.

## 🎯 Features

### Core Capabilities
- **Text-to-3D Generation** using OpenAI's Shap-E (CPU-friendly, fast)
- **REST API** with FastAPI and async job queue
- **Automated Post-Processing**: decimation, LOD generation, format conversion
- **Quality Validation**: polycount analysis, UV map detection, import testing
- **Systematic Experiments**: parameter sweeps with detailed analysis

### Why Shap-E?
- ✅ Fast generation (15-30s on CPU)
- ✅ Decent quality for game props/assets
- ✅ Directly outputs meshes (not NeRF/voxels)
- ✅ Easy to install and run locally
- ✅ Good parameter control

## 🚀 Quick Start

### Installation

```bash
# Clone repository
git clone https://github.com/yourusername/game-3d-generator.git
cd game-3d-generator

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Basic Usage

```bash
# Generate a single asset
python demo.py --prompt "medieval wooden chair" --output outputs/chair.glb

# With parameters
python demo.py --prompt "futuristic sword" \
    --steps 64 \
    --guidance-scale 15.0 \
    --seed 42 \
    --postprocess \
    --target-tris 2000

# Run experiments
python run_experiments.py

# Start API server
python src/api/server.py
```

### API Usage

```bash
# Generate asset
curl -X POST "http://localhost:8000/generate" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "fantasy shield", "steps": 64, "postprocess": true}'

# Response: {"job_id": "abc123", "status": "queued"}

# Check status
curl "http://localhost:8000/status/abc123"

# Response: {"status": "completed", "download_url": "/download/abc123"}
```

## 📁 Project Structure

```
game-3d-generator/
├── src/
│   ├── api/              # REST API and job queue
│   ├── generation/       # ML model backends
│   ├── postprocess/      # Mesh optimization
│   └── utils/           # Shared utilities
├── experiments/         # Parameter testing
├── outputs/            # Generated assets
├── docs/              # Documentation
├── demo.py           # Simple demo script
└── run_experiments.py
```

## 🔬 Parameter Experiments

Tested parameters:
- **Steps**: 16, 32, 64, 128 (generation iterations)
- **Guidance Scale**: 3.0, 7.5, 15.0 (prompt adherence)
- **Seed**: Multiple random seeds (output variation)
- **Prompt Engineering**: Detailed vs. concise

Key findings documented in `experiments/EXPERIMENTS.md`:
- Higher steps (64-128) reduce artifacts but increase time
- Guidance scale 15.0 produces most prompt-accurate results
- Different seeds create significantly different structures
- Detailed prompts ("medieval wooden chair with ornate carvings") outperform vague ones

## 🎮 Post-Processing Pipeline

1. **Validation**: Check polycount, UV maps, watertightness
2. **Decimation**: Reduce to target triangle count (default: 2000)
3. **LOD Generation**: Create LOD0, LOD1 (50%), LOD2 (25%)
4. **Format Conversion**: Export as GLB for Unity/Unreal
5. **Quality Report**: Generate metrics JSON

## 📊 Quality Metrics

Automated validation includes:
- Triangle/vertex count
- UV map presence and coverage
- Mesh watertightness
- Bounding box dimensions
- Import success in Blender/Unity

Example output:
```json
{
  "polycount": 1847,
  "vertices": 924,
  "has_uvs": true,
  "watertight": true,
  "bounds": [1.2, 0.8, 0.5],
  "generation_time": 23.4
}
```

## 🏗️ Architecture

### Generation Backend
- `ShapEGenerator`: Primary text-to-3D model
- Configurable parameters: steps, guidance scale, seed
- Outputs mesh + texture data

### Post-Processing
- `MeshDecimator`: Reduces polycount while preserving shape
- `LODGenerator`: Creates multiple detail levels
- `FormatConverter`: Exports to GLB, OBJ, FBX
- `MeshValidator`: Quality checks and metrics

### API Layer
- FastAPI with async/await
- Redis-based job queue (or in-memory fallback)
- Status tracking and progress updates
- File delivery via static serving

## 🔄 Example Workflow

```python
from src.generation.shap_e import ShapEGenerator
from src.postprocess.decimation import decimate_mesh
from src.postprocess.lod import generate_lods

# Generate
generator = ShapEGenerator()
mesh = generator.generate("fantasy axe", steps=64, guidance_scale=15.0)

# Optimize
mesh_optimized = decimate_mesh(mesh, target_faces=2000)

# Create LODs
lods = generate_lods(mesh_optimized, levels=[1.0, 0.5, 0.25])

# Export
for i, lod_mesh in enumerate(lods):
    lod_mesh.export(f"axe_LOD{i}.glb")
```

## 📈 Performance

On Intel i5 CPU (no GPU):
- Generation: 20-35s (depending on steps)
- Decimation: 1-3s
- LOD generation: 2-5s
- Total pipeline: 25-45s per asset

## 🔮 Future Improvements

With more time/resources:

1. **Better Models**
   - Fine-tune on game asset dataset
   - Integrate DreamFusion or Magic3D for higher quality
   - Multi-view consistent generation

2. **Advanced Post-Processing**
   - Auto-UV unwrapping optimization
   - PBR texture generation
   - Automatic rigging for characters
   - Material assignment

3. **Production Features**
   - Batch processing
   - Asset versioning
   - Unity/Unreal plugins
   - Cloud deployment (AWS/GCP)
   - GPU acceleration
   - Style transfer for consistent art direction

4. **Quality Improvements**
   - Training custom LoRAs for specific game styles
   - Physics collision mesh generation
   - Topology optimization
   - Normal map baking

## 🛠️ Technical Stack

- **ML**: PyTorch, Transformers, Shap-E
- **3D**: Trimesh, PyMeshLab, Open3D
- **API**: FastAPI, Pydantic, Redis
- **Utils**: NumPy, Pillow, Matplotlib

## 📝 Sample Outputs

See `outputs/` directory for:
- Generated GLB models
- Parameter comparison screenshots
- Experiment result visualizations
- Quality metric reports

## 🤝 Contributing

Improvements welcome! Areas of interest:
- Additional model backends
- Better post-processing algorithms
- Unity/Unreal integration
- Documentation improvements

## 📄 License

MIT License - See LICENSE file

## 🔗 Resources

- [Shap-E Paper](https://arxiv.org/abs/2305.02463)
- [API Documentation](docs/API.md)
- [Architecture Details](docs/ARCHITECTURE.md)
- [Experiment Results](experiments/EXPERIMENTS.md)