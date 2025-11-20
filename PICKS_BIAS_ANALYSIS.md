# AI Picks Bias Analysis & Fix

## Problem Identified

**Date**: 2025-11-20  
**Issue**: AI picks showing heavy bias toward totals (90%) and Under bets (78%)

### Observed Bias in Picks:
- **90% Totals** (9 out of 10 picks)
- **78% Under** (7 out of 9 totals)
- **10% H2H** (1 out of 10 picks)
- **0% Spreads** (0 out of 10 picks)

### Expected Distribution:
- **~33% Spreads**
- **~33% Totals**
- **~33% H2H/Moneyline**

---

## Root Cause Analysis

### Investigation Steps:

1. **Checked AI Prompt** ✅
   - Prompt does NOT explicitly favor totals
   - Prompt asks for "best value bets" without market preference

2. **Checked Scraped Data** ⚠️ **ROOT CAUSE FOUND**
   - Analyzed `prompt_context` table with 262 entries
   - **81% of scraped data is totals** (213 out of 262 entries)
   - **17% spreads** (44 out of 262 entries)
   - **2% moneyline** (5 out of 262 entries)

### Data Source Breakdown:

| Source | Totals | Spreads | Moneyline | Total |
|--------|--------|---------|-----------|-------|
| **OddsShark** | 194 (100%) | 0 (0%) | 0 (0%) | 194 |
| **OddsTrader** | 10 (20%) | 35 (70%) | 5 (10%) | 50 |
| **CBS Sports** | 9 (50%) | 9 (50%) | 0 (0%) | 18 |

**Key Finding**: OddsShark provides 74% of all scraped data (194 out of 262), and **100% of OddsShark data is totals**.

---

## Why This Causes Bias

1. **Consensus Requirement**: AI prompt requires 2+ sources to agree for high confidence
2. **OddsShark Dominance**: OddsShark provides 74% of data, all totals
3. **Limited Spread/ML Data**: Only 17% spreads, 2% moneyline in scraped data
4. **AI Follows Data**: AI correctly identifies consensus, but consensus is biased toward totals

**The AI is working correctly** - it's finding consensus in the data. The problem is the data itself is biased.

---

## Solution Implemented

### Short-Term Fix (Prompt Enhancement):

Added explicit market diversity requirements to AI prompt:

```
2. **MARKET DIVERSITY REQUIREMENT** (CRITICAL):
   - **MUST include picks from ALL THREE markets**: spreads, totals, h2h/moneyline
   - Target distribution: ~33% spreads, ~33% totals, ~33% h2h
   - If context data is heavily weighted toward one market, actively seek picks from underrepresented markets
   - **DO NOT generate only totals picks** - this is a common bias to avoid
   - Prioritize spread and h2h picks if totals are overrepresented in context

7. **PICK SELECTION STRATEGY**:
   - Return a maximum of 3 picks
   - Prioritize highest consensus first
   - **ENSURE MARKET DIVERSITY**: If all 3 picks are from the same market, replace the lowest confidence pick with a pick from a different market
   - Example good output: 1 spread, 1 total, 1 h2h
   - Example bad output: 3 totals (too concentrated)
```

This forces the AI to:
1. Recognize when data is biased toward one market
2. Actively seek picks from underrepresented markets
3. Ensure final output has market diversity

---

## Long-Term Fix Needed (Scraper Improvements):

### OddsShark Scraper Issues:
- ✅ Code DOES scrape moneyline, spread, and totals
- ⚠️ But 100% of stored data is totals
- **Likely cause**: HTML structure changed, or selectors not matching

### Recommended Actions:

1. **Debug OddsShark Scraper**:
   - Run `python tests/test_scrapers.py americanfootball_nfl`
   - Check if moneyline and spread data is being extracted
   - Update CSS selectors if HTML structure changed

2. **Add More Data Sources**:
   - Current: OddsShark (74%), OddsTrader (19%), CBS Sports (7%)
   - Consider adding: Action Network, Covers.com, ESPN

3. **Balance Data Collection**:
   - Ensure each source contributes equally
   - Don't let one source dominate (OddsShark = 74%)

4. **Add Data Validation**:
   - Alert if market distribution is >60% for any single market
   - Alert if any source provides >50% of total data

---

## Testing & Validation

### Before Fix:
```
Market Distribution:
  totals:  9 picks (90.0%)
  h2h:     1 picks (10.0%)
  spreads: 0 picks (0.0%)

Totals Breakdown:
  Over:    2 picks (22.2%)
  Under:   7 picks (77.8%)
```

### After Fix (Expected):
```
Market Distribution:
  spreads: ~3 picks (33%)
  totals:  ~3 picks (33%)
  h2h:     ~3 picks (33%)

Totals Breakdown:
  Over:    ~50%
  Under:   ~50%
```

---

## Files Modified

1. **app/ai_picks.py**
   - Added market diversity requirement to prompt
   - Added pick selection strategy with diversity enforcement

2. **tests/analyze_picks_bias.py** (NEW)
   - Analyzes exported picks for bias patterns
   - Detects market concentration and Over/Under bias

3. **tests/check_context_data.py** (NEW)
   - Analyzes scraped data in database
   - Identifies data source bias

---

## Monitoring

Run these scripts regularly to detect bias:

```bash
# Analyze picks for bias
python tests/analyze_picks_bias.py

# Check scraped data distribution
python tests/check_context_data.py
```

**Alert if**:
- Any market >60% of picks
- Any source >50% of scraped data
- Over/Under ratio >70/30

---

## Next Steps

1. ✅ Deploy prompt fix to production
2. ⏳ Test with next pick generation
3. ⏳ Debug OddsShark scraper (moneyline/spread extraction)
4. ⏳ Add data validation alerts
5. ⏳ Consider adding more data sources

---

**Status**: Prompt fix deployed, awaiting test results

