from pydantic import BaseModel


class FieldAnswerRequest(BaseModel):
    field_label: str
    profile_text: str


class FieldAnswerOut(BaseModel):
    answer: str
