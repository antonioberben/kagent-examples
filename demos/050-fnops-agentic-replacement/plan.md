# FinOps → Kagent Agents, MCPs & Skills — Replacement Plan

## Block 1: FinOps Features That Can Be Replaced by Agents

The following FinOps platform capabilities can be decomposed into autonomous agent tasks, MCP server integrations, and reusable skills. Each feature is tagged with a **replacement complexity** (🟢 Easy, 🟡 Medium, 🔴 Hard) and the **agent architecture** that would replace it.

---

### 1. Cost Visibility & Monitoring

| # | Feature | Description | Complexity | Agent Architecture |
|---|---------|-------------|------------|-------------------|
| 1.1 | **Real-Time Cost Monitoring** | Query cloud billing APIs on a schedule or on-demand and surface current spend | 🟢 | Agent + Cloud Provider MCPs (AWS/GCP/Azure billing APIs) |
| 1.2 | **Multi-Cloud Cost Consolidation** | Aggregate billing data from AWS, Azure, GCP into a unified view | 🟡 | Orchestrator Agent + per-cloud MCP servers + normalization skill |
| 1.3 | **Granular Cost Breakdown** | Break costs down by service, region, account, resource type | 🟢 | Agent + Cloud Provider MCPs with query parameters |
| 1.4 | **Historical Cost Analysis** | Retrieve and analyze spending trends over configurable time windows | 🟢 | Agent + time-series query skill + storage MCP |
| 1.5 | **Cost Explorer / Ad-Hoc Queries** | Natural-language interface to slice-and-dice cost data | 🟢 | LLM Agent (native capability) + Cloud MCPs |

### 2. Cost Allocation & Tagging

| # | Feature | Description | Complexity | Agent Architecture |
|---|---------|-------------|------------|-------------------|
| 2.1 | **Tag-Based Cost Allocation** | Allocate costs to teams/projects/departments using resource tags | 🟢 | Agent + Cloud tagging APIs via MCP |
| 2.2 | **Tag Compliance Auditing** | Scan resources for missing/non-compliant tags and report violations | 🟢 | Scheduled Agent + Cloud resource MCPs + policy skill |
| 2.3 | **Auto-Tagging Suggestions** | Use heuristics/AI to suggest tags for untagged resources | 🟡 | LLM Agent + resource metadata MCP + naming-convention skill |
| 2.4 | **Shared Cost Distribution** | Split shared infrastructure costs across teams (proportional, even, fixed) | 🟡 | Agent + allocation-rules skill + cost data MCP |
| 2.5 | **Kubernetes Cost Allocation** | Allocate K8s costs by namespace, deployment, pod, label | 🟡 | Agent + Kubernetes MCP (OpenCost/Kubecost API) |

### 3. Budgeting & Forecasting

| # | Feature | Description | Complexity | Agent Architecture |
|---|---------|-------------|------------|-------------------|
| 3.1 | **Budget Creation & Tracking** | Define budgets per team/project/account and track spend vs. budget | 🟢 | Agent + budget-store skill + Cloud billing MCP |
| 3.2 | **Budget Threshold Alerts** | Fire alerts when spend approaches or exceeds budget thresholds | 🟢 | Scheduled Agent + notification MCP (Slack/Teams/email) |
| 3.3 | **Cost Forecasting** | Predict future spend using historical trends and growth rates | 🟡 | Agent + forecasting skill (time-series model) + cost data MCP |
| 3.4 | **Scenario / What-If Modeling** | Model cost impact of architectural changes, growth, or migration | 🟡 | LLM Agent + pricing APIs MCP + simulation skill |
| 3.5 | **Forecast Variance Analysis** | Compare forecasted vs. actual spend and explain deviations | 🟡 | Agent + analytics skill + cost data MCP |

### 4. Anomaly Detection & Alerting

| # | Feature | Description | Complexity | Agent Architecture |
|---|---------|-------------|------------|-------------------|
| 4.1 | **Spending Anomaly Detection** | Detect unusual cost spikes or drops using statistical/ML methods | 🟡 | Scheduled Agent + anomaly-detection skill + cost data MCP |
| 4.2 | **Real-Time Spike Alerts** | Immediately notify teams of sudden cost increases | 🟢 | Event-driven Agent + notification MCP (Slack/PagerDuty) |
| 4.3 | **Alert Routing by Ownership** | Route anomaly alerts to the team that owns the affected resource | 🟢 | Agent + ownership-mapping skill + notification MCP |
| 4.4 | **Custom Alert Thresholds** | Allow per-service or per-team configurable thresholds | 🟢 | Agent + config-store skill |

### 5. Optimization Recommendations

| # | Feature | Description | Complexity | Agent Architecture |
|---|---------|-------------|------------|-------------------|
| 5.1 | **Rightsizing Recommendations** | Identify overprovisioned instances and suggest optimal sizes | 🟡 | Agent + CloudWatch/Monitoring MCP + rightsizing skill |
| 5.2 | **Idle Resource Detection** | Find stopped instances, unattached volumes, unused LBs, idle IPs | 🟢 | Scheduled Agent + Cloud resource MCPs + waste-detection skill |
| 5.3 | **Orphaned Resource Cleanup** | Detect and (optionally) remove orphaned snapshots, volumes, IPs | 🟡 | Agent + Cloud resource MCPs + cleanup skill (with approval gate) |
| 5.4 | **Storage Tier Optimization** | Recommend moving data to cheaper storage classes (S3 IA, Glacier, etc.) | 🟢 | Agent + storage-analysis skill + Cloud storage MCP |
| 5.5 | **Scheduling Non-Critical Workloads** | Shut down dev/test environments during off-hours | 🟡 | Scheduled Agent + Cloud compute MCP + schedule skill |
| 5.6 | **Network/Egress Cost Optimization** | Analyze data transfer patterns and suggest architectural improvements | 🔴 | Agent + network-flow MCP + egress-analysis skill |
| 5.7 | **Container Rightsizing** | Optimize K8s resource requests/limits based on actual usage | 🟡 | Agent + K8s metrics MCP + container-rightsizing skill |

### 6. Commitment & Rate Optimization

| # | Feature | Description | Complexity | Agent Architecture |
|---|---------|-------------|------------|-------------------|
| 6.1 | **RI/Savings Plan Coverage Analysis** | Analyze what % of usage is covered by commitments | 🟡 | Agent + Cloud billing MCP + coverage-analysis skill |
| 6.2 | **Commitment Purchase Recommendations** | Recommend optimal RI/SP purchases based on usage patterns | 🟡 | Agent + usage-analysis skill + pricing MCP |
| 6.3 | **Commitment Utilization Tracking** | Monitor whether purchased commitments are being fully used | 🟢 | Agent + Cloud billing MCP + utilization-tracking skill |
| 6.4 | **Expiration & Renewal Alerts** | Alert before commitments expire with renewal recommendations | 🟢 | Scheduled Agent + commitment-store skill + notification MCP |
| 6.5 | **Spot Instance Recommendations** | Identify workloads suitable for spot/preemptible instances | 🟡 | Agent + workload-analysis skill + spot-pricing MCP |

