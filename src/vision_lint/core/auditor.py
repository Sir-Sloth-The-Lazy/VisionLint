import os
from typing import List
import cv2
import numpy as np
from PIL import Image, UnidentifiedImageError
import logging
from vision_lint.base import BaseLinter, LintResult

# logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class IntegrityLinter(BaseLinter):
    def __init__(self):
        self.supported_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp'}

    def check(self, data_path: str) -> List[LintResult]:
        """
        Recursively scans the directory and checks for integrity issues.
        Skips hidden files and system files.
        """
        results = []
        if not os.path.exists(data_path):
            logger.error(f"Path not found: {data_path}")
            return [LintResult(
                file_path=data_path,
                linter_name="IntegrityLinter",
                issue_type="Path Error",
                severity="Critical",
                message="Path does not exist"

            )]

        # Handle single file check
        if os.path.isfile(data_path):
            if any(data_path.lower().endswith(ext) for ext in self.supported_extensions):
                return self.check_image_integrity(data_path)
            else:
                return [LintResult(
                    file_path=data_path,
                    linter_name="IntegrityLinter",
                    issue_type="No Images Found",
                    severity="Critical",
                    message=f"File extension not supported. Supported: {self.supported_extensions}"
                )]

        images_found = False
        for root, _, files in os.walk(data_path):
            for file in files:
                # Reliability: Skip hidden files and system files
                if file.startswith('.') or file == 'Thumbs.db':
                    logger.debug(f"Skipping hidden/system file: {file}")
                    continue

                if any(file.lower().endswith(ext) for ext in self.supported_extensions):
                    images_found = True
                    file_path = os.path.join(root, file)
                    file_results = self.check_image_integrity(file_path)
                    results.extend(file_results)
        
        if not images_found:
            return [LintResult(
                file_path=data_path,
                linter_name="IntegrityLinter",
                issue_type="No Images Found",
                severity="Critical",
                message=f"No image files found with extensions {self.supported_extensions}"
            )]
            
        return results

    def check_image_integrity(self, file_path: str) -> List[LintResult]:
        """
        Checks a single image for corruption, truncation, 0-pixel area, and hidden grayscale.
        Includes robust error handling for unreadable files.
        """
        results: List[LintResult] = []
        try:
            # 1. Check if file is empty
            if os.path.getsize(file_path) == 0:
                return [LintResult(
                    file_path=file_path,
                    linter_name="IntegrityLinter",
                    issue_type="Empty File",
                    severity="Critical",
                    message="File size is 0 bytes"
                )]

            # 2. Check with PIL (detects truncation and basic corruption)
            try:
                with Image.open(file_path) as img:
                    img.verify() # Verify file integrity
            except (IOError, SyntaxError, UnidentifiedImageError) as e:
                 return [LintResult(
                    file_path=file_path,
                    linter_name="IntegrityLinter",
                    issue_type="Corrupted Image (PIL)",
                    severity="Critical",
                    message=f"PIL cannot open/verify image: {str(e)}"
                )]

            # 3. Check with OpenCV (detects decoding errors and empty images)
            try:
                img_cv = cv2.imread(file_path)
            except cv2.error as e:
                return [LintResult(
                    file_path=file_path,
                    linter_name="IntegrityLinter",
                    issue_type="Corrupted Image (OpenCV)",
                    severity="Critical",
                    message=f"OpenCV cannot decode image: {str(e)}"
                )]

            if img_cv is None:
                return [LintResult(
                    file_path=file_path,
                    linter_name="IntegrityLinter",
                    issue_type="Corrupted Image (OpenCV)",
                    severity="Critical",
                    message="OpenCV cannot decode image (returned None)"
                )]
            
            if img_cv.size == 0 or img_cv.shape[0] == 0 or img_cv.shape[1] == 0:
                 return [LintResult(
                    file_path=file_path,
                    linter_name="IntegrityLinter",
                    issue_type="Zero Pixel Area",
                    severity="Critical",
                    message=f"Image has invalid dimensions: {img_cv.shape}"
                )]

            # 4. Check for hidden grayscale (R=G=B) in RGB images
            # OpenCV loads as BGR. If all channels are equal, it's grayscale.
            # Performance: Uses vectorized NumPy comparisons.
            if len(img_cv.shape) == 3 and img_cv.shape[2] == 3:
                b, g, r = cv2.split(img_cv)
                if np.array_equal(b, g) and np.array_equal(b, r):
                    results.append(LintResult(
                        file_path=file_path,
                        linter_name="IntegrityLinter",
                        issue_type="Grayscale as RGB",
                        severity="Warning",
                        message="Image is encoded as RGB but all pixels are grayscale (R=G=B)"
                    ))

            return results

        except Exception as e:
             logger.exception(f"Unexpected error auditing file {file_path}")
             return [LintResult(
                file_path=file_path,
                linter_name="IntegrityLinter",
                issue_type="Unknown Error",
                severity="Critical",
                message=f"An unexpected error occurred: {str(e)}"
            )]
