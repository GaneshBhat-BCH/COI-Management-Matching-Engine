"""
COI Management Matching Engine - Architecture Diagram Generator
Uses diagrams library to create visual architecture diagrams
"""

from diagrams import Diagram, Cluster, Edge
from diagrams.programming.framework import Fastapi
from diagrams.onprem.database import PostgreSQL
from diagrams.azure.ml import CognitiveServices
from diagrams.programming.language import Python
from diagrams.onprem.client import Client

# Set diagram attributes
graph_attr = {
    "fontsize": "14",
    "bgcolor": "white",
    "pad": "0.5"
}

# System Architecture Diagram
with Diagram("COI Management System Architecture", 
             filename="architecture_diagram", 
             show=False, 
             direction="TB",
             graph_attr=graph_attr):
    
    client = Client("API Client")
    
    with Cluster("FastAPI Application"):
        api = Fastapi("FastAPI\nMain App")
        
        with Cluster("Routers"):
            upload_router = Python("Upload Router\n/api/upload")
            search_router = Python("Search Router\n/api/search")
        
        with Cluster("Services"):
            ai_service = Python("AI Service\nAzure OpenAI")
            logger = Python("Logger\nActivity Tracking")
        
        api >> Edge(label="route") >> [upload_router, search_router]
        upload_router >> Edge(label="analyze") >> ai_service
        search_router >> Edge(label="embed") >> ai_service
        [upload_router, search_router] >> logger
    
    with Cluster("External Services"):
        azure_openai = CognitiveServices("Azure OpenAI\nGPT-5 + Embeddings")
    
    with Cluster("Database Layer"):
        postgres = PostgreSQL("PostgreSQL\n+ pgvector")
        
        with Cluster("Tables"):
            docs = Python("pdf_documents")
            answers = Python("pdf_answers")
            chunks = Python("pdf_chunks")
    
    # Connections
    client >> Edge(label="HTTP POST") >> api
    ai_service >> Edge(label="API calls") >> azure_openai
    [upload_router, search_router] >> Edge(label="SQL queries") >> postgres
    postgres >> [docs, answers, chunks]


# Upload Flow Diagram
with Diagram("Document Upload Flow", 
             filename="upload_flow_diagram", 
             show=False, 
             direction="LR",
             graph_attr=graph_attr):
    
    client = Client("Client")
    
    with Cluster("Upload Process"):
        upload = Python("1. Receive\nDocument")
        db_insert = PostgreSQL("2. Create\nRecord")
        ai_analyze = CognitiveServices("3. AI\nAnalysis")
        embed_answers = CognitiveServices("4. Embed\nAnswers")
        store_answers = PostgreSQL("5. Store\nAnswers")
        create_chunks = Python("6. Create\nChunks")
        embed_chunks = CognitiveServices("7. Embed\nChunks")
        store_chunks = PostgreSQL("8. Store\nChunks")
    
    client >> upload >> db_insert >> ai_analyze >> embed_answers >> store_answers
    store_answers >> create_chunks >> embed_chunks >> store_chunks


# Search Flow Diagram
with Diagram("Hybrid Search Flow", 
             filename="search_flow_diagram", 
             show=False, 
             direction="TB",
             graph_attr=graph_attr):
    
    client = Client("Client")
    
    with Cluster("Search Strategy"):
        prepare = Python("1. Prepare\nQuery")
        keyword = PostgreSQL("2. Keyword\nSearch (FREE)")
        verify_kw = Python("3. Verify\nResults")
        decision = Python("4. Check\nCount >= 3?")
        
        with Cluster("Vector Fallback (Conditional)"):
            embed = CognitiveServices("5. Generate\nEmbedding")
            vector = PostgreSQL("6. Vector\nSearch")
            verify_vec = Python("7. Verify\nResults")
            combine = Python("8. Combine\nResults")
    
    client >> prepare >> keyword >> verify_kw >> decision
    decision >> Edge(label="< 3 results") >> embed >> vector >> verify_vec >> combine
    decision >> Edge(label=">= 3 results", style="dashed") >> combine

print("Architecture diagrams generated successfully!")
print("Files created:")
print("  - architecture_diagram.png")
print("  - upload_flow_diagram.png")
print("  - search_flow_diagram.png")
