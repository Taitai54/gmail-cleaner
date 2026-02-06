#!/usr/bin/env python3
"""
Create icon files for Gmail Cleaner app
Generates .icns for macOS and .ico for Windows
"""

import subprocess
import os
from pathlib import Path

def create_png_from_svg(svg_path, png_path, size):
    """Convert SVG to PNG using sips (macOS built-in tool)"""
    # First convert to a temporary large PNG
    temp_png = f"{png_path}.temp.png"

    # Use qlmanage to convert SVG to PNG (macOS built-in)
    try:
        subprocess.run([
            "qlmanage", "-t", "-s", str(size), "-o", os.path.dirname(png_path), svg_path
        ], check=True, capture_output=True)

        # qlmanage creates filename with .png.png extension
        generated = f"{svg_path}.png"
        if os.path.exists(generated):
            os.rename(generated, png_path)
            return True
    except:
        pass

    # Fallback: use sips to create a basic icon
    try:
        # Create a simple colored square as fallback
        subprocess.run([
            "sips", "-z", str(size), str(size), svg_path, "--out", png_path
        ], check=True, capture_output=True)
        return True
    except:
        return False

def create_iconset():
    """Create macOS iconset and .icns file"""
    project_dir = Path(__file__).parent
    svg_path = project_dir / "icon.svg"
    iconset_dir = project_dir / "gmail-cleaner.iconset"

    # Create iconset directory
    iconset_dir.mkdir(exist_ok=True)

    # Required icon sizes for macOS
    sizes = [
        (16, "icon_16x16.png"),
        (32, "icon_16x16@2x.png"),
        (32, "icon_32x32.png"),
        (64, "icon_32x32@2x.png"),
        (128, "icon_128x128.png"),
        (256, "icon_128x128@2x.png"),
        (256, "icon_256x256.png"),
        (512, "icon_256x256@2x.png"),
        (512, "icon_512x512.png"),
        (1024, "icon_512x512@2x.png"),
    ]

    print("Creating PNG icons from SVG...")
    for size, filename in sizes:
        output = iconset_dir / filename
        print(f"  Creating {filename} ({size}x{size})...")
        create_png_from_svg(str(svg_path), str(output), size)

    # Convert iconset to .icns using iconutil
    print("\nCreating .icns file...")
    icns_path = project_dir / "gmail-cleaner.icns"
    try:
        subprocess.run([
            "iconutil", "-c", "icns", str(iconset_dir), "-o", str(icns_path)
        ], check=True)
        print(f"✓ Created {icns_path}")
    except Exception as e:
        print(f"✗ Failed to create .icns: {e}")

    # Create Windows .ico file (256x256 PNG should work)
    print("\nCreating Windows .ico file...")
    ico_path = project_dir / "gmail-cleaner.ico"
    png_256 = iconset_dir / "icon_256x256.png"

    if png_256.exists():
        try:
            # Use sips to convert PNG to ico format
            subprocess.run([
                "sips", "-s", "format", "icns", str(png_256), "--out", str(ico_path)
            ], check=True, capture_output=True)
            # Rename to .ico
            if ico_path.with_suffix('.icns').exists():
                ico_path.with_suffix('.icns').rename(ico_path)
            print(f"✓ Created {ico_path}")
        except Exception as e:
            # If sips fails, just copy the PNG as .ico (Windows can often use PNG as .ico)
            import shutil
            shutil.copy(png_256, ico_path)
            print(f"✓ Created {ico_path} (PNG format)")

    print("\n✓ Icon creation complete!")
    print(f"  - macOS: {icns_path}")
    print(f"  - Windows: {ico_path}")

if __name__ == "__main__":
    create_iconset()
