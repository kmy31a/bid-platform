import streamlit as st
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, date, timedelta
from typing import Any
import time
import urllib.parse

# ============================================================
# 설정
# ============================================================

# 나라장터 API 설정
NARA_API_KEY = "887d7fccefd8a0adfe4f33a62b6532b6c355c131138a3d7303dc6d2f6c3d0bea"
NARA_ENDPOINT = "https://apis.data.go.kr/1230000/BidPublicInfoService04/getBidPblancListInfoServcPPSSrch"

# 기본 검색어 목록
DEFAULT_KEYWORDS_KR = ["IT", "ICT", "기자재", "장비", "ITS", "보건", "의료", "교육", "교통", "건설장비", "버스"]
DEFAULT_KEYWORDS_EN = ["Construction Equipment", "Vehicle", "Transport", "Medical", "Health"]

# 바로가기 링크
EXTERNAL_LINKS = {
    "KOICA": "https://www.koica.go.kr/koica_kr/901/subview.do",
    "EDCF": "https://www.edcfkorea.go.kr/site/homepage/menu/viewMenu?menuid=004002001",
    "AfDB": "https://www.afdb.org/en/projects-and-operations/procurement",
    "EBRD": "https://www.ebrd.com/work-with-us/procurement.html",
    "ADB": "https://www.adb.org/projects/tenders",
}

STATUS_COLORS = {
    "진행중": "green",
    "마감임박": "orange",
    "마감": "gray",
}


# ============================================================
# 나라장터 API
# ============================================================

def fetch_nara_bids(keyword: str, num_rows: int = 30) -> list[dict[str, Any]]:
    """나라장터 입찰공고 검색 (용역)"""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)

    params = {
        "serviceKey": NARA_API_KEY,
        "pageNo": "1",
        "numOfRows": str(num_rows),
        "inqryDiv": "1",
        "inqryBgnDt": start_date.strftime("%Y%m%d") + "0000",
        "inqryEndDt": end_date.strftime("%Y%m%d") + "2359",
        "bidNtceNm": keyword,
    }

    try:
        response = requests.get(NARA_ENDPOINT, params=params, timeout=15)
        response.raise_for_status()

        root = ET.fromstring(response.content)

        result_code = root.find(".//resultCode")
        if result_code is not None and result_code.text != "00":
            result_msg = root.find(".//resultMsg")
            error_msg = result_msg.text if result_msg is not None else "Unknown error"
            return []

        items = root.findall(".//item")
        results = []

        for item in items:
            bid_data = {
                "source": "나라장터",
                "id": get_xml_text(item, "bidNtceNo"),
                "title": get_xml_text(item, "bidNtceNm"),
                "agency": get_xml_text(item, "ntceInsttNm") or get_xml_text(item, "dminsttNm"),
                "deadline": parse_nara_date(get_xml_text(item, "bidClseDt")),
                "budget": format_budget(get_xml_text(item, "presmptPrce") or get_xml_text(item, "asignBdgtAmt")),
                "url": get_xml_text(item, "bidNtceDtlUrl"),
                "method": get_xml_text(item, "bidMethdNm"),
                "category": get_xml_text(item, "ntceKindNm") or "용역",
            }
            if bid_data["title"]:
                results.append(bid_data)

        return results

    except Exception as e:
        st.error(f"나라장터 API 오류: {str(e)}")
        return []


def get_xml_text(element: ET.Element, tag: str) -> str:
    found = element.find(tag)
    return found.text.strip() if found is not None and found.text else ""


def parse_nara_date(date_str: str) -> str:
    if not date_str:
        return ""
    try:
        if len(date_str) >= 8:
            dt = datetime.strptime(date_str[:8], "%Y%m%d")
            return dt.strftime("%Y-%m-%d")
    except:
        pass
    return date_str


