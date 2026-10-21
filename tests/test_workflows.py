"""Text checks on the GitHub Actions workflows: least-privilege CI (review F015, F020, F026, F028, F048, F058, F071).

Plain text, no YAML dependency (one parse check skips without PyYAML): a step is everything from its
'      - name:' line to the next. The commit steps' own shell also runs against local git repos (no network,
nothing touches GitHub)."""
import os
import re
import shutil
import subprocess
import textwrap
from pathlib import Path

import pytest

WORKFLOWS = Path(__file__).resolve().parent.parent / ".github" / "workflows"
ALL_WORKFLOWS = ("ai-sync.yml", "tests.yml", "weekly-sync.yml")

# What each data workflow may change on main: everything it legitimately commits, nothing else.
ALLOWLIST = {
    "ai-sync.yml": "^data/synced/",
    "weekly-sync.yml": "^(data/synced/|static/og/(member|state)/)",
}
REMOTE = 'remote="https://x-access-token:${GH_TOKEN}@github.com/${GITHUB_REPOSITORY}"'
NO_HOOKS = "git -c core.hooksPath=/dev/null"
GIT_PUSH = re.compile(r"^\s*git\b[^\n]*\spush\b", re.M)
GIT_PULL = re.compile(r"^\s*git\b[^\n]*\spull\b", re.M)


def _text(name: str) -> str:
    return (WORKFLOWS / name).read_text()


def _steps(text: str) -> list[tuple[str, str]]:
    parts = re.split(r"^      - name: ", text, flags=re.M)[1:]
    return [(part.split("\n", 1)[0].strip(), part) for part in parts]


def _script(step: str) -> str:
    """The step's `run: |` block, as the shell script the runner executes."""
    lines = []
    for line in step.split("        run: |\n", 1)[1].split("\n"):
        if line and not line.startswith("          "):
            break
        lines.append(line)
    return textwrap.dedent("\n".join(lines))


def _code(step: str) -> str:
    """The step without comment lines (comments above the next step belong to this one's text)."""
    return "\n".join(line for line in step.split("\n") if not line.lstrip().startswith("#"))


def _push_steps(name: str) -> list[tuple[str, str]]:
    return [(step_name, text) for step_name, text in _steps(_text(name)) if GIT_PUSH.search(_code(text))]


@pytest.mark.parametrize("name", ALL_WORKFLOWS)
def test_workflow_parses_as_yaml(name):
    yaml = pytest.importorskip("yaml")
    doc = yaml.safe_load(_text(name))
    assert doc["permissions"] and doc["jobs"]
    for job in doc["jobs"].values():
        assert [step["name"] for step in job["steps"]] == [step for step, _ in _steps(_text(name))]


# --- Pinned actions, no persisted credentials, read-only test job (F058, F015) ---

@pytest.mark.parametrize("name", ALL_WORKFLOWS)
def test_every_action_is_pinned_to_a_full_commit_sha(name):
    uses = re.findall(r"^ +(?:- )?uses: (.*)$", _text(name), re.M)
    assert uses
    for ref in uses:
        assert re.fullmatch(r"[\w.-]+/[\w.-]+@[0-9a-f]{40} # v\d+\.\d+\.\d+", ref), ref


def test_each_action_has_one_pin_across_workflows():
    pins: dict[str, set[str]] = {}
    for name in ALL_WORKFLOWS:
        for action, ref in re.findall(r"uses: ([\w.-]+/[\w.-]+)@(\S+ # \S+)", _text(name)):
            pins.setdefault(action, set()).add(ref)
    assert set(pins) == {"actions/checkout", "actions/setup-python"}
    assert all(len(refs) == 1 for refs in pins.values()), pins


@pytest.mark.parametrize("name", ALL_WORKFLOWS)
def test_every_checkout_keeps_no_credentials(name):
    checkouts = [text for _, text in _steps(_text(name)) if "uses: actions/checkout@" in text]
    assert checkouts
    for text in checkouts:
        assert "        with:\n" in text and "          persist-credentials: false\n" in text


def test_tests_workflow_token_is_read_only():
    text = _text("tests.yml")
    assert "\npermissions:\n  contents: read\n\njobs:\n" in text
    assert "write" not in text and "secrets." not in text and not GIT_PUSH.search(_code(text))


# --- The push token reaches only the commit steps, which rebase, check paths and push (F015, F071) ---

