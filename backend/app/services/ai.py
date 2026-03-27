from openai import AsyncAzureOpenAI
import json
from app.config import (
    AZURE_OPENAI_API_KEY,
    AZURE_OPENAI_ENDPOINT,
    GPT_DEPLOYMENT,
    EMBEDDING_DEPLOYMENT,
    API_VERSION
)
from app.utils.logger import log_event

# Handle potential full URL in env var
if AZURE_OPENAI_ENDPOINT and "/openai" in AZURE_OPENAI_ENDPOINT:
    AOAI_ENDPOINT = AZURE_OPENAI_ENDPOINT.split("/openai")[0]
else:
    AOAI_ENDPOINT = AZURE_OPENAI_ENDPOINT

client = AsyncAzureOpenAI(
    azure_endpoint=AOAI_ENDPOINT,
    api_key=AZURE_OPENAI_API_KEY,
    api_version=API_VERSION
)

async def get_embeddings(input_data: str | list[str]):
    """
    Fetches embeddings for a single string or a list of strings.
    Uses OpenAI batch API for performance when a list is provided.
    """
    if not input_data:
        return []

    # Ensure input is a list for the API call
    is_single = isinstance(input_data, str)
    api_input = [input_data] if is_single else input_data

    response = await client.embeddings.create(
        input=api_input,
        model=EMBEDDING_DEPLOYMENT,
        dimensions=1536
    )
    
    if is_single:
        return response.data[0].embedding
    else:
        return [item.embedding for item in response.data]

from app.utils.masking import mask_text

async def ocr_document_visual(base64_images: list[str]) -> str:
    """
    Performs raw OCR of a document by processing each page individually.
    Splitting into single pages drastically reduces 'jailbreak' filter triggers
    on complex legal/medical documents.
    """
    log_event("AI Service", f"Starting sequential OCR for {len(base64_images)} pages", "START")
    
    all_extracted_text = []
    # Limit to 10 pages for cost/performance, or use all if needed
    pages_to_process = base64_images[:10] 
    
    for i, b64 in enumerate(pages_to_process):
        log_event("AI Service", f"OCRing Page {i+1}/{len(pages_to_process)}", "PROGRESS")
        
        try:
            response = await client.chat.completions.create(
                model=GPT_DEPLOYMENT,
                messages=[
                    {"role": "system", "content": "You are a neutral transcription assistant. Your only task is to provide a literal transcription of the text in the image."},
                    {"role": "user", "content": [
                        {"type": "text", "text": "Transcribe the text from this document page exactly as written."},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}", "detail": "auto"}}
                    ]}
                ]
            )
            
            page_text = response.choices[0].message.content
            if page_text:
                all_extracted_text.append(f"--- PAGE {i+1} ---\n{page_text}")
        except Exception as e:
            # If one page fails due to filtering, we log it and keep the others
            error_msg = str(e)
            print(f"DEBUG: OCR Page {i+1} Exception: {error_msg}")
            if "content_filter" in error_msg or "400" in error_msg:
                log_event("AI Service", f"Page {i+1} was filtered by Azure Safety. Skipping...", "WARNING")
            else:
                log_event("AI Service", f"Page {i+1} OCR Error: {error_msg}", "ERROR")
    
    if not all_extracted_text:
        log_event("AI Service", "OCR failed for ALL pages", "ERROR")
        return ""
        
    combined_text = "\n\n".join(all_extracted_text)
    log_event("AI Service", f"OCR complete. Combined {len(all_extracted_text)} pages.", "SUCCESS")
    return combined_text

