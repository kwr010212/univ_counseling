import os
import joblib
import json
import random
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.utils import timezone
from django.http import JsonResponse
from openai import OpenAI
import openai
from collections import defaultdict
import datetime
from django.contrib.auth.decorators import login_required

from .models import Question, Quote, AnalysisLog, CommunityPost, CommunityComment
from django.db.models import Count

# API 및 클라이언트 초기화
client = OpenAI(api_key=settings.OPENAI_API_KEY)
openai.api_key = getattr(settings, 'OPENAI_API_KEY', '기본값')

# 💬 글로벌 채팅방 메모리 저장소 (기존 코드 유지)
CHAT_ROOMS = {'취업': [], '진로': [], '인간관계': [], '일반': []}

# 👥 [새로 추가] 실시간 채팅방별 접속자 명단 관리를 위한 전역 메모리
ROOM_USERS = {'취업': set(), '진로': set(), '인간관계': set(), '일반': set()}


# 💡 토크나이저 함수 (머신러닝 직렬화 로드용 전역 선언)
def simple_korean_tokenizer(text):
    clean_text = "".join([c for c in text if c.isalnum() or c.isspace()])
    return clean_text.split()


# ==========================================================
# 🛠️ [졸업작품 핵심 알고리즘 1] 자체 감정 스코어링 엔진 (기존 코드)
# ==========================================================
def analyze_emotion_scores(text):
    anxiety_keywords = ['무섭다', '걱정', '두렵', '불안', '위축', '떨린', '긴장', '무서워', '두려워']
    urgency_keywords = ['조급', '뒤처', '늦었', '벌써', '나만', '빨리', '급하', '하루빨리', '초조']
    depression_keywords = ['우울', '괴롭', '쓸모', '외롭', '스트레스', '숨이', '막막', '자괴감', '무기력', '바닥']
    growth_keywords = ['열심히', '극복', '도전', '노력', '해내', '다짐', '굳게', '바꾸', '나아가']
    stability_keywords = ['다행', '감사', '고맙', '위로', '다독', '편안', '안심', '덕분에', '따뜻']

    anxiety_base, urgency_base, depression_base, growth_base, stability_base = 10, 10, 10, 10, 10

    for kw in anxiety_keywords:
        if kw in text: anxiety_base += 25
    for kw in urgency_keywords:
        if kw in text: urgency_base += 25
    for kw in depression_keywords:
        if kw in text: depression_base += 25
    for kw in growth_keywords:
        if kw in text: growth_base += 25
    for kw in stability_keywords:
        if kw in text: stability_base += 25

    return (
        min(anxiety_base, 100), 
        min(urgency_base, 100), 
        min(depression_base, 100),
        min(growth_base, 100),
        min(stability_base, 100)
    )


# ==========================================================
# 🛠️ [졸업작품 핵심 알고리즘 2] 로컬 RAG 지식 매칭 (기존 코드 발전)
# ==========================================================
def find_matched_guidelines(text, category):
    guide_db = {
        "취업": "[교내 백서 가이드라인 항목 12번]: 학생처 대학일자리플러스센터(본관 3층) 1:1 자기소개서 첨삭 프로그램 및 무료 AI 모의면접 루틴 운영.",
        "진로": "[교내 백서 가이드라인 항목 07번]: 학사관리 규정 제 24조에 따른 전과 및 복수전공 신청 기준 안내 및 학생생활상담소 직무 적성 검사(HOLLAND) 프로그램.",
        "인간관계": "[교내 백서 가이드라인 항목 02번]: 교내 학생심리상담센터(복지관 2층) 익명 개인 상담 및 대인관계 회복탄력성 모듈 집단 치유 프로그램 운영."
    }
    matched = guide_db.get(category, "전공 주임 교수님과의 대면 면담 세션 및 교내 학생 지원 통합 시스템 연계 가이드라인을 매칭합니다.")
    
    if "학점" in text or "공부" in text:
        matched += " [추가 지식 주입: 교수학습개발센터(CTL)의 학습 바우처 및 튜터링 프로그램 정보 포함]"
    if "비용" in text or "경제" in text:
        matched += " [추가 지식 주입: 학생과 장학팀의 긴급 가계 곤란 장학금 및 근로장학생 신청 조건 포함]"
        
    return matched


