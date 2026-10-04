#!/bin/sh
# Startup entrypoint for the Q-Health backend.
#
# On Render the persistent disk is mounted root-owned and is only available at
# runtime (never during the build or pre-deploy steps). The application itself
# must run as the non-root qhealth user (uid/gid 10001). This script therefore
# starts as root, makes the runtime storage path writable by qhealth, then drops
# privileges and execs the server command so the application process never runs
# as root.
#
# When the container already starts as a non-root user (for example a plain
# `docker run --user`), the script verifies the runtime path is writable and
# fails closed if it is not, rather than starting with broken storage.
set -eu

RUNTIME="${QHEALTH_STORAGE_ROOT:-/runtime}"
APP_USER="qhealth"

if [ "$(id -u)" = "0" ]; then
  mkdir -p "$RUNTIME/data/datasets" "$RUNTIME/models" "$RUNTIME/experiments"
  # Render mounts persistent disks at runtime. Avoid recursively chowning the
  # entire disk on every restart; large experiment/model stores can otherwise
  # delay the HTTP health check and make the service flap.
  MARKER="$RUNTIME/.qhealth_permissions_initialized"
  if [ ! -f "$MARKER" ]; then
    if chown -R "$APP_USER:$APP_USER" "$RUNTIME"; then
      : > "$MARKER"
      chown "$APP_USER:$APP_USER" "$MARKER" 2>/dev/null || true
    else
      echo "[entrypoint] unable to prepare persistent runtime ownership" >&2
    fi
  else
    chown "$APP_USER:$APP_USER" "$RUNTIME" "$RUNTIME/data" "$RUNTIME/models" "$RUNTIME/experiments" 2>/dev/null || true
  fi
  if command -v setpriv >/dev/null 2>&1; then
    exec setpriv --reuid="$APP_USER" --regid="$APP_USER" --init-groups "$@"
  fi
  # Fallback if setpriv is unavailable: drop privileges via Python.
  exec python -c 'import os, sys; os.setgroups([]); os.setgid(10001); os.setuid(10001); os.execvp(sys.argv[1], sys.argv[1:])' "$@"
fi

if [ ! -w "$RUNTIME" ]; then
  echo "[entrypoint] runtime path $RUNTIME is not writable by uid $(id -u)" >&2
  exit 1
fi

exec "$@"