@pytest.mark.parametrize("name", sorted(ALLOWLIST))
def test_only_commit_steps_get_the_push_token(name):
    text = _text(name)
    assert "github.token" not in text.split("\n    steps:\n", 1)[0]
    for step_name, step in _steps(text):
        code = _code(step)
        pushes = bool(GIT_PUSH.search(code))
        assert pushes == ("github.token" in code), step_name
        assert pushes == bool(GIT_PULL.search(code)), step_name
        if pushes:
            assert "        env:\n          GH_TOKEN: ${{ github.token }}\n" in step, step_name


@pytest.mark.parametrize("name", sorted(ALLOWLIST))
def test_every_push_rebases_checks_the_allowlist_and_disables_hooks(name):
    allow = ALLOWLIST[name]
    steps = _push_steps(name)
    assert len(steps) == {"ai-sync.yml": 1, "weekly-sync.yml": 9}[name]
    for step_name, step in steps:
        lines = [line for line in _script(step).splitlines() if line and not line.startswith("#")]
        adds = [line for line in lines if line.startswith("git add ")]
        assert adds and lines[:len(adds)] == adds, step_name
        for path in (p for line in adds for p in line.split()[2:]):
            assert re.match(allow, path.rstrip("/") + "/"), (step_name, path)
        rest = lines[len(adds):]
        assert re.fullmatch(re.escape(NO_HOOKS) + r' commit -m "data: [a-z ]+ \[automated\]"', rest[2]), step_name
        assert rest[:2] + rest[3:] == [
            "git diff --cached --quiet && exit 0",
            REMOTE,
            f'{NO_HOOKS} pull --rebase "$remote" main || {{ {NO_HOOKS} rebase --abort; exit 1; }}',
            "outgoing=$(git diff --no-renames --name-only FETCH_HEAD HEAD)",
            f"if printf '%s\\n' \"$outgoing\" | grep -vE '{allow}' | grep -q .; then",
            rest[6],
            "  exit 1",
            "fi",
            f'{NO_HOOKS} push "$remote" HEAD:main',
        ], step_name
        assert rest[6].startswith('  echo "::error::Outgoing commits change files outside '), step_name


# --- AI credentials, CLI pin and the gates before the AI commit (F020, F026, F028) ---

def test_ai_credentials_reach_only_the_steps_that_use_them():
    text = _text("ai-sync.yml")
    assert "secrets." not in text.split("\n    steps:\n", 1)[0]
    body = dict(_steps(text))
    oauth = {name for name, step in body.items() if "CLAUDE_CODE_OAUTH_TOKEN: ${{ secrets." in step}
    api = {name for name, step in body.items() if "ANTHROPIC_API_KEY: ${{ secrets." in step}
    assert oauth == {"Check for credentials", "Run AI generation (subscription)"}
    assert api == {"Check for credentials", "Run AI generation (API)"}
    assert "          ANTHROPIC_API_KEY: ''\n" in body["Run AI generation (subscription)"]


def test_claude_cli_is_pinned_to_an_exact_version():
    installs = re.findall(r"run: (npm .*)$", _text("ai-sync.yml"), re.M)
    assert len(installs) == 1
    assert re.fullmatch(r"npm install -g @anthropic-ai/claude-code@\d+\.\d+\.\d+", installs[0])


def test_ai_sync_validates_and_tests_before_it_commits():
    steps = _steps(_text("ai-sync.yml"))
    names = [name for name, _ in steps]
    assert names[-3:] == ["Validate synced data", "Run tests", "Commit AI content"]
    assert max(names.index("Run AI generation (subscription)"), names.index("Run AI generation (API)")) \
        < names.index("Validate synced data")
    body = dict(steps)
    validate = body["Validate synced data"]
    assert "        id: validate_ai\n" in validate
    assert "        if: always() && steps.key-check.outputs.mode != 'none'\n" in validate
    assert "          CONGRESS_API_KEY: offline-validate\n" in validate
    assert "        run: python sync.py --step validate\n" in validate
    tests = body["Run tests"]
    assert "        id: tests\n" in tests
    assert "        if: always() && steps.validate_ai.outcome == 'success'\n" in tests
    assert "        run: python -m pytest -q -p no:cacheprovider\n" in tests
    assert ("        if: always() && steps.validate_ai.outcome == 'success' && steps.tests.outcome == 'success'\n"
            in body["Commit AI content"])
    assert "-r requirements-dev.txt" in body["Install dependencies"]


