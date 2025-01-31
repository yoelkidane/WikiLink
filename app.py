from flask import Flask, render_template, jsonify, request, session, redirect, url_for, flash
import requests
import time
from datetime import datetime
from bs4 import BeautifulSoup
import logging

logging.basicConfig(level=logging.DEBUG)
app = Flask(__name__)
app.secret_key = 'your_secret_key'

def get_random_wikipedia_page():
    url = "https://en.wikipedia.org/api/rest_v1/page/random/summary"
    response = requests.get(url)
    data = response.json()
    title = data.get("title")
    summary = data.get("extract")
    return title, summary

def get_wikipedia_html(page_title):
    url = f"https://en.wikipedia.org/wiki/{page_title}"
    app.logger.debug(f"Fetching Wikipedia page: {page_title}")
    response = requests.get(url)
    if response.status_code != 200:
        return None

    soup = BeautifulSoup(response.content, 'html.parser')
    for figure in soup.find_all('figure', class_='mw-default-size'):
        caption = figure.find('figcaption')
        if caption:
            caption.string = f"Caption: {caption.get_text()}"

    for elem in soup(['header', 'footer', 'nav', '.sistersitebox', '.toc', '.mw-editsection', '.mw-editsection-bracket']):
        elem.decompose()

    for edit_link in soup.find_all('span', class_='mw-editsection'):
        edit_link.decompose()

    for abbr in soup.find_all('abbr', title=True):
        if 'Discuss this template' in abbr['title'] or 'Template' in abbr['title']:
            abbr.decompose()

    for navbar in soup.find_all('div', class_='navbar plainlinks hlist navbar-mini'):
        navbar.decompose()

    for update_table in soup.find_all('table', class_='box-Update plainlinks metadata ambox ambox-content ambox-Update'):
        update_table.decompose()

    for issue_table in soup.find_all('table', class_='box-Multiple_issues'):
        issue_table.decompose()

    for unwanted_table in soup.find_all('table', class_='box-Update'):
        unwanted_table.decompose()

    return str(soup.find(id="content"))

def validate_session_state():
    required_keys = ['click_counter', 'start_page', 'end_page', 'visited_pages', 'current_index']
    for key in required_keys:
        if key not in session or session[key] is None:
            app.logger.debug(f"Session validation failed. Missing key: {key}")
            return False
    return True

def check_win_condition(page_title):
    end_page = session.get('end_page', '').replace(" ", "_")
    return page_title.replace(" ", "_") == end_page

@app.route('/')
def home():
    session['click_counter'] = -1
    session['visited_pages'] = []
    session['current_index'] = -1
    session['start_time'] = time.time()
    session['end_time'] = None
    return render_template('index.html', back_used=False)

@app.route('/api/challenge')
def get_challenge():
    start_page, start_summary = get_random_wikipedia_page()
    end_page, end_summary = get_random_wikipedia_page()

    session['start_page'] = start_page
    session['end_page'] = end_page
    session['summary_start'] = start_summary
    session['summary_end'] = end_summary
    session['connection_text'] = f'Connect "{start_page}" to "{end_page}"'
    session['click_counter'] = 0
    session['visited_pages'] = [start_page]
    session['current_index'] = 0
    session['start_time'] = time.time()
    session['end_time'] = None

    return jsonify({
        'start': start_page,
        'end': end_page,
        'summary_start': start_summary,
        'summary_end': end_summary,
        'connection_text': session['connection_text']
    })

@app.route('/wiki/<page_title>')
def wiki_page(page_title):
    destination_article_url = None
    if not validate_session_state():
        flash("Session state is invalid. Restarting the game.", "error")
        return redirect(url_for('home'))

    session['click_counter'] = max(session.get('click_counter', 0), 0) + 1

    if 'visited_pages' not in session or not session['visited_pages']:
        session['visited_pages'] = [page_title]
        session['current_index'] = 0
    else:
        if page_title != session['visited_pages'][session['current_index']]:
            if session['current_index'] + 1 < len(session['visited_pages']):
                session['visited_pages'] = session['visited_pages'][:session['current_index'] + 1]
            session['visited_pages'].append(page_title)
            session['current_index'] += 1

    app.logger.debug(f"Visited Pages: {session['visited_pages']}")
    app.logger.debug(f"Current Index: {session['current_index']}")

    if session['start_time'] is None:
        app.logger.debug("Recording start time for the game.")
        session['start_time'] = time.time()

    page_html = get_wikipedia_html(page_title)
    if not page_html:
        flash("The link you clicked is not a valid Wikipedia article and cannot be visited.", "error")
        last_page = session['visited_pages'][-2] if len(session['visited_pages']) > 1 else None
        return redirect(url_for('wiki_page', page_title=last_page) if last_page else url_for('home'))

    win = check_win_condition(page_title)
    if win:
        app.logger.debug(f"Win condition met! Current page: {page_title}")
        destination_article_url = f"https://en.wikipedia.org/wiki/{page_title}"
        if not session.get('end_time'):
            session['end_time'] = time.time()
            session['game_finished'] = True

    time_taken = None
    if session.get('end_time') and session.get('start_time'):
        time_taken = session['end_time'] - session['start_time']

    formatted_title = page_title.replace("_", " ")
    return render_template(
        'wiki_page.html',
        title=formatted_title,
        content=page_html,
        summary=session.get('summary_start', "Summary not available."),
        end_summary=session.get('summary_end', "Summary not available."),
        click_counter=session.get('click_counter', 0),
        win=win,
        game_finished=session.get('game_finished', False),
        time_taken=time_taken,
        destination_article_url=destination_article_url,
    )

@app.route('/back')
def back():
    if 'visited_pages' in session:
        visited_pages = session.get('visited_pages', [])
        current_index = session.get('current_index', 0)

        if current_index > 0:
            session['current_index'] -= 1
            new_page = visited_pages[session['current_index']]
            session.modified = True
            return jsonify({
                "redirect_url": url_for('wiki_page', page_title=new_page),
                "has_no_previous_article": False
            })

        elif current_index == 0:
            return jsonify({
                "has_no_previous_article": True,
                "message": "You are already at the first article!"
            })

    return jsonify({
        "error": "Session is invalid or no pages have been visited yet.",
        "has_no_previous_article": True
    })

@app.route('/api/timer', methods=['GET', 'POST'])
def timer():
    if request.method == 'POST':
        session['start_time'] = time.time()
        session['end_time'] = None
        return jsonify({"message": "Timer reset", "start_time": session['start_time']})

    start_time = session.get('start_time')
    if not start_time:
        elapsed_time = None
    else:
        elapsed_time = time.time() - start_time

    return jsonify({"elapsed_time": elapsed_time})

if __name__ == '__main__':
    app.run(debug=True)
