"""
Lab Notebook - Local web app for experiment logging
Run: python app.py
"""

import os
import re
import json
import uuid
import base64
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from flask import Flask, request, jsonify, send_from_directory, send_file
from openai import OpenAI

app = Flask(__name__, static_folder='static', template_folder='templates')

BASE_DIR = Path(__file__).parent
DATA_FILE = BASE_DIR / 'data' / 'entries.json'
WEEKLY_FILE = BASE_DIR / 'data' / 'weekly_reports.json'
UPLOADS_DIR = BASE_DIR / 'uploads'
DATA_FILE.parent.mkdir(exist_ok=True)
UPLOADS_DIR.mkdir(exist_ok=True)

def load_weekly_reports():
    if WEEKLY_FILE.exists():
        with open(WEEKLY_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_weekly_reports(reports):
    with open(WEEKLY_FILE, 'w', encoding='utf-8') as f:
        json.dump(reports, f, ensure_ascii=False, indent=2)

# Ollama 로컬 LLM 클라이언트
OLLAMA_MODEL = os.getenv('OLLAMA_MODEL', 'gemma4:31b')

# 연구자 맞춤 시스템 프롬프트
SYSTEM_PROMPT = """당신은 고려대학교 바이오의공학과 소속 박사후연구원(김규남)의 실험 노트 분석 AI 어시스턴트입니다.

[연구자 프로필]
- 전공: DLP/볼류메트릭 3D 프린팅, 라디칼/양이온 하이브리드 광중합, PIPS 기반 미세구조 제어, 경사기능재료
- 현재 주요 연구: YBCO 세라믹 슬러리 DLP 프린팅 (초전도체 다공성 구조체 제작)
- 진행 중 과제: 박사후국내연수 제안서 준비 (성균관대 기계공학과 이준 교수 연구실, 볼류메트릭 3D 프린팅)
- 주요 관심 변수: 노광시간(exposure time), 경화깊이(cure depth), 오버큐어링(overcuring), 적층 불량, FEP 필름 밀착, 슬러리 점도, PMMA 기공제 비율, 소결 조건

[분석 스타일 지침]
- 연구 노트 분석 시 해당 연구 맥락(DLP 세라믹/초전도체 프린팅)을 항상 염두에 둘 것
- 수치 데이터(μm, vol%, mJ/cm², s 등)는 정확히 인용하고 의미를 해석할 것
- 다음 실험 제안은 현재 연구 흐름에 맞게 구체적으로 제시할 것
- 태그는 연구 키워드 중심으로 (DLP, YBCO, overcuring, cure_depth, PMMA, sintering 등)
- 한국어로 간결하게 작성, 전문 용어는 영문 병기 허용
- JSON 형식으로만 응답, 다른 말 없이"""
client = OpenAI(base_url='http://localhost:11434/v1', api_key='ollama')


def load_entries():
    if DATA_FILE.exists():
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []


def save_entries(entries):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)


# ── Static & Index ──────────────────────────────────────────────────────────

@app.route('/')
def index():
    return send_from_directory('templates', 'index.html')


@app.route('/uploads/<path:filename>')
def serve_upload(filename):
    return send_from_directory(UPLOADS_DIR, filename)


# ── Entries CRUD ────────────────────────────────────────────────────────────

@app.route('/api/entries', methods=['GET'])
def get_entries():
    entries = load_entries()
    entries.sort(key=lambda x: x['created_at'], reverse=True)
    return jsonify(entries)


@app.route('/api/entries', methods=['POST'])
def create_entry():
    data = request.json
    entry = {
        'id': str(uuid.uuid4()),
        'title': data.get('title', ''),
        'memo': data.get('memo', ''),
        'tags': data.get('tags', []),
        'images': data.get('images', []),
        'ai_summary': '',
        'created_at': data.get('created_at', datetime.now().isoformat()),
        'date': data.get('date', datetime.now().strftime('%Y-%m-%d')),
        'week': _get_week_label(datetime.fromisoformat(data['date']) if 'date' in data else datetime.now()),
    }
    entries = load_entries()
    entries.append(entry)
    save_entries(entries)
    return jsonify(entry), 201


@app.route('/api/entries/<entry_id>', methods=['PUT'])
def update_entry(entry_id):
    data = request.json
    entries = load_entries()
    for e in entries:
        if e['id'] == entry_id:
            e.update({k: v for k, v in data.items() if k != 'id'})
            save_entries(entries)
            return jsonify(e)
    return jsonify({'error': 'not found'}), 404


@app.route('/api/entries/<entry_id>', methods=['DELETE'])
def delete_entry(entry_id):
    entries = load_entries()
    entries = [e for e in entries if e['id'] != entry_id]
    save_entries(entries)
    return jsonify({'ok': True})


# ── Image Upload ────────────────────────────────────────────────────────────

