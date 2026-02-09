import os
from dataclasses import dataclass
from typing import List, Optional, Tuple
import cv2
import numpy as np
from PIL import Image
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class Issue:
    file_path: str
    issue_type: str
    description: str

class IntegrityAuditor:
    def __init__(self):
        self.supported_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp'}

    def audit_dataset(self, path: str) -> List[Issue]:
        """
        recursively scans the directory and checks for integrity issues.
        """
        issues = []
        if not os.path.exists(path):
            logger.error(f"Path not found: {path}")
            return [Issue(path, "Path Error", "Path does not exist")]

        for root, _, files in os.walk(path):
            for file in files:
                if any(file.lower().endswith(ext) for ext in self.supported_extensions):
                    file_path = os.path.join(root, file)
                    issue = self.check_image_integrity(file_path)
                    if issue:
                        issues.append(issue)
        return issues

    def check_image_integrity(self, file_path: str) -> Optional[Issue]:
        """
        Checks a single image for corruption, truncation, or 0-pixel area.
        """
        try:
            # 1. Check if file is empty
            if os.path.getsize(file_path) == 0:
                return Issue(file_path, "Empty File", "File size is 0 bytes")

            # 2. Check with PIL (detects truncation and basic corruption)
            try:
                with Image.open(file_path) as img:
                    img.verify() # Verify file integrity
            except (IOError, SyntaxError) as e:
                return Issue(file_path, "Corrupted Image (PIL)", f"PIL cannot open/verify image: {str(e)}")

            # 3. Check with OpenCV (detects decoding errors and empty images)
            img_cv = cv2.imread(file_path)
            if img_cv is None:
                return Issue(file_path, "Corrupted Image (OpenCV)", "OpenCV cannot decode image")
            
            if img_cv.size == 0 or img_cv.shape[0] == 0 or img_cv.shape[1] == 0:
                 return Issue(file_path, "Zero Pixel Area", f"Image has invalid dimensions: {img_cv.shape}")

            return None # No issues found

        except Exception as e:
             return Issue(file_path, "Unknown Error", f"An unexpected error occurred: {str(e)}")
