#!/bin/bash
#
# ralph.sh — Unified loop runner for headless AI coding agents.
#
# Runs an AI agent (Claude Code, Codex, Amp) in a loop for N iterations.
# Concatenates prompt files into a single prompt, streams and logs output,
# and stops early if the agent emits a <promise>COMPLETE</promise> marker.
#
# ============================================================================
# PARAMETERS
# ============================================================================
#
#   $1  LLM        (required)   Which agent to run: claude, codex, amp
#   $2  ITERATIONS (default: 1) How many loop iterations to run
#   $3  DANGEROUS  (default: on) Skip permission prompts. on/off.
#                                 - claude: --dangerously-skip-permissions
#                                 - codex:  --dangerously-bypass-approvals-and-sandbox
#                                 - amp:    (no flag yet)
#   $4  CONTAINERS (default: "") Comma-separated Docker container names that
#                                 must be running before the loop starts.
#                                 Example: "myapp-1,mydb-1"
#                                 Leave empty or "" to skip the check.
#   $5  SLEEP      (default: 0) How long to sleep before starting.
#                                 Accepts any value valid for the sleep command.
#                                 Examples: 0, 30, 5m, 2h
#
# ============================================================================
# ENVIRONMENT VARIABLES (optional overrides)
# ============================================================================
#
#   KEEP_JSONL=0|1    Save raw NDJSON event log (Claude only, ON by default)
#   PROMPT_FILES=...  Space-separated list of prompt files to concatenate
#   CLAUDE_BIN=...    Path to claude binary (default: claude)
#   CODEX_BIN=...     Path to codex binary (default: codex)
#   AMP_BIN=...       Path to amp binary (default: amp)
#
# ============================================================================
# EXAMPLES
# ============================================================================
#
#   ./ralph.sh claude                          # 1 iteration, dangerous on
#   ./ralph.sh claude 5                        # 5 iterations, dangerous on
#   ./ralph.sh claude 5 off                    # 5 iterations, dangerous off
#   ./ralph.sh codex 3 on "app-1,db-1"        # 3 iterations, check containers
#   ./ralph.sh claude 5 on "" 2h              # 5 iterations, sleep 2 hours first
#   KEEP_JSONL=1 ./ralph.sh claude 5 on       # save raw NDJSON log
#
# ============================================================================
# REQUIREMENTS
# ============================================================================
#
#   - jq (required for Claude; install with: sudo apt-get install -y jq)
#   - docker (only if CONTAINERS is set)
#
# ============================================================================


# ============================================================================
# SECTION 1: PARSE PARAMETERS
# ============================================================================

# --- Parameter 1: LLM (required) ---
# Which AI agent to run. Must be one of: claude, codex, amp.
LLM="${1:-}"
if [ -z "$LLM" ]; then
  echo "Usage: $0 <llm> [iterations] [dangerous] [containers] [sleep]"
  echo ""
  echo "  llm:        claude | codex | amp  (required)"
  echo "  iterations:  number of loops       (default: 1)"
  echo "  dangerous:   on | off              (default: on)"
  echo "  containers:  comma-separated names (default: none)"
  echo "  sleep:       duration before start  (default: 0)"
  exit 1
fi

if [ "$LLM" != "claude" ] && [ "$LLM" != "codex" ] && [ "$LLM" != "amp" ]; then
  echo "ERROR: LLM must be one of: claude, codex, amp. Got: $LLM"
  exit 1
fi

# --- Parameter 2: ITERATIONS (default: 1) ---
# How many times to run the agent in a loop.
ITERATIONS="${2:-1}"

# --- Parameter 3: DANGEROUS (default: on) ---
# Whether to skip permission prompts. The actual CLI flag differs per LLM.
DANGEROUS_ARG="${3:-on}"

# Validate the dangerous flag value
if [ "$DANGEROUS_ARG" != "on" ] && [ "$DANGEROUS_ARG" != "off" ]; then
  echo "ERROR: dangerous must be 'on' or 'off'. Got: $DANGEROUS_ARG"
  exit 1
fi

