# AI Design

The AI layer should make the job data easier to search, understand, and act on. It should not replace the structured data model; it should enrich it.

## AI Use Cases

- Extract skills, seniority, tools, and domains from job descriptions.
- Generate embeddings for semantic job search.
- Match resumes to job postings.
- Identify skill gaps and recommend next learning steps.
- Answer user questions using RAG over structured data and source postings.
- Summarize hiring trends by role, company, location, and skill.

## Skill Extraction

Skill extraction should combine deterministic rules with model-assisted extraction.

Recommended approach:

1. Maintain a canonical skill taxonomy.
2. Use exact and fuzzy matching for common skills.
3. Use an LLM or classifier for ambiguous descriptions.
4. Store extracted skills with confidence, method, and required/preferred status.
5. Review low-confidence extractions during evaluation.

Examples:

- "Spark" maps to Apache Spark.
- "AWS Glue" maps to AWS and AWS Glue.
- "modern data stack" may require model-assisted interpretation.

## Embeddings Strategy

Generate embeddings for:

- Job title plus normalized title
- Cleaned job description
- Extracted skills
- Company and location context
- Resume text

Use embeddings for:

- Semantic job search
- Similar job recommendations
- Resume-to-job similarity
- Retrieval for AI answers

Store an `embedded_text_hash` so embeddings are regenerated only when relevant text changes.

## Resume Matching

Resume matching should combine multiple signals rather than relying on a single LLM response.

Signals:

- Skill overlap
- Required skill coverage
- Semantic similarity between resume and job description
- Seniority alignment
- Domain or industry alignment
- Experience years when available

Output:

- Overall match score
- Matched skills
- Missing skills
- Seniority fit
- Suggested resume improvements
- Suggested learning plan

## RAG Design

RAG should ground AI responses in retrieved records.

Flow:

1. User asks a question.
2. System classifies intent: search, trend analysis, resume help, or general career question.
3. System retrieves relevant job postings, aggregates, skills, or resume records.
4. LLM generates an answer using only retrieved context.
5. Response includes references to supporting postings, skills, or aggregate metrics.

Example question:

> What skills are rising fastest for data engineers in Texas?

Relevant context:

- `mart_skill_trends`
- Matching canonical jobs
- Skill growth metrics by time period

Expected answer:

- Top rising skills
- Directional trend explanation
- Supporting counts or percentages
- Caveat about data source coverage

## Evaluation

AI features should have simple evaluation from the beginning.

### Extraction Evaluation

Track:

- Precision and recall on labeled job descriptions
- Confidence distribution
- Most common false positives
- Most common missed skills

### Search Evaluation

Track:

- Whether top results match user intent
- Click-through or manual relevance labels
- Keyword search vs semantic search comparisons

### Resume Match Evaluation

Track:

- Whether matched skills are actually present in the resume
- Whether missing skills are genuinely missing
- Whether recommendations are specific and useful

### RAG Evaluation

Track:

- Groundedness
- Citation coverage
- Hallucination rate
- Answer relevance
- Refusal behavior when data is insufficient

## Guardrails

- Do not fabricate salary data when a posting has no salary range.
- Distinguish observed trends from inferred trends.
- Show data coverage limitations.
- Cite source postings or aggregate records where possible.
- Keep resume recommendations practical and specific.
