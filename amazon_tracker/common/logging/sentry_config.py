"""Sentry error monitoring configuration."""

from typing import Optional

import sentry_sdk
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration


def setup_sentry(
    dsn: Optional[str] = None,
    environment: str = "development",
    debug: bool = False,
    sample_rate: float = 1.0,
) -> None:
    """Setup Sentry error monitoring.

    Args:
        dsn: Sentry DSN
        environment: Environment name
        debug: Debug mode
        sample_rate: Error sampling rate
    """
    if not dsn:
        return

    integrations = [
        FastApiIntegration(auto_enabling_integrations=False),
        SqlalchemyIntegration(),
        CeleryIntegration(),
    ]

    sentry_sdk.init(
        dsn=dsn,
        environment=environment,
        debug=debug,
        sample_rate=sample_rate,
        integrations=integrations,
        traces_sample_rate=0.1,
    )
