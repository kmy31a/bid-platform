import streamlit as st
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, date, timedelta
from typing import Any
import time

# ============================================================
# 설정
# ============================================================

NARA_API_KEY = "887d7fccefd8a0adfe4f33a62b6532b6c355c131138a3d7303dc6d2f6c3d0bea"
NARA_ENDPOINT = "https://apis.data.go.kr/1230000/BidPublicInfoService04/getBidPblancListInfoServcPPSSrch"

DEFAULT_KEYWORDS = ["IT", "ICT", "의료", "교육", "건설"]

EXTERNAL_LINKS = {
    "KOICA": "https://www.koica.go.kr/koica_kr/901/subview.do",
    "EDCF": "https://www.edcfkorea.go.kr/site/homepage/menu/viewMenu?menuid=004002001",
    "ADB": "https://www.adb.org/projects/tenders",
    "AfDB": "https://www.afdb.org/en/projects-and-operations/procurement",
}

STATUS_COLORS = {"진행중": "green", "마감임박": "orange", "마감": "gray"}


# ============================================================
# 유틸리티 함수
# ============================================================

def get_xml_text(element, tag):
    found = element.find(tag)
    return found.text.strip() if found is not None and found.text else ""


def parse_date(date_str):
    if not date_str:
        return ""
    try:
        # 다양한 날짜 형식 처리
        if "T" in date_str:
            return datetime.strptime(date_str[:10], "%Y-%m-%d").strftime("%Y-%m-%d")
        if len(date_str) >= 10 and "-" in date_str:
            return date_str[:10]
        if len(date_str) >= 8:
            return datetime.strptime(date_str[:8], "%Y%m%d").strftime("%Y-%m-%d")
    except:
        pass
    return date_str[:10] if len(date_str) >= 10 else date_str


def format_budget(amount_str):
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
        return f"{amount:,}원"
    except:
        return amount_str


def get_status(deadline):
    if not deadline:
        return "진행중"
    try:
        deadline_date = datetime.strptime(deadline, "%Y-%m-%d").date()
        days_left = (deadline_date - date.today()).days
        if days_left < 0:
            return "마감"
        elif days_left <= 7:
            return "마감임박"
        return "진행중"
    except:
        return "진행중"


def get_days_left(deadline):
    if not deadline:
        return "-"
    try:
        deadline_date = datetime.strptime(deadline, "%Y-%m-%d").date()
        days_left = (deadline_date - date.today()).days
        if days_left < 0:
            return "마감"
        elif days_left == 0:
            return "오늘 마감"
        return f"D-{days_left}"
    except:
        return "-"


# ============================================================
# API 함수
# ============================================================

def fetch_nara_bids(keyword, num_rows=30):
    """나라장터 입찰공고 검색"""
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
        root = ET.fromstring(response.content)

        result_code = root.find(".//resultCode")
        if result_code is not None and result_code.text != "00":
            return []

        items = root.findall(".//item")
        results = []

        for item in items:
            bid_id = get_xml_text(item, "bidNtceNo")
            bid_seq = get_xml_text(item, "bidNtceOrd") or "00"
            
            # 상세페이지 URL 생성
            detail_url = get_xml_text(item, "bidNtceDtlUrl")
            if not detail_url and bid_id:
                detail_url = f"https://www.g2b.go.kr/pt/menu/selectSubFrame.do?framesrc=/pt/menu/frameTgong.do?url=https://www.g2b.go.kr:8101/ep/invitation/publish/bidInfoDtl.do?bidno={bid_id}"
            
            bid = {
                "source": "나라장터",
                "id": bid_id,
                "title": get_xml_text(item, "bidNtceNm"),
                "agency": get_xml_text(item, "ntceInsttNm") or get_xml_text(item, "dminsttNm"),
                "deadline": parse_date(get_xml_text(item, "bidClseDt")),
                "budget": format_budget(get_xml_text(item, "presmptPrce") or get_xml_text(item, "asignBdgtAmt")),
                "url": detail_url,
                "method": get_xml_text(item, "bidMethdNm"),
            }
            if bid["title"]:
                results.append(bid)

        return results
    except Exception as e:
        st.error(f"나라장터 오류: {e}")
        return []


