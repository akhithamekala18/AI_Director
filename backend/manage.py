#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import sys


def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Is the backend virtualenv active and are "
            "the dependencies installed? See backend/pyproject.toml."
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
