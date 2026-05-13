#!/usr/bin/env python3
"""
Fix PaddleFormers augment_utils.py for Pillow >= 10.x compatibility.

Pillow 10+ removed support for string resampling filter names like "nearest".
This patch converts string names to Image.Resampling enum values.

Usage:
    python scripts/fix_pillow_compat.py
"""

import os
import sys


def find_augment_utils():
    """Find augment_utils.py in paddleformers installation."""
    import paddleformers
    pkg_dir = os.path.dirname(paddleformers.__file__)
    target = os.path.join(pkg_dir, "datasets", "template", "augment_utils.py")
    if os.path.exists(target):
        return target
    # fallback search
    for root, dirs, files in os.walk(pkg_dir):
        if "augment_utils.py" in files:
            return os.path.join(root, "augment_utils.py")
    return None


def patch_file(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    old_line = "        return img.rotate(angle, self.interpolation, self.expand)"
    new_line = """        # Pillow 10+ compat: convert string filter to enum
        if isinstance(self.interpolation, str):
            interpolation = getattr(
                __import__("PIL.Image", fromlist=["Resampling"]).Resampling,
                self.interpolation.upper(),
                __import__("PIL.Image", fromlist=["Resampling"]).Resampling.BILINEAR,
            )
        else:
            interpolation = self.interpolation
        return img.rotate(angle, interpolation, self.expand)"""

    if old_line not in content:
        print(f"⚠️ Could not find expected line in {filepath}")
        print("Content may have changed. Manual inspection needed.")
        return False

    if new_line.split("\n")[0] in content:
        print(f"✅ Already patched: {filepath}")
        return True

    content = content.replace(old_line, new_line)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"✅ Patched: {filepath}")
    return True


def main():
    filepath = find_augment_utils()
    if not filepath:
        print("❌ Could not find augment_utils.py in paddleformers installation.")
        sys.exit(1)

    print(f"Found: {filepath}")
    if patch_file(filepath):
        print("\nPatch applied successfully. You can now run training.")
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
