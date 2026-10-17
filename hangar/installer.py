"""Takımın ortak sürüm listesinin (install/versions.yaml) okunması ve kontrolü."""
import re
import stat
import subprocess
import sys
from dataclasses import dataclass, field

import yaml

from .paths import APP_DIR, CACHE_DIR, SCRIPTS_DIR, VERSIONS_FILE, expand
from .process import child_env


@dataclass
class Component:
    id: str
    name: str
    required: str  # ekranda gösterilen sürüm
    version: str  # kurulum betiğine REQ_VERSION olarak verilir
    match: str  # yüklü sürüm bu regex'e uyuyorsa "güncel"
    check: str  # yüklü sürümü stdout'a yazan komut
    script: str
    description: str = ""


@dataclass
class VersionSet:
    team_version: str = ""
    env: dict[str, str] = field(default_factory=dict)
    components: list[Component] = field(default_factory=list)


def load_versions() -> VersionSet:
    with open(VERSIONS_FILE, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    comps = []
    for c in data.get("components") or []:
        version = str(c.get("version", ""))
        comps.append(Component(
            id=str(c["id"]),
            name=str(c.get("name", c["id"])),
            required=str(c.get("required", version)),
            version=version,
            match=str(c.get("match") or "^" + re.escape(version) + "$"),
            check=str(c.get("check", "")),
            script=str(c.get("script", "")),
            description=str(c.get("description", "")),
        ))
    return VersionSet(
        team_version=str(data.get("team_version", "")),
        env={str(k): expand(str(v)) for k, v in (data.get("env") or {}).items()},
        components=comps,
    )


def component_env(vs: VersionSet, comp: Component | None = None) -> dict[str, str]:
    extra = dict(vs.env)
    extra["HANGAR_MARKER_DIR"] = expand("~/.local/share/ecofuav-hangar/installed")
    if comp is not None:
        extra["REQ_VERSION"] = comp.version
        extra["HANGAR_COMPONENT"] = comp.id
    env = child_env(extra)
    env["SUDO_ASKPASS"] = ensure_askpass()
    return env


def check_installed(vs: VersionSet, comp: Component) -> str:
    """Yüklü sürümü döner; bulunamazsa boş string."""
    if not comp.check:
        return ""
    try:
        res = subprocess.run(
            ["bash", "-c", comp.check], env=component_env(vs, comp), stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=20, text=True,
        )
    except subprocess.TimeoutExpired:
        return ""
    lines = [l.strip() for l in res.stdout.splitlines() if l.strip()]
    return lines[0] if lines else ""


def is_up_to_date(comp: Component, installed: str) -> bool:
    return bool(installed) and re.search(comp.match, installed) is not None


def install_script(vs: VersionSet, comp: Component) -> str:
    path = SCRIPTS_DIR / comp.script
    return f"exec bash {_q(str(path))}\n"


def ensure_askpass() -> str:
    """sudo -A için grafik şifre penceresini açan küçük bir sarmalayıcı yazar."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    wrapper = CACHE_DIR / "askpass.sh"
    content = f'#!/bin/sh\nexec {_q(sys.executable)} {_q(str(APP_DIR / "hangar" / "askpass.py"))} "$@"\n'
    if not wrapper.exists() or wrapper.read_text() != content:
        wrapper.write_text(content)
        wrapper.chmod(wrapper.stat().st_mode | stat.S_IXUSR)
    return str(wrapper)


def is_git_checkout() -> bool:
    return (APP_DIR / ".git").exists()


def _q(s: str) -> str:
    return "'" + s.replace("'", "'\\''") + "'"