# ==========================================================
# 💬 실시간 누적 대화 & 종료 제어형 상담 엔진
# ==========================================================

@login_required
def process_counseling(request):
    if request.method == 'POST':
        user_answer = request.POST.get('user_answer', '').strip()
        action = request.POST.get('action', '')

        if 'chat_history' not in request.session:
            request.session['chat_history'] = []
        
        chat_history = request.session['chat_history']
        is_topic_room = request.session.get('is_topic_room', False)

        if action == 'finish' or user_answer == '종료':
            if not chat_history:
                return redirect('counseling_home')

            full_context = " ".join([f"[{msg['sender']}]: {msg['text']}" for msg in chat_history])
            first_user_msg = next((msg['text'] for msg in chat_history if msg['sender'] == 'USER'), "집중 주제 상담 대화")
            
            predicted_category = '일반'
            try:
                model_path = os.path.join(settings.BASE_DIR, 'counseling', 'ml_model', 'worry_classifier.pkl')
                model_pipeline = joblib.load(model_path)
                predicted_category = model_pipeline.predict([first_user_msg])[0]
            except Exception:
                if any(w in full_context for w in ['취업', '자소서', '면접', '스펙']): predicted_category = '취업'
                elif any(w in full_context for w in ['진로', '전공', '전과', '휴학']): predicted_category = '진로'
                elif any(w in full_context for w in ['친구', '인간관계', '팀플', '갈등']): predicted_category = '인간관계'

            anxiety, urgency, depression, growth, stability = analyze_emotion_scores(full_context)
            matched_guide_text = find_matched_guidelines(full_context, predicted_category)

            try:
                prompt = f"""
                당신은 대학생 전문 상담 교수입니다. 
                아래 학생이 교수와 주고받은 전체 대화 내역과 교내 공식 대응 가이드라인을 분석하여, 
                따뜻한 위로와 함께 앞으로의 실질적인 행동 지침(결론)을 도출해 주세요.

                [교수와 학생의 전체 대화 내역]:
                {full_context}

                [정량적 감정 지수]: 불안 {anxiety}, 조급 {urgency}, 우울 {depression}, 성장의지 {growth}, 안정감 {stability}
                [교내 매뉴얼 가이드라인 컨텍스트]:
                {matched_guide_text}
                """
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.7
                )
                ai_solution = response.choices[0].message.content
            except Exception as e:
                ai_solution = f"👩‍⚕️ AI 최종 솔루션 산출 중 기술적 오류가 발생했습니다. ({str(e)})"

            db_chat_backup = json.dumps(chat_history, ensure_ascii=False)
            combined_backup = f"{matched_guide_text}|||{db_chat_backup}"

            display_title = f"[{predicted_category} 집중 상담] AI 교수의 심층 꼬리질문 진단" if is_topic_room else "실시간 자율 연속 대화 진단"

            log = AnalysisLog.objects.create(
                user=request.user,
                chosen_question=display_title,
                user_answer=first_user_msg[:100], 
                predicted_category=predicted_category,
                ai_solution=ai_solution,
                anxiety_score=anxiety, urgency_score=urgency, depression_score=depression,
                growth_score=growth, stability_score=stability,
                matched_guide=combined_backup  
            )

            if 'chat_history' in request.session: del request.session['chat_history']
            if 'is_topic_room' in request.session: del request.session['is_topic_room']
            request.session.modified = True

            return redirect('counseling_detail', log_id=log.id)

        if user_answer:
            chat_history.append({'sender': 'USER', 'text': user_answer})
            
            try:
                context_stream = " ".join([f"{m['sender']}: {m['text']}" for m in chat_history])
                prompt = f"""
                당신은 학생과 실시간 상담 중인 대학의 전문 상담 교수입니다.
                학생의 직전 대답을 듣고 진심 어린 공감을 해준 뒤, 학생의 속마음이나 구체적인 처지를 더 구체화할 수 있도록 친절한 '추가 질문(꼬리질문)'을 이어서 던져주세요.
                아직 상담이 진행 중이므로 너무 성급하게 조언이나 결론을 내리지 마세요. 2~3문장 이내의 간결하고 다정한 대화로 리드해 주세요.

                [현재까지의 대화 맥락]: {context_stream}
                """
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.7
                )
                ai_reply = response.choices[0].message.content
            except Exception as e:
                ai_reply = f"🤖 방금 하신 말씀에 대해 조금 더 구체적으로 말씀해 주실 수 있을까요?"

            chat_history.append({'sender': 'AI', 'text': ai_reply})
            request.session['chat_history'] = chat_history
            request.session.modified = True

    return render(request, 'counseling/continuous_chat.html')


