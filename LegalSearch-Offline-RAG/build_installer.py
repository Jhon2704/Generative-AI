# -*- coding: utf-8 -*-
"""
build_installer.py - Orquestador de empaquetado para LegalSearch Offline Qt

Pasos:
  1. SVG -> ICO  (cairosvg + Pillow)
  2. PyInstaller -> dist/LegalSearchOfflineQt.exe  (onefile, solo bytecode)
  3. Inno Setup  -> dist/LegalSearch_Offline_Setup.exe
"""

import io
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent
SVG_SRC = ROOT / "src" / "legalsearch_icon.svg"
ICO_OUT = ROOT / "resources" / "legalsearch_icon.ico"
SPEC_FILE = ROOT / "LegalSearchOfflineQt.spec"
ISS_FILE = ROOT / "installer.iss"

ISCC_CANDIDATES = [
    r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
    r"C:\Program Files\Inno Setup 6\ISCC.exe",
    r"C:\Program Files (x86)\Inno Setup 5\ISCC.exe",
    r"C:\Program Files\Inno Setup 5\ISCC.exe",
]

# --- helpers ------------------------------------------------------------------

def _print(msg: str, ok: bool = True) -> None:
    prefix = "[OK]" if ok else "[ERROR]"
    print(f"  {prefix}  {msg}")


def _run(cmd: list, *, cwd: Path = ROOT) -> None:
    """Ejecuta un subproceso y termina con error si falla."""
    print(f"\n  $ {' '.join(str(c) for c in cmd)}")
    result = subprocess.run(cmd, cwd=str(cwd))
    if result.returncode != 0:
        _print(f"Comando fallo con codigo {result.returncode}", ok=False)
        sys.exit(result.returncode)


# --- paso 1: SVG -> ICO -------------------------------------------------------

def build_icon() -> None:
    print("\n[1/3] Convirtiendo SVG -> ICO ...")


    try:
        import cairosvg  # noqa: F401
        from PIL import Image
    except ImportError:
        _print(
            "Faltan dependencias. Instalalas con:\n"
            "       pip install cairosvg Pillow",
            ok=False,
        )
        sys.exit(1)

    ICO_OUT.parent.mkdir(parents=True, exist_ok=True)

    sizes = [16, 32, 48, 256]
    images = []

    for size in sizes:
        png_bytes = cairosvg.svg2png(
            url=str(SVG_SRC),
            output_width=size,
            output_height=size,
        )
        img = Image.open(io.BytesIO(png_bytes)).convert("RGBA")
        images.append(img)

    # Guardar como ICO multi-resolucion
    images[0].save(
        ICO_OUT,
        format="ICO",
        sizes=[(s, s) for s in sizes],
        append_images=images[1:],
    )
    _print(f"Icono guardado en {ICO_OUT}")


# --- paso 2: PyInstaller ------------------------------------------------------

def build_exe() -> None:
    print("\n[2/3] Empaquetando con PyInstaller (onefile) ...")

    if not SPEC_FILE.exists():
        _print(f"No se encontro {SPEC_FILE}", ok=False)
        sys.exit(1)

    _run([sys.executable, "-m", "PyInstaller", str(SPEC_FILE), "--noconfirm"])
    dist_exe = ROOT / "dist" / "LegalSearchOfflineQt.exe"
    if dist_exe.exists():
        _print(f"EXE listo: {dist_exe}")
    else:
        _print("No se encontro el EXE de salida; revisa el log de PyInstaller.", ok=False)
        sys.exit(1)


# --- paso 3: Inno Setup -------------------------------------------------------

def _find_iscc():
    # 1. PATH del sistema
    iscc = shutil.which("iscc") or shutil.which("ISCC")
    if iscc:
        return iscc
    # 2. Rutas estandar de instalacion
    for candidate in ISCC_CANDIDATES:
        if Path(candidate).exists():
            return candidate
    return None


def build_installer() -> None:
    print("\n[3/3] Compilando instalador con Inno Setup ...")

    iscc = _find_iscc()
    if iscc is None:
        _print(
            "iscc.exe no encontrado. Instala Inno Setup desde:\n"
            "       https://jrsoftware.org/isdl.php\n\n"
            "  Luego ejecuta manualmente:\n"
            f"       iscc \"{ISS_FILE}\"",
            ok=False,
        )
        print("\n  El EXE portable (sin instalador) ya esta en:")
        print(f"    {ROOT / 'dist' / 'LegalSearchOfflineQt.exe'}")
        return

    _run([iscc, str(ISS_FILE)])
    installer = ROOT / "dist" / "LegalSearch_Offline_Setup.exe"
    if installer.exists():
        _print(f"Instalador listo: {installer}")
    else:
        _print("No se genero el instalador; revisa el log de Inno Setup.", ok=False)


# --- main ---------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 60)
    print("  LegalSearch Offline - Build Installer")
    print("=" * 60)

    build_icon()
    build_exe()
    build_installer()

    print("\n" + "=" * 60)
    print("  Build completado.")
    print("=" * 60)
