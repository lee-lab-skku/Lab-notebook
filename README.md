# Lab Notebook

실험 사진/메모를 기록하고 로컬 LLM(Ollama)이 자동으로 분석·요약해주는 로컬 웹 앱.

## 설치 및 실행

```bash
cd lab-notebook
pip install -r requirements.txt
python app.py
```

브라우저 → http://localhost:5001

Ollama도 실행되어 있어야 함:
```bash
ollama serve
ollama run gemma4:31b
```

## 주요 기능

- **새 기록**: 실험 제목 + 메모 + 사진 드래그앤드롭 / 붙여넣기(Ctrl+V)
- **AI 분석**: 개별 기록에서 "AI 분석" 버튼 → Ollama가 요약 + 태그 + 다음 스텝 생성 (이미지 최대 6장)
- **Weekly 리포트**: 주차별 타임라인 + 핵심 결과 + 문제점 + 다음 주 계획 자동 생성
- **AI 채팅**: 연구 관련 질문 + SearXNG 웹검색 연동
- **라이트박스**: 사진 클릭 시 확대 보기

## 단축키

| 키 | 동작 |
|----|------|
| `n` | 새 기록 작성 |
| `Esc` | 모달 / 라이트박스 닫기 |

## 데이터 저장 위치

| 경로 | 내용 |
|------|------|
| `data/entries.json` | 모든 실험 기록 |
| `data/weekly_reports.json` | 캐시된 주간 리포트 |
| `uploads/` | 업로드된 사진 |

## 환경 변수

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `OLLAMA_MODEL` | `gemma4:31b` | 사용할 Ollama 모델 |
| `SEARXNG_URL` | `http://localhost:8888` | SearXNG 검색 엔진 주소 |

---

## 개발 지침

### 브랜치 전략

- `master` : 안정 버전 (직접 커밋 가능, 소규모 프로젝트)
- 큰 기능 추가 시 feature 브랜치 후 merge

### 개발 로그 작성 규칙

코드 변경 시 반드시 `development/` 폴더에 로그 파일 작성.

**파일명 규칙:**
```
development/dev_YYYYMMDD_HHMMSS.md
```

현재 시각 확인:
```powershell
Get-Date -Format yyyyMMdd_HHmmss
```

**로그 포함 내용:**
1. 작업 개요 (1-2줄 요약)
2. 각 변경 사항별: 문제 → 원인 → 수정 내용 (코드 diff 포함)
3. 변경 파일 요약 테이블

### GitHub 커밋/푸시 방법

#### GitHub Remote

```
https://github.com/lee-lab-skku/Lab-notebook
```

이미 설정 완료. 별도 설정 불필요.

#### 일반 커밋/푸시

```bash
cd "g:/다른 컴퓨터/SKKU 실험대/D/BIM LAB/취업준비-박사후연구원/성균관대학교/연구노트/lab-notebook"
git add -A
git commit -m "feat: 변경 내용 요약"
git push origin main
```

#### 커밋 메시지 컨벤션

| 접두어 | 용도 |
|--------|------|
| `feat:` | 새 기능 추가 |
| `fix:` | 버그 수정 |
| `refactor:` | 리팩토링 (기능 변경 없음) |
| `style:` | CSS/UI 변경 |
| `docs:` | 문서/주석 수정 |
| `chore:` | 설정, 의존성 등 기타 |

예시:
```
feat: 주간 리포트 항목 수 증가 및 레이아웃 50/50 고정
fix: 재생성 버튼 텍스트 고착 버그 수정
```

#### 자동 커밋/푸시 스크립트

`lab-notebook/` 루트에 `push.bat` 생성하여 사용:

```bat
@echo off
cd /d "g:\다른 컴퓨터\SKKU 실험대\D\BIM LAB\취업준비-박사후연구원\성균관대학교\연구노트"
git add lab-notebook/
git commit -m "%~1"
git push
echo Done.
pause
```

사용법:
```bat
push.bat "fix: 재생성 버튼 버그 수정"
```

### 주의사항

- `data/` 폴더 (entries.json, weekly_reports.json) 는 `.gitignore`에 추가 권장 (개인 연구 데이터)
- `uploads/` 폴더도 `.gitignore` 권장 (사진 파일 용량)
- 모델명(`OLLAMA_MODEL`) 변경 시 README 환경 변수 표 업데이트

### 개발 환경

- Python 3.11+
- Flask
- Ollama (gemma4:31b)
- SearXNG (선택, 웹검색 기능)