# --- Weekly sync: no unused FEC key, the suite gates the last pushes (F048, F028) ---

def test_weekly_sync_does_not_get_the_fec_key():
    assert "secrets.FEC_API_KEY" not in _text("weekly-sync.yml")


def test_weekly_sync_runs_the_suite_before_its_last_pushes():
    steps = _steps(_text("weekly-sync.yml"))
    names = [name for name, _ in steps]
    assert names.index("Validate all synced data") < names.index("Run tests") < names.index("Final commit")
    body = dict(steps)
    tests = body["Run tests"]
    assert "        id: tests\n" in tests
    assert "        if: always() && steps.validate_all.outcome == 'success'\n" in tests
    assert "          CONGRESS_API_KEY: ''\n" in tests
    assert "        run: python -m pytest -q -p no:cacheprovider\n" in tests
    gate = "        if: always() && steps.validate_all.outcome == 'success' && steps.tests.outcome == 'success'\n"
    for name in ("Final commit", "Build share cards", "Commit share cards"):
        assert gate in body[name], name
    assert "-r requirements-dev.txt" in body["Install dependencies"]


def test_weekly_pushes_after_the_first_validation_are_gated_on_it():
    steps = _steps(_text("weekly-sync.yml"))
    first_gate = [name for name, _ in steps].index("Validate member voting records")
    for name, step in steps[first_gate:]:
        if GIT_PUSH.search(_code(step)):
            assert re.search(r"^        if: always\(\) && steps\.validate_\w+\.outcome == 'success'", step, re.M), name


# --- The commit steps' shell, run against a local bare "GitHub" remote (F015, F071) ---
# git's url.<base>.insteadOf points the step's token URL at the bare repo; hooks planted in the runner's
# .git/hooks record GH_TOKEN if they ever run.

_FAKE_URL = "https://x-access-token:FAKE-TOKEN@github.com/clearvoting/test"
_HOOKS = ("pre-commit", "commit-msg", "post-commit", "pre-rebase", "post-rewrite", "post-checkout",
          "reference-transaction", "pre-push")
needs_git = pytest.mark.skipif(not (shutil.which("git") and shutil.which("bash")), reason="needs git and bash")


class _Runner:
    def __init__(self, tmp: Path):
        tmp.mkdir(parents=True, exist_ok=True)
        self.tmp = tmp
        self.remote = tmp / "remote.git"
        self.leak = tmp / "leaked-token"
        self.env = {
            "PATH": os.environ.get("PATH", ""), "HOME": str(tmp), "LEAK": str(self.leak),
            "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.com",
            "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.com",
            "GIT_CONFIG_COUNT": "1", "GIT_CONFIG_KEY_0": f"url.{self.remote.as_uri()}.insteadOf",
            "GIT_CONFIG_VALUE_0": _FAKE_URL,
        }
        self.git(tmp, "init", "-q", "--bare", "-b", "main", str(self.remote))
        self.human = tmp / "human"
        self.git(tmp, "init", "-q", "-b", "main", str(self.human))
        self.write(self.human, "app/main.py", "print('site')\n")
        self.write(self.human, "data/synced/a.json", '{"v": 1}\n')
        self.commit(self.human, "seed")
        self.git(self.human, "push", "-q", self.remote.as_uri(), "main")
        self.dir = tmp / "runner"  # like actions/checkout: depth 1, then no credentials kept
        self.git(tmp, "clone", "-q", "--depth", "1", self.remote.as_uri(), str(self.dir))
        for hook in _HOOKS:
            path = self.dir / ".git" / "hooks" / hook
            path.write_text('#!/bin/sh\necho "$GH_TOKEN" >> "$LEAK"\n')
            path.chmod(0o755)

    def git(self, cwd: Path, *args: str) -> str:
        return subprocess.run(["git", *args], cwd=cwd, env=self.env, check=True,
                              capture_output=True, text=True).stdout.strip()

    def write(self, repo: Path, rel: str, content: str):
        (repo / rel).parent.mkdir(parents=True, exist_ok=True)
        (repo / rel).write_text(content)

    def commit(self, repo: Path, message: str):
        self.git(repo, "-c", "core.hooksPath=/dev/null", "add", "-A")
        self.git(repo, "-c", "core.hooksPath=/dev/null", "commit", "-q", "-m", message)

    def human_pushes(self, rel: str, content: str):
        self.write(self.human, rel, content)
        self.commit(self.human, f"human: {rel}")
        self.git(self.human, "push", "-q", self.remote.as_uri(), "main")

    def main(self) -> str:
        return self.git(self.remote, "rev-parse", "main")

    def run_step(self, workflow: str, step_name: str) -> subprocess.CompletedProcess:
        script = self.tmp / "step.sh"
        script.write_text(_script(dict(_steps(_text(workflow)))[step_name]))
        env = dict(self.env, GH_TOKEN="FAKE-TOKEN", GITHUB_REPOSITORY="clearvoting/test")
        return subprocess.run(["bash", "--noprofile", "--norc", "-e", str(script)], cwd=self.dir, env=env,
                              capture_output=True, text=True)


