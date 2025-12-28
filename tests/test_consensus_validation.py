#!/usr/bin/env python3
"""
Test script to verify the consensus direction validation works correctly.
"""

def test_validate_pick_against_consensus():
    """Test the validation function with various scenarios."""
    
    # Mock validation function (simplified version)
    def validate_pick_against_consensus(pick, context_payload):
        """
        Validates that the AI's pick matches the consensus direction.
        Returns (is_valid, reason) tuple.
        """
        game = pick.get('game', '')
        market = pick.get('market', '').lower()
        pick_value = pick.get('pick', '').lower()
        
        # Find this game in the context
        games = context_payload.get('games', [])
        game_context = None
        for g in games:
            if g.get('game_id', '') == game:
                game_context = g
                break
        
        if not game_context:
            return (True, "No context found")
        
        # Get expert consensus for this game
        expert_consensus = game_context.get('context', {}).get('expert_consensus', [])
        
        if not expert_consensus:
            return (True, "No consensus data")
        
        # For totals, check if consensus direction matches pick direction
        if market == 'totals':
            consensus_directions = []
            for expert in expert_consensus:
                if isinstance(expert, dict):
                    direction = expert.get('direction', '').lower()
                    if not direction and 'pick' in expert:
                        pick_text = expert.get('pick', '').lower()
                        if 'over' in pick_text:
                            direction = 'over'
                        elif 'under' in pick_text:
                            direction = 'under'
                    
                    if direction in ['over', 'under']:
                        consensus_directions.append(direction)
            
            if consensus_directions:
                over_count = consensus_directions.count('over')
                under_count = consensus_directions.count('under')
                
                if over_count > under_count:
                    consensus_dir = 'over'
                elif under_count > over_count:
                    consensus_dir = 'under'
                else:
                    return (True, "Consensus is split")
                
                if pick_value != consensus_dir:
                    return (False, f"Pick is {pick_value} but consensus is {consensus_dir} ({over_count} over, {under_count} under)")
        
        return (True, "Validated")
    
    # Test Case 1: Memphis/Wizards - Should REJECT Over when consensus is Under
    print("=" * 80)
    print("TEST CASE 1: Memphis Grizzlies @ Washington Wizards")
    print("=" * 80)
    
    pick1 = {
        'game': 'Memphis Grizzlies @ Washington Wizards',
        'market': 'totals',
        'pick': 'Over',
        'line': 239.5
    }
    
    context1 = {
        'games': [{
            'game_id': 'Memphis Grizzlies @ Washington Wizards',
            'context': {
                'expert_consensus': [
                    {'source': 'oddsshark', 'direction': 'under', 'line': '240.5'},
                    {'source': 'oddstrader', 'direction': 'under', 'line': '240.5'},
                    {'source': 'cbs_sports', 'direction': 'under', 'line': '240.5'}
                ]
            }
        }]
    }
    
    is_valid, reason = validate_pick_against_consensus(pick1, context1)
    print(f"Pick: {pick1['pick']} {pick1['line']}")
    print(f"Consensus: 3 sources say Under 240.5")
    print(f"Result: {'✅ VALID' if is_valid else '❌ REJECTED'}")
    print(f"Reason: {reason}")
    assert not is_valid, "Should reject Over when consensus is Under"
    print("✅ Test passed!\n")
    
    # Test Case 2: Same game but picking Under - Should ACCEPT
    print("=" * 80)
    print("TEST CASE 2: Memphis Grizzlies @ Washington Wizards (Corrected)")
    print("=" * 80)
    
    pick2 = {
        'game': 'Memphis Grizzlies @ Washington Wizards',
        'market': 'totals',
        'pick': 'Under',
        'line': 239.5
    }
    
    is_valid, reason = validate_pick_against_consensus(pick2, context1)
    print(f"Pick: {pick2['pick']} {pick2['line']}")
    print(f"Consensus: 3 sources say Under 240.5")
    print(f"Result: {'✅ VALID' if is_valid else '❌ REJECTED'}")
    print(f"Reason: {reason}")
    assert is_valid, "Should accept Under when consensus is Under"
    print("✅ Test passed!\n")
    
    # Test Case 3: Split consensus - Should ACCEPT either direction
    print("=" * 80)
    print("TEST CASE 3: Split Consensus (2 Over, 2 Under)")
    print("=" * 80)
    
    pick3 = {
        'game': 'Lakers @ Celtics',
        'market': 'totals',
        'pick': 'Over',
        'line': 220.5
    }
    
    context3 = {
        'games': [{
            'game_id': 'Lakers @ Celtics',
            'context': {
                'expert_consensus': [
                    {'source': 'oddsshark', 'direction': 'over', 'line': '221'},
                    {'source': 'oddstrader', 'direction': 'under', 'line': '221'},
                    {'source': 'cbs_sports', 'direction': 'over', 'line': '220.5'},
                    {'source': 'another', 'direction': 'under', 'line': '220.5'}
                ]
            }
        }]
    }
    
    is_valid, reason = validate_pick_against_consensus(pick3, context3)
    print(f"Pick: {pick3['pick']} {pick3['line']}")
    print(f"Consensus: 2 Over, 2 Under (split)")
    print(f"Result: {'✅ VALID' if is_valid else '❌ REJECTED'}")
    print(f"Reason: {reason}")
    assert is_valid, "Should accept either direction when consensus is split"
    print("✅ Test passed!\n")
    
    print("=" * 80)
    print("ALL TESTS PASSED! ✅")
    print("=" * 80)

if __name__ == "__main__":
    test_validate_pick_against_consensus()

