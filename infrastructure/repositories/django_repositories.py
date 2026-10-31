from domain.repositories.repositories import Repositories
from infrastructure.repositories.django_night_repository import DjangoNightRepository
from infrastructure.repositories.file_scare_catalog_repository import FileScareCatalogRepository


def build_django_repositories():
    return Repositories(nights=DjangoNightRepository(), catalog=FileScareCatalogRepository())
