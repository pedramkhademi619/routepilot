"""Selector type enum."""

from enum import StrEnum


class SelectorType(StrEnum):
    """Classification of traffic matching selector."""

    DOMAIN = "domain"
    DOMAIN_AND_SUBDOMAINS = "domain_and_subdomains"
    IP_ADDRESS = "ip_address"
    CIDR = "cidr"
    APPLICATION = "application"
