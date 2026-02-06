"""
Test Script for Smart Email Pattern Learning System

This script demonstrates and tests the enhanced email pattern learning features:
1. Pattern persistence (JSON file storage)
2. Confidence scoring
3. Fast-track mode (high-confidence patterns)
4. Automatic pattern learning
5. Pattern statistics tracking
"""

# Fix Unicode output on Windows
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

sys.path.append('d:/corporate-intel-saas')

from app.services.pattern_engine import PatternEngine
from app.services.email_engine import EmailPermutator

def test_pattern_basics():
    """Test basic pattern operations"""
    print("\n" + "="*60)
    print("TEST 1: Basic Pattern Operations")
    print("="*60)
    
    # Clear any existing patterns for clean test
    PatternEngine.clear_patterns()
    
    # Test pattern deduction
    email = "john.doe@example.com"
    pattern = PatternEngine.deduce_pattern(email, "John", "Doe", "example.com")
    print(f"✓ Deduced pattern from '{email}': {pattern}")
    assert pattern == "{fn}.{ln}", f"Expected '{{fn}}.{{ln}}', got '{pattern}'"
    
    # Test pattern construction
    constructed_email = PatternEngine.construct_email(pattern, "Jane", "Smith", "example.com")
    print(f"✓ Constructed email: {constructed_email}")
    assert constructed_email == "jane.smith@example.com"
    
    print("✅ Basic pattern operations passed!\n")

def test_pattern_persistence():
    """Test pattern saving and loading"""
    print("="*60)
    print("TEST 2: Pattern Persistence")
    print("="*60)
    
    # Save a pattern
    PatternEngine.save_pattern(
        domain="openai.com",
        pattern="{fn}{ln}",
        example_email="samaltman@openai.com",
        success=True
    )
    print("✓ Saved pattern for openai.com")
    
    # Retrieve it
    retrieved = PatternEngine.get_pattern("openai.com")
    print(f"✓ Retrieved pattern: {retrieved}")
    assert retrieved == "{fn}{ln}", f"Expected '{{fn}}{{ln}}', got '{retrieved}'"
    
    # Get with confidence
    data = PatternEngine.get_pattern_with_confidence("openai.com")
    print(f"✓ Pattern data: confidence={data['confidence']:.2f}, success_count={data['success_count']}")
    
    print("✅ Pattern persistence tests passed!\n")

def test_confidence_scoring():
    """Test confidence score calculation"""
    print("="*60)
    print("TEST 3: Confidence Scoring")
    print("="*60)
    
    domain = "testdomain.com"
    
    # First success
    PatternEngine.save_pattern(domain, "{fn}.{ln}", "test@testdomain.com", success=True)
    data = PatternEngine.get_pattern_with_confidence(domain)
    print(f"✓ After 1 success: confidence={data['confidence']:.2f} (expected 1.0)")
    assert data['confidence'] == 1.0
    
    # Add more successes
    for _ in range(4):
        PatternEngine.update_pattern_stats(domain, success=True)
    
    # Add one failure
    PatternEngine.update_pattern_stats(domain, success=False)
    
    data = PatternEngine.get_pattern_with_confidence(domain)
    expected_confidence = 5 / 6  # 5 successes out of 6 attempts
    print(f"✓ After 5/6 successes: confidence={data['confidence']:.2f} (expected {expected_confidence:.2f})")
    assert abs(data['confidence'] - expected_confidence) < 0.01
    
    print("✅ Confidence scoring tests passed!\n")