@app.route('/api/upload', methods=['POST'])
def upload_image():
    if 'file' not in request.files:
        return jsonify({'error': 'no file'}), 400
    f = request.files['file']
    ext = Path(f.filename).suffix.lower()
    if ext not in {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp'}:
        return jsonify({'error': 'unsupported format'}), 400
    filename = f'{uuid.uuid4().hex}{ext}'
    dest = UPLOADS_DIR / filename
    f.save(dest)
    return jsonify({'filename': filename, 'url': f'/uploads/{filename}'})


# ── AI Features ─────────────────────────────────────────────────────────────

@app.route('/api/ai/summarize', methods=['POST'])
def ai_summarize():
    """Summarize a single entry using Ollama (multimodal)."""
    data = request.json
    memo = data.get('memo', '')
    title = data.get('title', '')
    images = data.get('images', [])

    # Ollama OpenAI 호환 형식: 이미지는 image_url 타입 (base64)
    content_parts = []

    for img_url in images[:3]:
        img_path = UPLOADS_DIR / Path(img_url).name
        if img_path.exists():
            with open(img_path, 'rb') as f:
                img_data = base64.standard_b64encode(f.read()).decode('utf-8')
            ext = img_path.suffix.lower().lstrip('.')
            media_type = 'image/jpeg' if ext in ('jpg', 'jpeg') else f'image/{ext}'
            content_parts.append({
                'type': 'image_url',
                'image_url': {'url': f'data:{media_type};base64,{img_data}'}
            })

    content_parts.append({
        'type': 'text',
        'text': (
            f"다음 실험 노트를 분석하고 JSON으로만 응답해줘 (한국어). 다른 말 없이 JSON만.\n\n"
            f"제목: {title or '(없음)'}\n메모: {memo}\n\n"
            "응답 형식:\n"
            "{\n"
            '  "title": "제목이 없으면 메모 내용 기반으로 간결한 실험 제목 생성, 있으면 그대로",\n'
            '  "summary": "2-3문장 핵심 요약",\n'
            '  "key_findings": ["발견1", "발견2"],\n'
            '  "suggested_tags": ["태그1", "태그2"],\n'
            '  "next_steps": "다음에 해볼 것"\n'
            "}"
        )
    })

    import time
    t0 = time.time()
    print(f"[AI] 모델: {OLLAMA_MODEL} | 분석 시작...")
    try:
        resp = client.chat.completions.create(
            model=OLLAMA_MODEL,
            messages=[
                {'role': 'system', 'content': SYSTEM_PROMPT},
                {'role': 'user', 'content': content_parts}
            ],
            max_tokens=4096,
        )
        elapsed = time.time() - t0
        raw = resp.choices[0].message.content or ''
        print(f"[AI] 완료 {elapsed:.1f}s | 모델: {OLLAMA_MODEL} | 응답 {len(raw)}자")
        print(f"[RAW]\n{raw[:600]}\n---")
        text = raw.strip()
        # thinking 블록 제거
        text = re.sub(r'(?s)^Thinking\.\.\..*?\.\.\.done thinking\.\n*', '', text).strip()
        # 코드펜스 제거
        text = re.sub(r'^```(?:json)?\s*\n?', '', text, flags=re.MULTILINE)
        text = re.sub(r'\n?```\s*$', '', text, flags=re.MULTILINE).strip()
        # JSON 블록만 추출
        m = re.search(r'\{.*\}', text, re.DOTALL)
        if m:
            text = m.group(0)
        result = json.loads(text)
        return jsonify(result)
    except Exception as e:
        elapsed = time.time() - t0
        import traceback
        traceback.print_exc()
        print(f"[AI ERROR] {elapsed:.1f}s 후 실패: {e}")
        return jsonify({'error': str(e)}), 500



@app.route('/api/ai/weekly/cache', methods=['GET'])
def get_weekly_cache():
    """캐시된 weekly report만 반환. 없으면 404."""
    week = request.args.get('week')
    if not week:
        return jsonify({'error': 'week required'}), 400
    reports = load_weekly_reports()
    if week in reports:
        return jsonify(reports[week])
    return jsonify({'error': 'not cached'}), 404


@app.route('/api/ai/weekly', methods=['POST'])
def ai_weekly():
    """Generate (or load cached) weekly report."""
    data = request.json
    week = data.get('week')
    force = data.get('force', False)  # force=True면 재생성
    entries = load_entries()

    if week:
        week_entries = [e for e in entries if e.get('week') == week]
    else:
        current_week = _get_week_label(datetime.now())
        week_entries = [e for e in entries if e.get('week') == current_week]
        week = current_week

    if not week_entries:
        return jsonify({'error': 'no entries for this week'}), 404

    # 캐시된 리포트 있으면 바로 반환 (force=True면 재생성)
    reports = load_weekly_reports()
    if week in reports and not force:
        print(f"[WEEKLY] 캐시 반환: {week}")
        return jsonify(reports[week])

    # 이전 주차 리포트에서 next_week 가져오기
    reports = load_weekly_reports()
    prev_next_week = None

    # 이전 주차 계산
    import re as _re
    wm = _re.match(r'(\d{4})-W(\d+)', week)
    if wm:
        yr, wn = int(wm.group(1)), int(wm.group(2))
        if wn == 1:
            prev_week = f"{yr-1}-W52"
        else:
            prev_week = f"{yr}-W{wn-1:02d}"
        if prev_week in reports:
            prev_next_week = reports[prev_week].get('next_week', [])

    # 프롬프트 구성
    entries_text = ''
    for e in week_entries:
        entries_text += f"\n---\n날짜: {e['date']}\n제목: {e['title']}\n메모: {e['memo']}\nAI요약: {e.get('ai_summary','')}\n"

    prev_plan_text = ''
    if prev_next_week:
        prev_plan_text = f"\n\n[지난 주 계획 ({prev_week})]\n" + '\n'.join(f'- {p}' for p in prev_next_week)
        prev_plan_text += "\n\n위 지난 주 계획 대비 이번 주 달성률을 0-100 사이 정수로 progress_score에 넣어줘."
        has_prev = True
    else:
        has_prev = False

    prompt = (
        f"주간({week}) 실험 노트들을 분석해서 JSON으로 응답해줘 (한국어).\n\n"
        f"{entries_text}{prev_plan_text}\n\n"
        "분류 기준:\n"
        "- main_research: DLP 프린팅, YBCO, 세라믹, 슬러리, 광중합, 볼류메트릭, 소결, 경화 관련 실험\n"
        "- side_quest: 코딩, 소프트웨어 개발, 제안서 작성, 행정, 기타 비실험 작업\n\n"
        "응답 형식 (JSON만, 백틱 없이):\n"
        "{\n"
        "  \"week_summary\": \"이번 주 전체 요약 3-4문장 (main_research 중심)\",\n"
        "  \"timeline\": [{\"date\": \"날짜\", \"headline\": \"한줄요약\", \"type\": \"main_research 또는 side_quest\"}],\n"
        "  \"key_results\": [\"핵심 결과1\", \"핵심 결과2\"],\n"
        "  \"problems\": [\"문제점1\"],\n"
        "  \"next_week\": [\"다음 주 할 것1\", \"다음 주 할 것2\"],\n"
        "  \"side_quests\": [\"side quest 항목1\"],\n" +
        ("  \"progress_score\": 75,\n  \"progress_basis\": \"달성률 근거 한 문장 (main_research만 기준)\",\n" if has_prev else "  \"progress_score\": null,\n") +
        "  \"has_side_quest\": true\n"
        "}"
    )

    import time as _time
    t0 = _time.time()
    try:
        print(f"[WEEKLY] 모델: {OLLAMA_MODEL} | {week} 생성 시작... ({len(week_entries)}개 기록)")
        resp = client.chat.completions.create(
            model=OLLAMA_MODEL,
            messages=[
                {'role': 'system', 'content': SYSTEM_PROMPT},
                {'role': 'user', 'content': prompt}
            ],
            max_tokens=16384,
        )
        elapsed = _time.time() - t0
        text = resp.choices[0].message.content.strip()
        print(f"[WEEKLY] 완료 {elapsed:.1f}s | 모델: {OLLAMA_MODEL} | 응답 {len(text)}자")
        # thinking 블록 제거
        text = re.sub(r'(?s)^Thinking\.\.\..*?\.\.\.done thinking\.\n*', '', text).strip()
        # 코드펜스 제거
        text = re.sub(r'^```(?:json)?\s*\n?', '', text, flags=re.MULTILINE)
        text = re.sub(r'\n?```\s*$', '', text, flags=re.MULTILINE).strip()
        # JSON 블록만 추출
        m = re.search(r'\{.*\}', text, re.DOTALL)
        if m:
            text = m.group(0)
        result = json.loads(text)
        result['week'] = week
        result['entry_count'] = len(week_entries)
        result['generated_at'] = datetime.now().isoformat()
        # 이전 주차 없으면 progress_score 강제 제거
        if not has_prev:
            result.pop('progress_score', None)
            result.pop('progress_basis', None)

        # 저장
        reports[week] = result
        save_weekly_reports(reports)
        print(f"[WEEKLY] 저장 완료: {week}")
        return jsonify(result)
    except Exception as e:
        elapsed = _time.time() - t0
        import traceback
        traceback.print_exc()
        print(f"[WEEKLY ERROR] {elapsed:.1f}s 후 실패: {e}")
        return jsonify({'error': str(e)}), 500


# ── Utilities ────────────────────────────────────────────────────────────────

def _get_week_label(dt: datetime) -> str:
    return dt.strftime('%G-W%V')


@app.route('/api/weeks', methods=['GET'])
def get_weeks():
    entries = load_entries()
    weeks = sorted(set(e.get('week', '') for e in entries if e.get('week')), reverse=True)
    return jsonify(weeks)


if __name__ == '__main__':
    print("🔬 Lab Notebook 시작 → http://localhost:5001")
    app.run(debug=True, port=5001)
