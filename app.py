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

DEFAULT_KEYWORDS = ["IT", "ICT", "의료", "교육", "보건", "교통", "기자재"]

EXTERNAL_LINKS = {
    "KOICA": "https://www.koica.go.kr/koica_kr/901/subview.do",
    "EDCF": "https://www.edcfkorea.go.kr/fe/HPHFFE065M01",
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
            bid = {
                "source": "나라장터",
                "id": get_xml_text(item, "bidNtceNo"),
                "title": get_xml_text(item, "bidNtceNm"),
                "agency": get_xml_text(item, "ntceInsttNm") or get_xml_text(item, "dminsttNm"),
                "deadline": parse_date(get_xml_text(item, "bidClseDt")),
                "budget": format_budget(get_xml_text(item, "presmptPrce") or get_xml_text(item, "asignBdgtAmt")),
                "url": get_xml_text(item, "bidNtceDtlUrl"),
                "method": get_xml_text(item, "bidMethdNm"),
            }
            if bid["title"]:
                results.append(bid)

        return results
    except Exception as e:
        st.error(f"나라장터 오류: {e}")
        return []


def fetch_worldbank_bids(keyword, num_rows=30):
    """World Bank 입찰공고 검색"""
    url = "https://projects.worldbank.org/en/projects-operations/opportunities"
    params = {"format": "json", "qterm": keyword, "rows": num_rows}

    try:
        response = requests.get(url, params=params, timeout=15)
        data = response.json()
        proc_data = data.get("procnotices", {})

        results = []
        for key, doc in proc_data.items():
            if isinstance(doc, dict) and key not in ["total", "rows"]:
                bid = {
                    "source": "World Bank",
                    "id": doc.get("id", key),
                    "title": doc.get("notice_title", "") or doc.get("project_name", ""),
                    "agency": doc.get("borrower", "") or doc.get("buyer", ""),
                    "country": doc.get("countryname", ""),
                    "deadline": parse_date(doc.get("submission_date", "") or doc.get("deadline_date", "")),
                    "budget": "별도 확인",
                    "url": doc.get("url", ""),
                    "method": doc.get("notice_type", ""),
                }
                if bid["title"]:
                    results.append(bid)

        return results
    except Exception as e:
        st.error(f"World Bank 오류: {e}")
        return []


# ============================================================
# UI 컴포넌트
# ============================================================

def render_bid_card(bid):
    """입찰공고 카드"""
    status = get_status(bid.get("deadline", ""))
    color = STATUS_COLORS.get(status, "gray")

    with st.container(border=True):
        col1, col2 = st.columns([4, 1])

        with col1:
            emoji = "🇰🇷" if bid["source"] == "나라장터" else "🌍"
            title = bid.get("title", "제목 없음")
            short_title = title[:55] + "..." if len(title) > 55 else title
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
        c3.markdown(f"📋 **방식**\n\n{(bid.get('method', '-') or '-')[:12]}")
        c4.markdown(f"⏰ **남은기간**\n\n{get_days_left(bid.get('deadline', ''))}")

        if bid.get("url"):
            st.link_button("🔗 공고 보기", bid["url"])


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
        search_clicked = st.button("🔍 검색", type="primary", use_container_width=True)

        st.divider()
        render_links()

    # 메인
    st.title("🌐 글로벌 입찰정보 통합 플랫폼")
    st.caption("나라장터 · World Bank 입찰공고를 한 곳에서 검색하세요")

    # 검색 실행
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
            total = len(sources) * len(keywords)
            step = 0

            for source in sources:
                for keyword in keywords:
                    step += 1
                    progress.progress(step / total)

                    if source == "나라장터":
                        bids = fetch_nara_bids(keyword, max_results // len(keywords))
                    elif source == "World Bank":
                        bids = fetch_worldbank_bids(keyword, max_results // len(keywords))
                    else:
                        bids = []

                    all_bids.extend(bids)
                    time.sleep(0.2)

            progress.empty()

        # 중복 제거
        seen = set()
        unique_bids = []
        for bid in all_bids:
            bid_id = f"{bid['source']}_{bid['id']}"
            if bid_id not in seen:
                seen.add(bid_id)
                unique_bids.append(bid)

        # 마감일 정렬
        unique_bids.sort(key=lambda x: x.get("deadline", "9999-99-99"))

        st.session_state["bids"] = unique_bids
        st.session_state["search_time"] = datetime.now().strftime("%Y-%m-%d %H:%M")

    # 결과 표시
    bids = st.session_state.get("bids", [])
    search_time = st.session_state.get("search_time", "")

    if search_time:
        st.caption(f"🕐 검색 시간: {search_time}")

    st.divider()

    if bids:
        render_statistics(bids)
        st.divider()

        # 탭
        tab_all, tab_nara, tab_wb = st.tabs([
            f"📋 전체 ({len(bids)})",
            f"🇰🇷 나라장터 ({len([b for b in bids if b['source'] == '나라장터'])})",
            f"🌍 World Bank ({len([b for b in bids if b['source'] == 'World Bank'])})",
        ])

        with tab_all:
            for bid in bids:
                render_bid_card(bid)

        with tab_nara:
            nara_bids = [b for b in bids if b["source"] == "나라장터"]
            if nara_bids:
                for bid in nara_bids:
                    render_bid_card(bid)
            else:
                st.info("나라장터 결과가 없습니다.")

        with tab_wb:
            wb_bids = [b for b in bids if b["source"] == "World Bank"]
            if wb_bids:
                for bid in wb_bids:
                    render_bid_card(bid)
            else:
                st.info("World Bank 결과가 없습니다.")
    else:
        st.info("🔍 왼쪽 사이드바에서 검색 버튼을 눌러주세요.")


if __name__ == "__main__":
    main()