### 7. Reporting & Dashboards

| # | Feature | Description | Complexity | Agent Architecture |
|---|---------|-------------|------------|-------------------|
| 7.1 | **Scheduled Cost Reports** | Generate and email/Slack daily/weekly/monthly cost summaries | 🟢 | Scheduled Agent + report-generation skill + notification MCP |
| 7.2 | **Executive Summaries** | Natural-language summary of cost trends, anomalies, and savings | 🟢 | LLM Agent (native capability) + cost data MCP |
| 7.3 | **Team-Level Cost Reports** | Per-team breakdowns with optimization suggestions | 🟢 | Agent + allocation skill + report-generation skill |
| 7.4 | **Data Export (CSV/JSON/Parquet)** | Export cost data in standard formats for downstream systems | 🟢 | Agent + export skill + storage MCP |
| 7.5 | **Dashboard Generation** | Generate web dashboards or Grafana configs from cost data | 🟡 | Agent + dashboard-template skill + Grafana MCP |

### 8. Chargeback & Showback

| # | Feature | Description | Complexity | Agent Architecture |
|---|---------|-------------|------------|-------------------|
| 8.1 | **Showback Reports** | Informational cost reports showing each team's consumption | 🟢 | Agent + allocation skill + report-generation skill |
| 8.2 | **Automated Chargeback** | Generate actual billing entries or journal entries per team | 🟡 | Agent + financial-system MCP + chargeback skill |
| 8.3 | **100% Cost Allocation Enforcement** | Ensure every dollar is mapped to an owner | 🟡 | Agent + allocation-audit skill + notification MCP |

### 9. Unit Economics

| # | Feature | Description | Complexity | Agent Architecture |
|---|---------|-------------|------------|-------------------|
| 9.1 | **Cost-Per-Customer Calculation** | Calculate infrastructure cost per customer/tenant | 🟡 | Agent + business-metrics MCP + unit-economics skill |
| 9.2 | **Cost-Per-Transaction/API Call** | Calculate unit costs for specific operations | 🟡 | Agent + observability MCP + unit-economics skill |
| 9.3 | **COGS Attribution** | Map cloud costs to Cost of Goods Sold for margin analysis | 🟡 | Agent + financial-mapping skill + cost data MCP |
| 9.4 | **Revenue-to-Cost Correlation** | Correlate cloud spend with revenue metrics | 🟡 | Agent + business-metrics MCP + correlation skill |

### 10. Governance & Policy Enforcement

| # | Feature | Description | Complexity | Agent Architecture |
|---|---------|-------------|------------|-------------------|
| 10.1 | **Policy-Based Cost Guards** | Enforce rules like "no instance larger than X without approval" | 🟡 | Event-driven Agent + policy-engine skill + Cloud events MCP |
| 10.2 | **Tagging Policy Enforcement** | Block or flag resource creation without required tags | 🟡 | Agent + Cloud events MCP + policy skill |
| 10.3 | **Approval Workflows for Actions** | Require human approval before executing optimization actions | 🟡 | Agent + approval-gate skill + notification MCP |
| 10.4 | **Compliance Reporting** | Generate reports for auditors showing cost governance adherence | 🟢 | Agent + audit-trail skill + report-generation skill |

### 11. Sustainability & Carbon Tracking

| # | Feature | Description | Complexity | Agent Architecture |
|---|---------|-------------|------------|-------------------|
| 11.1 | **Carbon Emissions Estimation** | Estimate CO₂ from cloud usage using provider carbon APIs | 🟡 | Agent + carbon-data MCP (AWS Carbon Footprint, etc.) |
| 11.2 | **Green Region Recommendations** | Suggest lower-carbon regions for workload placement | 🟢 | Agent + carbon-intensity skill + region-data MCP |
| 11.3 | **Sustainability Reports** | Generate periodic sustainability/ESG reports | 🟢 | Agent + report-generation skill + carbon data |

### 12. Invoice & Billing Management

| # | Feature | Description | Complexity | Agent Architecture |
|---|---------|-------------|------------|-------------------|
| 12.1 | **Invoice Reconciliation** | Compare cloud invoices against internal allocation records | 🟡 | Agent + billing MCP + reconciliation skill |
| 12.2 | **Discount & Credit Tracking** | Track applied credits, EDPs, and promotional discounts | 🟢 | Agent + billing MCP + discount-tracking skill |
| 12.3 | **Billing Anomaly Detection** | Flag unexpected invoice line items or pricing changes | 🟡 | Agent + anomaly-detection skill + billing MCP |

### 13. Collaboration & Notifications

| # | Feature | Description | Complexity | Agent Architecture |
|---|---------|-------------|------------|-------------------|
| 13.1 | **Slack/Teams Cost Bot** | Interactive chatbot for cost queries in Slack or Teams | 🟢 | LLM Agent + Slack/Teams MCP + cost data MCP |
| 13.2 | **Jira/ServiceNow Ticket Creation** | Auto-create tickets for optimization opportunities | 🟢 | Agent + Jira/ServiceNow MCP + ticket-creation skill |
| 13.3 | **Cost Ownership Assignment** | Maintain and enforce a mapping of resources → owners | 🟢 | Agent + ownership-registry skill |
| 13.4 | **Weekly Digest to Stakeholders** | Send personalized cost digests to each team lead | 🟢 | Scheduled Agent + report-generation skill + notification MCP |

### 14. Benchmarking & Maturity

| # | Feature | Description | Complexity | Agent Architecture |
|---|---------|-------------|------------|-------------------|
| 14.1 | **Internal Team Benchmarking** | Compare cost efficiency across internal teams | 🟢 | Agent + benchmarking skill + cost data MCP |
| 14.2 | **FinOps Maturity Assessment** | Evaluate and track org's FinOps maturity (Crawl/Walk/Run) | 🟡 | LLM Agent + maturity-framework skill + survey MCP |
| 14.3 | **Best Practice Recommendations** | Suggest next steps to improve FinOps practice | 🟢 | LLM Agent (native capability) + context from other agents |

---

### Summary: Feature Count by Replacement Complexity

| Complexity | Count | Description |
|------------|-------|-------------|
| 🟢 Easy | **28** | Direct API queries, simple scheduling, report generation, LLM-native tasks |
| 🟡 Medium | **26** | Requires custom skills with business logic, multi-step orchestration, or ML models |
| 🔴 Hard | **1** | Deep network analysis requiring specialized tooling |

**Total: 55 replaceable features across 14 categories**

---

### Key MCP Servers Needed

