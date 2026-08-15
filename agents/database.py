import sqlite3
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from loguru import logger


class Database:
    def __init__(self, db_path: str = 'autosre.db'):
        self.db_path = db_path
        self._init_database()
        
    def _init_database(self):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS incidents (
                    id TEXT PRIMARY KEY,
                    timestamp TEXT,
                    status TEXT,
                    total_alerts INTEGER,
                    alert_groups INTEGER,
                    top_causes TEXT,
                    reports_generated INTEGER,
                    duration TEXT,
                    severity TEXT
                )
            ''')
            
            conn.commit()
            conn.close()
            logger.info(f'Database initialized: {self.db_path}')
        except Exception as e:
            logger.error(f'Database init failed: {str(e)}')
    
    def save_incident(self, incident_result):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            summary = incident_result.get('summary', {})
            incident_id = incident_result.get('incident_id', '')
            
            cursor.execute('''
                INSERT OR REPLACE INTO incidents 
                (id, timestamp, status, total_alerts, alert_groups, 
                 top_causes, reports_generated, duration, severity)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                incident_id,
                datetime.now().isoformat(),
                incident_result.get('status', 'unknown'),
                summary.get('total_alerts', 0),
                summary.get('alert_groups', 0),
                json.dumps(summary.get('top_causes', []), ensure_ascii=False),
                summary.get('reports_generated', 0),
                '0 minutes',
                'warning'
            ))
            
            conn.commit()
            conn.close()
            logger.info(f'Incident saved: {incident_id}')
            return True
        except Exception as e:
            logger.error(f'Save incident failed: {str(e)}')
            return False
    
    def get_recent_incidents(self, limit=10):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM incidents ORDER BY timestamp DESC LIMIT ?', (limit,))
            
            columns = [description[0] for description in cursor.description]
            incidents = []
            
            for row in cursor.fetchall():
                incident = dict(zip(columns, row))
                try:
                    incident['top_causes'] = json.loads(incident.get('top_causes', '[]'))
                except:
                    incident['top_causes'] = []
                incidents.append(incident)
            
            conn.close()
            return incidents
        except Exception as e:
            logger.error(f'Get incidents failed: {str(e)}')
            return []
    
    def get_incident_stats(self):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT COUNT(*) FROM incidents')
            total_incidents = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM incidents WHERE status = ?', ('completed',))
            completed = cursor.fetchone()[0]
            
            cursor.execute('SELECT COALESCE(SUM(total_alerts), 0) FROM incidents')
            total_alerts = cursor.fetchone()[0]
            
            conn.close()
            
            return {
                'total_incidents': total_incidents,
                'completed_incidents': completed,
                'total_alerts': total_alerts,
                'success_rate': completed / total_incidents if total_incidents > 0 else 0
            }
        except Exception as e:
            logger.error(f'Get stats failed: {str(e)}')
            return {
                'total_incidents': 0,
                'completed_incidents': 0,
                'total_alerts': 0,
                'success_rate': 0
            }
