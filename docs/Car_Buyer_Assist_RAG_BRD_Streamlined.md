

Business Requirements Document

**Car Buyer Assist RAG Application**

*Proof of Concept*


| Version | 1.0 - Streamlined |
| --- | --- |
| Date | December 2025 |
| Type | POC - AI-Assisted Development |


# Project Overview

## What We're Building

A conversational AI system that helps prospective car buyers get instant, accurate answers about Toyota vehicles by asking natural language questions. The system uses Retrieval-Augmented Generation (RAG) to ground responses in official Toyota specification documents, ensuring accuracy while providing a natural chat experience.

## Why We're Building It

Current car buying research is frustrating:

Customers must manually search through dense PDF spec sheets

Comparing features across models requires significant effort

Sales representatives aren't always available for quick questions

This POC demonstrates how RAG technology can provide immediate, accurate vehicle information through conversational queries, improving the customer experience while reducing repetitive support burden.

## Dataset

**Eight Toyota vehicle specification PDFs covering diverse segments:**

**Sedans: **Corolla, Camry

**SUVs: **RAV4, Highlander

**Hybrids: **Prius, Prius Prime

**Truck: **Tacoma

**Electric: **bZ4X

Each PDF contains comprehensive specifications including engine options, features, safety systems, pricing, fuel efficiency, and competitive comparisons.

# User Scenarios & Sample Queries

The system must handle diverse question types across different buyer needs:

## Specification Queries

"What is the fuel efficiency of the Camry hybrid?"

"How much horsepower does the RAV4 Prime have?"

"What is the towing capacity of the Tacoma V6?"

"What is the electric range of the bZ4X?"

## Comparison Queries

"Compare fuel efficiency between Prius and Prius Prime"

"What are the differences between RAV4 and Highlander?"

"Which sedan is better for first-time buyers?"

"How does the Camry compare to the Honda Accord?"

## Feature & Safety Queries

"What safety features does the Corolla have?"

"Does the Highlander have third-row seating?"

"What technology features are in the RAV4?"

"Is AWD available on the Camry?"

## Pricing & Value Queries

"What is the starting price of the Corolla?"

"Which Toyota SUV offers the best value?"

"What trim levels are available for the Tacoma?"

## Recommendation Queries

"What Toyota vehicle is best for a family of five?"

"I need a fuel-efficient car for city driving, what do you recommend?"

"Which hybrid has the longest electric range?"

# Functional Requirements

## Document Processing

Extract text from all eight Toyota PDF specification documents

Chunk text into semantically meaningful segments (optimize size for retrieval)

Generate embeddings for each chunk and store in vector database

Preserve metadata (source document, model name, section) for citation

## Query & Retrieval

Accept natural language questions via web-based chat interface

Convert queries to embeddings using same model as document processing

Perform semantic search to retrieve top 3-5 most relevant chunks

Return relevant context with source information

## Response Generation

Use LLM to generate natural language answers grounded in retrieved context

Include source citations (model name, document section) with responses

Handle cases where information isn't found (acknowledge limitation vs. hallucinating)

Format responses clearly with proper structure for readability

## User Interface

Web-based chat interface (e.g., Streamlit or similar framework)

Display conversation history within current session

Provide example queries to guide users

Show loading indicators during processing

Option to clear/reset conversation

There should a page where documents are uploaded manually and processed.

At a given time, we should be able to upload one or more documents for processing.

Progress should be shown while documents are being processed.

# Non-Functional Requirements

## Performance

Response time: < 10 seconds for typical queries

Document ingestion: Complete all 8 PDFs within 5 minutes

## Accuracy

Responses must be grounded in source documents (minimize hallucinations)

Acknowledge when information isn't available rather than guessing

Retrieval relevance: Top results should match query intent 80%+ of time

## Usability

No training required - intuitive for non-technical users

Works in standard web browsers (Chrome, Firefox, Safari, Edge)

Clear error messages if something fails

## Observability

The prompts should be tracked (time taken, cost, etc)

The data pipeline also should be tracked

Overall there should be observability in the application


# Success Criteria

**The POC is successful when:**

**Complete RAG Pipeline: **End-to-end flow works from PDF ingestion → embedding → retrieval → response generation

**Accurate Retrieval: **System finds relevant information for 80%+ of test queries from the sample scenarios

**Quality Responses: **Answers are factually correct, well-formatted, and cite sources appropriately

**Diverse Query Handling: **System successfully handles specifications, comparisons, features, pricing, and recommendations

**Usable Interface: **Non-technical users can interact with the system without assistance

**Performance Targets Met: **Response times and ingestion speed meet NFR requirements

# Scope Boundaries

## In Scope (Must Have)

Data pipeline with the 8 Toyota specification PDFs

Web-based chat interface for Q&A (RAG)

Session-based conversation context

Source citations with responses

Example queries for user guidance

## Out of Scope (Not Needed for POC)

User authentication or accounts

Persistent conversation history across sessions

Multi-language support

Real-time inventory or pricing integration

Appointment scheduling or CRM integration

Lead capture or sales tracking

Mobile apps (web only)

Advanced analytics or reporting dashboards

Production infrastructure, security hardening, or scaling

## Key Constraints

**Dataset: **Fixed to 8 Toyota models - no expansion during POC

**Technology: **Use standard, well-documented frameworks (e.g., Streamlit, LangChain, ChromaDB)

**Deployment: **Local or simple cloud deployment for demonstration only

**Development: **AI-assisted workflow using Claude for prompts and Cursor agents for implementation

# Next Steps

Following this BRD, the development workflow proceeds as:

**Design Document: **Technical architecture, component specifications, technology stack decisions, and RAG pipeline design

**Implementation Prompts: **Claude generates detailed prompts for each component that Cursor agents will use to write code

**Development: **Cursor agents implement the system based on the prompts

**Testing & Validation: **Verify success criteria are met with sample queries
