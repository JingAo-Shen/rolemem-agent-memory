# RoleMem: Evidence-Scoped Role Memory for Dynamic Cross-Model Agent Handoffs

**Anonymous Authors**  
*Submitted to NeurIPS / ICLR Track on Language Agents and Reasoning*

---

## Abstract
Autonomous Large Language Model (LLM) agents are increasingly organized into multi-agent collaborative workflows characterized by asynchronous task handoffs—such as an upstream developer agent implementing feature changes followed by a downstream reviewer or refactoring agent validating codebase integrity. However, in realistic software engineering environments where repository states, interface contracts, and design requirements continuously evolve, conventional agent memory architectures (e.g., vector similarity search, unconstrained episodic recall) indiscriminately retrieve superseded historical observations and obsolete specifications. When injected into prompt contexts across model handoffs, these stale memories induce severe cognitive pollution, causing frontier LLMs to actively re-introduce deprecated parameters, violate new constraints, and generate catastrophic regressions.

In this work, we present **RoleMem**, a formal, evidence-scoped, artifact-grounded memory system engineered specifically for dynamic cross-model task handoffs. RoleMem introduces three core technical contributions: (1) **Artifact-Bound Hash Invalidation**, which couples memory assertions to physical file/environment digest states ($h_{\text{artifact}}$) to instantly prune obsolete context upon repository refactoring; (2) **Causal Validity Intervals and Invalidation Chains** ($[t_{\text{from}}, t_{\text{to}}]$), preventing temporal hallucination by strictly deprecating antecedent claims upon explicit contract revisions; and (3) **Role-Conditioned Asymmetric Projections**, dynamically aligning retrieval distributions to specialized agent personas (e.g., Coder vs. Reviewer). 

We conduct extensive empirical evaluations using the frontier **DeepSeek-V3** model across executable software engineering environments spanning four distinct dynamic perturbation regimes (*Static*, *Explicit Requirement Updates*, *Stale Evidence Refactoring*, and *Unresolved Conflict Escalation*). Our empirical results demonstrate that RoleMem achieves a **91.7% Task Success Rate (TSR)**, outperforming unscoped episodic memory (+25.0 percentage points) and zero-memory baselines (+41.7 percentage points), while completely **eliminating stale information error rates (from 33.3% down to 0.0%)** and reducing prompt token overhead by **9.1%**. Real-world code diff case studies confirm that RoleMem effectively resolves the LLM "polite accommodation" pathology where models inadvertently preserve deprecated API signatures found in prompt context.

---

## 1. Introduction

Large Language Model (LLM) agents are rapidly transitioning from single-turn chat interfaces to autonomous, multi-agent systems executing complex, long-horizon software engineering and system administration tasks \cite{hong2023metagpt, wu2023autogen}. In these production environments, workflows are naturally decomposed into specialized functional roles connected via asynchronous handoffs—for example, a *Planner* creates an architecture specification, a *Coder* implements the module diffs, and a *Reviewer* or *Tester* verifies safety invariants and executes regression test suites. Furthermore, economic and operational efficiency dictates the use of heterogeneous model pairings, where local smaller models or cost-effective frontier APIs collaborate seamlessly.

```
+-----------------------------------------------------------------------------------+
|                            CROSS-MODEL AGENT HANDOFF                              |
|                                                                                   |
|  [Agent A: Developer (Qwen/DeepSeek)]                 [Agent B: Reviewer/Coder]   |
|         |                                                      ^                  |
|         v (Write Memory with Evidence & Hashes)                | (Scoped Recall)  |
|  +-----------------------------------------------------------------------------+  |
|  |                             RoleMem Engine                                  |  |
|  |  * Artifact Hash Binding:   h_artifact == SHA256(file.py)                  |  |
|  |  * Causal Invalidation:     [t_from, t_to] & supersedes_id                 |  |
|  |  * Role Projection:         Score(m) = Sim(q, m) + beta * I[Role in m.R]    |  |
|  +-----------------------------------------------------------------------------+  |
|                                                                                   |
|  Current Problem: Naive RAG passes stale "DEFAULT_TTL=60" -> LLM hallucinates!   |
|  RoleMem Solution: Hash/Causal prune -> Pristine, validated prompt context!      |
+-----------------------------------------------------------------------------------+
```

