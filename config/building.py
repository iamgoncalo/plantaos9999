"""CFT/HORSE building zone definitions.

Complete spatial model of the HORSE/Renault CFT training building in Aveiro.
Two floors, ~1000 users. Every room is defined with its real area (m²),
capacity, and zone type.
"""

from enum import Enum

from pydantic import BaseModel, Field


class ZoneType(str, Enum):
    """Classification of building zones by function."""

    TRAINING = "training"
    MEETING = "meeting"
    OFFICE = "office"
    SOCIAL = "social"
    CIRCULATION = "circulation"
    STORAGE = "storage"
    SANITARY = "sanitary"
    RECEPTION = "reception"
    LIBRARY = "library"
    IT_LAB = "it_lab"
    AUDITORIUM = "auditorium"
    PRODUCTION = "production"
    ARCHIVE = "archive"
    DOJO = "dojo"
    MULTIPURPOSE = "multipurpose"


class Zone(BaseModel):
    """A single zone (room/area) in the building."""

    id: str = Field(description="Unique zone identifier (e.g., 'p0_sala_multiusos')")
    name: str = Field(description="Human-readable zone name")
    floor: int = Field(description="Floor number (0 = ground, 1 = first)")
    area_m2: float = Field(description="Zone area in square meters")
    capacity: int = Field(default=0, description="Maximum occupancy (0 = not applicable)")
    zone_type: ZoneType = Field(description="Functional classification")
    has_hvac: bool = Field(default=True, description="Whether zone has HVAC")
    has_sensors: bool = Field(default=True, description="Whether zone has comfort sensors")


class Floor(BaseModel):
    """A single floor of the building."""

    number: int = Field(description="Floor number (0 = ground, 1 = first)")
    name: str = Field(description="Floor display name")
    zones: list[Zone] = Field(description="All zones on this floor")
    total_area_m2: float = Field(default=0.0, description="Total floor area in m²")

    def model_post_init(self, __context: object) -> None:
        """Compute total area from zones if not provided."""
        if self.total_area_m2 == 0.0:
            self.total_area_m2 = sum(z.area_m2 for z in self.zones)


class Building(BaseModel):
    """Complete building definition."""

    name: str = Field(description="Building name")
    location: str = Field(description="Building location")
    floors: list[Floor] = Field(description="All floors in the building")
    max_occupancy: int = Field(default=0, description="Total building capacity")

    def model_post_init(self, __context: object) -> None:
        """Compute max occupancy from zone capacities if not provided."""
        if self.max_occupancy == 0:
            self.max_occupancy = sum(
                z.capacity for f in self.floors for z in f.zones
            )

    @property
    def all_zones(self) -> list[Zone]:
        """Get all zones across all floors."""
        return [z for f in self.floors for z in f.zones]

    @property
    def total_area_m2(self) -> float:
        """Get total building area."""
        return sum(f.total_area_m2 for f in self.floors)


# ═══════════════════════════════════════════════
# Ground Floor — Piso 0
# ═══════════════════════════════════════════════
FLOOR_0_ZONES = [
    Zone(
        id="p0_sala_multiusos",
        name="Sala Multiusos",
        floor=0,
        area_m2=93.10,
        capacity=60,
        zone_type=ZoneType.MULTIPURPOSE,
    ),
    Zone(
        id="p0_biblioteca",
        name="Biblioteca / Espólio HORSE",
        floor=0,
        area_m2=46.50,
        capacity=20,
        zone_type=ZoneType.LIBRARY,
    ),
    Zone(
        id="p0_zona_social",
        name="Zona Social / Copa",
        floor=0,
        area_m2=35.10,
        capacity=15,
        zone_type=ZoneType.SOCIAL,
    ),
    Zone(
        id="p0_hall",
        name="Hall",
        floor=0,
        area_m2=41.50,
        capacity=30,
        zone_type=ZoneType.CIRCULATION,
    ),
    Zone(
        id="p0_circulacao",
        name="Circulação",
        floor=0,
        area_m2=50.30,
        capacity=0,
        zone_type=ZoneType.CIRCULATION,
        has_sensors=False,
    ),
    Zone(
        id="p0_aula_camara",
        name="Aula / Câmara",
        floor=0,
        area_m2=18.00,
        capacity=10,
        zone_type=ZoneType.TRAINING,
    ),
    Zone(
        id="p0_formacao_1",
        name="Sala de Formação 1",
        floor=0,
        area_m2=51.20,
        capacity=30,
        zone_type=ZoneType.TRAINING,
    ),
    Zone(
        id="p0_formacao_2",
        name="Sala de Formação 2",
        floor=0,
        area_m2=41.30,
        capacity=25,
        zone_type=ZoneType.TRAINING,
    ),
    Zone(
        id="p0_formacao_3",
        name="Sala de Formação 3",
        floor=0,
        area_m2=31.00,
        capacity=20,
        zone_type=ZoneType.TRAINING,
    ),
    Zone(
        id="p0_reuniao",
        name="Sala de Reunião",
        floor=0,
        area_m2=25.10,
        capacity=12,
        zone_type=ZoneType.MEETING,
    ),
    Zone(
        id="p0_informatica",
        name="Sala de Informática",
        floor=0,
        area_m2=41.70,
        capacity=30,
        zone_type=ZoneType.IT_LAB,
    ),
    Zone(
        id="p0_auditorio",
        name="Auditório",
        floor=0,
        area_m2=41.70,
        capacity=27,
        zone_type=ZoneType.AUDITORIUM,
    ),
    Zone(
        id="p0_arrumos",
        name="Arrumos",
        floor=0,
        area_m2=12.00,
        capacity=0,
        zone_type=ZoneType.STORAGE,
        has_hvac=False,
        has_sensors=False,
    ),
    Zone(
        id="p0_recepcao",
        name="Recepção",
        floor=0,
        area_m2=15.00,
        capacity=5,
        zone_type=ZoneType.RECEPTION,
    ),
    Zone(
        id="p0_wc_m",
        name="WC Masculino",
        floor=0,
        area_m2=12.00,
        capacity=0,
        zone_type=ZoneType.SANITARY,
        has_hvac=False,
        has_sensors=False,
    ),
    Zone(
        id="p0_wc_f",
        name="WC Feminino",
        floor=0,
        area_m2=12.00,
        capacity=0,
        zone_type=ZoneType.SANITARY,
        has_hvac=False,
        has_sensors=False,
    ),
]

