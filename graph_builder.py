"""
Graph Builder — RepoMind Utility
Builds and renders dependency graphs using NetworkX + Matplotlib.
"""

import networkx as nx
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import io
import re
from typing import Optional


MODULE_COLORS = {
    "frontend": "#00D4FF",
    "backend": "#7C3AED",
    "database": "#3FB950",
    "config": "#8B949E",
    "utils": "#F0883E",
    "api": "#58A6FF",
    "auth": "#FF6B6B",
    "middleware": "#FFB347",
    "services": "#DA70D6",
    "models": "#98FB98",
    "routes": "#87CEEB",
    "tests": "#DDA0DD",
    "cli": "#F0E68C",
    "default": "#E6EDF3",
}


def detect_module_type(module_name: str, files: list[str]) -> str:
    """Detect module type from name and files."""
    name_lower = module_name.lower()
    
    if any(k in name_lower for k in ["front", "ui", "view", "template", "component", "react", "vue", "angular"]):
        return "frontend"
    if any(k in name_lower for k in ["auth", "login", "session", "token", "oauth"]):
        return "auth"
    if any(k in name_lower for k in ["db", "database", "model", "schema", "migration", "orm"]):
        return "database"
    if any(k in name_lower for k in ["config", "setting", "env", "setup"]):
        return "config"
    if any(k in name_lower for k in ["util", "helper", "common", "shared", "tool"]):
        return "utils"
    if any(k in name_lower for k in ["api", "endpoint", "handler"]):
        return "api"
    if any(k in name_lower for k in ["route", "router", "url"]):
        return "routes"
    if any(k in name_lower for k in ["service", "business", "logic"]):
        return "services"
    if any(k in name_lower for k in ["middleware", "filter", "interceptor"]):
        return "middleware"
    if any(k in name_lower for k in ["test", "spec", "mock"]):
        return "tests"
    if any(k in name_lower for k in ["cli", "command", "script"]):
        return "cli"
    if any(k in name_lower for k in ["back", "server", "app", "main", "core"]):
        return "backend"
    
    return "default"


def parse_modules_from_analysis(analysis: dict) -> tuple[list[dict], list[tuple]]:
    """
    Parse module map and dependencies from reasoning agent output.
    Returns (modules, edges) where modules are dicts and edges are (from, to) tuples.
    """
    modules = []
    edges = []
    
    # Try to get from structured data
    module_map = analysis.get("module_map", [])
    dependencies = analysis.get("dependency_analysis", {})
    
    if isinstance(module_map, list):
        for mod in module_map:
            if isinstance(mod, dict):
                modules.append({
                    "name": mod.get("name", "Unknown"),
                    "purpose": mod.get("purpose", ""),
                    "files": mod.get("files", []),
                    "type": detect_module_type(mod.get("name", ""), mod.get("files", [])),
                    "critical": mod.get("critical", False),
                })
    
    # If no modules parsed, create from raw text
    if not modules:
        modules = _extract_modules_from_text(analysis)
    
    # Parse edges from dependency text
    dep_text = ""
    if isinstance(dependencies, dict):
        dep_text = str(dependencies.get("relationships", "")) + " " + str(dependencies.get("description", ""))
    elif isinstance(dependencies, str):
        dep_text = dependencies
    
    edges = _extract_edges_from_text(dep_text, [m["name"] for m in modules])
    
    return modules, edges


def _extract_modules_from_text(analysis: dict) -> list[dict]:
    """Fallback: extract module names from text analysis."""
    text = str(analysis)
    modules = []
    seen = set()
    
    # Common patterns
    patterns = [
        r"\*\*([A-Z][a-zA-Z\s]+Module)\*\*",
        r"Module:\s*([A-Z][a-zA-Z\s]+)",
        r"- ([A-Z][a-zA-Z]+)\s+module",
    ]
    
    for pattern in patterns:
        for match in re.finditer(pattern, text):
            name = match.group(1).strip()
            if name not in seen and len(name) < 30:
                seen.add(name)
                modules.append({
                    "name": name,
                    "purpose": "",
                    "files": [],
                    "type": detect_module_type(name, []),
                    "critical": False,
                })
    
    # Minimal fallback
    if not modules:
        for name in ["Core App", "API Layer", "Data Layer", "Utilities", "Configuration"]:
            modules.append({
                "name": name,
                "purpose": "Extracted from analysis",
                "files": [],
                "type": detect_module_type(name, []),
                "critical": name == "Core App",
            })
    
    return modules


