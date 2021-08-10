import os
from flask import Flask, render_template, request, g, session, url_for, redirect
from database import get_db
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = b'\xe0\x95\x11\xf8\xda\xfc0\xdag\x19\x11\x8c\x1ahu\xcaU\x8eh\xc4\x8bC\xf6\xfd'


@app.teardown_appcontext
def close_db(error):
    if hasattr(g, 'postgres_db_cur'):
        g.postgres_db_cur.close()

    if hasattr(g, 'postgres_db_conn'):
        g.postgres_db_conn.close()


def get_current_user():
    user_result = None
    if 'user' in session:
        user = session['user']

        db = get_db()
        db.execute('SELECT id, name, password, expert, admin FROM users WHERE name = %s', (user,))
        user_result = db.fetchone()

    return user_result


@app.route('/')
def home():
    user = get_current_user()
    db = get_db()
    db.execute('SELECT questions.id as question_id, questions.question_text, askers.name as asker_name,'
               'experts.name as expert_name FROM questions '
               'join users as askers on askers.id = questions.asked_by_id '
               'join users as experts on experts.id = questions.expert_id '
               'WHERE questions.answer_text IS NOT NULL')
    questions_results = db.fetchall()

    return render_template('home.html', user=user, questions=questions_results)


@app.route('/register', methods=['GET', 'POST'])
def register():
    user = get_current_user()

    if request.method == 'POST':
        name = request.form.get('name')

        db = get_db()
        db.execute('SELECT id FROM users WHERE name = %s', (request.form.get('name'),))
        existing_user = db.fetchone()

        if existing_user:
            return render_template('register.html', user=user, error='User already exists!')

        hashed_password = generate_password_hash(request.form.get('password'), method='sha256')
        db.execute(f'INSERT INTO users (name, password, expert, admin) values (%s, %s, %s, %s)',
                   (name, hashed_password, '0', '0'))

        session['user'] = name
        return redirect(url_for('home'))

    return render_template('register.html', user=user)


@app.route('/login', methods=['GET', 'POST'])
def login():
    user = get_current_user()
    error = None

    if request.method == 'POST':
        db = get_db()

        name = request.form.get('name')
        password = request.form.get('password')

        db.execute('SELECT name, password FROM users WHERE name = %s', (name,))
        user_result = db.fetchone()

        if user_result:

            password_db = user_result['password']

            if check_password_hash(password_db, password):
                session['user'] = user_result['name']
                return redirect(url_for('home'))
            else:
                error = 'The password is incorrect'
        else:
            error = 'The usename is incorrect'

    return render_template('login.html', user=user, error=error)


@app.route('/question/<question_id>')
def question(question_id):
    user = get_current_user()

    db = get_db()
    db.execute('SELECT questions.question_text, questions.answer_text, askers.name as asker_name, '
               'experts.name as expert_name FROM questions '
               'join users as askers on askers.id = questions.asked_by_id '
               'join users as experts on experts.id = questions.expert_id '
               'WHERE questions.id = %s', (question_id,))
    question_result = db.fetchone()

    return render_template('question.html', user=user, question=question_result)


@app.route('/answer/<question_id>', methods=['GET', 'POST'])
def answer(question_id):
    user = get_current_user()

    if not user:
        return redirect(url_for('login'))

    if not user['expert']:
        return redirect(url_for('home'))

    db = get_db()
    db.execute('SELECT id, question_text FROM questions WHERE id = %s', (question_id,))
    question_result = db.fetchone()

    if request.method == 'POST':
        db.execute('UPDATE questions SET answer_text = %s WHERE id = %s', (request.form.get("answer"), question_id))
        return redirect(url_for('unanswered'))

    return render_template('answer.html', user=user, question=question_result)


@app.route('/ask', methods=['GET', 'POST'])
def ask():
    db = get_db()
    user = get_current_user()

    if not user:
        return redirect(url_for('login'))

    if request.method == 'POST':
        db.execute('INSERT INTO questions (question_text, asked_by_id, expert_id) values (%s, %s, %s)',
                   (request.form.get('question'), user['id'], request.form.get('expert')))
        return redirect(url_for('home'))

    db.execute('SELECT id, name FROM users WHERE expert = True')
    expert_results = db.fetchall()

    return render_template('ask.html', user=user, experts=expert_results)


@app.route('/unanswered')
def unanswered():
    user = get_current_user()

    if not user:
        return redirect(url_for('login'))

    if not user['expert']:
        return redirect(url_for('home'))

    db = get_db()
    db.execute('SELECT questions.id as id, questions.question_text as question_text, users.name as '
               'name FROM questions join users on questions.asked_by_id = users.id '
               'WHERE questions.answer_text is null AND questions.expert_id = %s',
               (user['id'],))
    question_results = db.fetchall()

    return render_template('unanswered.html', user=user, questions=question_results)


@app.route('/users')
def users():
    user = get_current_user()

    if not user:
        return redirect(url_for('login'))

    if not user['admin']:
        return redirect(url_for('home'))

    db = get_db()
    db.execute('SELECT id, name, expert, admin FROM users')
    users_results = db.fetchall()

    return render_template('users.html', user=user, users=users_results)


@app.route('/promote/<user_id>')
def promote(user_id):
    user = get_current_user()

    if not user:
        return redirect(url_for('login'))

    if not user['admin']:
        return redirect(url_for('home'))

    db = get_db()
    db.execute('UPDATE users SET expert = True WHERE id = %s', (user_id,))

    return redirect(url_for('users'))


@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('home'))


if __name__ == '__main__':
    app.run(debug=True)