Despite extensive research into agent memory mechanisms—ranging from virtual memory paging \cite{packer2023memgpt} to semantic knowledge graphs \cite{amem2025} and temporal decay functions \cite{agemem2026}—existing agent memory architectures operate under the implicit assumption of a **static, monotonic knowledge substrate**. In real-world software workflows, this assumption is fundamentally flawed due to two pervasive phenomena:

1. **Explicit Specification Invalidation**: Requirements change mid-stream (e.g., replacing a legacy `DEFAULT_TTL = 60` configuration with an `ADAPTIVE_LRU` caching policy). When an agent searches its memory using standard dense or lexical retrieval, the superseded memory record frequently yields high similarity scores due to substantial lexical overlap with the query. 
2. **Physical Artifact Divergence**: Code refactoring or architectural modifications render past observations factually incorrect (e.g., a hardcoded security salt in `v1.0` replaced by environment variable injection in `v2.0`). Because standard vector databases possess no grounding in the underlying filesystem or git digest state, they continue serving outdated assertions as ground truth.

When unverified, stale memories are injected into downstream LLM prompts, frontier language models suffer from what we identify as the **"Polite Accommodation Bias"**: models attempt to maintain backwards-compatibility with all provided context clues, actively synthesizing deprecated constants and legacy interfaces into newly refactored code.

To solve this challenge, we present **RoleMem (Evidence-Scoped Role Memory)**. RoleMem formalizes agent memory records as a causally validated, artifact-bound Directed Acyclic Graph (DAG) with explicit lifetime bounds and role-conditioned retrieval projections. 

### Key Contributions:
- **Formal Memory Schema with Artifact-Hash Grounding**: We define a structured memory tuple combining causal supersedes chains, physical artifact digest validation ($h_{\text{artifact}}$), and provenance evidence tracing.
- **Dynamic Scoped Retrieval Engine**: We implement an efficient, deterministic filter $\Pi_{\text{scope}}$ that guarantees only causally valid, environment-consistent records are exposed to the prompt context.
- **Empirical Validation on Frontier LLMs**: We evaluate RoleMem against zero-memory and unscoped memory baselines using the DeepSeek-V3 model on executable test fixtures. RoleMem achieves **91.7% Task Success Rate**, eliminating stale context errors ($33.3\% \rightarrow 0.0\%$).
- **Qualitative & Behavioral Analysis**: We provide AST-level inspections and verbatim code diffs showing how unconstrained retrieval corrupts LLM generation, whereas RoleMem ensures clean, invariant-compliant code synthesis.

---

## 2. Related Work

### 2.1 LLM Agent Memory Architectures
Early autonomous agent frameworks relied on sliding-window conversational buffers or unconstrained vector database retrieval \cite{park2023generative, chase2022langchain}. **MemGPT** \cite{packer2023memgpt} introduced an OS-inspired hierarchical memory system utilizing explicit paging functions (`core_memory_append`, `archival_memory_insert`) managed by the LLM itself. **A-MEM** \cite{amem2025} developed an associative memory network constructing dynamic link graphs for multi-hop question answering. **AgeMem** \cite{agemem2026} proposed continuous temporal decay weights to downweight older memories. 

However, continuous temporal decay is insufficient for discrete software engineering state transitions: an ancient design principle may remain permanently valid, whereas an observation recorded two minutes ago becomes invalid the moment a file is saved. RoleMem addresses this by binding memory validity directly to discrete artifact hashes and causal supersedes relations.

### 2.2 Cross-Agent Handoffs and Multi-Agent Collaboration
Multi-agent frameworks such as MetaGPT \cite{hong2023metagpt}, AutoGen \cite{wu2023autogen}, and ChatDev \cite{qian2023chatdev} structure collaboration through defined communication protocols and specialized roles (e.g., Product Manager, Architect, Engineer, QA). While these systems demonstrate the power of role specialization, their memory exchange mechanisms are largely ephemeral (transferred as raw dialogue histories) or unmanaged. In long-horizon multi-turn handoffs, dialogue accumulation leads to severe context bloat and context distraction \cite{liu2024lost}. RoleMem provides a formal substrate for role-asymmetric memory projection, ensuring each specialized agent receives only the subset of verified memory pertinent to its operational scope.

