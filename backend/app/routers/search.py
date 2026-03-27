from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends
from app.database import get_db
from app.services.ai import get_embeddings, is_semantic_equivalent_batch
from app.utils.logger import log_event
from app.utils.html_templates import generate_search_results_html
from app.questions import QUESTIONS
from pydantic import BaseModel
import json

router = APIRouter()

# Precompute Question Text to ID Mapping
QUESTION_TEXT_TO_ID = { q["text"].lower().strip(): str(q["id"]) for q in QUESTIONS }

class SearchItem(BaseModel):
    question: str
    answer: str
    question_id: Optional[str] = None

class SearchRequest(BaseModel):
    user_id: str
    questions_answers: list[SearchItem]

@router.post("/search")
async def search_documents(request: SearchRequest, db = Depends(get_db)):
    log_event("Search Module", "Search request received", "START")
    try:

        # 1. Prepare Query
        # Combine Q&A into text for Embedding AND Keyword search
        # 1. Collect Query Vectors and Metadata
        query_text = ""
        for item in request.questions_answers:
             q = item.question
             a = item.answer
             q_id = item.question_id
             
             if not q_id:
                 q_id = QUESTION_TEXT_TO_ID.get(q.lower().strip())
             
             if not q_id:
                  print(f"Warning: Question text not recognized for fallback ID: {q[:50]}...")
                  continue
             
             # NEW Logic: Skip NA/Blank in query text to improve retrieval focus
             if a.upper().strip() in ["NA", "N/A", ""] or not a.strip():
                 continue
                 
             query_text += f" {q} {a} " # Space separated for keywords
             
        if not query_text.strip():
            log_event("Search Module", "Empty search query", "WARNING")
            raise HTTPException(status_code=400, detail="Empty search query")


        # Weighted Scoring Configuration
        HIGH_WEIGHT_IDS = {"1", "2", "13", "14", "15"}
        HIGH_WEIGHT_VAL = 3.0
        NORMAL_WEIGHT_VAL = 1.0
        THRESHOLD_PERCENT = 0.80  # 80% match requirement

        # Helper: Process a list of DB rows into Verified Forensic Candidates
        async def get_verified_candidates(rows, source_label="Unknown"):
            if not rows: return []
            processed_candidates = []
            semantic_candidates = []
            
            # --- PASS 1: Rule-Based Matching ---
            for row_idx, row in enumerate(rows):
                pdf_id = row["pdf_id"]
                query_answers = "SELECT question_id, question_text, answer_text FROM coi_mgmt.pdf_answers WHERE pdf_id = :pdf_id"
                stored_answers = await db.fetch_all(query_answers, values={"pdf_id": pdf_id})
                
                stored_map = { str(rec["question_id"]): rec["answer_text"] for rec in stored_answers }
                stored_map_text = { (rec["question_text"] or "").lower().strip(): rec["answer_text"] for rec in stored_answers }
                
                matches = []
                non_matches = []
                total_possible_weight = 0.0
                current_weighted_score = 0.0
                
                for item in request.questions_answers:
                    q_text = item.question or "Unknown Question"
                    q_id = str(item.question_id or "")
                    if not q_id or q_id == "None":
                         q_id = QUESTION_TEXT_TO_ID.get(q_text.lower().strip(), "")
                    
                    user_ref = item.answer or ""
                    if user_ref.upper().strip() in ["NA", "N/A", ""] or not user_ref.strip():
                        continue

                    weight = HIGH_WEIGHT_VAL if q_id in HIGH_WEIGHT_IDS else NORMAL_WEIGHT_VAL
                    total_possible_weight += weight
                    
                    found_answer = stored_map.get(q_id) or stored_map_text.get(q_text.lower().strip())
                    
                    if found_answer and found_answer.upper().strip() not in ["N/A", "NA", ""]:
                        # 1. Normalize
                        def normalize_for_match(text):
                            import re
                            text = text.lower()
                            return re.sub(r'[^a-zA-Z0-9]', '', text) 

                        norm_user = normalize_for_match(user_ref)
                        norm_pdf = normalize_for_match(found_answer)
                        score_mult = 0.0
                        status_msg = "Mismatch"

                        # 2. Tiered Rules
                        if norm_user == norm_pdf:
                            score_mult = 1.0
                            status_msg = "Match (Exact)"
                        else:
                            from difflib import SequenceMatcher
                            similarity = SequenceMatcher(None, norm_user, norm_pdf).ratio()
                            if similarity >= 0.95:
                                score_mult = 1.0
                                status_msg = f"Match (Fuzzy {similarity:.0%})"
                            else:
                                import re
                                user_tokens = set(re.split(r'[^a-zA-Z0-9]+', user_ref.lower()))
                                pdf_tokens = set(re.split(r'[^a-zA-Z0-9]+', found_answer.lower()))
                                user_tokens = {t for t in user_tokens if t if len(t) > 2}
                                pdf_tokens = {t for t in pdf_tokens if t if len(t) > 2}
                                common = user_tokens.intersection(pdf_tokens)
                                if common:
                                    score_mult = 0.8
                                    status_msg = f"Partial Match (Overlap: {len(common)} tokens)"
                                else:
                                    # Flag for Pass 2 (Semantic)
                                    semantic_candidates.append({
                                        "cand_idx": row_idx,
                                        "match_idx": len(matches),
                                        "user_val": user_ref,
                                        "pdf_val": found_answer
                                    })

                        matches.append({
                            "question": q_text, 
                            "pdf_answer": found_answer, 
                            "user_answer_ref": user_ref, 
                            "match_type": status_msg,
                            "weight": weight,
                            "score_earned": (weight * score_mult)
                        })
                        current_weighted_score += (weight * score_mult)
                    else:
                        non_matches.append({
                            "question": q_text, 
                            "pdf_answer": "NA", 
                            "user_answer_ref": user_ref,
                            "match_type": "Mismatch",
                            "weight": weight,
                            "score_earned": 0.0
                        })

                processed_candidates.append({
                    "pdf_name": row["file_name"],
                    "pdf_id": str(pdf_id),
                    "match_score_raw": 0.0,
                    "weighted_score": current_weighted_score,
                    "total_possible": total_possible_weight,
                    "matched_qa": matches,
                    "unmatched_qa": non_matches,
                    "relevance_details": {"vector": float(row["max_sim"]), "keyword_rank": float(row["max_rank"])},
                    "source_label": source_label 
                })

            # --- PASS 2: Batch Semantic AI Bridge ---
            if semantic_candidates:
                log_event("Search Module", f"Batching {len(semantic_candidates)} semantic checks...", "PROGRESS")
                pairs = [(c["user_val"], c["pdf_val"]) for c in semantic_candidates]
                batch_results = await is_semantic_equivalent_batch(pairs)
                for i, is_match in enumerate(batch_results):
                    if is_match:
                        info = semantic_candidates[i]
                        cand = processed_candidates[info["cand_idx"]]
                        match_item = cand["matched_qa"][info["match_idx"]]
                        match_item["match_type"] = "Match (Semantic AI)"
                        match_item["score_earned"] = match_item["weight"]
                        cand["weighted_score"] += match_item["weight"]

            # --- PASS 3: Final Filtering & Scoring ---
            verified = []
            for cand in processed_candidates:
                score = (cand["weighted_score"] / cand["total_possible"] * 100) if cand["total_possible"] > 0 else 0
                cand["match_score_raw"] = round(score, 1)
                
                # Split matched_qa into actual matches vs confirmed mismatches
                final_matches = [m for m in cand["matched_qa"] if m["score_earned"] > 0]
                final_mismatches = [m for m in cand["matched_qa"] if m["score_earned"] == 0]
                final_mismatches.extend(cand["unmatched_qa"])
                
                cand["matched_qa"] = final_matches
                cand["unmatched_qa"] = final_mismatches
                
                if cand["match_score_raw"] >= THRESHOLD_PERCENT * 100:
                    cand["match_score"] = f"{cand['match_score_raw']}%"
                    cand["weightage_details"] = f"Score: {cand['weighted_score']}/{cand['total_possible']}"
                    verified.append(cand)

            verified.sort(key=lambda x: x["match_score_raw"], reverse=True)
            return verified

        # 2. STEP 1: DEEP KEYWORD SEARCH
        log_event("Search Module", "Attempting Deep Keyword search...", "PROGRESS")
        
        # Check for AI-preferred questions (2, 4, 14) to force vector search later
        AI_DYNAMIC_IDS = {"2", "4", "14"}
        has_dynamic_q = any(
            str(item.question_id or "") in AI_DYNAMIC_IDS 
            for item in request.questions_answers 
            if (item.answer or "").upper().strip() not in ["NA", "N/A", ""]
        )

        # Construct OR-based TSQuery (match ANY term) to avoid strict AND failure
        import re
        tokens = re.findall(r'\w+', query_text)
        query_or = " | ".join(tokens) if tokens else query_text
        query_regex = "|".join(tokens) if tokens else query_text

        keyword_search_query = """
        WITH kw_candidates AS (
            -- Search in chunks
            SELECT pdf_id, MAX(ts_rank(search_vector, to_tsquery('english', :query_or))) as rank
            FROM coi_mgmt.pdf_chunks
            WHERE search_vector @@ to_tsquery('english', :query_or)
            GROUP BY pdf_id
            UNION
            -- Search in extracted answers (using regex for broad matching)
            SELECT pdf_id, 1.0 as rank
            FROM coi_mgmt.pdf_answers
            WHERE answer_text ~* :query_regex
            GROUP BY pdf_id
        )
        SELECT pdf.file_name, c.pdf_id, 0 as max_sim, MAX(c.rank) as max_rank
        FROM kw_candidates c
        JOIN coi_mgmt.pdf_documents pdf ON c.pdf_id = pdf.pdf_id
        GROUP BY pdf.file_name, c.pdf_id
        ORDER BY max_rank DESC LIMIT 200
        """
        try:
            results_kw = await db.fetch_all(keyword_search_query, values={"query_or": query_or, "query_regex": query_regex})
        except Exception as sql_err:
             # Fallback to plainto_tsquery if OR syntax fails (rare)
             log_event("Search Module", f"Deep query failed ({sql_err}), falling back to standard...", "WARNING")
             query_std = """
             SELECT pdf.file_name, pdf.pdf_id, 0 as max_sim, MAX(ts_rank(c.search_vector, plainto_tsquery('english', :query_text))) as max_rank
             FROM coi_mgmt.pdf_chunks c
             JOIN coi_mgmt.pdf_documents pdf ON c.pdf_id = pdf.pdf_id
             WHERE c.search_vector @@ plainto_tsquery('english', :query_text)
             GROUP BY pdf.file_name, pdf.pdf_id
             ORDER BY max_rank DESC LIMIT 200
             """
             results_kw = await db.fetch_all(query_std, values={"query_text": query_text})

        log_event("Search Module", f"Step 1 Raw Results: Found {len(results_kw)} rows via SQL.", "DEBUG")
        candidates = await get_verified_candidates(results_kw, source_label="Deep Keyword")
        search_method = "Keyword (BM25)"

        # 3. STEP 2: FALLBACK VECTOR SEARCH 
        # (Only if fewer than 3 verified PDFs OR if high-impact dynamic questions are used)
        if len(candidates) < 3 or has_dynamic_q:
            if has_dynamic_q:
                log_event("Search Module", "High-impact questions detected (2, 4, 14). Forcing AI Vector Search for semantic accuracy.", "PROGRESS")
            else:
                log_event("Search Module", f"Found only {len(candidates)} high-confidence matches via keywords. Triggering Vector Fallback...", "PROGRESS")
            
            search_method = "Hybrid (Deep Keyword + Vector)"
            query_embedding = await get_embeddings(query_text)
            embedding_str = str(query_embedding)
            
            search_query_vec = """
                SELECT pdf.file_name, pdf.pdf_id, 1 - (c.chunk_embedding <=> :embedding) as max_sim, 0 as max_rank
                FROM coi_mgmt.pdf_chunks c
                JOIN coi_mgmt.pdf_documents pdf ON c.pdf_id = pdf.pdf_id
                WHERE 1 - (c.chunk_embedding <=> :embedding) > 0.5
                ORDER BY max_sim DESC LIMIT 100
            """
            results_vec = await db.fetch_all(search_query_vec, values={"embedding": embedding_str})
            
            # Identify which PDFs we already found via keyword to avoid redundant verification
            existing_pdf_ids = {str(c["pdf_id"]) for c in candidates}
            
            # Filter results_vec to only new PDFs
            new_results_vec = [r for r in results_vec if str(r["pdf_id"]) not in existing_pdf_ids]
            
            if new_results_vec:
                log_event("Search Module", f"Vector search found {len(new_results_vec)} NEW raw candidates.", "PROGRESS")
                vector_candidates = await get_verified_candidates(new_results_vec, source_label="Vector Search")
                candidates.extend(vector_candidates)
            
            log_event("Search Module", f"Verification complete. Final combined count: {len(candidates)} unique PDFs.", "SUCCESS")
        else:
            log_event("Search Module", f"Keyword search found {len(candidates)} verified PDFs. Skipping Vectorization.", "SUCCESS")
        
        # Sort combined results again to ensure Vector matches can beat Keyword matches if score is higher
        candidates.sort(key=lambda x: x["match_score_raw"], reverse=True)

        final_results = candidates[:3]
        formatted_results = []
        for c in final_results:
             formatted_results.append({
                "pdf_name": c["pdf_name"],
                "weightage_details": c.get("weightage_details", ""),
                "match_score": c.get("match_score", "0%"),
                "search_method": c.get("source_label", search_method),
                "relevance_details": c.get("relevance_details", {}),
                "matched_qa": c["matched_qa"],
                "unmatched_qa": c["unmatched_qa"]
             })
        
        # 4. FEEDBACK: Ensure we return exactly top 3 (or placeholders)
        current_count = len(formatted_results)
        if current_count < 3:
            for i in range(current_count + 1, 4): # e.g. if count 1, range(2,4) -> 2, 3
                formatted_results.append({
                    "pdf_name": "No Data Found",
                    "match_score": "0%",
                    "search_method": search_method,
                    "relevance_details": {},
                    "matched_qa": [],
                    "unmatched_qa": [],
                     "feedback_message": f"We don't have PDF {i} data currently matched with the criteria."
                })
        
        # 5. LOGGING: Persist FULL search session
        try:
            # Collect search methods per PDF
            query_type_map = { res["pdf_name"]: res.get("search_method", "Unknown") for res in formatted_results }
            
            insert_query = """
                INSERT INTO coi_mgmt.user_queries (user_id, input_json, agent_answer, query_type)
                VALUES (:user_id, :input_json, :agent_answer, :query_type)
            """
            await db.execute(insert_query, values={
                "user_id": request.user_id,
                "input_json": json.dumps(request.questions_answers),       # Store raw input list
                "agent_answer": json.dumps(formatted_results),             # Store final output list
                "query_type": json.dumps(query_type_map)                   # Store method map
            })
            log_event("Search Module", f"Logged search session for user {request.user_id}", "INFO")
        except Exception as log_err:
            log_event("Search Module", f"Failed to log session: {log_err}", "WARNING")

        # Generate HTML Email Body
        email_html = generate_search_results_html(formatted_results, search_method)

        return {
            "search_method_used": search_method,
            "results": formatted_results,
            "email_body": email_html
        }

    except ValueError as ve:
        log_event("Search Module", f"Query Error: {str(ve)}", "ERROR")
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"Internal Search Error: {e}\n{error_trace}")
        log_event("Search Module", f"System Error: {str(e)}", "ERROR")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")
