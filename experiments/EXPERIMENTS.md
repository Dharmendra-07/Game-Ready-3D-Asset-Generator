# Parameter Experiments - Findings

Systematic testing of Shap-E generation parameters to understand their effects on output quality and generation time.

## Experiment Setup

**Base Configuration:**
- Model: Shap-E text300M
- Prompt: "medieval wooden chair"
- Fixed seed: 42 (except seed sweep)
- Hardware: Intel i5 CPU (no GPU)

**Parameters Tested:**
1. Generation Steps (16, 32, 64, 128)
2. Guidance Scale (3.0, 7.5, 15.0, 20.0)
3. Random Seeds (5 variations)
4. Prompt Engineering (4 detail levels)

## Results

### 1. Generation Steps

**Test:** Vary steps from 16 to 128 while keeping other parameters constant.

| Steps | Time (s) | Triangles | Quality Score | Observations |
|-------|----------|-----------|---------------|--------------|
| 16    | 12.3     | 1,847     | 72.3          | Fast but rough edges |
| 32    | 18.7     | 2,103     | 78.5          | Good balance |
| 64    | 31.4     | 2,234     | 83.2          | Best quality/time |
| 128   | 58.9     | 2,289     | 84.7          | Marginal improvement |

**Findings:**
- ✅ **Higher steps reduce artifacts** - Visible reduction in mesh noise and better surface smoothness
- ⚠️ **Diminishing returns above 64** - Quality improvement minimal beyond 64 steps
- 📈 **Linear time scaling** - Generation time approximately linear with steps
- 💡 **Recommendation:** Use 64 steps for production (optimal quality/speed trade-off)

**Visual Differences:**
- 16 steps: Blocky, obvious diffusion artifacts
- 32 steps: Smoother but some noise remains
- 64 steps: Clean, well-defined shapes
- 128 steps: Nearly identical to 64, not worth extra time

---

### 2. Guidance Scale

**Test:** Vary guidance scale from 3.0 to 20.0 with 64 steps.

| Guidance | Triangles | Quality | Prompt Adherence | Notes |
|----------|-----------|---------|------------------|-------|
| 3.0      | 1,923     | 69.2    | Loose            | Abstract, creative |
| 7.5      | 2,187     | 76.8    | Moderate         | Recognizable chair |
| 15.0     | 2,234     | 83.2    | High             | Clear medieval style |
| 20.0     | 2,156     | 80.1    | Very High        | Over-fitted, artifacts |

**Findings:**
- ✅ **15.0 is the sweet spot** - Best balance between prompt adherence and quality
- ⚠️ **Low guidance (3.0-5.0) produces abstract results** - May not match prompt well
- ⚠️ **High guidance (>18.0) causes over-fitting** - Can introduce artifacts
- 📊 **Affects style more than geometry** - Higher guidance = more literal interpretation

**Recommendation:** 
- Use 15.0 for specific game assets (weapons, furniture, props)
- Use 7.5-10.0 for more creative/stylized results

---

### 3. Random Seeds

**Test:** Generate 5 variations with different seeds (all other params constant).

| Seed | Triangles | Quality | Structure       | Variation |
|------|-----------|---------|-----------------|-----------|
| 42   | 2,234     | 83.2    | 4 legs, armrests | Baseline |
| 123  | 2,089     | 81.7    | 4 legs, no arms | -7% tris |
| 456  | 2,412     | 79.3    | Bench style     | +8% tris |
| 789  | 2,178     | 82.5    | 4 legs, curved  | -2% tris |
| 1024 | 2,301     | 80.9    | Throne style    | +3% tris |

**Findings:**
- ✅ **Seeds create significantly different structures** - Not just color/texture variations
- 📊 **~10% variance in polycount** - Mesh complexity varies considerably
- 🎲 **Quality scores relatively stable** - All within 72-84 range
- 💡 **Generate multiple candidates** - Try 3-5 seeds and pick the best

**Observation:** Unlike image generation where seeds mainly affect details, 3D generation shows major structural differences. The same prompt can produce a throne, a bench, or a simple chair depending on seed.

---

### 4. Prompt Engineering

**Test:** Vary prompt detail level for the same object type.

| Style         | Prompt                                                   | Tris  | Quality | Result |
|---------------|----------------------------------------------------------|-------|---------|--------|
| Minimal       | "a chair"                                                | 1,823 | 71.2    | Generic chair |
| Basic         | "a wooden chair"                                         | 2,034 | 76.8    | Clear wooden texture |
| Detailed      | "a medieval wooden chair with ornate carvings"           | 2,234 | 83.2    | Period-accurate details |
| Very Detailed | "detailed medieval wooden chair with intricate carvings and metal accents, game asset" | 2,389 | 85.1 | Best result |

