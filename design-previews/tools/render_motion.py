"""Render concept SVGs to GIFs through the bundled beautify-github-readme pipeline.

The upstream renderer shells out to `rsvg-convert` (or macOS `sips`). Neither is
available on this Windows host, so only the SVG rasterizer is replaced with
headless Chrome. Layer extraction, timing, easing, chroma flattening, palette
generation and GIF encoding all remain the Skill's own code.

Run: python design-previews/tools/render_motion.py [concept ...]
"""

from __future__ import annotations

import argparse
import importlib.util
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
PREVIEWS = ROOT / "design-previews"
SKILL_SCRIPT = (
    ROOT
    / "dist"
    / "tools-src"
    / "beautify-github-readme-main"
    / "skills"
    / "beautify-github-readme"
    / "scripts"
    / "render_motion_gif.py"
)

CHROME_CANDIDATES = [
    Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
    Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
]


def chrome() -> Path:
    for candidate in CHROME_CANDIDATES:
        if candidate.is_file():
            return candidate
    raise SystemExit("Chrome not found; cannot rasterize SVG layers")


def svg_size(path: Path) -> tuple[int, int]:
    head = path.read_text(encoding="utf-8", errors="ignore")[:600]
    width = re.search(r'\bwidth="(\d+)"', head)
    height = re.search(r'\bheight="(\d+)"', head)
    if width and height:
        return int(width.group(1)), int(height.group(1))
    raise SystemExit(f"cannot read SVG size: {path}")


class ChromeRenderer:
    """Drop-in stand-in for the Skill's rsvg-convert renderer."""

    def render(self, svg_path: Path, png_path: Path) -> None:
        width, height = svg_size(svg_path)
        with tempfile.TemporaryDirectory(prefix="chrome-profile-") as profile:
            command = [
                str(chrome()),
                "--headless=new",
                "--disable-gpu",
                "--hide-scrollbars",
                "--no-first-run",
                "--no-default-browser-check",
                "--disable-extensions",
                "--default-background-color=00000000",
                "--force-device-scale-factor=1",
                f"--user-data-dir={profile}",
                f"--window-size={width},{height}",
                "--virtual-time-budget=2500",
                f"--screenshot={png_path}",
                svg_path.resolve().as_uri(),
            ]
            subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def load_skill_module():
    spec = importlib.util.spec_from_file_location("render_motion_gif", SKILL_SCRIPT)
    if spec is None or spec.loader is None:
        raise SystemExit(f"cannot load {SKILL_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


STILL_AT = {
    "concept-a-ai-orchestration": 0.42,
    "concept-b-intelligence-engine": 0.84,
    "concept-c-creative-automation": 0.78,
}


def still_from_gif(gif: Path, target: Path, fraction: float = 0.66) -> None:
    with Image.open(gif) as image:
        index = min(image.n_frames - 1, int(image.n_frames * fraction))
        image.seek(index)
        image.convert("RGB").save(target)


def render(name: str) -> None:
    folder = PREVIEWS / name
    svg = folder / "hero.svg"
    spec = folder / "hero-motion.json"
    gif = folder / "hero.gif"
    if not svg.is_file() or not spec.is_file():
        raise SystemExit(f"missing source in {folder}")

    module = load_skill_module()
    renderer = ChromeRenderer()

    def choose_renderer() -> tuple[str, str]:
        return "chrome", str(chrome())

    def render_svg(_renderer, svg_path, png_path) -> None:
        renderer.render(Path(svg_path), Path(png_path))

    module.choose_renderer = choose_renderer
    module.render_svg = render_svg

    module.run(
        argparse.Namespace(input_svg=svg, output_gif=gif, spec=spec, keep_frames=None)
    )

    still_from_gif(gif, folder / "preview.png", STILL_AT.get(name, 0.66))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("concepts", nargs="*")
    args = parser.parse_args()
    names = args.concepts or sorted(p.name for p in PREVIEWS.glob("concept-*") if p.is_dir())
    for name in names:
        print(f"--- {name}")
        render(name)


if __name__ == "__main__":
    main()
