from typing import Any, Dict, Optional, Union

from sqlalchemy.orm import Session

from app.core.security import get_password_hash, verify_password
from app.crud.base import ModelBase
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate


class UserModel(ModelBase[User, UserCreate, UserUpdate]):
    """
    Class that wraps the User model.
    """

    def get_by_username(self, db: Session, *, user_name: str) -> Optional[User]:
        """
        Get a user by username from the database.
        """
        return db.query(User).filter(User.user_name == user_name).first()

    def create(self, db: Session, *, obj_in: UserCreate) -> User:
        """
        Create a new user object.
        """
        db_obj = User(
            user_name=obj_in.user_name,
            hashed_password=get_password_hash(obj_in.password),
            is_superuser=obj_in.is_superuser,
            is_active=obj_in.is_active,
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(
        self, db: Session, *, db_obj: User, obj_in: Union[UserUpdate, Dict[str, Any]]
    ) -> User:
        """
        Update a user.
        """
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.dict(exclude_unset=True)
        if update_data["password"]:
            hashed_password = get_password_hash(update_data["password"])
            del update_data["password"]
            update_data["hashed_password"] = hashed_password
        return super().update(db, db_obj=db_obj, obj_in=update_data)

    def authenticate(
        self, db: Session, *, user_name: str, password: str
    ) -> Optional[User]:
        """
        Determine if a user exists by the user name and checking the password.
        """
        user = self.get_by_username(db, user_name=user_name)
        if not user:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user

    def is_active(self, user: User) -> bool:
        """
        Courtesy function to see if user is active.
        """
        return user.is_active

    def is_superuser(self, user: User) -> bool:
        """
        Courtesy function to check if a user is a superuser.
        """
        return user.is_superuser


user = UserModel(User)
