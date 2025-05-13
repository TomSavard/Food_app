from dataclasses import dataclass, field
from typing import List, Dict, Optional
import pandas as pd
import json
import uuid 

@dataclass
class Ingredient:
    name: str
    quantity: float = 0
    unit: str = ""
    notes: str = ""
    
    def to_dict(self):
        return {
            "name": self.name,
            "quantity": self.quantity,
            "unit": self.unit,
            "notes": self.notes
        }
    
    @classmethod
    def from_dict(cls, data):
        return cls(
            name=data.get("name", ""),
            quantity=data.get("quantity", 0),
            unit=data.get("unit", ""),
            notes=data.get("notes", "")
        )

@dataclass
class Recipe:
    name: str
    ingredients: List[Ingredient] = field(default_factory=list)
    instructions: List[str] = field(default_factory=list)
    prep_time: int = 0  # minutes
    cook_time: int = 0  # minutes
    servings: int = 1
    cuisine_type: str = ""
    tags: List[str] = field(default_factory=list)
    description: str = ""
    image_file_id: str = ""  # Google Drive file ID for recipe image
    recipe_id: str = field(default_factory=lambda: str(uuid.uuid4())) # Générer un ID unique
    
    def to_dict(self):
        return {
            "name": self.name,
            "ingredients": [i.to_dict() for i in self.ingredients],
            "instructions": self.instructions,
            "prep_time": self.prep_time,
            "cook_time": self.cook_time,
            "servings": self.servings,
            "cuisine_type": self.cuisine_type,
            "tags": self.tags,
            "description": self.description,
            "image_file_id": self.image_file_id
        }
    
    @classmethod
    def from_dict(cls, data):
        return cls(
            name=data.get("name", ""),
            ingredients=[Ingredient.from_dict(i) for i in data.get("ingredients", [])],
            instructions=data.get("instructions", []),
            prep_time=data.get("prep_time", 0),
            cook_time=data.get("cook_time", 0),
            servings=data.get("servings", 1),
            cuisine_type=data.get("cuisine_type", ""),
            tags=data.get("tags", []),
            description=data.get("description", ""),
            image_file_id=data.get("image_file_id", "")
        )
    
    def to_json(self):
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)
    
    @classmethod
    def from_json(cls, json_str):
        return cls.from_dict(json.loads(json_str))
    
    def to_dataframe_row(self):
        """Convert recipe to a pandas DataFrame row format"""
        return {
            "Recipe Name": self.name,
            "Description": self.description,
            "Preparation Time (min)": self.prep_time,
            "Cooking Time (min)": self.cook_time,
            "Total Time (min)": self.prep_time + self.cook_time,
            "Servings": self.servings,
            "Cuisine Type": self.cuisine_type,
            "Tags": ", ".join(self.tags),
            "Ingredient Count": len(self.ingredients),
            "Has Image": bool(self.image_file_id)
        }