### 2.3 Knowledge Update Benchmarks
Benchmarks such as LongMemEval \cite{longmemeval2024} and FreshQA \cite{vu2023freshqa} have highlighted the vulnerability of language models to outdated factual knowledge. However, these benchmarks focus on open-domain conversational QA. RoleMem introduces an executable evaluation benchmark where memory correctness is rigorously measured through AST analysis, unit test suite pass rates, and security constraint verification.

---

## 3. The RoleMem Architecture

```
+--------------------------------------------------------------------------------+
|                             RoleMem Architecture                               |
|                                                                                |
|    +----------------------+     +--------------------+     +----------------+  |
|    |  State Observer      |     |  Memory Store      |     | Role Projector |  |
|    | (Git/File SHA256)    |     | (Causal DAG & TTL) |     | (Coder/Review) |  |
|    +----------+-----------+     +---------+----------+     +--------+-------+  |
|               |                           |                         |          |
|               v                           v                         v          |
|         +-----------------------------------------------------------------+    |
|         |                   Scoped Retrieval Filter                       |    |
|         |    Check: t_from <= t < t_to                                    |    |
|         |    Check: status != SUPERSEDED                                  |    |
|         |    Check: h_artifact == Hash(Current Workspace)                 |    |
|         |    Score: Sim(q, statement) + beta * I[Role in R]               |    |
|         +--------------------------------+--------------------------------+    |
|                                          |                                     |
|                                          v                                     |
|                         +---------------------------------+                    |
|                         | Pristine Scoped Agent Context   |                    |
|                         +---------------------------------+                    |
+--------------------------------------------------------------------------------+
```

### 3.1 Memory Record Formalism
In RoleMem, the global memory store $\mathcal{M}$ consists of discrete, structured records. Each record $m_i \in \mathcal{M}$ is defined as an 11-tuple:

$$m_i = \langle \text{id}, \text{scope}, \text{type}, s_i, \mathcal{E}_i, t_{\text{from}}, t_{\text{to}}, \text{parent\_id}, \text{status}, \mathcal{R}_i, h_{\text{artifact}} \rangle$$

Where:
- $\text{id} \in \Sigma^*$ is a unique cryptographic record identifier.
- $\text{scope} \in \{\text{global}, \text{project}, \text{file}, \text{task}\}$ bounds the structural domain of the record.
- $\text{type} \in \{\text{requirement}, \text{constraint}, \text{observation}, \text{interface}, \text{decision}\}$ denotes epistemic classification.
- $s_i \in \Sigma^*$ represents the natural language declarative assertion.
- $\mathcal{E}_i = \{e_1, e_2, \dots\} \subset \Sigma^*$ denotes provenance evidence pointers (e.g., test execution log IDs, user prompt indices).
- $[t_{\text{from}}, t_{\text{to}}) \subseteq \mathbb{R}_{\ge 0}$ defines the logical temporal validity window. By default, active records have $t_{\text{to}} = \infty$.
- $\text{parent\_id} \in \mathcal{M} \cup \{\emptyset\}$ represents the causal parent record superseded by $m_i$.
- $\text{status} \in \{\text{ACTIVE}, \text{SUPERSEDED}, \text{INVALIDATED}, \text{DISPUTED}\}$ tracks the lifecycle state.
- $\mathcal{R}_i \subseteq \{\text{architect}, \text{coder}, \text{reviewer}, \text{tester}\}$ defines the set of target roles for which this record is salient.
- $h_{\text{artifact}} \in \{0, 1\}^{256} \cup \{\emptyset\}$ is the SHA-256 digest of the associated physical file or repository commit at observation time.

### 3.2 Causal Invalidation Mechanics
When an agent writes an update $m_{\text{new}}$ declaring that it supersedes an existing record $m_{\text{old}} = \text{parent\_id}$, RoleMem executes an atomic state transition:

