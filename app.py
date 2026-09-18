import json
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import streamlit as st


DATA_PATH = Path(__file__).parent / "data" / "tenders.json"

STATUS_LABELS = {
    "open": "진행 중",
    "closing_soon": "마감 임박",
    "closed": "마감",
}

STATUS_COLORS = {
    "open": "green",
    "closing_soon": "orange",
    "closed": "gray",
}

SAMPLE_TENDERS: list[dict[str, Any]] = [
    {
        "id": "TND-2026-004",
        "title": "스마트시티 통합 관제 플랫폼 구축 사업",
        "country": "싱가포르",
        "agency": "Singapore GovTech",
        "category": "IT · 디지털",
        "status": "closing_soon",
        "deadline": "2026-09-26",
        "budget": "SGD 4.8M",
        "procedure": "공개경쟁입찰",
        "description": "도시 전역의 교통, 안전, 환경 데이터를 통합하는 클라우드 기반 관제 플랫폼 구축 사업입니다.",
        "requirements": "유사 규모 공공 프로젝트 5년 이상 수행 경험, ISO 27001 인증 보유, 현지 파트너사 참여",
        "contact": "procurement@govtech.gov.sg",
        "notice_url": "https://www.gebiz.gov.sg/",
        "created_at": "2026-09-17",
    },
    {
        "id": "TND-2026-003",
        "title": "해상풍력 발전단지 해저케이블 공급 및 설치",
        "country": "영국",
        "agency": "Crown Estate",
        "category": "에너지 · 인프라",
        "status": "open",
        "deadline": "2026-10-18",
        "budget": "GBP 82M",
        "procedure": "제한경쟁입찰",
        "description": "북해 해상풍력 발전단지와 육상 변전소를 연결하는 해저케이블의 설계, 공급, 설치 사업입니다.",
        "requirements": "해저케이블 설치 실적, 해상 작업선 보유 또는 임차 계획, 환경영향평가 준수",
        "contact": "tenders@thecrownestate.co.uk",
        "notice_url": "https://www.find-tender.service.gov.uk/",
        "created_at": "2026-09-13",
    },
    {
        "id": "TND-2026-002",
        "title": "공공병원 의료장비 현대화 프로그램",
        "country": "사우디아라비아",
        "agency": "Ministry of Health",
        "category": "의료 · 헬스케어",
        "status": "open",
        "deadline": "2026-11-03",
        "budget": "SAR 145M",
        "procedure": "국제경쟁입찰",
        "description": "주요 공공병원의 영상진단 및 수술 장비를 교체하고 유지보수 체계를 구축합니다.",
        "requirements": "의료기기 제조사 또는 공식 대리점, 현지 서비스센터 운영 계획, 제품 인증서",
        "contact": "tenders@moh.gov.sa",
        "notice_url": "https://www.moh.gov.sa/",
        "created_at": "2026-09-11",
    },
    {
        "id": "TND-2026-001",
        "title": "도시철도 3호선 신호시스템 개량 사업",
        "country": "캐나다",
        "agency": "Metrolinx",
        "category": "교통 · 물류",
        "status": "open",
        "deadline": "2026-10-07",
        "budget": "CAD 31.5M",
        "procedure": "공개경쟁입찰",
        "description": "노후 도시철도 구간의 열차제어 및 신호시스템을 최신 표준으로 개량하는 사업입니다.",
        "requirements": "철도 신호시스템 설계·시공 자격, 북미 철도 프로젝트 실적, 안전관리계획서",
        "contact": "procurement@metrolinx.com",
        "notice_url": "https://www.metrolinx.com/",
        "created_at": "2026-09-08",
    },
    {
        "id": "TND-2025-118",
        "title": "국가 전자조달 시스템 운영 및 유지보수",
        "country": "베트남",
        "agency": "Ministry of Planning and Investment",
        "category": "IT · 디지털",
        "status": "closed",
        "deadline": "2026-09-16",
        "budget": "USD 6.2M",
        "procedure": "국제경쟁입찰",
        "description": "국가 전자조달 시스템의 24시간 운영, 보안 모니터링, 기능 개선을 담당합니다.",
        "requirements": "전자정부 시스템 운영 경험, 보안관제 조직, 베트남 현지 법인 또는 파트너",
        "contact": "bid@mppi.gov.vn",
        "notice_url": "https://muasamcong.mpi.gov.vn/",
        "created_at": "2026-08-29",
    },
    {
        "id": "TND-2025-117",
        "title": "수자원 정화시설 확장 및 시운전",
        "country": "호주",
        "agency": "Water Corporation",
        "category": "환경 · 수자원",
        "status": "closed",
        "deadline": "2026-09-12",
        "budget": "AUD 19.7M",
        "procedure": "공개경쟁입찰",
        "description": "서부 지역 정수 처리용량 확대를 위한 플랜트 증설과 시운전 사업입니다.",
        "requirements": "수처리 플랜트 EPC 실적, 호주 건설안전 기준 준수, 현지 기술인력 확보",
        "contact": "contracts@watercorporation.com.au",
        "notice_url": "https://www.watercorporation.com.au/",
        "created_at": "2026-08-21",
    },
]


