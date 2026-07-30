#!/usr/bin/env python3
"""
End-to-end test for the gRPC integration of Sexta-Feira OS.

Tests:
1. gRPC server health check
2. Chat streaming
3. Memory CRUD (create, get, update, delete)
4. Memory graph (link, search, neighbours)
5. Action dispatch
6. Automation workflow trigger (graceful failure if n8n offline)

Run with:
    python scripts/test_grpc_flow.py
"""
import asyncio
import sys
import time

sys.path.insert(0, "backend-core")

import grpc
from app.grpc.cognitive_core_pb2 import (
    HealthCheckRequest, ChatRequest, CreateMemoryRequest,
    GetMemoryRequest, UpdateMemoryRequest, DeleteMemoryRequest,
    SearchMemoryRequest, LinkMemoriesRequest, UnlinkMemoriesRequest,
    GetNeighboursRequest, GetMemoryGraphRequest, DispatchActionRequest,
)
from app.grpc.cognitive_core_pb2_grpc import CognitiveCoreStub
from app.grpc.automation_events_pb2 import TriggerWorkflowRequest
from app.grpc.automation_events_pb2_grpc import AutomationServiceStub

SERVER = "127.0.0.1:50051"
PASS = 0
FAIL = 0


def ok(msg: str) -> None:
    global PASS
    PASS += 1
    print(f"  ✅ {msg}")


def fail(msg: str) -> None:
    global FAIL
    FAIL += 1
    print(f"  ❌ {msg}")


async def test_health(stub: CognitiveCoreStub) -> None:
    print("\n📋 Health Check")
    try:
        resp = await stub.CheckHealth(HealthCheckRequest())
        assert resp.status in ("ok", "degraded")
        assert resp.version
        ok(f"Status={resp.status}, version={resp.version}, voice={resp.voice_available}")
    except Exception as e:
        fail(f"Health check failed: {e}")


async def test_chat(stub: CognitiveCoreStub) -> None:
    print("\n📋 Chat Streaming")
    try:
        tokens = []
        async for resp in stub.Chat(ChatRequest(message="Diga 'olá' em português.")):
            if resp.HasField("text_chunk"):
                tokens.append(resp.text_chunk)
        reply = "".join(tokens)
        assert len(reply) > 0, "Empty reply"
        ok(f"Chat stream returned {len(reply)} chars: {reply[:60]}...")
    except Exception as e:
        fail(f"Chat stream failed: {e}")


async def test_memory_crud(stub: CognitiveCoreStub) -> str:
    print("\n📋 Memory CRUD")
    memory_id = ""

    # Create
    try:
        created = await stub.CreateMemory(
            CreateMemoryRequest(content="Teste de integração gRPC", title="Teste", kind=1)
        )
        memory_id = created.id
        assert memory_id
        ok(f"Created memory: id={memory_id[:8]}... title={created.title}")
    except Exception as e:
        fail(f"Create memory failed: {e}")
        return ""

    # Get
    try:
        got = await stub.GetMemory(GetMemoryRequest(id=memory_id))
        assert got.id == memory_id
        ok(f"Get memory: content={got.content[:40]}...")
    except Exception as e:
        fail(f"Get memory failed: {e}")

    # Update
    try:
        updated = await stub.UpdateMemory(
            UpdateMemoryRequest(id=memory_id, content="Teste de integração gRPC — atualizado")
        )
        assert "atualizado" in updated.content
        ok(f"Update memory: {updated.content[:40]}...")
    except Exception as e:
        fail(f"Update memory failed: {e}")

    # Delete
    try:
        deleted = await stub.DeleteMemory(DeleteMemoryRequest(id=memory_id))
        assert deleted.success
        ok(f"Deleted memory: id={deleted.deleted_id[:8]}...")
    except Exception as e:
        fail(f"Delete memory failed: {e}")

    return memory_id


