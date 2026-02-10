Car Buyer Assist RAG Application

**Design Document**

| Version | 1.0 |
| --- | --- |
| Date | December 2025 |
| Type | POC Design - AI-Assisted Development |


# 1. Objective

This design document provides the technical blueprint for implementing the Car Buyer Assist RAG Application. It translates business requirements into a concrete system architecture, specifying components, technology choices, data flows, and implementation approaches. This document serves as the foundation for AI-assisted development, where implementation prompts will be generated for Cursor agents to build the actual system.

# 2. System Architecture

## 2.1 High-Level Architecture

The system follows a modern RAG architecture with clear separation of concerns:

| USER INTERFACE LAYER
Streamlit Web Application
• Dashboard  • Connectivity Validation  • Document Processing  • Interactive Assistant  • Observability |
| --- |
| ↓ |
| ORCHESTRATION LAYER LangChain Framework • Document Loaders  • Text Splitters  • RAG Chain  • Prompt Management |
| ↙        ↓        ↘ |
|  |


## 2.2 Component Explanation

**User Interface Layer (****Streamlit****)**

Provides a web-based interface for all user interactions. Built with Streamlit for rapid development and intuitive UX. Handles document uploads, displays chat interfaces, shows processing progress, and presents observability metrics. Manages session state for conversation context.

**Orchestration Layer (****LangChain****)**

Core framework that coordinates all RAG operations. Manages document loading from PDFs, text chunking strategies, embedding generation, vector storage operations, and the complete RAG chain for query processing. Provides standardized interfaces to integrate with various LLM providers and vector databases.

**Vector Store (****ChromaDB****)**

Persistent storage for document embeddings and metadata. Enables efficient similarity search to retrieve relevant context for user queries. Stores document chunks with associated metadata (source file, page numbers, section) for proper citation. Optimized for semantic search operations.

**LLM Service (GCP Vertex AI)**

Provides both embedding generation (text-embedding-004) and text generation capabilities (gemini-1.5-pro). Embeddings convert text into vector representations for semantic similarity. Text generation produces natural language responses grounded in retrieved context. Accessed via Google Cloud Platform APIs.

**Observability Layer (****LangSmith****)**

Tracks all LLM interactions, including prompts, responses, token usage, latency, and costs. Provides visibility into the RAG pipeline performance, enabling debugging and optimization. Traces complete conversation flows from query to response generation.

## 2.3 Data Flow

**Document Processing Flow:**

User uploads PDF documents via Streamlit interface

LangChain's PyPDFLoader extracts text content from PDFs

RecursiveCharacterTextSplitter chunks text (1000 chars, 200 overlap)

Vertex AI generates embeddings (text-embedding-004) for each chunk

ChromaDB stores embeddings with metadata (filename, chunk index)

LangSmith tracks processing metrics (time, cost, chunk count)

**Query-Response Flow:**

User enters natural language question in chat interface

LangChain converts query to embedding using Vertex AI

ChromaDB performs similarity search, returns top 5 relevant chunks

RAG chain constructs prompt with: query + retrieved context + instructions

Vertex AI (gemini-1.5-pro) generates response grounded in context

Response formatted with citations (source document + section)

Streamlit displays response to user, updates conversation history

LangSmith logs complete trace (query, retrieval, generation, timing, cost)

# 3. Component Design

## 3.1 Document Processing Pipeline

**PDF Text Extraction**

Library: PyPDFLoader from LangChain

Preserves text structure, extracts page metadata

Handles multi-page PDFs, maintains document order

**Text Chunking Strategy**

Method: RecursiveCharacterTextSplitter

Chunk Size: 1000 characters (balances context vs. retrieval precision)

Overlap: 200 characters (maintains continuity across chunk boundaries)

Splitting Hierarchy: Paragraphs → Sentences → Words (preserves semantic units)

**Embedding Generation**

