import sqlite3
from flask import Flask, request, jsonify, g, render_template
import openai
from twilio.rest import Client
import json

openai.api_key = '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'
twilio_client = Client('AC652aeef1d32f9cf28315b2558c34aa31', 'fe39d68cac19aae0b3f438ed22fa6670')
DATABASE = r'C:\Users\sikan\OneDrive\Desktop\database\test.db'


app = Flask(__name__)

def read_txt_file(filename):
    with open(filename, 'r') as file:
        return file.read()


def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
    return db

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/ongoing-chats')
def chats():
    return render_template('chats.html')


@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

@app.route('/tasks', methods=['POST', 'GET'])
def manage_tasks():
    db = get_db()
    cursor = db.cursor()

    if request.method == 'POST':
        data = request.get_json()
        cursor.execute('INSERT INTO employees (name, phone_number, leaves, salary, designation) VALUES (?, ?, ?, ?, ?)',
                       (data['name'], data['phone_number'], data['leaves'], data['salary'], data['designation']))
        db.commit()
        return jsonify(cursor.lastrowid)

    cursor.execute('SELECT * FROM employees')
    tasks = cursor.fetchall()
    return jsonify(tasks)

@app.route('/tasks/<int:id>', methods=['PUT', 'DELETE'])
def update_delete_task(id):
    db = get_db()
    cursor = db.cursor()

    if request.method == 'PUT':
        data = request.get_json()
        cursor.execute('UPDATE employees SET name = ?, phone_number = ?, leaves = ?, salary = ?, designation = ? WHERE id = ?',
                       (data['name'], data['phone_number'], data['leaves'], data['salary'], data['designation'], id))
        db.commit()
        return jsonify(id)

    if request.method == 'DELETE':
        cursor.execute('DELETE FROM employees WHERE id = ?', (id,))
        db.commit()
        return jsonify(id)

# Set up route to receive WhatsApp messages
@app.route('/sms', methods=['POST'])

def sms_reply():
    # Get the message body and sender's phone number
    message_body = request.form['Body']
    sender = request.form['From']

    str_sender = "0" + str(sender[-10:])
    print(str_sender)

    db = get_db()
    cursor = db.cursor()

    # Query database for user data based on phone number
    cursor.execute(f"SELECT * FROM employees WHERE phone_number = '{str_sender}';")

    user_data = cursor.fetchone()
    print(user_data)
    print(message_body)

 
    if user_data is None:
        response_text = "Sorry, I couldn't find your information in the database. Please try again."
    else:

        # Re-query the database to get updated user data
        cursor.execute(f"SELECT * FROM employees WHERE phone_number = '{str_sender}';")
        user_data = cursor.fetchone()


        # Convert user data to JSON format
        user_json = {
            "id": user_data[0], 
            "name": user_data[1], 
            "phone_number": user_data[2],
            "leaves": user_data[3],
            "salary": user_data[4]
        }

        policies = read_txt_file("./data/data.txt")
        instructions = read_txt_file("./data/instructions.txt")

        # Construct conversation history including user data
        conversation = [
            {"role": "system", "content": f"{instructions}.As a HR Manager, you provide guidance on company policies, benefits, and HR-related topics. You maintain confidentiality, respect privacy, and know when to escalate concerns to a human HR manager. You're here to assist a specific employee with their queries. These are the company policies: {policies}"},
            {"role": "user", "content": f"{message_body}"},
            {"role": "user", "content": json.dumps(user_json)}
        ]

        # Use OpenAI API to generate response based on message and user data
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=conversation
        )

        # Extract the generated response from the OpenAI API
        response_text = response['choices'][0]['message']['content']
        print(response_text)


    # Send response back through Twilio
    twilio_client.messages.create(
        body=response_text,
        from_='whatsapp:+14155238886',
        to=sender
    )

    return 'OK', 200


if __name__ == '__main__':
    with app.app_context():
        db = get_db()
        db.execute("CREATE TABLE IF NOT EXISTS tasks (id INTEGER PRIMARY KEY, title TEXT, description TEXT);")
    app.run(debug=True)
