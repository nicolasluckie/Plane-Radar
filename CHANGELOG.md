# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.0] - 2026-06-21

### Added

- Raspberry Pi port of the ESP32-C3 Plane Radar
- GC9A01 240×240 framebuffer display driver (RGB565 via `/dev/fb1`)
- Circular radar renderer — range rings, heading triangles, speed vectors, runway overlay
- ADS-B aircraft tracking via adsb.fi public API with configurable fetch radius and interval
- Flask web server — browser-based radar view at `/` and JSON API at `/api/aircraft`
- Centralized configuration via `config.py` — all `PLANERADAR_*` env vars validated at startup
- Structured logging — stderr always on, optional rotating file log (`PLANERADAR_LOG_TO_DISK`)
- Configurable log level (`PLANERADAR_LOG_LEVEL`, default: `warning`)
- Dependency injection throughout — no module-level singletons or side effects
- Type annotations on all public interfaces
- 68 pytest unit tests (no hardware required)
- `pyproject.toml` with packaging metadata and ruff configuration
- GitHub Actions CI — ruff lint + pytest on every push and PR
- Pre-commit hooks (ruff lint + format)
- Mock data mode (`PLANERADAR_MOCK_DATA=1`) for offline development