async def test_memory_graph(stub: CognitiveCoreStub) -> None:
    print("\n📋 Memory Graph")
    # Create two memories and link them
    try:
        a = await stub.CreateMemory(CreateMemoryRequest(content="Gosto de viajar", kind=1))
        b = await stub.CreateMemory(CreateMemoryRequest(content="Gosto de praia", kind=1))
        assert a.id and b.id
        ok(f"Created two memories: {a.id[:8]}... {b.id[:8]}...")
    except Exception as e:
        fail(f"Create memories for graph failed: {e}")
        return

    # Link
    try:
        link = await stub.LinkMemories(
            LinkMemoriesRequest(source_id=a.id, target_id=b.id, relation=1, label="gosta_de")
        )
        ok(f"Linked memories: id={link.id[:8]}...")
    except Exception as e:
        fail(f"Link memories failed: {e}")

    # Neighbours
    try:
        nb = await stub.GetNeighbours(GetNeighboursRequest(memory_id=a.id))
        ok(f"Neighbours: {len(nb.neighbours)} neighbour(s), {len(nb.links)} link(s)")
    except Exception as e:
        fail(f"Get neighbours failed: {e}")

    # Search
    try:
        sr = await stub.SearchMemory(SearchMemoryRequest(query="praia", limit=5))
        ok(f"Search 'praia': {len(sr.results)} result(s)")
    except Exception as e:
        fail(f"Search memory failed: {e}")

    # Graph
    try:
        graph = await stub.GetMemoryGraph(GetMemoryGraphRequest(max_nodes=50))
        ok(f"Graph: {len(graph.nodes)} node(s), {len(graph.links)} link(s)")
    except Exception as e:
        fail(f"Get graph failed: {e}")

    # Unlink and clean up
    try:
        await stub.UnlinkMemories(UnlinkMemoriesRequest(link_id=link.id))
        await stub.DeleteMemory(DeleteMemoryRequest(id=a.id))
        await stub.DeleteMemory(DeleteMemoryRequest(id=b.id))
        ok("Cleaned up graph test memories")
    except Exception as e:
        fail(f"Cleanup failed: {e}")


async def test_actions(stub: CognitiveCoreStub) -> None:
    print("\n📋 Action Dispatch")
    try:
        resp = await stub.DispatchAction(
            DispatchActionRequest(device="celular", action="open_app", params={"app": "maps"})
        )
        # Actions may fail if device is offline, but command should be accepted
        ok(f"Action dispatched: accepted={resp.accepted}, command_id={resp.command_id[:8] if resp.command_id else 'N/A'}...")
    except Exception as e:
        fail(f"Action dispatch failed: {e}")


async def test_automation(stub_auto: AutomationServiceStub) -> None:
    print("\n📋 Automations")
    try:
        resp = await stub_auto.TriggerWorkflow(
            TriggerWorkflowRequest(workflow_id="test-workflow", params={"test": "true"})
        )
        ok(f"Workflow trigger: accepted={resp.accepted}, execution_id={resp.execution_id[:8] if resp.execution_id else 'N/A'}...")
    except Exception as e:
        fail(f"Workflow trigger failed: {e}")

    try:
        workflows = await stub_auto.ListWorkflows()
        ok(f"Listed {len(workflows.workflows)} workflow(s)")
    except Exception as e:
        fail(f"List workflows failed: {e}")


async def main() -> None:
    print("=" * 60)
    print("🧪 Sexta-Feira OS — gRPC Integration Test Suite")
    print("=" * 60)
    print(f"\nServer: {SERVER}")
    print(f"Started: {time.strftime('%H:%M:%S')}")

    # Connect
    channel = grpc.aio.insecure_channel(SERVER)
    stub = CognitiveCoreStub(channel)
    stub_auto = AutomationServiceStub(channel)

    try:
        # Wait for channel to be ready
        await grpc.channel_ready_future(channel)
        ok("gRPC channel ready")
    except Exception as e:
        fail(f"Channel not ready — is the gRPC server running on {SERVER}? {e}")
        print(f"\n📋 Run the backend with: cd backend-core && python -m app.main")
        print(f"   Or start manually via: .venv/Scripts/python -m app.main")
        channel.close()
        sys.exit(1)

    try:
        await test_health(stub)
        await test_chat(stub)
        await test_memory_crud(stub)
        await test_memory_graph(stub)
        await test_actions(stub)
        await test_automation(stub_auto)
    finally:
        channel.close()

    # Summary
    total = PASS + FAIL
    print("\n" + "=" * 60)
    print(f"📊 Results: {PASS}/{total} passed, {FAIL} failed")
    print("=" * 60)

    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
