#!/bin/bash

set -e

# Colors for better readability
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper function to execute action with visible echo
run_action() {
    local description="$1"
    local command="$2"
    
    echo -e "${BLUE}>>> ${description}${NC}"
    eval "$command"
    echo ""
}

# Helper function to wait for user confirmation
wait_for_enter() {
    local message="${1:-Press ENTER to continue}"
    echo -e "${YELLOW}${message}...${NC}"
    read -r
    echo ""
}

# Get the actual network name used by docker-compose
get_network_name() {
    # Find network name by inspecting cassandra-1 container
    docker inspect cassandra-1 --format='{{range $k, $v := .NetworkSettings.Networks}}{{$k}}{{end}}' 2>/dev/null || echo "audit_net"
}

echo -e "${GREEN}======================================${NC}"
echo -e "${GREEN}Cassandra Cluster Failure Test Script${NC}"
echo -e "${GREEN}======================================${NC}"
echo ""

# Detect network name
NETWORK_NAME=$(get_network_name)
echo -e "${BLUE}Detected network: ${NETWORK_NAME}${NC}"
echo ""

wait_for_enter "Press ENTER to start Test 1"

echo -e "${GREEN}=== Test 1: Pause single node (QUORUM should work) ===${NC}"
echo ""

run_action "Pausing cassandra-2..." \
    "docker pause cassandra-2"

wait_for_enter "Node cassandra-2 paused. Press ENTER to check cluster status"

run_action "Checking cluster status from cassandra-1..." \
    "docker exec cassandra-1 nodetool status"

wait_for_enter "Test API via Swagger now. Press ENTER when done testing"

run_action "Unpausing cassandra-2..." \
    "docker unpause cassandra-2"

wait_for_enter "Node cassandra-2 restored. Press ENTER to verify cluster status"

run_action "Verifying cluster status..." \
    "docker exec cassandra-1 nodetool status"

wait_for_enter "Test 1 completed. Press ENTER to start Test 2"

echo ""
echo -e "${GREEN}=== Test 2: Pause two nodes (QUORUM should FAIL) ===${NC}"
echo ""

run_action "Pausing cassandra-2..." \
    "docker pause cassandra-2"

wait_for_enter "Node cassandra-2 paused. Press ENTER to pause cassandra-3"

run_action "Pausing cassandra-3..." \
    "docker pause cassandra-3"

wait_for_enter "Nodes cassandra-2 and cassandra-3 paused. Press ENTER to check cluster status"

run_action "Checking cluster status from cassandra-1..." \
    "docker exec cassandra-1 nodetool status"

wait_for_enter "Test API via Swagger (should FAIL - QUORUM not satisfied). Press ENTER when done testing"

run_action "Unpausing cassandra-2..." \
    "docker unpause cassandra-2"

wait_for_enter "Node cassandra-2 restored. Test API via Swagger (should work now). Press ENTER when done testing"

run_action "Unpausing cassandra-3..." \
    "docker unpause cassandra-3"

wait_for_enter "Node cassandra-3 restored. Press ENTER to verify full cluster status"

run_action "Verifying full cluster status..." \
    "docker exec cassandra-1 nodetool status"

wait_for_enter "Test 2 completed. Press ENTER to start Test 3"

echo ""
echo -e "${GREEN}=== Test 3: Network partition ===${NC}"
echo ""

run_action "Disconnecting cassandra-2 from network..." \
    "docker network disconnect ${NETWORK_NAME} cassandra-2"

wait_for_enter "Network disconnected for cassandra-2. Press ENTER to check cluster status"

run_action "Checking cluster status (cassandra-2 should be DOWN)..." \
    "docker exec cassandra-1 nodetool status"

wait_for_enter "Test API via Swagger (should work with 2 nodes). Press ENTER when done testing"

run_action "Reconnecting cassandra-2 to network..." \
    "docker network connect ${NETWORK_NAME} cassandra-2"

wait_for_enter "Network restored. Press ENTER to check gossip info"

run_action "Checking gossip info on cassandra-2..." \
    "docker exec cassandra-2 nodetool gossipinfo | head -n 30"

wait_for_enter "Press ENTER to verify final cluster status"

run_action "Verifying final cluster status..." \
    "docker exec cassandra-1 nodetool status"

echo ""
echo -e "${GREEN}======================================${NC}"
echo -e "${GREEN}All tests completed successfully!${NC}"
echo -e "${GREEN}======================================${NC}"
echo ""
echo -e "${BLUE}Summary:${NC}"
echo "- Test 1: Single node failure (cassandra-2) - QUORUM maintained ✓"
echo "- Test 2: Two node failure (cassandra-2 + cassandra-3) - QUORUM lost, then restored ✓"
echo "- Test 3: Network partition (cassandra-2) - QUORUM maintained ✓"
echo ""
