# counseling/models.py
from django.db import models
from django.contrib.auth.models import User
from django.conf import settings  # 💡 django.conf 로 변경!

class Question(models.Model):
    CATEGORY_CHOICES = [
        ('취업', '취업'),
        ('진로', '진로'),
        ('인간관계', '인간관계'),
    ]
    category = models.CharField(max_length=10, choices=CATEGORY_CHOICES)
    content = models.TextField()

    def __str__(self):
        return f"[{self.category}] {self.content[:30]}"

class Quote(models.Model):
    content = models.TextField()
    author = models.CharField(max_length=50, default="작자 미상")

    def __str__(self):
        return f"\"{self.content[:20]}\" - {self.author}"

class AnalysisLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    chosen_question = models.TextField()
    user_answer = models.TextField()
    predicted_category = models.CharField(max_length=20)
    ai_solution = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    # 💡 [졸업작품 알고리즘 핵심 컬럼 추가]
    # 1. 자체 감정 스코어링 지수 (0 ~ 100점)
    anxiety_score = models.IntegerField(default=0, verbose_name="불안 지수")
    urgency_score = models.IntegerField(default=0, verbose_name="조급 지수")
    depression_score = models.IntegerField(default=0, verbose_name="우울 지수")
    # 💡 [긍정 감정 점수 컬럼 추가]
    growth_score = models.IntegerField(default=0, verbose_name="성장 의지 지수")
    stability_score = models.IntegerField(default=0, verbose_name="안정/감사 지수")
    
    # 2. RAG 기반 매칭된 교내 가이드라인 수록
    matched_guide = models.TextField(blank=True, null=True, verbose_name="매칭된 내부 가이드라인")

    def __str__(self):
        return f"[{self.user.username}] {self.predicted_category} 상담 ({self.created_at.strftime('%Y-%m-%d')})"
    
    # counseling/models.py 맨 아래에 추가

class CommunityPost(models.Model):
    CATEGORY_CHOICES = [
        ('취업', '취업'),
        ('진로', '진로'),
        ('인간관계', '인간관계'),
        ('일반', '일반'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    category = models.CharField(max_length=10, choices=CATEGORY_CHOICES)
    title = models.CharField(max_length=200, verbose_name="제목")
    content = models.TextField(verbose_name="내용")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"[{self.category}] {self.title[:20]}"

class CommunityComment(models.Model):
    post = models.ForeignKey(CommunityPost, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField(verbose_name="댓글 내용")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username}의 댓글 - {self.content[:10]}"