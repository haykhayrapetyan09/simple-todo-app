import pika
import json
import os
import time
import psycopg2
from datetime import date

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

def update_statistics(event_type):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    today = date.today()
    
    cursor.execute('''
        INSERT INTO task_statistics (date, tasks_created, tasks_completed, tasks_deleted, last_updated)
        VALUES (%s, 0, 0, 0, CURRENT_TIMESTAMP)
        ON CONFLICT (date) DO NOTHING
    ''', (today,))
    
    if event_type == 'task_created':
        cursor.execute('''
            UPDATE task_statistics 
            SET tasks_created = tasks_created + 1, last_updated = CURRENT_TIMESTAMP
            WHERE date = %s
        ''', (today,))
    elif event_type == 'task_completed':
        cursor.execute('''
            UPDATE task_statistics 
            SET tasks_completed = tasks_completed + 1, last_updated = CURRENT_TIMESTAMP
            WHERE date = %s
        ''', (today,))
    elif event_type == 'task_deleted':
        cursor.execute('''
            UPDATE task_statistics 
            SET tasks_deleted = tasks_deleted + 1, last_updated = CURRENT_TIMESTAMP
            WHERE date = %s
        ''', (today,))
    
    conn.commit()
    cursor.close()
    conn.close()

def callback(ch, method, properties, body):
    try:
        message = json.loads(body)
        event_type = message.get('event_type')
        task = message.get('task')
        timestamp = message.get('timestamp')
        
        print(f"[{timestamp}] Received event: {event_type}")
        print(f"Task data: {json.dumps(task, indent=2)}")
        
        if event_type == 'task_created':
            print(f"New task created: '{task.get('title')}' (ID: {task.get('id')})")
        elif event_type == 'task_completed':
            print(f"Task completed: '{task.get('title')}' (ID: {task.get('id')})")
        elif event_type == 'task_uncompleted':
            print(f"Task uncompleted: '{task.get('title')}' (ID: {task.get('id')})")
        elif event_type == 'task_deleted':
            print(f"Task deleted: ID {task.get('id')}")
        
        update_statistics(event_type)
        print("Statistics updated successfully")
        print("-" * 50)
        
        ch.basic_ack(delivery_tag=method.delivery_tag)
    except Exception as e:
        print(f"Error processing message: {e}")
        ch.basic_nack(delivery_tag=method.delivery_tag)

def main():
    max_retries = 10
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            print("Connecting to RabbitMQ...")
            connection = get_rabbitmq_connection()
            channel = connection.channel()
            
            channel.queue_declare(queue='task_events', durable=True)
            
            channel.basic_qos(prefetch_count=1)
            channel.basic_consume(queue='task_events', on_message_callback=callback)
            
            print("Consumer started. Waiting for messages...")
            channel.start_consuming()
        except KeyboardInterrupt:
            print("Consumer stopped by user")
            break
        except Exception as e:
            retry_count += 1
            print(f"Connection failed (attempt {retry_count}/{max_retries}): {e}")
            if retry_count < max_retries:
                print("Retrying in 5 seconds...")
                time.sleep(5)
            else:
                print("Failed to connect after multiple attempts")
                raise

if __name__ == '__main__':
    main()
