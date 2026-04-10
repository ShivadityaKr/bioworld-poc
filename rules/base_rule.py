from abc import ABC, abstractmethod
import pandas as pd


class BaseRule(ABC):
    rule_id: str
    rule_name: str

    @abstractmethod
    def validate(self, row: pd.Series, context: dict) -> dict:
        """
        Returns:
        {
            "rule_id":   str,
            "rule_name": str,
            "status":    "PASS" | "FAIL",
            "reason":    str | None
        }
        """
        pass

    def _pass(self) -> dict:
        return {"rule_id": self.rule_id, "rule_name": self.rule_name,
                "status": "PASS", "reason": None}

    def _fail(self, reason: str) -> dict:
        return {"rule_id": self.rule_id, "rule_name": self.rule_name,
                "status": "FAIL", "reason": reason}
