# Agents

Notes on building AI agents with the LangChain stack.

## The three layers

Top-down. Each layer is built on the one below.

| Layer | What it is | You write |
|---|---|---|
| Deep Agents | Agent harness. Planning, files, subagents, memory included. | `create_deep_agent(model, tools=[...])` |
| LangGraph | Agent runtime. Custom control flow, durable state. | `StateGraph`, nodes, edges |
| LangChain | Framework. Models, tools, agent loop. | `create_agent(model, tools=[...])` |

LangSmith: observability for all layers. Not a framework.

You code against one layer. The layers below come as dependencies.
Deep Agents uses LangGraph and LangChain inside. You do not see them.

## When to use which

Check in order. Stop at the first match.

1. Needs planning, file work across a long session, persistent memory,
   subagent delegation, or on-demand skills: **Deep Agents**.
2. Needs custom control flow: deterministic loops, branching, reflection,
   precise human breakpoints, state that survives failures: **LangGraph**.
3. Single-purpose agent with a fixed tool set: **LangChain `create_agent`**.
4. No agent loop: prompt chain, retrieval, structured output:
   **LangChain** direct model call.

## Mixing layers

- A compiled LangGraph graph can be a subagent or tool inside Deep Agents.
- LangChain tools and retrievers work inside all layers.

## Sources

- Docs root: https://docs.langchain.com
- LangChain: https://docs.langchain.com/oss/python/langchain/overview
- LangGraph: https://docs.langchain.com/oss/python/langgraph/overview
- Deep Agents: https://docs.langchain.com/oss/python/deepagents/overview
- LangSmith: https://docs.langchain.com/langsmith/home