# Map the on/off value to the correct CLI flag for each LLM.
#
# When dangerous is "on":
#   claude -> --dangerously-skip-permissions  (skips all permission prompts)
#   codex  -> --dangerously-bypass-approvals-and-sandbox  (most permissive mode)
#   amp    -> (no flag; amp has no dangerous mode yet)
#
# When dangerous is "off":
#   claude -> (no flag; runs with normal permission prompts)
#   codex  -> --full-auto  (autonomous but sandboxed; codex requires a mode flag
#             to run non-interactively, so we use its safer auto mode here)
#   amp    -> (no flag)
#
DANGEROUS_FLAG=""
if [ "$DANGEROUS_ARG" = "on" ]; then
  if [ "$LLM" = "claude" ]; then
    DANGEROUS_FLAG="--dangerously-skip-permissions"
  elif [ "$LLM" = "codex" ]; then
    DANGEROUS_FLAG="--dangerously-bypass-approvals-and-sandbox"
  elif [ "$LLM" = "amp" ]; then
    DANGEROUS_FLAG=""
  fi
else
  # dangerous is "off"
  if [ "$LLM" = "codex" ]; then
    DANGEROUS_FLAG="--full-auto"
  elif [ "$LLM" = "claude" ]; then
    DANGEROUS_FLAG=""
  elif [ "$LLM" = "amp" ]; then
    DANGEROUS_FLAG=""
  fi
fi

# --- Parameter 4: CONTAINERS (default: "") ---
# Comma-separated list of Docker container names that must be running.
# Leave empty to skip the Docker check entirely.
CONTAINERS_ARG="${4:-}"

# --- Parameter 5: SLEEP (default: 0) ---
# How long to sleep before starting the loop.
# Accepts any value valid for the sleep command (e.g., 0, 30, 5m, 2h).
SLEEP_ARG="${5:-0}"


# ============================================================================
# SECTION 2: CONFIGURATION
# ============================================================================

# Determine paths relative to where this script lives
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)

# The target repo is one level up from where ralph lives
REPO_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"

# Timestamp for log filenames (Pacific time)
TIMESTAMP=$(TZ="America/Los_Angeles" date +"%Y%m%d_%H%M%S")

# Log directory lives inside the ralph directory
LOG_DIR="${SCRIPT_DIR}/.ralph-logs"
mkdir -p "$LOG_DIR"

# Text log — always created, captures readable output
TEXT_LOG="${LOG_DIR}/ralph_${LLM}_${TIMESTAMP}.md"

# JSONL log — Claude only, on by default for Claude.
# Override with KEEP_JSONL=0 to disable.
if [ "$LLM" = "claude" ]; then
  KEEP_JSONL="${KEEP_JSONL:-1}"
else
  KEEP_JSONL="${KEEP_JSONL:-0}"
fi
if [ "$KEEP_JSONL" = "1" ] && [ "$LLM" = "claude" ]; then
  JSONL_LOG="${LOG_DIR}/ralph_${LLM}_${TIMESTAMP}.jsonl"
fi

# Prompt files — defaults to the three standard templates
PROMPT_FILES="${PROMPT_FILES:-${SCRIPT_DIR}/prompt-project.md ${SCRIPT_DIR}/prompt-sandbox.md ${SCRIPT_DIR}/prompt-base.md}"


# ============================================================================
# SECTION 3: RESOLVE THE AGENT BINARY
# ============================================================================

# Find the CLI binary for the selected LLM.
# Checks: env var override, PATH, then common install locations.
resolve_bin() {
  local bin_name="$1"
  shift
  # All remaining arguments are candidate paths
  local candidates=("$@")

  # 1) Check if the binary is already in PATH
  local found
  found="$(command -v "$bin_name" 2>/dev/null || true)"
  if [ -n "$found" ] && [ -x "$found" ]; then
    echo "$found"
    return 0
  fi

  # 2) Check common install locations
  local c
  for c in "${candidates[@]}"; do
    if [ -x "$c" ]; then
      echo "$c"
      return 0
    fi
  done

  # Not found
  return 1
}

if [ "$LLM" = "claude" ]; then
  # Allow override via CLAUDE_BIN env var
  if [ -n "${CLAUDE_BIN:-}" ] && [ -x "$CLAUDE_BIN" ]; then
    AGENT_BIN="$CLAUDE_BIN"
  else
    AGENT_BIN="$(resolve_bin claude \
      "$HOME/.claude/local/claude" \
      "$HOME/.local/bin/claude" \
      "/usr/local/bin/claude" \
      "/usr/bin/claude" \
      || true)"
  fi

