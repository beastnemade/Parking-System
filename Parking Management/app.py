from flask import Flask, render_template, request, redirect, url_for, session
from datetime import datetime
import random
import string

app = Flask(__name__)
app.secret_key = "parking"

users = {
    "admin": "admin-log",
    "gatekeeper": "gate-log"
}

storeys = []
vehicles = {}

def generate_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))

def calculate_charges(parking_time, vehicle_type):
    exit_time = datetime.now()
    parking_time = datetime.strptime(parking_time, "%Y-%m-%d %H:%M:%S")
    duration = (exit_time - parking_time).total_seconds() / 60 

    if vehicle_type == "2":  
        if duration <= 30:
            return 50
        elif 30 < duration <= 60:
            return 60
        else:
            return 80 + ((duration - 60) // 60) * 80
    elif vehicle_type == "4": 
        if duration <= 30:
            return 70
        elif 30 < duration <= 60:
            return 90
        else:
            return 120 + ((duration - 60) // 60) * 120

@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if username in users and users[username] == password:
            session["user"] = username
            session["role"] = username  
            return redirect(url_for("home"))
        return "Invalid credentials. Please try again."
    return render_template("index.html")

@app.route("/logout")
def logout():
    session.pop("user", None)
    session.pop("role", None)
    return redirect(url_for("login"))

@app.route("/home")
def home():
    if "user" not in session:
        return redirect(url_for("login"))
    
    user_role = session.get("role")
    
    available_slots = 0
    filled_slots = 0
    for storey in storeys:
        for row in storey["slots"]:
            for slot in row:
                if slot is None:
                    available_slots += 1
                else:
                    filled_slots += 1

    return render_template("home.html", user_role=user_role, available_slots=available_slots, filled_slots=filled_slots)

@app.route("/add_storey", methods=["GET", "POST"])
def add_storey():
    if session.get("role") != "admin":
        return redirect(url_for("login"))
    if request.method == "POST":
        storey_id = len(storeys) + 1
        rows = int(request.form.get("rows"))
        columns = int(request.form.get("columns"))
        storeys.append({"id": storey_id, "rows": rows, "columns": columns, "slots": [[None] * columns for _ in range(rows)]})
        return redirect(url_for("add_storey"))
    return render_template("add_storey.html", storeys=storeys)

@app.route("/add_vehicle", methods=["GET", "POST"])
def add_vehicle():
    if session.get("user") != "gatekeeper":
        return redirect(url_for("login"))
    
    vehicle_code = None
    message = ""  

    if request.method == "POST":
        vehicle_number = request.form.get("vehicle_number")
        vehicle_type = request.form.get("vehicle_type")
        parking_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        for vehicle in vehicles.values():
            if vehicle["number"] == vehicle_number:
                message = "This vehicle is already parked."
                return render_template("add_vehicle.html", vehicle_code=None, message=message)

        vehicle_code = generate_code()  

        assigned = False 

        for storey in storeys:
            if (vehicle_type == "2" and storey["id"] % 2 == 0) or (vehicle_type == "4" and storey["id"] % 2 != 0):
                # Try to assign the vehicle to this storey if it's available for its type
                for i, row in enumerate(storey["slots"]):
                    for j, slot in enumerate(row):
                        if slot is None:
                            storey["slots"][i][j] = vehicle_code
                            vehicles[vehicle_code] = {
                                "number": vehicle_number,
                                "type": vehicle_type,
                                "storey_id": storey["id"],
                                "slot": (i, j),
                                "parking_time": parking_time,
                                "code": vehicle_code  # Ensure code is stored
                            }
                            assigned = True
                            break
                    if assigned:
                        break
            if assigned:
                break

        # If no slot is available
        if not assigned:
            message = "Parking space not available for your vehicle."
        return render_template("add_vehicle.html", vehicle_code=vehicle_code, message=message)

    return render_template("add_vehicle.html", vehicle_code=vehicle_code, message=message)

@app.route("/exit_vehicle", methods=["GET", "POST"])
def exit_vehicle():
    if session.get("role") != "gatekeeper":
        return redirect(url_for("login"))
    if request.method == "POST":
        code = request.form.get("code")
        vehicle = vehicles.pop(code, None)
        if vehicle:
            for storey in storeys:
                if storey["id"] == vehicle["storey_id"]:
                    i, j = vehicle["slot"]
                    storey["slots"][i][j] = None
            charges = calculate_charges(vehicle["parking_time"], vehicle["type"])
            return f"Vehicle {vehicle['number']} exited. Charges: Rs. {charges:.2f}"
        return "Invalid code."
    return render_template("exit_vehicle.html")

@app.route("/search_vehicle", methods=["GET", "POST"])
def search_vehicle():
    vehicle_found = False
    message = ""
    search_result = None

    if request.method == "POST":
        search_input = request.form.get("search_input")

        for vehicle_code, vehicle_data in vehicles.items():
            if vehicle_data["number"] == search_input or vehicle_code == search_input:
                vehicle_found = True
                search_result = vehicle_data
                break

        if not vehicle_found:
            message = "Vehicle not found."

    return render_template("search_vehicle.html", 
                           vehicle_found=vehicle_found, 
                           search_result=search_result,
                           message=message)

@app.route("/display_storey")
def display_storey():
    if session.get("role") != "gatekeeper":
        return redirect(url_for("login"))
    
    # Calculate parking cost for each parked vehicle
    for vehicle_code, vehicle in vehicles.items():
        parking_time = vehicle["parking_time"]
        vehicle_type = vehicle["type"]
        vehicles[vehicle_code]["cost"] = calculate_charges(parking_time, vehicle_type)

    return render_template("display_storey.html", storeys=storeys, vehicles=vehicles)

if __name__ == "__main__":
    app.run(debug=True)