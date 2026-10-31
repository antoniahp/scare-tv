#!/usr/bin/env python
"""Django utility: `python manage.py scare_tv`, `make_scares`, `make_real_scares`, `night_summary`…"""
import os
import sys


def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
