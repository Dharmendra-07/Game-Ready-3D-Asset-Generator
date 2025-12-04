"""
Job queue management for asynchronous task processing.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, Optional
from datetime import datetime
import threading


class JobStatus(Enum):
  """Job status enumeration."""
  QUEUED = "queued"
  PROCESSING = "processing"
  COMPLETED = "completed"
  FAILED = "failed"
  CANCELLED = "cancelled"


@dataclass
class Job:
  """Job data structure."""
  job_id: str
  status: JobStatus = JobStatus.QUEUED
  created_at: datetime = field(default_factory=datetime.now)
  started_at: Optional[datetime] = None
  completed_at: Optional[datetime] = None
  progress: float = 0.0
  message: str = ""
  params: Dict[str, Any] = field(default_factory=dict)
  result: Optional[Dict[str, Any]] = None
  error: Optional[str] = None


class JobQueue:
  """
  Simple in-memory job queue.
  
  For production, replace with Redis/Celery for distributed processing.
  """
  
  def __init__(self):
      self.jobs: Dict[str, Job] = {}
      self.lock = threading.Lock()
  
  def create_job(self, job_id: str, params: Dict[str, Any]) -> Job:
      """Create a new job."""
      with self.lock:
          job = Job(job_id=job_id, params=params)
          self.jobs[job_id] = job
          return job
  
  def get_job(self, job_id: str) -> Optional[Job]:
      """Get job by ID."""
      return self.jobs.get(job_id)
  
  def update_job(
      self,
      job_id: str,
      status: Optional[JobStatus] = None,
      progress: Optional[float] = None,
      message: Optional[str] = None,
      result: Optional[Dict[str, Any]] = None,
      error: Optional[str] = None
  ) -> Optional[Job]:
      """Update job status and metadata."""
      with self.lock:
          job = self.jobs.get(job_id)
          if not job:
              return None
          
          if status:
              job.status = status
              
              if status == JobStatus.PROCESSING and not job.started_at:
                  job.started_at = datetime.now()
              
              if status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
                  job.completed_at = datetime.now()
          
          if progress is not None:
              job.progress = progress
          
          if message is not None:
              job.message = message
          
          if result is not None:
              job.result = result
          
          if error is not None:
              job.error = error
          
          return job
  
  def get_jobs_by_status(self, status: JobStatus) -> list:
      """Get all jobs with given status."""
      return [job for job in self.jobs.values() if job.status == status]
  
  def cleanup_old_jobs(self, max_age_hours: int = 24):
      """Remove jobs older than max_age_hours."""
      with self.lock:
          now = datetime.now()
          to_remove = []
          
          for job_id, job in self.jobs.items():
              age = (now - job.created_at).total_seconds() / 3600
              if age > max_age_hours:
                  to_remove.append(job_id)
          
          for job_id in to_remove:
              del self.jobs[job_id]
          
          return len(to_remove)


class CeleryQueue:
  """
  Celery-based queue for distributed processing.
  
  Use this for production deployments.
  """
  
  def __init__(self, broker_url: str = "redis://localhost:6379/0"):
      """
      Initialize Celery queue.
      
      Args:
          broker_url: Redis or RabbitMQ URL
      """
      from celery import Celery
      
      self.celery = Celery(
          'game_3d_generator',
          broker=broker_url,
          backend=broker_url
      )
      
      self.celery.conf.update(
          task_serializer='json',
          accept_content=['json'],
          result_serializer='json',
          timezone='UTC',
          enable_utc=True,
          task_track_started=True,
          task_time_limit=30 * 60,  # 30 minutes
          task_soft_time_limit=25 * 60,
      )
      
      self._register_tasks()
  
  def _register_tasks(self):
      """Register Celery tasks."""
      
      @self.celery.task(bind=True, name='generate_asset')
      def generate_asset_task(self, job_id: str, params: dict):
          """Celery task for asset generation."""
          from src.generation.shap_e import ShapEGenerator
          from src.postprocess.decimation import optimize_mesh_for_game
          
          # Update progress
          self.update_state(state='PROGRESS', meta={'progress': 0.0})
          
          # Generate
          generator = ShapEGenerator()
          result = generator.generate_with_metadata(**params)
          
          self.update_state(state='PROGRESS', meta={'progress': 0.5})
          
          # Post-process if requested
          if params.get('postprocess', False):
              mesh = optimize_mesh_for_game(
                  result['mesh'],
                  target_tris=params.get('target_tris', 2000)
              )
              result['mesh'] = mesh
          
          self.update_state(state='PROGRESS', meta={'progress': 0.8})
          
          # Save
          output_path = f"outputs/{job_id}.glb"
          result['mesh'].export(output_path)
          
          return {
              'job_id': job_id,
              'file_path': output_path,
              'metadata': result['metadata']
          }
      
      self.generate_asset_task = generate_asset_task
  
  def submit_job(self, job_id: str, params: dict) -> str:
      """Submit job to queue."""
      task = self.generate_asset_task.apply_async(
          args=[job_id, params],
          task_id=job_id
      )
      return task.id
  
  def get_job_status(self, job_id: str) -> dict:
      """Get job status from Celery."""
      from celery.result import AsyncResult
      
      result = AsyncResult(job_id, app=self.celery)
      
      return {
          'job_id': job_id,
          'status': result.state,
          'progress': result.info.get('progress', 0) if isinstance(result.info, dict) else 0,
          'result': result.result if result.successful() else None,
          'error': str(result.info) if result.failed() else None
      }


if __name__ == "__main__":
  # Test job queue
  queue = JobQueue()
  
  # Create job
  job = queue.create_job("test-123", {"prompt": "test"})
  print(f"Created job: {job.job_id}")
  
  # Update job
  queue.update_job("test-123", JobStatus.PROCESSING, progress=0.5)
  print(f"Updated job: {queue.get_job('test-123').status}")
  
  # Complete job
  queue.update_job("test-123", JobStatus.COMPLETED, progress=1.0, result={"file": "output.glb"})
  print(f"Completed job: {queue.get_job('test-123').result}")