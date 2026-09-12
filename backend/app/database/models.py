from datetime import datetime
from enum import Enum
from uuid import UUID, uuid4
from sqlalchemy import JSON, TIMESTAMP, Boolean, Integer, String, Enum as SqlEnum, ForeignKey, Uuid, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

class Base(DeclarativeBase):
    pass

class RoleEnum(str, Enum):
    ADMIN = "admin"
    USER = "user"

class ProgrammingLanguageEnum(str, Enum):
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    JAVA = "java"
    CSHARP = "csharp"
    RUBY = "ruby"
    GO = "go"
    PHP = "php"
    CPLUSPLUS = "cplusplus"
    SWIFT = "swift"
    KOTLIN = "kotlin"

class CandidateLevelEnum(str, Enum):
    INTERN = "intern"
    FRESHER = "fresher"
    JUNIOR = "junior"
    MID = "mid"
    SENIOR = "senior"

class PersonalityTypeEnum(str, Enum):
    STRICT = "strict"
    WARM = "warm"
    ENGINEERING = "engineering"
    ACADEMIC = "academic"
    SARCASM = "sarcasm"
    COACHING = "coaching"

class CorrectionModeEnum(str, Enum):
    STRICT = "strict"
    GUIDED = "guided"

class StageEnum(str, Enum):
    ICE_BREAKER = "ice_breaker"
    TECHNICAL = "technical"
    CODING = "coding"
    BEHAVIORAL = "behavioral"
    WRAP_UP = "wrap_up"

class StatusEnum(str, Enum):
    ACTIVE = "active"
    FINISHED = "finished"

class SenderEnum(str, Enum):
    INTERVIEWER = "interviewer"
    CANDIDATE = "candidate"

class User(Base):
    __tablename__ = "users"
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, index=True, default = uuid4)
    email: Mapped[str] = mapped_column(String, unique=True, index =True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)
    role: Mapped[RoleEnum] = mapped_column(SqlEnum(RoleEnum), nullable=False, default = RoleEnum.USER)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())

class Interview(Base):
    __tablename__ = "interviews"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, index=True, default = uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    programming_language: Mapped[ProgrammingLanguageEnum] = mapped_column(SqlEnum(ProgrammingLanguageEnum), nullable=False)
    candidate_level: Mapped[CandidateLevelEnum] = mapped_column(SqlEnum(CandidateLevelEnum), nullable=False)
    personality_type: Mapped[PersonalityTypeEnum] = mapped_column(SqlEnum(PersonalityTypeEnum), nullable=False)
    correction_mode: Mapped[CorrectionModeEnum] = mapped_column(SqlEnum(CorrectionModeEnum), nullable=False)
    resume_text: Mapped[str | None] = mapped_column(String, nullable=True)
    jd_text: Mapped[str | None] = mapped_column(String, nullable=True)

    stage: Mapped[StageEnum] = mapped_column(SqlEnum(StageEnum), nullable=False, default=StageEnum.ICE_BREAKER)
    current_topic: Mapped[str] = mapped_column(String, nullable=True, default="")
    focus_topics: Mapped[list[str]|None] = mapped_column(JSON, nullable=True, default=list)
    covered_topics: Mapped[list[str]|None] = mapped_column(JSON, nullable=True, default=list)
    probe_depth: Mapped[int] = mapped_column(Integer, default=0)
    consecutive_wrongs: Mapped[int] = mapped_column(Integer, default=0)
    question_asked_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    next_question: Mapped[str] = mapped_column(String, nullable=True, default="")
    status: Mapped[StatusEnum] = mapped_column(SqlEnum(StatusEnum), nullable=False, default=StatusEnum.ACTIVE)

    report: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    finished_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())

    messages: Mapped[list["Messages"]] = relationship(back_populates="interview", cascade="all, delete-orphan")

class Messages(Base):
    __tablename__ = "messages"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, index=True, default=uuid4)
    interview_id: Mapped[UUID] = mapped_column(ForeignKey("interviews.id", ondelete="CASCADE"), nullable=False)
    sender: Mapped[SenderEnum] = mapped_column(SqlEnum(SenderEnum), nullable=False)
    content: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())

    interview: Mapped["Interview"] = relationship(back_populates="messages")

class References(Base):
    __tablename__ = "references"
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    programming_language: Mapped[ProgrammingLanguageEnum | None] = mapped_column(SqlEnum(ProgrammingLanguageEnum), nullable=True)  # NULL = language-neutral (redis, mysql…)
    topic: Mapped[str] = mapped_column(String, nullable=False, index=True)
    sub_topic: Mapped[str | None] = mapped_column(String, nullable=True)
    question: Mapped[str] = mapped_column(String, nullable=False)
    reference_answer: Mapped[str] = mapped_column(String, nullable=False)
    key_points: Mapped[list | None] = mapped_column(JSON, nullable=True)
    difficulty: Mapped[int] = mapped_column(Integer, nullable=False, default=2)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())