"""
User Schemas
"""
from pydantic import BaseModel, EmailStr, field_validator
from datetime import datetime
from typing import Optional, List, Literal


# ============== Group Access Schemas ==============

class UserGroupAccessBase(BaseModel):
    """Basis-Schema für Gruppen-Zuordnung"""
    group_name: str


class UserGroupAccessCreate(UserGroupAccessBase):
    """Schema für Gruppen-Zuordnung erstellen"""
    pass


class UserGroupAccessRead(UserGroupAccessBase):
    """Schema für Gruppen-Zuordnung Response"""
    id: int

    class Config:
        from_attributes = True


# ============== Playbook Access Schemas ==============

class UserPlaybookAccessBase(BaseModel):
    """Basis-Schema für Playbook-Zuordnung"""
    playbook_name: str


class UserPlaybookAccessCreate(UserPlaybookAccessBase):
    """Schema für Playbook-Zuordnung erstellen"""
    pass


class UserPlaybookAccessRead(UserPlaybookAccessBase):
    """Schema für Playbook-Zuordnung Response"""
    id: int

    class Config:
        from_attributes = True


# ============== User Schemas ==============

class UserCreate(BaseModel):
    """Schema für User-Erstellung"""
    username: str
    password: str
    email: Optional[EmailStr] = None
    is_super_admin: bool = False

    @field_validator('username')
    @classmethod
    def username_must_be_valid(cls, v):
        if len(v) < 3:
            raise ValueError('Username muss mindestens 3 Zeichen haben')
        if len(v) > 50:
            raise ValueError('Username darf maximal 50 Zeichen haben')
        return v

    @field_validator('password')
    @classmethod
    def password_must_be_strong(cls, v):
        if len(v) < 8:
            raise ValueError('Passwort muss mindestens 8 Zeichen haben')
        return v


class UserUpdate(BaseModel):
    """Schema für User-Aktualisierung"""
    email: Optional[EmailStr] = None
    is_super_admin: Optional[bool] = None
    is_active: Optional[bool] = None


class UserResponse(BaseModel):
    """Schema für User-Response (kurz)"""
    id: int
    username: str
    email: Optional[str] = None
    is_admin: bool  # Legacy
    is_super_admin: bool
    is_active: bool
    netbox_user_id: Optional[int] = None  # NetBox User ID für Synchronisation
    theme: str = "blue"  # UI-Theme (blue, orange, green, purple, teal)
    created_at: datetime
    last_login: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserResponseWithAccess(UserResponse):
    """Schema für User-Response mit Berechtigungen"""
    group_access: List[UserGroupAccessRead] = []
    playbook_access: List[UserPlaybookAccessRead] = []
    accessible_groups: List[str] = []
    accessible_playbooks: List[str] = []

    class Config:
        from_attributes = True


class UserListResponse(BaseModel):
    """Schema für User-Liste Response"""
    items: List[UserResponse]
    total: int


# ============== Auth Schemas ==============

class UserLogin(BaseModel):
    """Schema für Login"""
    username: str
    password: str


class Token(BaseModel):
    """JWT Token Response"""
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Token Payload"""
    username: Optional[str] = None
    user_id: Optional[int] = None


class PasswordChangeRequest(BaseModel):
    """Schema für Passwort-Änderung"""
    current_password: str
    new_password: str
    confirm_password: str
    sync_to_netbox: bool = True  # Standardmäßig aktiviert

    @field_validator('new_password')
    @classmethod
    def password_must_be_strong(cls, v):
        if len(v) < 8:
            raise ValueError('Neues Passwort muss mindestens 8 Zeichen haben')
        return v

    @field_validator('confirm_password')
    @classmethod
    def passwords_must_match(cls, v, info):
        if 'new_password' in info.data and v != info.data['new_password']:
            raise ValueError('Passwörter stimmen nicht überein')
        return v


class PasswordResetRequest(BaseModel):
    """Schema für Passwort-Reset durch Admin"""
    new_password: str

    @field_validator('new_password')
    @classmethod
    def password_must_be_strong(cls, v):
        if len(v) < 8:
            raise ValueError('Neues Passwort muss mindestens 8 Zeichen haben')
        return v


# ============== Access Summary Schemas ==============

class UserAccessSummary(BaseModel):
    """Schema für Berechtigungsübersicht"""
    is_super_admin: bool
    is_active: bool
    accessible_groups: List[str]
    accessible_playbooks: List[str]
    can_manage_users: bool


# ============== Settings Schemas ==============

class AppSettingRead(BaseModel):
    """Schema für Settings Response"""
    key: str
    value: Optional[str] = None
    description: Optional[str] = None

    class Config:
        from_attributes = True


class AppSettingUpdate(BaseModel):
    """Schema für Settings Update"""
    value: Optional[str] = None


class DefaultAccessSettings(BaseModel):
    """Schema für Default-Zugriffs-Einstellungen"""
    default_groups: List[str] = []
    default_playbooks: List[str] = []


# ============== User Preferences Schemas ==============

# Verfuegbare Theme-Namen
ThemeName = Literal["blue", "orange", "green", "purple", "teal"]


class UserPreferencesUpdate(BaseModel):
    """Schema für User-Einstellungen Update"""
    theme: Optional[ThemeName] = None


class UserPreferencesResponse(BaseModel):
    """Schema für User-Einstellungen Response"""
    theme: str
