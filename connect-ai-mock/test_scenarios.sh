#!/bin/bash
#
# Connect AI Mock API - Test Scenarios
# =====================================
# This script tests all available mock scenarios.
# Run each scenario one at a time by uncommenting or passing scenario name.
#
# Usage:
#   ./test_scenarios.sh              # Interactive menu
#   ./test_scenarios.sh <scenario>   # Run specific scenario
#   ./test_scenarios.sh all          # Run all scenarios
#
# Start server first:
#   cd /Users/prateekn/connect-ai-mock-api
#   source venv/bin/activate
#   python run.py
#

BASE_URL="http://localhost:8080"
QUERY_ENDPOINT="$BASE_URL/api/query"
CATALOGS_ENDPOINT="$BASE_URL/api/catalogs"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_header() {
    echo ""
    echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
    echo -e "${YELLOW}$1${NC}"
    echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
}

print_scenario() {
    echo -e "${GREEN}Scenario:${NC} $1"
    echo -e "${GREEN}Credentials:${NC} $2"
    echo -e "${GREEN}Expected:${NC} $3"
    echo ""
}

run_query() {
    local creds=$1
    local query=$2
    curl -s -N -u "$creds" -X POST "$QUERY_ENDPOINT" \
        -H "Content-Type: application/json" \
        -d "{\"query\": \"$query\"}"
}

run_metadata() {
    local creds=$1
    local endpoint=$2
    curl -s -u "$creds" "$BASE_URL/api/$endpoint"
}

# ============================================================================
# SCENARIO FUNCTIONS
# ============================================================================

scenario_health() {
    print_header "Health Check"
    echo "Checking if server is running..."
    curl -s "$BASE_URL/" | python3 -m json.tool
}

scenario_default() {
    print_header "Default Scenario - Normal Mock Data"
    print_scenario "default" "test@example.com:any_token" "Returns standard mock data (3 catalogs)"

    echo "GET /api/catalogs:"
    run_metadata "test@example.com:any_token" "catalogs" | python3 -m json.tool
}

scenario_error_auth() {
    print_header "Error Scenario - Authentication Error"
    print_scenario "error_auth" "test@example.com:error_pat" "Returns 401 Invalid credentials"

    echo "GET /api/catalogs:"
    run_metadata "test@example.com:error_pat" "catalogs" | python3 -m json.tool
}

scenario_error_not_found() {
    print_header "Error Scenario - Not Found"
    print_scenario "error_not_found" "test@example.com:notfound_pat" "Returns 404 Resource not found"

    echo "GET /api/catalogs:"
    run_metadata "test@example.com:notfound_pat" "catalogs" | python3 -m json.tool
}

scenario_error_server() {
    print_header "Error Scenario - Server Error"
    print_scenario "error_server" "test@example.com:server_error_pat" "Returns 500 Internal server error"

    echo "GET /api/catalogs:"
    run_metadata "test@example.com:server_error_pat" "catalogs" | python3 -m json.tool
}

scenario_empty() {
    print_header "Empty Data Scenario"
    print_scenario "empty_data" "test@example.com:empty_pat" "Returns empty result sets"

    echo "GET /api/catalogs:"
    run_metadata "test@example.com:empty_pat" "catalogs" | python3 -m json.tool
}

scenario_slow() {
    print_header "Slow Response Scenario (2s delay)"
    print_scenario "slow_response" "test@example.com:slow_pat" "Adds 2 second delay before response"

    echo "GET /api/catalogs (timing):"
    time run_metadata "test@example.com:slow_pat" "catalogs" | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'Catalogs: {len(d[\"results\"][0][\"rows\"])}')"
}

scenario_large() {
    print_header "Large Dataset Scenario"
    print_scenario "large_dataset" "test@example.com:large_pat" "Returns large datasets (150 contacts, 100 accounts, 200 orders)"

    echo "POST /api/query - SELECT * FROM Salesforce1.Salesforce.Contact:"
    run_query "test@example.com:large_pat" "SELECT * FROM Salesforce1.Salesforce.Contact" | \
        python3 -c "import sys,json; d=json.load(sys.stdin); print(f'Rows: {len(d[\"results\"][0][\"rows\"])}')"
}

scenario_datatypes() {
    print_header "Data Types Scenario"
    print_scenario "datatypes" "test@example.com:datatypes_pat" "Returns data with various SQL data types"

    echo "POST /api/query - Products (numeric types):"
    run_query "test@example.com:datatypes_pat" "SELECT * FROM TestDB.dbo.Products" | \
        python3 -c "import sys,json; d=json.load(sys.stdin); cols=[c['dataTypeName'] for c in d['results'][0]['schema']]; print(f'Data types: {cols}')"

    echo ""
    echo "POST /api/query - Events (date/time types):"
    run_query "test@example.com:datatypes_pat" "SELECT * FROM TestDB.dbo.Events" | \
        python3 -c "import sys,json; d=json.load(sys.stdin); cols=[c['dataTypeName'] for c in d['results'][0]['schema']]; print(f'Data types: {cols}')"
}