# ==========================================================
# 🗂️ 기존 기능의 Views 함수 영역
# ==========================================================

@login_required
def counseling_home(request):
    quote = Quote.objects.order_by('?').first()
    random_questions = Question.objects.order_by('?')[:3]
    user_logs = AnalysisLog.objects.filter(user=request.user).order_by('-created_at')
    context = {
        'quote': quote,
        'questions': random_questions,
        'user_logs': user_logs
    }
    return render(request, 'counseling/dashboard.html', context)


@login_required
def category_counseling(request, category_name):
    deep_questions_pool = {
        '취업': [
            "취업 준비 단계 중 가장 막히는 부분이 어디인가요? (자소서, 면접, 스펙 등)",
            "내가 원하는 직무나 기업의 기준과 현실적인 조건 사이에서 어떤 갈등을 겪고 계시나요?",
            "하반기 채용 시즌이 다가오면서 느끼는 조급함이나 불안감의 가장 큰 원인은 무엇인가요?",
            "준비해야 할 자격증이나 어학 점수 때문에 심리적 압박감을 크게 받고 계신가요?",
            "주변 동기들의 합격 소식을 들을 때 나만 뒤처지는 것 같은 기분이 드시나요?"
        ],
        '진로': [
            "현재 전공이 맞지 않다고 느끼시는 가장 결정적인 계기나 이유가 무엇인가요?",
            "복수전공, 전과, 혹은 휴학 중에서 고민하고 계신 구체적인 방향이 있으신가요?",
            "졸업 후의 불투명한 미래 때문에 지금 당장 학업에 집중하기 힘든 상황이신가요?",
            "내가 정말 좋아하는 일과 잘하는 일 사이에서 선택을 내리지 못해 고민이신가요?",
            "부모님이 원하시는 진로 방향과 내가 가고 싶은 길에 차이가 있나요?"
        ],
        '인간관계': [
            "현재 갈등을 겪고 있는 대상(팀플 조원, 동기, 선후배, 연인 등)과의 핵심 문제가 무엇인가요?",
            "대인관계에서 오는 스트레스로 인해 일상생활이나 학업에 지장을 받고 계신가요?",
            "타인의 시선이나 평가에 과도하게 신경 쓰이게 되는 구체적인 일화가 있었나요?",
            "새로운 학기나 새로운 환경에서 사람들과 친해지는 것 자체가 부담스럽게 느껴지시나요?",
            "믿었던 친구나 주변 사람에게 서운함을 느끼거나 배신감을 경험하신 적이 있나요?"
        ]
    }
    
    questions = deep_questions_pool.get(category_name, [
        "최근 마음을 가장 무겁게 만들고 있는 생각은 무엇인가요?",
        "누구에게도 말하지 못하고 혼자 삼켜야 했던 답답한 상황이 있으신가요?",
        "요즘 일상에서 무기력함을 느끼거나 의욕이 떨어지는 특별한 원인이 있을까요?"
    ])
    
    sampled_questions = random.sample(questions, min(len(questions), 3))
    
    context = {
        'category_name': category_name,
        'questions': sampled_questions
    }
    return render(request, 'counseling/select_question.html', context)


@login_required
def start_topic_counseling(request):
    if request.method == 'POST':
        category_name = request.POST.get('category_name', '일반')
        selected_question = request.POST.get('selected_question', '')
        
        request.session['chat_history'] = []
        request.session['is_topic_room'] = True  
        
        request.session['chat_history'].append({
            'sender': 'AI',
            'text': f"안녕하세요! 오늘 [{category_name}]에 대해 깊이 있는 이야기를 나누어 보려고 해요.\n\n골라주신 질문인 \"{selected_question}\" 에 대해 지금 어떤 마음이나 상황이신지 편하게 말씀해 주세요. 👩‍⚕️"
        })
        
        request.session.modified = True
        return redirect('process_counseling')
        
    return redirect('counseling_home')

