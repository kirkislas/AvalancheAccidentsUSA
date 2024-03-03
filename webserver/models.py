from sqlalchemy import Column, Integer, String, Float
from database import Base


class Accident(Base):
    __tablename__ = "accidents_silver"

    id = Column(Integer, primary_key=True, index=True)
    season = Column(String(50))  
    date = Column(String(25))  
    state = Column(String(50))  
    location = Column(String)  
    description = Column(String)  
    fatalities = Column(Integer)  
    latitude = Column(Float)
    longitude = Column(Float)
    
    def to_dict(self):
    # Serialize the model instance to a dictionary
    	return {
        	column.name: getattr(self, column.name) for column in self.__table__.columns
    }