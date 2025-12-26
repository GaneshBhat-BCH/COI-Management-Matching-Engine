# Architecture Diagram Generator - README

## Overview
This script generates visual architecture diagrams for the COI Management Matching Engine using the `diagrams` library.

## Prerequisites
Install the diagrams library:
```bash
pip install diagrams
```

**Note**: This library also requires Graphviz to be installed on your system:
- **Windows**: Download from https://graphviz.org/download/
- **Linux**: `sudo apt-get install graphviz`
- **Mac**: `brew install graphviz`

## Usage
Run the script to generate PNG diagrams:
```bash
python generate_diagrams.py
```

## Generated Files
The script creates three PNG files:
1. **architecture_diagram.png** - Overall system architecture
2. **upload_flow_diagram.png** - Document upload and ingestion flow
3. **search_flow_diagram.png** - Hybrid search flow with decision logic

## Alternative: Mermaid Diagrams
If you prefer not to install Graphviz, use the Mermaid diagrams in `TECHNICAL_ARCHITECTURE.md` instead. These can be viewed in:
- GitHub (renders automatically)
- VS Code (with Mermaid extension)
- Any Markdown viewer with Mermaid support
- Online at https://mermaid.live/

## Diagram Types Included

### 1. System Architecture
Shows the complete system with:
- Client layer
- FastAPI application (routers, services)
- Azure OpenAI integration
- PostgreSQL database with tables

### 2. Upload Flow
Step-by-step visualization of document processing:
1. Receive document
2. Create database record
3. AI analysis with GPT-5
4. Generate answer embeddings
5. Store answers
6. Create search chunks
7. Generate chunk embeddings
8. Store chunks with dual indexes

### 3. Search Flow
Hybrid search strategy visualization:
1. Prepare query
2. Keyword search (free)
3. Verify results
4. Decision point (>= 3 results?)
5. Conditional vector search
6. Combine results

## Notes
- The diagrams library creates high-quality PNG images
- Mermaid diagrams in TECHNICAL_ARCHITECTURE.md are more detailed and include sequence diagrams
- Both approaches are valid - choose based on your preference and tooling
