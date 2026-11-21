#!/usr/bin/env python3
# Owner: Dws (PIC 1) | Status: COMPLETE | Ref: SA §15.2, §14.1, §15.4
"""Launcher lintas OS untuk stack lokal Lettrust (hanya Python standard library)."""

from __future__ import annotations

import argparse
import json
import os
import re
import secrets
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = ROOT / ".env"
ENV_EXAMPLE = ROOT / ".env.example"
COMPOSE_FILE = ROOT / "compose.yaml"
COMPOSE_DEV_FILE = ROOT / "compose.dev.yaml"
NODE_IMAGE = "node:24.22.3-trixie-slim"
OPENAPI_TS_VERSION = "7.13.0"
FRONTEND_APPS = ("issuer-console", "partner-portal")
PYTHON_SERVICES = {"backend": "Dws (PIC 1)", "ai-service": "B (PIC 5)"}
LOCK_EXCLUDED = ("pip", "setuptools", "wheel")
SERVICES = ("chain", "chain-deployer", "backend", "ai-service", "issuer-console", "partner-portal")
GENERATED_SECRETS = ("JWT_SECRET", "INTERNAL_API_TOKEN", "PARTNER_TOKEN")
REQUIRED_ENV = GENERATED_SECRETS + (
    "REGISTRY_SIGNER_PRIVATE_KEY",
    "SEED_ADMIN_PASSWORD",
    "SEED_HR_PASSWORD",
)
HOST_PORTS = {
    "CONSOLE_HOST_PORT": 3000,
    "PORTAL_HOST_PORT": 3001,
    "BACKEND_HOST_PORT": 8000,
    "AI_SERVICE_HOST_PORT": 8001,
    "CHAIN_HOST_PORT": 8545,
}
NATIVE_POINTER = (
    "Docker/Compose v2 tidak tersedia atau daemon tidak berjalan.\n"
    "Jalankan Docker Desktop (Windows/macOS) atau Docker Engine + plugin Compose v2 (Linux),\n"
    "atau gunakan jalur native: lihat README.md bagian 'Jalur Native (Cadangan)'."
)


class LauncherError(Exception):
    """Kesalahan launcher yang ditampilkan ke pengguna tanpa traceback."""


# Mencetak pesan informasi dengan prefiks seragam.
def info(message: str) -> None:
    print(f"[dev] {message}", flush=True)


# Mencetak peringatan ke stderr.
def warn(message: str) -> None:
    print(f"[dev] PERINGATAN: {message}", file=sys.stderr, flush=True)


# Menjalankan perintah eksternal sebagai daftar argumen (tanpa shell) dari root repo.
def run(cmd: list[str], *, check: bool = True, capture: bool = False, cwd: Path | None = None) -> subprocess.CompletedProcess:
    try:
        result = subprocess.run(
            cmd,
            cwd=str(cwd or ROOT),
            check=False,
            text=True,
            encoding="utf-8",
            errors="replace",
            stdout=subprocess.PIPE if capture else None,
            stderr=subprocess.PIPE if capture else None,
        )
    except FileNotFoundError as exc:
        raise LauncherError(f"Perintah tidak ditemukan: {cmd[0]}") from exc
    if check and result.returncode != 0:
        detail = (result.stderr or "").strip() if capture else ""
        raise LauncherError(f"Perintah gagal (exit {result.returncode}): {' '.join(cmd[:4])} ...\n{detail}".rstrip())
    return result


# Menyusun prefiks perintah docker compose dengan berkas compose yang dipakai.
def compose_cmd(dev: bool = False) -> list[str]:
    cmd = ["docker", "compose", "-f", str(COMPOSE_FILE)]
    if dev:
        cmd += ["-f", str(COMPOSE_DEV_FILE)]
    return cmd


# Memeriksa bahwa docker CLI, daemon, dan Compose v2 tersedia; mengembalikan versi Compose.
def docker_available() -> tuple[bool, str]:
    if shutil.which("docker") is None:
        return False, "docker CLI tidak ditemukan di PATH"
    info_result = run(["docker", "info", "--format", "{{.ServerVersion}}"], check=False, capture=True)
    if info_result.returncode != 0:
        return False, "daemon Docker tidak berjalan (docker info gagal)"
    version_result = run(["docker", "compose", "version", "--short"], check=False, capture=True)
    if version_result.returncode != 0:
        return False, "plugin docker compose (v2) tidak tersedia"
    version = version_result.stdout.strip().lstrip("v")
    major = int(re.match(r"(\d+)", version).group(1)) if re.match(r"(\d+)", version) else 0
    if major < 2:
        return False, f"Compose v2 diperlukan, ditemukan {version}"
    return True, version