def format_budget(amount_str: str) -> str:
    if not amount_str:
        return "미정"
    try:
        amount = int(float(amount_str))
        if amount == 0:
            return "미정"
        if amount >= 100000000:
            return f"{amount / 100000000:.1f}억원"
        elif amount >= 10000:
            return f"{amount / 10000:.0f}만원"
        else:
            return f"{amount:,}원"
    except:
        return amount_str


# ============================================================
# World Bank API
# ============================================================

def fetch_worldbank_bids(keyword: str, num_rows: int = 30) -> list[dict[str, Any]]:
    """World Bank 입찰공고 검색"""
    url = "https://search.worldbank.org/api/v2/procnotices"

    params = {
        "format": "json",
        "qterm": keyword,
        "rows": num_rows,
        "os": 0,
    }

    try:
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()

        results = []
        proc_data = data.get("procnotices", {})

        if isinstance(proc_data, dict):
            for key, doc in proc_data.items():
                if isinstance(doc, dict) and key not in ["total", "rows"]:
                    bid_data = {
                        "source": "World Bank",
                        "id": doc.get("id", key),
                        "title": doc.get("notice_title", "") or doc.get("project_name", ""),
                        "agency": doc.get("borrower", "") or doc.get("buyer", ""),
                        "country": doc.get("countryname", "") or doc.get("regionname", ""),
                        "deadline": parse_wb_date(doc.get("submission_date", "") or doc.get("deadline_date", "")),
                        "budget": "별도 확인",
                        "url": doc.get("url", ""),
                        "method": doc.get("procurement_method", "") or doc.get("notice_type", ""),
                        "category": doc.get("sector", "") or doc.get("notice_type", ""),
                    }
                    if bid_data["title"]:
                        results.append(bid_data)

        return results

    except Exception as e:
        st.error(f"World Bank API 오류: {str(e)}")
        return []


def parse_wb_date(date_str: str) -> str:
    if not date_str:
        return ""
    try:
        for fmt in ["%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d", "%d-%b-%Y"]:
            try:
                dt = datetime.strptime(date_str[:19], fmt)
                return dt.strftime("%Y-%m-%d")
            except:
                continue
    except:
        pass
    return date_str[:10] if len(date_str) >= 10 else date_str


# ============================================================
# ADB (바로가기만 제공 - 공식 API 없음)
# ============================================================

def fetch_adb_bids(keyword: str, num_rows: int = 30) -> list[dict[str, Any]]:
    """ADB는 공식 API가 없어 바로가기 안내"""
    return []


# ============================================================
# 유틸리티 함수
# ============================================================

def get_status(deadline: str) -> str:
    if not deadline:
        return "진행중"
    try:
        deadline_date = datetime.strptime(deadline, "%Y-%m-%d").date()
        days_left = (deadline_date - date.today()).days
        if days_left < 0:
            return "마감"
        elif days_left <= 7:
            return "마감임박"
        else:
            return "진행중"
    except:
        return "진행중"


def get_days_left(deadline: str) -> str:
    if not deadline:
        return "-"
    try:
        deadline_date = datetime.strptime(deadline, "%Y-%m-%d").date()
        days_left = (deadline_date - date.today()).days
        if days_left < 0:
            return "마감"
        elif days_left == 0:
            return "오늘 마감"
        else:
            return f"D-{days_left}"
    except:
        return "-"


# ============================================================
# UI 컴포넌트
# ============================================================

