#!/bin/bash
# ============================================================================
# RecoverFlow — Full Demo Script
# Demonstrates: Login → Simulate Failure → AI Agent → Recovery Email Sent
# ============================================================================

set -uo pipefail
BASE="http://localhost:8001"
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'
BOLD='\033[1m'

header() { echo -e "\n${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"; echo -e "${BOLD}$1${NC}"; echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"; }
step()   { echo -e "${YELLOW}▸ $1${NC}"; }
ok()     { echo -e "${GREEN}✔ $1${NC}"; }
fail()   { echo -e "${RED}✘ $1${NC}"; }

# ──────────────────────────────────────────────────────────────────────────────
# STEP 1: Health Check
# ──────────────────────────────────────────────────────────────────────────────
header "STEP 1 — System Health Check"
step "Checking backend health..."
HEALTH=$(curl -sf "$BASE/api/health")
echo "$HEALTH" | python3 -m json.tool
ok "Backend healthy\n"

# ──────────────────────────────────────────────────────────────────────────────
# STEP 2: Register / Login
# ──────────────────────────────────────────────────────────────────────────────
header "STEP 2 — Authentication"
DEMO_EMAIL="demo-$(date +%s)@example.com"
DEMO_PASS="Demo@12345"

step "Registering user: $DEMO_EMAIL"
REGISTER_RESP=$(curl -sf -X POST "$BASE/api/auth/register" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$DEMO_EMAIL\",\"password\":\"$DEMO_PASS\",\"name\":\"Demo User\"}")
TOKEN=$(echo "$REGISTER_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
ok "Token obtained: ${TOKEN:0:20}...\n"

AUTH_HEADER="Authorization: Bearer $TOKEN"

# ──────────────────────────────────────────────────────────────────────────────
# STEP 3: Simulate Payment Failure (triggers full recovery pipeline)
# ──────────────────────────────────────────────────────────────────────────────
header "STEP 3 — Simulate Payment Failure + AI Recovery Pipeline"
CUSTOMER_EMAIL="bhagwatyashas5@gmail.com"

step "Simulating ₹499 payment failure for $CUSTOMER_EMAIL..."
SIM_RESP=$(curl -sf -X POST "$BASE/api/simulate/failure" \
  -H "Content-Type: application/json" \
  -H "$AUTH_HEADER" \
  -d "{
    \"customer_email\": \"$CUSTOMER_EMAIL\",
    \"customer_name\": \"Yashas Bhagwat\",
    \"amount\": 49900,
    \"failure_type\": \"insufficient_funds\"
  }")
echo "$SIM_RESP" | python3 -m json.tool

PAYMENT_ID=$(echo "$SIM_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['payment_id'])")
ORDER_ID=$(echo "$SIM_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['razorpay_order_id'])")
EMAIL_SENT=$(echo "$SIM_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['email_sent_to'])")
ok "Payment created: $PAYMENT_ID"
ok "Order ID: $ORDER_ID"
ok "Recovery email sent to: $EMAIL_SENT\n"

step "Waiting for AI agent to process (5s)..."
sleep 5

# ──────────────────────────────────────────────────────────────────────────────
# STEP 4: Check Payment Status (should be recovery_pending)
# ──────────────────────────────────────────────────────────────────────────────
header "STEP 4 — Verify Payment Status"
step "Fetching payment $PAYMENT_ID..."
PAY_RESP=$(curl -sf -H "$AUTH_HEADER" "$BASE/api/payments/$PAYMENT_ID")
echo "$PAY_RESP" | python3 -m json.tool
PAY_STATUS=$(echo "$PAY_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['status'])")
ok "Payment status: $PAY_STATUS\n"

# ──────────────────────────────────────────────────────────────────────────────
# STEP 5: Check AI Agent Run
# ──────────────────────────────────────────────────────────────────────────────
header "STEP 5 — AI Agent Run"
step "Fetching latest agent runs..."
RUNS_RESP=$(curl -sf -H "$AUTH_HEADER" "$BASE/api/agents/runs?page=1&page_size=1")
echo "$RUNS_RESP" | python3 -m json.tool 2>/dev/null | head -40
ok "Agent run fetched\n"

# ──────────────────────────────────────────────────────────────────────────────
# STEP 6: Check Recovery Attempts
# ──────────────────────────────────────────────────────────────────────────────
header "STEP 6 — Recovery Attempts"
step "Checking recovery attempts for payment..."
RECOVERY_RESP=$(curl -sf -H "$AUTH_HEADER" "$BASE/api/recovery/v2/incidents?page=1&page_size=5")
echo "$RECOVERY_RESP" | python3 -m json.tool 2>/dev/null | head -40
ok "Recovery data fetched\n"

# ──────────────────────────────────────────────────────────────────────────────
# STEP 7: Evaluation Dashboard
# ──────────────────────────────────────────────────────────────────────────────
header "STEP 7 — Evaluation Dashboard"
step "Fetching evaluation metrics..."
EVAL=$(curl -sf -H "$AUTH_HEADER" "$BASE/api/evaluation/dashboard")
echo "$EVAL" | python3 -m json.tool
ok "Evaluation dashboard loaded\n"

# ──────────────────────────────────────────────────────────────────────────────
# STEP 8: Overview Stats
# ──────────────────────────────────────────────────────────────────────────────
header "STEP 8 — System Overview"
step "Fetching overview metrics..."
OVERVIEW=$(curl -sf -H "$AUTH_HEADER" "$BASE/api/payments/stats/overview")
echo "$OVERVIEW" | python3 -m json.tool
ok "Overview metrics loaded\n"

# ──────────────────────────────────────────────────────────────────────────────
# SUMMARY
# ──────────────────────────────────────────────────────────────────────────────
header "DEMO COMPLETE"
echo -e "${GREEN}${BOLD}Full recovery flow demonstrated:${NC}"
echo -e "  1. ✅ System health verified"
echo -e "  2. ✅ User registered & authenticated"
echo -e "  3. ✅ Payment failure simulated (insufficient_funds)"
echo -e "  4. ✅ AI agent investigated & diagnosed (Groq LLM)"
echo -e "  5. ✅ Recovery email sent with REAL Razorpay payment link"
echo -e "  6. ✅ Evaluation dashboard shows metrics"
echo ""
echo -e "${CYAN}Check your email: $EMAIL_SENT${NC}"
echo -e "${CYAN}Frontend UI: http://localhost:3001${NC}"
echo -e "${CYAN}API Docs:    http://localhost:8001/docs${NC}"
echo -e "${CYAN}Backend:     http://localhost:8001/api/health${NC}"