scenario_template() {
    print_header "Template Streaming Scenario"
    print_scenario "template_stream" "test@example.com:template_pat" "100 rows generated from template, pauses every 25 rows [100ms, 500ms, 100ms]"

    echo "POST /api/query (streaming with pauses):"
    time run_query "test@example.com:template_pat" "SELECT * FROM TestDB.dbo.Users" | \
        python3 -c "import sys,json; d=json.load(sys.stdin); print(f'Rows: {len(d[\"results\"][0][\"rows\"])}')"
}

scenario_template_slow() {
    print_header "Template Slow Streaming Scenario"
    print_scenario "template_slow" "test@example.com:template_slow_pat" "50 rows, pause every 10 rows [1s, 2s, 1s]"

    echo "POST /api/query (streaming with long pauses ~5s total):"
    time run_query "test@example.com:template_slow_pat" "SELECT * FROM TestDB.dbo.Users" | \
        python3 -c "import sys,json; d=json.load(sys.stdin); print(f'Rows: {len(d[\"results\"][0][\"rows\"])}')"
}

scenario_template_large() {
    print_header "Template Large Scenario"
    print_scenario "template_large" "test@example.com:template_large_pat" "1000 rows generated from template"

    echo "POST /api/query:"
    time run_query "test@example.com:template_large_pat" "SELECT * FROM TestDB.dbo.Users" | \
        python3 -c "import sys,json; d=json.load(sys.stdin); print(f'Rows: {len(d[\"results\"][0][\"rows\"])}')"
}

scenario_million() {
    print_header "Million Records Scenario"
    print_scenario "template_million" "test@example.com:million_pat" "1,000,000 rows with 20ms pause every 1000 rows"

    echo -e "${RED}WARNING: This will generate 1 million rows and take ~30+ seconds${NC}"
    read -p "Continue? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "POST /api/query:"
        time run_query "test@example.com:million_pat" "SELECT * FROM TestDB.dbo.Users" | \
            python3 -c "import sys,json; d=json.load(sys.stdin); print(f'Rows: {len(d[\"results\"][0][\"rows\"]):,}')"
    fi
}

scenario_partial_error() {
    print_header "Partial Error Scenario"
    print_scenario "template_partial_error" "test@example.com:partial_error_pat" "Returns 50 rows + error (connection timeout)"

    echo "POST /api/query:"
    run_query "test@example.com:partial_error_pat" "SELECT * FROM TestDB.dbo.Users" | \
        python3 -c "import sys,json; d=json.load(sys.stdin); print(f'Rows: {len(d[\"results\"][0][\"rows\"])}'); print(f'Error: {d[\"error\"]}')"
}

scenario_partial_500() {
    print_header "Partial Error 500 Scenario"
    print_scenario "template_partial_500" "test@example.com:partial_500_pat" "Returns 100 rows + server error"

    echo "POST /api/query:"
    run_query "test@example.com:partial_500_pat" "SELECT * FROM TestDB.dbo.Users" | \
        python3 -c "import sys,json; d=json.load(sys.stdin); print(f'Rows: {len(d[\"results\"][0][\"rows\"])}'); print(f'Error: {d[\"error\"]}')"
}

scenario_all_features() {
    print_header "All Features Combined Scenario"
    print_scenario "template_all_features" "test@example.com:all_features_pat" "100 rows + pauses [200ms, 500ms] + error"

    echo "POST /api/query:"
    time run_query "test@example.com:all_features_pat" "SELECT * FROM TestDB.dbo.Users" | \
        python3 -c "import sys,json; d=json.load(sys.stdin); print(f'Rows: {len(d[\"results\"][0][\"rows\"])}'); print(f'Error: {d[\"error\"]}')"
}

scenario_truncated() {
    print_header "Truncated Response Scenario (Server Crash)"
    print_scenario "truncated_response" "test@example.com:truncate_pat" "Returns truncated/malformed JSON after 10 rows"

    echo "POST /api/query:"
    run_query "test@example.com:truncate_pat" "SELECT * FROM TestDB.dbo.Users" | \
        python3 -c "
import sys,json
data = sys.stdin.read()
print(f'Response length: {len(data)} chars')
print(f'Last 60 chars: ...{data[-60:]}')
try:
    json.loads(data)
    print('JSON: VALID (unexpected)')
except json.JSONDecodeError as e:
    print(f'JSON: INVALID (truncated as expected)')"
}

