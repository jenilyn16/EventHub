from pathlib import Path
from tkinter import PhotoImage
from functools import lru_cache

BASE = Path(__file__).resolve().parent
PHOTO_DIR = BASE / "photos"

CATEGORY_FOLDERS = {
    "Catering": "catering",
    "Photography": "photography",
    "Venue": "venue",
    "Event Styling & Decoration": "styling",
}

EVENT_FOLDERS = {"Birthday": "birthday", "Debut": "debut", "Wedding": "wedding"}


def ensure_photo_folders():
    folders = [
        PHOTO_DIR / "hero",
        PHOTO_DIR / "events"
    ]

    for event_folder in EVENT_FOLDERS.values():
        for category_folder in CATEGORY_FOLDERS.values():
            folders.append(
                PHOTO_DIR
                / "packages"
                / event_folder
                / category_folder
            )

    folders += [
        PHOTO_DIR / "events" / x
        for x in EVENT_FOLDERS.values()
    ]

    for folder in folders:
        folder.mkdir(
            parents=True,
            exist_ok=True
        )


def _find(folder, stems):
    if not folder.exists():
        return None
    for stem in stems:
        for ext in (".png", ".jpg", ".jpeg", ".webp", ".jfif"):
            candidate = folder / (stem + ext)
            if candidate.exists():
                return candidate
    return None


def package_photo_path(category, package_id, package_name="", event_type=""):
    event_folder = EVENT_FOLDERS.get(
        event_type,
        str(event_type).lower().strip()
    )

    category_folder = CATEGORY_FOLDERS.get(
        category,
        str(category).lower().strip()
    )

    folder = (
        PHOTO_DIR
        / "packages"
        / event_folder
        / category_folder
    )

    import re

    # Get package number from the package name
    # Example:
    # Catering Package 01 -> 1
    # Photography Package 25 -> 25
    match = re.search(
        r"(\d+)\s*$",
        str(package_name)
    )

    if match:
        number = int(match.group(1))
    else:
        number = int(package_id)

    path = _find(
        folder,
        [
            f"{category_folder}{number}",
            f"{category_folder}_{number}",
            f"{category_folder}{number:02d}",
            f"{category_folder}_{number:02d}",
            f"package{number}",
            f"package_{number}",
        ]
    )

    print(
        f"[PHOTO] {event_type} | {category} | "
        f"Package {number} -> {path}"
    )

    return path


def event_photo_path(event_type):
    return _find(PHOTO_DIR / "events" / EVENT_FOLDERS.get(event_type, ""), ["cover", event_type.lower()])



def hero_photo_path():
    return _find(PHOTO_DIR / "hero", ["hero", "home"])

def hero1_photo_path():
    path = PHOTO_DIR / "hero" / "hero1.png"
    print("HERO1 PATH:", path)
    print("HERO1 EXISTS:", path.exists())
    return path if path.exists() else None



@lru_cache(maxsize=256)
def load_image(path, width=260, height=140):
    if not path:
        return None

    try:
        from PIL import Image, ImageTk, ImageOps

        image = Image.open(path).convert("RGB")
        image = ImageOps.fit(
            image,
            (width, height),
            method=Image.Resampling.LANCZOS
        )

        return ImageTk.PhotoImage(image)

    except Exception as e:
        print("IMAGE LOAD ERROR:", repr(e))
        return None

    
def load_faded_image(path, width=1600, height=900, fade=0.68):
    if not path:
        return None

    try:
        from PIL import Image, ImageTk, ImageOps

        image = Image.open(path).convert("RGB")

        image = ImageOps.fit(
            image,
            (width, height),
            method=Image.Resampling.LANCZOS
        )

        # Lighten the image to create a faded background effect
        white = Image.new(
            "RGB",
            image.size,
            "white"
        )

        image = Image.blend(
            image,
            white,
            fade
        )

        return ImageTk.PhotoImage(image)

    except Exception:
        return None


def photo_instructions():
    return PHOTO_DIR / "README.txt"

def get_package_image(image_path):
    if not image_path:
        return None

    path = Path(image_path)

    # Kung absolute path, gamitin mismo.
    if path.is_absolute() and path.is_file():
        return path

    # Kung relative path mula sa project folder.
    project_path = BASE / path
    if project_path.is_file():
        return project_path

    # Subukan din ang filename sa photos/packages.
    package_path = PHOTO_DIR / "packages" / path.name
    if package_path.is_file():
        return package_path

    print("[PACKAGE IMAGE NOT FOUND]", image_path)
    return None