#!/usr/bin/env python3
"""Switch Claude CLI/macOS Desktop gateways without editing conversation data."""
import argparse
import contextlib
import datetime as dt
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
import urllib.parse
import uuid


class Refused(Exception):
    pass


def digest(data):
    return hashlib.sha256(data).hexdigest()


def read_json(path):
    return json.loads(path.read_text())


def atomic(path, data, mode=0o600):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix=".claude-switch-", dir=path.parent)
    try:
        os.fchmod(fd, mode)
        with os.fdopen(fd, "wb") as out:
            out.write(data)
            out.flush()
            os.fsync(out.fileno())
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def encoded(obj):
    return (json.dumps(obj, ensure_ascii=False, indent=2) + "\n").encode()


class Switcher:
    def __init__(self, home=None):
        self.home = Path(home or Path.home()).resolve()
        self.root = self.home / "Desktop/key/claude-api-switcher"
        self.desktop = self.home / "Library/Application Support/Claude-3p"

    def private_dir(self, path):
        path.mkdir(parents=True, exist_ok=True)
        path.chmod(0o700)

    @contextlib.contextmanager
    def lock(self):
        self.private_dir(self.root)
        with (self.root / ".lock").open("a") as f:
            os.chmod(f.name, 0o600)
            try:
                fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise Refused("Another switch is running.")
            yield

    def profile_path(self, name):
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,47}", name):
            raise Refused("Profile name must contain lowercase letters, numbers or hyphens.")
        return self.root / "profiles" / (name + ".json")

    def validate(self, obj):
        for field in ("base_url", "api_key", "model"):
            if not isinstance(obj.get(field), str) or not obj[field].strip():
                raise Refused("Missing profile field: " + field)
            if any(c in obj[field] for c in "\r\n\x00"):
                raise Refused("Multiline profile fields are not supported.")
        url = urllib.parse.urlsplit(obj["base_url"])
        if url.scheme != "https" or not url.hostname or url.username or url.password or url.query or url.fragment:
            raise Refused("Use an HTTPS base URL without credentials, query or fragment.")
        if not re.fullmatch(r"[A-Za-z0-9._:/\[\]-]+", obj["model"]):
            raise Refused("Invalid model ID.")
        if obj["api_key"].startswith("Bearer ") or any(c.isspace() for c in obj["api_key"]):
            raise Refused("Use the raw API key without Bearer or whitespace.")
        obj["base_url"] = obj["base_url"].rstrip("/")
        if obj["base_url"].endswith("/messages"):
            raise Refused("Use the provider base URL, not a messages endpoint.")
        return obj

    def load(self, name):
        return self.validate(read_json(self.profile_path(name)))

    def import_md(self, name, source):
        fields = {}
        for k, v in re.findall(r"^\s*(API_BASE_URL|API_KEY|MODEL)\s*=\s*(.*?)\s*$", Path(source).read_text(), re.M):
            if k in fields:
                raise Refused("Duplicate field: " + k)
            fields[k] = v.strip().strip("\"'")
        obj = self.validate({"base_url": fields.get("API_BASE_URL"), "api_key": fields.get("API_KEY"), "model": fields.get("MODEL")})
        path = self.profile_path(name)
        self.private_dir(path.parent)
        if path.exists():
            if read_json(path) != obj:
                raise Refused("Profile exists with different values; use a new name.")
        else:
            atomic(path, encoded(obj))
        return {"profile": name, "base_url": obj["base_url"], "model": obj["model"], "key": "saved (hidden)"}

    def active_paths(self):
        meta_path = self.desktop / "configLibrary/_meta.json"
        meta = read_json(meta_path)
        active = meta.get("appliedId", "")
        if not re.fullmatch(r"[a-zA-Z0-9-]+", active):
            raise Refused("Unknown desktop config identity; inspect the app before switching.")
        return self.home / ".claude/settings.json", self.desktop / "configLibrary" / (active + ".json")

    def status(self):
        cli, desk = self.active_paths()
        e = read_json(cli).get("env", {})
        d = read_json(desk)
        profiles = []
        for path in sorted((self.root / "profiles").glob("*.json")):
            p = self.load(path.stem)
            profiles.append({"name": path.stem, "base_url": p["base_url"], "model": p["model"],
                "cli_matches": e.get("ANTHROPIC_BASE_URL") == p["base_url"] and e.get("ANTHROPIC_AUTH_TOKEN") == p["api_key"],
                "desktop_matches": d.get("inferenceGatewayBaseUrl") == p["base_url"] and d.get("inferenceGatewayApiKey") == p["api_key"]})
        return {"cli_url": e.get("ANTHROPIC_BASE_URL"), "desktop_url": d.get("inferenceGatewayBaseUrl"), "profiles": profiles}

    def probe(self, name):
        p = self.load(name)
        cli = self.home / '.local/bin/claude'
        if not cli.exists():
            found = shutil.which('claude')
            if not found:
                raise Refused('Claude CLI is required for the probe.')
            cli = Path(found)
        start = time.monotonic()
        # A real Claude Code request: some gateways explicitly disallow generic HTTP clients.
        # Keep credentials out of process arguments and suppress customization/history loading.
        with tempfile.TemporaryDirectory(prefix='claude-api-probe-') as temporary:
            folder = Path(temporary)
            env = os.environ.copy()
            selected = {'ANTHROPIC_BASE_URL': p['base_url'], 'ANTHROPIC_AUTH_TOKEN': p['api_key'],
                'ANTHROPIC_API_KEY': '', 'ANTHROPIC_MODEL': p['model'],
                'CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC': '1', 'CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS': '1'}
            env.update(selected)
            for key in ('CLAUDE_CODE_USE_BEDROCK', 'CLAUDE_CODE_USE_VERTEX', 'CLAUDE_CODE_USE_FOUNDRY'):
                env.pop(key, None)
            settings = folder / 'settings.json'
            atomic(settings, encoded({'env': selected, 'disableAllHooks': True}))
            command = [str(cli), '-p', 'Do not use tools. Reply with exactly OK.', '--model', p['model'],
                '--effort', 'medium', '--safe-mode', '--tools', '', '--no-session-persistence',
                '--output-format', 'json', '--setting-sources', '', '--settings', str(settings), '--max-budget-usd', '0.50']
            try:
                r = subprocess.run(command, cwd=folder, env=env, text=True, capture_output=True, timeout=75)
            except subprocess.TimeoutExpired:
                raise Refused('CLI probe timed out after 75 seconds; configuration not changed.')
        try:
            response = json.loads(r.stdout)
        except ValueError:
            response = {}
        ok = r.returncode == 0 and response.get('is_error') is False and response.get('result', '').strip() == 'OK'
        result = {"profile": name, "method": "claude-cli", "exit_code": r.returncode, "elapsed_s": round(time.monotonic() - start, 2), "ok": ok}
        if not ok:
            raise Refused("Probe failed; configuration not changed. " + json.dumps(result))
        return result

    def assert_quiet(self):
        # Do not terminate apps or CLI processes, and never print their arguments.
        r = subprocess.run(["ps", "-axo", "pid=,comm="], text=True, capture_output=True, check=True)
        active = []
        for line in r.stdout.splitlines():
            cols = line.strip().split(None, 1)
            if len(cols) != 2:
                continue
            pid, command = cols
            leaf = Path(command).name.lower()
            if leaf in ("claude", "claude.exe") or "/Claude.app/" in command or "/.local/share/claude/versions/" in command or "/claude-code/" in command or "claude cli" in leaf:
                active.append(int(pid))
        if active:
            raise Refused("Claude is running. Finish/pause tasks, quit desktop and CLI, then retry. PIDs: " + ",".join(map(str, active)))
        if os.environ.get("CLAUDE_CONFIG_DIR"):
            raise Refused("Custom CLAUDE_CONFIG_DIR detected; this skill supports the standard profile only.")

    def protected_roots(self):
        return [self.home / ".claude/projects", self.home / ".claude/history.jsonl", self.home / ".claude.json",
                self.desktop / "claude-code-sessions", self.desktop / "local-agent-mode-sessions",
                self.desktop / "configLibrary/_meta.json", self.desktop / "claude_desktop_config.json"]

    def inventory(self):
        result = {}
        for root in self.protected_roots():
            if not root.exists() and not root.is_symlink():
                result[str(root.relative_to(self.home))] = {"absent": True}
                continue
            paths = [root]
            if root.is_dir() and not root.is_symlink():
                paths += sorted(root.rglob("*"))
            for p in paths:
                rel = str(p.relative_to(self.home))
                if p.is_symlink():
                    result[rel] = {"link": os.readlink(p)}
                elif p.is_file():
                    h = hashlib.sha256()
                    with p.open("rb") as f:
                        for block in iter(lambda: f.read(1024 * 1024), b""):
                            h.update(block)
                    result[rel] = {"sha256": h.hexdigest(), "size": p.stat().st_size}
                elif p.is_dir():
                    result[rel] = {"directory": True}
        return result

    def changes(self, p):
        cli, desk = self.active_paths()
        c, d = read_json(cli), read_json(desk)
        if d.get("inferenceProvider") != "gateway" or d.get("inferenceCredentialKind") != "static":
            raise Refused("Desktop must already use Gateway / Static API key.")
        e = c.setdefault("env", {})
        if any(e.get(k) not in (None, "", "0") for k in ("CLAUDE_CODE_USE_BEDROCK", "CLAUDE_CODE_USE_VERTEX", "CLAUDE_CODE_USE_FOUNDRY")):
            raise Refused("A different inference provider is enabled.")
        e.update(ANTHROPIC_BASE_URL=p["base_url"], ANTHROPIC_AUTH_TOKEN=p["api_key"], ANTHROPIC_DEFAULT_OPUS_MODEL=p["model"])
        if "ANTHROPIC_API_KEY" in e:
            e["ANTHROPIC_API_KEY"] = ""
        model = c.get("model", "opus")
        if model not in ("opus", "opus[1m]") and model != p["model"]:
            raise Refused("CLI has a different model override; decide explicitly before switching.")
        d["inferenceGatewayBaseUrl"], d["inferenceGatewayApiKey"] = p["base_url"], p["api_key"]
        opus = [m for m in d.get("inferenceModels", []) if m.get("anthropicFamilyTier") == "opus"]
        if len(opus) != 1:
            raise Refused("Unknown desktop model mapping; inspect before editing.")
        opus[0]["name"] = p["model"]
        result = {cli: encoded(c), desk: encoded(d)}
        replacements = {"ANTHROPIC_BASE_URL": p["base_url"], "ANTHROPIC_AUTH_TOKEN": p["api_key"], "ANTHROPIC_API_KEY": "", "ANTHROPIC_MODEL": p["model"], "ANTHROPIC_DEFAULT_OPUS_MODEL": p["model"]}
        for filename in (".zshrc", ".zprofile", ".zshenv", ".bashrc", ".bash_profile", ".profile"):
            path = self.home / filename
            if not path.exists():
                continue
            original = path.read_text()
            lines = original.splitlines(keepends=True)
            for i, line in enumerate(lines):
                relevant = [k for k in replacements if re.search(r"\b" + k + r"\s*=", line) and not line.lstrip().startswith("#")]
                if not relevant:
                    continue
                match = re.fullmatch(r"\s*(?:export\s+)?(" + "|".join(replacements) + r")\s*=([^\n]*)\n?", line)
                if not match or any(x in match.group(2) for x in (";", "&&", "||", "$(`", "`", "$(")):
                    raise Refused("Complex shell assignment requires manual review: " + filename + ":" + str(i + 1))
                k = match.group(1)
                lines[i] = "export " + k + "=" + shlex.quote(replacements[k]) + "\n"
            updated = "".join(lines)
            if updated != original:
                result[path] = updated.encode()
        for path in result:
            if path.is_symlink():
                raise Refused("Config symlink requires explicit handling: " + path.name)
        return result

    def backup(self, changes):
        self.assert_quiet()
        bid = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ-") + uuid.uuid4().hex[:8]
        dest = self.root / "backups" / bid
        self.private_dir(dest)
        manifest = {"id": bid, "state": "prepared", "before_history": self.inventory(), "files": []}
        for n, (path, data) in enumerate(changes.items()):
            old = path.read_bytes()
            atomic(dest / f"config-{n}.bin", old)
            manifest["files"].append({"path": str(path.relative_to(self.home)), "backup": f"config-{n}.bin", "before": digest(old), "after": digest(data), "mode": path.stat().st_mode & 0o777})
        archive = dest / "history.tar.gz"
        with tarfile.open(archive, "w:gz", dereference=False) as tar:
            for root in self.protected_roots():
                if root.exists() or root.is_symlink():
                    tar.add(root, arcname=str(root.relative_to(self.home)))
        archive.chmod(0o600)
        if self.inventory() != manifest["before_history"]:
            raise Refused("History changed during backup; no configuration was changed.")
        manifest["history_archive_sha256"] = digest(archive.read_bytes())
        atomic(dest / "manifest.json", encoded(manifest))
        return dest, manifest

    def apply(self, name):
        p = self.load(name)
        self.assert_quiet()
        probe = self.probe(name)
        changes = self.changes(p)
        dest, manifest = self.backup(changes)
        written = []
        try:
            self.assert_quiet()
            for item, (path, data) in zip(manifest["files"], changes.items()):
                if digest(path.read_bytes()) != item["before"]:
                    raise Refused("Configuration changed while switching; aborting.")
                atomic(path, data, item["mode"] if path.name.startswith(".") else 0o600)
                written.append(item)
            if self.inventory() != manifest["before_history"]:
                raise Refused("Conversation integrity check changed; inspect backup before continuing.")
            for item in manifest["files"]:
                if digest((self.home / item["path"]).read_bytes()) != item["after"]:
                    raise Refused("Config readback failed.")
            manifest["state"] = "applied"
            manifest["profile"] = name
            atomic(dest / "manifest.json", encoded(manifest))
        except Exception:
            conflicts = []
            for item in reversed(written):
                path = self.home / item["path"]
                if digest(path.read_bytes()) == item["after"]:
                    atomic(path, (dest / item["backup"]).read_bytes(), item["mode"])
                else:
                    conflicts.append(item["path"])
            manifest["state"] = "failed"
            manifest["rollback_conflicts"] = conflicts
            atomic(dest / "manifest.json", encoded(manifest))
            raise
        return {"applied": name, "base_url": p["base_url"], "probe": probe, "backup_id": manifest["id"], "history_identical": True, "restart_required": True}

    def snapshot(self):
        cli, desk = self.active_paths()
        current = {p: p.read_bytes() for p in (cli, desk)}
        for filename in ('.zshrc', '.zprofile', '.zshenv', '.bashrc', '.bash_profile', '.profile'):
            p = self.home / filename
            if p.exists():
                current[p] = p.read_bytes()
        dest, manifest = self.backup(current)
        manifest['state'] = 'snapshot_only'
        atomic(dest / 'manifest.json', encoded(manifest))
        return {'backup_id': manifest['id'], 'history_identical': True, 'configuration_changed': False}

    def rollback(self, bid):
        if not re.fullmatch(r"[0-9TZ-]+[a-f0-9]{8}", bid):
            raise Refused("Invalid backup ID.")
        self.assert_quiet()
        dest = self.root / "backups" / bid
        m = read_json(dest / "manifest.json")
        if m["state"] != "applied":
            raise Refused("Only an applied transaction can be rolled back.")
        changes = {}
        for item in m["files"]:
            path = self.home / item["path"]
            if not path.resolve().is_relative_to(self.home) or path.is_symlink():
                raise Refused("Unsafe backup path.")
            if digest(path.read_bytes()) != item["after"]:
                raise Refused("Config changed since this switch. Refusing to overwrite later edits: " + item["path"])
            data = (dest / item["backup"]).read_bytes()
            if digest(data) != item["before"]:
                raise Refused("Backup checksum mismatch.")
            changes[path] = data
        before_history = self.inventory()
        # Preserve newer conversation records; never extract an old history archive here.
        written = []
        try:
            for item, (path, data) in zip(m["files"], changes.items()):
                old = path.read_bytes()
                written.append((path, old, path.stat().st_mode & 0o777))
                atomic(path, data, item["mode"])
            if self.inventory() != before_history:
                raise Refused("History changed during rollback.")
        except Exception:
            for path, data, mode in reversed(written):
                atomic(path, data, mode)
            raise
        m["state"] = "rolled_back"
        atomic(dest / "manifest.json", encoded(m))
        return {"rolled_back": bid, "history_identical": True, "restart_required": True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest="command", required=True)
    subs.add_parser("status")
    subs.add_parser("snapshot")
    imp = subs.add_parser("import-md"); imp.add_argument("name"); imp.add_argument("source")
    for name in ("probe", "plan", "apply"):
        p = subs.add_parser(name); p.add_argument("profile")
    roll = subs.add_parser("rollback"); roll.add_argument("backup_id")
    args = parser.parse_args()
    s = Switcher()
    try:
        with s.lock():
            if args.command == "status":
                result = s.status()
            elif args.command == "snapshot":
                result = s.snapshot()
            elif args.command == "import-md":
                result = s.import_md(args.name, args.source)
            elif args.command == "probe":
                result = s.probe(args.profile)
            elif args.command == "plan":
                p = s.load(args.profile)
                result = {"profile": args.profile, "base_url": p["base_url"], "model": p["model"], "edit_paths": [str(x) for x in s.changes(p)], "history_action": "backup and checksum only; no edits"}
            elif args.command == "apply":
                result = s.apply(args.profile)
            else:
                result = s.rollback(args.backup_id)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except Refused as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except Exception as exc:
        # Do not expose response bodies, process arguments, URLs containing credentials or config contents.
        print("Operation failed (" + type(exc).__name__ + "). Inspect locally without printing secrets.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
