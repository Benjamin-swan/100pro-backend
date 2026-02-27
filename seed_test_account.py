"""
test@test.com 계정에 캘린더 시드 데이터를 백엔드 DB에 등록하는 스크립트.
이미 태스크가 존재하면 중복 생성하지 않는다.
"""
import httpx
from datetime import datetime, timedelta

BASE_URL = "http://localhost:8000"

# 1. 로그인
login_res = httpx.post(f"{BASE_URL}/auth/login", json={"email": "test@test.com", "password": "password123"})
if login_res.status_code != 200:
    print(f"로그인 실패: {login_res.text}")
    exit(1)

token = login_res.json()["access_token"]
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
print("로그인 성공")

# 2. 기존 태스크 확인 (중복 방지)
existing_res = httpx.get(f"{BASE_URL}/tasks", headers=headers)
archive_res = httpx.get(f"{BASE_URL}/tasks/archive", headers=headers)
existing_titles = set()
for t in existing_res.json():
    existing_titles.add(t["title"])
for t in archive_res.json():
    existing_titles.add(t["title"])

print(f"기존 태스크 {len(existing_titles)}개 발견")

now = datetime.now()
today = now.replace(hour=0, minute=0, second=0, microsecond=0)

def days_ago(n, hour=9, minute=30):
    d = today - timedelta(days=n)
    return d.replace(hour=hour, minute=minute).isoformat()

def fixed_date(year, month, day, hour=9, minute=30):
    return datetime(year, month, day, hour, minute).isoformat()

# 시드 태스크 정의: (title, description, due_date, isDone, is_archived)
seed_tasks = [
    # 2/16 ~ 2/21 캘린더 스티커 0~5단계 표시용
    ("2/16 할 일 1", "스티커 0단계", fixed_date(2026, 2, 16, 9, 0), False, False),

    ("2/17 할 일 1", "스티커 1단계", fixed_date(2026, 2, 17, 9, 0), True, False),

    ("2/18 할 일 1", "스티커 2단계", fixed_date(2026, 2, 18, 9, 0), True, False),
    ("2/18 할 일 2", "스티커 2단계", fixed_date(2026, 2, 18, 10, 0), True, False),

    ("2/19 할 일 1", "스티커 3단계", fixed_date(2026, 2, 19, 9, 0), True, False),
    ("2/19 할 일 2", "스티커 3단계", fixed_date(2026, 2, 19, 10, 0), True, False),
    ("2/19 할 일 3", "스티커 3단계", fixed_date(2026, 2, 19, 11, 0), True, False),

    ("2/20 할 일 1", "스티커 4단계", fixed_date(2026, 2, 20, 9, 0), True, False),
    ("2/20 할 일 2", "스티커 4단계", fixed_date(2026, 2, 20, 10, 0), True, False),
    ("2/20 할 일 3", "스티커 4단계", fixed_date(2026, 2, 20, 11, 0), True, False),
    ("2/20 할 일 4", "스티커 4단계", fixed_date(2026, 2, 20, 12, 0), True, False),

    ("2/21 할 일 1", "스티커 5단계", fixed_date(2026, 2, 21, 9, 0), True, False),
    ("2/21 할 일 2", "스티커 5단계", fixed_date(2026, 2, 21, 10, 0), True, False),
    ("2/21 할 일 3", "스티커 5단계", fixed_date(2026, 2, 21, 11, 0), True, False),
    ("2/21 할 일 4", "스티커 5단계", fixed_date(2026, 2, 21, 12, 0), True, False),
    ("2/21 할 일 5", "스티커 5단계", fixed_date(2026, 2, 21, 13, 0), True, False),

    # 어제
    ("프로젝트 기획안 정리", "핵심 요구사항/범위/리스크 항목까지 문서화", days_ago(1, 9, 20), False, False),
    ("팀 회의록 작성", "결정사항과 담당자 액션 아이템 정리 완료", days_ago(1, 11, 15), True, False),
    ("발표 리허설", "타이밍 체크까지 마무리", days_ago(1, 13, 50), True, False),
    ("자료 백업", "백업 데이터는 필요 시 오늘 할 일로 다시 지정", days_ago(1, 16, 40), False, True),

    # 2일 전
    ("주간 목표 정리", "이번 주 반드시 끝낼 일 3개 우선순위로 선정", days_ago(2, 9, 10), False, False),
    ("고객 문의 답변", "오전 문의 2건 답변 완료", days_ago(2, 10, 45), False, False),
    ("초안 검토", "2월 22일 초안 1차 검토 완료", days_ago(2, 11, 20), True, False),
    ("참고 링크 정리", "지금은 보류, 필요하면 오늘 할 일로 재지정", days_ago(2, 15, 40), False, True),

    # 오늘
    ("고객 미팅 준비", "발표 자료 최종 점검하고 질문 리스트 정리하기", days_ago(0, 10, 0), False, False),
]

created = 0
skipped = 0

for title, desc, due_date, is_done, is_archived in seed_tasks:
    if title in existing_titles:
        skipped += 1
        continue

    # 태스크 생성
    create_res = httpx.post(
        f"{BASE_URL}/tasks",
        headers=headers,
        json={"title": title, "description": desc, "due_date": due_date},
    )
    if create_res.status_code != 201:
        print(f"  생성 실패 [{title}]: {create_res.text}")
        continue

    task_id = create_res.json()["id"]

    # 완료 상태 업데이트
    patch_body = {}
    if is_done:
        patch_body["status"] = "completed"
    if is_archived:
        patch_body["is_archived"] = True

    if patch_body:
        patch_res = httpx.patch(
            f"{BASE_URL}/tasks/{task_id}",
            headers=headers,
            json=patch_body,
        )
        if patch_res.status_code != 200:
            print(f"  업데이트 실패 [{title}]: {patch_res.text}")

    status_str = ("완료" if is_done else "진행") + (" / 보관" if is_archived else "")
    print(f"  생성: {title} ({status_str})")
    created += 1

print(f"\n완료: {created}개 생성, {skipped}개 스킵(중복)")
