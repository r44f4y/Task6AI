import os
from datetime import datetime,timezone
from pathlib import Path

from sqlalchemy import JSON, Boolean, ForeignKey, Integer, LargeBinary, String, UniqueConstraint, create_engine,event,select,text
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from backend.schema import Settings,Workflow
from synthetic_data.catalog import ROOT,get_workflows

def now():
    return datetime.now(timezone.utc).isoformat()

class Base(DeclarativeBase):
    pass

class WorkflowVersion(Base):
    __tablename__='workflow_versions'
    org: Mapped[str]=mapped_column(String,primary_key=True)
    version: Mapped[int]=mapped_column(Integer,primary_key=True)
    config: Mapped[dict]=mapped_column(JSON)

class Case(Base):
    __tablename__='requests'
    id: Mapped[str]=mapped_column(String,primary_key=True)
    org: Mapped[str]=mapped_column(String,index=True)
    thread: Mapped[str]=mapped_column(String)
    sender: Mapped[str]=mapped_column(String)
    subject: Mapped[str]=mapped_column(String)
    channel: Mapped[str]=mapped_column(String)
    version: Mapped[int]=mapped_column(Integer)
    created: Mapped[str]=mapped_column(String)
    updated: Mapped[str]=mapped_column(String)
    unread: Mapped[bool]=mapped_column(Boolean,default=True)
    fixture: Mapped[str | None]=mapped_column(String,nullable=True,index=True,unique=True)
    state: Mapped[dict]=mapped_column(JSON)
    __table_args__=(UniqueConstraint('org','thread'),)

class Message(Base):
    __tablename__='messages'
    id: Mapped[str]=mapped_column(String,primary_key=True)
    external_id: Mapped[str]=mapped_column(String)
    org: Mapped[str]=mapped_column(String,index=True)
    case_id: Mapped[str]=mapped_column(ForeignKey("requests.id",ondelete='CASCADE'),index=True)
    created: Mapped[str]=mapped_column(String)
    sender: Mapped[str]=mapped_column(String)
    body: Mapped[str]=mapped_column(String)
    direction: Mapped[str]=mapped_column(String)
    in_reply_to: Mapped[str | None]=mapped_column(String)
    historical: Mapped[bool]=mapped_column(Boolean,default=False)
    __table_args__=(UniqueConstraint('org','external_id'),)

class DocumentSource(Base):
    __tablename__='documents'
    id: Mapped[str]=mapped_column(String,primary_key=True)
    org: Mapped[str]=mapped_column(String,index=True)
    case_id: Mapped[str | None]=mapped_column(ForeignKey('requests.id',ondelete='CASCADE'),index=True)
    filename: Mapped[str]=mapped_column(String)
    kind: Mapped[str]=mapped_column(String)
    created: Mapped[str]=mapped_column(String)
    content: Mapped[bytes]=mapped_column(LargeBinary)
    pages: Mapped[list]=mapped_column(JSON)
    warning: Mapped[str | None]=mapped_column(String)
    version: Mapped[int]=mapped_column(Integer,default=1)

class Preference(Base):
    __tablename__='preferences'
    id: Mapped[int]=mapped_column(Integer,primary_key=True)
    data: Mapped[dict]=mapped_column(JSON)

def connect(path=None):
    target=Path(path or os.getenv('RELAY_DB',ROOT/'.local'/'relay.sqlite')).resolve()
    target.parent.mkdir(parents=True,exist_ok=True)
    engine=create_engine(f"sqlite:///{target}",connect_args={'check_same_thread':False,'timeout':20})
    @event.listens_for(engine,'connect')
    def configure(dbapi, _):
        dbapi.execute("PRAGMA foreign_keys=ON")
        dbapi.execute("PRAGMA journal_mode=WAL")
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        write_lock(s)
        for key,cfg in get_workflows().items():
            if not s.get(WorkflowVersion,(key,1)):
                config=Workflow.model_validate(cfg).model_dump()
                s.add(WorkflowVersion(org=key,version=1,config=config))
        if not s.get(Preference,1):
            settings=Settings(mode=os.getenv('APP_MODE','local_ai'),model=os.getenv('OLLAMA_MODEL','qwen3:4b'))
            s.add(Preference(id=1,data=settings.model_dump()))
        s.commit()
    return engine

def write_lock(session):
    session.execute(text('BEGIN IMMEDIATE'))

def latest(session,org):
    return session.scalar(select(WorkflowVersion).where(WorkflowVersion.org==org).order_by(WorkflowVersion.version.desc()))
