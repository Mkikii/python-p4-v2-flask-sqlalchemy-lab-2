from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import MetaData
from sqlalchemy.ext.associationproxy import association_proxy

metadata = MetaData(naming_convention={
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
})

db = SQLAlchemy(metadata=metadata)

class SimpleSerializerMixin:
    def to_dict(self, rules=(), _visited=None):
        if _visited is None:
            _visited = set()
        
        # Prevent infinite recursion
        obj_id = id(self)
        if obj_id in _visited:
            return f"<{self.__class__.__name__} {getattr(self, 'id', '')}>"
        _visited.add(obj_id)
        
        result = {}
        
        # Add column values
        for column in self.__table__.columns:
            result[column.name] = getattr(self, column.name)
        
        # Convert rules to tuple if it's a list
        if isinstance(rules, list):
            rules = tuple(rules)
        
        # Combine instance rules with passed rules
        instance_rules = getattr(self, 'serialize_rules', ())
        all_rules = tuple(set(instance_rules + rules))
        
        # Add relationship values with recursion prevention
        for relationship in self.__mapper__.relationships:
            relationship_name = relationship.key
            
            # Check if this relationship should be excluded
            if f"-{relationship_name}" in all_rules:
                continue
                
            related_obj = getattr(self, relationship_name)
            
            # Handle nested rules (e.g., '-customer.reviews')
            nested_rules = []
            for rule in all_rules:
                if rule.startswith(f"-{relationship_name}."):
                    nested_rules.append(rule[len(relationship_name) + 2:])  # +2 for the . and -
            
            if related_obj is None:
                result[relationship_name] = None
            elif hasattr(related_obj, '__iter__'):
                # Handle to-many relationships
                result[relationship_name] = [
                    item.to_dict(nested_rules, _visited.copy()) if hasattr(item, 'to_dict') else item 
                    for item in related_obj
                ]
            else:
                # Handle to-one relationships
                result[relationship_name] = (
                    related_obj.to_dict(nested_rules, _visited.copy()) 
                    if hasattr(related_obj, 'to_dict') 
                    else related_obj
                )
        
        return result

class Customer(db.Model, SimpleSerializerMixin):
    __tablename__ = 'customers'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)

    reviews = db.relationship('Review', back_populates='customer')
    items = association_proxy('reviews', 'item')

    serialize_rules = ('-reviews.customer',)

    def __repr__(self):
        return f'<Customer {self.id}, {self.name}>'

class Item(db.Model, SimpleSerializerMixin):
    __tablename__ = 'items'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    price = db.Column(db.Float)

    reviews = db.relationship('Review', back_populates='item')

    serialize_rules = ('-reviews.item',)

    def __repr__(self):
        return f'<Item {self.id}, {self.name}, {self.price}>'

class Review(db.Model, SimpleSerializerMixin):
    __tablename__ = 'reviews'

    id = db.Column(db.Integer, primary_key=True)
    comment = db.Column(db.String)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'))
    item_id = db.Column(db.Integer, db.ForeignKey('items.id'))

    customer = db.relationship('Customer', back_populates='reviews')
    item = db.relationship('Item', back_populates='reviews')

    serialize_rules = ('-customer.reviews', '-item.reviews')

    def __repr__(self):
        return f'<Review {self.id}, {self.comment}>'