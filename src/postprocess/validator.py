"""
Mesh validation and quality metrics for game assets.
"""

import trimesh
import numpy as np
from typing import Dict, Any, Optional
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


def validate_mesh(mesh: trimesh.Trimesh) -> Dict[str, Any]:
  """
  Comprehensive mesh validation with quality metrics.
  
  Args:
      mesh: Input mesh to validate
  
  Returns:
      Dict containing validation metrics
  """
  metrics = {}
  
  # Basic counts
  metrics['vertex_count'] = len(mesh.vertices)
  metrics['triangle_count'] = len(mesh.faces)
  metrics['edge_count'] = len(mesh.edges_unique)
  
  # Geometry checks
  metrics['is_watertight'] = mesh.is_watertight
  metrics['is_valid'] = mesh.is_valid
  metrics['euler_number'] = mesh.euler_number
  
  # Bounding box
  bounds = mesh.bounds
  metrics['bounds_min'] = bounds[0].tolist()
  metrics['bounds_max'] = bounds[1].tolist()
  metrics['bounds_size'] = (bounds[1] - bounds[0]).tolist()
  metrics['scale'] = float(mesh.scale)
  
  # Volume and area
  if mesh.is_watertight:
      metrics['volume'] = float(mesh.volume)
      metrics['is_convex'] = mesh.is_convex
  else:
      metrics['volume'] = None
      metrics['is_convex'] = None
  
  metrics['surface_area'] = float(mesh.area)
  
  # UV mapping
  if hasattr(mesh.visual, 'uv') and mesh.visual.uv is not None:
      metrics['has_uvs'] = True
      metrics['uv_count'] = len(mesh.visual.uv)
      metrics['uv_coverage'] = calculate_uv_coverage(mesh)
  else:
      metrics['has_uvs'] = False
      metrics['uv_count'] = 0
      metrics['uv_coverage'] = 0.0
  
  # Vertex colors
  if hasattr(mesh.visual, 'vertex_colors') and mesh.visual.vertex_colors is not None:
      metrics['has_vertex_colors'] = True
  else:
      metrics['has_vertex_colors'] = False
  
  # Material/texture
  if hasattr(mesh.visual, 'material'):
      metrics['has_material'] = True
  else:
      metrics['has_material'] = False
  
  # Mesh quality
  quality = check_mesh_quality(mesh)
  metrics.update(quality)
  
  return metrics


def check_mesh_quality(mesh: trimesh.Trimesh) -> Dict[str, Any]:
  """
  Check mesh quality issues.
  
  Returns:
      Dict with quality metrics
  """
  quality = {}
  
  # Check for degenerate faces
  face_areas = mesh.area_faces
  degenerate_faces = np.sum(face_areas < 1e-10)
  quality['degenerate_faces'] = int(degenerate_faces)
  quality['degenerate_faces_percent'] = float(degenerate_faces / len(mesh.faces) * 100)
  
  # Check for duplicate vertices
  unique_vertices = len(np.unique(mesh.vertices, axis=0))
  duplicates = len(mesh.vertices) - unique_vertices
  quality['duplicate_vertices'] = int(duplicates)
  
  # Check for unreferenced vertices
  referenced = np.unique(mesh.faces.flatten())
  unreferenced = len(mesh.vertices) - len(referenced)
  quality['unreferenced_vertices'] = int(unreferenced)
  
  # Triangle quality (aspect ratio)
  if len(mesh.faces) > 0:
      # Calculate edge lengths for each triangle
      edges = mesh.vertices[mesh.faces]
      edge_lengths = np.linalg.norm(
          edges[:, [1, 2, 0]] - edges[:, [0, 1, 2]], axis=2
      )
      
      # Aspect ratio: longest edge / shortest edge
      aspect_ratios = edge_lengths.max(axis=1) / (edge_lengths.min(axis=1) + 1e-10)
      
      quality['mean_aspect_ratio'] = float(np.mean(aspect_ratios))
      quality['max_aspect_ratio'] = float(np.max(aspect_ratios))
      quality['poor_quality_tris'] = int(np.sum(aspect_ratios > 10))
      quality['poor_quality_tris_percent'] = float(
          np.sum(aspect_ratios > 10) / len(mesh.faces) * 100
      )
  
  # Overall quality score (0-100)
  score = 100.0
  score -= quality['degenerate_faces_percent']
  score -= min(quality.get('poor_quality_tris_percent', 0), 20)
  score -= min(duplicates / len(mesh.vertices) * 100, 10)
  quality['overall_quality_score'] = max(0, min(100, score))
  
  return quality


def calculate_uv_coverage(mesh: trimesh.Trimesh) -> float:
  """
  Calculate UV map coverage (0.0 to 1.0).
  
  Returns:
      Coverage percentage
  """
  if not hasattr(mesh.visual, 'uv') or mesh.visual.uv is None:
      return 0.0
  
  uv = mesh.visual.uv
  
  # Check if UVs are in valid range [0, 1]
  valid_uvs = np.sum((uv >= 0) & (uv <= 1), axis=0)
  coverage = np.mean(valid_uvs) / 2.0  # Divide by 2 for u and v
  
  return float(coverage)


