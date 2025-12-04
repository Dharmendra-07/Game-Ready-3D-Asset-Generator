"""
Systematic parameter sweep experiments.
"""

import json
import time
from pathlib import Path
from typing import Dict, List, Any
from itertools import product
import numpy as np

from src.generation.shap_e import ShapEGenerator
from src.postprocess.validator import validate_mesh
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class ParameterSweep:
    """Run systematic parameter experiments."""
    
    def __init__(self, output_dir: str = "outputs/experiments"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.generator = ShapEGenerator()
        self.results = []
    
    def run_single_experiment(
        self,
        prompt: str,
        params: Dict[str, Any],
        experiment_id: str
    ) -> Dict[str, Any]:
        """Run single experiment with given parameters."""
        logger.info(f"Running experiment {experiment_id}: {params}")
        
        start_time = time.time()
        
        try:
            # Generate mesh
            result = self.generator.generate_with_metadata(
                prompt=prompt,
                **params
            )
            mesh = result['mesh']
            metadata = result['metadata']
            
            # Validate
            validation = validate_mesh(mesh)
            
            # Save mesh
            output_path = self.output_dir / f"{experiment_id}.glb"
            mesh.export(str(output_path))
            
            # Collect results
            experiment_result = {
                'experiment_id': experiment_id,
                'prompt': prompt,
                'parameters': params,
                'generation_time': metadata['generation_time'],
                'total_time': time.time() - start_time,
                'vertex_count': validation['vertex_count'],
                'triangle_count': validation['triangle_count'],
                'is_watertight': validation['is_watertight'],
                'quality_score': validation['overall_quality_score'],
                'output_file': str(output_path),
                'success': True,
                'error': None
            }
            
            logger.info(f"Experiment {experiment_id} completed: "
                       f"{validation['triangle_count']} tris, "
                       f"quality {validation['overall_quality_score']:.1f}")
            
            return experiment_result
            
        except Exception as e:
            logger.error(f"Experiment {experiment_id} failed: {e}")
            return {
                'experiment_id': experiment_id,
                'prompt': prompt,
                'parameters': params,
                'success': False,
                'error': str(e)
            }
    
    def run_steps_sweep(
        self,
        prompt: str = "medieval wooden chair",
        steps_values: List[int] = [16, 32, 64, 128]
    ) -> List[Dict]:
        """Test effect of generation steps."""
        logger.info(f"=== Steps Sweep: {steps_values} ===")
        
        results = []
        for steps in steps_values:
            exp_id = f"steps_{steps}"
            result = self.run_single_experiment(
                prompt=prompt,
                params={'steps': steps, 'guidance_scale': 15.0, 'seed': 42},
                experiment_id=exp_id
            )
            results.append(result)
        
        return results
    
    def run_guidance_sweep(
        self,
        prompt: str = "futuristic sword",
        guidance_values: List[float] = [3.0, 7.5, 15.0, 20.0]
    ) -> List[Dict]:
        """Test effect of guidance scale."""
        logger.info(f"=== Guidance Scale Sweep: {guidance_values} ===")
        
        results = []
        for guidance in guidance_values:
            exp_id = f"guidance_{guidance:.1f}"
            result = self.run_single_experiment(
                prompt=prompt,
                params={'steps': 64, 'guidance_scale': guidance, 'seed': 42},
                experiment_id=exp_id
            )
            results.append(result)
        
        return results
    
    def run_seed_sweep(
        self,
        prompt: str = "fantasy shield",
        num_seeds: int = 5
    ) -> List[Dict]:
        """Test effect of random seed."""
        logger.info(f"=== Seed Sweep: {num_seeds} variations ===")
        
        results = []
        seeds = [42, 123, 456, 789, 1024][:num_seeds]
        
        for i, seed in enumerate(seeds):
            exp_id = f"seed_{i}_{seed}"
            result = self.run_single_experiment(
                prompt=prompt,
                params={'steps': 64, 'guidance_scale': 15.0, 'seed': seed},
                experiment_id=exp_id
            )
            results.append(result)
        
        return results
    
    def run_prompt_engineering_sweep(
        self,
        base_object: str = "chair"
    ) -> List[Dict]:
        """Test effect of prompt detail."""
        logger.info("=== Prompt Engineering Sweep ===")
        
        prompts = {
            'minimal': f"a {base_object}",
            'basic': f"a wooden {base_object}",
            'detailed': f"a medieval wooden {base_object} with ornate carvings",
            'very_detailed': f"a detailed medieval wooden {base_object} with intricate ornate carvings and metal accents, game asset",
        }
        
        results = []
        for style, prompt in prompts.items():
            exp_id = f"prompt_{style}"
            result = self.run_single_experiment(
                prompt=prompt,
                params={'steps': 64, 'guidance_scale': 15.0, 'seed': 42},
                experiment_id=exp_id
            )
            results.append(result)
        
        return results
    
    def run_full_sweep(self) -> Dict[str, List[Dict]]:
        """Run all parameter sweeps."""
        logger.info("=== Starting Full Parameter Sweep ===")
        
        all_results = {
            'steps': self.run_steps_sweep(),
            'guidance': self.run_guidance_sweep(),
            'seeds': self.run_seed_sweep(),
            'prompts': self.run_prompt_engineering_sweep()
        }
        
        # Save results
        results_path = self.output_dir / "results.json"
        with open(results_path, 'w') as f:
            json.dump(all_results, f, indent=2)
        
        logger.info(f"Results saved to {results_path}")
        
        return all_results
    
    def analyze_results(self, results: Dict[str, List[Dict]]) -> Dict[str, Any]:
        """Analyze experimental results."""
        analysis = {}
        
        # Steps analysis
        if 'steps' in results:
            steps_data = [r for r in results['steps'] if r['success']]
            if steps_data:
                analysis['steps'] = {
                    'parameter_values': [r['parameters']['steps'] for r in steps_data],
                    'generation_times': [r['generation_time'] for r in steps_data],
                    'triangle_counts': [r['triangle_count'] for r in steps_data],
                    'quality_scores': [r['quality_score'] for r in steps_data],
                    'finding': self._analyze_steps(steps_data)
                }
        
        # Guidance analysis
        if 'guidance' in results:
            guidance_data = [r for r in results['guidance'] if r['success']]
            if guidance_data:
                analysis['guidance'] = {
                    'parameter_values': [r['parameters']['guidance_scale'] for r in guidance_data],
                    'triangle_counts': [r['triangle_count'] for r in guidance_data],
                    'quality_scores': [r['quality_score'] for r in guidance_data],
                    'finding': self._analyze_guidance(guidance_data)
                }
        
        # Seed analysis
        if 'seeds' in results:
            seed_data = [r for r in results['seeds'] if r['success']]
            if seed_data:
                tri_counts = [r['triangle_count'] for r in seed_data]
                analysis['seeds'] = {
                    'num_variations': len(seed_data),
                    'triangle_count_std': float(np.std(tri_counts)),
                    'triangle_count_range': (min(tri_counts), max(tri_counts)),
                    'finding': f"Random seeds produce significant variation (tri count std: {np.std(tri_counts):.0f})"
                }
        
        # Prompt analysis
        if 'prompts' in results:
            prompt_data = [r for r in results['prompts'] if r['success']]
            if prompt_data:
                analysis['prompts'] = {
                    'styles': [r['experiment_id'].replace('prompt_', '') for r in prompt_data],
                    'quality_scores': [r['quality_score'] for r in prompt_data],
                    'finding': self._analyze_prompts(prompt_data)
                }
        
        return analysis
    
    def _analyze_steps(self, data: List[Dict]) -> str:
        """Analyze steps parameter effect."""
        times = [r['generation_time'] for r in data]
        qualities = [r['quality_score'] for r in data]
        
        time_increase = (times[-1] - times[0]) / times[0] * 100
        quality_change = qualities[-1] - qualities[0]
        
        return (f"Increasing steps from {data[0]['parameters']['steps']} to "
                f"{data[-1]['parameters']['steps']} increases time by {time_increase:.0f}% "
                f"and changes quality by {quality_change:+.1f} points")
    
    def _analyze_guidance(self, data: List[Dict]) -> str:
        """Analyze guidance scale effect."""
        qualities = [r['quality_score'] for r in data]
        best_idx = qualities.index(max(qualities))
        best_guidance = data[best_idx]['parameters']['guidance_scale']
        
        return f"Best quality ({qualities[best_idx]:.1f}) achieved at guidance scale {best_guidance}"
    
    def _analyze_prompts(self, data: List[Dict]) -> str:
        """Analyze prompt engineering effect."""
        qualities = [r['quality_score'] for r in data]
        best_idx = qualities.index(max(qualities))
        best_style = data[best_idx]['experiment_id'].replace('prompt_', '')
        
        return f"'{best_style}' prompt style achieved best quality ({qualities[best_idx]:.1f})"


def main():
    """Run parameter sweep experiments."""
    sweep = ParameterSweep()
    
    # Run all experiments
    results = sweep.run_full_sweep()
    
    # Analyze
    analysis = sweep.analyze_results(results)
    
    # Save analysis
    analysis_path = sweep.output_dir / "analysis.json"
    with open(analysis_path, 'w') as f:
        json.dump(analysis, f, indent=2)
    
    # Print summary
    print("\n=== Experiment Summary ===\n")
    for category, data in analysis.items():
        print(f"{category.upper()}:")
        print(f"  {data.get('finding', 'N/A')}\n")


if __name__ == "__main__":
    main()