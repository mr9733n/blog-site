import fnmatch
import os
import shutil
import zipfile
from datetime import datetime
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = os.path.join(ROOT_DIR, "blog-site")
# Что архивируем
ARCHIVES = {
    "blog-site": ROOT_DIR / "blog-site",
}

# Папки и паттерны, которые исключаем
EXCLUSIONS = {
    "logs", ".venv", ".idea", "__pycache__", ".git", "node_modules",
    "*.db", "*.pyc", "*.pyo", "*.pyd", "*.log", "*.sqlite3", ".gitattributes", ".gitignore", "_default.conf", "*.mermaid", "*.svg", "*.webp",
    "*.md"
}

def should_exclude(path: Path) -> bool:
    for pattern in EXCLUSIONS:
        if fnmatch.fnmatch(path.name, pattern):
            return True
    for part in path.parts:
        for pattern in EXCLUSIONS:
            if fnmatch.fnmatch(part, pattern):
                return True
    return False

def create_clean_archive(source_dir: Path, output_dir: Path, archive_name: str):
    temp_dir = output_dir / "temp_archive"
    archive_root_dir = temp_dir / archive_name
    archive_path = output_dir / f"{archive_name}.zip"

    # Удалим временную папку, если осталась с прошлого раза
    if temp_dir.exists():
        shutil.rmtree(temp_dir)
    temp_dir.mkdir(parents=True)
    archive_root_dir.mkdir(parents=True)

    # Копируем файлы, исключая мусор
    for root, dirs, files in os.walk(source_dir):
        rel_path = Path(root).relative_to(source_dir)
        dest_path = archive_root_dir / rel_path

        dirs[:] = [d for d in dirs if not should_exclude(Path(root) / d)]
        dest_path.mkdir(parents=True, exist_ok=True)

        for file in files:
            file_path = Path(root) / file
            if not should_exclude(file_path):
                shutil.copy2(file_path, dest_path / file)

    # Архивируем
    with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for root, dirs, files in os.walk(archive_root_dir):
            for file in files:
                file_path = Path(root) / file
                archive.write(file_path, file_path.relative_to(temp_dir))

    shutil.rmtree(temp_dir)
    print(f"✅ Архив создан {datetime.now()}: {archive_path}")

if __name__ == "__main__":
    for name, path in ARCHIVES.items():
        if not path.exists():
            print(f"⚠️ Пропущено: {name}, путь не существует: {path}")
            continue
        create_clean_archive(path, ROOT_DIR, name)
