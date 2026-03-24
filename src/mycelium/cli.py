"""Mycelium CLI — all commands."""
from __future__ import annotations
import asyncio
import sys
from datetime import datetime
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

console = Console()


def _find_config() -> Path:
    """Find mycelium.toml in current directory or parents."""
    current = Path.cwd()
    for parent in [current] + list(current.parents):
        candidate = parent / "mycelium.toml"
        if candidate.exists():
            return candidate
    # Default to current directory
    return current / "mycelium.toml"


def _load_orchestrator():
    """Load config and create orchestrator."""
    from mycelium.shared.config import load_config
    from mycelium.orchestrator.orchestrator import Orchestrator
    config_path = _find_config()
    if not config_path.exists():
        console.print(f"[red]Config not found: {config_path}[/red]")
        sys.exit(1)
    config = load_config(config_path)
    config.data_dir.mkdir(parents=True, exist_ok=True)
    return Orchestrator(config)


@click.group()
def cli():
    """Mycelium — Self-enriching knowledge engine."""
    pass


@cli.command()
def init():
    """Initialize Mycelium: create data dirs, init DBs, verify dependencies."""
    config_path = _find_config()
    if not config_path.exists():
        console.print(f"[red]No mycelium.toml found. Create one first.[/red]")
        return

    from mycelium.shared.config import load_config
    config = load_config(config_path)
    config.data_dir.mkdir(parents=True, exist_ok=True)

    # Init brainstem DB
    from mycelium.brainstem.store import BrainstemStore
    store = BrainstemStore(config.data_dir / "brainstem.db")
    store.initialize()
    store.close()
    console.print("[green]\\u2713[/green] Brainstem DB initialized")

    # Init observation DB
    from mycelium.observe.store import ObservationStore
    obs = ObservationStore(config.data_dir / "observation.db")
    obs.close()
    console.print("[green]\\u2713[/green] Observation DB initialized")

    # Check Claude CLI
    async def check_claude():
        from mycelium.shared.llm import ClaudeCLI
        llm = ClaudeCLI()
        return await llm.health_check()

    claude_ok = asyncio.run(check_claude())
    if claude_ok:
        console.print("[green]\\u2713[/green] Claude CLI available")
    else:
        console.print("[yellow]![/yellow] Claude CLI not found — learn/serve will fail")

    # Check NATS
    console.print("[green]\\u2713[/green] Mycelium initialized at", str(config.data_dir))


@cli.command()
@click.option("--calls", default=50, help="Call budget for this learn cycle")
@click.option("--quick", is_flag=True, help="Quick learn (20 calls)")
@click.option("--deep", is_flag=True, help="Deep learn (100 calls)")
def learn(calls: int, quick: bool, deep: bool):
    """Run a learn cycle."""
    if quick:
        calls = 20
    elif deep:
        calls = 100

    console.print(f"Starting learn cycle with budget={calls}")
    orch = _load_orchestrator()

    session = asyncio.run(orch.learn(budget=calls))

    console.print(f"\n[green]Learn cycle complete[/green]")
    console.print(f"  Documents: {len(session.documents_processed)}")
    console.print(f"  Entities:  {session.entities_created}")
    console.print(f"  Edges:     {session.edges_created}")
    console.print(f"  Agents:    {session.agents_discovered}")
    console.print(f"  Spillovers:{session.spillovers}")
    console.print(f"  Calls:     {session.spent}/{session.budget}")


@cli.command()
@click.option("--port", default=8000, help="Port to serve on")
@click.option("--host", default="127.0.0.1", help="Host to bind to")
def serve(port: int, host: str):
    """Start the serve API."""
    import uvicorn
    from mycelium.serve.api import create_app

    app = create_app(host=host)
    console.print(f"Serving on {host}:{port}")
    uvicorn.run(app, host=host, port=port)


@cli.command()
@click.argument("query")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def ask(query: str, as_json: bool):
    """Ask a question."""
    import json as json_mod
    orch = _load_orchestrator()

    async def run_query():
        from mycelium.serve.intent import IntentParser
        from mycelium.serve.router import AgentRouter
        from mycelium.serve.reasoner import ParallelReasoner
        from mycelium.serve.synthesizer import Synthesizer

        intent = IntentParser(orch.graph).parse(query)
        agents = AgentRouter().select(intent, orch.agent_manager.agents)

        if not agents:
            return {"answer": "No agents available. Run 'mycelium learn' first.", "agents_used": []}

        agent_details = {a.agent_id: orch.agent_manager.get(a.agent_id) for a in agents}
        reasoner = ParallelReasoner(orch._llm)
        responses = await reasoner.reason(query, agents, agent_details, orch.graph)

        synthesizer = Synthesizer(orch._llm)
        result = await synthesizer.synthesize(query, responses)

        return {
            "answer": result.answer,
            "rationale": result.rationale_chain,
            "unknowns": result.unknowns,
            "follow_ups": result.follow_ups,
            "agents_used": [a.agent_name for a in agents],
        }

    result = asyncio.run(run_query())

    if as_json:
        click.echo(json_mod.dumps(result, indent=2))
    else:
        console.print(f"\n{result['answer']}")
        if result.get("agents_used"):
            console.print(f"\n[dim]Agents: {', '.join(result['agents_used'])}[/dim]")