def render_bid_card(bid: dict[str, Any]) -> None:
    status = get_status(bid.get("deadline", ""))

    with st.container(border=True):
        col1, col2 = st.columns([4, 1])
        with col1:
            source_emoji = {"나라장터": "🇰🇷", "World Bank": "🌍", "ADB": "🌏"}.get(bid["source"], "📋")
            title = bid.get("title", "제목 없음")
            display_title = title[:60] + "..." if len(title) > 60 else title
            st.markdown(f"### {source_emoji} {display_title}")

            agency = bid.get("agency", "-") or "-"
            country = bid.get("country", "")
            location = f"{country} · " if country else ""
            st.caption(f"{bid['source']} | {location}{agency}")

        with col2:
            color = STATUS_COLORS.get(status, "gray")
            st.markdown(f":{color}[**{status}**]")

        info_cols = st.columns(4)
        info_cols[0].markdown(f"**마감일**\n\n{bid.get('deadline', '-') or '-'}")
        info_cols[1].markdown(f"**예산**\n\n{bid.get('budget', '-')}")
        method = bid.get("method", "-") or "-"
        info_cols[2].markdown(f"**입찰방식**\n\n{method[:15]}")
        info_cols[3].markdown(f"**남은기간**\n\n{get_days_left(bid.get('deadline', ''))}")

        if bid.get("url"):
            st.link_button("📄 공고 상세보기", bid["url"], use_container_width=False)


def render_external_links() -> None:
    st.subheader("📎 기관 바로가기")
    st.caption("아래 기관들은 직접 사이트에서 검색하세요.")

    cols = st.columns(len(EXTERNAL_LINKS))
    for idx, (name, url) in enumerate(EXTERNAL_LINKS.items()):
        with cols[idx]:
            st.link_button(f"🔗 {name}", url, use_container_width=True)


def render_statistics(all_bids: list[dict[str, Any]]) -> None:
    total = len(all_bids)
    by_source = {}
    closing_soon = 0

    for bid in all_bids:
        source = bid.get("source", "기타")
        by_source[source] = by_source.get(source, 0) + 1
        if get_status(bid.get("deadline", "")) == "마감임박":
            closing_soon += 1

    cols = st.columns(4)
    cols[0].metric("전체 공고", f"{total}건")
    cols[1].metric("나라장터", f"{by_source.get('나라장터', 0)}건")
    cols[2].metric("World Bank", f"{by_source.get('World Bank', 0)}건")
    cols[3].metric("마감 임박 (7일내)", f"{closing_soon}건")


# ============================================================
# 메인
# ============================================================

def main():
    st.set_page_config(
        page_title="글로벌 입찰정보 통합 플랫폼",
        page_icon="🌐",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # 사이드바
    with st.sidebar:
        st.title("🌐 BidScope Global")
        st.caption("글로벌 입찰정보 통합 플랫폼")
        st.divider()

        st.subheader("검색 설정")

        sources = st.multiselect(
            "데이터 소스",
            ["나라장터", "World Bank"],
            default=["나라장터", "World Bank"],
            help="ADB는 공식 API가 없어 바로가기 탭에서 직접 검색하세요."
        )

        default_keywords = ", ".join(DEFAULT_KEYWORDS_KR[:5])
        keywords_input = st.text_area(
            "검색 키워드 (쉼표로 구분)",
            value=default_keywords,
            height=100,
        )

        max_results = st.slider("소스별 최대 결과 수", 10, 50, 20)

        search_clicked = st.button("🔍 검색", type="primary", use_container_width=True)

        st.divider()
        st.caption("💡 검색어 예시: IT, 의료, 건설장비")

    # 메인 컨텐츠
    st.title("🌐 글로벌 입찰정보 통합 플랫폼")
    st.caption("나라장터 · World Bank 입찰공고를 한 곳에서 검색하세요")

    # 검색 실행
    if search_clicked:
        keywords = [k.strip() for k in keywords_input.split(",") if k.strip()]

        if not keywords:
            st.warning("검색 키워드를 입력해주세요.")
            return

        if not sources:
            st.warning("최소 하나의 데이터 소스를 선택해주세요.")
            return

        all_bids = []

        with st.spinner("입찰정보를 수집 중입니다..."):
            progress_bar = st.progress(0)
            total_steps = len(sources) * len(keywords)
            current_step = 0

            for source in sources:
                for keyword in keywords:
                    current_step += 1
