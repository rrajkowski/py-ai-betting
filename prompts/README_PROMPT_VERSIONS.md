ru# Prompt Versions - AI Picks System

## Current Versions

### `picks_prompt_v1.txt` (V1 - Original, Archived)
- **Created**: Pre-Feb 2026
- **Size**: 1,793 words (178 lines)
- **Min Confidence**: 3 stars (with fallback)
- **Status**: 📦 Archived

**Characteristics**:
- Comprehensive but verbose
- Allows 3-star picks as fallback
- Redundant validation rules (repeated 3x)
- Complex confidence weighting system

**Performance**:
- Response time: ~12-14 seconds (NBA)
- Effective but slower

---

### `picks_prompt.txt` (V2 - Feb 2026 Optimized, Active)
- **Created**: 2026-02-09
- **Size**: 620 words (123 lines)
- **Min Confidence**: 4 stars (strict, 3-star fallback per sport)
- **Status**: ✅ Active in production

**Characteristics**:
- 65% smaller than V1
- Processing steps guide at top
- Consolidated validation checklist
- Stricter quality standards (4-star minimum)
- Table format for source baselines

**Performance**:
- Response time: ~2-3 seconds (NBA)
- **70-80% faster** than V1
- Same or better quality (stricter filtering)

**Key Improvements**:
1. **Speed**: Reduced prompt size and clearer structure
2. **Quality**: 4-star minimum (no 3-star fallback)
3. **Maintainability**: Single validation checklist, less redundancy
4. **Clarity**: Processing steps, table format for baselines

---

## Comparison Summary

| Metric | V1 (Original) | V2 (Feb 2026) | Improvement |
|--------|---------------|---------------|-------------|
| **Prompt Size** | 1,793 words | 620 words | **-65.4%** |
| **Response Time** | 12-14s | 2-3s | **-78%** |
| **Min Confidence** | 3 stars | 4 stars | **Stricter** |
| **Validation Rules** | Scattered (3x) | Consolidated (1x) | **Cleaner** |
| **Processing Guide** | None | 5-step workflow | **Better** |

---

## Migration Guide

### V2 is Now Active

V2 (`picks_prompt.txt`) is the active prompt loaded by `app/picks.py`.

**To rollback to V1**:
1. Rename `picks_prompt.txt` → `picks_prompt_v2.txt`
2. Rename `picks_prompt_v1.txt` → `picks_prompt.txt`
3. No code changes needed — `app/picks.py` always loads `picks_prompt.txt`

---

## Testing

### Comparison Script
```bash
python3 scripts/compare_prompts_nba.py
```

This script:
- Tests both prompts side-by-side
- Measures response time, prompt size, confidence
- Saves results to `test_results/prompt_comparison_*.json`
- Generates detailed comparison metrics

### Test Results
See: `test_results/PROMPT_COMPARISON_REPORT_FEB2026.md`

---

## Recommendations

### ✅ **Use V2 for Production**

**Reasons**:
1. **70-80% faster** = Lower API costs + better UX
2. **65% smaller** = Easier to maintain
3. **Stricter quality** = Better long-term win rate
4. **Clearer structure** = Less prone to errors

### 📊 **Monitor These Metrics**

When deploying V2:
1. **Response time**: Should be 2-4s (vs 12-14s)
2. **Average confidence**: Should be 4+ stars
3. **Empty pick rate**: May increase (expected with stricter filtering)
4. **Win rate**: Track over 20-30 picks

---

## Version History

| Version | Date | Changes | Status |
|---------|------|---------|--------|
| V1 | Pre-2026 | Original prompt | 📦 Archived (`picks_prompt_v1.txt`) |
| V2 | 2026-02-09 | 65% smaller, 4-star min, 70-80% faster | ✅ Active (`picks_prompt.txt`) |

---

## Future Improvements

Potential enhancements for V3:
1. **Dynamic confidence thresholds** based on sport/time
2. **Ensemble voting** across multiple LLM calls
3. **Confidence calibration** based on historical win rate
4. **Market-specific rules** (e.g., totals vs spreads)
5. **Injury/news integration** for real-time adjustments

