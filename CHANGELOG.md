## [1.1.2](https://github.com/Lakshmanshenoy/Macbook_Battery_Alert_Monitor/compare/v1.1.1...v1.1.2) (2026-05-21)


### Bug Fixes

* **tests:** remove unused imports, fix lambda, update version assertion to APP_VERSION ([04e3290](https://github.com/Lakshmanshenoy/Macbook_Battery_Alert_Monitor/commit/04e3290b55e78259019710e892af3ac201a8b0fe))

## [1.1.1](https://github.com/Lakshmanshenoy/Macbook_Battery_Alert_Monitor/compare/v1.1.0...v1.1.1) (2026-05-21)


### Bug Fixes

* **battery:** is_charging false-positive when discharging ([2cfab30](https://github.com/Lakshmanshenoy/Macbook_Battery_Alert_Monitor/commit/2cfab302f4ebab418cb6dce5d4bf0e34235f46d9))

## [1.1.0](https://github.com/Lakshmanshenoy/Macbook_Battery_Alert_Monitor/compare/v1.0.0...v1.1.0) (2026-05-21)


### Features

* phase 10 quality gate automation across CI, tests, and docs ([#12](https://github.com/Lakshmanshenoy/Macbook_Battery_Alert_Monitor/issues/12)) ([674ac3f](https://github.com/Lakshmanshenoy/Macbook_Battery_Alert_Monitor/commit/674ac3f499f372db4a38657407f506dbdf9105c3))
* phase 11 runtime resilience and recovery hardening ([#13](https://github.com/Lakshmanshenoy/Macbook_Battery_Alert_Monitor/issues/13)) ([9d19e5c](https://github.com/Lakshmanshenoy/Macbook_Battery_Alert_Monitor/commit/9d19e5c86cd2a8941683f00fb29c6adb1abce042))


### Bug Fixes

* **ci:** add package-lock for npm ci workflows ([1927e6e](https://github.com/Lakshmanshenoy/Macbook_Battery_Alert_Monitor/commit/1927e6ee14640ef3fec4a6642f23ce6ae7828cdf))
* **ci:** fallback to npm install when lockfile missing ([75ee1d0](https://github.com/Lakshmanshenoy/Macbook_Battery_Alert_Monitor/commit/75ee1d0f692d2717e7886f11b13b7dfa20dbbda4))
* **ci:** grant semantic-release workflow write permissions ([83e2e96](https://github.com/Lakshmanshenoy/Macbook_Battery_Alert_Monitor/commit/83e2e96de7bb593e184027a9638182f7b3afd018))
* **ci:** update workflow actions and actionlint issues ([b2ede22](https://github.com/Lakshmanshenoy/Macbook_Battery_Alert_Monitor/commit/b2ede22cf843022662d5a635c74d87d8274c736c))
* **release:** prevent husky commitlint from blocking semantic-release ([90de6c0](https://github.com/Lakshmanshenoy/Macbook_Battery_Alert_Monitor/commit/90de6c0d2e351cd0c6bf5bab5a07d23ce1273767))

# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]
- Initial public release preparations: notarization, signed DMG, checksums.
