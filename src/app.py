from flask import Flask, jsonify, request, send_from_directory
from datetime import datetime
import psycopg2
import os
import time
import pika
import json

app = Flask(__name__)

def get_db_connection():
    conn = psycopg2.connect(
        host=os.environ.get('DB_HOST', 'localhost'),
        port=os.environ.get('DB_PORT', '5432'),
        database=os.environ.get('DB_NAME', 'tododb'),
        user=os.environ.get('DB_USER', 'postgres'),
        password=os.environ.get('DB_PASSWORD', 'postgres')
    )
    return conn

def get_rabbitmq_connection():
    credentials = pika.PlainCredentials(
        os.environ.get('RABBITMQ_USER', 'guest'),
        os.environ.get('RABBITMQ_PASSWORD', 'guest')
    )
    parameters = pika.ConnectionParameters(
        host=os.environ.get('RABBITMQ_HOST', 'localhost'),
        port=int(os.environ.get('RABBITMQ_PORT', '5672')),
        credentials=credentials
    )
    return pika.BlockingConnection(parameters)

def publish_message(event_type, task_data):
    max_retries = 3
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            connection = get_rabbitmq_connection()
            channel = connection.channel()
            channel.queue_declare(queue='task_events', durable=True)
            
            message = {
                'event_type': event_type,
                'task': task_data,
                'timestamp': datetime.now().isoformat()
            }
            
            channel.basic_publish(
                exchange='',
                routing_key='task_events',
                body=json.dumps(message),
                properties=pika.BasicProperties(
                    delivery_mode=2,
                )
            )
            
            connection.close()
            print(f"Published message: {event_type} - {task_data}")
            break
        except Exception as e:
            retry_count += 1
            print(f"Failed to publish message (attempt {retry_count}/{max_retries}): {e}")
            if retry_count < max_retries:
                time.sleep(1)
            else:
                print("Failed to publish message after multiple attempts")

def init_db():
    max_retries = 5
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tasks (
                    id SERIAL PRIMARY KEY,
                    title VARCHAR(255) NOT NULL,
                    completed BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS task_statistics (
                    id SERIAL PRIMARY KEY,
                    date DATE DEFAULT CURRENT_DATE,
                    tasks_created INTEGER DEFAULT 0,
                    tasks_completed INTEGER DEFAULT 0,
                    tasks_deleted INTEGER DEFAULT 0,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(date)
                )
            ''')
            conn.commit()
            cursor.close()
            conn.close()
            print("Database initialized successfully")
            break
        except psycopg2.OperationalError as e:
            retry_count += 1
            print(f"Database connection failed (attempt {retry_count}/{max_retries}): {e}")
            if retry_count < max_retries:
                time.sleep(2)
            else:
                print("Failed to connect to database after multiple attempts")
                raise

@app.route('/')
def home():
    return send_from_directory('.', 'index.html')

@app.route('/api')
def api_info():
    return jsonify({
        'service': 'Simple Todo API',
        'version': '2.0',
        'endpoints': {
            'GET /api': 'API info',
            'GET /api/health': 'Health check',
            'GET /api/tasks': 'List all todo tasks',
            'POST /api/tasks': 'Create a todo task',
            'PUT /api/tasks/<id>': 'Update a todo task',
            'DELETE /api/tasks/<id>': 'Delete a todo task',
            'GET /api/analytics': 'Get task statistics'
        }
    })

@app.route('/api/health')
def health():
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/tasks', methods=['GET'])
def get_tasks():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id, title, completed, created_at, completed_at FROM tasks ORDER BY id ASC')
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    
    tasks = []
    for row in rows:
        tasks.append({
            'id': row[0],
            'title': row[1],
            'completed': row[2],
            'created_at': row[3].isoformat(),
            'completed_at': row[4].isoformat() if row[4] else None
        })
    
    return jsonify({
        'count': len(tasks),
        'tasks': tasks
    })

@app.route('/api/tasks', methods=['POST'])
def create_task():
    data = request.get_json()
    title = data.get('title', 'Untitled')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO tasks (title, completed) VALUES (%s, %s) RETURNING id, title, completed, created_at',
        (title, False)
    )
    row = cursor.fetchone()
    conn.commit()
    cursor.close()
    conn.close()
    
    task = {
        'id': row[0],
        'title': row[1],
        'completed': row[2],
        'created_at': row[3].isoformat()
    }
    
    publish_message('task_created', task)
    
    return jsonify(task), 201

@app.route('/api/tasks/<int:task_id>', methods=['PUT'])
def update_task(task_id):
    data = request.get_json()
    completed = data.get('completed')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if completed is not None:
        if completed:
            cursor.execute(
                'UPDATE tasks SET completed = %s, completed_at = CURRENT_TIMESTAMP WHERE id = %s RETURNING id, title, completed, created_at, completed_at',
                (True, task_id)
            )
        else:
            cursor.execute(
                'UPDATE tasks SET completed = %s, completed_at = NULL WHERE id = %s RETURNING id, title, completed, created_at, completed_at',
                (False, task_id)
            )
    
    row = cursor.fetchone()
    conn.commit()
    cursor.close()
    conn.close()
    
    if row:
        task = {
            'id': row[0],
            'title': row[1],
            'completed': row[2],
            'created_at': row[3].isoformat(),
            'completed_at': row[4].isoformat() if row[4] else None
        }
        
        publish_message('task_completed' if completed else 'task_uncompleted', task)
        
        return jsonify(task), 200
    else:
        return jsonify({'error': 'Task not found'}), 404

@app.route('/api/tasks/<int:task_id>', methods=['DELETE'])
def delete_task(task_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM tasks WHERE id = %s', (task_id,))
    conn.commit()
    cursor.close()
    conn.close()
    
    publish_message('task_deleted', {'id': task_id})
    
    return jsonify({'success': True}), 200

@app.route('/api/analytics', methods=['GET'])
def get_analytics():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT 
            date,
            tasks_created,
            tasks_completed,
            tasks_deleted
        FROM task_statistics
        ORDER BY date DESC
        LIMIT 7
    ''')
    stats_rows = cursor.fetchall()
    
    cursor.execute('SELECT COUNT(*) FROM tasks')
    total_tasks = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM tasks WHERE completed = true')
    completed_tasks = cursor.fetchone()[0]
    
    cursor.close()
    conn.close()
    
    daily_stats = []
    for row in stats_rows:
        daily_stats.append({
            'date': row[0].isoformat(),
            'created': row[1],
            'completed': row[2],
            'deleted': row[3]
        })
    
    return jsonify({
        'total_tasks': total_tasks,
        'completed_tasks': completed_tasks,
        'pending_tasks': total_tasks - completed_tasks,
        'daily_stats': daily_stats
    })

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000)
