# RAG Agent Corpus Documents 📃

This folder contains the documents that form the **RAG Agent Corpus**. The knowledge is organized using a **semi-structured** approach, where each file focuses on a specific scope of information; for example, education, projects, or technical skills. Within each file, content is further divided into **subcategories** related to the file’s main topic.  

To improve retrieval accuracy and relevance, information is stored with **contextual information**, ensuring that each piece of data is easily matched to user queries.  

For easier parsing and automated processing, custom **tags** are embedded within each document. These tags are leveraged during preprocessing to facilitate efficient embedding, indexing, and retrieval.  

## Section labels

Each `<section>` contains a `<label>` tag identifying its topic,
for example, `<label>projects_portfolio_agent</label>`. The loader
preserves this value as `CorpusItem.label` and generates a fresh
UUID version 4 string for `CorpusItem.item_id` using the shared
`generate_uuid_str` helper.