# Menghentikan launcher dengan panduan native apabila Docker tidak siap.
def require_docker() -> None:
    ok, detail = docker_available()
    if not ok:
        print(f"[dev] {detail}", file=sys.stderr)
        print(NATIVE_POINTER, file=sys.stderr)
        sys.exit(2)


# Membaca .env menjadi dict tanpa interpolasi.
def read_env(path: Path = ENV_FILE) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, _, value = stripped.partition("=")
        values[key.strip()] = value.strip()
    return values


# Membuat .env dari .env.example dan mengisi secret lokal acak; tidak pernah mencetak nilainya.
def ensure_env() -> None:
    if ENV_FILE.exists():
        return
    if not ENV_EXAMPLE.exists():
        raise LauncherError(".env.example tidak ditemukan.")
    lines = ENV_EXAMPLE.read_text(encoding="utf-8").splitlines()
    generated: list[str] = []
    output: list[str] = []
    for line in lines:
        key = line.split("=", 1)[0].strip() if "=" in line and not line.lstrip().startswith("#") else None
        if key in GENERATED_SECRETS:
            output.append(f"{key}={secrets.token_urlsafe(32)}")
            generated.append(key)
        else:
            output.append(line)
    ENV_FILE.write_text("\n".join(output) + "\n", encoding="utf-8")
    info(f".env dibuat dari .env.example; secret lokal dibuat acak: {', '.join(generated)}")
    if not read_env().get("LLM_API_KEY"):
        warn("LLM_API_KEY kosong di .env. Analisis AI akan berstatus 'unconfigured' sampai diisi.")


# Port host efektif: environment shell > .env > default SA §15.1 (sama dengan prioritas Docker Compose).
def host_port(name: str) -> int:
    return int(os.environ.get(name) or read_env().get(name) or HOST_PORTS[name])


# URL health backend sesuai port host efektif.
def health_url() -> str:
    return f"http://127.0.0.1:{host_port('BACKEND_HOST_PORT')}/api/v1/health"