def check_game_engine_compatibility(mesh: trimesh.Trimesh) -> Dict[str, Any]:
  """
  Check compatibility with common game engines (Unity, Unreal).
  
  Returns:
      Dict with compatibility info
  """
  compat = {}
  
  # Polygon count recommendations
  vertex_count = len(mesh.vertices)
  tri_count = len(mesh.faces)
  
  if tri_count < 500:
      compat['polycount_rating'] = 'Low (good for mobile)'
  elif tri_count < 2000:
      compat['polycount_rating'] = 'Medium (good for most games)'
  elif tri_count < 10000:
      compat['polycount_rating'] = 'High (desktop/console)'
  else:
      compat['polycount_rating'] = 'Very High (may need optimization)'
  
  # Check for common issues
  issues = []
  
  if not mesh.is_watertight:
      issues.append("Mesh is not watertight (may cause issues with physics)")
  
  if not mesh.is_valid:
      issues.append("Mesh has invalid geometry")
  
  if not (hasattr(mesh.visual, 'uv') and mesh.visual.uv is not None):
      issues.append("No UV mapping (textures won't work)")
  
  quality = check_mesh_quality(mesh)
  if quality['degenerate_faces'] > 0:
      issues.append(f"{quality['degenerate_faces']} degenerate faces found")
  
  if quality.get('poor_quality_tris', 0) > tri_count * 0.1:
      issues.append("More than 10% of triangles have poor aspect ratio")
  
  compat['issues'] = issues
  compat['is_game_ready'] = len(issues) == 0
  
  # Unity specific
  compat['unity'] = {
      'max_vertices': 65535,  # Unity mesh limit
      'within_limits': vertex_count <= 65535,
      'recommended_format': 'GLB' if mesh.visual.material else 'FBX'
  }
  
  # Unreal specific
  compat['unreal'] = {
      'max_triangles': 50000,  # Recommended for real-time
      'within_limits': tri_count <= 50000,
      'recommended_format': 'FBX'
  }
  
  return compat


def generate_validation_report(mesh: trimesh.Trimesh, output_path: Optional[str] = None) -> str:
  """
  Generate human-readable validation report.
  
  Args:
      mesh: Mesh to validate
      output_path: Optional path to save report
  
  Returns:
      Report as string
  """
  metrics = validate_mesh(mesh)
  compat = check_game_engine_compatibility(mesh)
  
  report = f"""
=== Mesh Validation Report ===

Basic Info:
Vertices: {metrics['vertex_count']:,}
Triangles: {metrics['triangle_count']:,}
Edges: {metrics['edge_count']:,}

Geometry:
Watertight: {'✓' if metrics['is_watertight'] else '✗'}
Valid: {'✓' if metrics['is_valid'] else '✗'}
Volume: {metrics['volume']:.4f if metrics['volume'] else 'N/A'}
Surface Area: {metrics['surface_area']:.4f}

Bounds:
Size: [{metrics['bounds_size'][0]:.3f}, {metrics['bounds_size'][1]:.3f}, {metrics['bounds_size'][2]:.3f}]
Scale: {metrics['scale']:.4f}

Texturing:
UV Mapping: {'✓' if metrics['has_uvs'] else '✗'}
UV Coverage: {metrics['uv_coverage']*100:.1f}%
Vertex Colors: {'✓' if metrics['has_vertex_colors'] else '✗'}

Quality:
Overall Score: {metrics['overall_quality_score']:.1f}/100
Degenerate Faces: {metrics['degenerate_faces']} ({metrics['degenerate_faces_percent']:.2f}%)
Mean Aspect Ratio: {metrics.get('mean_aspect_ratio', 0):.2f}
Poor Quality Tris: {metrics.get('poor_quality_tris', 0)} ({metrics.get('poor_quality_tris_percent', 0):.2f}%)

Game Engine Compatibility:
Polycount Rating: {compat['polycount_rating']}
Game Ready: {'✓' if compat['is_game_ready'] else '✗'}

Unity:
  Within Limits: {'✓' if compat['unity']['within_limits'] else '✗'}
  Recommended Format: {compat['unity']['recommended_format']}

Unreal:
  Within Limits: {'✓' if compat['unreal']['within_limits'] else '✗'}
  Recommended Format: {compat['unreal']['recommended_format']}

"""
  
  if compat['issues']:
      report += "Issues Found:\n"
      for issue in compat['issues']:
          report += f"  ⚠ {issue}\n"
  else:
      report += "✓ No issues found!\n"
  
  if output_path:
      with open(output_path, 'w') as f:
          f.write(report)
      logger.info(f"Validation report saved to {output_path}")
  
  return report


if __name__ == "__main__":
  # Test validation
  mesh = trimesh.creation.box(extents=[2, 1, 0.5])
  report = generate_validation_report(mesh)
  print(report)