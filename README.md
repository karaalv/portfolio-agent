# Portfolio Agent 🤖

This repository contains my portfolio agent, which is a RAG (Retrieval-Augmented Generation) agent designed to answer questions about my profile and generate content such as:

- Resumes
- Cover letters

The agent can also email these documents to you.

To interact wth the agent, you can check it out on my website [Alvin Karanja](https://www.alvinkaranja.dev/chat)

## 🏗️ Deployment

- The agent is deployed using AWS as a traditional backend service, I use terraform to manage the infrastructure, and kubernetes to manage the containerized application.

## 🌐 User Management

- This repository also contains a user management functionality that manages users and their sessions. It uses JWT for authentication and authorization.

## 🗂️ Project Structure 

The project is structured into the following packages to make things easier for myself:

- `agent`: Contains the agent logic and configuration.
- `database`: Contains the database logic and configuration, mainly to manage database resources.
- `api`: Contains the API logic and configuration to communicate with the frontend.