import asyncio
import os
import sys
import json

# Add current directory to path
sys.path.append(os.getcwd())

from app.services.ai import analyze_document_and_answer
from app.questions import QUESTIONS_DATA

async def test_extraction():
    print("--- TESTING AI EXTRACTION REFINEMENT (v2) ---")
    
    # Text from user's example
    pdf_text = """
    CONFIDENTIAL MEMORANDUM
    TO: Conflict of Interest Committee
    FROM: Suneet Agarwal, MD, PhD
    RE: Conflict of Interest Management Plan for Rejuveron Telomere Sciences
    DATE: May 10, 2021
    I am the Co-Program Leader for the Stem Cell Transplant Center at Boston Children’s Hospital ("Children’s” or “BCH”). 
    I also hold a Harvard Medical School (“HMS”) appointment as an Associate Professor of Pediatrics. 
    I am the Co-founder and hold equity in the company.
    
    Q: Has the company licensed or is it planning to license intellectual property from BCH? 
    A: Yes.
    
    Q: Is the researcher an inventor of the technology?
    A: Yes, I am an inventor of the licensed IP.
    """
    
    # We call the service
    # Note: We simulate a state where Q7 is already "Yes" in the context
    result = await analyze_document_and_answer(pdf_text, QUESTIONS_DATA)
    
    answers = result.get("answers", [])
    print("\nEXTRACTION RESULTS:")
    q13_ans = "NOT FOUND"
    q14_ans = "NOT FOUND"
    
    for a in answers:
        if a["question_id"] == 13:
            q13_ans = a["answer_text"]
        if a["question_id"] == 14:
            q14_ans = a["answer_text"]
            
    print(f"Question 13 (Policy): {q13_ans}")
    print(f"Question 14 (Rule): {q14_ans}")
    
    # Validation
    if q13_ans == "Inventor_Equity_and_Licensing_Conflict_Policy" and \
       q14_ans == "Inventor Equity and Licensing Conflict Policy Rule":
        print("\n✅ SUCCESS: Question 13 and 14 correctly prioritized Inventor role.")
    else:
        print("\n❌ FAILED: Unexpected results.")

if __name__ == "__main__":
    asyncio.run(test_extraction())
