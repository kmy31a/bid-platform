import streamlit as st
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, date, timedelta
import time

st.set_page_config(page_title="글로벌 입찰정보", page_icon="🌐", layout="wide")

NARA_API_KEY = "887d7fccefd8a0adfe4f33a62b6532b6c355c131138a3d7303dc6d2f6c3d0bea"
NARA_ENDPOINT = "https://apis.data.go.kr/1230000/BidPublicInfoService04/getBidPblancListInfoServcPPSSrch"
DEFAULT_KEYWORDS = ["IT", "ICT", "의료", "교육", "건설"]

EXTERNAL_LINKS = {
    "KOICA": "https://www.koica.go.kr/koica_kr/901/subview.do",
    "EDCF": "https://www.edcfkorea.go.kr/site/homepage/menu/viewMenu?menuid=004002001",
    "ADB": "https://www.adb.org/projects/tenders",
    "AfDB": "https://www.afdb.org/en/projects-and-operations/procurement",
}
if "sources" not in st.session_state:
    st.session_state.sources = ["나라장터", "World Bank"]
if "keywords_input" not in st.session_state:
    st.session_state.keywords_input = ", ".join(DEFAULT_KEYWORDS)
if "max_results" not in st.session_state:
    st.session_state.max_results = 20
if "include_closed" not in st.session_state:
    st.session_state.include_closed = False

if "bids" not in st.session_state:
    st.session_state.bids = []
if "search_time" not in st.session_state:
    st.session_state.search_time = ""
if "do_search" not in st.session_state:
    st.session_state.do_search = False


def get_xml_text(element, tag):
    found = element.find(tag)
    if found is not None and found.text:
        return found.text.strip()
    return ""


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
    except Exception:
        pass
    if len(date_str) >= 10:
        return date_str[:10]
    return date_str


def format_budget(amount_str):
    if not amount_str:
        return "미정"
    try:
        amount = int(float(amount_str))
        if amount == 0:
            return "미정"
        if amount >= 100000000:
            return f"{amount / 100000000:.1f}억원"
        if amount >= 10000:
            return f"{amount / 10000:.0f}만원"
        return f"{amount:,}원"
    except Exception:
        return amount_str


def get_status(deadline):
    if not deadline:
        return "진행중"
    try:
        deadline_date = datetime.strptime(deadline, "%Y-%m-%d").date()
        days_left = (deadline_date - date.today()).days
        if days_left < 0:
            return "마감"
        if days_left <= 7:
            return "마감임박"
        return "진행중"
    except Exception:
        return "진행중"


def get_days_left(deadline):
    if not deadline:
        return "-"
    try:
        deadline_date = datetime.strptime(deadline, "%Y-%m-%d").date()
        days_left = (deadline_date - date.today()).days
        if days_left < 0:
            return "마감"
        if days_left == 0:
            return "오늘 마감"
        return f"D-{days_left}"
    except Exception:
        return "-"


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
    except Exception:
        return []


def fetch_worldbank_bids(keyword, num_rows=30, include_closed=False):
    url = "https://search.worldbank.org/api/v2/procnotices"
    params = {"format": "json", "qterm": keyword, "rows": num_rows * 3, "os": 0}
    try:
        response = requests.get(url, params=params, timeout=30)
        data = response.json()
        proc_data = data.get("procnotices", {})
        results = []
        for key, doc in proc_data.items() if isinstance(proc_data, dict) else []:
            if key in ["total", "rows"]:
                continue
            if not isinstance(doc, dict):
                continue
            deadline_raw = doc.get("submission_date", "") or doc.get("deadline_date", "")
            deadline = parse_date(deadline_raw)
            if not include_closed and deadline:
                try:
                    if datetime.strptime(deadline, "%Y-%m-%d").date() < date.today():
                        continue
                except Exception:
                    pass
            notice_id = doc.get("id", key)
            detail_url = doc.get("url", "")
            if not detail_url and notice_id:
                detail_url = f"https://projects.worldbank.org/en/projects-operations/procurement-detail/{notice_id}"
            bid = {
                "source": "World Bank",
                "id": notice_id,
                "title": doc.get("notice_title", "") or doc.get("project_name", ""),
                "agency": doc.get("borrower", "") or doc.get("buyer", ""),
                "country": doc.get("countryname", "") or doc.get("country", ""),
                "deadline": deadline,
                "budget": "별도 확인",
                "url": detail_url,
                "method": doc.get("notice_type", "") or doc.get("procurement_method", "") or "-",
            }
            if bid["title"]:
                results.append(bid)
        return results[:num_rows]
    except Exception:
        return []


