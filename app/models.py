from datetime import datetime
from sqlalchemy import Text, Integer, ForeignKey, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column, relationship
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class User(db.Model):
    __tablename__ = 'users'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    first_name: Mapped[str] = mapped_column(Text, nullable=True)
    last_name: Mapped[str] = mapped_column(Text, nullable=True)
    date_of_birth: Mapped[str] = mapped_column(Text, nullable=True)
    
    # Relationship
    properties: Mapped[list["Property"]] = relationship(
        "Property", back_populates="owner", cascade="all, delete-orphan"
    )
    
    def to_dict(self):
        return {
            'id': self.id,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'date_of_birth': self.date_of_birth,
        }


class Property(db.Model):
    __tablename__ = 'properties'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_id: Mapped[int] = mapped_column(
        Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP, nullable=False, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    property_type: Mapped[str] = mapped_column(Text, nullable=False)
    city: Mapped[str] = mapped_column(Text, nullable=False)
    rooms_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rooms_details: Mapped[str] = mapped_column(Text, nullable=True)
    
    # Relationship
    owner: Mapped["User"] = relationship("User", back_populates="properties")
    
    def to_dict(self, include_owner=True):
        data = {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'property_type': self.property_type,
            'city': self.city,
            'rooms_count': self.rooms_count,
            'rooms_details': self.rooms_details,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
        
        if include_owner and self.owner:
            data['owner'] = {
                'id': self.owner.id,
                'first_name': self.owner.first_name,
                'last_name': self.owner.last_name,
            }
        
        return data