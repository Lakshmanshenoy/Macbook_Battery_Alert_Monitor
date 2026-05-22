## [1.2.9](https://github.com/Lakshmanshenoy/battmon-macos/compare/v1.2.8...v1.2.9) (2026-05-22)


### Bug Fixes

* **dmg:** improve installer label contrast ([2bdbfdc](https://github.com/Lakshmanshenoy/battmon-macos/commit/2bdbfdc2b59177dac671d7c1db43aaee6f0250b4))

## [1.2.8](https://github.com/Lakshmanshenoy/battmon-macos/compare/v1.2.7...v1.2.8) (2026-05-22)


### Bug Fixes

* **dmg:** restore styled release builds ([5fd5146](https://github.com/Lakshmanshenoy/battmon-macos/commit/5fd51460d96a1322262b64273f95c94843210b99))

## [1.2.7](https://github.com/Lakshmanshenoy/battmon-macos/compare/v1.2.6...v1.2.7) (2026-05-22)


### Bug Fixes

* **release:** dispatch asset workflow ([3aeed3d](https://github.com/Lakshmanshenoy/battmon-macos/commit/3aeed3de40a20d7bfc995fecb6b0ab29c777539e))

## [1.2.6](https://github.com/Lakshmanshenoy/battmon-macos/compare/v1.2.5...v1.2.6) (2026-05-22)


### Bug Fixes

* **release:** automate asset publishing ([ac39f07](https://github.com/Lakshmanshenoy/battmon-macos/commit/ac39f07155304dda44bad789c9cc65da97bda596))

## [1.2.5](https://github.com/Lakshmanshenoy/battmon-macos/compare/v1.2.4...v1.2.5) (2026-05-22)


### Bug Fixes

* **release:** support CI dmg uploads ([2ec2a34](https://github.com/Lakshmanshenoy/battmon-macos/commit/2ec2a341fe66fa6bfc8508d137dde8ff27891917))

## [1.2.4](https://github.com/Lakshmanshenoy/battmon-macos/compare/v1.2.3...v1.2.4) (2026-05-22)


### Bug Fixes

* **ci:** make update smoke tests version-agnostic ([7924bd9](https://github.com/Lakshmanshenoy/battmon-macos/commit/7924bd9cfbf68b403002432fe2294795b20ebafd))

## [1.2.1](https://github.com/Lakshmanshenoy/battmon-macos/compare/v1.2.0...v1.2.1) (2026-05-21)


### Bug Fixes

* **build:** allow release builds without local venv ([4e8b4d4](https://github.com/Lakshmanshenoy/battmon-macos/commit/4e8b4d4281fbecff4fcf88db0c48247945454130))

## [1.2.0](https://github.com/Lakshmanshenoy/battmon-macos/compare/v1.1.4...v1.2.0) (2026-05-21)


### Features

* **distribution:** add BattMon download button and cask ([a06bc29](https://github.com/Lakshmanshenoy/battmon-macos/commit/a06bc29559cde67eae3bb860e186570d284745f9))

## [1.1.4](https://github.com/Lakshmanshenoy/battmon-macos/compare/v1.1.3...v1.1.4) (2026-05-21)


### Bug Fixes

* **release:** use BattMon artifact path in manifest checks ([2599f45](https://github.com/Lakshmanshenoy/battmon-macos/commit/2599f45e684ab9dc17b0f1a542164fefcb8de60a))

## [1.1.3](https://github.com/Lakshmanshenoy/Macbook_Battery_Alert_Monitor/compare/v1.1.2...v1.1.3) (2026-05-21)


### Bug Fixes

* **ci:** use BattMon artifact path in verification steps ([57d8487](https://github.com/Lakshmanshenoy/Macbook_Battery_Alert_Monitor/commit/57d8487b8abdc4272eaf92d091596a6804db04b0))

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
