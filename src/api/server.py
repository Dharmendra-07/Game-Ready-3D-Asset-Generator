"""
FastAPI server for 3D asset generation with job queue.
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from typing import Optional, List
import uuid
from pathlib import Path
import uvicorn

from src.api.queue import JobQueue, JobStatus
from src.generation.shap_e import ShapEGenerator
from src.postprocess.decimation import optimize_mesh_for_game
from src.postprocess.lod import generate_lods
from src.postprocess.validator import validate_mesh, check_game_engine_compatibility
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

# Initialize
app = FastAPI(
  title="Game 3D Asset Generator API",
  description="Generate game-ready 3D assets from text prompts",
  version="1.0.0"
)

# Job queue
queue = JobQueue()

# Generator (lazy load)
generator = None

# Output directory
OUTPUT_DIR = Path("outputs/api")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


class GenerateRequest(BaseModel):
  """Request model for /generate endpoint."""
  prompt: str = Field(..., description="Text description of the 3D object")
  steps: int = Field(64, ge=16, le=128, description="Generation steps")
  guidance_scale: float = Field(15.0, ge=3.0, le=20.0, description="Guidance scale")
  seed: Optional[int] = Field(None, description="Random seed")
  postprocess: bool = Field(True, description="Apply post-processing")
  target_tris: int = Field(2000, ge=100, le=50000, description="Target triangle count")
  generate_lods: bool = Field(False, description="Generate LOD levels")


class JobResponse(BaseModel):
  """Response model for job endpoints."""
  job_id: str
  status: str
  progress: Optional[float] = None
  message: Optional[str] = None
  download_url: Optional[str] = None
  metadata: Optional[dict] = None
  error: Optional[str] = None


@app.on_event("startup")
async def startup_event():
  """Initialize generator on startup."""
  global generator
  logger.info("Initializing Shap-E generator...")
  generator = ShapEGenerator()
  logger.info("Server ready!")


@app.get("/")
async def root():
  """API root endpoint."""
  return {
      "name": "Game 3D Asset Generator API",
      "version": "1.0.0",
      "endpoints": {
          "generate": "/generate",
          "status": "/status/{job_id}",
          "download": "/download/{job_id}",
          "queue_status": "/queue/status"
      }
  }


@app.post("/generate", response_model=JobResponse)
async def generate_asset(request: GenerateRequest, background_tasks: BackgroundTasks):
  """
  Generate a 3D asset from text prompt.
  
  Returns a job_id to check status and download result.
  """
  job_id = str(uuid.uuid4())
  
  logger.info(f"New job {job_id}: {request.prompt}")
  
  # Create job
  job = queue.create_job(
      job_id=job_id,
      params={
          "prompt": request.prompt,
          "steps": request.steps,
          "guidance_scale": request.guidance_scale,
          "seed": request.seed,
          "postprocess": request.postprocess,
          "target_tris": request.target_tris,
          "generate_lods": request.generate_lods,
      }
  )
  
  # Add to background tasks
  background_tasks.add_task(process_generation_job, job_id, request)
  
  return JobResponse(
      job_id=job_id,
      status=job.status.value,
      message="Job queued for processing"
  )


@app.get("/status/{job_id}", response_model=JobResponse)
async def get_job_status(job_id: str):
  """Get status of a generation job."""
  job = queue.get_job(job_id)
  
  if not job:
      raise HTTPException(status_code=404, detail="Job not found")
  
  response = JobResponse(
      job_id=job_id,
      status=job.status.value,
      progress=job.progress,
      message=job.message
  )
  
  if job.status == JobStatus.COMPLETED:
      response.download_url = f"/download/{job_id}"
      response.metadata = job.result.get("metadata") if job.result else None
  elif job.status == JobStatus.FAILED:
      response.error = job.error
  
  return response


@app.get("/download/{job_id}")
async def download_asset(job_id: str, lod: Optional[int] = None):
  """Download generated asset."""
  job = queue.get_job(job_id)
  
  if not job:
      raise HTTPException(status_code=404, detail="Job not found")
  
  if job.status != JobStatus.COMPLETED:
      raise HTTPException(status_code=400, detail=f"Job status: {job.status.value}")
  
  # Get file path
  if lod is not None and "lod_paths" in job.result:
      file_path = job.result["lod_paths"].get(f"LOD{lod}")
      if not file_path:
          raise HTTPException(status_code=404, detail=f"LOD{lod} not found")
  else:
      file_path = job.result.get("file_path")
  
  if not file_path or not Path(file_path).exists():
      raise HTTPException(status_code=404, detail="File not found")
  
  return FileResponse(
      file_path,
      media_type="model/gltf-binary",
      filename=Path(file_path).name
  )


@app.get("/queue/status")
async def get_queue_status():
  """Get overall queue status."""
  return {
      "total_jobs": len(queue.jobs),
      "queued": len([j for j in queue.jobs.values() if j.status == JobStatus.QUEUED]),
      "processing": len([j for j in queue.jobs.values() if j.status == JobStatus.PROCESSING]),
      "completed": len([j for j in queue.jobs.values() if j.status == JobStatus.COMPLETED]),
      "failed": len([j for j in queue.jobs.values() if j.status == JobStatus.FAILED]),
  }


@app.delete("/jobs/{job_id}")
async def delete_job(job_id: str):
  """Delete a job and its files."""
  job = queue.get_job(job_id)
  
  if not job:
      raise HTTPException(status_code=404, detail="Job not found")
  
  # Delete files
  if job.result and "file_path" in job.result:
      file_path = Path(job.result["file_path"])
      if file_path.exists():
          file_path.unlink()
  
  # Remove job
  queue.jobs.pop(job_id, None)
  
  return {"message": "Job deleted"}


async def process_generation_job(job_id: str, request: GenerateRequest):
  """Background task to process generation job."""
  job = queue.get_job(job_id)
  
  try:
      # Update status
      queue.update_job(job_id, JobStatus.PROCESSING, progress=0.0, message="Generating mesh...")
      
      # Generate mesh
      result = generator.generate_with_metadata(
          prompt=request.prompt,
          steps=request.steps,
          guidance_scale=request.guidance_scale,
          seed=request.seed
      )
      mesh = result['mesh']
      metadata = result['metadata']
      
      queue.update_job(job_id, JobStatus.PROCESSING, progress=0.5, message="Validating...")
      
      # Validate
      validation = validate_mesh(mesh)
      compat = check_game_engine_compatibility(mesh)
      metadata['validation'] = validation
      metadata['compatibility'] = compat
      
      # Post-process
      if request.postprocess:
          queue.update_job(job_id, JobStatus.PROCESSING, progress=0.6, message="Optimizing mesh...")
          mesh = optimize_mesh_for_game(mesh, target_tris=request.target_tris)
      
      # Save main file
      output_path = OUTPUT_DIR / f"{job_id}.glb"
      mesh.export(str(output_path))
      
      result_data = {
          "file_path": str(output_path),
          "metadata": metadata
      }
      
      # Generate LODs
      if request.generate_lods:
          queue.update_job(job_id, JobStatus.PROCESSING, progress=0.8, message="Generating LODs...")
          lods = generate_lods(mesh, levels=[1.0, 0.5, 0.25])
          
          lod_paths = {}
          for i, lod_mesh in enumerate(lods):
              lod_path = OUTPUT_DIR / f"{job_id}_LOD{i}.glb"
              lod_mesh.export(str(lod_path))
              lod_paths[f"LOD{i}"] = str(lod_path)
          
          result_data["lod_paths"] = lod_paths
      
      # Complete
      queue.update_job(
          job_id,
          JobStatus.COMPLETED,
          progress=1.0,
          message="Generation complete",
          result=result_data
      )
      
      logger.info(f"Job {job_id} completed successfully")
      
  except Exception as e:
      logger.error(f"Job {job_id} failed: {e}")
      queue.update_job(
          job_id,
          JobStatus.FAILED,
          error=str(e)
      )


if __name__ == "__main__":
  uvicorn.run(
      "src.api.server:app",
      host="0.0.0.0",
      port=8000,
      reload=True
  )