def trigger_search():
    st.session_state.do_search = True


def render_bid_card(bid):
    status = get_status(bid.get("deadline", ""))
    color = {"진행중": "green", "마감임박": "orange", "마감": "gray"}.get(status, "gray")
    with st.container(border=True):
        col1, col2 = st.columns([4, 1])
        with col1:
            emoji = "🇰🇷" if bid["source"] == "나라장터" else "🌍"
            title = bid.get("title", "제목 없음")
            short = title[:55] + "..." if len(title) > 55 else title
            if bid.get("url"):
                st.markdown(f"**{emoji} [{short}]({bid['url']})**")
            else:
                st.markdown(f"**{emoji} {short}**")
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
            st.link_button("🔗 상세보기", bid["url"], use_container_width=True)


def render_stats(bids):
    total = len(bids)
    nara = len([b for b in bids if b["source"] == "나라장터"])
    wb = len([b for b in bids if b["source"] == "World Bank"])
    urgent = len([b for b in bids if get_status(b.get("deadline", "")) == "마감임박"])
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("전체", f"{total}건")
    c2.metric("나라장터", f"{nara}건")
    c3.metric("World Bank", f"{wb}건")
    c4.metric("마감임박", f"{urgent}건")


with st.sidebar:
    st.title("🌐 BidScope")
    st.divider()
    sources = st.multiselect("데이터 소스", ["나라장터", "World Bank"], key="sources")
    keywords_input = st.text_area("검색 키워드 (쉼표 구분)", height=80, key="keywords_input")
    max_results = st.slider("소스별 최대 결과", 10, 50, key="max_results")
    include_closed = st.checkbox("마감된 공고도 포함", key="include_closed")
    st.button("🔍 검색", type="primary", use_container_width=True, on_click=trigger_search)
    st.divider()
    st.subheader("🔗 기관 바로가기")
    lcol = st.columns(2)
    for i, (name, url) in enumerate(EXTERNAL_LINKS.items()):
        lcol[i % 2].link_button(name, url, use_container_width=True)

st.title("🌐 글로벌 입찰정보 통합 플랫폼")
st.caption("나라장터 · World Bank 입찰공고를 한 곳에서 검색하세요")

if st.session_state.do_search:
    keywords = [k.strip() for k in keywords_input.split(",") if k.strip()]
    if not keywords:
        st.warning("검색 키워드를 입력해주세요.")
    elif not sources:
        st.warning("데이터 소스를 선택해주세요.")
    else:
        all_bids = []
        prog = st.progress(0)
        txt = st.empty()
        total = len(sources) * len(keywords)
        step = 0
        for src in sources:
            for kw in keywords:
                step += 1
                prog.progress(step / total)
                txt.text(f"검색 중: {src} - {kw}")
                if src == "나라장터":
                    res = fetch_nara_bids(kw, max_results // len(keywords) + 1)
                else:
                    res = fetch_worldbank_bids(kw, max_results // len(keywords) + 1, include_closed)
                all_bids.extend(res)
                time.sleep(0.1)
        prog.empty()
        txt.empty()
        seen = set()
        unique = []
        for b in all_bids:
            key = f"{b['source']}_{b['id']}"
            if key not in seen:
                seen.add(key)
                unique.append(b)
        unique.sort(key=lambda x: x.get("deadline", "") or "9999-99-99")
        st.session_state.bids = unique
        st.session_state.search_time = datetime.now().strftime("%Y-%m-%d %H:%M")
    st.session_state.do_search = False

if st.session_state.bids:
    st.success(f"🕐 {st.session_state.search_time} 검색 완료")
    render_stats(st.session_state.bids)
    st.divider()
    flt = st.selectbox("소스 필터", ["전체", "나라장터", "World Bank"])
    display = st.session_state.bids if flt == "전체" else [b for b in st.session_state.bids if b["source"] == flt]
    st.subheader(f"📋 검색 결과 ({len(display)}건)")
    for bid in display:
        render_bid_card(bid)
else:
    st.info("👈 사이드바에서 키워드를 입력하고 검색 버튼을 클릭하세요.")