# Memeriksa apakah port lokal dapat di-bind (bebas).
def port_free(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind(("127.0.0.1", port))
        except OSError:
            return False
    return True


# Perintah doctor: memeriksa prasyarat tanpa mengubah apa pun dan tanpa mencetak nilai secret.
def cmd_doctor(_: argparse.Namespace) -> int:
    problems = 0
    ok, detail = docker_available()
    if ok:
        info(f"OK   Docker daemon aktif, Compose v{detail}")
    else:
        info(f"GAGAL Docker: {detail}")
        print(NATIVE_POINTER)
        problems += 1
    info(f"OK   Python {sys.version.split()[0]}")
    running = set()
    if ok:
        ps = run(compose_cmd() + ["ps", "--services", "--status", "running"], check=False, capture=True)
        running = set(ps.stdout.split()) if ps.returncode == 0 else set()
    for port in (host_port(name) for name in HOST_PORTS):
        if port_free(port):
            info(f"OK   Port {port} bebas")
        elif running:
            info(f"INFO Port {port} terpakai (stack Lettrust sedang berjalan: {', '.join(sorted(running))})")
        else:
            info(f"GAGAL Port {port} terpakai oleh proses lain")
            problems += 1
    if not ENV_FILE.exists():
        info("GAGAL .env tidak ada.")
        problems += 1
    else:
        env = read_env()
        example_keys = set(read_env(ENV_EXAMPLE))
        missing_keys = sorted(example_keys - set(env))
        empty_required = [key for key in REQUIRED_ENV if not env.get(key)]
        if missing_keys:
            info(f"GAGAL .env tidak memuat variabel: {', '.join(missing_keys)}")
            problems += 1
        if empty_required:
            info(f"GAGAL .env memiliki secret/variabel wajib kosong: {', '.join(empty_required)}")
            problems += 1
        if not missing_keys and not empty_required:
            info("OK   .env lengkap (nilai secret tidak ditampilkan)")
        if not env.get("LLM_API_KEY"):
            warn("LLM_API_KEY kosong; AI akan 'unconfigured'.")
    info("Selesai: tidak ada masalah." if problems == 0 else f"Selesai: {problems} masalah ditemukan.")
    return 0 if problems == 0 else 1


# Membaca status container service dari docker compose ps (format JSON).
def compose_ps() -> list[dict]:
    result = run(compose_cmd() + ["ps", "-a", "--format", "json"], check=False, capture=True)
    if result.returncode != 0 or not result.stdout.strip():
        return []
    text = result.stdout.strip()
    if text.startswith("["):
        return json.loads(text)
    return [json.loads(line) for line in text.splitlines() if line.strip()]


# Menunggu seluruh service yang dijalankan sehat (atau one-shot selesai sukses) hingga batas waktu.
def wait_healthy(services: list[str], timeout: int = 600) -> bool:
    deadline = time.monotonic() + timeout
    pending: list[str] = list(services)
    while time.monotonic() < deadline:
        states = {item.get("Service"): item for item in compose_ps()}
        pending = []
        for svc in services:
            item = states.get(svc)
            if item is None:
                pending.append(svc)
                continue
            state, health = item.get("State", ""), item.get("Health", "")
            if svc == "chain-deployer":
                if state == "exited" and int(item.get("ExitCode", 1)) != 0:
                    raise LauncherError("chain-deployer gagal. Lihat: python scripts/dev.py logs chain-deployer")
                if state != "exited":
                    pending.append(svc)
            elif state == "exited":
                raise LauncherError(f"Service {svc} berhenti. Lihat: python scripts/dev.py logs {svc}")
            elif health and health != "healthy":
                pending.append(svc)
        if not pending:
            return True
        time.sleep(3)
    warn(f"Batas waktu menunggu health terlampaui: {', '.join(pending)}")
    return False


# Perintah up: membuat .env bila perlu lalu menjalankan service (opsional --build, --dev, --except).
def cmd_up(args: argparse.Namespace) -> int:
    require_docker()
    ensure_env()
    excluded = set(args.except_ or [])
    unknown = excluded - set(SERVICES)
    if unknown:
        raise LauncherError(f"Service tidak dikenal untuk --except: {', '.join(sorted(unknown))}")
    selected = [svc for svc in SERVICES if svc not in excluded]
    cmd = compose_cmd(args.dev) + ["up", "-d"]
    if args.build:
        cmd.append("--build")
    if excluded:
        cmd += selected
        info(f"Menjalankan tanpa: {', '.join(sorted(excluded))} (dependensi tetap dijalankan oleh Compose).")
    run(cmd)
    info("Menunggu service sehat ...")
    if wait_healthy(selected):
        info("Seluruh service yang dijalankan sehat.")
        return cmd_status(args)
    return 1


# Perintah down: menghentikan dan menghapus container tanpa menghapus volume data.
def cmd_down(_: argparse.Namespace) -> int:
    require_docker()
    run(compose_cmd() + ["down"])
    info("Service dihentikan. Volume data (chain-data, backend-data, shared) dipertahankan.")
    return 0


# Perintah reset: menghapus volume chain-data, backend-data, shared lalu menjalankan ulang (deploy + seed).
def cmd_reset(args: argparse.Namespace) -> int:
    require_docker()
    if not args.yes:
        answer = input("Reset akan MENGHAPUS state chain, basis data, dan info deployment. Lanjutkan? [y/N] ")
        if answer.strip().lower() not in ("y", "ya", "yes"):
            info("Reset dibatalkan.")
            return 1
    run(compose_cmd() + ["down", "-v"])
    info("Volume dihapus. Menjalankan ulang stack ...")
    return cmd_up(argparse.Namespace(build=False, dev=False, except_=None))


# Mengambil ringkasan health backend; mengembalikan None bila backend tidak dapat dihubungi.
def fetch_health() -> dict | None:
    try:
        with urllib.request.urlopen(health_url(), timeout=5) as response:
            return json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, OSError, ValueError):
        return None