@cli.command()
@click.option("--full", is_flag=True, help="Show detailed status")
def status(full: bool):
    """Show system status."""
    orch = _load_orchestrator()
    s = orch.status()

    table = Table(title="Mycelium Status")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Graph Nodes", str(s["graph"]["nodes"]))
    table.add_row("Graph Edges", str(s["graph"]["edges"]))
    table.add_row("Agents (active)", str(s["agents"]["active"]))
    table.add_row("Agents (total)", str(s["agents"]["total"]))
    table.add_row("Connectors", ", ".join(s["connectors"]) or "none")

    if s["last_session"]["id"]:
        table.add_row("Last Session", s["last_session"]["status"])
        table.add_row("Last Entities", str(s["last_session"]["entities_created"]))

    console.print(table)


@cli.command()
def history():
    """Show past learn sessions."""
    orch = _load_orchestrator()
    sessions = orch.session_store.list_sessions()

    if not sessions:
        console.print("No learn sessions yet. Run 'mycelium learn' first.")
        return

    table = Table(title="Learn Sessions")
    table.add_column("ID", style="dim", max_width=12)
    table.add_column("Status")
    table.add_column("Budget")
    table.add_column("Spent")
    table.add_column("Entities")
    table.add_column("Edges")
    table.add_column("Started")

    for s in sessions:
        table.add_row(
            s.id[:12],
            s.status,
            str(s.budget),
            str(s.spent),
            str(s.entities_created),
            str(s.edges_created),
            s.started_at.strftime("%Y-%m-%d %H:%M"),
        )

    console.print(table)


@cli.command()
def observe():
    """Launch live TUI dashboard."""
    from mycelium.shared.config import load_config
    config = load_config(_find_config())
    from mycelium.observe.store import ObservationStore
    from mycelium.observe.tui import MyceliumTUI
    store = ObservationStore(config.data_dir / "observation.db")
    app = MyceliumTUI(store)
    app.run()


@cli.group()
def agents():
    """Manage discovered agents."""
    pass


@agents.command("list")
def agents_list():
    """List all agents."""
    orch = _load_orchestrator()
    table = Table(title="Agents")
    table.add_column("ID", style="dim", max_width=12)
    table.add_column("Name")
    table.add_column("Domain")
    table.add_column("Status")
    table.add_column("Nodes")
    table.add_column("Pinned")

    for a in orch.agent_manager.agents:
        table.add_row(
            a.id[:12], a.name, a.domain, a.status,
            str(len(a.node_ids)), "Yes" if a.pinned else "",
        )

    console.print(table)


@agents.command("rename")
@click.argument("agent_id")
@click.argument("new_name")
def agents_rename(agent_id: str, new_name: str):
    """Rename an agent."""
    orch = _load_orchestrator()
    if orch.agent_manager.rename(agent_id, new_name):
        console.print(f"[green]Renamed to {new_name}[/green]")
    else:
        console.print(f"[red]Agent {agent_id} not found[/red]")


@agents.command("pin")
@click.argument("agent_id")
def agents_pin(agent_id: str):
    """Pin an agent (prevent retirement)."""
    orch = _load_orchestrator()
    if orch.agent_manager.pin(agent_id):
        console.print(f"[green]Agent pinned[/green]")
    else:
        console.print(f"[red]Agent {agent_id} not found[/red]")


@cli.command()
@click.option("--path", default=None, help="Backup destination")
def backup(path: str | None):
    """Create atomic backup of all data."""
    import shutil
    from mycelium.shared.config import load_config
    config = load_config(_find_config())

    dest = Path(path) if path else config.data_dir / "backups"
    dest.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_dir = dest / f"backup-{timestamp}"
    backup_dir.mkdir()

    for f in ["brainstem.db", "observation.db", "embeddings.faiss", "embeddings.idx2id.json"]:
        src = config.data_dir / f
        if src.exists():
            shutil.copy2(src, backup_dir / f)

    console.print(f"[green]Backup saved to {backup_dir}[/green]")