| MCP Server | Purpose |
|------------|---------|
| `aws-billing-mcp` | AWS Cost Explorer, CUR, pricing APIs |
| `azure-billing-mcp` | Azure Cost Management, consumption APIs |
| `gcp-billing-mcp` | GCP Cloud Billing, BigQuery billing export |
| `kubernetes-mcp` | K8s API, OpenCost/Kubecost endpoints |
| `slack-mcp` | Slack messaging for alerts and reports |
| `teams-mcp` | MS Teams notifications |
| `jira-mcp` | Jira ticket creation and management |
| `grafana-mcp` | Dashboard creation and management |
| `pagerduty-mcp` | Incident alerting |
| `github-mcp` | IaC/Terraform PR integration |
| `storage-mcp` | Persist budgets, configs, historical data |

### Key Skills Needed

| Skill | Purpose |
|-------|---------|
| `cost-normalization` | Normalize billing formats across clouds |
| `anomaly-detection` | Statistical/ML anomaly detection on time-series cost data |
| `forecasting` | Time-series forecasting (Prophet, linear regression, etc.) |
| `rightsizing` | Match utilization metrics to optimal instance families |
| `report-generation` | Generate formatted reports (Markdown, HTML, PDF) |
| `policy-engine` | Evaluate resources against configurable policy rules |
| `unit-economics` | Calculate cost-per-unit business metrics |
| `allocation-rules` | Apply chargeback/showback allocation logic |
| `waste-detection` | Identify idle, orphaned, and underutilized resources |
| `budget-tracking` | Track spend against defined budgets with threshold logic |

---

---

## Block 2: Agent Topology & Orchestration Design

The system is composed of **specialized agents** that each own a domain, an **orchestrator agent** that coordinates cross-domain workflows, and **shared MCPs/skills** that agents compose together.

### 2.1 Architecture Overview

```
┌──────────────────────────────────────────────────────────────────────┐
│                        USER / TRIGGER LAYER                         │
│  (Slack bot, CLI, Cron schedule, Cloud event, API call, Chat UI)    │
└──────────────────────┬───────────────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────────────┐
│                     ORCHESTRATOR AGENT (kagent)                     │
│                                                                     │
│  • Routes requests to domain agents                                 │
│  • Composes multi-agent workflows (e.g. "full cost review")         │
│  • Maintains conversation context & session state                   │
│  • Enforces approval gates before destructive actions               │
│  • Aggregates results into unified responses                        │
└───┬──────┬──────┬──────┬──────┬──────┬──────┬──────┬────────────────┘
    │      │      │      │      │      │      │      │
    ▼      ▼      ▼      ▼      ▼      ▼      ▼      ▼
┌──────┐┌──────┐┌──────┐┌──────┐┌──────┐┌──────┐┌──────┐┌──────┐
│COST  ││ALLOC ││BUDGET││ANOMLY││OPTIM ││COMMIT││REPORT││GOVERN│
│VISIB ││& TAG ││& FCT ││DETECT││RECOM ││MGMT  ││& DASH││& POL │
│AGENT ││AGENT ││AGENT ││AGENT ││AGENT ││AGENT ││AGENT ││AGENT │
└──┬───┘└──┬───┘└──┬───┘└──┬───┘└──┬───┘└──┬───┘└──┬───┘└──┬───┘
   │       │       │       │       │       │       │       │
   └───────┴───────┴───────┴───────┴───────┴───────┴───────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────────────┐
│                     SHARED LAYER: MCPs + Skills                     │
│                                                                     │
│  MCPs:  aws-billing │ azure-billing │ gcp-billing │ kubernetes     │
│         slack       │ jira          │ grafana     │ pagerduty      │
│         github      │ storage       │ teams       │ email          │
│                                                                     │
│  Skills: cost-normalization │ anomaly-detection │ forecasting      │
│          rightsizing │ report-generation │ policy-engine            │
│          unit-economics │ allocation-rules │ waste-detection       │
│          budget-tracking │ approval-gate │ export                  │
└──────────────────────────────────────────────────────────────────────┘
```

### 2.2 Agent Definitions

| Agent | Trigger Model | Owns Features | Key MCPs | Key Skills |
|-------|--------------|---------------|----------|------------|
| **Cost Visibility Agent** | On-demand + Scheduled (hourly) | 1.1–1.5 | aws/azure/gcp-billing | cost-normalization |
| **Allocation & Tagging Agent** | Scheduled (daily) + On-demand | 2.1–2.5 | aws/azure/gcp-billing, kubernetes | allocation-rules |
| **Budget & Forecast Agent** | Scheduled (daily) + Event-driven | 3.1–3.5 | aws/azure/gcp-billing, slack | budget-tracking, forecasting |
| **Anomaly Detection Agent** | Scheduled (every 15 min) + Event-driven | 4.1–4.4 | aws/azure/gcp-billing, slack, pagerduty | anomaly-detection |
| **Optimization Agent** | Scheduled (daily) + On-demand | 5.1–5.7, 6.5 | aws/azure/gcp-billing, kubernetes | rightsizing, waste-detection |
| **Commitment Mgmt Agent** | Scheduled (weekly) + On-demand | 6.1–6.4 | aws/azure/gcp-billing | coverage-analysis |
| **Reporting & Dashboard Agent** | Scheduled (daily/weekly) + On-demand | 7.1–7.5, 8.1–8.3 | grafana, slack, email, storage | report-generation, export |
| **Governance & Policy Agent** | Event-driven (CloudTrail/Activity Log) | 10.1–10.4 | aws/azure/gcp events, jira | policy-engine, approval-gate |

**Supplemental Agents** (lower priority, Phase 3+):

| Agent | Owns Features |
|-------|---------------|
| **Unit Economics Agent** | 9.1–9.4 |
| **Sustainability Agent** | 11.1–11.3 |
| **Invoice Agent** | 12.1–12.3 |
| **Collaboration Agent** | 13.1–13.4 |
| **Benchmarking Agent** | 14.1–14.3 |

### 2.3 Orchestration Patterns

#### Pattern 1: Direct Query (single agent)
```
User: "What did we spend on AWS EC2 last month?"
  → Orchestrator routes to Cost Visibility Agent
  → Agent calls aws-billing-mcp → returns answer
```

#### Pattern 2: Multi-Agent Composition (fan-out/fan-in)
```
User: "Give me a full monthly cost review"
  → Orchestrator fans out to:
      ├─ Cost Visibility Agent     → total spend, breakdown
      ├─ Anomaly Detection Agent   → anomalies detected this month
      ├─ Optimization Agent        → savings opportunities found
      ├─ Commitment Mgmt Agent     → RI/SP coverage & utilization
      └─ Budget & Forecast Agent   → budget status & next month forecast
  → Orchestrator aggregates into unified report
  → Reporting Agent formats and delivers
```

