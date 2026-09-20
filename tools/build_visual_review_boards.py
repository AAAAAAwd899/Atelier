"""Build compact contact sheets from Atelier's current-source capture suites."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output" / "playwright"
BOARDS = OUTPUT / "visual-review-boards"

SUITES = {
    "final-matrix": ["home", "library", "widgets", "tools", "question", "answer"],
    "final-home-workflows": ["library-grid", "library-list", "progress"],
    "final-planner": ["exam-setup", "practice-builder", "pip", "results"],
    "final-card": ["card-studio", "mask-studio"],
}


def font(size: int) -> ImageFont.ImageFont:
    try:
        return ImageFont.truetype("arial.ttf", size)
    except OSError:
        return ImageFont.load_default()


def entries(theme: str, viewport: str) -> list[tuple[str, Path]]:
    found: list[tuple[str, Path]] = []
    for suite, screens in SUITES.items():
        for screen in screens:
            path = OUTPUT / suite / f"{theme}-{screen}-{viewport}.png"
            if not path.exists():
                raise FileNotFoundError(path)
            found.append((screen, path))
    return found


def board(theme: str, viewport: str, cell: tuple[int, int], columns: int) -> Path:
    items = entries(theme, viewport)
    label_height = 38
    rows = (len(items) + columns - 1) // columns
    canvas = Image.new("RGB", (cell[0] * columns, (cell[1] + label_height) * rows), "#09121d")
    draw = ImageDraw.Draw(canvas)
    label_font = font(21)
    for index, (screen, path) in enumerate(items):
        image = Image.open(path).convert("RGB")
        image.thumbnail(cell, Image.Resampling.LANCZOS)
        x = (index % columns) * cell[0] + (cell[0] - image.width) // 2
        y = (index // columns) * (cell[1] + label_height)
        canvas.paste(image, (x, y))
        draw.text((x + 8, y + cell[1] + 6), screen, fill="#e8edf5", font=label_font)
    destination = BOARDS / f"{theme}-{viewport}-all-screens.png"
    destination.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(destination, optimize=True)
    return destination


def main() -> None:
    made = [
        board("forest", "1440x900", (480, 300), 3),
        board("forest", "390x720", (260, 480), 3),
        board("sunset-beach", "1440x900", (480, 300), 3),
        board("castle", "1440x900", (480, 300), 3),
        board("linen", "1440x900", (480, 300), 3),
    ]
    print("\n".join(str(path) for path in made))


if __name__ == "__main__":
    main()