def _extract_edges_from_text(text: str, module_names: list[str]) -> list[tuple]:
    """Extract dependency edges from text description."""
    edges = []
    text_lower = text.lower()
    
    dep_keywords = [
        r"(\w[\w\s]+?)\s+depends on\s+([\w\s]+)",
        r"(\w[\w\s]+?)\s+uses\s+([\w\s]+)",
        r"(\w[\w\s]+?)\s+imports\s+([\w\s]+)",
        r"(\w[\w\s]+?)\s+calls\s+([\w\s]+)",
    ]
    
    name_lower_map = {n.lower(): n for n in module_names}
    
    for pattern in dep_keywords:
        for match in re.finditer(pattern, text_lower):
            src = match.group(1).strip()
            dst = match.group(2).strip()
            
            src_real = name_lower_map.get(src)
            dst_real = name_lower_map.get(dst)
            
            if src_real and dst_real and src_real != dst_real:
                edges.append((src_real, dst_real))
    
    # If no edges found, create a simple chain
    if not edges and len(module_names) >= 2:
        for i in range(len(module_names) - 1):
            edges.append((module_names[i], module_names[i + 1]))
    
    return list(set(edges))  # deduplicate


def build_dependency_graph(modules: list[dict], edges: list[tuple], repo_name: str = "Repository") -> io.BytesIO:
    """Build and render the dependency graph, returning PNG bytes."""
    
    G = nx.DiGraph()
    
    # Add nodes
    for mod in modules:
        G.add_node(mod["name"], **mod)
    
    # Add edges
    for src, dst in edges:
        if src in G.nodes and dst in G.nodes:
            G.add_edge(src, dst)
    
    # Compute node sizes based on degree
    degrees = dict(G.degree())
    min_size, max_size = 800, 3000
    if max(degrees.values(), default=1) > 0:
        sizes = [
            min_size + (max_size - min_size) * degrees[n] / max(degrees.values(), default=1)
            for n in G.nodes()
        ]
    else:
        sizes = [1200] * len(G.nodes())
    
    # Colors
    node_colors = []
    node_edge_colors = []
    for node in G.nodes():
        mod_data = G.nodes[node]
        mtype = mod_data.get("type", "default")
        color = MODULE_COLORS.get(mtype, MODULE_COLORS["default"])
        node_colors.append(color)
        if mod_data.get("critical", False):
            node_edge_colors.append("#F0883E")
        else:
            node_edge_colors.append("#30363D")
    
    # Layout
    if len(G.nodes()) <= 3:
        pos = nx.circular_layout(G)
    elif len(G.nodes()) <= 6:
        pos = nx.spring_layout(G, k=2.0, iterations=50, seed=42)
    else:
        try:
            pos = nx.kamada_kawai_layout(G)
        except Exception:
            pos = nx.spring_layout(G, k=1.5, iterations=50, seed=42)
    
    # Figure setup
    fig, ax = plt.subplots(1, 1, figsize=(12, 8))
    fig.patch.set_facecolor("#0D1117")
    ax.set_facecolor("#161B22")
    ax.set_xlim(-1.4, 1.4)
    ax.set_ylim(-1.4, 1.4)
    
    # Draw edges first
    if G.edges():
        nx.draw_networkx_edges(
            G, pos, ax=ax,
            edge_color="#30363D",
            arrows=True,
            arrowsize=20,
            arrowstyle="-|>",
            connectionstyle="arc3,rad=0.1",
            width=1.5,
            alpha=0.8,
            min_source_margin=20,
            min_target_margin=20,
        )
    
    # Draw nodes
    nx.draw_networkx_nodes(
        G, pos, ax=ax,
        node_color=node_colors,
        node_size=sizes,
        edgecolors=node_edge_colors,
        linewidths=2.5,
    )
    
    # Draw labels
    nx.draw_networkx_labels(
        G, pos, ax=ax,
        font_size=9,
        font_color="#0D1117",
        font_weight="bold",
    )
    
    # Title
    ax.set_title(
        f"RepoMind Dependency Graph — {repo_name}",
        color="#E6EDF3",
        fontsize=13,
        fontweight="bold",
        pad=15,
    )
    
    # Legend
    legend_items = []
    used_types = set(G.nodes[n].get("type", "default") for n in G.nodes())
    for mtype in used_types:
        color = MODULE_COLORS.get(mtype, MODULE_COLORS["default"])
        patch = mpatches.Patch(color=color, label=mtype.title())
        legend_items.append(patch)
    
    if legend_items:
        legend = ax.legend(
            handles=legend_items,
            loc="lower right",
            facecolor="#161B22",
            edgecolor="#30363D",
            labelcolor="#E6EDF3",
            fontsize=8,
            title="Module Types",
            title_fontsize=9,
        )
        legend.get_title().set_color("#8B949E")
    
    # Critical node indicator
    critical_patch = mpatches.Patch(facecolor="none", edgecolor="#F0883E", linewidth=2, label="Critical Module")
    ax.legend(
        handles=[critical_patch] + legend_items,
        loc="lower right",
        facecolor="#161B22",
        edgecolor="#30363D",
        labelcolor="#E6EDF3",
        fontsize=8,
        title="Legend",
        title_fontsize=9,
    )
    
    ax.axis("off")
    plt.tight_layout(pad=0.5)
    
    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=130, bbox_inches="tight", facecolor="#0D1117")
    plt.close(fig)
    buf.seek(0)
    return buf
