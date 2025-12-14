from flask import Flask, jsonify, request, send_from_directory
from datetime import datetime
import psycopg2
import os
import time

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
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
        'version': '1.0',
        'endpoints': {
            'GET /api': 'API info',
            'GET /api/health': 'Health check',
            'GET /api/tasks': 'List all todo tasks',
            'POST /api/tasks': 'Create a todo task',
            'DELETE /api/tasks/<id>': 'Delete a todo task'
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
    cursor.execute('SELECT id, title, completed, created_at FROM tasks ORDER BY id ASC')
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    
    tasks = []
    for row in rows:
        tasks.append({
            'id': row[0],
            'title': row[1],
            'completed': row[2],
            'created_at': row[3].isoformat()
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
    
    return jsonify(task), 201

@app.route('/api/tasks/<int:task_id>', methods=['DELETE'])
def delete_task(task_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM tasks WHERE id = %s', (task_id,))
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({'success': True}), 200

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000)
