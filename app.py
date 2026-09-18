import streamlit as st
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, date
from typing import Any
import time

# ============================================================
# 설정
# ============================================================

# 나라장터 API 설정
NARA_API_KEY = "887d7fccefd8a0adfe4f33a62b6532b6c355c131138a3d7303dc6d2f6c3d0bea"
NARA_ENDPOINT = "https://apis.data.go.kr/1230000/BidPublicInfoService04/getBidPblancListInfoServc01"

# 기본 검색어 목록
DEFAULT_KEYWORDS_KR = ["IT", "ICT", "기자재", "장비", "ITS", "보건", "의료", "교육", "교통", "건설장비", "버스"]
DEFAULT_KEYWORDS_EN = ["Construction Equipment", "Vehicle", "Transport", "Medical", "Health"]

# 바로가기 링크
EXTERNAL_LINKS = {
    "KOICA": "https://www.koica.go.kr/koica_kr/901/subview.do",
    "EDCF": "https://www.edcfkorea.go.kr/site/homepage/menu/viewMenu?menuid=004002001",
    "AfDB": "https://www.afdb.org/en/projects-and-operations/procurement",
    "EBRD": "https://www.ebrd.com/work-with-us/procurement.html",
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
    """나라장터 입찰공고 검색"""
    params = {
        "serviceKey": NARA_API_KEY,
        "pageNo": "1",
        "numOfRows": str(num_rows),
        "inqryDiv": "1",  # 공고명 검색
        "inqryBgnDt": (datetime.now().replace(day=1)).strftime("%Y%m%d") + "0000",
        "inqryEndDt": datetime.now().strftime("%Y%m%d") + "2359",
        "bidNtceNm": keyword,
        "type": "xml",
    }
    
    try:
        response = requests.get(NARA_ENDPOINT, params=params, timeout=10)
        response.raise_for_status()
        
        root = ET.fromstring(response.content)
        items = root.findall(".//item")
        
        results = []
        for item in items:
            bid_data = {
                "source": "나라장터",
                "id": get_xml_text(item, "bidNtceNo"),
                "title": get_xml_text(item, "bidNtceNm"),
                "agency": get_xml_text(item, "ntceInsttNm"),
                "deadline": parse_nara_date(get_xml_text(item, "bidClseDt")),
                "budget": format_budget(get_xml_text(item, "presmptPrce")),
                "url": get_xml_text(item, "bidNtceDtlUrl"),
                "method": get_xml_text(item, "bidMethdNm"),
                "category": get_xml_text(item, "ntceKindNm"),
            }
            results.append(bid_data)
        
        return results
    except Exception as e:
        st.error(f"나라장터 API 오류: {str(e)}")
        return []


def get_xml_text(element: ET.Element, tag: str) -> str:
    """XML 요소에서 텍스트 추출"""
    found = element.find(tag)
    return found.text if found is not None and found.text else ""


def parse_nara_date(date_str: str) -> str:
    """나라장터 날짜 파싱"""
    if not date_str:
        return ""
    try:
        dt = datetime.strptime(date_str[:8], "%Y%m%d")
        return dt.strftime("%Y-%m-%d")
    except:
        return date_str


def format_budget(amount_str: str) -> str:
    """예산 포맷팅"""
    if not amount_str:
        return "미정"
    try:
        amount = int(float(amount_str))
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
        "srt": "noticedate",
        "order": "desc",
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        results = []
        for doc in data.get("procnotices", {}).values():
            if isinstance(doc, dict):
                bid_data = {
                    "source": "World Bank",
                    "id": doc.get("id", ""),
                    "title": doc.get("project_name", doc.get("notice_title", "")),
                    "agency": doc.get("borrower", ""),
                    "country": doc.get("countryname", ""),
                    "deadline": parse_wb_date(doc.get("submission_date", "")),
                    "budget": "별도 확인",
                    "url": doc.get("url", ""),
                    "method": doc.get("procurement_method", ""),
                    "category": doc.get("notice_type", ""),
                }
                results.append(bid_data)
        
        return results
    except Exception as e:
        st.error(f"World Bank API 오류: {str(e)}")
        return []


def parse_wb_date(date_str: str) -> str:
    """World Bank 날짜 파싱"""
    if not date_str:
        return ""
    try:
        dt = datetime.strptime(date_str[:10], "%Y-%m-%d")
        return dt.strftime("%Y-%m-%d")
    except:
        return date_str


# ============================================================
# ADB API
# ============================================================

def fetch_adb_bids(keyword: str, num_rows: int = 30) -> list[dict[str, Any]]:
    """ADB 입찰공고 검색"""
    url = "https://www.adb.org/api/v1/business-opportunities"
    params = {
        "keyword": keyword,
        "limit": num_rows,
        "offset": 0,
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        results = []
        for item in data.get("data", []):
            bid_data = {
                "source": "ADB",
                "id": item.get("id", ""),
                "title": item.get("title", ""),
                "agency": item.get("executing_agency", ""),
                "country": item.get("country", ""),
                "deadline": item.get("deadline", ""),
                "budget": "별도 확인",
                "url": f"https://www.adb.org{item.get('url', '')}",
                "method": item.get("procurement_method", ""),
                "category": item.get("sector", ""),
            }
            results.append(bid_data)
        
        return results
    except Exception as e:
        st.error(f"ADB API 오류: {str(e)}")
        return []


# ============================================================
# 유틸리티 함수
# ============================================================

def get_status(deadline: str) -> str:
    """마감일 기준 상태 반환"""
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
    """남은 일수 계산"""
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


def render_status_badge(status: str) -> None:
    """상태 뱃지 렌더링"""
    color = STATUS_COLORS.get(status, "gray")
    st.markdown(f":{color}[{status}]")


# ============================================================
# UI 컴포넌트
# ============================================================

def render_bid_card(bid: dict[str, Any]) -> None:
    """입찰공고 카드 렌더링"""
    status = get_status(bid.get("deadline", ""))
    
    with st.container(border=True):
        # 헤더
        col1, col2 = st.columns([4, 1])
        with col1:
            source_emoji = {"나라장터": "🇰🇷", "World Bank": "🌍", "ADB": "🌏"}.get(bid["source"], "📋")
            st.markdown(f"### {source_emoji} {bid.get('title', '제목 없음')[:60]}...")
            
            agency = bid.get('agency', '-')
            country = bid.get('country', '')
            location = f"{country} · " if country else ""
            st.caption(f"{bid['source']} | {location}{agency}")
        
        with col2:
            render_status_badge(status)
        
        # 상세 정보
        info_cols = st.columns(4)
        info_cols[0].markdown(f"**마감일**\n\n{bid.get('deadline', '-')}")
        info_cols[1].markdown(f"**예산**\n\n{bid.get('budget', '-')}")
        info_cols[2].markdown(f"**입찰방식**\n\n{bid.get('method', '-')[:10] if bid.get('method') else '-'}")
        info_cols[3].markdown(f"**남은기간**\n\n{get_days_left(bid.get('deadline', ''))}")
        
        # 버튼
        if bid.get("url"):
            st.link_button("📄 공고 원문 보기", bid["url"], use_container_width=False)


def render_external_links() -> None:
    """바로가기 링크 섹션"""
    st.subheader("📎 기타 기관 바로가기")
    st.caption("아래 기관은 API가 제공되지 않아 직접 사이트 방문이 필요합니다.")
    
    cols = st.columns(len(EXTERNAL_LINKS))
    for idx, (name, url) in enumerate(EXTERNAL_LINKS.items()):
        with cols[idx]:
            st.link_button(f"🔗 {name}", url, use_container_width=True)


def render_statistics(all_bids: list[dict[str, Any]]) -> None:
    """통계 표시"""
    total = len(all_bids)
    by_source = {}
    closing_soon = 0
    
    for bid in all_bids:
        source = bid.get("source", "기타")
        by_source[source] = by_source.get(source, 0) + 1
        if get_status(bid.get("deadline", "")) == "마감임박":
            closing_soon += 1
    
    cols = st.columns(5)
    cols[0].metric("전체 공고", f"{total}건")
    cols[1].metric("나라장터", f"{by_source.get('나라장터', 0)}건")
    cols[2].metric("World Bank", f"{by_source.get('World Bank', 0)}건")
    cols[3].metric("ADB", f"{by_source.get('ADB', 0)}건")
    cols[4].metric("마감 임박", f"{closing_soon}건", "7일 이내")


# ============================================================
# 메인 페이지
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
        
        # 데이터 소스 선택
        sources = st.multiselect(
            "데이터 소스",
            ["나라장터", "World Bank", "ADB"],
            default=["나라장터", "World Bank", "ADB"],
        )
        
        # 검색어 입력
        default_keywords = ", ".join(DEFAULT_KEYWORDS_KR[:5])
        keywords_input = st.text_area(
            "검색 키워드",
            value=default_keywords,
            help="쉼표로 구분하여 여러 키워드 입력",
            height=100,
        )
        
        # 결과 수 제한
        max_results = st.slider("소스별 최대 결과 수", 10, 50, 20)
        
        search_clicked = st.button("🔍 검색", type="primary", use_container_width=True)
        
        st.divider()
        st.caption("💡 Tip: 검색어는 쉼표로 구분")
        st.caption("예: IT, 의료, 건설장비")
    
    # 메인 컨텐츠
    st.title("🌐 글로벌 입찰정보 통합 플랫폼")
