import json
import toml
import subprocess
import os
import shutil
from pathlib import Path
from src.config.paths import PATH_TO_GAMES, SETUP_PATH, OPTIMIZATION_PATH, PROJECT_PATH


class OptimizationExecution:
    """Handles execution of Rust optimization algorithm from python."""

    @staticmethod
    def load_math_config(filename: str) -> dict:
        """Load optimization parameter config file."""
        with open(filename, "r", encoding="UTF-8") as f:
            data = json.load(f)
        return data

    @staticmethod
    def run_opt_single_mode(game_config, mode, threads):
        """Create setup txt file for a single mode and run Rust executable binary."""
        os.chdir(PROJECT_PATH)
        filename = os.path.join(PATH_TO_GAMES, game_config.game_id, "library", "configs", "math_config.json")
        opt_config = OptimizationExecution.load_math_config(filename)

        opt_config = game_config.opt_params
        params = None
        for idx, obj in opt_config.items():
            if idx == mode:
                params = obj["parameters"]
        params["game_name"] = game_config.game_id
        params["path_to_games"] = "../games/"
        params["run_1000_batch"] = False
        params["bet_type"] = mode
        params["threads_for_fence_construction"] = threads
        params["threads_for_show_construction"] = threads

        assert params is not None, "Could not load optimization parameters."

        with open(SETUP_PATH, "w", encoding="UTF-8") as f:
            toml.dump(params, f)
        print(f"Running optimization for mode: {mode}")
        OptimizationExecution.run_rust_script()

    @staticmethod
    def run_all_modes(game_config, modes_to_run, rust_threads):
        """Loop through all game modes to run"""
        for mode in modes_to_run:
            OptimizationExecution.run_opt_single_mode(game_config, mode, rust_threads)

    @staticmethod
    def run_rust_script():
        """Run compiled binary and pip results to terminal."""
        env = OptimizationExecution.build_rust_optimizer_env()
        result = subprocess.run(
            ["cargo", "run", "--release"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=OPTIMIZATION_PATH,
            check=False,
            env=env,
        )
        if result.returncode == 0:
            print(result.stdout)
        else:
            if result.stdout:
                print(OptimizationExecution._tail(result.stdout), end="")
            if result.stderr:
                print(OptimizationExecution._tail(result.stderr), end="")
            raise RuntimeError(f"Rust optimization program failed with exit code {result.returncode}.")

    @staticmethod
    def build_rust_optimizer_env():
        """Return an environment that reliably runs Cargo with the MSVC linker on Windows."""
        return {**os.environ, "PATH": OptimizationExecution.build_rust_optimizer_path()}

    @staticmethod
    def build_rust_optimizer_path():
        cargo_bin_path = Path(os.path.expanduser("~")) / ".cargo" / "bin"
        entries = []

        if os.name == "nt":
            msvc_link_dir = OptimizationExecution._find_msvc_link_dir()
            if msvc_link_dir is None:
                current_link = shutil.which("link.exe")
                shadow_detail = f" Current PATH link.exe: {current_link}." if current_link else ""
                raise RuntimeError(
                    "MSVC link.exe was not found. Install Visual Studio Build Tools or run from a "
                    f"Developer PowerShell before optimizer execution.{shadow_detail}"
                )
            else:
                entries.append(str(msvc_link_dir))

        if cargo_bin_path.exists():
            entries.append(str(cargo_bin_path))

        entries.extend(os.environ.get("PATH", "").split(os.pathsep))
        optimized_path = OptimizationExecution._dedupe_path_entries(entries)

        if os.name == "nt":
            link_path = shutil.which("link.exe", path=optimized_path)
            if link_path is not None and "Microsoft Visual Studio" not in link_path:
                raise RuntimeError(
                    "Rust optimizer would use a non-MSVC link.exe: "
                    f"{link_path}. MSVC link.exe must be ahead of Git usr/bin/link.exe on PATH."
                )

        return optimized_path

    @staticmethod
    def _find_msvc_link_dir():
        current_link = shutil.which("link.exe")
        if current_link and "Microsoft Visual Studio" in current_link:
            return str(Path(current_link).parent)

        roots = []
        for env_name in ("ProgramFiles(x86)", "ProgramFiles"):
            root = os.environ.get(env_name)
            if root:
                roots.append(Path(root) / "Microsoft Visual Studio")

        candidates = []
        editions = ("BuildTools", "Community", "Professional", "Enterprise")
        for root in roots:
            for year in ("2022", "2019", "2017"):
                for edition in editions:
                    tools_root = root / year / edition / "VC" / "Tools" / "MSVC"
                    if tools_root.exists():
                        candidates.extend(tools_root.glob("*/bin/Hostx64/x64"))

        for candidate in sorted(candidates, reverse=True):
            link_path = candidate / "link.exe"
            if link_path.exists():
                return str(candidate)

        return None

    @staticmethod
    def _dedupe_path_entries(entries):
        seen = set()
        deduped = []
        for entry in entries:
            if not entry:
                continue
            key = os.path.normcase(os.path.abspath(entry))
            if key in seen:
                continue
            seen.add(key)
            deduped.append(entry)
        return os.pathsep.join(deduped)

    @staticmethod
    def _tail(text, max_lines=120):
        lines = text.splitlines(keepends=True)
        return "".join(lines[-max_lines:])