def test_fast_track_mode():
    """Test fast-track mode trigger"""
    print("="*60)
    print("TEST 4: Fast-Track Mode")
    print("="*60)
    
    # Setup: Create a high-confidence pattern
    high_conf_domain = "google.com"
    PatternEngine.save_pattern(high_conf_domain, "{fn}{ln}", "johnsmith@google.com", success=True)
    
    # Simulate 9 more successes (10 total, 100% success rate)
    for _ in range(9):
        PatternEngine.update_pattern_stats(high_conf_domain, success=True)
    
    # Test fast-track check
    should_fast_track = PatternEngine.should_use_fast_track(high_conf_domain)
    print(f"✓ High-confidence domain (100%): should_use_fast_track = {should_fast_track}")
    assert should_fast_track == True
    
    # Test email generation (should return only 1 email)
    permutator = EmailPermutator()
    candidates = permutator.generate("Jane Doe", high_conf_domain)
    print(f"✓ Generated {len(candidates)} candidates (expected 1 for fast-track)")
    assert len(candidates) == 1, f"Fast-track should generate 1 email, got {len(candidates)}"
    print(f"✓ Fast-track email: {candidates[0]}")
    assert candidates[0] == "janedoe@google.com"
    
    # Setup: Create a low-confidence pattern
    low_conf_domain = "lowconf.com"
    PatternEngine.save_pattern(low_conf_domain, "{fn}.{ln}", "test@lowconf.com", success=True)
    PatternEngine.update_pattern_stats(low_conf_domain, success=False) # 1/2 = 50%
    
    # Test that low confidence doesn't trigger fast-track
    should_fast_track = PatternEngine.should_use_fast_track(low_conf_domain)
    print(f"✓ Low-confidence domain (50%): should_use_fast_track = {should_fast_track}")
    assert should_fast_track == False
    
    # Should generate multiple candidates
    candidates = permutator.generate("Test User", low_conf_domain)
    print(f"✓ Generated {len(candidates)} candidates (expected >1 for standard mode)")
    assert len(candidates) > 1
    
    print("✅ Fast-track mode tests passed!\n")

def test_pattern_priority():
    """Test that known patterns are prioritized"""
    print("="*60)
    print("TEST 5: Pattern Priority")
    print("="*60)
    
    domain = "priority-test.com"
    
    # Save a known pattern (but with low confidence to avoid fast-track)
    PatternEngine.save_pattern(domain, "{fi}{ln}", "jdoe@priority-test.com", success=True)
    PatternEngine.update_pattern_stats(domain, success=False)  # Lower confidence to 50%
    
    # Generate candidates
    permutator = EmailPermutator()
    candidates = permutator.generate("John Doe", domain)
    
    print(f"✓ Generated {len(candidates)} candidates")
    print(f"✓ First candidate: {candidates[0]} (should match known pattern)")
    
    # First candidate should match the known pattern
    assert candidates[0] == "jdoe@priority-test.com", "Known pattern should be first in list"
    
    print("✅ Pattern priority tests passed!\n")

def view_all_patterns():
    """Display all learned patterns"""
    print("="*60)
    print("SUMMARY: All Learned Patterns")
    print("="*60)
    
    all_patterns = PatternEngine.get_all_patterns()
    
    if not all_patterns:
        print("No patterns learned yet.")
    else:
        print(f"Total domains: {len(all_patterns)}\n")
        for domain, data in sorted(all_patterns.items()):
            print(f"Domain: {domain}")
            print(f"  Pattern: {data['pattern']}")
            print(f"  Confidence: {data['confidence']:.1%}")
            print(f"  Success Rate: {data['success_count']}/{data['total_attempts']}")
            if 'example_email' in data:
                print(f"  Example: {data['example_email']}")
            print()

def run_all_tests():
    """Run all test functions"""
    try:
        test_pattern_basics()
        test_pattern_persistence()
        test_confidence_scoring()
        test_fast_track_mode()
        test_pattern_priority()
        view_all_patterns()
        
        print("="*60)
        print("🎉 ALL TESTS PASSED!")
        print("="*60)
        print("\nKey Features Verified:")
        print("✓ Pattern deduction and construction")
        print("✓ JSON file persistence (data/email_patterns.json)")  
        print("✓ Confidence scoring (success/total ratio)")
        print("✓ Fast-track mode (>75% confidence → 1 email)")
        print("✓ Pattern priority (known patterns first)")
        print("\nNext: Test with real email validation to see learning in action!")
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        return False
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
