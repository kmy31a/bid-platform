import streamlit as st
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, date, timedelta
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
            detail_url = get_xml_text(item, "bidNtceDtlUrl")
            if not detail_url and bid_id:
                detail_url = f"https://www.g2b.go.kr:8101/ep/invitation/publish/bidInfoDtl.do?bidno={bid_id}"
            
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


def fetch_worldbank_bids(keyword, num_rows=30, include_closed=False):
    url = "https://search.worldbank.org/api/v2/procnotices"
    
    params = {
        "format": "json",
        "qterm": keyword,
        "rows": num_rows * 3,
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
                
                deadline_raw = doc.get("submission_date", "") or doc.get("deadline_date", "")
                deadline = parse_date(deadline_raw)
                
                if not include_closed and deadline:
                    try:
                        deadline_date = datetime.strptime(deadline, "%Y-%m-%d").date()
                        if deadline_date < date.today():
                            return None
                    except:
                        pass
                
                notice_id = doc.get("id", key)
                detail_url = doc.get("url", "")
                if not detail_url and notice_id:
                    detail_url = f"https://projects.worldbank.org/en/projects-operations/procurement-detail/{notice_id}"
                
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
            
            if isinstance(proc_data, dict):
                for key, doc in proc_data.items():
                    if key not in ["total", "rows"]:
                        bid = process_doc(doc, key)
                        if bid:
                            results.append(bid)
            
            elif isinstance(proc_data, list):
                for doc in proc_data:
                    bid = process_doc(doc)
                    if bid:
                        results.append(bid)

            return results[:num_rows]
            
        except requests.exceptions.Timeout:
            if attempt == 0:
                time.sleep(1)
                continue
            else:
                st.warning("World Bank 서버 응답이 느립니다.")
                return []
        except Exception as e:
            st.error(f"World Bank 오류: {e}")
            return []
    
    return []


# ============================================================
# UI 컴포넌트
# ============================================================

def render_bid_card(bid):
    status = get_status(bid.get("deadline", ""))
    color = STATUS_COLORS.get(status, "gray")
    
    with st.container(border=True):
        col1, col2 = st.columns([4, 1])

        with col1:
            emoji = "🇰🇷" if bid["source"] == "나라장터" else "🌍"
            title = bid.get("title", "제목 없음")
            short_title = title[:55] + "..." if len(title) > 55 else title
            
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
        c3.markdown(f"📋 **방식**\n\n{bid.get('method', '-') or '-'}")
        c4.markdown(f"⏰ **D-Day**\n\n{get_days_left(bid.get('deadline', ''))}")

        if bid.get("url"):
            st.link_button("🔗 상세 공고 보기", bid["url"], use_container_width=True)


def render_statistics(bids):
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
    st.subheader("🔗 기관 바로가기")
    cols = st.columns(len(EXTERNAL_LINKS))
    for idx, (name, url) in enumerate(EXTERNAL_LINKS.items()):
        cols[idx].link_button(name, url, use_container_width=True)


# ============================================================
# 메인
# ============================================================

def main():
    st.set_page_config(page_title="글로벌 입찰정보", page_icon="🌐", layout="wide")

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
        include_closed = st.checkbox("마감된 공고도 포함", value=False)
        search_clicked = st.button("🔍 검색", type="primary", use_container_width=True)

        st.divider()
        render_links()

    st.title("🌐 글로벌 입찰정보 통합 플랫폼")
    st.caption("나라장터 · World Bank 입찰공고를 한 곳에서 검색하세요")

    if search_clicked:
        keywords = [k.strip() for k in keywords_input.split(",") if k.strip()]

        if not keywords:
            st.warning("검색 키워드를 입력해주세요.")
            return

        if not sources:
            st.warning("데이터 소스를 선택해주세요.")
            return

        all_bids = []

        with st.spinner("입찰정보 수집 중..."):
            progress = st.progress(0)
            total_steps = len(sources) * len(keywords)
            step = 0

            for source in sources:
                for keyword in keywords:
                    step += 1
                    progress.progress(step / total_steps)

                    if source == "나라장터":
                        bids = fetch_nara_bids(keyword, max_results // len(keywords))
                    elif source == "World Bank":
                        bids = fetch_worldbank_bids(keyword, max_results // len(keywords), include_closed)
                    else:
                        bids = []

                    all_bids.extend(bids)
                    time.sleep(0.2)

            progress.empty()

        seen = set()
        unique_bids = []
        for bid in all_bids:
            bid_key = f"{bid['source']}_{bid['id']}"
            if bid_key not in seen:
                seen.add(bid_key)
                unique_bids.append(bid)

        unique_bids.sort(key=lambda x: x.get("deadline", "") or "9999-99-99")

        st.session_state["bids"] = unique_bids
        st.session_state["search_time"] = datetime.now().strftime("%Y-%m-%d %H:%M")

    if "bids" in st.session_state and st.session_state["bids"]:
        bids = st.session_state["bids"]
        
        st.success(f"🕐 {st.session_state.get('search_time', '')} 검색 완료")
        render_statistics(bids)
        
        st.divider()
        
        filter_source = st.selectbox("소스 필터", ["전체", "나라장터", "World Bank"])
