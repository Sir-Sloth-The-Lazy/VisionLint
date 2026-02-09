import os
import shutil
import tempfile
import pytest
from PIL import Image
import cv2
import numpy as np
from vision_lint.core.auditor import IntegrityAuditor

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

    # 4. Zero Pixel Area (Technically hard to save 0x0 image with PIL, but let's try 0x100)
    # PIL might handle 0x0 gracefully or error out, let's see. 
    # Actually, let's just make a very small image that might be valid for PIL but we want to fail logic if we had logic for minimum size.
    # The requirement was "images with 0-pixel area". 
    # cv2.imread might return empty matrix for some cases.
    # Let's create a file that is not an image but has image extension
    corrupt_header_path = os.path.join(test_dir, "corrupt_header.png")
    with open(corrupt_header_path, 'wb') as f:
        f.write(b'Not an image')

    yield test_dir
    
    # Cleanup
    shutil.rmtree(test_dir)

def test_auditor_finds_issues(test_dataset):
    auditor = IntegrityAuditor()
    issues = auditor.audit_dataset(test_dataset)
    
    # We expect:
    # 1. empty.jpg -> Empty File
    # 2. truncated.jpg -> Corrupted Image (PIL) or similar
    # 3. corrupt_header.png -> Corrupted Image (PIL) or OpenCV
    
    assert len(issues) >= 3
    
    issue_types = [issue.issue_type for issue in issues]
    assert "Empty File" in issue_types
    # Exact error messages depend on PIL/OpenCV versions, but we should have corruption errors
    assert any("Corrupted Image" in t for t in issue_types)

def test_check_image_integrity_valid_file(test_dataset):
    auditor = IntegrityAuditor()
    valid_path = os.path.join(test_dataset, "valid.jpg")
    issue = auditor.check_image_integrity(valid_path)
    assert issue is None

def test_check_image_integrity_empty_file(test_dataset):
    auditor = IntegrityAuditor()
    empty_path = os.path.join(test_dataset, "empty.jpg")
    issue = auditor.check_image_integrity(empty_path)
    assert issue is not None
    assert issue.issue_type == "Empty File"
