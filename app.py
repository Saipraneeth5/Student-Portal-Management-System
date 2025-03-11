from flask import Flask, render_template, request, redirect, url_for, session, flash
import requests
import json
import os
from collections import defaultdict

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Change this to a random secret key


# Hardcoded credentials for demonstration purposes
USERNAME = "anuragwifi"
PASSWORD = "anuragwifi"

# File to store problems
PROBLEMS_FILE = 'problems.json'

def load_problems():
    if os.path.exists(PROBLEMS_FILE):
        with open(PROBLEMS_FILE, 'r') as f:
            return json.load(f)
    return {"problems": [], "solved_problems": []}

def save_problems(data):
    with open(PROBLEMS_FILE, 'w') as f:
        json.dump(data, f)

# Load problems at the start
data = load_problems()

STUDENT_USERNAME = "Anurag"
STUDENT_PASSWORD = "Anurag@123"


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        if username == STUDENT_USERNAME and password == STUDENT_PASSWORD:
            session['logged_in'] = True
            session['username'] = username
            return redirect(url_for('home'))
        else:
            flash('Invalid username or password. Please try again.')
            return redirect(url_for('login'))
    
    return render_template('login.html')


@app.route('/')
def home():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    return render_template('home.html')

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    session.pop('username', None)
    return redirect(url_for('login'))


# WiFi Routes
@app.route('/wifi')
def wifi():
    return render_template('wifi.html')

@app.route('/wifi/login', methods=['POST'])
def wifi_login():
    username = request.form['username']
    password = request.form['password']
    
    if username == USERNAME and password == PASSWORD:
        session['logged_in'] = True
        return redirect(url_for('wifi'))
    else:
        flash('Invalid credentials, please try again.')
        return redirect(url_for('wifi'))

@app.route('/wifi/logout')
def wifi_logout():
    session.pop('logged_in', None)
    return redirect(url_for('wifi'))

# Attendance Calculator Routes
@app.route('/attendance', methods=['GET', 'POST'])
def attendance():
    results = ""
    if request.method == 'POST':
        # Get user inputs
        total_hours = int(request.form['totalHours'])
        total_hours_until_today = int(request.form['totalHoursUntilToday'])
        your_percentage = float(request.form['attendancePercentage'])

        # Calculate hours attended and remaining hours
        no_of_hours_you_attended = (your_percentage / 100) * total_hours_until_today
        remaining_hours = total_hours - total_hours_until_today

        # Calculate attendance requirements
        attendance_requirements = {
            65: int(total_hours * 0.65 - no_of_hours_you_attended) + 1,
            75: int(total_hours * 0.75 - no_of_hours_you_attended) + 1,
            85: int(total_hours * 0.85 - no_of_hours_you_attended) + 1,
            95: int(total_hours * 0.95 - no_of_hours_you_attended) + 1
        }

        # Generate results
        for percentage, tmp in attendance_requirements.items():
            if tmp > remaining_hours:
                results += f"For {percentage}% attendance: You are unworthy<br>"
            elif tmp < 0:
                results += f"For {percentage}% attendance: You can ignore all classes left<br>"
            else:
                results += f"For {percentage}% attendance: You need to attend {tmp} more hours out of {remaining_hours}<br>"

    return render_template('attendance.html', results=results)

# Backlog Calculator Routes
@app.route('/backlogs', methods=['GET', 'POST'])
def backlogs():
    results = None
    roll_number = None
    failed_subjects = []
    total_credits = 0
    total_failed_credits = 0
    total_credits_you_have = 0
    credits_needed_to_promote = 0
    credits_you_needed_to_promote = 0
    combinations_needed = []
    message = ""

    if request.method == 'POST':
        roll_number = request.form['roll_number']
        
        # API Details
        url = "https://api.campx.in/exams/student-results/external"
        headers = {
            "accept": "application/json",
            "x-api-version": "2",
            "x-institution-code": "aupulse",
            "x-tenant-id": "aupulse",
            "origin": "https://aupulse.campx.in",
            "referer": "https://aupulse.campx.in/",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        }
        
        params = {
            "examType": "general",
            "rollNo": roll_number,
        }
        response = requests.get(url, headers=headers, params=params)

        if response.status_code == 200:
            data = response.json()
            if "results" in data and isinstance(data["results"], list):
                results = data["results"]
                subjects = []  # To store all subjects for combination calculation

                for sem in results:
                    for subject in sem['subjectsResults']:
                        total_credits += float(subject['subject']['credits'])
                        subjects.append(subject['subject'])  # Store subject details
                        if not subject['consideredGrade']['passed']:
                            failed_subjects.append([subject['subject']['name'], subject['subject']['credits']])
                            total_failed_credits += float(subject['subject']['credits'])

                # Calculate total credits you have
                total_credits_you_have = total_credits - total_failed_credits

                # Calculate credits needed to promote
                credits_needed_to_promote = 0.60 * total_credits
                credits_you_needed_to_promote = int(credits_needed_to_promote - total_credits_you_have)+1

                # Check if credits you need to promote is greater than 0
                if credits_you_needed_to_promote > 0:
                    combinations_needed = find_combinations(failed_subjects, credits_you_needed_to_promote)
                    
                else:
                    message = "This time you can let it go."

        else:
            failed_subjects.append(["Error fetching data", "N/A"])

    return render_template('backlogs.html', results=results, roll_number=roll_number, 
                          failed_subjects=failed_subjects, total_credits=total_credits,
                          total_credits_you_have=total_credits_you_have,
                          credits_needed_to_promote=credits_needed_to_promote,
                          credits_you_needed_to_promote=credits_you_needed_to_promote,
                          combinations_needed=combinations_needed,
                          message=message)

def find_combinations(subjects, target):
    dp = defaultdict(list)
    dp[0] = [[]]  # Base case: one way to make 0 credits (empty selection)

    for name, credits in subjects:
        credits = int(float(credits))  # Ensure credits are treated as integers

        new_dp = defaultdict(list, dp)  # Start with a copy of the current dp
        for total, combinations in dp.items():
            for combination in combinations:
                if name not in [subj[0] for subj in combination]:  # Check for unique subjects
                    new_dp[total + credits].append(combination + [(name, credits)])

        dp = new_dp  # Update dp with new combinations

    # Collect and sort results
    result = []
    for total, combinations in dp.items():
        if total >= target:  # Only consider combinations that meet or exceed the target
            result.extend(combinations)

    result.sort(key=lambda x: (len(x), x))  # Sort by length and lexicographically

    return result[:15]  # Return up to 15 combinations

# Problem Reporting Routes
@app.route('/problems')
def problems():
    return render_template('problems.html', problems=data['problems'], solved_problems=data['solved_problems'])

@app.route('/problems/report', methods=['POST'])
def report_problem():
    problem_text = request.form.get('problemText')
    if problem_text:
        data['problems'].append({'text': problem_text, 'solved': False})
        save_problems(data)
    return redirect(url_for('problems'))

@app.route('/problems/solve/<int:index>')
def solve_problem(index):
    if 0 <= index < len(data['problems']):
        problem = data['problems'].pop(index)
        problem['solved'] = True
        data['solved_problems'].append(problem)
        save_problems(data)
    return redirect(url_for('problems'))

if __name__ == '__main__':
    app.run(debug=True)