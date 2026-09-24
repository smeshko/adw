# TASK-001: Detect the language and test command with ProjectTypeDetector

Depends on: None
Suggested commit: `refactor(wizard): detect the language with ProjectTypeDetector`

## Goal

The wizard's detected language and default test command come from `config/detector.ProjectTypeDetector`, the same source as `adw init --no-interactive`, and its own marker and test-command tables are gone.

## Files

- `src/adw/cli/wizard/basics.py`:
  - delete `LANGUAGE_MARKERS`, `DEFAULT_TEST_COMMANDS`, `detect_language` and `detect_test_command`
  - in `run_basics_step`, build one `ProjectTypeDetector()`. The detected language is `detected: str = detector.get_defaults(detector.detect(root))["language"] or "unknown"`; `get_defaults` returns `dict[str, str | None]`, so the `or` narrows it for `_prompt_language(console, detected: str)` under `mypy --strict`. It is `"unknown"` when no marker matches. The test-command default is `detector.get_defaults(language)["test_command"] or ""`, computed from the final (possibly user-chosen) language. An unknown or custom language falls back to the detector's `generic` defaults, so its default is empty, as today.
  - keep `SUPPORTED_LANGUAGES`, `SUPPORTED_PLATFORMS` and the prompt helpers as they are
- `src/adw/config/detector.py`: add `setup.cfg` to `MARKERS["python"]` and `build.gradle.kts` to `MARKERS["java"]`, the two markers only the wizard's table had. Without them a Kotlin-DSL Gradle project would stop being detected as java. Minimal init gains both too.
- `tests/unit/config/test_detector.py`: add a parametrized `test_detects_markers_the_wizard_used` for `setup.cfg` → python and `build.gradle.kts` → java.
- `src/adw/cli/wizard/__init__.py`: drop `detect_language` and `detect_test_command` from the import and `__all__`.
- `tests/unit/cli/wizard/test_basics.py`:
  - delete `TestLanguageDetection`, `TestTestCommandDetection` and `test_language_markers_covers_major_languages`; they test the deleted tables
  - replace each `patch("adw.cli.wizard.basics.detect_language", return_value=X)` with a marker file in the test's cwd (`tmp_path`, via the autouse `isolated_cwd`): `pyproject.toml` for python, `package.json` for javascript, `Cargo.toml` for rust, nothing for unknown
  - add a parametrized `test_detected_defaults_match_project_type_detector`: for each marker (`requirements.txt` → python/`pytest`, `setup.cfg` → python/`pytest`, `package.json` → javascript/`npm test`, `build.gradle` → java/`gradle test`, `build.gradle.kts` → java/`gradle test`, `composer.json` → php/`vendor/bin/phpunit`), accept every default and assert that the detection prompt was shown (`Confirm.ask` called once, and `rich.text.Text.from_markup(question).plain` contains `Language detected: <language>`; the raw question carries Rich markup, `Language detected: [cyan]python[/]. Correct?`), and that `result["language"]` and `result["test_command"]` equal `ProjectTypeDetector().get_defaults(...)`'s. The detection assert is what makes the `requirements.txt` case RED today: the wizard does not detect it and lands on python only through `_prompt_language`'s `"python"` fallback. The java and php cases fail on the test command too.
  - add `test_chosen_language_sets_test_command_default`: with a `package.json` present, reject the detection, type `go`, accept the test-command default; `result["test_command"] == "go test ./..."`

## Acceptance

- [ ] With `requirements.txt` or `setup.cfg` as the only marker, the wizard detects python and asks to confirm it; with `build.gradle` or `build.gradle.kts`, it detects java and offers `gradle test`; with `composer.json`, `vendor/bin/phpunit`.
- [ ] `ProjectTypeDetector` detects `setup.cfg` as python and `build.gradle.kts` as java.
- [ ] Picking a different language than the detected one offers that language's detector test command.
- [ ] `grep -rn "LANGUAGE_MARKERS\|DEFAULT_TEST_COMMANDS\|detect_language\|detect_test_command" src tests` returns nothing.
- [ ] `uv run pytest tests/unit/cli/wizard tests/unit/cli/test_init.py tests/unit/config/test_detector.py -o addopts=""` passes, and `scripts/preflight.sh` passes.

Evidence: the RED failures of the new parametrized cases (`requirements.txt`, java, php), the GREEN pytest tail, the grep and the preflight tail.

## Steps

### RED
- [ ] Add `test_detected_defaults_match_project_type_detector` and `test_chosen_language_sets_test_command_default` using marker files.
- [ ] Run `test_basics.py`: the `requirements.txt` (no detection prompt), `build.gradle`/`build.gradle.kts` and `composer.json` (test command) cases fail. `setup.cfg` passes today and guards the marker added below.

### GREEN
- [ ] Add `setup.cfg` and `build.gradle.kts` to `ProjectTypeDetector.MARKERS`, with `test_detects_markers_the_wizard_used`.
- [ ] Switch `run_basics_step` to `ProjectTypeDetector` and delete the four tables/functions and their re-exports.
- [ ] Rewrite the `detect_language` patches as marker files; delete the table tests.
- [ ] Run the partial suite: green.

### REFACTOR
- [ ] `scripts/preflight.sh` passes.

## Notes

- `ProjectTypeDetector.detect` checks markers in dict order (python before nodejs), so a directory with both `pyproject.toml` and `package.json` still detects python.
- `run_basics_step` keeps its `state` parameter until TASK-004; don't change the signature here.
