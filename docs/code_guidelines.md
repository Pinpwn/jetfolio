
# AI Coding Guidelines & System Instructions

This document serves as the mandatory specification for all code generation, refactoring, and architectural decisions. AI agents must adhere to these principles to ensure the system is **secure by design**, **performant**, and **highly resilient**.

---

## 1. Hardened Security (The "Unhackable" Standard)

The primary goal is to eliminate attack vectors at the source.

* **Zero-Trust Input:** Treat all input (API params, environment variables, user data, even internal DB strings) as malicious.
* *Mandatory:* Use strict schema validation (e.g., Pydantic, Zod) for all entry points.
* *Mandatory:* Use parameterized queries/ORMs to prevent SQL Injection.


* **Cryptographic Rigor:** * Never use MD5 or SHA-1 for security. Use Argon2id for passwords and SHA-256/3 for hashing.
* Use AES-256-GCM for encryption at rest.


* **Principal of Least Privilege:** Code must operate with the minimum permissions required. Avoid `sudo` or `admin` scopes in scripts.
* **Dependency Hygiene:** Only suggest well-maintained, audited libraries. Prefer standard libraries over third-party packages where possible.

---

## 2. Robust Performance & Resource Efficiency

Code must be optimized for low latency and minimal footprint.

* **Big O Awareness:** Prefer $O(1)$ or $O(\log n)$ operations. Avoid nested loops ($O(n^2)$) unless mathematically necessary.
* **Memory Management:** * Use generators/streams for processing large datasets to avoid memory spikes.
* Explicitly close database connections and file handles using context managers (`with` statements).


* **Concurrency & Async:** Utilize non-blocking I/O (`asyncio` in Python, `Worker Threads` in Node) for I/O-bound tasks to maximize CPU utilization.
* **Caching Strategy:** Implement memoization or TTL-based caching for expensive computations or frequent DB lookups.

---

## 3. Best Coding Principles (Clean Code)

Maintainability is as important as functionality.

* **SOLID Principles:** Ensure classes/functions have a **Single Responsibility**. Code should be open for extension but closed for modification.
* **DRY (Don't Repeat Yourself):** Abstract repeated logic into reusable components or utility functions.
* **Functional Purity:** Prefer pure functions (no side effects) to make testing and debugging deterministic.
* **Naming Conventions:** Use descriptive, intention-revealing names. (e.g., `calculate_remaining_balance()` instead of `calc_bal()`).

---

## 4. Error Handling & Resilience

The system must "fail gracefully" without exposing sensitive data.

* **Strict Typing:** Always use type hints (Python) or TypeScript interfaces. This allows the LLM to catch logic errors before execution.
* **Defensive Programming:** Use `try-except-finally` blocks extensively.
* **Never** use bare `except:` catch-all blocks.
* **No Silent Failures:** Log errors with context but return generic error messages to the end-user (to prevent information leakage).


* **Circuit Breakers:** For external API calls, implement timeouts and retry logic with exponential backoff.

---

## 5. Documentation & Traceability

* **Self-Documenting Code:** Write code that explains "what" it is doing; use comments only to explain "why" (the business logic).
* **Docstrings:** Every function must have a docstring following the [Google/Sphinx] format, including `Args`, `Returns`, and `Raises`.
* **Audit Logging:** Ensure critical actions (authentication, data deletion, configuration changes) are logged for forensic traceability.

---

## AI Agent Check-Step

Before providing a final code snippet, ask yourself:

1. **Does this code introduce a buffer overflow or injection risk?**
2. **Is there a more memory-efficient way to handle this data?**
3. **Will this code be readable by a human developer in 6 months?**

> **Note:** If a requested feature conflicts with these security or performance guidelines, the AI must flag the conflict and suggest a safer/more efficient alternative.
