---
description: Use local Ollama models to answer questions and generate code with 0 cloud token consumption
---

# Local Model Workflow — Zero Cloud Token

When the user asks a question or requests code generation, prefer using local Ollama models via MCP tools to minimize cloud token usage.

## Available MCP Tools (ollama-local server)

1. **local_chat** — General Q&A using local Ollama (0 cloud tokens)
   - Use for: knowledge queries, explanations, translations, summaries
   - Models: qwen3:32b (deep reasoning), qwen3:8b (general), qwen3:4b (fast)

2. **local_code** — Code generation/analysis (0 cloud tokens)
   - Use for: writing functions, debugging, code review, refactoring
   - Automatically uses qwen3:32b for best quality

3. **local_analyze** — Document/code analysis (0 cloud tokens)
   - Use for: analyzing large text, code review, error analysis

4. **local_construction** — Construction engineering Q&A (0 cloud tokens)
   - Use for: construction regulations, safety standards, engineering calculations

5. **local_models** — List available local models

## Decision Flow

1. If the user asks a general question → use `local_chat`
2. If the user asks about code → use `local_code`
3. If the user asks to analyze content → use `local_analyze`
4. If the user asks about construction/engineering → use `local_construction`
5. Only use cloud AI for tasks that require:
   - File editing (Cascade's core capability)
   - Tool calling orchestration
   - Multi-step complex workflows
   - Tasks where local model quality is insufficient

## Example Usage

User: "What is the difference between TCP and UDP?"
→ Call `local_chat` with prompt "What is the difference between TCP and UDP?"

User: "Write a Python function to calculate rebar usage"
→ Call `local_code` with task "Write a Python function to calculate rebar usage"

User: "Analyze this error log and find the root cause"
→ Call `local_analyze` with the error content and instruction "find root cause"
