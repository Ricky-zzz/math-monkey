import uuid
from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User
from django.contrib import messages
import random
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
import json
from django.utils import timezone
from .models import GameRecord, Profile, WordProblem
import math
from .question_data import QUESTIONS_DATA

NAMES = ["Alice", "Bob", "Charlie", "Mia", "Leo", "Lina", "Dino", "Zara", "Ben", "Sara"]
ITEMS = ["apple", "banana", "coin", "star", "book", "pencil", "cookie", "ball", "flower"]

ADD_TEMPLATES = [
    "{name} picked {a} {item}s in the morning and {b} in the afternoon. How many did they pick in total?",
    "{a} {item}s were on the table, and {b} more were added. How many are there now?",
    "{name} bought {a} {item}s from one store and {b} from another. How many did they buy altogether?",
    "{name} counted {a} {item}s in a jar and {b} more in a bag. What is the total number?",
    "A basket has {a} {item}s. {name} puts {b} more inside. How many are in the basket now?",
    "{name} grows {a} {item}s in the garden and finds {b} more on the ground. How many do they have?",
    "There are {a} {item}s on one shelf and {b} on another shelf. How many are there in all?",
    "{name} collects {a} {item}s today and {b} tomorrow. How many do they collect?",
    "A box contains {a} {item}s. {b} new {item}s were added. How many does the box have now?",
    "{name} received {a} {item}s as a gift. Later, {name2} gave them {b} more. How many do they have now?"
]

SUB_TEMPLATES = [
    "{name} starts with {a} {item}s. They used {b}. How many remain?",
    "There were {a} {item}s in the basket. {name} ate {b}. How many are left?",
    "{name} had {a} {item}s, but lost {b}. How many do they still have?",
    "A store had {a} {item}s. It sold {b} today. How many are left?",
    "{name} collected {a} {item}s but gave {b} to {name2}. How many remain?",
    "There were {a} {item}s in a jar. {b} fell out. How many are still inside?",
    "{name} saved {a} {item}s. They spent {b}. How many do they have now?",
    "A box holds {a} {item}s. Someone removed {b}. How many are still in the box?",
    "{name} had {a} {item}s for a project but only used {b}. How many are unused?",
    "{a} {item}s were on the desk. After {name} took {b}, how many remain?"
]

MUL_TEMPLATES = [
    "{name} has {a} bags with {b} {item}s in each. How many {item}s do they have total?",
    "There are {a} groups of {item}s, and each group has {b}. How many {item}s are there?",
    "{name} read {a} pages each day for {b} days. How many pages did they read?",
    "{name} bought {a} packs of {item}s. Each pack contains {b}. How many {item}s did they buy?",
    "A garden has {a} rows of plants. Each row has {b} {item}s. How many plants are there?",
    "A teacher arranged the class into {a} teams with {b} students each. How many students total?",
    "{name} makes {a} batches of cookies. Each batch uses {b} {item}s. How many {item}s are needed?",
    "There are {a} shelves, and each shelf has {b} {item}s. How many in total?",
    "{name} claps {a} times per minute for {b} minutes. How many claps is that?",
    "Each box holds {b} {item}s. If there are {a} boxes, how many {item}s are there?"
]

DIV_TEMPLATES = [
    "{name} has {a} {item}s and wants to divide them among {b} people. How many does each person get?",
    "{a} {item}s need to be packed equally into {b} boxes. How many per box?",
    "{name} baked {a} cookies and places {b} in each bag. How many bags can they fill?",
    "A total of {a} {item}s are shared among {b} students. How many per student?",
    "A teacher has {a} {item}s and gives each child {b}. How many children can receive one?",
    "{name} wants to split {a} {item}s into groups of {b}. How many groups will be formed?",
    "There are {a} {item}s to distribute into {b} equal piles. How many in each pile?",
    "A factory produced {a} {item}s and packages them in groups of {b}. How many packages are made?",
    "{name} collected {a} {item}s and gives {b} to each friend. How many friends can get one share?",
    "If {a} {item}s are placed equally into {b} rows, how many will be in each row?"
]

def seed_db(request):
    if not request.user.is_superuser:
        return JsonResponse({'status': 'error', 'message': 'Admins only'}, status=403)

    WordProblem.objects.all().delete()

    problems = []
    for q_text, ans, topic, diff in QUESTIONS_DATA:
        problems.append(WordProblem(
            question_text=q_text,
            answer=ans,
            topic=topic,
            difficulty=diff
        ))
    WordProblem.objects.bulk_create(problems)
    
    return JsonResponse({'status': 'success', 'count': len(problems)})

def multiplayer_view(request):
    if not request.user.is_authenticated:
        return redirect('auth')
    return render(request, 'game/multiplayer.html')