async def analyze_document_visual(base64_images: list[str], questions_config: dict | list) -> dict:
    """
    Performs multimodal analysis of a document using images of its pages.
    """
    log_event("AI Service", f"Constructing visual prompt for {len(base64_images)} pages", "START")
    
    # Handle config (same as text-based)
    if isinstance(questions_config, dict) and "QUESTIONS_DATA" in questions_config:
        root_data = questions_config["QUESTIONS_DATA"]
        questions_list = root_data.get("QUESTIONS", [])
        global_instr = root_data.get("global_instructions", {})
        ref_policies = root_data.get("REFERENCE_POLICIES", {})
        system_role = questions_config.get("role", "You are a forensic document auditor.")
    elif isinstance(questions_config, list):
        questions_list = questions_config
        global_instr = {}
        ref_policies = {}
        system_role = "You are a forensic document auditor."
    else:
        questions_list = questions_config.get("QUESTIONS", [])
        global_instr = questions_config.get("global_instructions", {})
        ref_policies = questions_config.get("REFERENCE_POLICIES", questions_config)
        system_role = "You are a forensic document auditor."

    # Construct the user message with images
    content = [
        {
            "type": "text",
            "text": f"""
            {system_role}
            Your goal is to extract specific details from the images of the document pages provided.
            Analyze EVERY page carefully. The document is a Conflict of Interest (COI) Management Plan.
            
            YOUR TASK:
            Answer the following questions based on the document content in the images.
            Do NOT return 'NA' unless you have searched all 15 pages and the information is truly not there.
            If the text is blurry, do your best to squint and infer the correct value.
            
            GLOBAL INSTRUCTIONS:
            {json.dumps(global_instr, indent=2)}

            REFERENCE POLICIES:
            {json.dumps(ref_policies, indent=2)}

            QUESTIONS AND EXTRACTION PROMPTS:
            {json.dumps(questions_list, indent=2)}

            OUTPUT FORMAT (JSON):
            {{
                "answers": [
                    {{ "question_id": <int>, "question_text": "<str>", "answer_text": "<extracted detail or inference>" }},
                    ...
                ]
            }}
            """
        }
    ]
    
    # Add images (limit to 8 pages for best performance)
    for b64 in base64_images[:8]: 
        content.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:image/png;base64,{b64}",
                "detail": "auto" # Auto detail for faster processing
            }
        })
    
    log_event("AI Service", "Visual Analysis request sending to GPT-5", "PENDING")
    
    try:
        response = await client.chat.completions.create(
            model=GPT_DEPLOYMENT,
            messages=[
                {"role": "system", "content": system_role},
                {"role": "user", "content": content}
            ],
            response_format={"type": "json_object"}
        )
        
        resp_content = response.choices[0].message.content
        usage = response.usage
        
        log_event("AI Service", f"Visual Response received. Usage: {usage.total_tokens}", "SUCCESS")
             
        data = json.loads(resp_content)
        return {
            "answers": data.get("answers", []),
            "usage": {
                "prompt_tokens": usage.prompt_tokens,
                "completion_tokens": usage.completion_tokens,
                "total_tokens": usage.total_tokens
            }
        }
    except Exception as e:
        log_event("AI Service", f"Visual Analysis failed: {str(e)}", "ERROR")
        print(f"AI VISUAL ERROR: {e}")
        return {"answers": [], "usage": {}}

async def analyze_document_and_answer(text_content: str, questions_config: dict | list) -> dict:
    log_event("AI Service", "masking document content", "START")
    masked_text = mask_text(text_content)
    
    log_event("AI Service", "constructing prompt", "PROGRESS")
    
    # Handle backward compatibility or list input
    # Handle new nested structure (QUESTIONS_DATA top level)
    if isinstance(questions_config, dict) and "QUESTIONS_DATA" in questions_config:
        # New Structure
        root_data = questions_config["QUESTIONS_DATA"]
        questions_list = root_data.get("QUESTIONS", [])
        global_instr = root_data.get("global_instructions", {})
        ref_policies = root_data.get("REFERENCE_POLICIES", {})
        system_role = questions_config.get("role", "You are a forensic document auditor.")
    elif isinstance(questions_config, list):
        # Legacy list
        questions_list = questions_config
        global_instr = {}
        ref_policies = {}
        system_role = "You are a forensic document auditor."
    else:
        # Intermediate structure (flat dict)
        questions_list = questions_config.get("QUESTIONS", [])
        global_instr = questions_config.get("global_instructions", {})
        ref_policies = questions_config.get("REFERENCE_POLICIES", questions_config)
        system_role = "You are a forensic document auditor."

    prompt = f"""
    The following is a document text from a COI Management Plan. 
    Please extract the specific details requested in the questions below. 
    If a value is not found, return 'NA'.
    
    DOCUMENT CONTENT:
    ~~~~~~~~~~~~~~~~~
    {masked_text}
    ~~~~~~~~~~~~~~~~~
    
    QUESTIONS AND EXTRACTION PROMPTS:
    {json.dumps(questions_list, indent=2)}
    
    GLOBAL INSTRUCTIONS:
    {json.dumps(global_instr, indent=2)}

    OUTPUT FORMAT (JSON):
    {{
        "answers": [
            {{ "question_id": <int>, "question_text": "<str>", "answer_text": "<extracted detail>" }},
            ...
        ]
    }}
    """
    
    log_event("AI Service", "Analysis request sending to GPT-5", "PENDING")
    
    try:
        response = await client.chat.completions.create(
            model=GPT_DEPLOYMENT,
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}
        )
        
        content = response.choices[0].message.content
        usage = response.usage
        
        usage_data = {
            "prompt_tokens": usage.prompt_tokens,
            "completion_tokens": usage.completion_tokens,
            "total_tokens": usage.total_tokens
        }
        
        log_event("AI Service", f"Response received from GPT-5. Usage: {usage.total_tokens}", "SUCCESS")
             
        data = json.loads(content)
        answers = data.get("answers", [])
        
        # --- NEW: Double-Check Logic for Questions 13 and 14 ---
        # If any of these critical questions are 'NA', try one more time with a more persistent prompt.
        retry_ids = [13, 14]
        needs_retry = [q for q in answers if q.get("question_id") in retry_ids and q.get("answer_text", "").upper() in ["NA", "N/A", ""]]
        
        if needs_retry:
            log_event("AI Service", f"Triggering double-check for questions: {[q.get('question_id') for q in needs_retry]}", "PROGRESS")
            retry_questions = [q for q in questions_list if q.get("id") in [r.get("question_id") for r in needs_retry]]
            
            retry_prompt = f"""
            The initial extraction for the following fields was inconclusive. 
            Please perform a secondary review of the document text to verify if any values were missed.
            Focus specifically on policy names (Q13) and rule titles (Q14).
            
            DOCUMENT CONTENT:
            {masked_text}
            
            GLOBAL INSTRUCTIONS:
            {json.dumps(global_instr, indent=2)}

            REFERENCE POLICIES (CRITICAL for Q13 and Q14):
            {json.dumps(ref_policies, indent=2)}

            RETRY QUESTIONS:
            {json.dumps(retry_questions, indent=2)}

            OUTPUT FORMAT (JSON):
            {{ "answers": [ {{ "question_id": <int>, "answer_text": "<extracted detail>" }}, ... ] }}
            """
            
            try:
                retry_resp = await client.chat.completions.create(
                    model=GPT_DEPLOYMENT,
                    messages=[
                        {"role": "system", "content": "You are a helpful assistant."},
                        {"role": "user", "content": retry_prompt}
                    ],
                    response_format={"type": "json_object"}
                )
                retry_data = json.loads(retry_resp.choices[0].message.content)
                retry_answers = retry_data.get("answers", [])
                
                # Update original answers with retry results if they are NOT 'NA'
                for r_ans in retry_answers:
                    if r_ans.get("answer_text", "").upper() not in ["NA", "N/A", ""]:
                        for orig in answers:
                            if orig.get("question_id") == r_ans.get("question_id"):
                                orig["answer_text"] = r_ans["answer_text"]
                                log_event("AI Service", f"Double-check FOUND data for Q{orig.get('question_id')}", "SUCCESS")
            except Exception as re:
                print(f"Retry pass failed: {re}")

        return {
            "answers": answers,
            "usage": usage_data
        }
    except Exception as e:
        log_event("AI Service", f"Analysis failed: {str(e)}", "ERROR")
        print(f"AI ERROR: {e}")
        return {"answers": [], "usage": {}}
