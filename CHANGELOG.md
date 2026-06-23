# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Add automated CHANGELOG generation via git-cliff ([`5f2fa24`](https://github.com/nicolasluckie/Plane-Radar/commit/5f2fa2430e415a564665149a53b61884b847021c))
- Add Pi hardening script and update README ([`253e1ec`](https://github.com/nicolasluckie/Plane-Radar/commit/253e1ece0fcf2190b739b8d25e06128f12ccd04c))
- Replace polling with SSE for real-time sync across tabs ([`3ab6c9c`](https://github.com/nicolasluckie/Plane-Radar/commit/3ab6c9c9a11d061b2556fa674c697fde824ba6ff))
- Add scale label left of E cardinal on radar canvas ([`a981a7e`](https://github.com/nicolasluckie/Plane-Radar/commit/a981a7e909e45386a301fab6b648ac11691bd64e))
- Add squawk code meanings to aircraft tag display ([`2c0e2e5`](https://github.com/nicolasluckie/Plane-Radar/commit/2c0e2e5ecf41f28c7d1fcf93060edbf7ee57aa3c))

### Changed

- Fix typo in README ([`b3e31c2`](https://github.com/nicolasluckie/Plane-Radar/commit/b3e31c2bea04a424b1e90034a995128328b1a7d8))

### Fixed

- Handle fetch timeout and network errors in updateRadar ([`99d9575`](https://github.com/nicolasluckie/Plane-Radar/commit/99d95756a7bbb677099b0ae6d53d53f5d1dd746f))
- Replace bare range_manager global with self.range_manager ([`36efb95`](https://github.com/nicolasluckie/Plane-Radar/commit/36efb95e80d7a8498edd42933b003e4dc5695ab3))
- Address pre-push review findings ([`19854d5`](https://github.com/nicolasluckie/Plane-Radar/commit/19854d5b075a1985bdc724d8dbf7cae3a8446537))
- Use genbadge cli directly instead of python -m ([`c05c61e`](https://github.com/nicolasluckie/Plane-Radar/commit/c05c61e6785bd173f76f617281e851527ed16ae5))
- Pull --rebase before changelog push to avoid non-fast-forward ([`1a255ca`](https://github.com/nicolasluckie/Plane-Radar/commit/1a255ca7fd61952d2cb656d0faf4ddf52ff64946))


