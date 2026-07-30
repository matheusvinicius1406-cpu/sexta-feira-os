#!/usr/bin/env python3
"""
E2E validation script for Sexta-Feira OS gRPC integration.

Starts the backend server as a subprocess, waits for it to be ready,
runs the full gRPC test suite, then cleanly shuts down.

Usage:
    cd backend-core
    python ../scripts/run_e2e_test.py
"""
import asyncio
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = REPO_ROOT / "backend-core"
SERVER_LOG = REPO_ROOT / "tmp" / "server_e2e.log"
PASS = 0
FAIL = 0


def log(msg: str) -> None:
    print(f"  {msg}")


def ok(msg: str) -> None:
    global PASS
    PASS += 1
    log(f"  [PASS] {msg}")


def fail(msg: str) -> None:
    global FAIL
    FAIL += 1
    log(f"  [FAIL] {msg}")


async def wait_for_server(url: str, timeout: float = 30.0) -> bool:
    """Wait for the HTTP server to respond to health checks."""
    import urllib.request
    start = time.time()
    while time.time() - start < timeout:
        try:
            resp = urllib.request.urlopen(f"{url}/api/v1/health", timeout=2)
            if resp.status == 200:
                data = json.loads(resp.read().decode())
                log(f"Server ready: status={data.get('status')}, version={data.get('version')}")
                return True
        except Exception:
            pass
        await asyncio.sleep(1)
    return False


async def test_grpc_flow():
    """Run the gRPC test suite against the running server."""
    import grpc
    from app.grpc.cognitive_core_pb2 import (
        HealthCheckRequest, CreateMemoryRequest, DeleteMemoryRequest,
        SearchMemoryRequest, GetMemoryGraphRequest,
        LinkMemoriesRequest, UnlinkMemoriesRequest,
    )
    from app.grpc.cognitive_core_pb2_grpc import CognitiveCoreStub

    channel = grpc.aio.insecure_channel("127.0.0.1:50051")
    stub = CognitiveCoreStub(channel)

    try:
        # ── 1. Health ──────────────────────────────────
        log("1. Health Check...")
        health = await stub.CheckHealth(HealthCheckRequest())
        assert health.status in ("ok", "degraded")
        assert health.version
        ok(f"Status={health.status}, version={health.version}, voice={health.voice_available}")

        # ── 2. Memory Create ───────────────────────────
        log("2. Memory Create...")
        created = await stub.CreateMemory(CreateMemoryRequest(
            content="Teste de integracao gRPC E2E", kind=1))
        assert created.id
        mem_id = created.id
        ok(f"Created: id={mem_id[:12]}..., content={created.content[:40]}")

        # ── 3. Memory Delete ───────────────────────────
        log("3. Memory Delete...")
        deleted = await stub.DeleteMemory(DeleteMemoryRequest(id=mem_id))
        assert deleted.success
        ok(f"Deleted: success={deleted.success}")

        # ── 4. Memory Search ───────────────────────────
        log("4. Memory Search...")
        # Create a memory first so we have something to search
        await stub.CreateMemory(CreateMemoryRequest(
            content="Gosto de viajar para praias", kind=1))
        search = await stub.SearchMemory(SearchMemoryRequest(query="praia", limit=5))
        ok(f"Search 'praia': {len(search.results)} result(s)")

        # ── 5. Memory Graph ────────────────────────────
        log("5. Memory Graph...")
        graph = await stub.GetMemoryGraph(GetMemoryGraphRequest(max_nodes=50))
        ok(f"Graph: {len(graph.nodes)} node(s), {len(graph.links)} link(s)")

        # ── 6. Link operations ──────────────────────────
        log("6. Link/Unlink...")
        a = await stub.CreateMemory(CreateMemoryRequest(content="Node A link test", kind=1))
        b = await stub.CreateMemory(CreateMemoryRequest(content="Node B link test", kind=1))
        link = await stub.LinkMemories(LinkMemoriesRequest(
            source_id=a.id, target_id=b.id, relation=1, label="test_link"))
        assert link.id
        ok(f"Linked: id={link.id[:12]}...")

        unlinked = await stub.UnlinkMemories(UnlinkMemoriesRequest(link_id=link.id))
        assert unlinked.success
        ok(f"Unlinked: success={unlinked.success}")

        # Cleanup
        await stub.DeleteMemory(DeleteMemoryRequest(id=a.id))
        await stub.DeleteMemory(DeleteMemoryRequest(id=b.id))

        log("All gRPC integration tests completed!")

    finally:
        await channel.close()


async def main():
    # Ensure we're in the backend-core directory
    os.chdir(str(BACKEND_DIR))
    sys.path.insert(0, str(BACKEND_DIR))

    # Ensure tmp dir exists
    (REPO_ROOT / "tmp").mkdir(exist_ok=True)

    # Kill only the specific port processes, not all Python
    log("Checking for previous server on port 8000/50051...")
    import urllib.request
    try:
        resp = urllib.request.urlopen("http://127.0.0.1:8000/api/v1/health", timeout=2)
        if resp.status:
            log("Old server still running — skipping clean start")
    except Exception:
        log("Port 8000 free — starting fresh")

    # Start server
    log("Starting backend server (FastAPI + gRPC)...")
    server_log = open(SERVER_LOG, "w", buffering=1)
    server_proc = subprocess.Popen(
        [sys.executable, "-m", "app.main"],
        cwd=str(BACKEND_DIR),
        stdout=server_log,
        stderr=subprocess.STDOUT,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0,
    )
    log(f"Server PID: {server_proc.pid}")

    try:
        # Wait for server to be ready
        ready = await wait_for_server("http://127.0.0.1:8000", timeout=20)
        if not ready:
            fail("Server failed to start within 20s")
            log("--- Last 30 lines of server log ---")
            with open(SERVER_LOG) as f:
                lines = f.readlines()
                for line in lines[-30:]:
                    log(line.rstrip())
            server_proc.terminate()
            return 1

        # Run tests
        await test_grpc_flow()

    finally:
        # Clean shutdown
        log("Shutting down server...")
        if sys.platform == "win32":
            subprocess.run(["taskkill", "/F", "/PID", str(server_proc.pid)], capture_output=True)
        else:
            server_proc.terminate()
            try:
                server_proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server_proc.kill()
        server_log.close()

    # Summary
    total = PASS + FAIL
    log("=" * 50)
    log(f"Results: {PASS}/{total} passed, {FAIL} failed")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