#### Pattern 3: Event-Driven Chain (sequential)
```
CloudTrail Event: new EC2 instance launched
  → Governance Agent checks tagging policy
  → IF tags missing:
      → Governance Agent notifies via Slack
      → Governance Agent creates Jira ticket
      → Allocation Agent flags for next cost report
```

#### Pattern 4: Scheduled Pipeline (cron)
```
Daily 8:00 AM:
  → Cost Visibility Agent refreshes cost data
  → Anomaly Detection Agent scans for spikes
  → Budget Agent checks thresholds
  → IF anomaly or budget breach:
      → Notification via Slack/PagerDuty
  → Reporting Agent generates daily digest
  → Sends to all team leads
```

### 2.4 Inter-Agent Communication

| Mechanism | Use Case |
|-----------|----------|
| **Shared data store** (via storage-mcp) | Agents write results to a shared store; other agents read as needed |
| **Orchestrator message passing** | Orchestrator collects outputs and passes them as context to downstream agents |
| **Event bus** (CloudEvents / NATS) | Event-driven agents subscribe to topics and react asynchronously |
| **Direct agent invocation** | Orchestrator calls agents as sub-tasks with structured input/output contracts |

### 2.5 Human-in-the-Loop Gates

Certain actions **must** require human approval before execution:

| Action | Gate Type | Approval Channel |
|--------|-----------|-----------------|
| Delete/terminate any resource | Explicit approval | Slack interactive message / Jira ticket |
| Purchase RI/Savings Plan | Explicit approval | Email + Slack to FinOps lead |
| Apply auto-scaling changes | Configurable (auto/manual) | Slack notification with override window |
| Modify tags on production resources | Explicit approval | Jira ticket with change request |
| Execute chargeback journal entries | Explicit approval | Finance team Slack channel |

---

## Block 3: MCP Server Specifications

### 3.1 Cloud Billing MCPs

#### `aws-billing-mcp`
| Tool | Description | Input | Output |
|------|-------------|-------|--------|
| `get_cost_and_usage` | Query AWS Cost Explorer | time_period, granularity, filter, group_by | Cost results by dimension |
| `get_reservation_coverage` | RI/SP coverage data | time_period, filter | Coverage percentage & details |
| `get_reservation_utilization` | RI/SP utilization data | time_period, filter | Utilization percentage |
| `get_savings_plans_utilization` | Savings Plan usage | time_period | Utilization & savings |
| `describe_instances` | List EC2 instances with metadata | filters | Instance details, tags, type |
| `get_cost_forecast` | AWS native forecast | time_period, metric, granularity | Forecasted amounts |
| `list_unattached_volumes` | Find orphaned EBS volumes | filters | Volume IDs, sizes, costs |
| `get_cloudwatch_metrics` | CPU/Memory/Network metrics | instance_id, period, stat | Utilization time-series |

#### `azure-billing-mcp`
| Tool | Description |
|------|-------------|
| `query_usage_details` | Azure consumption/usage details by date range and scope |
| `get_budget_status` | Current budget spend and remaining amounts |
| `list_reservation_recommendations` | Azure RI purchase recommendations |
| `get_advisor_recommendations` | Azure Advisor cost recommendations |
| `list_resources_by_tag` | Query resources filtered by tags |
| `get_metrics` | Azure Monitor metrics for resource utilization |

#### `gcp-billing-mcp`
| Tool | Description |
|------|-------------|
| `query_billing_export` | Query BigQuery billing export table |
| `get_budget_alerts` | GCP budget alert status |
| `list_committed_use_discounts` | CUD inventory and utilization |
| `get_recommender_insights` | GCP Recommender cost insights |
| `list_resources` | Resource inventory with labels |
| `get_monitoring_metrics` | Cloud Monitoring utilization data |

### 3.2 Kubernetes MCP

#### `kubernetes-mcp`
| Tool | Description |
|------|-------------|
| `get_namespace_costs` | Cost breakdown by namespace (via OpenCost/Kubecost API) |
| `get_pod_costs` | Per-pod cost with CPU/memory breakdown |
| `get_cluster_efficiency` | Cluster idle cost percentage and node utilization |
| `get_container_recommendations` | Rightsizing recommendations for resource requests/limits |
| `list_pods_by_label` | Query pods by label selectors |
| `get_node_utilization` | Node-level CPU/memory/disk utilization |
| `get_gpu_costs` | GPU allocation costs by workload |

### 3.3 Notification MCPs

#### `slack-mcp`
| Tool | Description |
|------|-------------|
| `send_message` | Post a message to a Slack channel |
| `send_interactive_message` | Post message with approval buttons (approve/reject) |
| `send_file` | Upload a report file to a Slack channel |
| `create_thread` | Start a threaded discussion on a cost alert |

#### `pagerduty-mcp`
| Tool | Description |
|------|-------------|
| `create_incident` | Trigger a PagerDuty incident for critical cost anomalies |
| `resolve_incident` | Auto-resolve an incident when anomaly clears |

#### `email-mcp`
| Tool | Description |
|------|-------------|
| `send_report` | Send formatted cost report via email (HTML/PDF attachment) |
| `send_alert` | Send cost alert email to specified recipients |

### 3.4 Integration MCPs

#### `jira-mcp`
| Tool | Description |
|------|-------------|
| `create_issue` | Create a Jira ticket for optimization opportunities or policy violations |
| `update_issue` | Update ticket status, add comments |
| `search_issues` | Query existing cost-related tickets |

#### `grafana-mcp`
| Tool | Description |
|------|-------------|
| `create_dashboard` | Programmatically create a Grafana dashboard from JSON model |
| `update_panel` | Update a specific panel's query or visualization |
| `create_alert_rule` | Set up Grafana alerting rules for cost thresholds |

#### `github-mcp`
| Tool | Description |
|------|-------------|
| `create_pr_comment` | Add cost-impact comments to Terraform/IaC pull requests |
| `get_pr_diff` | Read PR changes to estimate cost impact |

### 3.5 Storage MCP

#### `storage-mcp`
| Tool | Description |
|------|-------------|
| `store_cost_snapshot` | Persist a point-in-time cost snapshot for historical analysis |
| `get_historical_data` | Retrieve historical cost snapshots by date range |
| `store_budget` | Save budget definitions (team, amount, period) |
| `get_budgets` | Retrieve all active budget definitions |
| `store_config` | Save agent configuration (thresholds, schedules, policies) |
| `get_config` | Retrieve agent configuration |
| `store_allocation_rules` | Save cost allocation rules |
| `get_allocation_rules` | Retrieve allocation rules |

---

## Block 4: Implementation Phases

### Phase 0: Foundation (Weeks 1–2)
**Goal:** Stand up the kagent infrastructure and prove a single agent can query real cloud costs.

