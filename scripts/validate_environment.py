#!/usr/bin/env python3
"""
Environment validation script for Harmonia Memory Storage System.
Run this script to validate that the development environment is properly set up.
"""
import sys
import subprocess
import sqlite3
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel


def main():
    """Main validation function."""
    console = Console()
    
    console.print(Panel.fit(
        "[bold blue]Harmonia Memory Storage System[/bold blue]\n"
        "[dim]Environment Validation[/dim]",
        border_style="blue"
    ))
    
    results = []
    
    # Check Python version
    python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    python_ok = sys.version_info >= (3, 11)
    results.append(("Python Version", python_version, "✅" if python_ok else "❌"))
    
    # Check virtual environment
    venv_path = Path(sys.executable).parent.parent
    venv_ok = venv_path.name == ".venv"
    venv_status = f"Running in {venv_path.name}" if venv_ok else f"Not in .venv (in {venv_path.name})"
    results.append(("Virtual Environment", venv_status, "✅" if venv_ok else "❌"))
    
    # Check SQLite FTS5
    try:
        conn = sqlite3.connect(":memory:")
        conn.execute("CREATE VIRTUAL TABLE test_fts USING fts5(content)")
        conn.close()
        fts5_ok = True
        fts5_status = "Available"
    except Exception as e:
        fts5_ok = False
        fts5_status = f"Error: {e}"
    results.append(("SQLite FTS5", fts5_status, "✅" if fts5_ok else "❌"))
    
    # Check Ollama
    try:
        result = subprocess.run(
            ["ollama", "list"], 
            capture_output=True, 
            text=True, 
            timeout=5
        )
        ollama_ok = result.returncode == 0
        ollama_status = "Available" if ollama_ok else f"Error: {result.stderr.strip()}"
    except (FileNotFoundError, subprocess.TimeoutExpired):
        ollama_ok = False
        ollama_status = "Not installed or not responding"
    results.append(("Ollama", ollama_status, "✅" if ollama_ok else "⚠️"))
    
    # Check key packages
    key_packages = [
        "fastapi", "uvicorn", "pydantic", "sqlalchemy", 
        "ollama", "pytest", "black", "rich"
    ]
    
    package_results = []
    all_packages_ok = True
    
    for package in key_packages:
        try:
            __import__(package)
            package_results.append((package, "✅"))
        except ImportError:
            package_results.append((package, "❌"))
            all_packages_ok = False
    
    results.append(("Key Packages", f"{len([r for r in package_results if r[1] == '✅'])}/{len(key_packages)} installed", "✅" if all_packages_ok else "❌"))
    
    # Check project structure
    project_root = Path(__file__).parent.parent
    required_dirs = [
        "src", "tests", "scripts", "config", "docs", 
        "data", "logs", "feature/initial-design"
    ]
    
    missing_dirs = []
    for dir_path in required_dirs:
        if not (project_root / dir_path).exists():
            missing_dirs.append(dir_path)
    
    structure_ok = len(missing_dirs) == 0
    structure_status = "Complete" if structure_ok else f"Missing: {', '.join(missing_dirs)}"
    results.append(("Project Structure", structure_status, "✅" if structure_ok else "❌"))
    
    # Create results table
    table = Table(title="Environment Validation Results")
    table.add_column("Component", style="bold")
    table.add_column("Status")
    table.add_column("Result", justify="center")
    
    for component, status, result in results:
        table.add_row(component, status, result)
    
    console.print(table)
    
    # Package details table
    if package_results:
        console.print("\n")
        package_table = Table(title="Package Import Status")
        package_table.add_column("Package", style="bold")
        package_table.add_column("Status", justify="center")
        
        for package, status in package_results:
            package_table.add_row(package, status)
        
        console.print(package_table)
    
    # Overall status
    all_critical_ok = all(result == "✅" for component, _, result in results if component != "Ollama")
    overall_status = "✅ Ready for development" if all_critical_ok else "❌ Issues need resolution"
    
    console.print(f"\n[bold]Overall Status:[/bold] {overall_status}")
    
    if not all_critical_ok:
        console.print("\n[red]Please resolve the issues above before proceeding with development.[/red]")
        sys.exit(1)
    elif not ollama_ok:
        console.print("\n[yellow]⚠️  Ollama is not available. You'll need to install it for LLM functionality.[/yellow]")
        console.print("Install from: https://ollama.ai")
    else:
        console.print("\n[green]🎉 Environment is fully configured and ready![/green]")


if __name__ == "__main__":
    main()