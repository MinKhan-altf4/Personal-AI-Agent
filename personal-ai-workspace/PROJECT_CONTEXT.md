# PROJECT CONTEXT — Personal AI-Agent Workspace

**Document status:** Initial baseline  
**Version:** 1.0  
**Created:** 2026-11-15  
**Owner:** Workspace Owner / Commander  
**Primary environment:** Windows  
**Primary language:** Vietnamese; technical identifiers and code may use English.

---

## 1. Project identity

**Name:** Personal AI-Agent Workspace  
**Concept:** A personal AI operating system that helps one human owner coordinate learning, software projects, research, business experiments, and personal execution through specialized AI agents.

The workspace is a modular system of:
- Human-controlled objectives and approvals
- An orchestrator that decomposes and routes tasks
- Specialist agents with bounded responsibilities
- Reusable skills and workflows
- Project-specific context and a curated knowledge base
- Tools and runtime integrations added incrementally

## 2. Owner and operating context

The owner is an Information Technology university student and independent builder. The workspace should support both academic and practical outcomes.

Relevant ongoing or recurring work areas include:
- Software engineering and system design
- FDE-related learning and applied AI development
- Data analysis and technical coursework
- The World of Knights & Demons, a personal MMORPG project
- WinterArc and other personal software products
- Business and monetization experiments
- Personal planning and performance review

Treat this list as a starting index, not as a complete or permanently fixed list. Confirm current project status from project-specific documents before making assumptions.

## 3. Mission

Help the owner convert goals and ideas into verified, maintainable outputs while reducing coordination overhead.

The workspace should:
1. Understand the owner's goal and constraints.
2. Identify the relevant project and retrieve its context.
3. Break work into appropriately sized tasks.
4. Select the smallest sufficient set of agents and skills.
5. Use tools only within granted permissions.
6. Verify results and distinguish completed work from proposals.
7. Preserve important decisions and reusable knowledge.
8. Present clear options, risks, costs, and next actions.

## 4. Success criteria

The workspace is useful when it demonstrably:
- Reduces time spent organizing and repeating context.
- Produces outputs that can be checked and reused.
- Keeps project information separate and current.
- Makes task ownership and status visible.
- Uses AI models and tools at a reasonable cost.
- Requires human approval for consequential external actions.
- Supports multiple AI clients without duplicating the canonical skill content.

Do not use agent count, token volume, or apparent autonomy as primary success metrics.

## 5. Scope

### In scope
- Personal task intake, planning, and delegation
- Research and source verification
- Software design, implementation assistance, and code review
- Learning plans, explanations, exercises, and feedback
- Data analysis support
- Business and market analysis
- Project documentation and decision tracking
- Knowledge retrieval and maintenance
- Tool integrations with explicit permissions

### Out of scope for the initial version
- Unsupervised financial transactions
- Autonomous public posting or messaging
- Unrestricted access to the owner's computer or accounts
- Automatic deployment to production
- A complex multi-agent runtime before workflows are validated
- Replacing the source repositories or project management systems of individual products

## 6. Design principles

1. **Human ownership:** The owner defines goals and retains final authority.
2. **Modularity:** Agents, skills, workflows, models, and tools are separable.
3. **Smallest sufficient system:** Use one agent for simple tasks; use multiple agents only when specialization or independent review adds value.
4. **Context before action:** Read relevant global and project context before executing.
5. **Evidence over confidence:** Mark facts, assumptions, estimates, and opinions distinctly.
6. **Verify before claiming:** Never claim an action, test, or external change succeeded unless verified.
7. **Least privilege:** Give each agent only the data and tools required for its task.
8. **Cost awareness:** Choose model capability according to task complexity and measured quality.
9. **Reversibility:** Prefer drafts, branches, backups, and reversible changes.
10. **Maintainability:** Prefer clear, documented, extensible solutions over quick but fragile fixes.

## 7. System architecture

The conceptual architecture has six layers:

1. **Human interface:** Request intake, status, review, and approval.
2. **Orchestration:** Intent classification, planning, routing, task state, and coordination.
3. **Agent system:** Specialist roles such as research, engineering, education, business, data analysis, project management, knowledge management, and QA.
4. **Skills and tools:** Reusable instructions, APIs, local tools, and integrations.
5. **Knowledge and memory:** Global context, project context, task records, and decision history.
6. **Execution infrastructure:** Windows environment, Git, runtime, databases, and optional cloud services.

The initial repository implements the instruction and configuration foundation. It is not itself a running agent runtime.

## 8. Initial agent set

The first implementation should start with five agents:
- Orchestrator
- Research
- Engineering
- Knowledge Manager
- QA & Auditor

Add Education, Business, Data Analyst, and Project Manager agents after the core workflow is reliable. These later roles may initially be handled as skills attached to an existing agent.

## 9. Canonical source of truth

- Global operating principles: `PROJECT_CONTEXT.md` and `AGENTS.md`
- Agent roster: `config/agent-registry.yaml`
- Permissions: `config/permissions.yaml`
- Model selection policy: `config/model-routing.yaml`
- Agent role definitions: `agents/`
- Reusable skill definitions: `skills/`
- Project-specific facts: `projects/<project>/`
- Important decisions: each project’s `DECISIONS.md` or the workspace decision log when global

If two documents conflict, do not silently choose one. Identify the conflict, prefer the newest explicitly approved decision, and ask the owner if approval status is unclear.

## 10. Project context loading protocol

Before doing project work:
1. Identify the project from the request.
2. Read its `PROJECT_CONTEXT.md` and relevant current task/decision documents.
3. Check document dates and status.
4. Separate confirmed facts from assumptions.
5. Ask one focused question only if a missing detail blocks safe or useful execution.
6. Do not copy project-specific details into global memory unless they are genuinely cross-project.

## 11. Delivery standard

Every substantial task should produce:
- A clear objective
- Scope and assumptions
- Actions actually performed
- Results and evidence
- Known issues or unverified items
- Recommended next action
- Status: `completed`, `partial`, or `blocked`

## 12. Initial roadmap

- Phase 1: Repository, context, rules, registry, and core skills.
- Phase 2: Validate the five core agents in manual or AI-client workflows.
- Phase 3: Build a minimal Python runtime and task persistence.
- Phase 4: Add specialist roles and integrations based on demonstrated need.
- Phase 5: Add a dashboard and monitoring if the CLI/API workflow proves useful.

## 13. Open decisions

The following are intentionally not hard-coded yet:
- Primary AI provider and model lineup
- Exact AI client integration format
- Whether orchestration will use LangGraph or a simpler custom state machine
- Persistent database choice beyond an initial local prototype
- Web dashboard framework
- Cloud deployment and hosting
- Monthly AI budget

Resolve these through small experiments and record approved decisions. Do not treat suggested technologies as final commitments.