DATA_STEPS = [("weekly-sync.yml", "Commit members"), ("ai-sync.yml", "Commit AI content")]


@needs_git
@pytest.mark.parametrize("workflow, step", DATA_STEPS)
def test_commit_step_rebases_onto_a_moved_main_and_pushes(tmp_path, workflow, step):
    runner = _Runner(tmp_path)
    runner.human_pushes("app/main.py", "print('hotfix')\n")  # a PR merged mid-run
    runner.write(runner.dir, "data/synced/a.json", '{"v": 2}\n')
    result = runner.run_step(workflow, step)
    assert result.returncode == 0, result.stdout + result.stderr
    assert runner.main() == runner.git(runner.dir, "rev-parse", "HEAD")
    assert runner.git(runner.remote, "log", "--format=%s", "main").splitlines()[1:] == ["human: app/main.py", "seed"]
    assert runner.git(runner.remote, "show", "main:app/main.py") == "print('hotfix')"
    assert runner.git(runner.remote, "show", "main:data/synced/a.json") == '{"v": 2}'
    assert not runner.leak.exists()


@needs_git
@pytest.mark.parametrize("workflow, step", DATA_STEPS)
@pytest.mark.parametrize("smuggle", ["edit", "rename"])
def test_commit_step_refuses_a_local_commit_outside_the_allowlist(tmp_path, workflow, step, smuggle):
    runner = _Runner(tmp_path)
    before = runner.main()
    if smuggle == "edit":  # an earlier step commits site code locally
        runner.write(runner.dir, "app/main.py", "print('injected')\n")
    else:  # a rename into data/synced/ must still count as touching app/
        runner.git(runner.dir, "mv", "app/main.py", "data/synced/main.py")
    runner.commit(runner.dir, "sneaky")
    runner.write(runner.dir, "data/synced/a.json", '{"v": 2}\n')
    result = runner.run_step(workflow, step)
    assert result.returncode != 0
    assert "::error::Outgoing commits change files outside" in result.stdout
    assert runner.main() == before
    assert not runner.leak.exists()


@needs_git
def test_ai_sync_may_not_push_share_cards_but_weekly_sync_may(tmp_path):
    for workflow, step, allowed in [("ai-sync.yml", "Commit AI content", False),
                                    ("weekly-sync.yml", "Commit members", True)]:
        runner = _Runner(tmp_path / workflow)
        before = runner.main()
        runner.write(runner.dir, "static/og/member/X000001.png", "png")
        runner.commit(runner.dir, "card")
        runner.write(runner.dir, "data/synced/a.json", '{"v": 2}\n')
        result = runner.run_step(workflow, step)
        assert (result.returncode == 0) == allowed, workflow
        assert (runner.main() != before) == allowed, workflow


@needs_git
def test_commit_step_aborts_a_conflicting_rebase_without_pushing(tmp_path):
    runner = _Runner(tmp_path)
    runner.human_pushes("data/synced/a.json", '{"v": "human"}\n')
    after_human = runner.main()
    runner.write(runner.dir, "data/synced/a.json", '{"v": "bot"}\n')
    result = runner.run_step("weekly-sync.yml", "Commit members")
    assert result.returncode != 0
    assert runner.main() == after_human
    assert not (runner.dir / ".git" / "rebase-merge").exists()
    assert not (runner.dir / ".git" / "rebase-apply").exists()
    assert runner.git(runner.dir, "status", "--porcelain") == ""
    assert not runner.leak.exists()


@needs_git
def test_commit_step_with_nothing_staged_pushes_nothing(tmp_path):
    runner = _Runner(tmp_path)
    before = runner.main()
    result = runner.run_step("weekly-sync.yml", "Commit members")
    assert result.returncode == 0, result.stdout + result.stderr
    assert runner.main() == before
