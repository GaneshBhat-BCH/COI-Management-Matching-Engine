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
    {system_role}
    Your goal is to extract specific details from the document text provided below.
    Note: Some medical or sensitive words in the document text have been masked (e.g. C*ncer, De*th) to ensure system compatibility. Please interpret them correctly and provide the regular unmasked word in your answer output.
    
    DOCUMENT CONTENT:
    ~~~~~~~~~~~~~~~~~
    {masked_text}
    ~~~~~~~~~~~~~~~~~
    
    YOUR TASK:
    Answer the following questions based on the document text.
    
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
    
    log_event("AI Service", "Analysis request sending to GPT-5", "PENDING")
    
    try:
        response = await client.chat.completions.create(
            model=GPT_DEPLOYMENT,
            messages=[
                {"role": "system", "content": system_role},
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
        return {
            "answers": data.get("answers", []),
            "usage": usage_data
        }
    except Exception as e:
        log_event("AI Service", f"Analysis failed: {str(e)}", "ERROR")
        print(f"AI ERROR: {e}")
        return {"answers": [], "usage": {}}