| Task | Deliverable |
|------|------------|
| Deploy kagent control plane on a K8s cluster | Running kagent with CRDs |
| Build `aws-billing-mcp` (Cost Explorer + CUR) | MCP server with `get_cost_and_usage`, `describe_instances` |
| Build `storage-mcp` (PostgreSQL or S3-backed) | MCP server for persisting snapshots and configs |
| Create **Cost Visibility Agent** | Agent that answers "What did we spend on X?" |
| Manual testing via CLI / chat | Validated Q&A with real AWS cost data |

### Phase 1: Core FinOps Loop (Weeks 3–5)
**Goal:** Deliver the minimum viable FinOps replacement — cost visibility, anomaly detection, budgets, and basic optimization.

| Task | Deliverable |
|------|------------|
| Build `anomaly-detection` skill | Z-score / IQR-based anomaly detection on cost time-series |
| Build `budget-tracking` skill | Budget definition, threshold checking, alert logic |
| Build `waste-detection` skill | Idle resource detection (stopped EC2, unattached EBS, unused EIPs) |
| Build `slack-mcp` | Slack notifications for alerts and reports |
| Create **Anomaly Detection Agent** | Scheduled agent that scans costs every 15 min, alerts on anomalies |
| Create **Budget & Forecast Agent** | Daily budget check agent with Slack threshold alerts |
| Create **Optimization Agent** (basic) | Daily scan for idle resources, generates report |
| Build `report-generation` skill | Markdown / HTML report formatting |
| Create **Orchestrator Agent** | Routes user queries, composes daily digest from sub-agents |
| Build daily digest pipeline | Scheduled cron: cost refresh → anomaly scan → budget check → digest to Slack |

### Phase 2: Allocation, Governance & Advanced Optimization (Weeks 6–9)
**Goal:** Add cost allocation, tagging governance, rightsizing, commitment management, and Kubernetes cost tracking.

| Task | Deliverable |
|------|------------|
| Build `allocation-rules` skill | Tag-based allocation, shared cost splitting |
| Build `policy-engine` skill | Configurable rules for tag compliance, instance size limits |
| Build `rightsizing` skill | Match CloudWatch utilization to optimal instance types |
| Build `kubernetes-mcp` | OpenCost/Kubecost API integration |
| Build `forecasting` skill | Linear regression + seasonal decomposition forecasting |
| Create **Allocation & Tagging Agent** | Daily allocation runs, tag compliance audits |
| Create **Governance & Policy Agent** | Event-driven policy enforcement |
| Create **Commitment Mgmt Agent** | Weekly RI/SP coverage and utilization reports |
| Enhance **Optimization Agent** | Add rightsizing, container rightsizing, storage tier recs |
| Build `approval-gate` skill | Slack interactive approval for destructive actions |
| Build `jira-mcp` | Ticket creation for policy violations and optimization tasks |

### Phase 3: Multi-Cloud, Unit Economics & Collaboration (Weeks 10–13)
**Goal:** Extend to Azure/GCP, add unit economics, chargeback, and rich collaboration features.

| Task | Deliverable |
|------|------------|
| Build `azure-billing-mcp` | Azure Cost Management API integration |
| Build `gcp-billing-mcp` | GCP BigQuery billing export integration |
| Build `cost-normalization` skill | Normalize billing schemas across AWS/Azure/GCP |
| Build `unit-economics` skill | Cost-per-customer, cost-per-transaction calculations |
| Build `grafana-mcp` | Programmatic dashboard creation |
| Create **Unit Economics Agent** | On-demand unit cost calculations |
| Create **Invoice Agent** | Monthly invoice reconciliation and billing anomaly detection |
| Create **Collaboration Agent** | Slack cost bot for interactive queries |
| Enhance **Reporting Agent** | Chargeback reports, Grafana dashboard generation |
| Build `github-mcp` | Cost-impact PR comments for Terraform changes |

### Phase 4: Sustainability, Benchmarking & Polish (Weeks 14–16)
**Goal:** Complete feature parity. Add sustainability tracking, benchmarking, maturity assessment, and production hardening.

| Task | Deliverable |
|------|------------|
| Create **Sustainability Agent** | Carbon emissions estimation and green region recommendations |
| Create **Benchmarking Agent** | Internal team comparison and efficiency scoring |
| Build `pagerduty-mcp` | Critical anomaly escalation |
| Build `email-mcp` | Scheduled email report delivery |
| Production hardening | Rate limiting, retry logic, error handling, audit logging |
| Documentation | Agent playbooks, MCP API docs, runbooks |
| Load/stress testing | Validate with 50+ accounts, 10k+ resources |

---

## Block 5: Proof-of-Concept Scope

### PoC Objective
Demonstrate that **3 kagent agents + 2 MCPs + 3 skills** can replace the core daily workflow of a FinOps platform for a single AWS account within **2 weeks**.

### PoC Deliverables

```
┌─────────────────────────────────────────────────────────┐
│                    PoC ARCHITECTURE                     │
│                                                         │
│  ┌─────────────────────────────┐                        │
│  │    Orchestrator Agent       │                        │
│  │  (routes queries, composes  │                        │
│  │   daily digest)             │                        │
│  └─────┬──────┬──────┬────────┘                        │
│        │      │      │                                  │
│        ▼      ▼      ▼                                  │
│  ┌────────┐┌────────┐┌────────┐                        │
│  │ Cost   ││Anomaly ││Optimiz │                        │
│  │ Visib. ││Detect. ││Recomm. │                        │
│  │ Agent  ││Agent   ││Agent   │                        │
│  └───┬────┘└───┬────┘└───┬────┘                        │
│      │         │         │                              │
│      └─────────┼─────────┘                              │
│                ▼                                        │
│  ┌──────────────────────────────┐                       │
│  │  MCPs: aws-billing │ slack   │                       │
│  │  Skills: anomaly-detection   │                       │
│  │          waste-detection     │                       │
│  │          report-generation   │                       │
│  └──────────────────────────────┘                       │
└─────────────────────────────────────────────────────────┘
```

### PoC Feature Matrix

| # | Feature | Acceptance Criteria |
|---|---------|-------------------|
| 1 | **Ad-hoc cost query** | User asks "What did we spend on EC2 last week?" in Slack → Agent responds with accurate breakdown within 10s |
| 2 | **Daily cost digest** | Every morning at 8 AM, a Slack message is posted with: total spend, top 5 services, day-over-day change |
| 3 | **Anomaly detection** | Agent detects a >30% day-over-day spike and posts alert to Slack within 15 min of data availability |
| 4 | **Idle resource report** | Agent identifies stopped EC2 instances, unattached EBS volumes, and unused Elastic IPs; posts weekly summary |
| 5 | **Budget threshold alert** | Define a $10,000/month budget; agent alerts when 80% and 100% thresholds are crossed |
| 6 | **Month-end forecast** | Agent predicts end-of-month spend based on current run rate and posts to Slack |

### PoC Success Criteria

