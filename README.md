# 🔬 Lab Notebook

실험 사진/메모를 기록하고 Claude AI가 자동으로 분석·요약해주는 로컬 웹 앱.

## 설치

```bash
cd lab_notebook
pip install -r requirements.txt
```

## 실행

```bash
python app.py
```

브라우저에서 → http://localhost:5001

## 기능

- **새 기록**: 실험 제목 + 메모 + 사진 드래그앤드롭
- **AI 분석**: 저장 시 "저장 + AI 분석" 버튼으로 Claude가 자동 요약
- **Weekly 리포트**: 주차별 타임라인 + 핵심 결과 + 문제점 + 다음 주 계획
- **사진 뷰어**: 클릭하면 라이트박스로 확대 보기

## 단축키

- `n` : 새 기록 작성
- `Esc` : 모달/라이트박스 닫기

## 데이터 저장 위치

- `data/entries.json` : 모든 실험 기록
- `uploads/` : 업로드된 사진들

## 환경 변수

`ANTHROPIC_API_KEY`가 설정되어 있어야 AI 기능이 작동함.
Claude Code에서 실행 시 자동으로 설정됨.
