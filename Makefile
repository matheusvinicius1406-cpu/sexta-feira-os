# ─────────────────────────────────────────────────────────────────
# Sexta-Feira OS — Build & Dev Commands
# ─────────────────────────────────────────────────────────────────

.PHONY: help proto proto-python proto-csharp test test-py test-rust \
        lint lint-py check build build-ui build-maui clean

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ── Proto Generation ────────────────────────────────────────────

proto: proto-python proto-csharp  ## Generate all gRPC stubs

proto-python:  ## Generate Python gRPC stubs from .proto files
	@echo "📡 Generating Python gRPC stubs..."
	@cd backend-core && bash scripts/generate_protos.sh

proto-csharp:  ## Generate C# gRPC stubs from .proto files
	@echo "📡 Generating C# gRPC stubs..."
	@cd apps/maui/CognitiveHUD && dotnet build -t:Protobuf 2>/dev/null || \
		echo "⚠️  C# proto generation requires Grpc.Tools NuGet package"

# ── Build ───────────────────────────────────────────────────────

build: build-ui build-maui  ## Build all .NET projects

build-ui:  ## Build UI Engine (class library)
	@cd ui-engine && dotnet build --nologo -v q

build-maui:  ## Build MAUI CognitiveHUD (Android)
	@cd apps/maui/CognitiveHUD && dotnet build -f net8.0-android --nologo -v q

# ── Test & Lint ─────────────────────────────────────────────────

test: test-py  ## Run all tests

test-py:  ## Run Python backend tests
	@cd backend-core && python -m pytest -q

lint: lint-py  ## Run all linters

lint-py:  ## Lint Python code with ruff
	@cd backend-core && python -m ruff check app tests

check: lint-py  ## Alias for lint-py

# ── Clean ───────────────────────────────────────────────────────

clean:  ## Remove build artifacts
	@rm -rf ui-engine/bin ui-engine/obj
	@rm -rf apps/maui/CognitiveHUD/bin apps/maui/CognitiveHUD/obj
	@rm -rf backend-core/app/grpc/*_pb2*.py
	@echo "🧹 Clean"

# ── Setup ───────────────────────────────────────────────────────

setup:  ## Install Python dependencies
	@cd backend-core && python -m pip install -r requirements.txt
