from flask import Flask, request, render_template, jsonify
import requests
import sqlite3
import traceback

app = Flask(__name__)

# SQLite Database setup
DATABASE = 'assignments.db'

# Azure Logic App URLs
LOGIC_APP_ADD_URL = "https://prod-27.northcentralus.logic.azure.com:443/workflows/97b54b92d2c74cac97dd5f0952f6702f/triggers/When_a_HTTP_request_is_received/paths/invoke?api-version=2016-10-01&sp=%2Ftriggers%2FWhen_a_HTTP_request_is_received%2Frun&sv=1.0&sig=SiPX4ZGTsB13TaqWheYN12kxnlY8YKKki5IYJO8mvnI"
LOGIC_APP_DELETE_URL = "https://prod-27.northcentralus.logic.azure.com:443/workflows/delete-url-placeholder"

# Helper function to interact with SQLite database
def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

# Initialize the database
def init_db():
    with get_db() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS assignments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_name TEXT NOT NULL,
                due_date TEXT NOT NULL
            )
        ''')

init_db()

@app.route("/", methods=["GET"])
def index():
    # Fetch all assignments to display in the frontend
    with get_db() as conn:
        assignments = conn.execute("SELECT * FROM assignments ORDER BY due_date ASC").fetchall()
    return render_template("index.html", assignments=assignments)

@app.route("/add_assignment", methods=["POST"])
def add_assignment():
    try:
        file_name = request.form.get("file_name")
        due_date = request.form.get("due_date")

        if not file_name or not due_date:
            return jsonify({"error": "Both file_name and due_date are required."}), 400

        # Insert into the database
        with get_db() as conn:
            conn.execute("INSERT INTO assignments (file_name, due_date) VALUES (?, ?)", (file_name, due_date))

        # Send data to Azure Logic App
        data = {"file_name": file_name, "due_date": due_date}
        response = requests.post(LOGIC_APP_ADD_URL, json=data)

        if response.status_code != 200:
            return jsonify({"error": f"Failed to send data: {response.text}"}), response.status_code

        return jsonify({"message": "Assignment added and sent to Azure Logic App successfully!"})
    except Exception as e:
        error_message = f"An error occurred: {str(e)}\n{traceback.format_exc()}"
        print(error_message)
        return jsonify({"error": error_message}), 500

@app.route("/delete_assignment", methods=["POST"])
def delete_assignment():
    try:
        file_name = request.form.get("file_name")
        print(f"Received file_name for deletion: '{file_name}'")  # Debug log

        if not file_name:
            return jsonify({"error": "file_name is required to delete an assignment."}), 400

        # Normalize the file_name
        file_name = file_name.strip()

        # Remove from the database
        with get_db() as conn:
            cursor = conn.execute("DELETE FROM assignments WHERE file_name = ?", (file_name,))
            print(f"Rows affected: {cursor.rowcount}")  # Log affected rows
            if cursor.rowcount == 0:
                return jsonify({"error": f"No assignment found with the name '{file_name}'."}), 404

        # Notify Azure Logic App about the deletion
        response = requests.post(LOGIC_APP_DELETE_URL, json={"file_name": file_name})
        print(f"Logic App response: {response.status_code}, {response.text}")  # Log Azure response

        if response.status_code != 200:
            return jsonify({"error": f"Failed to notify Azure Logic App: {response.text}"}), response.status_code

        return jsonify({"message": f"Assignment '{file_name}' deleted successfully!"})

    except Exception as e:
        error_message = f"An error occurred: {str(e)}\n{traceback.format_exc()}"
        print(error_message)
        return jsonify({"error": error_message}), 500

@app.route("/get_assignments", methods=["GET"])
def get_assignments():
    try:
        # Fetch all assignments from the database, sorted by due_date in descending order
        with get_db() as conn:
            assignments = conn.execute(
                "SELECT * FROM assignments ORDER BY due_date ASC"
            ).fetchall()
        return jsonify([dict(assignment) for assignment in assignments])
    except Exception as e:
        error_message = f"An error occurred: {str(e)}\n{traceback.format_exc()}"
        print(error_message)
        return jsonify({"error": error_message}), 500

if __name__ == "__main__":
    app.run(debug=True)
