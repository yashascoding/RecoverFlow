# RecoverFlow

Autonomous AI payment-recovery system that detects failed payments, investigates root causes, and sends personalized recovery messages through Email to help merchants recover lost revenue.

**Payment Failed → AI Investigates → Policy Check → Email → Customer Pays → Revenue Recovered → Audit Trail**

---

## Problem

<!-- TODO: Write about the problem RecoverFlow solves -->

---

## Solution

<!-- TODO: Write about how RecoverFlow solves the problem -->

---

## Architecture

<!-- TODO: Add architecture diagram and explanation -->

<img width="1858" height="915" alt="architecture" src="https://github.com/user-attachments/assets/3dc67985-98fb-4ea2-8339-83226267a188" />

---

## AI Agent

<!-- TODO: Write about the LangGraph-based AI agent, its tools, and decision-making process -->

---

## Policy Firewall

<!-- TODO: Write about the deterministic policy engine, consent checks, financial limits, kill switch -->

---

## Razorpay

<!-- TODO: Write about Razorpay integration — payment links, webhooks, capture flow -->

---

## Resend

<!-- TODO: Write about Resend email integration — templates, delivery, webhooks -->

---

## Evaluation

<!-- TODO: Write about the evaluation methodology — control groups, A/B testing, metrics -->

---

## Results

<!-- TODO: Write about recovery rates, revenue recovered, lift over control -->

---

## Failure Handling

<!-- TODO: Write about how the system handles edge cases — idempotency, retries, dead letters -->

---

## Setup

<!-- TODO: Write setup instructions — prerequisites, env vars, docker compose, local dev -->

```bash
# Clone
git clone https://github.com/your-org/RecoverFlow.git
cd RecoverFlow

# Environment
cp .env.example .env
# Edit .env with your keys

# Run
docker compose up --build
```

---

## Demo

<!-- TODO: Write demo walkthrough — how to simulate a failure and watch recovery -->

---

## Future Work

<!-- TODO: Write about planned features — SMS recovery, multi-gateway, smart timing, etc. -->
