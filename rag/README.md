# Retrieval-Augmented Generation (RAG) System ⚙️

## Overview

This folder contains the **Retrieval-Augmented Generation (RAG)** system implementation for the portfolio agent.  
The RAG system enables the agent to retrieve and synthesize relevant information from my personal profile in response to user queries.

It powers both **general user interactions** and **custom document generation tasks**, such as creating tailored resumes and cover letters.

## Literature Review

The design draws on recent research in RAG systems and natural language processing, with particular influence from:

1. [Contextual Retrieval — Anthropic](https://www.anthropic.com/news/contextual-retrieval)  
2. [Knowledge Graph Infused RAG — Wu et al.](https://arxiv.org/abs/2506.09542)  
3. [Enhanced Document Retrieval with Topic Embeddings — Huseynova & Isbarov](https://arxiv.org/abs/2408.10435)  

## High-Level Architecture

The system operates in **five core stages**:

1. **Input Refiner**  
   Cleans and interprets the raw user query to extract intent and relevant context.  

2. **Query Planner**  
   Generates a structured set of targeted sub-queries designed to provide deep contextual coverage from the corpus.  

3. **Retriever**  
   Executes sub-queries in parallel, fetching relevant documents from the corpus.  
   All retrieved documents are merged for downstream processing.  

4. **Augmenter**  
   Enhances the retrieved content by aligning it with the original query context, ensuring relevance and cohesion.  

5. **Generator**  
   Synthesizes the augmented content into a coherent, context-aware final response.  

This architecture allows the portfolio agent to combine precise retrieval with fluent generation, producing outputs that are **accurate, personalized, and contextually rich**.

## Folder Structure

The folder has the following main files:

- `query_planner.py`: Contains the logic for the input refiner and query planner.
- `query_executor.py`: Handles the execution of queries against the document corpus (retrieval) and augmentation of the retrieved content.
- `main.py`: The entry point for the RAG system, orchestrating the overall process.