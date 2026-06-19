import os
import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline

# [변경 포인트] 자바 기반인 KoNLPy(Okt) 대신 
# 파이썬 기본 문자열 처리(공백 기준 띄어쓰기 및 단어 단위 분리)를 사용하는 토크나이저 정의
def simple_korean_tokenizer(text):
    # 문장 부호를 제거하고 공백 기준으로 단어를 분리
    clean_text = "".join([c for c in text if c.isalnum() or c.isspace()])
    return clean_text.split()

# 2. 기초 학습 데이터셋 (동일)
data = [
    # --- 취업 카테고리 ---
    ("요즘 하반기 공채 시즌인데 자소서 쓰기가 너무 막막해요.", "취업"),
    ("스펙이 부족한 것 같아서 인턴 지원해도 다 떨어질까 봐 걱정입니다.", "취업"),
    ("코딩 테스트 준비는 어떻게 해야 할지 대기업 포트폴리오 기준을 모르겠어요.", "취업"),
    ("면접만 가면 긴장해서 말을 제대로 못 하는데 면접 스터디를 해야 할까요?", "취업"),
    ("토익 점수랑 자격증 요구사항 맞추느라 하루 종일 학원만 다녀서 피곤해요.", "취업"),
    
    # --- 진로 (대학원/편입 등) 카테고리 ---
    ("학점이 낮아서 타 대학원 진학이 가능할지 전공 적성에 맞는지 의문입니다.", "진로"),
    ("지금 다니는 학교 전공이 마음에 안 들어서 일반 편입이나 학사 편입 생각 중이에요.", "진로"),
    ("졸업하고 바로 직장을 구해야 할지 아니면 석사 과정을 밟아야 할지 고민입니다.", "진로"),
    ("연구실 인턴을 해보고 싶은데 교수님께 컨택 이메일을 어떻게 보내야 하나요?", "진로"),
    ("진로를 아예 다른 분야로 전과하거나 복수전공 하려는데 학점 컷이 높을까요?", "진로"),
    
    # --- 인간관계 카테고리 ---
    ("팀플 조원들이 과제 참여를 안 하고 잠수를 타서 스트레스가 너무 심해요.", "인간관계"),
    ("동기들이랑 사소한 오해가 생겼는데 먼저 사과하기도 어색하고 소외감 느껴집니다.", "인간관계"),
    ("대학 와서 진짜 마음을 터놓고 얘기할 만한 진정한 친구를 못 사귄 것 같아요.", "인간관계"),
    ("동아리 선배들과의 관계가 너무 수직적이라 계속 활동해야 할지 고민입니다.", "인간관계"),
    ("룸메이트랑 생활 패턴이 너무 안 맞아서 기숙사 방을 바꾸고 싶어요.", "인간관계")
]

X_train = [text for text, label in data]
y_train = [label for text, label in data]

print("🎨 자바 없이 머신러닝 모델 학습을 시작합니다...")

# 3. 파이프라인 구축 (수정된 토크나이저 적용)
# 한 글자 단어(예: '봐', '한')도 분석에 포함되도록 token_pattern 설정을 조정합니다.
model_pipeline = Pipeline([
    ('tfidf', TfidfVectorizer(tokenizer=simple_korean_tokenizer, token_pattern=None, min_df=1)),
    ('clf', MultinomialNB())
])

# 4. 모델 학습 수행
model_pipeline.fit(X_train, y_train)
print("✅ 모델 학습 완료!")

# 5. 학습된 모델 및 파이프라인을 파일로 저장 (.pkl)
current_dir = os.path.dirname(os.path.abspath(__file__))
model_path = os.path.join(current_dir, 'worry_classifier.pkl')

joblib.dump(model_pipeline, model_path)
print(f"💾 모델 파일 저장 완료: {model_path}")

# 6. 간단한 자체 테스트
test_text = "자소서랑 면접 준비 때문에 잠을 못 자겠어요"
predicted = model_pipeline.predict([test_text])[0]
print(f"🔍 테스트 문장: '{test_text}' -> 예측된 고민 카테고리: [{predicted}]")