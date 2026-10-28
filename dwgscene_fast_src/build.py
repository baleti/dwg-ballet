"""Cross-platform build of the optional native scene kernels (no maturin needed): cargo build --release, then copy the library next to the
Python modules under the extension name Python expects (dwgscene_fast.abi3.so on Linux/macOS, dwgscene_fast.pyd on Windows).
Usage: python dwgscene_fast_src/build.py [--offline]    Without the result everything runs in pure Python."""
import os, subprocess, shutil, sys

here = os.path.dirname(os.path.abspath(__file__)); out = os.path.dirname(here)
cmd = ["cargo", "build", "--release"] + (["--offline"] if "--offline" in sys.argv else [])
env = dict(os.environ)
if sys.platform == "darwin": env["RUSTFLAGS"] = env.get("RUSTFLAGS", "") + " -C link-arg=-undefined -C link-arg=dynamic_lookup"   # pyo3 extension modules resolve Python symbols at load time
subprocess.check_call(cmd, cwd=here, env=env)
lib, dst = {"win32": ("dwgscene_fast.dll", "dwgscene_fast.pyd"), "darwin": ("libdwgscene_fast.dylib", "dwgscene_fast.abi3.so")}.get(sys.platform, ("libdwgscene_fast.so", "dwgscene_fast.abi3.so"))
tmp = os.path.join(out, dst + ".tmp"); shutil.copyfile(os.path.join(here, "target", "release", lib), tmp); os.replace(tmp, os.path.join(out, dst))
print("built", os.path.join(out, dst))