@require_http_methods(["GET"])
def get_questions(request):
    difficulty = request.GET.get('difficulty', 'medium')
    topics_param = request.GET.get('topics', 'mixed')
    
    form_param = request.GET.get('form', 'mixed') 
    if not form_param: form_param = 'mixed'

    count = int(request.GET.get('count', 10))
    
    if topics_param == 'mixed':
        selected_topics = ['addition', 'subtraction', 'multiplication', 'division']
    else:
        raw_topics = topics_param.split(',')
        selected_topics = [t for t in raw_topics if t != 'mixed' and t]
        
        if not selected_topics:
             selected_topics = ['addition', 'subtraction', 'multiplication', 'division']

    questions = []
    
    for i in range(count):
        topic = random.choice(selected_topics)
        
        if form_param == 'mixed':
            mode = random.choice(['word', 'numeric'])
        else:
            mode = form_param 
        
        question_text = ""
        answer = 0
        
        if mode == 'word':
            db_question = WordProblem.objects.filter(
                topic=topic, 
                difficulty=difficulty
            ).order_by('?').first()

            if db_question:
                question_text = db_question.question_text
                answer = db_question.answer
            else:
                if topic == 'addition':
                    question_text, answer = generate_word_addition(difficulty)
                elif topic == 'subtraction':
                    question_text, answer = generate_word_subtraction(difficulty)
                elif topic == 'multiplication':
                    question_text, answer = generate_word_multiplication(difficulty)
                elif topic == 'division':
                    question_text, answer = generate_word_division(difficulty)

        else:
            if topic == 'addition':
                question_text, answer = generate_addition(difficulty)
            elif topic == 'subtraction':
                question_text, answer = generate_subtraction(difficulty)
            elif topic == 'multiplication':
                question_text, answer = generate_multiplication(difficulty)
            elif topic == 'division':
                question_text, answer = generate_division(difficulty)
        
        choices = generate_choices(answer)
        
        questions.append({
            "id": i, 
            "text": question_text,
            "answer": answer,
            "choices": choices,
            "topic": topic,
            "mode": mode 
        })
        
    return JsonResponse(questions, safe=False)

def get_random_context():
    """Returns a dict with random name, name2, and item."""
    name1 = random.choice(NAMES)
    name2 = random.choice([n for n in NAMES if n != name1]) 
    item = random.choice(ITEMS)
    return name1, name2, item

def generate_choices(answer):
    choices = {answer} 
    lower_bound = max(0, answer - 10)
    upper_bound = answer + 10
    
    while len(choices) < 4:
        wrong = random.randint(lower_bound, upper_bound)
        if wrong != answer:
            choices.add(wrong)
            
    choices_list = list(choices)
    random.shuffle(choices_list)
    return choices_list

def generate_addition(difficulty):
    if difficulty == 'easy':
        a, b = random.randint(1, 10), random.randint(1, 10)
    elif difficulty == 'medium':
        a, b = random.randint(10, 50), random.randint(2, 20)
    else: 
        a, b = random.randint(50, 200), random.randint(20, 100)
    return f"{a} + {b}", a + b

def generate_subtraction(difficulty):
    if difficulty == 'easy':
        a, b = random.randint(5, 15), random.randint(1, 10)
    elif difficulty == 'medium':
        a, b = random.randint(20, 80), random.randint(5, 20)
    else: 
        a, b = random.randint(100, 300), random.randint(50, 150)
    
    if a < b: a, b = b, a 
    return f"{a} - {b}", a - b

def generate_multiplication(difficulty):
    if difficulty == 'easy':
        a, b = random.randint(1, 5), random.randint(1, 5)
    elif difficulty == 'medium':
        a, b = random.randint(3, 12), random.randint(2, 10)
    else: 
        a, b = random.randint(10, 20), random.randint(5, 15)
    return f"{a} × {b}", a * b

def generate_division(difficulty):
    if difficulty == 'easy':
        answer, divisor = random.randint(1, 5), random.randint(1, 5)
    elif difficulty == 'medium':
        answer, divisor = random.randint(2, 12), random.randint(2, 10)
    else:
        answer, divisor = random.randint(5, 20), random.randint(5, 15)
        
    dividend = answer * divisor
    return f"{dividend} ÷ {divisor}", answer

def generate_word_addition(difficulty):
    _, answer = generate_addition(difficulty)
    if difficulty == 'easy':
        a, b = random.randint(1, 10), random.randint(1, 10)
    elif difficulty == 'medium':
        a, b = random.randint(10, 50), random.randint(2, 20)
    else: 
        a, b = random.randint(50, 200), random.randint(20, 100)
        
    name1, name2, item = get_random_context()
    template = random.choice(ADD_TEMPLATES)
    question = template.format(name=name1, name2=name2, item=item, a=a, b=b)
    return question, a + b

def generate_word_subtraction(difficulty):
    if difficulty == 'easy':
        a, b = random.randint(5, 15), random.randint(1, 10)
    elif difficulty == 'medium':
        a, b = random.randint(20, 80), random.randint(5, 20)
    else: 
        a, b = random.randint(100, 300), random.randint(50, 150)
    
    if a < b: a, b = b, a
    
    name1, name2, item = get_random_context()
    template = random.choice(SUB_TEMPLATES)
    question = template.format(name=name1, name2=name2, item=item, a=a, b=b)
    return question, a - b