def ensure_data_file() -> None:
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not DATA_PATH.exists():
        DATA_PATH.write_text(
            json.dumps(SAMPLE_TENDERS, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


def load_tenders() -> list[dict[str, Any]]:
    ensure_data_file()
    try:
        records = json.loads(DATA_PATH.read_text(encoding="utf-8"))
        return records if isinstance(records, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def save_tenders(tenders: list[dict[str, Any]]) -> None:
    ensure_data_file()
    DATA_PATH.write_text(
        json.dumps(tenders, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def parse_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def format_date(value: str) -> str:
    return parse_date(value).strftime("%Y.%m.%d")


def days_until(value: str) -> int:
    return (parse_date(value) - date.today()).days


def next_id(tenders: list[dict[str, Any]]) -> str:
    year = date.today().year
    numbers = []
    for tender in tenders:
        try:
            numbers.append(int(str(tender.get("id", "")).split("-")[-1]))
        except ValueError:
            continue
    return f"TND-{year}-{max(numbers, default=0) + 1:03d}"


def render_status(status: str) -> None:
    st.markdown(
        f":{STATUS_COLORS.get(status, 'gray')}[{STATUS_LABELS.get(status, status)}]"
    )


def tender_matches(tender: dict[str, Any], keyword: str, countries: list[str], category: str, status: str) -> bool:
    searchable = " ".join(
        str(tender.get(field, ""))
        for field in ("title", "country", "agency", "category", "description")
    ).lower()
    if keyword and keyword.lower() not in searchable:
        return False
    if countries and tender.get("country") not in countries:
        return False
    if category != "전체" and tender.get("category") != category:
        return False
    if status != "전체" and STATUS_LABELS.get(tender.get("status")) != status:
        return False
    return True


def show_overview(tenders: list[dict[str, Any]]) -> None:
    st.title("해외 입찰공고 관리")
    st.caption("글로벌 사업 기회를 한 곳에서 발견하고, 중요한 마감일을 놓치지 마세요.")

    active = [t for t in tenders if t.get("status") != "closed"]
    closing_soon = [t for t in active if 0 <= days_until(t["deadline"]) <= 14]
    countries = len({t.get("country") for t in tenders})

    metric_cols = st.columns(4)
    metric_cols[0].metric("전체 공고", f"{len(tenders):,}", "로컬 데이터")
    metric_cols[1].metric("진행 중", f"{len(active):,}", "지원 가능한 기회")
    metric_cols[2].metric("마감 임박", f"{len(closing_soon):,}", "14일 이내")
    metric_cols[3].metric("등록 국가", f"{countries:,}", "국가 기준")

    st.divider()
    st.subheader("공고 목록")

    with st.container(border=True):
        search_col, status_col, country_col, category_col = st.columns([2.3, 1, 1.2, 1.3])
        keyword = search_col.text_input(
            "검색",
            placeholder="사업명, 발주기관, 국가 검색",
            label_visibility="collapsed",
        )
        status = status_col.selectbox("상태", ["전체", "진행 중", "마감 임박", "마감"], label_visibility="collapsed")
        all_countries = sorted({str(t.get("country", "")) for t in tenders if t.get("country")})
        countries_filter = country_col.multiselect(
            "국가",
            all_countries,
            placeholder="국가 선택",
            label_visibility="collapsed",
        )
        categories = ["전체"] + sorted({str(t.get("category", "")) for t in tenders if t.get("category")})
        category = category_col.selectbox("분야", categories, label_visibility="collapsed")

    filtered = [
        tender for tender in tenders
        if tender_matches(tender, keyword, countries_filter, category, status)
    ]
    filtered.sort(key=lambda item: item.get("deadline", "9999-12-31"))
    st.caption(f"{len(filtered)}개의 공고가 검색되었습니다.")

    if not filtered:
        st.info("조건에 맞는 입찰공고가 없습니다. 검색어나 필터를 바꿔보세요.")
        return

    for tender in filtered:
        with st.container(border=True):
            top_left, top_right = st.columns([4, 1])
            with top_left:
                st.markdown(f"#### {tender['title']}")
                st.caption(f"{tender['id']}  ·  {tender['country']}  ·  {tender['agency']}")
            with top_right:
                render_status(tender["status"])

            info_cols = st.columns([1.2, 1.1, 1.1, 1.1])
            info_cols[0].markdown(f"**마감일**  \n{format_date(tender['deadline'])}")
            info_cols[1].markdown(f"**예산**  \n{tender.get('budget', '-')}")
            info_cols[2].markdown(f"**분야**  \n{tender.get('category', '-')}")
            remaining = days_until(tender["deadline"])
            remaining_label = "마감" if remaining < 0 else ("오늘" if remaining == 0 else f"D-{remaining}")
            info_cols[3].markdown(f"**남은 기간**  \n{remaining_label}")

            st.write(tender.get("description", ""))
            if st.button("상세 보기", key=f"detail-{tender['id']}", use_container_width=False):
                st.session_state["selected_tender_id"] = tender["id"]
                st.session_state["page"] = "detail"
                st.rerun()


def show_detail(tenders: list[dict[str, Any]], tender_id: str) -> None:
    tender = next((item for item in tenders if item.get("id") == tender_id), None)
    if not tender:
        st.warning("해당 입찰공고를 찾을 수 없습니다.")
        if st.button("목록으로 돌아가기"):
            st.session_state["page"] = "list"
            st.rerun()
        return

    if st.button("← 목록으로 돌아가기"):
        st.session_state["page"] = "list"
        st.rerun()

    st.title(tender["title"])
    st.caption(f"{tender['id']}  ·  등록일 {format_date(tender.get('created_at', date.today().isoformat()))}")
    render_status(tender["status"])
    st.divider()

    summary_cols = st.columns(4)
    summary_cols[0].markdown(f"**발주 국가**  \n{tender.get('country', '-')}")
    summary_cols[1].markdown(f"**발주 기관**  \n{tender.get('agency', '-')}")
    summary_cols[2].markdown(f"**입찰 분야**  \n{tender.get('category', '-')}")
    summary_cols[3].markdown(f"**마감일**  \n{format_date(tender['deadline'])}")

    st.subheader("사업 개요")
    st.write(tender.get("description", "-"))

    detail_left, detail_right = st.columns(2)
    with detail_left:
        st.subheader("입찰 정보")
        st.write(f"**예상 예산:** {tender.get('budget', '-')}")
        st.write(f"**입찰 방식:** {tender.get('procedure', '-')}")
        st.write(f"**남은 기간:** {'마감' if days_until(tender['deadline']) < 0 else f'D-{days_until(tender['deadline'])}'}")
    with detail_right:
        st.subheader("문의 및 원문")
        st.write(f"**문의:** {tender.get('contact', '-')}")
        if tender.get("notice_url"):
            st.link_button("공고 원문 열기", tender["notice_url"])

    st.subheader("참가 요건")
    st.info(tender.get("requirements", "-"))


def show_create(tenders: list[dict[str, Any]]) -> None:
    st.title("새 입찰공고 등록")
    st.caption("공고 원문을 확인한 뒤 핵심 정보를 기록해 팀의 검토 목록에 추가하세요.")

    with st.form("new-tender-form", clear_on_submit=False):
        st.subheader("기본 정보")
        title = st.text_input("사업명 *", placeholder="예: 국가 스마트그리드 운영센터 구축")
        col1, col2 = st.columns(2)
        country = col1.text_input("발주 국가 *", placeholder="예: 독일")
        agency = col2.text_input("발주 기관 *", placeholder="예: Federal Ministry...")
        col3, col4 = st.columns(2)
        category_options = [
            "IT · 디지털",
            "에너지 · 인프라",
            "의료 · 헬스케어",
            "교통 · 물류",
            "환경 · 수자원",
            "건설 · 플랜트",
            "기타",
        ]
        category = col3.selectbox("분야 *", category_options)
        procedure = col4.selectbox("입찰 방식 *", ["공개경쟁입찰", "제한경쟁입찰", "국제경쟁입찰", "협상에 의한 계약", "기타"])
        col5, col6 = st.columns(2)
        deadline = col5.date_input("입찰 마감일 *", min_value=date.today(), value=date.today() + timedelta(days=30))
        budget = col6.text_input("예상 예산", placeholder="예: USD 12M")

        st.subheader("상세 정보")
        description = st.text_area("사업 개요 *", placeholder="사업의 목적과 주요 범위를 입력하세요.", height=110)
        requirements = st.text_area("참가 요건", placeholder="자격, 실적, 인증 등 주요 요건을 입력하세요.", height=100)
        col7, col8 = st.columns(2)
        contact = col7.text_input("문의처", placeholder="담당 부서 이메일 또는 연락처")
        notice_url = col8.text_input("공고 원문 URL", placeholder="https://")

        submitted = st.form_submit_button("공고 등록", type="primary", use_container_width=True)

    if submitted:
        required = {
            "사업명": title.strip(),
            "발주 국가": country.strip(),
            "발주 기관": agency.strip(),
            "사업 개요": description.strip(),
        }
        missing = [label for label, value in required.items() if not value]
        if missing:
            st.error(f"필수 항목을 입력해 주세요: {', '.join(missing)}")
            return

        new_tender = {
            "id": next_id(tenders),
            "title": title.strip(),
            "country": country.strip(),
            "agency": agency.strip(),
            "category": category,
            "status": "closing_soon" if (deadline - date.today()).days <= 14 else "open",
            "deadline": deadline.isoformat(),
            "budget": budget.strip() or "미정",
            "procedure": procedure,
            "description": description.strip(),
            "requirements": requirements.strip() or "별도 공고문 확인",
            "contact": contact.strip() or "미등록",
            "notice_url": notice_url.strip(),
            "created_at": date.today().isoformat(),
        }
        save_tenders([new_tender, *tenders])
        st.session_state["selected_tender_id"] = new_tender["id"]
        st.session_state["page"] = "detail"
        st.success("입찰공고가 등록되었습니다.")
        st.rerun()


def main() -> None:
    st.set_page_config(
        page_title="BidScope · 해외 입찰공고",
        page_icon="▦",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.sidebar.title("BidScope")
    st.sidebar.caption("해외 입찰공고 관리")

    tenders = load_tenders()
    page = st.session_state.get("page", "list")
    selected_id = st.session_state.get("selected_tender_id")

    if page == "create":
        show_create(tenders)
    elif page == "detail" and selected_id:
        show_detail(tenders, selected_id)
    else:
        show_overview(tenders)

    st.sidebar.divider()
    if st.sidebar.button("입찰 목록", use_container_width=True):
        st.session_state["page"] = "list"
        st.rerun()
    if st.sidebar.button("새 입찰 등록", type="primary", use_container_width=True):
        st.session_state["page"] = "create"
        st.rerun()
    st.sidebar.divider()
    st.sidebar.caption(f"로컬 JSON 저장소 · {len(tenders)}건")


if __name__ == "__main__":
    main()
