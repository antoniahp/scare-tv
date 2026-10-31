from dataclasses import dataclass

from domain.repositories.night_repository import NightRepository
from domain.repositories.scare_catalog_repository import ScareCatalogRepository


@dataclass
class Repositories:
    nights: NightRepository
    catalog: ScareCatalogRepository
