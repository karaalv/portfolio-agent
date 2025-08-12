# Portfolio Agent 🤖

This repository contains my portfolio agent, which is a RAG (Retrieval-Augmented Generation) agent designed to answer questions about my profile and generate content such as:

- Resumes
- Cover letters

The agent can also email these documents to you.

To interact with the agent, you can check it out on my website [link](https://www.alvinkaranja.dev/chat)

<!-- For a detailed explanation of how the agent works, you can refer to my blog post [link](https://www.alvinkaranja.dev/blog/portfolio-agent). -->

## 🏗️ Deployment

- The agent is deployed using AWS as a traditional backend service, I use terraform to manage the infrastructure, and kubernetes to manage container orchestration.

## 🌐 User Management

- This repository also contains user management functionality that manages users and their sessions. It uses JWTs to secure the API endpoints and manage user sessions.

## 🗂️ Project Structure 

The project is structured into the following packages to make things easier for myself:

- `agent/`: Contains the agent logic and configuration.
- `database/`: Contains the database logic and configuration, mainly to manage database resources.
- `api/`: Contains API logic and configuration to communicate with the frontend.
- `rag/`: Contains the implementation of the Retrieval-Augmented Generation (RAG) system.
- `corpus/`: Contains the RAG Agent Corpus, a collection of documents and resources for contextual knowledge.