# Perintah status: docker compose ps dan ringkasan health komponen backend.
def cmd_status(_: argparse.Namespace) -> int:
    require_docker()
    run(compose_cmd() + ["ps", "-a"])
    health = fetch_health()
    if health is None:
        info("Health backend: tidak dapat dihubungi di " + health_url())
        return 1
    components = ", ".join(f"{k}={v}" for k, v in health.get("components", {}).items())
    info(f"Health backend: status={health.get('status')} ({components})")
    return 0


# Perintah logs: mengikuti log semua service atau satu service.
def cmd_logs(args: argparse.Namespace) -> int:
    require_docker()
    cmd = compose_cmd() + ["logs", "-f", "--tail", "200"]
    if args.service:
        cmd.append(args.service)
    try:
        return run(cmd, check=False).returncode
    except KeyboardInterrupt:
        return 0


# Perintah seed: menjalankan seed ulang (idempotent) di container backend yang berjalan.
def cmd_seed(_: argparse.Namespace) -> int:
    require_docker()
    return run(compose_cmd() + ["exec", "backend", "python", "-m", "app.cli", "seed"], check=False).returncode


# Perintah stop: menghentikan satu service (untuk skenario kegagalan).
def cmd_stop(args: argparse.Namespace) -> int:
    require_docker()
    run(compose_cmd() + ["stop", args.service])
    info(f"Service {args.service} dihentikan.")
    return 0


# Perintah start: menjalankan kembali satu service yang dihentikan.
def cmd_start(args: argparse.Namespace) -> int:
    require_docker()
    run(compose_cmd() + ["start", args.service])
    info(f"Service {args.service} dijalankan kembali.")
    return 0


# Membaca info deployment contract dari volume shared melalui image chain-deployer.
def read_deployment() -> dict:
    result = run(
        compose_cmd() + ["run", "--rm", "--no-deps", "-T", "chain-deployer", "cat", "/shared/deployments/local.json"],
        check=False,
        capture=True,
    )
    if result.returncode != 0:
        raise LauncherError("Info deployment belum ada (/shared/deployments/local.json). Jalankan `python scripts/dev.py up`.")
    return json.loads(result.stdout)


# Memvalidasi format proofId (0x + 64 hex) sebelum dikirim ke cast.
def validate_proof_id(proof_id: str) -> str:
    if not re.fullmatch(r"0x[0-9a-fA-F]{64}", proof_id):
        raise LauncherError("proofId harus berformat 0x + 64 karakter hex.")
    return proof_id.lower()


# Perintah chain: membaca registry langsung (proof, events) atau mencetak alamat contract.
def cmd_chain(args: argparse.Namespace) -> int:
    require_docker()
    deployment = read_deployment()
    address = deployment["contractAddress"]
    if args.chain_command == "address":
        print(address)
        return 0
    proof_id = validate_proof_id(args.proof_id)
    rpc = ["--rpc-url", "http://127.0.0.1:8545"]
    exec_cast = compose_cmd() + ["exec", "-T", "chain", "cast"]
    if args.chain_command == "proof":
        signature = "getProof(bytes32)(bool,bytes32,bytes32,uint8,uint64,uint64)"
        result = run(exec_cast + ["call", address, signature, proof_id] + rpc, capture=True)
        labels = ("exists", "documentHash", "issuerRef", "status", "issuedAt", "revokedAt")
        for label, value in zip(labels, result.stdout.split()):
            print(f"{label}: {value}")
        return 0
    from_block = str(deployment.get("deployedAtBlock", 0))
    events = (
        "ProofIssued(bytes32 indexed proofId,bytes32 indexed issuerRef,bytes32 documentHash,uint64 issuedAt)",
        "ProofRevoked(bytes32 indexed proofId,bytes32 indexed issuerRef,uint64 revokedAt)",
    )
    for event in events:
        print(f"# {event.split('(')[0]}")
        run(exec_cast + ["logs", "--address", address, "--from-block", from_block, event, proof_id] + rpc, check=False)
    return 0