# ═══════════════════════════════════════════════
# First Floor — Piso 1
# ═══════════════════════════════════════════════
FLOOR_1_ZONES = [
    Zone(
        id="p1_arquivo",
        name="Arquivo",
        floor=1,
        area_m2=57.50,
        capacity=0,
        zone_type=ZoneType.ARCHIVE,
        has_sensors=False,
    ),
    Zone(
        id="p1_sala_grande",
        name="Sala Grande",
        floor=1,
        area_m2=42.10,
        capacity=25,
        zone_type=ZoneType.TRAINING,
    ),
    Zone(
        id="p1_sala_pequena",
        name="Sala Pequena",
        floor=1,
        area_m2=25.00,
        capacity=15,
        zone_type=ZoneType.MEETING,
    ),
    Zone(
        id="p1_sala_1",
        name="Sala 1",
        floor=1,
        area_m2=45.00,
        capacity=25,
        zone_type=ZoneType.TRAINING,
    ),
    Zone(
        id="p1_sala_2",
        name="Sala 2",
        floor=1,
        area_m2=38.50,
        capacity=22,
        zone_type=ZoneType.TRAINING,
    ),
    Zone(
        id="p1_sala_3",
        name="Sala 3",
        floor=1,
        area_m2=31.20,
        capacity=18,
        zone_type=ZoneType.TRAINING,
    ),
    Zone(
        id="p1_circulacao",
        name="Circulação",
        floor=1,
        area_m2=46.70,
        capacity=0,
        zone_type=ZoneType.CIRCULATION,
        has_sensors=False,
    ),
    Zone(
        id="p1_producao",
        name="Produção / Exibição Armazém",
        floor=1,
        area_m2=25.80,
        capacity=10,
        zone_type=ZoneType.PRODUCTION,
    ),
    Zone(
        id="p1_dojo",
        name="Sala Dojo Segurança",
        floor=1,
        area_m2=110.30,
        capacity=50,
        zone_type=ZoneType.DOJO,
    ),
    Zone(
        id="p1_wc",
        name="WC Piso 1",
        floor=1,
        area_m2=14.00,
        capacity=0,
        zone_type=ZoneType.SANITARY,
        has_hvac=False,
        has_sensors=False,
    ),
    Zone(
        id="p1_monitor",
        name="Área de Monitorização",
        floor=1,
        area_m2=18.00,
        capacity=5,
        zone_type=ZoneType.OFFICE,
    ),
]


# ═══════════════════════════════════════════════
# Building Assembly
# ═══════════════════════════════════════════════
CFT_BUILDING = Building(
    name="Centro de Formação Técnica HORSE/Renault",
    location="Aveiro, Portugal",
    floors=[
        Floor(number=0, name="Piso 0 (Rés-do-chão)", zones=FLOOR_0_ZONES),
        Floor(number=1, name="Piso 1", zones=FLOOR_1_ZONES),
    ],
)


# ── Helper Functions ──────────────────────────
def get_zone_by_id(zone_id: str) -> Zone | None:
    """Look up a zone by its unique ID.

    Args:
        zone_id: The unique zone identifier.

    Returns:
        The Zone model or None if not found.
    """
    for zone in CFT_BUILDING.all_zones:
        if zone.id == zone_id:
            return zone
    return None


def get_zones_by_floor(floor: int) -> list[Zone]:
    """Get all zones for a specific floor.

    Args:
        floor: Floor number (0 or 1).

    Returns:
        List of Zone models for the specified floor.
    """
    for f in CFT_BUILDING.floors:
        if f.number == floor:
            return f.zones
    return []


def get_zones_by_type(zone_type: ZoneType) -> list[Zone]:
    """Get all zones of a specific type across all floors.

    Args:
        zone_type: The ZoneType to filter by.

    Returns:
        List of matching Zone models.
    """
    return [z for z in CFT_BUILDING.all_zones if z.zone_type == zone_type]


def get_monitored_zones() -> list[Zone]:
    """Get all zones that have sensors installed.

    Returns:
        List of Zone models with has_sensors=True.
    """
    return [z for z in CFT_BUILDING.all_zones if z.has_sensors]