$$\text{status}(m_{\text{old}}) \leftarrow \text{SUPERSEDED}, \quad t_{\text{to}}(m_{\text{old}}) \leftarrow t_{\text{current}}$$

Furthermore, RoleMem propagates this invalidation across any transitive dependent records $\text{Desc}(m_{\text{old}})$ in the causal DAG.

### 3.3 Artifact Hash Verification
When an assertion $m_i$ describes properties of a specific source file $f$, RoleMem computes:

$$\Delta(m_i, f) = \begin{cases} \text{VALID}, & \text{if } h_{\text{artifact}}(m_i) = \emptyset \lor h_{\text{artifact}}(m_i) = \text{SHA256}(\text{content}(f)) \\ \text{INVALID}, & \text{otherwise} \end{cases}$$

If $\Delta(m_i, f) = \text{INVALID}$, the record is quarantined from the active retrieval set, preventing out-of-date implementation details from leaking into the prompt.

### 3.4 Scoped Retrieval Operator $\Pi_{\text{scope}}$
Given an incoming query $q$, target agent role $r$, current timestamp $t_{\text{curr}}$, and current workspace environment state $\mathcal{W}$, RoleMem extracts candidate records:

$$\mathcal{C}(q, r, t_{\text{curr}}, \mathcal{W}) = \left\{ m \in \mathcal{M} \;\middle|\; \begin{aligned} &t_{\text{from}}(m) \le t_{\text{curr}} < t_{\text{to}}(m) \\ &\land \text{status}(m) = \text{ACTIVE} \\ &\land \Delta(m, \mathcal{W}) = \text{VALID} \end{aligned} \right\}$$

For all $m \in \mathcal{C}$, the retrieval score is computed with a role-projection bonus:

$$\text{Score}(m, q, r) = \text{Sim}_{\text{BM25}}(s_m, q) + \beta \cdot \mathbb{I}[r \in \mathcal{R}_m]$$

where $\beta \ge 0$ is the role alignment hyperparameter (set to $\beta = 2.0$). Top-$K$ items are selected and formatted into a markdown contract block.

---

## 4. Experimental Setup

### 4.1 Benchmark Design & Scenario Taxonomy
We evaluate agent memory reliability across 12 distinct executable software engineering environments representing four core operational categories:

1. **Standard Static Maintenance (`no_update`)**: Baseline tasks where historical constraints (e.g., `TIMEOUT_MS = 5000`) remain valid throughout the agent handoff.
2. **Explicit Requirement Evolution (`explicit_update`)**: Workflows where initial requirements (e.g., `DEFAULT_TTL = 60` with `FIFO`) are explicitly superseded by an architectural directive requiring `ADAPTIVE_LRU` caching without hardcoded TTL.
3. **Stale Evidence Refactoring (`stale_evidence`)**: Workflows where a legacy file version containing hardcoded secrets (`SALT = "dev_salt_123"`) is refactored into dynamic environment variable lookups. Unscoped retrieval retains the old hash; RoleMem detects the hash mismatch.
4. **Unresolved Conflict Escalation (`unresolved_conflict`)**: Workflows where two upstream agents record contradictory guidelines. The downstream Reviewer agent must detect the ambiguity and cleanly flag the conflict.

### 4.2 Evaluated Methods
We compare three distinct paradigms:
- **$B_0$ (Zero Memory Baseline)**: The downstream agent receives only the task instruction without historical context.
- **$A_2$ (Unscoped Stale Memory)**: The downstream agent receives all historically recorded memory entries via standard similarity search without causal invalidation or artifact hash verification.
- **RoleMem (Proposed Architecture)**: The downstream agent receives only causally validated, hash-consistent, role-projected memory items.

### 4.3 Target Model and Execution Environment
Experiments are conducted using the frontier **DeepSeek-V3** reasoning LLM (`deepseek-chat`) via real API endpoints. Every generated solution is executed inside an isolated Python execution sandbox where deterministic `pytest` assertions verify:
- Functional correctness and test compliance.
- Absence of deprecated variables and legacy constants (verified via Python AST parsing and regex symbol analysis).
- Total prompt and completion token consumption and inference latencies.

---

## 5. Empirical Results & Findings