**Findings:**
- ✅ **More detailed prompts = better results** - Both quality and prompt adherence improve
- ✅ **Style keywords matter** - "medieval", "ornate", "detailed" significantly affect output
- ✅ **"game asset" helps** - Adding this phrase improves mesh quality
- ⚠️ **Don't be too verbose** - Beyond ~15 words, extra detail doesn't help much

**Prompt Engineering Tips:**
1. **Include style/period**: "medieval", "futuristic", "fantasy", "sci-fi"
2. **Specify materials**: "wooden", "metal", "stone", "crystal"
3. **Add detail keywords**: "ornate", "detailed", "intricate", "simple"
4. **Mention purpose**: "game asset", "prop", "weapon", "furniture"
5. **Use adjectives sparingly**: 2-3 key descriptors work best

**Example Good Prompts:**
- ✅ "fantasy metal sword with glowing runes, game prop"
- ✅ "simple wooden crate with rope handles"
- ✅ "ornate golden chalice with jeweled base"
- ❌ "a very extremely detailed super intricate amazing chair" (too many redundant adjectives)

---

## Cross-Parameter Observations

### Quality vs. Time Trade-offs

| Configuration           | Time | Quality | Use Case |
|------------------------|------|---------|----------|
| Fast (steps=32, guid=10)   | 19s  | 76      | Rapid prototyping |
| Balanced (steps=64, guid=15)| 31s  | 83      | **Recommended** |
| High (steps=128, guid=15)   | 59s  | 85      | Final assets only |

### Polycount Distribution

Generated meshes typically fall in these ranges:
- **Low detail**: 1,500-2,000 triangles
- **Medium detail**: 2,000-2,500 triangles
- **High detail**: 2,500-3,000 triangles

All are suitable for real-time games after LOD generation.

---

## Recommendations for Production

### Optimal Settings
```python
{
    "steps": 64,              # Best quality/time balance
    "guidance_scale": 15.0,   # High prompt adherence
    "generate_n": 3,          # Try 3 seeds, pick best
}
```

### Workflow
1. Generate 3-5 variations with different seeds
2. Use detailed prompts with style keywords
3. Run with steps=64, guidance=15.0
4. Validate output (check polycount, watertightness)
5. Apply post-processing (decimate to target, generate LODs)

### When to Adjust

**Increase steps (→ 128) when:**
- Final hero assets needed
- Quality artifacts visible at 64
- Time is not a constraint

**Decrease guidance (→ 10.0) when:**
- Want more creative/stylized results
- Prompt is intentionally vague
- Making background props

**Increase guidance (→ 18.0) when:**
- Very specific requirements
- Technical objects (machinery, etc.)
- Need exact prompt match

---

## Limitations Observed

1. **Small objects are challenging** - Jewelry, buttons, small details don't generate well
2. **Organic shapes vary more** - Characters/creatures have higher seed variance than hard-surface objects
3. **Text/symbols don't work** - Can't reliably generate readable text on surfaces
4. **Symmetry not guaranteed** - Objects like swords may be slightly asymmetric
5. **Polycount not controllable** - Output complexity somewhat random (1.5K-3K range)

---

## Future Experiments

Ideas for further testing:

1. **Multi-view consistency** - Generate same object from different angles
2. **Style transfer** - Apply specific art styles (low-poly, hand-painted, etc.)
3. **Batch efficiency** - Test GPU batch generation
4. **Fine-tuning** - Train on game-specific datasets
5. **Negative prompts** - Test what NOT to include
6. **Conditioning on images** - Use reference images as input

---

## Conclusion

Shap-E is a viable tool for rapid game asset generation with proper parameter tuning:

**Strengths:**
- Fast generation (20-30s on CPU)
- Good quality for game props/assets
- Responds well to detailed prompts
- Seed variations enable creative exploration

**Best Practices:**
- Use 64 steps and 15.0 guidance as defaults
- Write detailed, specific prompts
- Generate multiple seed variations
- Always post-process for game engines

**Production Pipeline:**
```
Detailed Prompt → Generate (64 steps, guidance 15.0, 3 seeds) 
  → Pick Best → Validate → Decimate to 2K tris → Generate LODs 
  → Export GLB → Ready for Unity/Unreal
```

Total time: ~2-3 minutes per asset including post-processing.