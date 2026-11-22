from typing import Literal
import re
from pydantic import BaseModel, Field, model_validator

Value = str | int | float | bool | None
Mode = Literal["local_ai", "offline_demo"]

class Condition(BaseModel):
    field: str
    equals: Value

class FieldSpec(BaseModel):
    key: str = Field(pattern=r'^[a-z][a-z0-9_]{0,49}$')
    label: str = Field(min_length=1,max_length=90)
    type: Literal["text","number","currency","date","time","boolean","email","phone","address","select"] = "text"
    required: bool = False
    when: Condition | None = None
    options: list[str] = Field(default_factory=list, max_length=100)
    minimum: float | None = None
    maximum: float | None = None
    integer: bool = False
    aliases: dict[str,Value] = Field(default_factory=dict,max_length=50)

class Workflow(BaseModel):
    id: str = Field(pattern=r'^[a-z][a-z0-9_]{0,49}$')
    name: str = Field(min_length=1,max_length=120)
    title: str = Field(min_length=1,max_length=120)
    industry: str = Field(min_length=1,max_length=80)
    description: str = Field(default="",max_length=2000)
    channels: list[str] = Field(min_length=1,max_length=8)
    reviewer: str = Field(min_length=1,max_length=80)
    output: Literal["json","csv","xlsx","docx","pdf","zip"]
    fields: list[FieldSpec] = Field(min_length=1,max_length=45)
    clarification: str = Field(default="",max_length=1000)
    template: str = Field(default="",max_length=3000)
    version: int = 1
    adapter: Literal["transport","print","mortgage","accommodation"] | None = None
    prices: dict[str,str] | None = None

    @model_validator(mode='after')
    def validate_config(self):
        keys = {f.key for f in self.fields}
        labels = {f.label.strip().lower() for f in self.fields}
        if len(keys) != len(self.fields) or len(labels) != len(self.fields):
            raise ValueError("Field keys and labels must be unique")
        for field in self.fields:
            if field.when and (field.when.field not in keys or field.when.field == field.key):
                raise ValueError(f"Invalid condition for {field.label}")
            if field.type == 'select' and not field.options:
                raise ValueError(f"{field.label} needs selectable options")
            if field.minimum is not None and field.maximum is not None and field.minimum > field.maximum:
                raise ValueError(f"Invalid range for {field.label}")
        return self

class Citation(BaseModel):
    key: str
    raw: str
    quote: str
    source: str
    issue: str = ""
    origin: str = "provider"

class Finding(BaseModel):
    key: str
    raw: str
    source: str

class Extraction(BaseModel):
    facts: list[Finding] = Field(max_length=100)

class Clarification(BaseModel):
    text: str = Field(min_length=1,max_length=3000)

class Intake(BaseModel):
    org: str
    channel: str = Field(min_length=1,max_length=80)
    subject: str = Field(min_length=1,max_length=180)
    sender: str = Field(min_length=1,max_length=200)
    body: str = Field(max_length=40000)
    thread: str | None = Field(default=None,max_length=250)
    message_id: str | None = Field(default=None,max_length=250)
    in_reply_to: str | None = Field(default=None,max_length=250)

class Settings(BaseModel):
    mode: Mode
    model: str = Field(pattern=r'^[\w][\w.-]*(?::[\w.-]+)?$',max_length=100)

    @model_validator(mode='after')
    def local_models_only(self):
        if re_cloud(self.model):
            raise ValueError("Select an installed local model")
        return self

def re_cloud(model):
    return bool(re.search(r'(^|[:._-])cloud($|[:._-])', model.lower()))

class Correction(BaseModel):
    value: Value
    reason: str = Field(min_length=3,max_length=1000)
    revision: int

class Review(BaseModel):
    revision: int
    role: str
    comment: str = Field(default="",max_length=2000)
    decision: Literal['approve','reject','return'] = 'approve'

class TextEdit(BaseModel):
    text: str = Field(min_length=1,max_length=12000)
    revision: int

class DraftEdit(TextEdit):
    draft_id: str
    draft_version: int

class DraftReview(Review):
    draft_id: str
    draft_version: int

class ExportDestination(BaseModel):
    directory: str | None = Field(default=None,max_length=1000)
