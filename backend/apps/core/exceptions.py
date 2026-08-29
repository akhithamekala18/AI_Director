# -*- coding: utf-8 -*-
"""Exception handling re-export.

The canonical structured-error envelope lives in apps.core.response; this module
is the landing point referenced by REST_FRAMEWORK.EXCEPTION_HANDLER.
"""
from apps.core.response import api_exception_handler  # noqa: F401
