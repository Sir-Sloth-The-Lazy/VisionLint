from abc import ABC, abstractmethod
from typing import List
from pydantic import BaseModel

class LintResult(BaseModel):
    file_path: str
    linter_name: str
    issue_type: str
    severity: str
    message: str

class BaseLinter(ABC):
    @abstractmethod
    def check(self, data_path: str) -> List[LintResult]:
        """
        Run the linter on the given path and return a list of LintResults.
        """
        pass