elif [ "$LLM" = "codex" ]; then
  # Allow override via CODEX_BIN env var
  if [ -n "${CODEX_BIN:-}" ] && [ -x "$CODEX_BIN" ]; then
    AGENT_BIN="$CODEX_BIN"
  else
    AGENT_BIN="$(resolve_bin codex \
      "$HOME/.local/bin/codex" \
      "$HOME/.codex/local/codex" \
      "/usr/local/bin/codex" \
      "/usr/bin/codex" \
      || true)"
  fi

elif [ "$LLM" = "amp" ]; then
  # Allow override via AMP_BIN env var
  if [ -n "${AMP_BIN:-}" ] && [ -x "$AMP_BIN" ]; then
    AGENT_BIN="$AMP_BIN"
  else
    AGENT_BIN="$(resolve_bin amp \
      "$HOME/.local/bin/amp" \
      "/usr/local/bin/amp" \
      "/usr/bin/amp" \
      || true)"
  fi
fi

if [ -z "${AGENT_BIN:-}" ]; then
  echo "ERROR: $LLM CLI not found."
  echo "Make sure it is installed and in your PATH, or set the env var:"
  echo "  CLAUDE_BIN, CODEX_BIN, or AMP_BIN"
  exit 1
fi


# ============================================================================
# SECTION 4: PREFLIGHT CHECKS
# ============================================================================

# --- Check: prompt files exist ---
for pf in $PROMPT_FILES; do
  if [ ! -f "$pf" ]; then
    echo "ERROR: Prompt file not found: $pf"
    exit 1
  fi
done

# --- Check: jq is installed (required for Claude's NDJSON streaming) ---
if [ "$LLM" = "claude" ]; then
  if ! command -v jq &> /dev/null; then
    echo "ERROR: 'jq' is required for Claude but was not found."
    echo "Install with: sudo apt-get install -y jq"
    exit 1
  fi
fi

