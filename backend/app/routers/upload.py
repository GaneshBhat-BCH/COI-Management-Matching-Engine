from fastapi import APIRouter, HTTPException, Depends
from app.database import get_db
from app.services.ai import analyze_document_and_answer, get_embeddings
from app.questions import QUESTIONS, QUESTIONS_DATA
from app.utils.chunking import chunk_text
from app.utils.logger import log_event
from pydantic import BaseModel
import uuid
import json

from app.services.sharepoint_sync import sync_sharepoint
from typing import Optional

router = APIRouter()

class UploadRequest(BaseModel):
    file_name: str
    pdf_text: str
    user_text: str = ""

@router.post("/upload")
async def upload_file(
    request: Optional[UploadRequest] = None,
    db = Depends(get_db)
):
    # Case 1: Trigger SharePoint Sync (No body provided)
    if not request:
        log_event("Sync Module", "Automatic SharePoint sync triggered via /api/upload", "START")
        processed_files = await sync_sharepoint()
        return {"processed_files": processed_files}

    # Case 2: Manual Upload (Existing logic)
    log_event("Upload Module", "Manual upload request received", "START")
    try:
        # 1. Insert into DB (pdf_documents)
        # Using "text-input" as placeholder for file_path since we don't save to disk
        # Capture Raw Input Body
        try:
            input_body_json = request.model_dump_json()
        except AttributeError:
             # Fallback for Pydantic v1
            input_body_json = request.json()

        query_doc = """
        INSERT INTO coi_mgmt.pdf_documents (file_name, file_path, input_body)
        VALUES (:file_name, :file_path, :input_body)
        RETURNING pdf_id
        """
        
        pdf_id = await db.fetch_val(query_doc, values={
            "file_name": request.file_name, 
            "file_path": "text-input",
            "input_body": input_body_json
        })
        log_event("Upload Module", f"Document record created (ID: {pdf_id})", "PROGRESS")
             
        # Combine PDF Text + User Input
        full_context = f"User Input:\n{request.user_text}\n\nDocument Content:\n{request.pdf_text}"
        
        # 2. Get Answers (AI)
        ai_result = await analyze_document_and_answer(full_context, QUESTIONS_DATA)
        answers_data = ai_result.get("answers", [])
        token_usage = ai_result.get("usage", {})
        
        # 3. Preparation for Processing
        answers_result = []
        texts_to_embed = []
        
        for q_def in QUESTIONS:
            ans_text = "N/A"
            for item in answers_data:
                if item.get("question_id") == q_def["id"] or item.get("question_text") == q_def["text"]:
                    ans_text = item.get("answer_text", "N/A")
                    break
            
            answers_result.append({
                "question_id": q_def["id"],
                "question_text": q_def["text"],
                "answer_text": ans_text
            })
            texts_to_embed.append(ans_text)

        # 4. Batch Embeddings for Answers
        all_embeddings = await get_embeddings(texts_to_embed)
        
        # 5. Store Answers in Relational DB
        query_ans = """
        INSERT INTO coi_mgmt.pdf_answers (pdf_id, question_id, question_text, answer_text, answer_embedding)
        VALUES (:pdf_id, :question_id, :question_text, :answer_text, :answer_embedding)
        """
        ans_values = []
        for i, item in enumerate(answers_result):
            ans_values.append({
                "pdf_id": pdf_id,
                "question_id": item["question_id"],
                "question_text": item["question_text"],
                "answer_text": item["answer_text"],
                "answer_embedding": str(all_embeddings[i])
            })
        
        if ans_values:
            # Fallback to loop to avoid potential execute_many hangs with large vectors
            for val in ans_values:
                await db.execute(query_ans, values=val)
            
        log_event("Upload Module", "AI Analysis & Answer Storage complete", "PROGRESS")
        
        # 6. RAG Vectorization (Structured Answers Only)
        chunks_to_index = []
        if request.user_text.strip():
             # Use variable chunking for potentially long user context
             user_text_chunks = chunk_text(request.user_text, target_chunk_size=1000)
             for i, c in enumerate(user_text_chunks):
                 chunks_to_index.append(f"General Context / Instructions (Part {i+1}): {c}")
             
        for item in answers_result:
            if item["answer_text"] != "N/A":
                # Variable Chunking Strategy: 
                # Each Question-Answer pair is treated as a single, semantic logical unit (one chunk).
                # This ensures the question context is never separated from the answer.
                chunks_to_index.append(f"Question: {item['question_text']}\nAnswer: {item['answer_text']}")

        # 7. Batch Embeddings for Chunks
        if chunks_to_index:
            chunk_vectors = await get_embeddings(chunks_to_index)
            
            query_chunk = """
            INSERT INTO coi_mgmt.pdf_chunks (pdf_id, chunk_text, chunk_embedding, search_vector)
            VALUES (:pdf_id, :chunk_text, :chunk_embedding, to_tsvector('english', :chunk_text))
            """
            chunk_values = []
            for i, chunk in enumerate(chunks_to_index):
                chunk_values.append({
                    "pdf_id": pdf_id,
                    "chunk_text": chunk,
                    "chunk_embedding": str(chunk_vectors[i])
                })
            
            await db.execute_many(query_chunk, values=chunk_values)
            
        log_event("Upload Module", f"Processing Complete. {len(chunks_to_index)} structured chunks indexed.", "SUCCESS")
        
        response_data = {
            "status": "success", 
            "pdf_id": str(pdf_id), 
            "extracted_text_preview": request.pdf_text[:200], 
            "answers": answers_result,
            "chunks_created": len(chunks_to_index),
            "token_usage": token_usage
        }

        # 8. Update Result Body in DB
        result_body_json = json.dumps(response_data, default=str, ensure_ascii=False)
        query_update_result = """
        UPDATE coi_mgmt.pdf_documents
        SET result_body = :result_body
        WHERE pdf_id = :pdf_id
        """
        await db.execute(query_update_result, values={"result_body": result_body_json, "pdf_id": pdf_id})

        return response_data
        
    except ValueError as ve:
        log_event("Upload Module", f"Validation Error: {str(ve)}", "ERROR")
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"Internal Server Error: {e}\n{error_trace}")
        log_event("Upload Module", f"System Error: {str(e)}", "ERROR")
        raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}")
