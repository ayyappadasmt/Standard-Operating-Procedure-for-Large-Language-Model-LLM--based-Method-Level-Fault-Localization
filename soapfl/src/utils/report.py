"""
Report Utilities
================
Formats and saves the final SOAPFL output (suspicious method list + rationale).
"""
from __future__ import annotations

import json
import os
import time
from typing import Optional

try:
    from rich.console import Console
    from rich.table   import Table
    from rich.panel   import Panel
    from rich         import box
    _RICH = True
    console = Console()
except ImportError:
    _RICH = False
    console = None  # type: ignore

from src.components.state_storage import MethodInfo, PipelineState
from config.settings import OUTPUT_DIR


def print_results(
    state: PipelineState,
    ranked_methods: list[MethodInfo],
    elapsed: float,
    token_summary: dict,
) -> None:
    """Pretty-print the final results to the terminal."""

    if _RICH and console:
        _print_rich(state, ranked_methods, elapsed, token_summary)
    else:
        _print_plain(state, ranked_methods, elapsed, token_summary)


def _print_plain(state, ranked_methods, elapsed, token_summary):
    sep = "=" * 70
    print(f"\n{sep}")
    print(f"  SOAPFL Results  |  Project: {state.project_name}  Bug: {state.bug_id}")
    print(sep)
    for rank, mi in enumerate(ranked_methods, 1):
        print(f"  #{rank}  [score={mi.suspiciousness_score}/10]  {mi.full_name}")
        if mi.suspiciousness_reason:
            print(f"       {mi.suspiciousness_reason[:120]}")
    if state.suspicious_class:
        print(f"\n  Suspicious class: {state.suspicious_class.full_name}")
    print(f"\n  Elapsed: {elapsed:.1f}s  |  Tokens: {token_summary['total_tokens']:,}")
    print(sep)


def _print_rich(state, ranked_methods, elapsed, token_summary):
    console.print()
    console.print(Panel(
        f"[bold cyan]SOAPFL Fault Localization Results[/bold cyan]\n"
        f"Project: [yellow]{state.project_name}[/yellow]  |  "
        f"Bug ID: [yellow]{state.bug_id}[/yellow]",
        box=box.DOUBLE_EDGE,
    ))

    table = Table(
        title="Suspicious Methods (ranked by suspiciousness score)",
        box=box.SIMPLE_HEAVY,
        show_lines=True,
    )
    table.add_column("Rank", style="bold", justify="center", width=6)
    table.add_column("Score", justify="center", width=7)
    table.add_column("Method", style="cyan", min_width=40)
    table.add_column("Rationale", style="white", min_width=50)

    for rank, mi in enumerate(ranked_methods, 1):
        color = "green" if rank == 1 else "yellow" if rank <= 3 else "white"
        table.add_row(
            f"[{color}]#{rank}[/{color}]",
            f"[{color}]{mi.suspiciousness_score}/10[/{color}]",
            mi.full_name,
            mi.suspiciousness_reason[:200] or "—",
        )
    console.print(table)

    if state.suspicious_class:
        console.print(Panel(
            f"[bold]Suspicious Class:[/bold] [cyan]{state.suspicious_class.full_name}[/cyan]\n"
            f"[dim]{state.suspicious_class_reason[:300]}[/dim]",
            title="Class-Level Result",
            border_style="blue",
        ))

    console.print(Panel(
        f"⏱  Elapsed: [bold]{elapsed:.1f} s[/bold]\n"
        f"🔢 Input tokens:  {token_summary['input_tokens']:,}\n"
        f"🔢 Output tokens: {token_summary['output_tokens']:,}\n"
        f"🔢 Total tokens:  {token_summary['total_tokens']:,}",
        title="Cost Analysis",
        border_style="dim",
    ))


def save_results(
    state: PipelineState,
    ranked_methods: list[MethodInfo],
    elapsed: float,
    token_summary: dict,
) -> str:
    """Save results to a JSON file in the output directory."""
    result = {
        "project": state.project_name,
        "bug_id":  state.bug_id,
        "test_class": state.test_class,
        "failed_tests": state.failed_tests,
        "suspicious_class": state.suspicious_class.full_name if state.suspicious_class else None,
        "suspicious_class_reason": state.suspicious_class_reason,
        "possible_causes": state.possible_causes,
        "suspicious_methods": [
            {
                "rank":   rank,
                "score":  mi.suspiciousness_score,
                "method": mi.full_name,
                "reason": mi.suspiciousness_reason,
            }
            for rank, mi in enumerate(ranked_methods, 1)
        ],
        "cost": {
            "elapsed_seconds": round(elapsed, 2),
            **token_summary,
        },
    }

    fname = f"{state.project_name}_{state.bug_id}_result.json"
    path  = os.path.join(OUTPUT_DIR, fname)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=2)

    msg = f"\nResults saved to {path}"
    if _RICH and console:
        console.print(f"\n[dim]Results saved to[/dim] [underline]{path}[/underline]")
    else:
        print(msg)
    return path