# --- Check: required Docker containers are running ---
# Only runs if CONTAINERS_ARG is non-empty.
if [ -n "$CONTAINERS_ARG" ]; then
  # Split comma-separated list into an array
  IFS=',' read -ra REQUIRED_CONTAINERS <<< "$CONTAINERS_ARG"
  MISSING_CONTAINERS=()

  for cname in "${REQUIRED_CONTAINERS[@]}"; do
    if ! docker ps --format '{{.Names}}' 2>/dev/null | grep -q "^${cname}$"; then
      MISSING_CONTAINERS+=("$cname")
    fi
  done

  if [ ${#MISSING_CONTAINERS[@]} -gt 0 ]; then
    echo "ERROR: Required Docker containers are not running:"
    for c in "${MISSING_CONTAINERS[@]}"; do
      echo "  - $c"
    done
    echo ""
    echo "Start them first with:  docker compose up -d"
    exit 1
  fi
  echo "  Docker containers: all running"
fi


# ============================================================================
# SECTION 5: BUILD THE PROMPT
# ============================================================================

# Concatenate all prompt files into a single string.
# Each file is separated by a newline.
PROMPT_TEXT=""
for pf in $PROMPT_FILES; do
  PROMPT_TEXT+="$(cat "$pf")"
  PROMPT_TEXT+=$'\n\n'
done


# ============================================================================
# SECTION 6: PRINT STARTUP BANNER
# ============================================================================

echo "Ralph Loop Runner"
echo "  LLM:        $LLM"
echo "  Binary:     $AGENT_BIN"
echo "  Iterations: $ITERATIONS"
if [ -n "$DANGEROUS_FLAG" ]; then
  echo "  Dangerous:  $DANGEROUS_ARG ($DANGEROUS_FLAG)"
else
  echo "  Dangerous:  $DANGEROUS_ARG (no flag)"
fi
echo "  Containers: ${CONTAINERS_ARG:-none}"
echo "  Sleep:      $SLEEP_ARG"
echo "  Log (text): $TEXT_LOG"
if [ -n "${JSONL_LOG:-}" ]; then
  echo "  Log (JSON): $JSONL_LOG"
fi
echo ""


# ============================================================================
# SECTION 7: SLEEP (if requested)
# ============================================================================

# Sleep before starting, if a non-zero duration was given.
# This is useful for delayed starts (e.g., schedule ralph to run later).
if [ "$SLEEP_ARG" != "0" ]; then
  echo "Sleeping for $SLEEP_ARG before starting..."
  sleep "$SLEEP_ARG"
  echo "Awake. Starting loop."
  echo ""
fi


# ============================================================================
# SECTION 8: MAIN LOOP
# ============================================================================

# Change to the target repo so the agent operates in the right directory
cd "$REPO_ROOT"

for ((i=1; i<=ITERATIONS; i++)); do
  echo ""
  echo "=========================================="
  echo "  Iteration $i of $ITERATIONS"
  echo "=========================================="
  echo ""

  echo "--- Iteration $i ---" >> "$TEXT_LOG"

  # --------------------------------------------------------------------------
  # Run the agent (LLM-specific)
  # --------------------------------------------------------------------------

  if [ "$LLM" = "claude" ]; then
    #
    # CLAUDE CODE
    #
    # Uses NDJSON streaming (--output-format stream-json) for real-time output.
    # The jq filter extracts text_delta events and prints them live.
    #
    # Pipeline: claude -> grep (filter non-JSON lines) -> [optional jsonl tee]
    #           -> jq (extract text) -> tee (log + stdout)
    #
    if [ -n "${JSONL_LOG:-}" ]; then
      # With JSONL logging: tee raw events to a .jsonl file
      "$AGENT_BIN" \
        -p "$PROMPT_TEXT" \
        $DANGEROUS_FLAG \
        --output-format stream-json \
        --verbose \
        --include-partial-messages \
        2>&1 \
        | grep --line-buffered '^{' \
        | tee -a "$JSONL_LOG" \
        | jq --unbuffered -rj '
            if .type == "stream_event" and .event.type? == "content_block_delta" and .event.delta.type? == "text_delta" then
              .event.delta.text
            elif .type == "stream_event" and .event.type? == "content_block_stop" then
              "\n"
            else
              empty
            end
          ' \
        | tee -a "$TEXT_LOG"
    else
      # Without JSONL logging: skip the raw event tee
      "$AGENT_BIN" \
        -p "$PROMPT_TEXT" \
        $DANGEROUS_FLAG \
        --output-format stream-json \
        --verbose \
        --include-partial-messages \
        2>&1 \
        | grep --line-buffered '^{' \
        | jq --unbuffered -rj '
            if .type == "stream_event" and .event.type? == "content_block_delta" and .event.delta.type? == "text_delta" then
              .event.delta.text
            elif .type == "stream_event" and .event.type? == "content_block_stop" then
              "\n"
            else
              empty
            end
          ' \
        | tee -a "$TEXT_LOG"
    fi

  elif [ "$LLM" = "codex" ]; then
    #
    # CODEX
    #
    # Runs in non-interactive exec mode.
    # Output goes straight to tee (no NDJSON parsing needed).
    #
    "$AGENT_BIN" exec \
      -C "$REPO_ROOT" \
      $DANGEROUS_FLAG \
      "$PROMPT_TEXT" \
      2>&1 | tee -a "$TEXT_LOG"

  elif [ "$LLM" = "amp" ]; then
    #
    # AMP
    #
    # TODO: Verify the correct amp CLI invocation.
    # For now, passes the prompt as the first argument with simple tee logging.
    # No NDJSON parsing needed (amp outputs plain text).
    #
    "$AGENT_BIN" \
      $DANGEROUS_FLAG \
      "$PROMPT_TEXT" \
      2>&1 | tee -a "$TEXT_LOG"
  fi

  # --------------------------------------------------------------------------
  # End of iteration
  # --------------------------------------------------------------------------

  echo "" | tee -a "$TEXT_LOG"
  echo "--- End of iteration $i ---" >> "$TEXT_LOG"

  # Check for the early-completion marker in the log.
  # If the agent outputs <promise>COMPLETE</promise>, we stop the loop.
  if grep -q "<promise>COMPLETE</promise>" "$TEXT_LOG" 2>/dev/null; then
    echo ""
    echo "All tasks complete after $i iterations." | tee -a "$TEXT_LOG"
    exit 0
  fi

done


# ============================================================================
# SECTION 9: DONE
# ============================================================================

echo ""
echo "Reached max iterations ($ITERATIONS)." | tee -a "$TEXT_LOG"

# Exit 1 = loop finished without seeing <promise>COMPLETE</promise>.
# Exit 0 only happens when the agent signals completion early (Section 8).
exit 1