@login_required
def counseling_detail(request, log_id):
    log = get_object_or_404(AnalysisLog, id=log_id, user=request.user)
    category_stats = AnalysisLog.objects.filter(user=request.user) \
                                        .values('predicted_category') \
                                        .annotate(count=Count('id'))
    
    categories = []
    counts = []
    
    for stat in category_stats:
        cat_name = stat['predicted_category'] if stat['predicted_category'] else '일반'
        categories.append(cat_name)
        counts.append(stat['count'])
        
    if not categories:
        categories = ['진단 데이터 없음']
        counts = [1]

    context = {
        'log': log,
        'category_labels': json.dumps(categories),
        'category_counts': json.dumps(counts),
        'current_category': log.predicted_category, 
    }
    
    return render(request, 'counseling/detail.html', context)


@login_required
def emotion_calendar(request):
    logs = AnalysisLog.objects.filter(user=request.user).order_by('created_at')
    calendar_data = defaultdict(lambda: {'emojis': [], 'logs': []})
    
    for log in logs:
        date_str = log.created_at.strftime('%Y-%m-%d')
        scores = {
            '🔥': log.anxiety_score or 0,     
            '😭': log.depression_score or 0,  
            '⏱️': log.urgency_score or 0,     
            '✨': log.growth_score or 0,       
            '🍀': log.stability_score or 0     
        }
        
        max_emoji = '😊'
        if max(scores.values()) > 0:
            max_emoji = max(scores, key=scores.get)
            
        if max_emoji not in calendar_data[date_str]['emojis']:
            calendar_data[date_str]['emojis'].append(max_emoji)
            
        calendar_data[date_str]['logs'].append({
            'id': log.id,
            'title': log.chosen_question,
            'category': log.predicted_category,
            'time': log.created_at.strftime('%H:%M'),
            'main_emoji': max_emoji
        })

    context = {
        'calendar_data': dict(calendar_data),
    }
    return render(request, 'counseling/emotion_calendar.html', context)


@login_required
def write_diary(request):
    if request.method == 'POST':
        diary_content = request.POST.get('diary_content')
        request.POST = {
            'csrf_token': request.POST.get('csrf_token'),
            'question_id': 'free',
            'user_answer': diary_content
        }
        return process_counseling(request)
    return redirect('emotion_calendar')


def get_user_top_worry(user):
    from django.db.models import Avg
    logs = AnalysisLog.objects.filter(user=user)
    
    if not logs.exists():
        return '일반'
        
    averages = logs.aggregate(
        avg_anxiety=Avg('anxiety_score'),
        avg_urgency=Avg('urgency_score'),
        avg_depression=Avg('depression_score'),
        avg_growth=Avg('growth_score'),
        avg_stability=Avg('stability_score')
    )
    
    latest_log = logs.order_by('-created_at').first()
    return latest_log.predicted_category if latest_log.predicted_category else '일반'


@login_required
def community_list(request):
    selected_category = request.GET.get('category')
    
    if selected_category and selected_category in ['취업', '진로', '인간관계', '일반']:
        posts = CommunityPost.objects.filter(category=selected_category).order_by('-created_at')
    else:
        posts = CommunityPost.objects.all().order_by('-created_at')
        selected_category = '전체' 
    
    latest_log = AnalysisLog.objects.filter(user=request.user).order_by('-created_at').first()
    
    if latest_log and latest_log.predicted_category:
        user_deepest_category = latest_log.predicted_category
    else:
        user_deepest_category = "일반"
        
    context = {
        'posts': posts,
        'user_deepest_category': user_deepest_category,
        'selected_category': selected_category, 
    }
    
    return render(request, 'counseling/community_list.html', context)

@login_required
def community_write(request):
    if request.method == 'POST':
        category = request.POST.get('category')
        title = request.POST.get('title')
        content = request.POST.get('content')
        
        if title and content and category:
            CommunityPost.objects.create(
                user=request.user,
                category=category,  
                title=title,
                content=content
            )
            return redirect('community_list')
            
    categories = ['취업', '진로', '인간관계', '일반']
    return render(request, 'counseling/community_write.html', {'categories': categories})


@login_required
def community_detail(request, post_id):
    post = get_object_or_404(CommunityPost, id=post_id)
    return render(request, 'counseling/community_detail.html', {'post': post})

