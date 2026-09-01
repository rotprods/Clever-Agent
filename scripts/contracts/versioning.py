from __future__ import annotations

SUPPORTED_MAJOR = 1


class UnsupportedContractVersion(ValueError):
    pass


def require_supported_major(major: int) -> None:
    if major != SUPPORTED_MAJOR:
        raise UnsupportedContractVersion(
            f"unsupported Clever contract major version {major}; supported={SUPPORTED_MAJOR}"
        )


def require_supported_mapping(payload: dict[str, object]) -> None:
    version = payload.get("contractVersion")
    if not isinstance(version, dict):
        raise UnsupportedContractVersion("contractVersion object is required")
    major = version.get("major")
    if not isinstance(major, int):
        raise UnsupportedContractVersion("contractVersion.major integer is required")
    require_supported_major(major)