# Perintah openapi: ekspor contracts/openapi.json dari container backend lalu regenerasi tipe frontend.
def cmd_openapi(_: argparse.Namespace) -> int:
    require_docker()
    ensure_env()
    result = run(
        compose_cmd() + ["run", "--rm", "--no-deps", "-T", "backend", "python", "-m", "app.cli", "export-openapi"],
        capture=True,
    )
    spec = json.loads(result.stdout)
    target = ROOT / "contracts" / "openapi.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    # LF eksplisit: hasil identik byte-per-byte di Windows, macOS, dan Linux.
    target.write_text(json.dumps(spec, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    info(f"OpenAPI ditulis ke {target.relative_to(ROOT)} ({len(spec.get('paths', {}))} path).")
    user_args = ["--user", f"{os.getuid()}:{os.getgid()}"] if hasattr(os, "getuid") else []
    for app in FRONTEND_APPS:
        app_dir = ROOT / "apps" / app
        if not app_dir.exists():
            warn(f"apps/{app} belum ada; tipe tidak dibuat.")
            continue
        run(
            ["docker", "run", "--rm", *user_args, "-e", "npm_config_cache=/tmp/.npm", "-v", f"{ROOT}:/repo", "-w", f"/repo/apps/{app}", NODE_IMAGE,
             "npx", "--yes", f"openapi-typescript@{OPENAPI_TS_VERSION}", "../../contracts/openapi.json", "-o", "src/lib/api/schema.d.ts"]
        )
        info(f"Tipe API dibuat: apps/{app}/src/lib/api/schema.d.ts")
        count = write_fixtures(app)
        info(f"Fixture dibuat: apps/{app}/src/fixtures/api/ ({count} contoh)")
    return 0


FIXTURE_HEADER = "// GENERATED by scripts/dev.py openapi — do not edit\n"


# Mengubah nama berkas contoh (mis. api-07.ai-only.json) menjadi identifier camelCase (api07AiOnly).
def fixture_name(file_name: str) -> str:
    parts = re.split(r"[^0-9A-Za-z]+", file_name.removesuffix(".json"))
    words = [p for p in parts if p]
    return words[0].lower() + "".join(w[:1].upper() + w[1:] for w in words[1:])


# Menulis fixture TypeScript (`satisfies` tipe OpenAPI) untuk app dari contracts/examples/index.json; hasil deterministik.
def write_fixtures(app: str) -> int:
    examples_dir = ROOT / "contracts" / "examples"
    index = json.loads((examples_dir / "index.json").read_text(encoding="utf-8"))["examples"]
    entries = sorted((e for e in index if app in e.get("apps", [])), key=lambda e: e["file"])
    target = ROOT / "apps" / app / "src" / "fixtures" / "api"
    target.mkdir(parents=True, exist_ok=True)
    for old in target.glob("*.ts"):
        if old.read_text(encoding="utf-8").startswith(FIXTURE_HEADER):
            old.unlink()
    exports = []
    for entry in entries:
        name = fixture_name(entry["file"])
        data = json.loads((examples_dir / entry["file"]).read_text(encoding="utf-8"))
        literal = json.dumps(data, indent=2, ensure_ascii=False)
        content = (
            FIXTURE_HEADER
            + f"// Sumber: contracts/examples/{entry['file']} | skema: {entry['schema']}\n"
            + 'import type { components } from "@/lib/api/schema";\n\n'
            + f'export const {name} = {literal} satisfies components["schemas"]["{entry["schema"]}"];\n'
        )
        (target / f"{name}.ts").write_text(content, encoding="utf-8", newline="\n")
        exports.append(name)
    index_ts = FIXTURE_HEADER + "".join(f'export {{ {name} }} from "./{name}";\n' for name in exports)
    (target / "index.ts").write_text(index_ts, encoding="utf-8", newline="\n")
    return len(exports)


# Menjalankan test satu service di container yang sesuai; mengembalikan exit code.
def run_service_tests(service: str) -> int:
    info(f"Menjalankan test: {service}")
    if service in ("backend", "ai-service"):
        cmd = compose_cmd() + ["run", "--rm", "--no-deps", "-T", "-e", "APP_ENV=test"]
        # Test kontrak memvalidasi contracts/examples yang berada di luar build context service.
        cmd += ["-v", f"{ROOT / 'contracts'}:/contracts:ro", "-e", "CONTRACTS_DIR=/contracts"]
        cmd += [service, "python", "-m", "pytest", "-q"]
        return run(cmd, check=False).returncode
    if service == "blockchain":
        cmd = compose_cmd() + ["run", "--rm", "--no-deps", "-T", "chain-deployer", "forge", "test", "-vv"]
        return run(cmd, check=False).returncode
    if service in FRONTEND_APPS:
        app_dir = ROOT / "apps" / service
        # node_modules container dipisah (volume anonim) agar dependency native host tidak tertimpa.
        cmd = ["docker", "run", "--rm", "-v", f"{app_dir}:/app", "-v", "/app/node_modules", "-w", "/app", NODE_IMAGE,
               "sh", "-c", "npm ci --no-audit --no-fund --loglevel=error && npm test"]
        return run(cmd, check=False).returncode
    raise LauncherError(f"Target test tidak dikenal: {service}")


# Perintah test: unit test di container; tanpa argumen menjalankan semua target.
def cmd_test(args: argparse.Namespace) -> int:
    require_docker()
    ensure_env()
    targets = [args.service] if args.service else ["blockchain", "backend", "ai-service", *FRONTEND_APPS]
    if args.service == "chain-deployer":
        targets = ["blockchain"]
    results = {target: run_service_tests(target) for target in targets}
    for target, code in results.items():
        info(f"{'PASS' if code == 0 else 'FAIL'} {target}")
    return 0 if all(code == 0 for code in results.values()) else 1


# Perintah eval: menjalankan skrip ai-eval/scripts/<script>.py di image ai-service dengan ai-eval/ ter-mount.
def cmd_eval(args: argparse.Namespace) -> int:
    require_docker()
    ensure_env()
    script = args.script if args.script.endswith(".py") else f"{args.script}.py"
    if not (ROOT / "ai-eval" / "scripts" / script).exists():
        # Alias SA §21.2: `eval run` menjalankan run_eval.py.
        script = script.replace(".py", "_eval.py")
    if not re.fullmatch(r"[a-z_]+\.py", script) or not (ROOT / "ai-eval" / "scripts" / script).exists():
        raise LauncherError(f"Skrip evaluasi tidak ditemukan: ai-eval/scripts/{script}")
    cmd = compose_cmd() + [
        "run", "--rm", "--no-deps", "-T", "-v", f"{ROOT / 'ai-eval'}:/ai-eval", "-v", f"{ROOT / 'fixtures'}:/fixtures",
        "ai-service", "python", f"/ai-eval/scripts/{script}", *args.script_args,
    ]
    return run(cmd, check=False).returncode


# Membangun image sementara tanpa constraints, menjalankan pip freeze, dan menulis ulang constraints.txt service.
def lock_service(service: str) -> int:
    service_dir = ROOT / "services" / service
    dockerfile_lines = (service_dir / "Dockerfile").read_text(encoding="utf-8").splitlines()
    base_image = next(line.split()[1] for line in dockerfile_lines if line.startswith("FROM "))
    tag = f"lettrust-{service}-lock:tmp"
    lock_dockerfile = (
        f"FROM {base_image}\n"
        "COPY requirements.txt requirements-dev.txt /tmp/req/\n"
        "RUN pip install --no-cache-dir --disable-pip-version-check --root-user-action=ignore "
        "-r /tmp/req/requirements-dev.txt\n"
    )
    info(f"[{service}] Membangun image sementara dari requirements*.txt (base {base_image}) ...")
    build = subprocess.run(
        ["docker", "build", "-q", "-t", tag, "-f", "-", str(service_dir)],
        input=lock_dockerfile, text=True, encoding="utf-8", capture_output=True, check=False,
    )
    if build.returncode != 0:
        raise LauncherError(f"Build image lock {service} gagal:\n{build.stderr.strip()}")
    try:
        frozen = run(["docker", "run", "--rm", tag, "pip", "freeze"], capture=True).stdout.splitlines()
    finally:
        run(["docker", "image", "rm", "-f", tag], check=False, capture=True)
    # Urutan dipertahankan sesuai output pip freeze agar diff stabil.
    pins = [line.strip() for line in frozen if line.strip() and not line.startswith("#")]
    pins = [pin for pin in pins if pin.split("==")[0].lower() not in LOCK_EXCLUDED]
    target = service_dir / "constraints.txt"
    old_pins = {line for line in target.read_text(encoding="utf-8").splitlines() if "==" in line} if target.exists() else set()
    header = (
        f"# Owner: {PYTHON_SERVICES[service]} | Status: COMPLETE | Ref: SA §12.2, AD-19\n"
        f"# Dihasilkan oleh `python scripts/dev.py lock {service}` (pip freeze); jangan diedit manual.\n"
    )
    target.write_text(header + "\n".join(pins) + "\n", encoding="utf-8", newline="\n")
    added, removed = sorted(set(pins) - old_pins), sorted(old_pins - set(pins))
    info(f"[{service}] {target.relative_to(ROOT)}: {len(pins)} pin; berubah +{len(added)} / -{len(removed)}")
    for line in removed:
        info(f"  - {line}")
    for line in added:
        info(f"  + {line}")
    return 0


# Perintah lock: mengunci dependency Python (termasuk transitif) untuk satu atau kedua service.
def cmd_lock(args: argparse.Namespace) -> int:
    require_docker()
    services = [args.service] if args.service else list(PYTHON_SERVICES)
    for service in services:
        lock_service(service)
    info("Selesai. Lanjutkan: python scripts/dev.py up --build lalu python scripts/dev.py test <svc>.")
    return 0


# Menyusun parser argumen untuk seluruh subperintah SA §15.2.
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python scripts/dev.py", description="Launcher stack lokal Lettrust.")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("doctor", help="Periksa Docker, Compose v2, port, dan .env").set_defaults(func=cmd_doctor)
    up = sub.add_parser("up", help="Jalankan seluruh service")
    up.add_argument("--build", action="store_true", help="Bangun ulang image")
    up.add_argument("--dev", action="store_true", help="Pakai compose.dev.yaml (bind mount + reload)")
    up.add_argument("--except", dest="except_", nargs="+", metavar="SVC", help="Service yang tidak dijalankan")
    up.set_defaults(func=cmd_up)
    sub.add_parser("down", help="Hentikan service tanpa menghapus data").set_defaults(func=cmd_down)
    reset = sub.add_parser("reset", help="Hapus volume data lalu jalankan ulang")
    reset.add_argument("--yes", action="store_true", help="Lewati konfirmasi")
    reset.set_defaults(func=cmd_reset)
    sub.add_parser("status", help="Status container dan health").set_defaults(func=cmd_status)
    logs = sub.add_parser("logs", help="Ikuti log")
    logs.add_argument("service", nargs="?", choices=SERVICES)
    logs.set_defaults(func=cmd_logs)
    sub.add_parser("seed", help="Jalankan seed ulang").set_defaults(func=cmd_seed)
    for name, func in (("stop", cmd_stop), ("start", cmd_start)):
        p = sub.add_parser(name, help=f"{name} satu service")
        p.add_argument("service", choices=SERVICES)
        p.set_defaults(func=func)
    chain = sub.add_parser("chain", help="Baca registry langsung")
    chain_sub = chain.add_subparsers(dest="chain_command", required=True)
    for name in ("proof", "events"):
        p = chain_sub.add_parser(name)
        p.add_argument("proof_id", metavar="proofId")
    chain_sub.add_parser("address")
    chain.set_defaults(func=cmd_chain)
    sub.add_parser("openapi", help="Ekspor contracts/openapi.json dan regenerasi tipe frontend").set_defaults(func=cmd_openapi)
    test = sub.add_parser("test", help="Unit test di container")
    test.add_argument("service", nargs="?", choices=("blockchain", "chain-deployer", "backend", "ai-service", *FRONTEND_APPS))
    test.set_defaults(func=cmd_test)
    ev = sub.add_parser("eval", help="Jalankan skrip ai-eval di image ai-service")
    ev.add_argument("script", help="Nama skrip di ai-eval/scripts, mis. run_eval")
    ev.add_argument("script_args", nargs=argparse.REMAINDER, help="Argumen untuk skrip")
    ev.set_defaults(func=cmd_eval)
    lock = sub.add_parser("lock", help="Kunci dependency Python (pip freeze) ke services/<svc>/constraints.txt")
    lock.add_argument("service", nargs="?", choices=tuple(PYTHON_SERVICES))
    lock.set_defaults(func=cmd_lock)
    return parser


# Titik masuk launcher; mengubah LauncherError menjadi pesan dan exit code non-zero.
def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        ensure_env()
        return args.func(args)
    except LauncherError as exc:
        print(f"[dev] ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