def fetch_worldbank_bids(keyword, num_rows=30):
    """World Bank 입찰공고 검색 - 마감일이 미래인 공고만"""
    url = "https://search.worldbank.org/api/v2/procnotices"
    
    # 오늘 날짜 기준으로 미래 마감 공고만 검색
    today_str = date.today().strftime("%Y-%m-%d")
    
    params = {
        "format": "json",
        "qterm": keyword,
        "rows": num_rows * 3,  # 필터링 후 충분한 결과를 위해 더 많이 요청
        "os": 0,
    }

    for attempt in range(2):
        try:
            response = requests.get(url, params=params, timeout=30)
            data = response.json()
            proc_data = data.get("procnotices", {})

            results = []
            
            def process_doc(doc, key=""):
                if not isinstance(doc, dict):
                    return None
                
                # 마감일 추출
                deadline_raw = doc.get("submission_date", "") or doc.get("deadline_date", "")
                deadline = parse_date(deadline_raw)
                
                # 마감일이 오늘 이후인 것만 포함 (마감일 없는 것도 포함)
                if deadline:
                    try:
                        deadline_date = datetime.strptime(deadline, "%Y-%m-%d").date()
                        if deadline_date < date.today():
                            return None  # 마감된 공고 제외
                    except:
                        pass
                
                # 상세 페이지 URL 생성
                notice_id = doc.get("id", key)
                detail_url = doc.get("url", "")
                if not detail_url and notice_id:
                    detail_url = f"https://projects.worldbank.org/en/projects-operations/procurement-detail/{notice_id}"
                
                # notice_type 전체 표시
                notice_type = doc.get("notice_type", "") or doc.get("procurement_method", "") or "-"
                
                bid = {
                    "source": "World Bank",
                    "id": notice_id,
                    "title": doc.get("notice_title", "") or doc.get("project_name", ""),
                    "agency": doc.get("borrower", "") or doc.get("buyer", ""),
                    "country": doc.get("countryname", "") or doc.get("country", ""),
                    "deadline": deadline,
                    "budget": "별도 확인",
                    "url": detail_url,
                    "method": notice_type,
                }
                return bid if bid["title"] else None
            
            # dict인 경우
            if isinstance(proc_data, dict):
                for key, doc in proc_data.items():
                    if key not in ["total", "rows"]:
                        bid = process_doc(doc, key)
                        if bid:
                            results.append(bid)
            
            # list인 경우
            elif isinstance(proc_data, list):
                for doc in proc_data:
                    bid = process_doc(doc)
                    if bid:
                        results.append(bid)

            # 결과 개수 제한
            return results[:num_rows]
            
        except requests.exceptions.Timeout:
            if attempt == 0:
                time.sleep(1)
                continue
            else:
                st.warning("World Bank 서버 응답이 느립니다. 나중에 다시 시도해주세요.")
                return []
        except Exception as e:
            st.error(f"World Bank 오류: {e}")
            return []
    
    return []


# ============================================================
# UI 컴포넌트
# ============================================================

def render_bid_card(bid):
    """입찰공고 카드 - 클릭 시 상세페이지로 이동"""
    status = get_status(bid.get("deadline", ""))
    color = STATUS_COLORS.get(status, "gray")
    
    # 카드 전체를 클릭 가능하게
    with st.container(border=True):
        col1, col2 = st.columns([4, 1])

        with col1:
            emoji = "🇰🇷" if bid["source"] == "나라장터" else "🌍"
            title = bid.get("title", "제목 없음")
            short_title = title[:55] + "..." if len(title) > 55 else title
            
            # 제목을 클릭 가능한 링크로
            if bid.get("url"):
                st.markdown(f"**{emoji} [{short_title}]({bid['url']})**")
            else:
                st.markdown(f"**{emoji} {short_title}**")

            agency = bid.get("agency", "-") or "-"
            country = bid.get("country", "")
            loc = f"{country} · " if country else ""
            st.caption(f"{bid['source']} | {loc}{agency}")

        with col2:
            st.markdown(f":{color}[**{status}**]")

        c1, c2, c3, c4 = st.columns(4)
        c1.markdown(f"📅 **마감일**\n\n{bid.get('deadline', '-') or '-'}")
        c2.markdown(f"💰 **예산**\n\n{bid.get('budget', '-')}")
        
        # 방식(method) 전체 표시 - 길면 줄바꿈
        method = bid.get('method', '-') or '-'
        c3.markdown(f"📋 **방식**\n\n{method}")
        
        c4.markdown(f"⏰ **남은기간**\n\n{get_days_left(bid.get('deadline', ''))}")

        # 공고 보기 버튼
        if bid.get("url"):
            st.link_button("🔗 상세 공고 보기", bid["url"], use_container_width=True)


def render_statistics(bids):
    """통계 표시"""
    total = len(bids)
    nara = len([b for b in bids if b["source"] == "나라장터"])
    wb = len([b for b in bids if b["source"] == "World Bank"])
    urgent = len([b for b in bids if get_status(b.get("deadline", "")) == "마감임박"])

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("전체", f"{total}건")
    c2.metric("나라장터", f"{nara}건")
    c3.metric("World Bank", f"{wb}건")
    c4.metric("마감임박", f"{urgent}건")


def render_links():
    """바로가기 링크"""
    st.subheader("🔗 기관 바로가기")
    cols = st.columns(len(EXTERNAL_LINKS))
    for idx, (name, url) in enumerate(EXTERNAL_LINKS.items()):
        cols[idx].link_button(name, url, use_container_width=True)


# ============================================================
# 메인
# ============================================================

def main():
    st.set_page_config(
        page_title="글로벌 입찰정보",
        page_icon="🌐",
        layout="wide",
    )

    # 사이드바
    with st.sidebar:
        st.title("🌐 BidScope")
        st.divider()

        sources = st.multiselect(
            "데이터 소스",
            ["나라장터", "World Bank"],
            default=["나라장터", "World Bank"],
        )

        keywords_input = st.text_area(
            "검색 키워드 (쉼표 구분)",
            value=", ".join(DEFAULT_KEYWORDS),
            height=80,
        )

        max_results = st.slider("소스별 최대 결과", 10, 50, 20)
        
        # 마감된 공고 포함 여부
        include_closed = st.checkbox("마감된 공고도 포함", value=False)
        
        search_clicked = st.button("🔍 검색", type="primary", use_container_width=True)

        st.divider()
        render_links()

    # 메인
    st.title("🌐 글로벌 입찰정보 통합 플랫폼")
    st.caption("나라장터 · World Bank 입찰공고를 한 곳에서 검색하세요