| Criterion | Target |
|-----------|--------|
| Cost data accuracy | ≥99% match vs. AWS Cost Explorer UI |
| Anomaly detection recall | Catches ≥90% of >30% daily spikes |
| Alert latency | <15 min from data availability |
| Daily digest reliability | 100% delivery for 14 consecutive days |
| Forecast accuracy | Within ±10% of actual month-end spend |
| User satisfaction | FinOps team rates "would replace current tool" ≥4/5 |

### PoC Timeline

| Day | Milestone |
|-----|-----------|
| Day 1–2 | Deploy kagent, build `aws-billing-mcp` with `get_cost_and_usage` |
| Day 3–4 | Build Cost Visibility Agent, validate ad-hoc queries |
| Day 5–6 | Build `anomaly-detection` skill + Anomaly Detection Agent |
| Day 7–8 | Build `slack-mcp`, wire up alerts and daily digest |
| Day 9–10 | Build `waste-detection` skill + Optimization Agent |
| Day 11–12 | Build Orchestrator Agent, integrate all flows |
| Day 13–14 | Testing, bug fixes, demo preparation |

### PoC Cost Estimate

| Component | Estimated Cost |
|-----------|---------------|
| LLM API calls (Claude Sonnet, ~500 calls/day) | ~$50–100/month |
| K8s cluster (3-node, t3.medium) | ~$150/month |
| AWS Cost Explorer API calls | Free (within limits) |
| Slack workspace | Free tier |
| **Total PoC monthly cost** | **~$200–250/month** |

vs. typical FinOps platform: **$5,000–50,000/month**

---

## Block 6: Competitive Advantages of the Agent-Based Approach

| Advantage | Description |
|-----------|-------------|
| **No vendor lock-in** | Agents, MCPs, and skills are open, composable, and portable |
| **Natural language interface** | LLM agents understand questions in plain English — no dashboard training needed |
| **Infinite customizability** | Add new skills or MCPs for any internal system; no feature-request backlog |
| **Cost transparency** | The system itself costs ~$200/month vs. $5k–50k for a SaaS FinOps platform |
| **Incremental adoption** | Start with 1 agent on 1 cloud account, scale to multi-cloud over weeks |
| **Event-driven architecture** | Real-time response to cloud events, not just periodic polling |
| **Context-aware reasoning** | LLM agents can explain *why* costs changed, not just *that* they changed |
| **Composable workflows** | Chain agents for complex workflows that would require custom integrations in a SaaS tool |

---

---

## Block 7: Agentic Workflow Triggers

Every agent workflow needs a **trigger** — the event, signal, or condition that causes the agent to wake up and act. Below is a comprehensive taxonomy of trigger types, mapped to every agent and feature in the system.

---

