from __future__ import annotations

import datetime
from typing import Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("telegram_id"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    username: Mapped[Optional[str]] = mapped_column(Text)
    first_name: Mapped[Optional[str]] = mapped_column(Text)
    last_name: Mapped[Optional[str]] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )

    chat_members: Mapped[list[ChatMember]] = relationship(back_populates="user")
    messages: Mapped[list[Message]] = relationship(back_populates="user")
    message_stats: Mapped[list[MessageStat]] = relationship(back_populates="user")


class Chat(Base):
    __tablename__ = "chats"
    __table_args__ = (
        CheckConstraint(
            "chat_type IN ('private', 'group', 'supergroup', 'channel')"
        ),
        UniqueConstraint("telegram_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    title: Mapped[Optional[str]] = mapped_column(Text)
    chat_type: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )

    settings: Mapped[ChatSettings] = relationship(
        back_populates="chat", uselist=False, cascade="all, delete-orphan"
    )
    activity: Mapped[ChatActivity] = relationship(
        back_populates="chat", uselist=False, cascade="all, delete-orphan"
    )
    members: Mapped[list[ChatMember]] = relationship(back_populates="chat")
    messages: Mapped[list[Message]] = relationship(back_populates="chat")
    message_stats: Mapped[list[MessageStat]] = relationship(back_populates="chat")
    quotes: Mapped[list[Quote]] = relationship(back_populates="chat")


class ChatSettings(Base):
    __tablename__ = "chat_settings"

    chat_id: Mapped[int] = mapped_column(
        ForeignKey("chats.id", ondelete="CASCADE"), primary_key=True
    )
    silence_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )
    silence_threshold_minutes: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("300")
    )
    reminder_text: Mapped[str] = mapped_column(
        Text, nullable=False, server_default=text("'Че молчите?'")
    )
    reminder_cooldown_minutes: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("1440")
    )
    babel_probability_percent: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default=text("20"),
    )
    glupy_probability_percent: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default=text("3"),
    )
    glupy_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("true"),
    )
    glupy_order: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))
    glupy_cooldown_minutes: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("10")
    )
    glupy_max_length: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("200")
    )
    glupy_reply_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )
    stats_show_usernames: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )
    timezone: Mapped[str] = mapped_column(
        Text, nullable=False, server_default=text("'UTC'")
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )

    chat: Mapped[Chat] = relationship(back_populates="settings")


class ChatActivity(Base):
    __tablename__ = "chat_activity"

    chat_id: Mapped[int] = mapped_column(
        ForeignKey("chats.id", ondelete="CASCADE"), primary_key=True
    )
    last_message_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime(timezone=True)
    )
    last_reminder_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime(timezone=True)
    )
    last_message_id: Mapped[Optional[int]] = mapped_column(BigInteger)
    glupy_last_sent_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime(timezone=True)
    )

    chat: Mapped[Chat] = relationship(back_populates="activity")


class ChatMember(Base):
    __tablename__ = "chat_members"
    __table_args__ = (
        CheckConstraint("role IN ('member', 'administrator', 'creator')"),
        Index("idx_chat_members_user", "user_id"),
    )

    chat_id: Mapped[int] = mapped_column(
        ForeignKey("chats.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    role: Mapped[str] = mapped_column(
        Text, nullable=False, server_default=text("'member'")
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )
    joined_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime(timezone=True)
    )
    left_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime(timezone=True)
    )

    chat: Mapped[Chat] = relationship(back_populates="members")
    user: Mapped[User] = relationship(back_populates="chat_members")


class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (
        UniqueConstraint("chat_id", "telegram_message_id"),
        Index("idx_messages_chat_sent_at", "chat_id", "sent_at"),
        Index("idx_messages_user_sent_at", "user_id", "sent_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    telegram_message_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    chat_id: Mapped[int] = mapped_column(
        ForeignKey("chats.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    message_text: Mapped[Optional[str]] = mapped_column("text", Text)
    content_type: Mapped[str] = mapped_column(
        Text, nullable=False, server_default=text("'text'")
    )
    emoji_count: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    reaction_count: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    media_file_id: Mapped[Optional[str]] = mapped_column(Text)
    sent_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )

    chat: Mapped[Chat] = relationship(back_populates="messages")
    user: Mapped[Optional[User]] = relationship(back_populates="messages")
    quote: Mapped[Optional[Quote]] = relationship(back_populates="message", uselist=False)


class Quote(Base):
    __tablename__ = "quotes"
    __table_args__ = (
        UniqueConstraint("message_id"),
        Index("idx_quotes_chat_created_at", "chat_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    chat_id: Mapped[int] = mapped_column(
        ForeignKey("chats.id", ondelete="CASCADE"), nullable=False
    )
    message_id: Mapped[int] = mapped_column(
        ForeignKey("messages.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )

    chat: Mapped[Chat] = relationship(back_populates="quotes")
    message: Mapped[Message] = relationship(back_populates="quote")


class MessageStat(Base):
    __tablename__ = "message_stats"
    __table_args__ = (
        CheckConstraint("message_count >= 0"),
        CheckConstraint("character_count >= 0"),
        UniqueConstraint("chat_id", "user_id", "period_date"),
        Index("idx_message_stats_chat_period", "chat_id", "period_date"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    chat_id: Mapped[int] = mapped_column(
        ForeignKey("chats.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    period_date: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    message_count: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    character_count: Mapped[int] = mapped_column(
        BigInteger, nullable=False, server_default=text("0")
    )

    chat: Mapped[Chat] = relationship(back_populates="message_stats")
    user: Mapped[Optional[User]] = relationship(back_populates="message_stats")
