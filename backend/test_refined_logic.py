import sys
from pathlib import Path

# Mocking the constants and dependencies to test the logic in isolation
HIGH_WEIGHT_IDS = {"1", "13", "14", "15"}
HIGH_WEIGHT_VAL = 3.0
NORMAL_WEIGHT_VAL = 1.0

def calculate_score(user_queries):
    total_possible_weight = 0.0
    current_weighted_score = 0.0
    
    for item in user_queries:
        q_id = str(item.get("question_id", ""))
        user_ref = item.get("answer_text", "")
        
        # Logic to test:
        if user_ref.upper().strip() in ["NA", "N/A", ""] or not user_ref.strip():
            continue
            
        weight = HIGH_WEIGHT_VAL if q_id in HIGH_WEIGHT_IDS else NORMAL_WEIGHT_VAL
        total_possible_weight += weight
        
        # Simulate a match for everything else for scoring demo
        current_weighted_score += weight
        
    return current_weighted_score, total_possible_weight

def test_logic():
    # Case 1: Standard query (no NA)
    # Total weight: Q1(3) + Q2(1) + Q3(1) = 5.0
    case1 = [
        {"question_id": "1", "answer_text": "Yes"},
        {"question_id": "2", "answer_text": "Founder"},
        {"question_id": "3", "answer_text": "Private"}
    ]
    score, total = calculate_score(case1)
    print(f"Case 1 (No NA): Score {score}/{total} (Expected 5/5)")
    assert total == 5.0

    # Case 2: One NA query (Q2 is NA)
    # Total weight: Q1(3) + Q3(1) = 4.0 (Q2 ignored)
    case2 = [
        {"question_id": "1", "answer_text": "Yes"},
        {"question_id": "2", "answer_text": "NA"},
        {"question_id": "3", "answer_text": "Private"}
    ]
    score, total = calculate_score(case2)
    print(f"Case 2 (One NA): Score {score}/{total} (Expected 4/4)")
    assert total == 4.0

    # Case 3: One Blank query (Q3 is Blank)
    # Total weight: Q1(3) + Q2(1) = 4.0 (Q3 ignored)
    case3 = [
        {"question_id": "1", "answer_text": "Yes"},
        {"question_id": "2", "answer_text": "Founder"},
        {"question_id": "3", "answer_text": "  "}
    ]
    score, total = calculate_score(case3)
    print(f"Case 3 (Blank): Score {score}/{total} (Expected 4/4)")
    assert total == 4.0

    # Case 4: High weight question is NA (Q1 is NA)
    # Total weight: Q2(1) + Q3(1) = 2.0 (Q1 ignored)
    case4 = [
        {"question_id": "1", "answer_text": "N/A"},
        {"question_id": "2", "answer_text": "Founder"},
        {"question_id": "3", "answer_text": "Private"}
    ]
    score, total = calculate_score(case4)
    print(f"Case 4 (High weight NA): Score {score}/{total} (Expected 2/2)")
    assert total == 2.0

    print("\nLogic Verification PASSED.")

if __name__ == "__main__":
    test_logic()
    
    # Test Retrieval Text Logic
    def test_retrieval_text():
        user_queries = [
            {"question_text": "Q1", "answer_text": "Yes"},
            {"question_text": "Q2", "answer_text": "NA"},
            {"question_text": "Q3", "answer_text": "Company"}
        ]
        query_text = ""
        for item in user_queries:
            q = item.get("question_text")
            a = item.get("answer_text")
            if a.upper().strip() in ["NA", "N/A", ""] or not a.strip():
                continue
            query_text += f" {q} {a} "
        
        print(f"Query Text: '{query_text.strip()}'")
        assert "Q2" not in query_text
        assert "NA" not in query_text
        assert "Q1 Yes" in query_text
        print("Retrieval Text Logic Verification PASSED.")

    test_retrieval_text()
