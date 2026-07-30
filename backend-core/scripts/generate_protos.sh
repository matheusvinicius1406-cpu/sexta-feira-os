#!/usr/bin/env bash
# generate_protos.sh — Generate Python gRPC stubs from .proto files
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
PROTO_DIR="$REPO_ROOT/shared/protobuf"
OUT_DIR="$REPO_ROOT/backend-core/app/grpc"
VENV_PYTHON="$REPO_ROOT/backend-core/.venv/Scripts/python"

mkdir -p "$OUT_DIR"

echo "📡 Generating Python gRPC stubs..."
"$VENV_PYTHON" -m grpc_tools.protoc \
    -I"$PROTO_DIR" \
    --python_out="$OUT_DIR" \
    --grpc_python_out="$OUT_DIR" \
    "$PROTO_DIR"/*.proto

# Fix relative imports in generated files (make them absolute under app.grpc).
# Only fix imports of our own _pb2 modules — leave google.protobuf untouched.
for f in "$OUT_DIR"/*_pb2*.py; do
    if [ -f "$f" ]; then
        sed -i 's/^from \([a-z].*_pb2\)/from app.grpc.\1/' "$f"
        sed -i 's/^import \([a-z].*_pb2\)/from app.grpc import \1/' "$f"
        # Fix the grpc import too (but only for local modules)
        sed -i 's/^from \([a-z].*_pb2_grpc\)/from app.grpc.\1/' "$f"
    fi
done

# Fix google.protobuf imports that were incorrectly prefixed
for f in "$OUT_DIR"/*_pb2*.py; do
    if [ -f "$f" ]; then
        sed -i 's/from app\.grpc\.google\.protobuf/from google.protobuf/g' "$f"
    fi
done

# Create __init__.py if missing
if [ ! -f "$OUT_DIR/__init__.py" ]; then
    cat > "$OUT_DIR/__init__.py" << 'PYEOF'
# gRPC stubs for Sexta-Feira OS Cognitive Protocol
# Auto-generated — do not edit manually
PYEOF
fi

echo "✅ Stubs generated in $OUT_DIR"
echo "   Files:"
ls -1 "$OUT_DIR"/*_pb2*.py 2>/dev/null || echo "   (none)"