Model: text-embedding-004 (Google's latest embedding model)

Dimensions: 768 (optimal balance of quality and performance)

Batch Processing: Process chunks in batches to optimize API calls

**Vector Storage**

Database: ChromaDB (lightweight, embedded vector database)

Persistence: Local directory for POC (./chroma_db)

Metadata Schema:

| Field | Description |
| --- | --- |
| source | Original PDF filename |
| page | Page number in source document |
| chunk_index | Sequential chunk number |
| model_name | Vehicle model (e.g., 'Camry', 'RAV4') |

**Progress Tracking**

Real-time progress bar in Streamlit UI

Status messages: 'Extracting text...', 'Generating embeddings...', 'Storing vectors...'

Final summary: Total chunks created, processing time, models covered

## 3.2 Interactive RAG Assistant

**Query Processing**

Accept natural language input via Streamlit text input

Convert query to embedding using text-embedding-004

Maintain conversation history in Streamlit session state

**Retrieval Strategy**

Similarity Search: Cosine similarity in vector space

Top-K Selection: Retrieve 5 most relevant chunks

Deduplication: Remove redundant chunks from same source

Context Assembly: Combine chunks with metadata for LLM prompt

**Response Generation**

Model: gemini-1.5-pro (strong reasoning, large context window)

Temperature: 0.3 (balance between consistency and natural language)

Max Output Tokens: 1024

System Prompt Instructions:

| Prompt Template:
You are a helpful Toyota car sales assistant. Answer questions based ONLY on the provided context from Toyota specification documents. If the information is not in the context, say 'I don't have that information in the available Toyota specifications.' Always cite the source document when providing answers. |
| --- |

**Citation Formatting**

Include source document name in response

Format: 'According to [Toyota_Camry_Specifications.pdf]...'

Display as expandable sections in Streamlit for full context


**Hallucination Mitigation**

Explicit instructions to not generate information outside retrieved context

Low temperature setting (0.3) for factual consistency

Trained to acknowledge when information is unavailable

# 4. UI Specification

The application uses Streamlit's multipage app structure with five distinct pages, each serving a specific purpose in the workflow.

## 4.1 Landing Page with Dashboard

**Purpose:**

Welcome screen providing system overview, quick stats, and navigation to other pages.

**Key Elements:**

Application title and description

System status indicators (services connected, documents processed)

Quick statistics: Total documents, total chunks, models covered

Navigation cards linking to: Connectivity Check, Document Processing, Interactive Assistant, Observability

Sample query examples to guide users

## 4.2 Connectivity Validation Page

**Purpose:**

Verify all external service connections before processing documents or queries.

**Validation Checks:**

| Service | Validation Test |
| --- | --- |
| GCP Vertex AI | Test embedding generation with sample text |
| ChromaDB | Verify database connection and read/write access |
| LangSmith | Check API key validity and trace logging capability |


**Display Format:**

Visual indicators: Green checkmark for success, red X for failure

Status messages explaining connection issues if any

'Test All Connections' button to run checks

Configuration display: Project ID, region, database path

## 4.3 Document Processing Page

**Purpose:**

Upload and process Toyota specification PDFs to create the knowledge base.

**Upload Interface:**

File uploader: Accept multiple PDF files simultaneously

File type validation: Restrict to .pdf extensions

Display uploaded file list with sizes

'Process Documents' button to start ingestion

**Processing Display:**

Progress bar showing overall completion percentage

Current operation status: 'Processing Toyota_Camry_Specifications.pdf...'

Real-time log messages: Extraction complete, generating embeddings, storing vectors

Per-document summary: Chunks created, processing time

**Completion Summary:**

Total documents processed

Total chunks created and stored

Total processing time

Models covered (extracted from filenames)

Success indicator and navigation prompt to Interactive Assistant

## 4.4 Interactive Assistant Page

**Purpose:**

Chat interface for asking questions about Toyota vehicles using the RAG system.

**Interface Layout:**

Chat history display: Scrollable conversation view

User messages: Right-aligned, light blue background

Assistant messages: Left-aligned, white background, includes citations

Input box: Fixed at bottom of screen for query entry

'Send' button to submit query

'Clear Conversation' button to reset chat history

**Example Queries:**

Display clickable example questions to guide users:

'What is the fuel efficiency of the Camry hybrid?'

'Compare RAV4 and Highlander for families'

'What safety features does the Corolla have?'

'What is the towing capacity of the Tacoma?'

**Response Formatting:**

Main answer in clear, readable paragraphs

Citations in smaller text below answer

Expandable sections showing retrieved context chunks

Loading spinner during processing

## 4.5 Observability Page

**Purpose:**

Display metrics and traces from LangSmith for system monitoring and debugging.

**Metrics Display:**

| Metric Category | Details Displayed |
| --- | --- |
| Query Statistics | Total queries, average response time, success rate |
| Token Usage | Total tokens consumed, input vs output breakdown |
| Cost Tracking | Estimated API costs (embeddings + generation) |
| Retrieval Metrics | Average chunks retrieved, similarity scores distribution |


**Trace Viewer:**

List of recent queries with timestamps

Click to expand: Full query text, retrieved chunks, LLM response, timing breakdown

Direct link to detailed trace in LangSmith UI

**Performance Charts:**

Response time over time (line chart)

Token usage over time (bar chart)

Retrieval quality indicators (similarity score distribution)

# 5. Implementation Notes

## 5.1 Technology Stack

| Component | Technology / Version |
| --- | --- |
| Frontend Framework | Streamlit 1.28+ |
| Orchestration | LangChain 0.1+ |
| Vector Database | ChromaDB 0.4+ |
| LLM Provider | GCP Vertex AI (gemini-1.5-pro, text-embedding-004) |
| Observability | LangSmith |
| PDF Processing | PyPDF (via LangChain) |
| Language | Python 3.10+ |

## 5.2 Key Dependencies

**Core Libraries:**

| streamlit>=1.28.0
langchain>=0.1.0
langchain-google-genai>=4.2.0
chromadb>=0.4.0
langsmith>=0.1.0
pypdf>=3.0.0
google-cloud-aiplatform>=1.38.0 |
| --- |

Vertex AI (embeddings and LLM) is used via `langchain-google-genai` with `vertexai=True` and project/region from environment (`GOOGLE_PROJECT_ID`, `GOOGLE_REGION`).

## 5.3 Environment Configuration

**Required Environment Variables:**

| Variable | Purpose |
| --- | --- |
| GOOGLE_PROJECT_ID | GCP project for Vertex AI access |
| GOOGLE_REGION | GCP region for Vertex AI (e.g., us-central1) |
| LANGSMITH_API_KEY | LangSmith API key for observability |
| LANGSMITH_PROJECT | LangSmith project name |
| GOOGLE_APPLICATION_CREDENTIALS | Path to GCP service account JSON key |

## 5.4 Development Considerations

**Project Structure:**

| car-buyer-assist/
  ├── pages/
  │   ├── 1_connectivity.py
  │   ├── 2_document_processing.py
  │   ├── 3_interactive_assistant.py
  │   └── 4_observability.py
  ├── utils/
  │   ├── document_processor.py
  │   ├── rag_chain.py
  │   └── observability.py
  ├── data/
  │   └── toyota_specs/  # PDF storage
  ├── chroma_db/  # Vector database persistence
  ├── Home.py  # Landing page
  ├── requirements.txt
  └── .env  # Environment variables |
| --- |


**Implementation Sequence:**

Set up project structure and install dependencies

Implement document processing pipeline (extract, chunk, embed, store)

Build RAG chain (retrieval + generation)

Create Streamlit pages (Home → Connectivity → Document Processing)

Implement Interactive Assistant with chat interface

Add LangSmith integration and Observability page

Test with sample queries from BRD

## 5.5 POC Constraints & Simplifications

Single-user session state (no multi-user support)

Local ChromaDB storage (no cloud vector database)

In-memory conversation history (resets on page refresh)

Fixed chunking parameters (no dynamic optimization)

Basic error handling (focus on happy path)

No user authentication or access control

Simple citation format (no advanced provenance tracking)

Limited to 8 Toyota PDFs (no dynamic dataset expansion)


*— End of Design Document —*
