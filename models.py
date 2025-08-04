from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone

db = SQLAlchemy()

class CaseQuery(db.Model):
    """Model to store case search queries"""
    __tablename__ = 'case_queries'
    
    id = db.Column(db.Integer, primary_key=True)
    case_type = db.Column(db.String(100), nullable=False)
    case_number = db.Column(db.String(50), nullable=False)
    filing_year = db.Column(db.String(10), nullable=False)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Relationship with case data
    case_data = db.relationship('CaseData', backref='query', lazy=True)
    
    def __repr__(self):
        return f'<CaseQuery {self.case_type}/{self.case_number}/{self.filing_year}>'

class CaseData(db.Model):
    """Model to store scraped case data"""
    __tablename__ = 'case_data'
    
    id = db.Column(db.Integer, primary_key=True)
    query_id = db.Column(db.Integer, db.ForeignKey('case_queries.id'), nullable=False)
    case_type = db.Column(db.String(100), nullable=False)
    case_number = db.Column(db.String(50), nullable=False)
    filing_year = db.Column(db.String(10), nullable=False)
    parties = db.Column(db.Text)  # JSON string of parties
    filing_date = db.Column(db.String(50))
    next_hearing_date = db.Column(db.String(50))
    orders_judgments = db.Column(db.Text)  # JSON string of orders/judgments
    raw_response = db.Column(db.Text)  # Raw HTML response
    status = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    def __repr__(self):
        return f'<CaseData {self.case_type}/{self.case_number}/{self.filing_year}>'