@login_required
def community_comment(request, post_id):
    if request.method == 'POST':
        post = get_object_or_404(CommunityPost, id=post_id)
        content = request.POST.get('content')
        CommunityComment.objects.create(post=post, user=request.user, content=content)
    return redirect('community_detail', post_id=post_id)


@login_required
def matching_chat(request):
    user_top_worry = get_user_top_worry(request.user)
    return render(request, 'counseling/matching_chat.html', {'room_name': user_top_worry})


# ==========================================================
# 🔄 [핵심 수정 & 신설] 실시간 대화 및 참여자 연동 API 존
# ==========================================================

# views.py 파일 위쪽에 ROOM_USERS 정의를 리스트 딕셔너리로 안전하게 변경
ROOM_USERS = {'취업': [], '진로': [], '인간관계': [], '일반': []}

@login_required
def chat_api(request):
    room = request.GET.get('room', '일반')
    current_user = request.user.username

    # 👥 유저가 대화창에 들어오거나 새로고침할 때 리스트에 없으면 추가
    if current_user not in ROOM_USERS[room]:
        ROOM_USERS[room].append(current_user)

    if request.method == 'POST':
        data = json.loads(request.body)
        msg_text = data.get('text', '').strip()
        if msg_text:
            msg_obj = {
                'user': current_user,
                'text': msg_text,
                'time': timezone.now().strftime('%H:%M:%S')
            }
            CHAT_ROOMS[room].append(msg_obj)
            if len(CHAT_ROOMS[room]) > 50:
                CHAT_ROOMS[room].pop(0)
        return JsonResponse({'status': 'success'})
        
    return JsonResponse({'messages': CHAT_ROOMS.get(room, [])})


@login_required
def room_users_api(request):
    """
    👥 현재 방에 들어와 있는 참여자 명단 목록을 프론트엔드로 안전하게 전달
    """
    room = request.GET.get('room', '일반')
    current_user = request.user.username
    
    # 💡 API를 호출하는 순간에도 혹시 누락되었다면 유저를 명단에 주입
    if current_user not in ROOM_USERS[room]:
        ROOM_USERS[room].append(current_user)
        
    user_list = ROOM_USERS.get(room, [])
    
    return JsonResponse({
        'users': user_list,
        'count': len(user_list)
    })


# ==========================================================
# 🗂️ 마이페이지 및 실시간 소모임 진입 뷰
# ==========================================================

@login_required
def my_page(request):
    recent_logs = AnalysisLog.objects.filter(user=request.user).order_by('-created_at')[:10]
    recent_logs = list(reversed(recent_logs))
    
    dates, anxiety, depression, urgency, growth, stability = [], [], [], [], [], []
    for log in recent_logs:
        dates.append(log.created_at.strftime('%m/%d'))
        anxiety.append(log.anxiety_score or 0)
        depression.append(log.depression_score or 0)
        urgency.append(log.urgency_score or 0)
        growth.append(log.growth_score or 0)
        stability.append(log.stability_score or 0)
        
    category_stats = AnalysisLog.objects.filter(user=request.user) \
                                        .values('predicted_category') \
                                        .annotate(count=Count('id'))
    
    categories = []
    counts = []
    for stat in category_stats:
        cat_name = stat['predicted_category'] if stat['predicted_category'] else '일반'
        categories.append(cat_name)
        counts.append(stat['count'])
        
    if not categories:
        categories = ['진단 데이터 없음']
        counts = [1]
        
    total_count = AnalysisLog.objects.filter(user=request.user).count()
    
    context = {
        'chart_dates': json.dumps(dates),
        'chart_anxiety': json.dumps(anxiety),
        'chart_depression': json.dumps(depression),
        'chart_urgency': json.dumps(urgency),
        'chart_growth': json.dumps(growth),
        'chart_stability': json.dumps(stability),
        
        'category_labels': json.dumps(categories),
        'category_counts': json.dumps(counts),
        
        'total_count': total_count,
        'recent_logs': recent_logs[:5], 
    }
    
    return render(request, 'counseling/my_page.html', context)

@login_required
def real_time_chat(request):
    latest_log = AnalysisLog.objects.filter(user=request.user).order_by('-created_at').first()
    
    if latest_log and latest_log.predicted_category:
        user_category = latest_log.predicted_category
    else:
        user_category = "일반"  
        
    context = {
        'user_category': user_category,
    }
    return render(request, 'counseling/real_time_chat.html', context)