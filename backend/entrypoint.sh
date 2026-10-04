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
  # The disk mount is root-owned; hand the runtime tree to the app user.
  chown -R "$APP_USER:$APP_USER" "$RUNTIME" 2>/dev/null || true
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