scenario_crash() {
    print_header "Crash Mid-Stream Scenario"
    print_scenario "truncated_mid_stream" "test@example.com:crash_pat" "Truncates after 50 rows with pauses"

    echo "POST /api/query:"
    time run_query "test@example.com:crash_pat" "SELECT * FROM TestDB.dbo.Users" | \
        python3 -c "
import sys,json
data = sys.stdin.read()
print(f'Response length: {len(data)} chars')
try:
    json.loads(data)
    print('JSON: VALID')
except:
    print('JSON: INVALID (truncated/crashed)')"
}

# ============================================================================
# MENU
# ============================================================================

show_menu() {
    echo ""
    echo -e "${BLUE}Connect AI Mock API - Test Scenarios${NC}"
    echo "======================================"
    echo ""
    echo "Basic Scenarios:"
    echo "  1)  health          - Health check"
    echo "  2)  default         - Default mock data"
    echo "  3)  empty           - Empty result sets"
    echo ""
    echo "Error Scenarios:"
    echo "  4)  error_auth      - 401 Authentication error"
    echo "  5)  error_not_found - 404 Not found error"
    echo "  6)  error_server    - 500 Server error"
    echo ""
    echo "Delay Scenarios:"
    echo "  7)  slow            - 2 second delay"
    echo ""
    echo "Data Scenarios:"
    echo "  8)  large           - Large dataset (150+ rows)"
    echo "  9)  datatypes       - Various SQL data types"
    echo ""
    echo "Template Streaming Scenarios:"
    echo "  10) template        - 100 rows with pauses"
    echo "  11) template_slow   - 50 rows with long pauses (5s)"
    echo "  12) template_large  - 1000 rows"
    echo "  13) million         - 1,000,000 rows (slow!)"
    echo ""
    echo "Partial Error Scenarios:"
    echo "  14) partial_error   - 50 rows + timeout error"
    echo "  15) partial_500     - 100 rows + server error"
    echo "  16) all_features    - Rows + pauses + error"
    echo ""
    echo "Crash/Truncation Scenarios:"
    echo "  17) truncated       - Malformed JSON after 10 rows"
    echo "  18) crash           - Crash mid-stream after 50 rows"
    echo ""
    echo "  all) Run all scenarios"
    echo "  q)   Quit"
    echo ""
}

run_scenario() {
    case $1 in
        health|1)          scenario_health ;;
        default|2)         scenario_default ;;
        empty|3)           scenario_empty ;;
        error_auth|4)      scenario_error_auth ;;
        error_not_found|5) scenario_error_not_found ;;
        error_server|6)    scenario_error_server ;;
        slow|7)            scenario_slow ;;
        large|8)           scenario_large ;;
        datatypes|9)       scenario_datatypes ;;
        template|10)       scenario_template ;;
        template_slow|11)  scenario_template_slow ;;
        template_large|12) scenario_template_large ;;
        million|13)        scenario_million ;;
        partial_error|14)  scenario_partial_error ;;
        partial_500|15)    scenario_partial_500 ;;
        all_features|16)   scenario_all_features ;;
        truncated|17)      scenario_truncated ;;
        crash|18)          scenario_crash ;;
        all)
            scenario_health
            scenario_default
            scenario_empty
            scenario_error_auth
            scenario_error_not_found
            scenario_error_server
            scenario_slow
            scenario_large
            scenario_datatypes
            scenario_template
            scenario_template_slow
            scenario_template_large
            scenario_partial_error
            scenario_partial_500
            scenario_all_features
            scenario_truncated
            scenario_crash
            ;;
        *)
            echo -e "${RED}Unknown scenario: $1${NC}"
            return 1
            ;;
    esac
}

# ============================================================================
# MAIN
# ============================================================================

# Check if server is running
if ! curl -s "$BASE_URL/" > /dev/null 2>&1; then
    echo -e "${RED}Error: Server is not running at $BASE_URL${NC}"
    echo ""
    echo "Start the server first:"
    echo "  cd /Users/prateekn/connect-ai-mock-api"
    echo "  source venv/bin/activate"
    echo "  python run.py"
    echo ""
    exit 1
fi

# Run scenario from argument or show menu
if [ -n "$1" ]; then
    run_scenario "$1"
else
    while true; do
        show_menu
        read -p "Select scenario: " choice
        if [ "$choice" = "q" ] || [ "$choice" = "Q" ]; then
            echo "Bye!"
            exit 0
        fi
        run_scenario "$choice"
        echo ""
        read -p "Press Enter to continue..."
    done
fi