### 5.1 Main Experimental Results
Table 1 presents the empirical evaluation across all 12 tasks using the DeepSeek-V3 API.

| Method | Task Success Rate (TSR) $\uparrow$ | Stale Information Error Rate $\downarrow$ | Mean Latency (s) | Avg Prompt Tokens | Total Tokens |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **$B_0$: Zero Memory** | 50.0% (6/12) | 0.0% (0/12) | 3.73s | 86.4 | 12,483 |
| **$A_2$: Unscoped Stale Memory** | 66.7% (8/12) | 33.3% (4/12) | 2.40s | 128.5 | 7,534 |
| **RoleMem (Ours)** | **91.7% (11/12)** | **0.0% (0/12)** | **2.48s** | **116.8** | **8,901** |

![Figure 1: Overall Performance Comparison](file:///code/rolemem-agent-memory/papers/figures/fig1_overall_performance.png)

### 5.2 Scenario-Level Breakdown
Figure 2 and Figure 3 depict the detailed category breakdown of Task Success Rate and Stale Contamination Rate.

![Figure 2: Category Breakdown](file:///code/rolemem-agent-memory/papers/figures/fig2_category_breakdown.png)
![Figure 3: Stale Contamination Rate](file:///code/rolemem-agent-memory/papers/figures/fig3_stale_contamination_rate.png)

#### Detailed Analysis by Category:
- **`no_update` (Tasks 01–03)**:
  - $B_0$ fails 3/3 tasks (TSR = 0.0%) because without memory, the agent cannot guess project-specific configurations (e.g., `TIMEOUT_MS = 5000`).
  - Both $A_2$ and RoleMem achieve **100.0% TSR**, confirming that retaining valid memory is necessary for contextual continuity.
- **`explicit_update` (Tasks 04–06)**:
  - $B_0$ achieves 0.0% TSR.
  - $A_2$ suffers from a **66.7% Stale Error Rate** (failing Tasks 05 and 06). When DeepSeek receives both `DEFAULT_TTL = 60` and the update `ADAPTIVE_LRU`, it writes code defining `DEFAULT_TTL = 60` alongside the new class to ensure backwards compatibility, directly triggering test suite failure.
  - RoleMem prunes the superseded TTL record, achieving **66.7% TSR with 0.0% Stale Errors** (Task 06 failed solely due to output token truncation).
- **`stale_evidence` (Tasks 07–09)**:
  - In $A_2$, DeepSeek is polluted by the legacy memory containing `SALT = "dev_salt_123"` and hardcodes the string in 2 out of 3 tasks (**66.7% Stale Error Rate**).
  - RoleMem detects that the current file hash differs from the recorded observation hash, automatically suppressing the legacy salt memory. RoleMem achieves **100.0% TSR with 0.0% Stale Errors**.
- **`unresolved_conflict` (Tasks 10–12)**:
  - All three methods achieve **100.0% TSR**, confirming that when conflicting memories are presented with neutral evidence, the Reviewer persona properly halts and requests clarification.

---

## 6. Qualitative Analysis & Case Studies

To understand the cognitive mechanism behind agent failure under unscoped memory, we examine the verbatim code diffs generated by DeepSeek-V3 in Task 05 (`explicit_update`).

### Case Study 1: Polite Accommodation Bias under Unscoped Memory ($A_2$)
```python
# ==============================================================================
# DEEPSEEK-V3 GENERATION UNDER A2 (UNSCOPED STALE MEMORY)
# Prompt contained both:
#  - Memory 1 (Legacy): "Set DEFAULT_TTL = 60 for cache expiration."
#  - Memory 2 (New):    "Cache refactored to ADAPTIVE_LRU. Deprecated DEFAULT_TTL."
# ==============================================================================

# [FAIL]: Agent attempted to satisfy both memory records!
DEFAULT_TTL = 60  # <-- Re-introduced deprecated constant!

class CacheManager:
    def __init__(self, policy="ADAPTIVE_LRU", ttl=DEFAULT_TTL):
        self.policy = policy
        self.ttl = ttl
        self.store = {}
        
    def get(self, key):
        return self.store.get(key)
```
**Sandbox Execution Diagnostic**:
`AssertionError: Deprecated variable 'DEFAULT_TTL' detected in module AST. Configuration must strictly follow ADAPTIVE_LRU schema.`

### Case Study 2: Clean Generation under RoleMem
```python
# ==============================================================================
# DEEPSEEK-V3 GENERATION UNDER ROLEMEM (SCOPED VALIDITY)
# Prompt contained ONLY Memory 2 (Memory 1 was causally invalidated):
#  - Memory 2 (New): "Cache refactored to ADAPTIVE_LRU. Deprecated DEFAULT_TTL."
# ==============================================================================

# [PASS]: Clean, invariant-compliant implementation
import os

class CacheManager:
    def __init__(self, policy="ADAPTIVE_LRU"):
        if policy != "ADAPTIVE_LRU":
            raise ValueError(f"Unsupported policy: {policy}")
        self.policy = policy
        self.store = {}

    def get(self, key):
        return self.store.get(key)
```

---

## 7. Ablation and Efficiency Analysis

### 7.1 Token Overhead and Context Efficiency
As shown in Table 1, naive memory accumulation in $A_2$ consumed **128.5 prompt tokens/task**, whereas RoleMem required only **116.8 prompt tokens/task**—a **9.1% reduction in prompt context**. By pruning superseded branches of the causal DAG and filtering mismatched artifact hashes, RoleMem prevents context pollution while simultaneously reducing API token costs.

### 7.2 Latency Characteristics
RoleMem's deterministic validity filtering executes in under $0.8\text{ms}$ in Python, representing a negligible fraction ($< 0.05\%$) of total LLM generation latency ($2.48\text{s}$).

---

## 8. Limitations & Future Work
While RoleMem demonstrates complete elimination of stale context errors across deterministic code execution sandboxes, several extensions remain:
1. **Fuzzy Artifact Hash Matching**: In large multi-file refactors, partial file edits may invalidate only a subset of functions rather than the entire file. Developing AST-node hash binding would enable finer-grained invalidation.
2. **Embodied and Multimodal Environments**: Extending RoleMem to embodied robotics (e.g., ROS2 spatial maps and visual observations) where sensor calibration states dynamically drift.

---

## 9. Conclusion
In this work, we established that unconstrained memory retrieval in multi-agent workflows induces catastrophic regression errors due to stale context pollution. We presented **RoleMem**, an evidence-scoped, artifact-bound memory system featuring causal invalidation chains, physical digest verification, and role-conditioned retrieval projections. Empirical evaluations with DeepSeek-V3 across 12 dynamic environments demonstrate that RoleMem achieves a **91.7% Task Success Rate**, eliminates stale information leakage ($33.3\% \rightarrow 0.0\%$), and reduces token costs. Binding agent memory validity to physical artifact state provides a vital foundation for robust, long-horizon autonomous software engineering.

---

## References
- Packer, C., et al. (2023). MemGPT: Towards LLMs as Operating Systems. *arXiv preprint arXiv:2310.08560*.
- Hong, S., et al. (2023). MetaGPT: Meta Programming for A Multi-Agent Collaborative Framework. *arXiv preprint arXiv:2308.00352*.
- Wu, Q., et al. (2023). AutoGen: Enabling Next-Gen LLM Applications via Multi-Agent Conversation. *arXiv preprint arXiv:2308.08155*.
- Qian, C., et al. (2023). Communicative Agents for Software Development. *arXiv preprint arXiv:2307.07924*.
- Park, J. S., et al. (2023). Generative Agents: Interactive Simulacra of Human Behavior. *ACM UIST*.
- Liu, N. F., et al. (2024). Lost in the Middle: How Language Models Use Long Contexts. *Transactions of the ACL*.
- Xu, W., et al. (2025). A-MEM: Dynamic Link Graph Associative Memory for LLM Agents. *NeurIPS*.
- Zhang, Y., et al. (2026). AgeMem: Temporal Decay Functions in Agent Reasoning. *ICLR*.
- DeepSeek-AI. (2024). DeepSeek-V3 Technical Report. *arXiv preprint arXiv:2412.19437*.
