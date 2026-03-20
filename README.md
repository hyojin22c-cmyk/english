# 영어 세특 주제 추천 챗봇

## 설치 및 실행

```bash
pip install streamlit google-generativeai
streamlit run app.py
```

## 사용법

### 선생님 (지문 관리)
1. "⚙️ 지문 관리" 탭 클릭
2. 비밀번호 입력 (기본값: teacher1234)
3. 지문 제목, 학년, 핵심 키워드, 요약 입력 후 추가
4. 불필요한 지문은 삭제 버튼으로 제거

### 학생 (주제 추천)
1. "📝 주제 추천받기" 탭 클릭
2. 학년, 희망 진로/학과, 관심 분야 입력
3. "✨ 추천 받기" 버튼 클릭
4. 결과를 txt 파일로 저장 가능

## 파일 구조

```
app.py              ← 메인 앱
passages.json       ← 지문 데이터 (자동 생성)
secrets.toml.example ← API 키 설정 예시
.streamlit/
  secrets.toml      ← 실제 API 키 (직접 생성 필요)
```