### 7.1 Trigger Taxonomy

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          TRIGGER SOURCES                                   │
│                                                                            │
│  ⏰ SCHEDULED        ☁️ CLOUD EVENT       💬 USER-INITIATED                │
│  (Cron / Interval)   (Push from provider)  (Chat / CLI / API)              │
│                                                                            │
│  📊 THRESHOLD        🔗 WEBHOOK           🔀 GITOPS                       │
│  (Metric breach)     (External system)     (PR / Merge / Deploy)           │
│                                                                            │
│  🔄 AGENT-CHAIN      📅 CALENDAR          🏷️ DATA-CHANGE                  │
│  (Upstream agent)    (Business calendar)   (New billing data available)     │
└─────────────────────────────────────────────────────────────────────────────┘
```

| Trigger Type | Mechanism | Latency | Example |
|-------------|-----------|---------|---------|
| **Scheduled (Cron)** | Kubernetes CronJob / kagent scheduler | Predictable | "Run every day at 8 AM UTC" |
| **Interval** | Polling loop within agent | Configurable | "Check every 15 minutes" |
| **Cloud Event** | CloudTrail / EventBridge / Activity Log / Pub/Sub push | Near real-time (~seconds) | "EC2 instance launched" |
| **Threshold Breach** | Agent detects metric crossing a boundary | Depends on poll interval | "Spend exceeded 80% of budget" |
| **User-Initiated** | Slack message, CLI command, REST API call, Chat UI | Immediate | "What did we spend on S3?" |
| **Webhook** | HTTP POST from external system | Near real-time | "Jira ticket status changed" |
| **GitOps** | GitHub/GitLab webhook on PR/merge/deploy | Near real-time | "Terraform PR opened" |
| **Agent-Chain** | Upstream agent completes and triggers downstream | Sequential | "Cost refresh done → run anomaly scan" |
| **Calendar** | Business calendar event (month-end, quarter-close) | Predictable | "Last business day of month" |
| **Data-Change** | New CUR/billing file lands in S3 / BigQuery | Event-driven (S3 notification) | "New CUR partition available" |

---

### 7.2 Triggers by Agent

#### Cost Visibility Agent

| Trigger | Type | Fires When | Workflow Initiated |
|---------|------|-----------|-------------------|
| Hourly cost refresh | ⏰ Scheduled | Every hour, on the hour | Pull latest costs from all cloud providers, store snapshot |
| User asks a cost question | 💬 User-Initiated | Slack message / CLI / API matches cost-query intent | Ad-hoc cost query → return answer |
| New CUR file lands in S3 | 🏷️ Data-Change | S3 event notification on CUR bucket | Ingest and parse new billing data |
| Upstream orchestrator request | 🔄 Agent-Chain | Orchestrator composing a multi-agent report | Return cost summary as sub-task |
| Month-end close | 📅 Calendar | Last day of month, 11:59 PM | Generate final monthly cost snapshot |

#### Allocation & Tagging Agent

| Trigger | Type | Fires When | Workflow Initiated |
|---------|------|-----------|-------------------|
| Daily allocation run | ⏰ Scheduled | Every day at 6 AM | Re-allocate all costs to teams using current tag/label mappings |
| New resource created without tags | ☁️ Cloud Event | CloudTrail `RunInstances` / `CreateBucket` with empty tags | Flag untagged resource, notify owner, create Jira ticket |
| Tag policy updated | 🔗 Webhook | Admin updates tagging policy in config store | Re-scan all resources against new policy |
| User requests allocation report | 💬 User-Initiated | "Show me Platform team's costs" | Generate on-demand allocation breakdown |
| Resource tag modified | ☁️ Cloud Event | CloudTrail `CreateTags` / `DeleteTags` | Update allocation mappings, re-attribute affected costs |

#### Budget & Forecast Agent

| Trigger | Type | Fires When | Workflow Initiated |
|---------|------|-----------|-------------------|
| Daily budget check | ⏰ Scheduled | Every day at 9 AM | Compare current spend to all active budgets |
| 80% budget threshold crossed | 📊 Threshold | Spend reaches 80% of any defined budget | Send warning alert to budget owner via Slack |
| 100% budget threshold crossed | 📊 Threshold | Spend reaches 100% of any budget | Send critical alert + PagerDuty incident |
| Custom threshold crossed | 📊 Threshold | Spend crosses any user-defined threshold (50%, 90%, etc.) | Send configurable notification |
| Weekly forecast refresh | ⏰ Scheduled | Every Monday at 7 AM | Re-run forecast model, update projected month-end spend |
| User asks for forecast | 💬 User-Initiated | "What will we spend this month?" | Run forecast on demand, return prediction |
| Month-end approaching (T-5 days) | 📅 Calendar | 5 days before end of month | Generate final forecast, compare to budget, send summary |
| New budget created | 🔗 Webhook / 💬 User-Initiated | Admin defines new budget via API or chat | Register budget, begin tracking |

#### Anomaly Detection Agent

| Trigger | Type | Fires When | Workflow Initiated |
|---------|------|-----------|-------------------|
| Periodic anomaly scan | ⏰ Interval | Every 15 minutes | Pull latest cost data, run anomaly detection model |
| New CUR data available | 🏷️ Data-Change | S3 notification on new CUR file | Ingest new data, scan for anomalies |
| Cost spike detected | 📊 Threshold | Anomaly model flags >30% day-over-day increase | Send Slack alert, create Jira ticket, page on-call if critical |
| Cost drop detected | 📊 Threshold | Anomaly model flags >50% unexpected decrease | Send informational alert (possible service outage indicator) |
| User asks about anomalies | 💬 User-Initiated | "Any cost spikes this week?" | Scan recent data, return anomaly report |
| Upstream agent detects unusual pattern | 🔄 Agent-Chain | Cost Visibility Agent flags unexpected service in top-5 | Deep-dive analysis on flagged service |

#### Optimization Agent

| Trigger | Type | Fires When | Workflow Initiated |
|---------|------|-----------|-------------------|
| Daily waste scan | ⏰ Scheduled | Every day at 7 AM | Scan for idle instances, unattached volumes, unused IPs |
| Weekly rightsizing analysis | ⏰ Scheduled | Every Sunday at midnight | Analyze 7-day utilization metrics, generate rightsizing recs |
| New EC2 instance launched | ☁️ Cloud Event | CloudTrail `RunInstances` event | Check if instance type matches workload profile, flag oversized |
| Instance running for >72h at <10% CPU | 📊 Threshold | CloudWatch metric falls below threshold for sustained period | Recommend downsize or termination |
| EBS volume unattached for >7 days | 📊 Threshold | Resource state unchanged for duration | Flag for cleanup, estimate savings |
| User asks for savings opportunities | 💬 User-Initiated | "Where can we cut costs?" | Run full optimization scan, return ranked recommendations |
| Post-deployment cost check | 🔀 GitOps | Terraform apply completes (webhook) | Compare pre/post deployment costs, flag unexpected increases |
| Approval received for cleanup | 🔗 Webhook | Slack interactive button clicked "Approve" | Execute approved cleanup action (delete volume, terminate instance) |

#### Commitment Management Agent

| Trigger | Type | Fires When | Workflow Initiated |
|---------|------|-----------|-------------------|
| Weekly coverage analysis | ⏰ Scheduled | Every Monday at 8 AM | Analyze RI/SP coverage gaps, generate purchase recommendations |
| RI/SP expiring in 30 days | 📅 Calendar | Commitment expiration date minus 30 days | Send renewal recommendation to FinOps lead |
| RI/SP expiring in 7 days | 📅 Calendar | Commitment expiration date minus 7 days | Send urgent renewal alert |
| Utilization drops below 80% | 📊 Threshold | Commitment utilization falls below target | Alert on underutilized commitments, suggest modifications |
| New on-demand usage pattern detected | 📊 Threshold | Consistent on-demand usage for >14 days on same instance family | Recommend commitment purchase |
| User asks about commitments | 💬 User-Initiated | "How are our reserved instances performing?" | Return coverage, utilization, and savings report |
| Quarterly commitment review | 📅 Calendar | First Monday of each quarter | Generate full commitment portfolio analysis |

#### Reporting & Dashboard Agent

| Trigger | Type | Fires When | Workflow Initiated |
|---------|------|-----------|-------------------|
| Daily digest | ⏰ Scheduled | Every day at 8 AM | Collect data from all agents, format daily cost digest, post to Slack |
| Weekly executive summary | ⏰ Scheduled | Every Friday at 4 PM | Generate executive-level summary with trends, anomalies, savings |
| Monthly chargeback report | 📅 Calendar | First business day of month | Generate per-team chargeback reports for previous month |
| Upstream agents complete | 🔄 Agent-Chain | All daily agents finish their runs | Aggregate results into unified dashboard update |
| User requests a report | 💬 User-Initiated | "Generate a cost report for Q1" | Build custom report on demand |
| Dashboard config changed | 🔗 Webhook | Admin updates Grafana dashboard config | Regenerate/update Grafana dashboards |
| Data export requested | 💬 User-Initiated | "Export last month's costs as CSV" | Query data, format, deliver file |

#### Governance & Policy Agent

| Trigger | Type | Fires When | Workflow Initiated |
|---------|------|-----------|-------------------|
| Resource created in cloud | ☁️ Cloud Event | Any `Create*` / `RunInstances` / `Put*` CloudTrail event | Evaluate resource against all active policies |
| Resource modified in cloud | ☁️ Cloud Event | Any `Modify*` / `Update*` CloudTrail event | Re-evaluate resource against policies |
| Large instance launched | ☁️ Cloud Event | `RunInstances` with instance type ≥ 4xlarge | Check if pre-approved, require justification if not |
| Expensive service activated | ☁️ Cloud Event | First usage of a high-cost service (e.g., SageMaker, Redshift) | Alert FinOps team, request cost estimate |
| Policy violation detected | 📊 Threshold | Resource fails policy check | Create Jira ticket, Slack notification to resource owner |
| Policy config updated | 🔗 Webhook | Admin updates policy rules | Re-scan all resources against updated policy set |
| Terraform PR opened | 🔀 GitOps | GitHub webhook on PR with `.tf` file changes | Estimate cost impact, post PR comment with cost delta |
| Terraform PR merged | 🔀 GitOps | PR merged to main branch | Log expected cost change, schedule post-deploy validation |
| Compliance audit requested | 💬 User-Initiated | "Show me all policy violations this quarter" | Generate compliance report |

#### Supplemental Agent Triggers

##### Unit Economics Agent
| Trigger | Type | Fires When |
|---------|------|-----------|
| Monthly unit cost calculation | ⏰ Scheduled | First of month — calculate cost-per-customer, cost-per-transaction |
| Customer onboarded/offboarded | 🔗 Webhook | CRM system notifies of customer change |
| User asks unit cost question | 💬 User-Initiated | "What's our cost per API call?" |
| Revenue data updated | 🏷️ Data-Change | New revenue figures posted to data warehouse |

##### Sustainability Agent
| Trigger | Type | Fires When |
|---------|------|-----------|
| Monthly carbon report | ⏰ Scheduled | First of month — pull carbon data from cloud provider APIs |
| New region selected for deployment | 🔀 GitOps | Terraform changes target region |
| User asks about carbon footprint | 💬 User-Initiated | "What's our carbon output from us-east-1?" |

##### Invoice Agent
| Trigger | Type | Fires When |
|---------|------|-----------|
| New invoice received | 🏷️ Data-Change | Cloud provider publishes monthly invoice |
| Invoice amount deviates >5% from forecast | 📊 Threshold | Reconciliation finds discrepancy |
| User asks about billing | 💬 User-Initiated | "Does our AWS invoice match our allocation?" |

##### Collaboration Agent
| Trigger | Type | Fires When |
|---------|------|-----------|
| Slack message with cost intent | 💬 User-Initiated | Any message in #finops channel mentioning costs |
| Slack reaction on alert | 🔗 Webhook | User reacts with :eyes: on a cost alert (triggers detail drill-down) |
| Weekly stakeholder digest | ⏰ Scheduled | Every Monday — personalized digest per team lead |

##### Benchmarking Agent
| Trigger | Type | Fires When |
|---------|------|-----------|
| Monthly benchmarking run | ⏰ Scheduled | First Monday of month |
| New team onboarded | 🔗 Webhook | Org chart / team registry updated |
| User asks for comparison | 💬 User-Initiated | "How does Team A's cost efficiency compare to Team B?" |

---

### 7.3 Trigger Implementation in kagent

Each trigger type maps to a concrete Kubernetes / kagent mechanism:

| Trigger Type | kagent / K8s Implementation |
|-------------|----------------------------|
| ⏰ **Scheduled** | `CronJob` CRD that invokes the agent's `/run` endpoint |
| ⏰ **Interval** | Agent container with internal ticker (e.g., Go `time.Ticker`, Python `schedule`) |
| ☁️ **Cloud Event** | EventBridge → SQS → kagent event-listener sidecar, or CloudEvents webhook receiver |
| 📊 **Threshold** | Agent checks metric during scheduled/interval run; if breached, triggers downstream workflow |
| 💬 **User-Initiated** | Slack bot (Bolt framework) or REST API gateway → routes to Orchestrator Agent |
| 🔗 **Webhook** | K8s `Ingress` + webhook handler service → forwards to target agent |
| 🔀 **GitOps** | GitHub App webhook → K8s webhook handler → Governance Agent |
| 🔄 **Agent-Chain** | Orchestrator invokes downstream agent via kagent's agent-to-agent API |
| 📅 **Calendar** | Pre-computed CronJob schedule aligned to business calendar (month-end, quarter-end) |
| 🏷️ **Data-Change** | S3 Event Notification → SQS → agent listener; or BigQuery scheduled query completion notification |

### 7.4 Trigger Configuration Example (kagent CRD)

```yaml
apiVersion: kagent.dev/v1alpha1
kind: Agent
metadata:
  name: anomaly-detection-agent
  namespace: finops
