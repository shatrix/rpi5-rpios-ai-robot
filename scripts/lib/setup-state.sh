#!/bin/bash
################################################################################
# Setup State Management Library
# Tracks completion status of setup steps for idempotent execution
################################################################################

STATE_FILE="/var/lib/rpi5-ai-robot/setup-state.json"
STATE_DIR="/var/lib/rpi5-ai-robot"

# Initialize state file if it doesn't exist
init_state() {
    if [ ! -f "$STATE_FILE" ]; then
        mkdir -p "$STATE_DIR"
        echo '{}' > "$STATE_FILE"
        chmod 644 "$STATE_FILE"
    fi
}

# Mark a step as complete with timestamp
# Usage: mark_step_complete "step_name"
mark_step_complete() {
    local step_name="$1"
    local timestamp=$(date -Iseconds)
    
    init_state
    
    # Use jq if available, otherwise use basic sed
    if command -v jq &> /dev/null; then
        local temp_file=$(mktemp)
        jq --arg step "$step_name" --arg ts "$timestamp" \
            '.[$step] = $ts' "$STATE_FILE" > "$temp_file"
        mv "$temp_file" "$STATE_FILE"
    else
        # Fallback: simple string replacement (less robust)
        # For simplicity, we'll just append if jq is not available
        echo "WARNING: jq not installed, state tracking may be limited"
    fi
}

# Check if a step is complete
# Usage: if is_step_complete "step_name"; then ...
is_step_complete() {
    local step_name="$1"
    
    if [ ! -f "$STATE_FILE" ]; then
        return 1  # Not complete
    fi
    
    if command -v jq &> /dev/null; then
        local status=$(jq -r --arg step "$step_name" '.[$step] // "null"' "$STATE_FILE")
        if [ "$status" != "null" ]; then
            return 0  # Complete
        fi
    fi
    
    return 1  # Not complete
}

# Get step completion status (timestamp or "not completed")
# Usage: status=$(get_step_status "step_name")
get_step_status() {
    local step_name="$1"
    
    if [ ! -f "$STATE_FILE" ]; then
        echo "not completed"
        return
    fi
    
    if command -v jq &> /dev/null; then
        local timestamp=$(jq -r --arg step "$step_name" '.[$step] // "not completed"' "$STATE_FILE")
        echo "$timestamp"
    else
        echo "not completed"
    fi
}

# List all completed steps
list_completed_steps() {
    if [ ! -f "$STATE_FILE" ]; then
        return
    fi
    
    if command -v jq &> /dev/null; then
        jq -r 'to_entries | .[] | "\(.key): \(.value)"' "$STATE_FILE"
    fi
}

# Reset all state (clear completion tracking)
# Usage: reset_state
reset_state() {
    if [ -f "$STATE_FILE" ]; then
        echo '{}' > "$STATE_FILE"
        echo "State reset: all steps marked as incomplete"
    fi
}

# Get count of completed steps
count_completed_steps() {
    if [ ! -f "$STATE_FILE" ]; then
        echo "0"
        return
    fi
    
    if command -v jq &> /dev/null; then
        jq 'length' "$STATE_FILE"
    else
        echo "0"
    fi
}
