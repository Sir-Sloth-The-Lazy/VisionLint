import os
import shutil
import tempfile
import pytest
from PIL import Image
import cv2
import numpy as np
from vision_lint.core.auditor import IntegrityLinter

@pytest.fixture
def test_dataset():
    # Create a temporary directory
    test_dir = tempfile.mkdtemp()
    
    # 1. Valid Image
    valid_path = os.path.join(test_dir, "valid.jpg")
    img = Image.new('RGB', (100, 100), color = 'red')
    img.save(valid_path)

    # 2. Empty File
    empty_path = os.path.join(test_dir, "empty.jpg")
    with open(empty_path, 'wb') as f:
        pass

    # 3. Truncated Image (Create valid then truncate)
    truncated_path = os.path.join(test_dir, "truncated.jpg")
    img.save(truncated_path)
    with open(truncated_path, 'ab') as f:
        f.truncate(10) # Truncate to 10 bytes

    # 4. Zero Pixel Area / Corrupt Header
    corrupt_header_path = os.path.join(test_dir, "corrupt_header.png")
    with open(corrupt_header_path, 'wb') as f:
        f.write(b'Not an image')

    # 5. Hidden Grayscale in RGB
    # Create an RGB image where R=G=B
    grayscale_rgb_path = os.path.join(test_dir, "grayscale_rgb.jpg")
    # Create a 100x100 gray image (single channel)
    gray_img = np.full((100, 100), 128, dtype=np.uint8)
    # Convert to RGB (stacking it 3 times)
    rgb_from_gray = cv2.merge([gray_img, gray_img, gray_img])
    cv2.imwrite(grayscale_rgb_path, rgb_from_gray)

    yield test_dir
    
    # Cleanup
    shutil.rmtree(test_dir)

def test_linter_finds_issues(test_dataset):
    linter = IntegrityLinter()
    results = linter.check(test_dataset)
    
    # We expect issues for: empty, truncated, corrupt_header, grayscale_rgb
    # valid.jpg should be fine.
    
    assert len(results) >= 4
    
    issue_types = [result.issue_type for result in results]
    assert "Empty File" in issue_types
    assert any("Corrupted Image" in t for t in issue_types)
    assert "Grayscale as RGB" in issue_types

def test_check_image_integrity_valid_file(test_dataset):
    linter = IntegrityLinter()
    valid_path = os.path.join(test_dataset, "valid.jpg")
    results = linter.check_image_integrity(valid_path)
    assert len(results) == 0

def test_check_image_integrity_empty_file(test_dataset):
    linter = IntegrityLinter()
    empty_path = os.path.join(test_dataset, "empty.jpg")
    results = linter.check_image_integrity(empty_path)
    assert len(results) == 1
    assert results[0].issue_type == "Empty File"

def test_check_grayscale_detection(test_dataset):
    linter = IntegrityLinter()
    grayscale_path = os.path.join(test_dataset, "grayscale_rgb.jpg")
    results = linter.check_image_integrity(grayscale_path)
    
    assert len(results) == 1
    assert results[0].issue_type == "Grayscale as RGB"
    assert results[0].severity == "Warning"

def test_linter_no_images_found(test_dataset):
    linter = IntegrityLinter()
    # Create a sub-directory with no images
    no_images_dir = os.path.join(test_dataset, "no_images")
    os.makedirs(no_images_dir)
    with open(os.path.join(no_images_dir, "text_file.txt"), "w") as f:
        f.write("Just text")
        
    results = linter.check(no_images_dir)
    assert len(results) == 1
    assert results[0].issue_type == "No Images Found"
    assert results[0].severity == "Critical"

def test_linter_skips_hidden_files(test_dataset):
    linter = IntegrityLinter()
    # Create a hidden file that would otherwise be flagged as empty/corrupt
    hidden_path = os.path.join(test_dataset, ".hidden.jpg")
    with open(hidden_path, 'wb') as f:
        pass # Empty file, would trigger error if checked
        
    # Also create a valid file so we don't trigger "No Images Found"
    valid_path = os.path.join(test_dataset, "visible.jpg")
    img = Image.new('RGB', (10, 10), color = 'blue')
    img.save(valid_path)

    results = linter.check(test_dataset)
    # Should only find issues for the pre-existing test_dataset setup (valid, empty, truncated, etc.)
    # We need to filter results for our specific files
    
    hidden_issues = [r for r in results if r.file_path == hidden_path]
    assert len(hidden_issues) == 0

def test_linter_single_file(test_dataset):
    linter = IntegrityLinter()
    valid_path = os.path.join(test_dataset, "valid.jpg")
    results = linter.check(valid_path)
    assert len(results) == 0

def test_linter_single_file_unsupported(test_dataset):
    linter = IntegrityLinter()
    text_path = os.path.join(test_dataset, "text.txt")
    with open(text_path, "w") as f:
        f.write("text")
    results = linter.check(text_path)
    assert len(results) == 1
    assert results[0].issue_type == "No Images Found"
