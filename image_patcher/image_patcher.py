import argparse
from PIL import Image
from pathlib import Path

def apply_patch(original_image_path: str, patch_image_path: str, x: int, y: int, output_path: str):
    """
    Pastes a patch image onto an original image at the given coordinates.

    Args:
        original_image_path (str): Path to the original image.
        patch_image_path (str): Path to the patch image.
        x (int): The x-coordinate for the top-left corner of the patch.
        y (int): The y-coordinate for the top-left corner of the patch.
        output_path (str): Path to save the resulting image.
    """
    try:
        with Image.open(original_image_path) as original, Image.open(patch_image_path) as patch:
            original_copy = original.copy()            
            mask = patch if patch.mode == 'RGBA' else None            
            original_copy.paste(patch, (x, y), mask=mask)
            original_copy.save(output_path)
    except FileNotFoundError as e:
        print(f"Error: Input file not found - {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

def batch_patch(original_dir_path: str, patch_image_path: str, x: int, y: int, output_dir_path: str):
    """
    Applies a patch to all .png images in a source directory and saves them to an output directory.

    Args:
        original_dir_path (str): Path to the directory with original .png images.
        patch_image_path (str): Path to the patch image.
        x (int): The x-coordinate for the top-left corner of the patch.
        y (int): The y-coordinate for the top-left corner of the patch.
        output_dir_path (str): Path to the directory to save patched images.
    """
    source_dir = Path(original_dir_path)
    output_dir = Path(output_dir_path)

    if not source_dir.is_dir():
        print(f"Error: Source directory not found at '{source_dir}'")
        return

    output_dir.mkdir(parents=True, exist_ok=True)
    png_files = list(source_dir.glob('*.png'))
    if not png_files:
        print(f"No .png files found in '{source_dir}'")
        return

    print(f"Found {len(png_files)} .png files. Starting batch patch...")
    for original_image_path in png_files:
        output_path = output_dir / original_image_path.name
        print(f"  - Patching '{original_image_path.name}'...")
        apply_patch(str(original_image_path), patch_image_path, x, y, str(output_path)) 

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="A tool to paste a patch image onto a single image or a batch of images.",
        formatter_class=argparse.RawTextHelpFormatter # Allows for newlines in help text
    )
    subparsers = parser.add_subparsers(dest="mode", required=True, help="Available modes")

    # --- Single image mode ---
    parser_single = subparsers.add_parser("single", help="Patch a single image.\nUsage: image_patcher.py single original.png patch.png output.png -c 10 20")
    parser_single.add_argument("original_image", help="Path to the original image file.")
    parser_single.add_argument("patch_image", help="Path to the patch image file.")
    parser_single.add_argument("output_image", help="Path for the output patched image.")
    parser_single.add_argument("-c", "--coords", nargs=2, type=int, required=True, metavar=('X', 'Y'), help="X and Y coordinates to paste the patch.")

    # --- Batch mode ---
    parser_batch = subparsers.add_parser("batch", help="Patch all .png images in a directory.\nUsage: image_patcher.py batch ./originals_dir patch.png ./output_dir -c 10 20")
    parser_batch.add_argument("original_dir", help="Path to the directory with original .png images.")
    parser_batch.add_argument("patch_image", help="Path to the patch image file.")
    parser_batch.add_argument("output_dir", help="Path to the directory for patched images.")
    parser_batch.add_argument("-c", "--coords", nargs=2, type=int, required=True, metavar=('X', 'Y'), help="X and Y coordinates to paste the patch.")

    args = parser.parse_args()

    if args.mode == "single":
        apply_patch(args.original_image, args.patch_image, args.coords[0], args.coords[1], args.output_image)
    elif args.mode == "batch":
        batch_patch(args.original_dir, args.patch_image, args.coords[0], args.coords[1], args.output_dir)
