"""Load the workspace's canonical configuration (config/*.yaml, agent and skill files)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml


class ConfigError(Exception):
    """Raised when workspace configuration is missing or inconsistent."""


@dataclass(frozen=True)
class AgentSpec:
    id: str
    name: str
    status: str
    responsibility: str
    permission_level: int
    tools: tuple[str, ...]
    agent_path: Path | None
    skill_path: Path | None
    domain_skill_paths: tuple[Path, ...]

    @property
    def active(self) -> bool:
        return self.status == "active"


@dataclass(frozen=True)
class ModelProfile:
    model: str
    effort: str
    max_tokens: int


@dataclass
class Workspace:
    root: Path
    agents: dict[str, AgentSpec]
    tool_min_levels: dict[str, int]
    task_output_area: str
    profiles: dict[str, ModelProfile]
    agent_profiles: dict[str, str]
    refusal_fallback: str | None
    max_tool_turns: int
    raw: dict = field(default_factory=dict)

    # --- convenience -----------------------------------------------------
    def agent(self, agent_id: str) -> AgentSpec:
        if agent_id not in self.agents:
            raise ConfigError(f"Unknown agent '{agent_id}'")
        return self.agents[agent_id]

    def active_agents(self) -> list[AgentSpec]:
        return [a for a in self.agents.values() if a.active]

    def profile_for(self, agent_id: str) -> ModelProfile:
        name = self.agent_profiles.get(agent_id, "balanced_general")
        if name not in self.profiles:
            raise ConfigError(f"Agent '{agent_id}' uses unknown profile '{name}'")
        return self.profiles[name]

    def read_text(self, relative: str) -> str:
        return (self.root / relative).read_text(encoding="utf-8-sig")

    @property
    def tasks_dir(self) -> Path:
        return self.root / "tasks"

    @property
    def data_dir(self) -> Path:
        return self.root / "runtime" / "data"


def _load_yaml(path: Path) -> dict:
    if not path.is_file():
        raise ConfigError(f"Missing config file: {path}")
    with path.open(encoding="utf-8-sig") as fh:
        data = yaml.safe_load(fh) or {}
    if not isinstance(data, dict):
        raise ConfigError(f"Config file is not a mapping: {path}")
    return data


def find_workspace_root(start: Path | None = None) -> Path:
    """Walk upwards from `start` until a directory with config/agent-registry.yaml is found."""
    here = (start or Path(__file__)).resolve()
    for candidate in [here, *here.parents]:
        if (candidate / "config" / "agent-registry.yaml").is_file():
            return candidate
    raise ConfigError("Could not find the workspace root (config/agent-registry.yaml)")


def load_workspace(root: Path | None = None) -> Workspace:
    root = (root or find_workspace_root()).resolve()
    registry = _load_yaml(root / "config" / "agent-registry.yaml")
    permissions = _load_yaml(root / "config" / "permissions.yaml")
    routing = _load_yaml(root / "config" / "model-routing.yaml")

    def resolve(rel: str | None) -> Path | None:
        return (root / rel).resolve() if rel else None

    agents: dict[str, AgentSpec] = {}
    for entry in registry.get("agents", []):
        agent_id = entry["id"]
        agents[agent_id] = AgentSpec(
            id=agent_id,
            name=entry.get("name", agent_id),
            status=entry.get("status", "planned"),
            responsibility=entry.get("responsibility", ""),
            permission_level=int(entry.get("permission_level", 0)),
            tools=tuple(entry.get("tools", []) or []),
            agent_path=resolve(entry.get("path")),
            skill_path=resolve(entry.get("skill")),
            domain_skill_paths=tuple(resolve(p) for p in entry.get("domain_skills", []) or []),
        )

    tool_min_levels = {
        name: int(spec.get("min_level", 99)) for name, spec in (permissions.get("tools") or {}).items()
    }

    runtime_cfg = routing.get("runtime") or {}
    profiles = {
        name: ModelProfile(model=p["model"], effort=p.get("effort", "medium"), max_tokens=int(p.get("max_tokens", 16000)))
        for name, p in (runtime_cfg.get("profile_models") or {}).items()
    }
    if not profiles:
        raise ConfigError("model-routing.yaml has no runtime.profile_models section")

    return Workspace(
        root=root,
        agents=agents,
        tool_min_levels=tool_min_levels,
        task_output_area=permissions.get("task_output_area", "tasks/<TASK-ID>/"),
        profiles=profiles,
        agent_profiles=dict(runtime_cfg.get("agent_profiles") or {}),
        refusal_fallback=runtime_cfg.get("refusal_fallback"),
        max_tool_turns=int(runtime_cfg.get("max_tool_turns", 20)),
        raw={"registry": registry, "permissions": permissions, "routing": routing},
    )


def validate(ws: Workspace) -> list[str]:
    """Return a list of human-readable problems; empty means the configuration is consistent."""
    problems: list[str] = []
    for agent in ws.active_agents():
        for label, path in (("path", agent.agent_path), ("skill", agent.skill_path)):
            if path is None or not path.is_file():
                problems.append(f"{agent.id}: {label} file missing ({path})")
        for path in agent.domain_skill_paths:
            if not path.is_file():
                problems.append(f"{agent.id}: domain skill missing ({path})")
        for tool in agent.tools:
            if tool not in ws.tool_min_levels:
                problems.append(f"{agent.id}: tool '{tool}' is not in the permissions.yaml tool catalog")
            elif agent.permission_level < ws.tool_min_levels[tool]:
                problems.append(
                    f"{agent.id}: level {agent.permission_level} < min_level {ws.tool_min_levels[tool]} for '{tool}'"
                )
        try:
            ws.profile_for(agent.id)
        except ConfigError as exc:
            problems.append(str(exc))
    if "orchestrator" not in ws.agents or not ws.agents["orchestrator"].active:
        problems.append("The orchestrator agent must be registered and active")
    return problems
