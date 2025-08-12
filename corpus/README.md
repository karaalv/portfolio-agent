# RAG Agent Corpus 📚

This folder contains the **RAG Agent Corpus**, a curated collection of documents and resources designed to provide the agent with contextual knowledge for more accurate and relevant responses.  

The corpus is used with a **contextual retrieval** approach, enhancing the agent’s ability to recall and apply relevant information during conversations. My implementation follows the general method described in [Anthropic’s article on contextual retrieval](https://www.anthropic.com/news/contextual-retrieval), with custom adaptations for this project.  

## Purpose

- Store all written content and reference materials forming the agent’s knowledge base.  
- Preprocess, embed, and upload the corpus to MongoDB for retrieval at runtime.  
- Serve as the primary source of context for the RAG system during inference.  

While this folder is primarily part of the **preprocessing pipeline**, it is included in the repository for completeness and transparency.