async def is_semantic_equivalent_batch(pairs: list[tuple[str, str]]) -> list[bool]:
    """
    Uses AI to determine semantic equivalence for a list of term pairs in a single call.
    Returns a list of booleans in the same order as the input pairs.
    """
    if not pairs:
        return []
    
    # 1. Prepare unique pairs to save tokens, but keep mapping for output
    unique_pairs = list(set(pairs))
    results_map = {}
    
    # 2. Pre-filter rule: Skip if either term is just symbols or empty
    def is_meaningful(text):
        if not text: return False
        import re
        # Must contain at least one alphanumeric character
        return bool(re.search(r'[a-zA-Z0-9]', text))

    # Fast-track literal matches for unique pairs
    remaining_pairs = []
    for p in unique_pairs:
        t1, t2 = p[0], p[1]
        
        if not is_meaningful(t1) or not is_meaningful(t2):
            # If one is meaningful but other is literally "NA", we could check, 
            # but usually [] vs NA is a mismatch in user intent.
            # If BOTH are non-meaningful (e.g. [] vs NA), it's a "technical match" but user wants DATA.
            # User expectation: [] vs NA should be a Mismatch (0 score) to avoid false pass.
            results_map[p] = False
        elif t1.lower().strip() == t2.lower().strip():
            results_map[p] = True
        else:
            remaining_pairs.append(p)
            
    if remaining_pairs:
        try:
            prompt = "Determine if the following term pairs are semantically equivalent (same entity, job title, or concept). Respond with a JSON list of booleans [true, false, ...] matching the order of the pairs.\n\nPAIRS:\n"
            for p in remaining_pairs:
                prompt += f"- Term 1: '{p[0]}', Term 2: '{p[1]}'\n"
            
            response = await client.chat.completions.create(
                model=GPT_DEPLOYMENT,
                messages=[
                    {"role": "system", "content": "You are a professional semantic matching assistant. Compare term pairs. Consider common institutional acronyms (SAB, BOD, BDA). Output ONLY a JSON list of booleans."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"}
            )
            
            # Robust JSON parsing: look for any list in the response
            data = json.loads(response.choices[0].message.content)
            batch_results = []
            if isinstance(data, list):
                batch_results = data
            elif isinstance(data, dict):
                # Look for the first value that is a list
                for val in data.values():
                    if isinstance(val, list):
                        batch_results = val
                        break
            
            for i, p in enumerate(remaining_pairs):
                if i < len(batch_results):
                    results_map[p] = bool(batch_results[i])
                else:
                    results_map[p] = False
        except Exception as e:
            print(f"Batch Semantic Error: {e}")
            for p in remaining_pairs:
                results_map[p] = False

    # Map back to original order
    return [results_map.get(p, False) for p in pairs]
