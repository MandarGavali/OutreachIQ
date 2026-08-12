# Technical Interview Explanation

If asked about the V2 architecture improvements during a technical interview, here are the key talking points:

### 1. Moving Away from Framework "Magic"
**The Problem**: The original main branch used LangChain's `AgentExecutor`. While quick to implement, it obscured failure modes, often resulted in infinite loops, and was difficult to test defensively.
**The Solution**: Implemented a custom agent loop. The LLM dictates tools directly via AIMessage, while Python controls execution, type-safety (Pydantic), and retry budgets.

### 2. Separation of Concerns in Scraping
**The Problem**: Scraping was tightly coupled.
**The Solution**: We built a `ProfileScraper` with adapters, cache, and rate-limiting. This allowed us to inject a `FixtureProfileAdapter` for deterministic E2E testing without making live requests to LinkedIn.

### 3. Self-Correction & Generative AI Quality
**The Problem**: Generative AI occasionally produces spammy or hallucinated outreach.
**The Solution**: We introduced a distinct Evaluator LLM layer that scores generations on 5 dimensions (Relevance, Specificity, Personalization, Naturalness, Factuality). If the score falls below a threshold, the loop automatically reprompts the Generator with specific feedback to improve the message, protecting the user from poor outputs.