spec:
  model:
    provider: anthropic
    name: claude-sonnet-4-20250514
  triggers:
    # Run every 15 minutes
    - type: cron
      schedule: "*/15 * * * *"
      workflow: anomaly-scan

    # React to new billing data
    - type: cloud-event
      source: aws.s3
      filter:
        bucket: company-cur-bucket
        prefix: cur/
      workflow: anomaly-scan

    # User-initiated via Slack
    - type: slack
      channel: "#finops"
      pattern: "anomal|spike|unusual"
      workflow: anomaly-query

    # Chained from Cost Visibility Agent
    - type: agent-chain
      upstream: cost-visibility-agent
      event: cost-refresh-complete
      workflow: anomaly-scan

  workflows:
    anomaly-scan:
      skills: [anomaly-detection, report-generation]
      mcps: [aws-billing-mcp, slack-mcp]
      on_anomaly_found:
        - notify: slack-mcp.send_message
          channel: "#finops-alerts"
        - create_ticket: jira-mcp.create_issue
          project: FINOPS

    anomaly-query:
      skills: [anomaly-detection]
      mcps: [aws-billing-mcp]
      response: slack-mcp.send_message
```

### 7.5 Trigger Dependency Graph (Daily Pipeline)

```
06:00 ─── [Allocation Agent] ─── Tag scan + cost allocation
              │
07:00 ─── [Cost Visibility Agent] ─── Refresh cost data ───┐
              │                                              │
07:15 ─── [Anomaly Detection Agent] ◄───────────────────────┘
              │                           (agent-chain)
              ├─── IF anomaly found ──► [Slack Alert]
              │                     ──► [PagerDuty] (if critical)
              │
08:00 ─── [Budget Agent] ─── Check all budgets ───┐
              │                                     │
              ├─── IF threshold crossed ──► [Slack Alert]
              │                                     │
08:00 ─── [Optimization Agent] ─── Waste scan ────┐│
              │                                     ││
              ├─── New idle resources found          ││
              │                                     ││
08:30 ─── [Reporting Agent] ◄──────────────────────┘┘
              │                  (agent-chain: all upstream complete)
              │
              └──► Daily Digest → Slack #finops-daily
              └──► Team Digests → Slack #team-* channels
              └──► Executive Summary → Email to VP Eng

Monday 08:00 ─── [Commitment Agent] ─── Weekly RI/SP analysis
                     │
                     └──► Coverage report → Slack #finops
                     └──► Purchase recs → Email to FinOps lead

1st of Month ─── [Invoice Agent] ─── Reconciliation
                     │
                 [Unit Economics Agent] ─── Unit cost calculation
                     │
                 [Benchmarking Agent] ─── Team comparison
                     │
                 [Sustainability Agent] ─── Carbon report
                     │
                     └──► All monthly reports → Email + Slack + Grafana
```

---

### 7.6 Trigger Volume Estimates (per day, single AWS account)

| Trigger Type | Est. Volume/Day | Notes |
|-------------|----------------|-------|
| ⏰ Scheduled runs | ~15–20 | Cron jobs across all agents |
| ⏰ Interval polls | ~96 | Anomaly agent every 15 min = 96/day |
| ☁️ Cloud Events | ~50–500 | Depends on resource churn in the account |
| 📊 Threshold breaches | ~0–5 | Rare on a stable account; more on volatile ones |
| 💬 User queries | ~5–20 | FinOps team asking questions via Slack |
| 🔀 GitOps events | ~5–15 | Terraform PRs per day |
| 🔄 Agent-chain | ~15–20 | Mirrors scheduled runs (each scheduled run triggers downstream) |
| **Total agent invocations** | **~190–680/day** | Translates to ~$2–5/day in LLM API costs |

---

> **Status:** Plan complete. Ready for Phase 0 implementation.
