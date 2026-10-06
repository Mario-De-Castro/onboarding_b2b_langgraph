from pydantic import BaseModel
from typing import Literal

class HumanDecisionRequest(BaseModel):
    decision: Literal["APPROVE", "REJECT"]