def generate_word_multiplication(difficulty):
    if difficulty == 'easy':
        a, b = random.randint(1, 5), random.randint(1, 5)
    elif difficulty == 'medium':
        a, b = random.randint(3, 12), random.randint(2, 10)
    else: 
        a, b = random.randint(10, 20), random.randint(5, 15)

    name1, name2, item = get_random_context()
    template = random.choice(MUL_TEMPLATES)
    question = template.format(name=name1, item=item, a=a, b=b)
    return question, a * b

def generate_word_division(difficulty):
    if difficulty == 'easy':
        answer, divisor = random.randint(1, 5), random.randint(1, 5)
    elif difficulty == 'medium':
        answer, divisor = random.randint(2, 12), random.randint(2, 10)
    else:
        answer, divisor = random.randint(5, 20), random.randint(5, 15)
    
    dividend = answer * divisor 
    
    name1, name2, item = get_random_context()
    template = random.choice(DIV_TEMPLATES)
    
    question = template.format(name=name1, item=item, a=dividend, b=divisor)
    return question, answer

# Auth page
def auth_view(request):
    if request.user.is_authenticated:
        return redirect('play')
    return render(request, 'game/auth.html')

# Login
def login_api(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('play')
        else:
            messages.error(request, "Invalid username or password.")
    return redirect('auth')

#Register
def register_api(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            email = request.POST.get('email')
            if email:
                user.email = email
                user.save()           
            
            login(request, user)
            return redirect('play')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    msg = f"{error}" if field == '__all__' else f"{field.capitalize()}: {error}"
                    messages.error(request, msg)
            return redirect('/?mode=register') 
            
    return redirect('auth')

# Guest Login
def guest_api(request):
    random_suffix = str(uuid.uuid4())[:4]
    username = f"Guest-{random_suffix}"
    user = User.objects.create_user(username=username)
    user.save()
    login(request, user)
    return redirect('play')

def logout_view(request):
    logout(request)
    return render(request, 'game/auth.html')

def play_view(request):
    return render(request, 'game/play.html')\


@require_http_methods(["POST"])
def submit_result(request):
    try:
        data = json.loads(request.body)
        
        record = GameRecord.objects.create(
            user=request.user,
            mode=data.get('mode', 'timetrial'),
            score=data.get('score', 0),
            total_questions=data.get('total_questions', 0),
            correct_answers=data.get('correct_answers', 0),
            duration=data.get('duration', 0), 
            difficulty=data.get('final_difficulty', 'adaptive'),
            topics=data.get('topics', ['mixed'])
        )
        
        profile = request.user.profile
        profile.games_played += 1
        
        earned_xp = (record.correct_answers * 10) + int(record.score / 10) 
        
        profile.xp += earned_xp
               
        new_level = math.floor(0.1 * math.sqrt(profile.xp)) + 1
        
        leveled_up = new_level > profile.level
        profile.level = new_level
        
        session_best_streak = data.get('highest_streak', 0)
        if session_best_streak > profile.highest_streak:
            profile.highest_streak = session_best_streak
            
        if record.accuracy > 80:
            profile.mmr += 25
        elif record.accuracy > 50:
            profile.mmr += 10
        else:
            profile.mmr = max(0, profile.mmr - 10)
            
        profile.save()
        
        return JsonResponse({
            'status': 'success', 
            'new_mmr': profile.mmr,
            'earned_xp': earned_xp,
            'new_level': profile.level,
            'leveled_up': leveled_up
        })
        
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    
def get_leaderboard(request):
    top_players = Profile.objects.select_related('user').order_by('-mmr')[:10]
    
    leaderboard = []
    for rank, profile in enumerate(top_players, 1):
        leaderboard.append({
            'rank': rank,
            'username': profile.user.username, 
            'level': profile.level,
            'mmr': profile.mmr,
            'avg_accuracy': profile.avg_accuracy,
        })
        
    return JsonResponse(leaderboard, safe=False)


@require_http_methods(["GET"])
def get_user_profile(request):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Not authenticated'}, status=401)
        
    profile = request.user.profile
    
    recent_games = GameRecord.objects.filter(user=request.user).order_by('-created_at')[:5]
    
    history_data = []
    for game in recent_games:
        history_data.append({
            'mode': game.get_mode_display(), 
            'score': game.score,
            'accuracy': game.accuracy,
            'difficulty': game.difficulty.capitalize(),
            'date': game.created_at.strftime("%b %d, %H:%M") 
        })
        
    data = {
        'username': request.user.username,
        'level': profile.level,
        'xp': profile.xp,
        'mmr': profile.mmr,
        'avg_accuracy': profile.avg_accuracy,
        'games_played': profile.games_played,
        'highest_streak': profile.highest_streak,
        'history': history_data
    }
    
    return JsonResponse(data)