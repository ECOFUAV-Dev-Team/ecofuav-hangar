"""Çoklu İHA simülasyonu: filo tanımı (fleet.yaml) ve PX4 SITL modüllerine çevrilmesi.

PX4 v1.15 + Gazebo Harmonic'te ilk araç Gazebo'yu kendisi açar, sonrakiler
PX4_GZ_STANDALONE=1 ile aynı dünyaya katılır. Tek bir XRCE Agent hepsine hizmet
eder; ROS 2 tarafında her araç /px4_<i>/fmu/... isim alanında görünür.
"""
import uuid
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path

import yaml

from .config import LauncherConfig, Module
from .paths import CONFIG_DIR

FLEET_FILE = CONFIG_DIR / "fleet.yaml"

# PX4 v1.15 Gazebo modelleri ve airframe (SYS_AUTOSTART) numaraları.
MODELS: dict[str, int] = {
    "gz_x500": 4001,
    "gz_x500_depth": 4002,
    "gz_rc_cessna": 4003,
    "gz_standard_vtol": 4004,
    "gz_x500_vision": 4005,
    "gz_x500_mono_cam": 4010,
}

PLACEHOLDER_HELP = "{i}: PX4 örnek no · {ns}: px4_{i} · {sysid}: MAV_SYS_ID · {name}: araç adı · {gz_model}: Gazebo model adı"


@dataclass
class Vehicle:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    name: str = "İHA"
    enabled: bool = True
    model: str = "gz_x500"
    autostart: int = 4001
    x: float = 0.0
    y: float = 0.0
    # Araçla birlikte başlatılacak ROS 2 komutu (ör. offboard düğümü); yer tutucular PLACEHOLDER_HELP'te.
    companion_command: str = ""

    @classmethod
    def from_dict(cls, data: dict) -> "Vehicle":
        known = {f.name for f in fields(cls)}
        v = cls(**{k: val for k, val in (data or {}).items() if k in known})
        v.name, v.model, v.companion_command = str(v.name), str(v.model), str(v.companion_command or "")
        v.autostart, v.x, v.y, v.enabled = int(v.autostart), float(v.x), float(v.y), bool(v.enabled)
        return v


@dataclass
class FleetConfig:
    px4_dir: str = "~/PX4-Autopilot"
    world: str = "default"
    headless: bool = False
    start_agent: bool = True
    companion_setup: list[str] = field(default_factory=lambda: ["source ~/iha_ws/install/setup.bash"])
    vehicles: list[Vehicle] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> "FleetConfig":
        data = data or {}
        cfg = cls()
        for key in ("px4_dir", "world"):
            if data.get(key):
                setattr(cfg, key, str(data[key]))
        cfg.headless = bool(data.get("headless", cfg.headless))
        cfg.start_agent = bool(data.get("start_agent", cfg.start_agent))
        if "companion_setup" in data:
            cfg.companion_setup = [str(s) for s in data.get("companion_setup") or []]
        cfg.vehicles = [Vehicle.from_dict(v) for v in data.get("vehicles") or []]
        return cfg

    def to_dict(self) -> dict:
        return asdict(self)

    def active(self) -> list[Vehicle]:
        return [v for v in self.vehicles if v.enabled]


def default_fleet() -> FleetConfig:
    return FleetConfig(vehicles=[
        Vehicle(name="Hedef", model="gz_x500", autostart=4001, x=0, y=0),
        Vehicle(name="Takipçi-1", model="gz_x500_mono_cam", autostart=4010, x=0, y=3),
        Vehicle(name="Takipçi-2", model="gz_x500_mono_cam", autostart=4010, x=0, y=-3),
    ])


def load_fleet(path: Path = FLEET_FILE) -> FleetConfig:
    if not path.exists():
        return default_fleet()
    with open(path, encoding="utf-8") as f:
        return FleetConfig.from_dict(yaml.safe_load(f))


def save_fleet(cfg: FleetConfig, path: Path = FLEET_FILE) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".yaml.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        yaml.safe_dump(cfg.to_dict(), f, allow_unicode=True, sort_keys=False)
    tmp.replace(path)


def fill_placeholders(template: str, values: dict[str, str]) -> str:
    # str.format kullanılmıyor; bash'teki ${VAR} gibi süslü parantezler bozulmasın.
    for key, value in values.items():
        template = template.replace("{" + key + "}", value)
    return template


def build_modules(fleet: FleetConfig, base: LauncherConfig) -> LauncherConfig:
    """Filoyu, Kontrol Paneli ile aynı şekilde çalıştırılabilecek modüllere çevirir."""
    modules: list[Module] = []
    if fleet.start_agent:
        modules.append(Module(
            id="fleet_agent", name="XRCE-DDS Agent", description="Tüm araçlar için ortak köprü (UDP 8888)",
            use_global_setup=False, command="MicroXRCEAgent udp4 -p 8888", start_delay=1, stop_timeout=3,
        ))

    companions: list[Module] = []
    for n, v in enumerate(fleet.active()):
        i = n + 1
        gz_model = v.model.removeprefix("gz_") + f"_{i}"
        env = {
            "PX4_SYS_AUTOSTART": str(v.autostart),
            "PX4_SIM_MODEL": v.model,
            "PX4_GZ_MODEL_POSE": f"{v.x:g},{v.y:g}",
            "PX4_GZ_WORLD": fleet.world,
        }
        if n > 0:
            env["PX4_GZ_STANDALONE"] = "1"  # Gazebo'yu ilk araç açtı, bu araç ona katılır
        if fleet.headless:
            env["HEADLESS"] = "1"
        role = "Gazebo'yu açar" if n == 0 else "dünyaya katılır"
        modules.append(Module(
            id=f"veh_{v.id}",
            name=f"{v.name}  #{i}",
            description=f"{v.model} · konum ({v.x:g}, {v.y:g}) · /px4_{i} · {role}",
            workdir=fleet.px4_dir,
            use_global_setup=False,
            # İlk araç, PX4 henüz derlenmemişse derler.
            setup=["[ -x build/px4_sitl_default/bin/px4 ] || DONT_RUN=1 make px4_sitl gz_x500"] if n == 0 else [],
            command=f"./build/px4_sitl_default/bin/px4 -i {i}",
            env=env,
            ready_pattern="Ready for takeoff",
            ready_timeout=600 if n == 0 else 120,
            start_delay=1,
            stop_timeout=10,
        ))
        if v.companion_command.strip():
            values = {"i": str(i), "ns": f"px4_{i}", "sysid": str(i + 1), "name": v.name, "gz_model": gz_model}
            companions.append(Module(
                id=f"veh_{v.id}_node",
                name=f"{v.name} düğümü",
                description=f"/px4_{i} için eşlik eden komut",
                setup=list(fleet.companion_setup),
                command=fill_placeholders(v.companion_command, values),
            ))
    return LauncherConfig(global_setup=list(base.global_setup), cleanup_command=base.cleanup_command,
                          modules=modules + companions)
